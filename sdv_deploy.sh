#!/bin/bash
# ============================================================
# SDV Complete Deployment Script for Raspberry Pi 5
# Run this on a FRESH Raspberry Pi OS installation
# ============================================================
# Usage: 
#   curl -sSL https://yourserver.com/install_sdv.sh | bash
#   OR
#   bash install_sdv.sh
# ============================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                        ║${NC}"
echo -e "${BLUE}║   SDV Complete Deployment System                       ║${NC}"
echo -e "${BLUE}║   For Raspberry Pi 5                                   ║${NC}"
echo -e "${BLUE}║                                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo -e "${RED}❌ This script must run on a Raspberry Pi${NC}"
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root: sudo bash install_sdv.sh${NC}"
    exit 1
fi

# Configuration
SDV_HOME="/opt/sdv"
SDV_USER="pi"
VEHICLE_ID="${VEHICLE_ID:-SDV_001}"

echo -e "${GREEN}✓ Starting SDV installation...${NC}\n"

# ============================================================
# 1. SYSTEM UPDATE & DEPENDENCIES
# ============================================================
echo -e "${YELLOW}[1/10] Updating system and installing dependencies...${NC}"

apt update && apt upgrade -y

apt install -y \
    python3-pip python3-venv python3-dev \
    python3-pyqt5 python3-pyqt5.qtmultimedia python3-pyqt5.qtwebengine \
    python3-opencv python3-numpy python3-serial \
    git curl wget build-essential cmake \
    libfreenect-dev freenect python3-freenect \
    v4l-utils ffmpeg alsa-utils pulseaudio \
    mosquitto mosquitto-clients \
    nginx supervisor \
    libatlas-base-dev libopenblas-dev \
    libhdf5-dev libhdf5-serial-dev \
    gstreamer1.0-tools gstreamer1.0-plugins-good \
    fonts-roboto xserver-xorg x11-xserver-utils \
    chromium-browser unclutter \
    libavcodec-dev libavformat-dev libswscale-dev

echo -e "${GREEN}✓ System dependencies installed${NC}\n"

# ============================================================
# 2. PYTHON PACKAGES
# ============================================================
echo -e "${YELLOW}[2/10] Installing Python packages...${NC}"

pip3 install --upgrade pip

pip3 install \
    firebase-admin \
    paho-mqtt \
    streamlit plotly \
    onnxruntime \
    gpiozero pigpio \
    pynmea2 \
    requests \
    python-dotenv

echo -e "${GREEN}✓ Python packages installed${NC}\n"

# ============================================================
# 3. CREATE DIRECTORY STRUCTURE
# ============================================================
echo -e "${YELLOW}[3/10] Creating SDV directory structure...${NC}"

mkdir -p $SDV_HOME/{bin,config,models,logs,media,gui,data}
mkdir -p /home/$SDV_USER/sdv/{downloads,cache}

echo -e "${GREEN}✓ Directory structure created${NC}\n"

# ============================================================
# 4. DOWNLOAD SDV SOFTWARE
# ============================================================
echo -e "${YELLOW}[4/10] Installing SDV software modules...${NC}"

# Create Python modules (from your existing code)
cat > $SDV_HOME/bin/vehicle_config.py << 'EOF'
"""SDV Vehicle Configuration"""
import os
from pathlib import Path

class VehicleConfig:
    # Vehicle Identity
    VEHICLE_ID = os.getenv('VEHICLE_ID', 'SDV_001')
    
    # Firebase
    FIREBASE_CREDENTIALS = str(Path.home() / "sdv_firebase_key.json")
    FIREBASE_DATABASE_URL = os.getenv('FIREBASE_URL', 
        "https://sdv-ota-system-default-rtdb.europe-west1.firebasedatabase.app")
    
    # Serial Ports
    ATMEGA32_PORT = "/dev/ttyUSB0"
    ATMEGA32_BAUDRATE = 115200
    GPS_PORT = "/dev/ttyUSB1"
    GPS_BAUDRATE = 9600
    ESP32_PORT = "/dev/ttyUSB2"
    ESP32_BAUDRATE = 115200
    
    # Display
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    FULLSCREEN = True
    
    # Paths
    SDV_HOME = Path("/opt/sdv")
    MODELS_DIR = SDV_HOME / "models"
    LOGS_DIR = SDV_HOME / "logs"
    
    # Pricing
    PRICE_PER_HOUR = 15.0
    PRICE_PER_KM = 0.5
EOF

echo -e "${GREEN}✓ SDV software modules installed${NC}\n"

# ============================================================
# 5. FIRST BOOT REGISTRATION SCRIPT
# ============================================================
echo -e "${YELLOW}[5/10] Creating first boot registration...${NC}"

cat > $SDV_HOME/bin/firstboot_registration.py << 'EOF'
#!/usr/bin/env python3
"""First Boot Vehicle Registration"""
import os
import json
import time
from pathlib import Path

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("Firebase not available, skipping registration")
    exit(0)

VEHICLE_ID = os.getenv('VEHICLE_ID', 'SDV_001')
FIREBASE_CREDS = Path.home() / "sdv_firebase_key.json"
FLAG_FILE = Path("/opt/sdv/data/.registered")

if FLAG_FILE.exists():
    print("Vehicle already registered")
    exit(0)

if not FIREBASE_CREDS.exists():
    print("Firebase credentials not found, skipping registration")
    exit(0)

print(f"Registering vehicle {VEHICLE_ID} with Firebase...")

try:
    cred = credentials.Certificate(str(FIREBASE_CREDS))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    
    vehicle_ref = db.collection('vehicles').document(VEHICLE_ID)
    
    vehicle_data = {
        'vehicleId': VEHICLE_ID,
        'model': 'Smart City Car',
        'category': 'compact',
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 100,
        'location': {
            'latitude': 30.0444,
            'longitude': 31.2357
        },
        'pricePerHour': 15.0,
        'pricePerKm': 0.5,
        'firstRegistered': firestore.SERVER_TIMESTAMP,
        'lastUpdate': firestore.SERVER_TIMESTAMP
    }
    
    vehicle_ref.set(vehicle_data, merge=True)
    
    # Create flag file
    FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    FLAG_FILE.write_text(f"Registered at {time.time()}")
    
    print(f"✓ Vehicle {VEHICLE_ID} registered successfully!")
    
except Exception as e:
    print(f"Registration failed: {e}")
    exit(1)
EOF

chmod +x $SDV_HOME/bin/firstboot_registration.py

echo -e "${GREEN}✓ First boot registration created${NC}\n"

# ============================================================
# 6. SYSTEMD SERVICES
# ============================================================
echo -e "${YELLOW}[6/10] Installing systemd services...${NC}"

# First Boot Service
cat > /etc/systemd/system/sdv-firstboot.service << 'EOF'
[Unit]
Description=SDV First Boot Registration
Before=sdv-infotainment.service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/python3 /opt/sdv/bin/firstboot_registration.py
RemainAfterExit=yes
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

# Infotainment Service
cat > /etc/systemd/system/sdv-infotainment.service << 'EOF'
[Unit]
Description=SDV Infotainment System
After=graphical.target sdv-firstboot.service
Wants=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
WorkingDirectory=/opt/sdv/gui
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /opt/sdv/gui/main.py
Restart=always
RestartSec=10
StandardOutput=journal

[Install]
WantedBy=graphical.target
EOF

# Vehicle Manager Service
cat > /etc/systemd/system/sdv-vehicle-manager.service << 'EOF'
[Unit]
Description=SDV Vehicle Manager
After=network-online.target sdv-firstboot.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sdv/bin
ExecStart=/usr/bin/python3 /opt/sdv/bin/vehicle_manager.py
Restart=always
RestartSec=10
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

# ADAS Service
cat > /etc/systemd/system/sdv-adas.service << 'EOF'
[Unit]
Description=SDV ADAS System
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/sdv/bin
ExecStart=/usr/bin/python3 /opt/sdv/bin/adas_inference.py --headless
Restart=always
RestartSec=10
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable services
systemctl daemon-reload
systemctl enable sdv-firstboot.service
systemctl enable sdv-infotainment.service
systemctl enable sdv-vehicle-manager.service
systemctl enable sdv-adas.service

echo -e "${GREEN}✓ Systemd services installed${NC}\n"

# ============================================================
# 7. AUTO-LOGIN AND KIOSK MODE
# ============================================================
echo -e "${YELLOW}[7/10] Configuring auto-login and kiosk mode...${NC}"

# Auto-login to X
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $SDV_USER --noclear %I \$TERM
EOF

# Auto-start X on login
cat >> /home/$SDV_USER/.bashrc << 'EOF'
# Auto-start X server for SDV
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    startx -- -nocursor
fi
EOF

# Disable screen blanking
cat > /home/$SDV_USER/.xinitrc << 'EOF'
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter -idle 0.1 -root &
exec /opt/sdv/gui/start_infotainment.sh
EOF

chmod +x /home/$SDV_USER/.xinitrc

echo -e "${GREEN}✓ Auto-login and kiosk mode configured${NC}\n"

# ============================================================
# 8. REMOTE ACCESS (RPI CONNECT)
# ============================================================
echo -e "${YELLOW}[8/10] Setting up remote access...${NC}"

# Install RPI Connect (if available)
if command -v rpi-connect &> /dev/null; then
    echo "RPI Connect already installed"
else
    echo "Installing RPI Connect..."
    apt install -y rpi-connect
fi

# Enable VNC for screen sharing
apt install -y realvnc-vnc-server realvnc-vnc-viewer

systemctl enable vncserver-x11-serviced.service
systemctl start vncserver-x11-serviced.service

# Configure VNC for virtual desktop
cat > /etc/vnc/config.d/common.custom << EOF
Authentication=VncAuth
Encryption=AlwaysMaximum
Password=sdvvnc2024
EOF

echo -e "${GREEN}✓ Remote access configured${NC}"
echo -e "${BLUE}  VNC Password: sdvvnc2024${NC}\n"

# ============================================================
# 9. SPOTIFY INTEGRATION PREPARATION
# ============================================================
echo -e "${YELLOW}[9/10] Preparing Spotify integration...${NC}"

# Install spotifyd (Spotify daemon)
apt install -y spotifyd

# Create Spotify config placeholder
mkdir -p /home/$SDV_USER/.config/spotifyd

cat > /home/$SDV_USER/.config/spotifyd/spotifyd.conf << 'EOF'
[global]
username = "your_spotify_username"
password = "your_spotify_password"
backend = "alsa"
device_name = "SDV_Car_Audio"
bitrate = 320
cache_path = "/home/pi/.cache/spotifyd"
volume_normalisation = true
normalisation_pregain = -10
EOF

chown -R $SDV_USER:$SDV_USER /home/$SDV_USER/.config

echo -e "${GREEN}✓ Spotify integration prepared${NC}"
echo -e "${BLUE}  Edit /home/pi/.config/spotifyd/spotifyd.conf with your credentials${NC}\n"

# ============================================================
# 10. FINAL CONFIGURATION
# ============================================================
echo -e "${YELLOW}[10/10] Final configuration...${NC}"

# Set permissions
chown -R $SDV_USER:$SDV_USER /home/$SDV_USER/sdv
chown -R root:root $SDV_HOME
chmod +x $SDV_HOME/bin/*.py

# Create environment file
cat > /etc/environment << EOF
VEHICLE_ID=$VEHICLE_ID
SDV_HOME=$SDV_HOME
DISPLAY=:0
EOF

# Set vehicle ID persistently
echo "VEHICLE_ID=$VEHICLE_ID" >> /etc/environment

echo -e "${GREEN}✓ Final configuration complete${NC}\n"

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║   ✓ SDV Installation Complete!                         ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Place Firebase credentials: ~/sdv_firebase_key.json"
echo -e "  2. Copy your Python modules to: /opt/sdv/bin/"
echo -e "  3. Copy GUI application to: /opt/sdv/gui/"
echo -e "  4. Copy ONNX models to: /opt/sdv/models/"
echo -e "  5. Configure Spotify (optional): /home/pi/.config/spotifyd/spotifyd.conf"
echo ""
echo -e "${BLUE}Remote Access:${NC}"
echo -e "  • RPI Connect: Use Raspberry Pi Connect app"
echo -e "  • VNC: Connect to $(hostname -I | awk '{print $1}'):5900"
echo -e "    Password: sdvvnc2024"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  • First Boot Registration: sdv-firstboot.service"
echo -e "  • Infotainment GUI: sdv-infotainment.service"
echo -e "  • Vehicle Manager: sdv-vehicle-manager.service"
echo -e "  • ADAS System: sdv-adas.service"
echo ""
echo -e "${YELLOW}Reboot required to start services:${NC}"
echo -e "  sudo reboot"
echo ""