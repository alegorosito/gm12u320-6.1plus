#!/bin/bash

echo "Installing GM12U320 dependencies (simple method)"
echo "================================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install required packages with --break-system-packages
echo "📦 Installing required packages..."

echo "Installing requests..."
pip3 install --break-system-packages requests

echo "Installing Pillow..."
pip3 install --break-system-packages Pillow

echo "Installing numpy..."
pip3 install --break-system-packages numpy

echo "Installing mss..."
pip3 install --break-system-packages mss

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "🚀 Usage:"
echo "  python3 show_image.py                    # Use default image"
echo "  python3 show_image.py <image_url>        # Use custom image URL"
echo "  python3 simple_mirror.py                 # Simple live mirror"
echo "  python3 live_mirror.py                   # Fast live mirror (if mss works)"
echo ""
echo "📝 Example:"
echo "  python3 show_image.py 1-800x600.jpg" 