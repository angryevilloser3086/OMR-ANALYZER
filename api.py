import os
from pickle import FALSE
import tempfile
import requests
import sys
import traceback
from pathlib import Path
import shutil
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from src.utils.parsing import open_config_with_defaults
from src.template import Template
from src.entry import process_dir
# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('omr_checker.log')
    ]
)

# Get logger for this module
logger = logging.getLogger(__name__)

def download_file(url: str, target_path: Path) -> bool:
    """Download a file from any URL to the specified path"""
    try:
        logger.info(f"Downloading file from {url} to {target_path}")
        # Handle Dropbox links
        if 'dropbox.com' in url and 'dl=0' in url:
            url = url.replace('dl=0', 'dl=1')
            logger.debug(f"Converted Dropbox URL to direct download: {url}")
            
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Successfully downloaded {url}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}", exc_info=True)
        return False

def process_omr(request_data: dict) -> dict:
    """
    Process OMR sheets from URLs and save files in project's inputs folder
    """
    logger.info("Starting OMR processing request")
    logger.debug(f"Request data: {request_data}")
    
    # Create inputs directory in project root if it doesn't exist
    project_root = Path(__file__).parent
    inputs_dir = project_root / "inputs"
    inputs_dir.mkdir(exist_ok=True)
    
    # Create a timestamped subdirectory for this request
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    request_dir = inputs_dir / f"request_{timestamp}"
    request_dir.mkdir()
    
    try:
        logger.info(f"Created request directory: {request_dir}")
        
        # 1. Define file paths in the request directory
        template_path = request_dir / "template.json"
        config_path = request_dir / "config.json"
        marker_path = request_dir / "marker.jpg"
        images_dir = request_dir / "images"
        images_dir.mkdir()
        
        # 2. Download required files
        logger.info("Starting file downloads...")
        if not download_file(request_data['template_url'], template_path):
            error_msg = "Failed to download template"
            logger.error(error_msg)
            return {"error": error_msg}
            
        if not download_file(request_data['config_url'], config_path):
            error_msg = "Failed to download config"
            logger.error(error_msg)
            return {"error": error_msg}
            
        if not download_file(request_data['marker_img_url'], marker_path):
            error_msg = "Failed to download marker image"
            logger.error(error_msg)
            return {"error": error_msg}
            
        # 3. Download OMR sheet images
        logger.info("Downloading OMR sheet images...")
        downloaded_images = []
        for img in request_data['images']:
            img_filename = f"sheet_{img['roll']}.jpg"
            img_path = images_dir / img_filename
            if not download_file(img['url'], img_path):
                error_msg = f"Failed to download image for roll {img['roll']}"
                logger.error(error_msg)
                return {"error": error_msg}
            downloaded_images.append({
                "roll": img['roll'],
                "path": str(img_path.relative_to(project_root))
            })
            logger.debug(f"Downloaded image for roll {img['roll']} to {img_path}")

        # 4. Process the OMR sheets
        logger.info("Starting OMR processing...")
        output_dir = project_root / "outputs"/f"request_{timestamp}"
        output_dir.mkdir(exist_ok=True)
        
        try:
            tuning_config = open_config_with_defaults(config_path)
            template = Template(template_path, tuning_config)
            logger.info(f"Successfully loaded template and config {template} :: images dir :: {images_dir}")
            
            args = {
                'input_paths': [str(images_dir)],
                'output_dir': str(output_dir),
                'autoAlign': request_data.get('auto_align', False),  # Default: False
                'setLayout': request_data.get('set_layout', False),  # Default: False
                'debug': False,
            }
            
            logger.debug(f"Calling process_dir with args: {args}")
            all_responses= process_dir(
                root_dir=images_dir,
                curr_dir=images_dir,
                args=args,
                template=template,
                tuning_config=tuning_config
            )
            
            # Read and process results
            # results_file = output_dir / "Results" / "Results.csv"
            # if not results_file.exists():
            #     error_msg = f"Results file not found at {results_file}"
            #     logger.error(error_msg)
            #     return {"error": error_msg}
                
            logger.info("Successfully processed OMR sheets")
            try:
                import shutil
                shutil.rmtree(request_dir)
                logger.info(f"Successfully cleaned up input directory: {images_dir}")
            except Exception as e:
                logger.warning(f"Warning: Could not clean up input directory {images_dir}: {str(e)}")
            
            
            # ... rest of your results processing code ...
            
            return {
                "status": "success",
                "request_dir": str(request_dir.relative_to(project_root)),
                "responses":all_responses,
                "message": "OMR processing completed successfully"
            }
            
        except Exception as e:
            error_msg = f"Error during OMR processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}
            
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Clean up the request directory if there was an error
        shutil.rmtree(request_dir, ignore_errors=True)
        return {"error": error_msg}
    finally:
        logger.info(f"Completed processing for request {timestamp}")

# Flask app setup
app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process():
    logger.info("Received new /process request")
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400
        logger.debug(f"Processing request data: {data}")
        result = process_omr(data)
        logger.info("Request processing completed")
        return jsonify(result)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Docker health checks and monitoring"""
    try:
        # Add any specific health checks here (database connectivity, etc.)
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'omr-analyzer'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'omr-analyzer'
        }, 500


if __name__ == '__main__':
    logger.info("Starting OMR Checker API")
    app.run(debug=True, host='0.0.0.0', port=5000)