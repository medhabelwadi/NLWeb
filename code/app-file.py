# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file is the entry point for the NLWeb Sample App.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import asyncio
import os
import sys
import argparse
from webserver.WebServer import fulfill_request, start_server
from dotenv import load_dotenv
from utils.logging_config_helper import get_logging_config, get_configured_logger

def initialize_logging(log_level=None, profile=None):
    """Initialize the logging system with the specified settings"""
    config = get_logging_config()
    
    # Apply profile if specified (development, production, testing)
    if profile:
        config.apply_profile(profile)
        
    # Override log level if specified
    if log_level:
        config.set_all_loggers_level(log_level)
    
    # Get a logger for the main application
    logger = get_configured_logger("app")
    logger.info(f"Application logging initialized with profile '{profile or 'default'}' and level '{log_level or 'from config'}'")
    
    # Also log environment information
    env_type = os.environ.get("ENVIRONMENT_TYPE", "development")
    logger.info(f"Running in {env_type} environment")
    
    # Log output directory configuration
    output_dir = os.getenv('NLWEB_OUTPUT_DIR')
    if output_dir:
        logger.info(f"Using output directory: {output_dir}")
    
    return logger

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NLWeb Sample App')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the global logging level')
    parser.add_argument('--profile', choices=['development', 'production', 'testing'],
                        help='Set the logging profile (development, production, or testing)')
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()
    
    # Get environment-specific profile if not specified in args
    profile = args.profile or os.environ.get("LOG_PROFILE", "development")
    
    # Initialize logging system
    app_logger = initialize_logging(
        log_level=args.log_level, 
        profile=profile
    )
    
    # Log startup
    app_logger.info("NLWeb Sample App starting up")

    # Get port from Azure environment or use default
    port = int(os.environ.get('PORT', 8000))
    app_logger.info(f"Starting server on port {port}")
    
    # Start the server
    try:
        asyncio.run(start_server(
            host='0.0.0.0',
            port=port,
            fulfill_request=fulfill_request
        ))
    except Exception as e:
        app_logger.critical(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
