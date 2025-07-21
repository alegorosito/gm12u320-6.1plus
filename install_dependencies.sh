#!/bin/bash

# Install Python dependencies for GM12U320 projector image display

echo "🐍 Installing Python dependencies for GM12U320 projector"
echo "========================================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install required Python packages
echo "📦 Installing required packages..."

# Install requests for HTTP requests
echo "Installing requests..."
pip3 install requests

# Install Pillow for image processing
echo "Installing Pillow..."
pip3 install Pillow

# Install numpy for array operations
echo "Installing numpy..."
pip3 install numpy

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "🚀 Usage:"
echo "  python3 show_image.py                    # Use default image"
echo "  python3 show_image.py <image_url>        # Use custom image URL"
echo ""
echo "📝 Example:"
echo "  python3 show_image.py https://picsum.photos/id/1/800/600" 