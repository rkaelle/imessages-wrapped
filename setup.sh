#!/bin/bash
# Setup script for iMessage Wrapped

echo "Setting up iMessage Wrapped..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✓ Setup complete!"
echo ""
echo "To run the app:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run Streamlit app: streamlit run web/app.py"
echo ""
echo "To deactivate virtual environment when done:"
echo "  deactivate"
