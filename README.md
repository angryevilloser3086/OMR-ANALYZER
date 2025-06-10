# OMRChecker API

This API provides a web service layer on top of the OMRChecker project, allowing you to process OMR sheets via HTTP requests.

## Getting Started

### Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Python 3.9+ (for local development)

### Running with Docker

The easiest way to run the API is using Docker:

```bash
# Build and start the API
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Running Locally

If you prefer to run the API locally:

```bash
# Install dependencies
pip install -r requirements.txt
pip install flask gunicorn

# Run the API
python api.py
```

## API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy"
}
```

### Process OMR Sheets

```
POST /process
```

Process OMR sheets from the provided URLs.

**Request Format:**
```json
{
  "template_url": "https://example.com/template.json",
  "config_url": "https://example.com/config.json",
  "images": [
    {
      "roll": 1,
      "url": "https://example.com/image1.jpg"
    },
    {
      "roll": 2,
      "url": "https://example.com/image2.jpg"
    }
  ]
}
```

**Response Format:**
```json
[
  {
    "roll": 1,
    "response": {
      "q1": "A",
      "q2": "B",
      "q3": "C",
      "q4": "D",
      "q5": "E"
    }
  },
  {
    "roll": 2,
    "response": {
      "q1": "A",
      "q2": "B",
      "q3": "C",
      "q4": "D",
      "q5": "E"
    }
  }
]
```

### Batch Process (Coming Soon)

```
POST /batch-process
```

Process multiple OMR sheets in batch mode (optimized for larger batches).

## Template and Config Files

The API requires template and config files to be accessible via URLs. These files should follow the same format as the standard OMRChecker template and config files.

### Template File Example

The template file defines the layout of the OMR sheet, including the positions of bubbles and other elements.

### Config File Example

The config file contains tuning parameters for the OMR processing.

## Deployment

### Server Requirements

- At least 2GB RAM
- 1 CPU core (2+ recommended for better performance)
- 10GB disk space

### Production Deployment

For production deployment, consider:

1. Using a reverse proxy like Nginx
2. Setting up SSL/TLS
3. Implementing rate limiting
4. Adding authentication

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- 200: Success
- 400: Bad request (missing parameters)
- 500: Server error

Error responses include a JSON object with an "error" field containing a description of the error.

## License

This API is part of the OMRChecker project and is subject to the same license.
