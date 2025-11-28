#!/bin/bash
# ============================================================================
# SDV Graduation Project - Complete Dependency Installation Script
# ============================================================================
# For: Raspberry Pi 5 (Bookworm OS)
# Project: Software-Defined Vehicle with ADAS, V2X, DMS, and IoT
# ============================================================================

set -e  # Exit on error

echo "============================================================================"
echo "  SDV Graduation Project - Installing All Dependencies"
echo "============================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error()   { echo -e "${RED}✗${NC} $1"; }
print_info()    { echo -e "${YELLOW}ℹ${NC} $1"; }

is_raspberry_pi() {
    [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model
    return $?
}

# ============================================================================
# 1. SYSTEM PACKAGES
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Installing System Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt update
sudo apt upgrade -y

sudo apt install -y \
    python3-pip python3-dev python3-venv build-essential cmake git wget curl unzip tar htop screen tmux \
    libopencv-dev python3-opencv libatlas3-base libopenblas-dev libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libgtk-3-dev libcanberra-gtk3-module \
    libusb-1.0-0-dev freeglut3-dev \
    python3-pyqt5 python3-pyqt5.qtquick python3-pyqt5.qtmultimedia pyqt5-dev-tools qttools5-dev-tools \
    mosquitto mosquitto-clients gcc-avr avr-libc avrdude binutils-avr

print_success "System packages installed"

# ============================================================================
# 2. Camera & Vision Libraries
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Installing Camera & Vision Libraries"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Kinect support
if ! command -v freenect-glview &>/dev/null; then
    print_info "Building libfreenect for Kinect..."
    cd /tmp
    git clone https://github.com/OpenKinect/libfreenect.git
    cd libfreenect
    mkdir -p build
    cd build
    cmake .. -DBUILD_PYTHON3=ON
    make -j$(nproc)
    sudo make install
    sudo ldconfig
    cd ~
    print_success "libfreenect installed"
else
    print_success "libfreenect already installed"
fi

# Raspberry Pi Camera
if is_raspberry_pi; then
    sudo apt install -y python3-picamera2 libcamera-dev libcamera-apps
    sudo raspi-config nonint do_camera 0
    print_success "Pi Camera support enabled"
fi

# ============================================================================
# 3. Serial Communication Tools
# ============================================================================
sudo apt install -y python3-serial minicom picocom
sudo usermod -a -G dialout $USER
print_success "Serial communication tools installed"

# ============================================================================
# 4. MQTT Broker
# ============================================================================
sudo tee /etc/mosquitto/conf.d/sdv.conf > /dev/null <<'EOF'
# SDV MQTT Configuration
listener 1883 0.0.0.0
allow_anonymous true
max_connections 100
max_queued_messages 1000
EOF

# Remove any duplicate log_dest lines in mosquitto.conf
sudo sed -i '/log_dest/d' /etc/mosquitto/mosquitto.conf

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto || true  # may fail if config issues exist
print_success "MQTT Broker configured"

# ============================================================================
# 5. Firebase & Cloud Tools
# ============================================================================
if ! command -v node &>/dev/null; then
    print_info "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

sudo npm install -g firebase-tools
print_success "Firebase CLI installed"

# ============================================================================
# 6. Python Packages (System-Wide)
# ============================================================================
python3 -m pip install --upgrade pip setuptools wheel --break-system-packages

# Core Python packages
python3 -m pip install --break-system-packages \
    numpy opencv-python opencv-python-headless pillow onnxruntime \
    pyserial pyusb pynmea2 geopy paho-mqtt firebase-admin google-cloud-firestore google-cloud-storage \
    freenect streamlit plotly pandas matplotlib cryptography pycryptodome flask flask-cors requests psutil

# Raspberry Pi specific
if is_raspberry_pi; then
    python3 -m pip install --break-system-packages RPi.GPIO smbus2 spidev
fi

print_success "Python packages installed"

# ============================================================================
# 7. ESP32 Toolchain
# ============================================================================
python3 -m pip install --break-system-packages platformio esptool
print_success "ESP32 toolchain installed"

# ============================================================================
# 8. Project Directory Structure
# ============================================================================
PROJECT_DIR="$HOME/Graduation_Project_SDV"
mkdir -p "$PROJECT_DIR"/{models/{Lane_Detection,Object_Detection,Traffic_Sign},logs,certs,keys,raspberry_pi,data,embedded_linux,esp32/src}
print_success "Project directories created"

# ============================================================================
# 9. UDEV Rules
# ============================================================================
sudo tee /etc/udev/rules.d/51-kinect.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"
EOF

sudo tee /etc/udev/rules.d/99-esp32.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="1a86", ATTR{idProduct}=="7523", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
print_success "udev rules configured"

# ============================================================================
# 10. Final Message
# ============================================================================
echo ""
echo "============================================================================"
echo "  ✓ SDV Installation Complete!"
echo "============================================================================"
echo "Project Structure: $PROJECT_DIR"
echo "Python packages installed system-wide with --break-system-packages"
echo "Activate your Python scripts with 'python3' directly."
echo "Remember: A reboot is recommended."
echo "Run: sudo reboot"
echo "============================================================================"
