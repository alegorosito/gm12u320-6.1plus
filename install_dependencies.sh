#!/bin/bash

# Install Python dependencies for GM12U320 projector image display

echo "🐍 Installing Python dependencies for GM12U320 projector"
echo "========================================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
VENV_DIR="gm12u320_env"
echo "📦 Creating virtual environment in $VENV_DIR..."

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists, removing..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Failed to create virtual environment"
    echo "Trying to install python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv
    python3 -m venv "$VENV_DIR"
fi

echo "✅ Virtual environment created"

# Activate virtual environment and install packages
echo "📦 Installing required packages in virtual environment..."

source "$VENV_DIR/bin/activate"

# Install required packages
pip install --upgrade pip

echo "Installing requests..."
pip install requests

echo "Installing Pillow..."
pip install Pillow

echo "Installing numpy..."
pip install numpy

echo "Installing mss..."
pip install mss

# Create activation script
cat > activate_env.sh << 'EOF'
#!/bin/bash
echo "🐍 Activating GM12U320 Python environment..."
source gm12u320_env/bin/activate
echo "✅ Environment activated!"
echo "🚀 Now you can run:"
echo "  python show_image.py                    # Use default image"
echo "  python show_image.py <image_url>        # Use custom image URL"
echo "  python live_mirror.py                   # Live screen mirror"
echo ""
echo "📝 Example:"
echo "  python show_image.py https://picsum.photos/id/1/800/600"
echo ""
echo "💡 To deactivate: deactivate"
EOF

chmod +x activate_env.sh

echo ""
echo "✅ All dependencies installed successfully in virtual environment!"
echo ""
echo "🚀 To use the projector scripts:"
echo "  1. Activate environment: source activate_env.sh"
echo "  2. Run scripts: python show_image.py"
echo ""
echo "📝 Or run directly:"
echo "  ./gm12u320_env/bin/python show_image.py"
echo "  ./gm12u320_env/bin/python live_mirror.py" 