import os
import sys
import logging
from azure_logger import log

# Set up logging

logger = None
def get_logger():
    global logger
    if logger is None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[  
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger('WebServer')
    return logger


# Determine the application root directory based on environment
def get_app_root():
    """Get the application root directory, handling both local and Azure environments."""
    logger = get_logger()
    # Check if running in Azure App Service
    if 'WEBSITE_SITE_NAME' in os.environ:
        # Azure App Service - use D:\home\site\wwwroot or the HOME environment variable
        azure_home = os.environ.get('HOME', '/home/site/wwwroot')
        logger.info(f"Using Azure App Service root directory: {azure_home}")
        log(f"Using Azure App Service root directory: {azure_home}")
        return azure_home
    else:
        # Local development - use the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Using local development root directory: {script_dir}")
        return script_dir

# Get the app root directory
APP_ROOT = get_app_root()
logger.info(f"Application root directory: {APP_ROOT}")
log(f"Application root directory: {APP_ROOT}")

# List all files in the app root and subdirectories to verify structure
def log_directory_structure(start_path=APP_ROOT, max_depth=3, current_depth=0):
    """Log the directory structure for debugging purposes."""
    if current_depth > max_depth:
        return
        
    try:
        for item in os.listdir(start_path):
            item_path = os.path.join(start_path, item)
            rel_path = os.path.relpath(item_path, APP_ROOT)
            if os.path.isdir(item_path):
                logger.debug(f"DIR: {rel_path}")
                log(f"DIR: {rel_path}")
                log_directory_structure(item_path, max_depth, current_depth + 1)
            else:
                logger.debug(f"FILE: {rel_path}")
                log(f"FILE: {rel_path}")
    except Exception as e:
        logger.error(f"Error listing directory {start_path}: {str(e)}")
        log(f"Error listing directory {start_path}: {str(e)}")

# Log the directory structure on startup
logger.info("Logging directory structure:")
log("Logging directory structure:")
log_directory_structure()