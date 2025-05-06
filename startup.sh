#!/bin/bash

# Change to the application directory
cd /home/site/wwwroot/code
echo "Python version:"
python --version
echo "Directory contents:"
ls -la

# Install dependencies individually to avoid whole-installation failure
echo "Installing dependencies..."
pip install -r requirements.txt


# Start the application
echo "Starting application..."
source set_keys.sh     # Test that this is not needed
echo "set_keys.sh done"
echo "Sleeping for 30 seconds"

#python app-file.py
python -m webserver/WebServer.py