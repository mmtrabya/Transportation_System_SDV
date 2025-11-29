"""
SDV System Configuration
Centralized configuration for all modules
"""

from pathlib import Path

# Base directories
BASE_DIR = Path.home() / "Graduation_Project_SDV"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
CERTS_DIR = BASE_DIR / "certs"
KEYS_DIR = BASE_DIR / "keys"

# Vehicle Information
VEHICLE_ID = "SDV001"
HARDWARE_VERSION = "1.0"

# Serial Ports
ATMEGA32_PORT = "/dev/ttyUSB0"
ATMEGA32_BAUDRATE = 115200

ESP32_PORT = "/dev/ttyUSB1"
ESP32_BAUDRATE = 115200

# MQTT Configuration
MQTT_BROKER = "localhost"  # Local Mosquitto
MQTT_PORT = 1883

# ONNX Models
LANE_MODEL = MODELS_DIR / "lane_detection.onnx"
OBJECT_MODEL = MODELS_DIR / "yolov8n.onnx"
SIGN_MODEL = MODELS_DIR / "traffic_signs.onnx"

# Update Server
UPDATE_SERVER = "http://localhost:5000"

# Create directories
for directory in [BASE_DIR, MODELS_DIR, LOGS_DIR, CERTS_DIR, KEYS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)