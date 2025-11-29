#!/bin/bash
# ============================================================
# flash_secure_v2.sh - Secure Vehicle 2 Deployment (SDV002)
# ============================================================
# This script:
# 1. Checks if credentials are already stored
# 2. If not, flashes credential setup first
# 3. Then flashes the secure main application
# ============================================================

PORT=$(ls /dev/ttyUSB* 2>/dev/null | tail -n1)
BAUD=115200

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Secure Vehicle 2 Deployment Script (SDV002)          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# Check if port is available
if [ -z "$PORT" ]; then
    echo -e "${RED}❌ Error: No USB device found${NC}"
    echo -e "${YELLOW}💡 Tip: Connect ESP32 and ensure drivers are installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found device: $PORT${NC}\n"

# Function to flash and wait
flash_and_wait() {
    local description=$1
    local source_file=$2
    local wait_time=$3
    
    echo -e "${YELLOW}📡 Step: $description${NC}"
    echo -e "   Source: $source_file"
    echo ""
    
    # Copy source to main.cpp
    cp "$source_file" src/main.cpp
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to copy source file${NC}"
        exit 1
    fi
    
    # Build and upload
    pio run -e esp32dev --target upload --upload-port "$PORT"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ Flash successful!${NC}\n"
        
        if [ -n "$wait_time" ]; then
            echo -e "${YELLOW}⏳ Waiting ${wait_time}s for operation to complete...${NC}"
            sleep "$wait_time"
        fi
        
        return 0
    else
        echo -e "\n${RED}❌ Flash failed!${NC}"
        exit 1
    fi
}

# Ask user if credentials are already stored
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Credential Status Check${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Are credentials already stored in this ESP32's NVS?"
echo ""
echo "  [1] No  - This is the FIRST TIME setup (will store credentials)"
echo "  [2] Yes - Credentials already stored (skip credential setup)"
echo ""
read -p "Enter choice [1/2]: " choice

case $choice in
    1)
        echo -e "\n${GREEN}→ Selected: First-time setup${NC}"
        echo -e "${YELLOW}⚠️  WARNING: This will store credentials in NVS${NC}\n"
        
        # Check if credential setup script exists
        if [ ! -f "scripts/setup_credentials_v2.cpp" ]; then
            echo -e "${RED}❌ Error: scripts/setup_credentials_v2.cpp not found${NC}"
            echo -e "${YELLOW}💡 Create this file first with the credentials for Vehicle 2${NC}"
            exit 1
        fi
        
        # Step 1: Flash credential setup
        flash_and_wait \
            "Storing credentials in NVS" \
            "scripts/setup_credentials_v2.cpp" \
            "5"
        
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  Credentials Stored Successfully!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        
        read -p "Press Enter to continue with main application flash..."
        ;;
        
    2)
        echo -e "\n${GREEN}→ Selected: Credentials already stored${NC}"
        echo -e "${BLUE}ℹ️  Skipping credential setup, flashing main app only${NC}\n"
        ;;
        
    *)
        echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Step 2: Flash main secure application
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Flashing Main Application${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if secure main exists
if [ ! -f "backup/main_2_secure.cpp" ]; then
    echo -e "${YELLOW}⚠️  backup/main_2_secure.cpp not found${NC}"
    echo -e "${YELLOW}    Using backup/main_2.cpp instead${NC}\n"
    MAIN_SOURCE="backup/main_2.cpp"
else
    MAIN_SOURCE="backup/main_2_secure.cpp"
fi

flash_and_wait \
    "Flashing secure V2X application" \
    "$MAIN_SOURCE" \
    ""

# Success!
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Vehicle 2 (SDV002) Deployed Successfully!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}\n"

# Open serial monitor
echo -e "${BLUE}🖥️  Opening serial monitor...${NC}"
echo -e "${YELLOW}    Press Ctrl+C to exit monitor${NC}\n"
sleep 2

pio run -e esp32dev --target upload --upload-port "$PORT" --upload-speed $BAUD
pio device monitor -e esp32dev --port "$PORT" --baud $BAUD