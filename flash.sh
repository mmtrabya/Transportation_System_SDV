#!/bin/bash

if [ "$1" == "1" ]; then
    echo "📡 Flashing Vehicle 1 (SDV_001)..."
    cp backup/main_1.cpp src/main.cpp
    pio run --target upload
    echo "✅ Vehicle 1 flashed successfully!"
    
elif [ "$1" == "2" ]; then
    echo "📡 Flashing Vehicle 2 (SDV_002)..."
    cp backup/main_2.cpp src/main.cpp
    pio run --target upload
    echo "✅ Vehicle 2 flashed successfully!"
    
else
    echo "❌ Usage: ./flash.sh [1|2]"
    echo "   ./flash.sh 1  - Flash Vehicle 1"
    echo "   ./flash.sh 2  - Flash Vehicle 2"
fi
