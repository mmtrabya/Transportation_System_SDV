#!/bin/bash

# Vehicle 1 flashing script (SDV_001)
PORT=$(ls /dev/ttyUSB* | tail -n1)
BAUD=115200

echo "📡 Flashing Vehicle 1 (SDV_001)..."
cp backup/main_1.cpp src/main.cpp

pio run -e esp32dev --target upload --upload-port $PORT
if [ $? -eq 0 ]; then
    echo "✅ Vehicle 1 flashed successfully!"
    echo "🖥️  Opening serial monitor..."
    pio device monitor -e esp32dev --port $PORT --baud $BAUD
else
    echo "❌ Flashing failed for Vehicle 1."
fi
