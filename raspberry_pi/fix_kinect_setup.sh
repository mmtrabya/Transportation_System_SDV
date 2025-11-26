#!/bin/bash
# Kinect Camera Setup Script for Raspberry Pi
# Fixes LIBUSB_ERROR_BUSY by disabling kernel drivers

echo "=========================================="
echo "Xbox 360 Kinect Setup Script"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Create udev rules for Kinect
echo "Creating udev rules for Kinect..."
cat > /etc/udev/rules.d/51-kinect.rules << 'EOF'
# Xbox 360 Kinect Motor and Camera
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"

# Unbind from kernel drivers (gspca_kinect)
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/gspca_kinect/unbind 2>/dev/null || true'"
EOF

echo "✓ udev rules created at /etc/udev/rules.d/51-kinect.rules"

# Step 2: Blacklist gspca_kinect kernel module
echo "Blacklisting gspca_kinect kernel module..."
cat > /etc/modprobe.d/blacklist-kinect.conf << 'EOF'
# Blacklist gspca_kinect to prevent it from claiming the Kinect camera
blacklist gspca_kinect
EOF

echo "✓ Kernel module blacklisted at /etc/modprobe.d/blacklist-kinect.conf"

# Step 3: Unload the module if it's currently loaded
if lsmod | grep -q gspca_kinect; then
    echo "Unloading gspca_kinect module..."
    modprobe -r gspca_kinect
    echo "✓ Module unloaded"
else
    echo "✓ gspca_kinect module not loaded"
fi

# Step 4: Reload udev rules
echo "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger
echo "✓ udev rules reloaded"

# Step 5: Check if Kinect is connected
echo ""
echo "Checking for Kinect devices..."
lsusb | grep "Microsoft Corp." | grep -E "(Kinect|Xbox NUI)"

if [ $? -eq 0 ]; then
    echo "✓ Kinect detected!"
else
    echo "⚠ Kinect not detected. Please ensure it's plugged in."
fi

# Step 6: Instructions
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Unplug and replug your Kinect USB cable"
echo "2. Wait 5 seconds for the device to initialize"
echo "3. Run your ADAS script: python3 adas_inference.py"
echo ""
echo "If issues persist, reboot your Raspberry Pi:"
echo "  sudo reboot"
echo ""
echo "=========================================="
