#!/bin/bash

# Change to the application directory
cd /home/site/wwwroot/code
echo "Python version:"
python --version
echo "Directory contents:"
ls -la

# Install dependencies individually to avoid whole-installation failure
echo "Installing dependencies..."
pip install azure-ai-inference>=1.0.0b9
pip install azure-core>=1.30.0
pip install azure-search-documents>=11.4.0
pip install azure-identity>=1.15.0
pip install anthropic>=0.18.1
pip install openai>=1.12.0
pip install google-generativeai>=0.3.2
pip install jsonschema>=4.19.1
pip install python-dotenv>=1.0.0
pip install aiohttp>=3.9.1
pip install pymilvus>=1.1.0

# Start the application
echo "Starting application..."
#source set_keys.sh     # Test that this is not needed
python app-file.py