#!/bin/bash

# Set serial port and baud rate (adjust if needed)
PORT="/dev/ttyUSB0"
BAUD=115200

if [ "$1" == "1" ]; then
    echo "📡 Flashing Vehicle 1 (SDV_001)..."
    cp backup/main_1.cpp src/main.cpp
    pio run -e esp32dev --target upload
    echo "✅ Vehicle 1 flashed successfully!"
    echo "🖥️  Opening serial monitor..."
    pio device monitor -e esp32dev --port $PORT --baud $BAUD

elif [ "$1" == "2" ]; then
    echo "📡 Flashing Vehicle 2 (SDV_002)..."
    cp backup/main_2.cpp src/main.cpp
    pio run -e esp32dev --target upload
    echo "✅ Vehicle 2 flashed successfully!"
    echo "🖥️  Opening serial monitor..."
    pio device monitor -e esp32dev --port $PORT --baud $BAUD

else
    echo "❌ Usage: ./flash.sh [1|2]"
    echo "   ./flash.sh 1  - Flash Vehicle 1"
    echo "   ./flash.sh 2  - Flash Vehicle 2"
fi
