#!/bin/bash

echo "Installing Graduation Project Dependencies..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install system packages
sudo apt install -y python3-pip python3-opencv mosquitto mosquitto-clients

# Install Python packages
pip3 install \
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
    requests

# Install Mosquitto broker
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Create directories
mkdir -p ~/Graduation_Project_SDV/{models,logs,certs,keys}

echo "Installation complete!"