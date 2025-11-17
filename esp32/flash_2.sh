#!/bin/bash

# Vehicle 2 flashing script (SDV_002)
PORT=$(ls /dev/ttyUSB* | tail -n1)
BAUD=115200

echo "📡 Flashing Vehicle 2 (SDV_002)..."
cp backup/main_2.cpp src/main.cpp

pio run -e esp32dev --target upload --upload-port $PORT
if [ $? -eq 0 ]; then
    echo "✅ Vehicle 2 flashed successfully!"
    echo "🖥️  Opening serial monitor..."
    pio device monitor -e esp32dev --port $PORT --baud $BAUD
else
    echo "❌ Flashing failed for Vehicle 2."
fi
