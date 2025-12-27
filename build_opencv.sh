#!/bin/bash
# OpenCV Build Script with GTK Support for Ubuntu/Raspberry Pi
# This will take 1-2 hours depending on your system

set -e  # Exit on any error

echo "=========================================="
echo "OpenCV Build Script with GTK Support"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will take 1-2 HOURS!"
echo "⚠️  Make sure you have at least 4GB free space"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# ==================== STEP 1: Install Dependencies ====================
echo ""
echo "=========================================="
echo "STEP 1: Installing Dependencies"
echo "=========================================="

sudo apt-get update
sudo apt-get install -y \
    build-essential cmake git pkg-config \
    libgtk2.0-dev libgtk-3-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libv4l-dev v4l-utils \
    libxvidcore-dev libx264-dev \
    libjpeg-dev libpng-dev libtiff-dev \
    gfortran openexr libatlas-base-dev \
    python3-dev python3-numpy \
    libtbb2 libtbb-dev libdc1394-22-dev \
    libopenblas-dev liblapack-dev

echo "✓ Dependencies installed"

# ==================== STEP 2: Remove Old OpenCV ====================
echo ""
echo "=========================================="
echo "STEP 2: Removing Old OpenCV"
echo "=========================================="

pip3 uninstall -y opencv-python opencv-contrib-python || true

echo "✓ Old OpenCV removed"

# ==================== STEP 3: Download OpenCV Source ====================
echo ""
echo "=========================================="
echo "STEP 3: Downloading OpenCV Source"
echo "=========================================="

cd ~
mkdir -p opencv_build
cd opencv_build

# Download OpenCV 4.8.0 (stable version)
OPENCV_VERSION="4.8.0"

if [ ! -d "opencv" ]; then
    echo "Downloading opencv ${OPENCV_VERSION}..."
    git clone --depth 1 --branch ${OPENCV_VERSION} https://github.com/opencv/opencv.git
else
    echo "opencv directory already exists, skipping download"
fi

if [ ! -d "opencv_contrib" ]; then
    echo "Downloading opencv_contrib ${OPENCV_VERSION}..."
    git clone --depth 1 --branch ${OPENCV_VERSION} https://github.com/opencv/opencv_contrib.git
else
    echo "opencv_contrib directory already exists, skipping download"
fi

echo "✓ Source code downloaded"

# ==================== STEP 4: Configure Build ====================
echo ""
echo "=========================================="
echo "STEP 4: Configuring CMake Build"
echo "=========================================="

cd ~/opencv_build/opencv
mkdir -p build
cd build

# Detect number of CPU cores
NPROC=$(nproc)
echo "Detected ${NPROC} CPU cores"

# Configure with CMake
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_build/opencv_contrib/modules \
    -D OPENCV_ENABLE_NONFREE=ON \
    -D WITH_GTK=ON \
    -D WITH_GTK_2_X=ON \
    -D WITH_V4L=ON \
    -D WITH_FFMPEG=ON \
    -D WITH_GSTREAMER=ON \
    -D WITH_TBB=ON \
    -D WITH_OPENMP=ON \
    -D BUILD_opencv_python3=ON \
    -D PYTHON3_EXECUTABLE=$(which python3) \
    -D PYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
    -D PYTHON3_PACKAGES_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
    -D BUILD_EXAMPLES=OFF \
    -D BUILD_TESTS=OFF \
    -D BUILD_PERF_TESTS=OFF \
    -D INSTALL_PYTHON_EXAMPLES=OFF \
    -D INSTALL_C_EXAMPLES=OFF \
    ..

echo ""
echo "✓ CMake configuration complete"
echo ""
echo "=========================================="
echo "Checking GTK Support in Configuration"
echo "=========================================="

# Verify GTK is enabled
if grep -q "GTK.*YES" CMakeCache.txt || grep -q "GTK_2.*YES" CMakeCache.txt; then
    echo "✓ GTK support: ENABLED"
else
    echo "✗ GTK support: DISABLED"
    echo "⚠️  Warning: GTK may not be properly detected!"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ==================== STEP 5: Compile OpenCV ====================
echo ""
echo "=========================================="
echo "STEP 5: Compiling OpenCV"
echo "=========================================="
echo "This will take 1-2 hours..."
echo "You can monitor progress by opening another terminal and running:"
echo "  watch -n 1 'ps aux | grep make'"
echo ""

# Compile with all available cores
make -j${NPROC}

echo "✓ Compilation complete"

# ==================== STEP 6: Install OpenCV ====================
echo ""
echo "=========================================="
echo "STEP 6: Installing OpenCV"
echo "=========================================="

sudo make install
sudo ldconfig

echo "✓ OpenCV installed"

# ==================== STEP 7: Verify Installation ====================
echo ""
echo "=========================================="
echo "STEP 7: Verifying Installation"
echo "=========================================="

echo ""
echo "Testing Python import..."
python3 -c "import cv2; print(f'OpenCV version: {cv2.__version__}')" || {
    echo "✗ Python import failed!"
    exit 1
}

echo ""
echo "Checking GTK support..."
GTK_STATUS=$(python3 -c "import cv2; info = cv2.getBuildInformation(); print('YES' if 'GTK' in info and 'YES' in info else 'NO')")

if [ "$GTK_STATUS" = "YES" ]; then
    echo "✓ GTK support: ENABLED"
else
    echo "✗ GTK support: NOT FOUND"
    echo ""
    echo "Full build information:"
    python3 -c "import cv2; print(cv2.getBuildInformation())" | grep -A 3 "GUI"
fi

echo ""
echo "Testing window creation..."
python3 << 'PYTHON_TEST'
import cv2
import numpy as np
try:
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imshow('Test Window', test_img)
    cv2.waitKey(1)
    cv2.destroyAllWindows()
    print("✓ Window creation: SUCCESS")
except Exception as e:
    print(f"✗ Window creation: FAILED - {e}")
PYTHON_TEST

# ==================== STEP 8: Cleanup ====================
echo ""
echo "=========================================="
echo "STEP 8: Cleanup (Optional)"
echo "=========================================="
echo ""
echo "Build files are in ~/opencv_build/"
echo "You can remove them to free up ~3GB of space:"
echo "  rm -rf ~/opencv_build"
echo ""
read -p "Remove build files now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ~
    rm -rf opencv_build
    echo "✓ Build files removed"
else
    echo "Build files kept in ~/opencv_build/"
fi

# ==================== FINAL SUMMARY ====================
echo ""
echo "=========================================="
echo "✓ INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "OpenCV has been built and installed with GTK support"
echo ""
echo "You can now run your ADAS system with GUI:"
echo "  python3 ./adas_inference.py"
echo ""
echo "To verify GTK support anytime, run:"
echo "  python3 -c \"import cv2; print(cv2.getBuildInformation())\" | grep -i gtk"
echo ""