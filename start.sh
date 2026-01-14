#!/bin/bash

# Ensure we're in the script's directory
cd "$(dirname "$0")"

echo "Checking Python environment..."

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install Python 3."
    exit 1
fi

# Activate venv if it exists, otherwise create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "Starting the application..."
python app.py
