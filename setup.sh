#!/bin/bash

# Setup script for GitHub Auto Signup tool

echo "Setting up GitHub Auto Signup tool..."

# Install Python dependencies
echo "Installing Python dependencies..."
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "Before running the script, make sure:"
echo "1. Firefox is installed"
echo "2. You have a stable internet connection"
echo "3. undetected-geckodriver will auto-download compatible geckodriver"
echo ""
echo "Note: The script now uses undetected-geckodriver for stealth automation"
echo "This helps bypass bot detection systems on websites"
echo ""
echo "To run the script: python main.py"
