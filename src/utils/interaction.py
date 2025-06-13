from dataclasses import dataclass
import os

import cv2
import numpy as np

from src.logger import logger
from src.utils.image import ImageUtils

# Check if we're running in a headless environment (like Docker)
HEADLESS_MODE = os.environ.get('HEADLESS', 'False').lower() in ('true', '1', 't')
logger.info(f"Running in {'headless' if HEADLESS_MODE else 'display'} mode")

# Default display dimensions
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080

# Try to get actual display info if not in headless mode
if not HEADLESS_MODE:
    try:
        from screeninfo import get_monitors
        monitors = get_monitors()
        if monitors:
            monitor_window = monitors[0]
            WINDOW_WIDTH, WINDOW_HEIGHT = monitor_window.width, monitor_window.height
        else:
            WINDOW_WIDTH, WINDOW_HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
    except Exception as e:
        logger.warning(f"Could not get display information: {e}")
        WINDOW_WIDTH, WINDOW_HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
else:
    WINDOW_WIDTH, WINDOW_HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
    logger.info(f"Using default window size in headless mode: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")


@dataclass
class ImageMetrics:
    # TODO: Move TEXT_SIZE, etc here and find a better class name
    window_width, window_height = WINDOW_WIDTH, WINDOW_HEIGHT
    # for positioning image windows
    window_x, window_y = 0, 0
    reset_pos = [0, 0]


class InteractionUtils:
    """Perform primary functions such as displaying images and reading responses"""

    image_metrics = ImageMetrics()

    @staticmethod
    def show(name, origin, pause=1, resize=False, reset_pos=None, config=None):
        image_metrics = InteractionUtils.image_metrics
        if origin is None:
            logger.info(f"'{name}' - NoneType image to show!")
            return
        
        if resize:
            if not config:
                raise Exception("config not provided for resizing the image to show")
            img = ImageUtils.resize_util(origin, config.dimensions.display_width)
        else:
            img = origin

        # In headless mode, just log that we would show the image
        if HEADLESS_MODE:
            h, w = img.shape[:2]
            logger.info(f"[HEADLESS] Would show image '{name}' with dimensions {w}x{h}")
            return
            
        # Display logic for non-headless mode
        if not is_window_available(name):
            cv2.namedWindow(name)

        cv2.imshow(name, img)

        if reset_pos:
            image_metrics.window_x = reset_pos[0]
            image_metrics.window_y = reset_pos[1]

        cv2.moveWindow(
            name,
            image_metrics.window_x,
            image_metrics.window_y,
        )

        h, w = img.shape[:2]

        # Set next window position
        margin = 25
        w += margin
        h += margin

        w, h = w // 2, h // 2
        if image_metrics.window_x + w > image_metrics.window_width:
            image_metrics.window_x = 0
            if image_metrics.window_y + h > image_metrics.window_height:
                image_metrics.window_y = 0
            else:
                image_metrics.window_y += h
        else:
            image_metrics.window_x += w

        if pause:
            logger.info(
                f"Showing '{name}'\n\t Press Q on image to continue. Press Ctrl + C in terminal to exit"
            )

            wait_q()
            InteractionUtils.image_metrics.window_x = 0
            InteractionUtils.image_metrics.window_y = 0


@dataclass
class Stats:
    # TODO Fill these for stats
    # Move qbox_vals here?
    # badThresholds = []
    # veryBadPoints = []
    files_moved = 0
    files_not_moved = 0


def wait_q():
    if HEADLESS_MODE:
        logger.info("[HEADLESS] Skipping wait for key press in headless mode")
        return
        
    esc_key = 27
    while cv2.waitKey(1) & 0xFF not in [ord("q"), esc_key]:
        pass
    cv2.destroyAllWindows()


def is_window_available(name: str) -> bool:
    """Checks if a window is available"""
    if HEADLESS_MODE:
        return False
        
    try:
        cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE)
        return True
    except Exception as e:
        print(e)
        return False