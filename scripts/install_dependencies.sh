#!/bin/bash

echo "Installing Graduation Project Dependencies..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install system packages
# Note: python-pip and python-opencv are for Python 2 (deprecated)
# Using python3 equivalents instead
sudo apt install -y \
    python3-pip \
    python3-opencv \
    mosquitto \
    mosquitto-clients \
    libatlas-base-dev \
    libopenblas-dev \
    python3-dev \
    build-essential

# Install Python packages
pip install \
    paho-mqtt \
    streamlit \
    plotly \
    pandas \
    onnxruntime \
    pyserial \
    psutil \
    cryptography \
    flask \
    flask-cors \
    requests \
    numpy \
    matplotlib \
    scikit-learn \
    opencv-python \
    opencv-python-headless \
    imutils \
    geopy \
    pynmea2 \
    smbus2 \
    freenect

# Raspberry Pi specific packages (will only work on RPi)
if [ -f /proc/device-tree/model ]; then
    echo "Detected Raspberry Pi - installing RPi-specific packages..."
    pip install RPi.GPIO picamera2
    
    # Enable camera interface
    sudo raspi-config nonint do_camera 0
else
    echo "Not running on Raspberry Pi - skipping RPi.GPIO and picamera"
fi

# Note: TensorFlow and Keras removed from main install
# They are VERY large (500MB+) and require specific versions for ARM/x86
# Install them separately if needed:
#   pip install tensorflow  # For x86/x64
#   pip install tensorflow-aarch64  # For Raspberry Pi 64-bit
#   pip install tflite-runtime  # Lightweight alternative for RPi

# Install Mosquitto broker
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Configure Mosquitto
sudo tee /etc/mosquitto/conf.d/sdv.conf > /dev/null <<EOF
listener 1883
allow_anonymous true
EOF

sudo systemctl restart mosquitto

# Create directories
mkdir -p ~/Graduation_Project_SDV/{models,logs,certs,keys,raspberry_pi,data}

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
echo ""

# Verify installations
echo "Verifying core packages..."
python -c "
import sys

packages = {
    'cv2': 'opencv-python',
    'numpy': 'numpy',
    'onnxruntime': 'onnxruntime',
    'serial': 'pyserial',
    'paho.mqtt.client': 'paho-mqtt',
    'freenect': 'freenect',
    'flask': 'flask',
    'pandas': 'pandas',
    'matplotlib': 'matplotlib'
}

missing = []
for module, package in packages.items():
    try:
        __import__(module)
        print(f'  ✓ {package}')
    except ImportError:
        print(f'  ✗ {package} - MISSING')
        missing.append(package)

if missing:
    print(f'\n⚠ Missing packages: {missing}')
    print('Install with: pip install ' + ' '.join(missing))
    sys.exit(1)
else:
    print('\n✓ All core packages installed!')
"

echo ""
echo "Checking services..."
systemctl is-active --quiet mosquitto && echo "  ✓ MQTT Broker running" || echo "  ✗ MQTT Broker not running"

echo ""
echo "Project structure:"
echo "  ~/Graduation_Project_SDV/"
echo "    ├── raspberry_pi/    (Python scripts)"
echo "    ├── models/          (ONNX models)"
echo "    ├── logs/            (Log files)"
echo "    ├── certs/           (Certificates)"
echo "    ├── keys/            (Keys)"
echo "    └── data/            (Runtime data)"
echo ""
echo "Next steps:"
echo "  1. Copy your Python scripts to ~/Graduation_Project_SDV/raspberry_pi/"
echo "  2. Download ONNX models to ~/Graduation_Project_SDV/models/"
echo "  3. Test: python verify_installation.py"