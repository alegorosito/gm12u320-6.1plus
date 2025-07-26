# GM12U320 Projector Driver

Linux kernel driver for the GM12U320 USB projector.

## Features

- Full 800x600 resolution support
- Proper stride handling (2562 bytes per line)
- BGR color format support
- Real-time screen capture and display
- Multiple input sources (files, URLs, screen capture)

## Live Screen Capture

The `show_image.py` script now supports real-time screen capture and display on the projector:

```bash
# Live screen capture at 10 FPS
python3 show_image.py 10 live

# Live screen capture at 15 FPS  
python3 show_image.py 15 continuous

# Single screen capture
python3 show_image.py 10 screen

# Static image display
python3 show_image.py 10 image.jpg

# Test pattern
python3 show_image.py
```

### Requirements for Live Capture

- **Linux**: May need additional packages for screen capture
- **macOS**: Requires screen recording permissions in System Preferences
- **Windows**: Should work out of the box

### Performance

The script captures the entire screen, resizes it to 800x600, and displays it on the projector. Performance depends on:
- Screen resolution (higher = slower processing)
- FPS setting (higher = more CPU usage)
- System performance

Typical performance: 10-15 FPS on modern systems.

## Installation

See the main README for driver installation instructions.

## Usage

1. Load the driver: `sudo modprobe gm12u320`
2. Run the display script: `python3 show_image.py 10 live`
3. Press Ctrl+C to stop

The projector will show your screen in real-time at the specified FPS.
