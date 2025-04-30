import os
import logging
import traceback
from azure_logger import log
from web_server_utils import APP_ROOT
# Get logger for this module
logger = logging.getLogger('StaticFileHandler')

# Import APP_ROOT from WebServer if available, or define a fallback
try:
    from WebServer import APP_ROOT
except ImportError:
    # Fallback: determine APP_ROOT similar to WebServer.py
    def get_app_root():
        if 'WEBSITE_SITE_NAME' in os.environ:
            return os.environ.get('HOME', '/home/site/wwwroot')
        else:
            return os.path.dirname(os.path.abspath(__file__))
    
    APP_ROOT = get_app_root()


async def send_static_file(path, send_response, send_chunk):
    # Map file extensions to MIME types
    mime_types = {
        '.html': 'text/html',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.css': 'text/css',
        '.js': 'application/javascript'
    }

    # Get file extension and corresponding MIME type
    file_ext = os.path.splitext(path)[1].lower()
    content_type = mime_types.get(file_ext, 'application/octet-stream')
    
    logger.info(f"Handling static file: {path} (content type: {content_type})")
    log(f"Handling static file: {path} (content type: {content_type})")

    try:
        # Remove leading slash and sanitize path
        safe_path = os.path.normpath(path.lstrip('/'))

        # Try multiple possible root locations
        possible_roots = [
            APP_ROOT,
            os.path.join(APP_ROOT, 'site', 'wwwroot'),
            '/home/site/wwwroot',
            os.environ.get('HOME', ''),
        ]
        
        # Remove empty paths
        possible_roots = [root for root in possible_roots if root]
        
        file_found = False
        full_path = None
       
        for root in possible_roots:
            try_path = os.path.join(root, safe_path)
            if os.path.isfile(try_path):
                full_path = try_path
                file_found = True
                break
        
        if not file_found:
            # Special case: check if removing 'html/' prefix works
            if safe_path.startswith('html/'):
                stripped_path = safe_path[5:]  # Remove 'html/' prefix
                for root in possible_roots:
                    try_path = os.path.join(root, stripped_path)
                    
                    if os.path.isfile(try_path):
                        full_path = try_path
                        file_found = True
                        break
        
        if not file_found:
            # Special case: check if there's no html/static directory
            # and the files are directly in the root
            parts = safe_path.split('/')
            if len(parts) > 1:
                filename = parts[-1]
                for root in possible_roots:
                    try_path = os.path.join(root, filename)
                    if os.path.isfile(try_path):
                        full_path = try_path
                        file_found = True
                        break
        
        if file_found:
            # Try to open and read the file
            with open(full_path, 'rb') as f:
                content = f.read()
                
            # Send successful response with proper headers
            await send_response(200, {'Content-Type': content_type, 'Content-Length': str(len(content))})
            await send_chunk(content, end_response=True)
            return
        
        # If we reached here, the file was not found
        error_msg = f"File not found (1): {path} {full_path}{possible_roots}{safe_path}"
        logger.error(error_msg)
        logger.error(f"Tried paths: {possible_roots}")
        log(error_msg)
        log(f"Tried paths: {possible_roots}")
        await send_response(404, {'Content-Type': 'text/plain'})
        await send_chunk(error_msg.encode('utf-8'), end_response=True)
        
    except FileNotFoundError:
        # Send 404 if file not found
        error_msg = f"File not found (2): {path}"
        logger.error(error_msg)
        log(error_msg)
        await send_response(404, {'Content-Type': 'text/plain'})
        await send_chunk(error_msg.encode('utf-8'), end_response=True)
        
    except Exception as e:
        # Send 500 for other errors
        error_msg = f"Internal server error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        log(f"{error_msg}\n{traceback.format_exc()}")
        await send_response(500, {'Content-Type': 'text/plain'})
        await send_chunk(error_msg.encode('utf-8'), end_response=True)
