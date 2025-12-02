#!/bin/bash
# ============================================================================
# Complete Embedded Linux Build System for Raspberry Pi 5
# Includes: Custom Kernel (RT-patched), U-Boot, Initramfs, Read-only rootfs
# ============================================================================

set -e
trap 'echo "❌ Error on line $LINENO"' ERR

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   SDV Embedded Linux Build System for Raspberry Pi 5           ║
║   Custom Kernel + U-Boot + Initramfs + Read-only Root          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================================
# CONFIGURATION
# ============================================================================

# Build directories
BUILD_ROOT="${HOME}/sdv_embedded_build"
KERNEL_DIR="${BUILD_ROOT}/linux"
UBOOT_DIR="${BUILD_ROOT}/u-boot"
ROOTFS_DIR="${BUILD_ROOT}/rootfs"
INITRAMFS_DIR="${BUILD_ROOT}/initramfs"
OUTPUT_DIR="${BUILD_ROOT}/output"

# Versions
LINUX_VERSION="6.6"  # LTS kernel
RT_PATCH_VERSION="6.6-rt"
UBOOT_VERSION="2024.01"

# Architecture
ARCH=arm64
CROSS_COMPILE=aarch64-linux-gnu-

# Raspberry Pi 5 specific
RPI5_DTB="bcm2712-rpi-5-b.dtb"
KERNEL_IMAGE="kernel_2712.img"

# SD Card device (BE CAREFUL!)
SD_CARD="/dev/mmcblk0"  # Change this to match your SD card

# Core count for parallel builds
CORES=$(nproc)

echo -e "${GREEN}Configuration:${NC}"
echo "  Build Root: ${BUILD_ROOT}"
echo "  Architecture: ${ARCH}"
echo "  Kernel Version: ${LINUX_VERSION} (RT-patched)"
echo "  CPU Cores: ${CORES}"
echo ""

# ============================================================================
# STEP 1: PREPARE BUILD ENVIRONMENT
# ============================================================================

prepare_environment() {
    echo -e "${YELLOW}[1/10] Preparing build environment...${NC}"
    
    # Install dependencies
    sudo apt update
    sudo apt install -y \
        git bc bison flex libssl-dev make libc6-dev libncurses5-dev \
        crossbuild-essential-arm64 gcc-aarch64-linux-gnu \
        device-tree-compiler u-boot-tools \
        qemu-user-static debootstrap \
        parted dosfstools e2fsprogs \
        cpio squashfs-tools \
        python3 python3-pip \
        kmod cpio
    
    # Create build directories
    mkdir -p "${BUILD_ROOT}"
    mkdir -p "${OUTPUT_DIR}"
    
    cd "${BUILD_ROOT}"
    
    echo -e "${GREEN}✓ Build environment ready${NC}\n"
}

# ============================================================================
# STEP 2: DOWNLOAD KERNEL SOURCES
# ============================================================================

download_kernel() {
    echo -e "${YELLOW}[2/10] Downloading Linux kernel sources...${NC}"
    
    if [ -d "${KERNEL_DIR}" ]; then
        echo "Kernel directory exists, updating..."
        cd "${KERNEL_DIR}"
        git pull
    else
        # Clone Raspberry Pi kernel (already has Pi 5 support)
        git clone --depth=1 --branch rpi-6.6.y \
            https://github.com/raspberrypi/linux.git "${KERNEL_DIR}"
    fi
    
    cd "${KERNEL_DIR}"
    
    echo -e "${GREEN}✓ Kernel sources downloaded${NC}\n"
}

# ============================================================================
# STEP 3: APPLY RT-PREEMPT PATCHES
# ============================================================================

apply_rt_patches() {
    echo -e "${YELLOW}[3/10] Applying PREEMPT_RT patches...${NC}"
    
    cd "${KERNEL_DIR}"
    
    # Get kernel version
    KERNEL_VER=$(make kernelversion)
    echo "Kernel version: ${KERNEL_VER}"
    
    # Download RT patch
    RT_PATCH_URL="https://cdn.kernel.org/pub/linux/kernel/projects/rt/6.6/patch-${KERNEL_VER}-rt45.patch.xz"
    
    if [ ! -f "patch-${KERNEL_VER}-rt45.patch" ]; then
        echo "Downloading RT patch..."
        wget -q "${RT_PATCH_URL}" -O patch-rt.patch.xz || {
            echo -e "${YELLOW}⚠ RT patch not available for this exact version${NC}"
            echo "Continuing with standard PREEMPT kernel..."
            return 0
        }
        xz -d patch-rt.patch.xz
    fi
    
    # Apply patch
    if [ -f "patch-rt.patch" ]; then
        echo "Applying RT patch..."
        patch -p1 < patch-rt.patch || {
            echo -e "${YELLOW}⚠ Patch failed, using standard PREEMPT${NC}"
        }
    fi
    
    echo -e "${GREEN}✓ RT patches applied${NC}\n"
}

# ============================================================================
# STEP 4: CONFIGURE KERNEL
# ============================================================================

configure_kernel() {
    echo -e "${YELLOW}[4/10] Configuring kernel...${NC}"
    
    cd "${KERNEL_DIR}"
    
    # Start with Pi 5 default config
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} bcm2712_defconfig
    
    # Enable RT features
    cat >> .config << EOF

# Real-Time Preemption
CONFIG_PREEMPT_RT=y
CONFIG_PREEMPT=y
CONFIG_HIGH_RES_TIMERS=y
CONFIG_NO_HZ_FULL=y
CONFIG_RCU_NOCB_CPU=y

# Automotive features
CONFIG_CAN=m
CONFIG_CAN_RAW=m
CONFIG_CAN_BCM=m
CONFIG_CAN_GW=m
CONFIG_CAN_VCAN=m

# V2X networking
CONFIG_IEEE802154=m
CONFIG_IEEE802154_SOCKET=m
CONFIG_MAC802154=m

# Embedded optimizations
CONFIG_EMBEDDED=y
CONFIG_EXPERT=y
CONFIG_SLOB=y
CONFIG_CC_OPTIMIZE_FOR_SIZE=y

# Security
CONFIG_SECURITY=y
CONFIG_SECURITY_NETWORK=y
CONFIG_SECCOMP=y

# Remove unnecessary drivers
# CONFIG_DRM is not set
# CONFIG_SOUND is not set
# CONFIG_USB_PRINTER is not set

# Keep essential drivers
CONFIG_USB_SERIAL=y
CONFIG_USB_SERIAL_FTDI_SIO=y
CONFIG_USB_SERIAL_PL2303=y
CONFIG_I2C=y
CONFIG_SPI=y
CONFIG_SERIAL_DEV_BUS=y

# Raspberry Pi specific
CONFIG_BCM2835_MBOX=y
CONFIG_RASPBERRYPI_FIRMWARE=y
CONFIG_RASPBERRYPI_POWER=y

# SDV Requirements
CONFIG_VIDEO_V4L2=y
CONFIG_USB_VIDEO_CLASS=y
CONFIG_MEDIA_CAMERA_SUPPORT=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_AMBA_PL011=y
CONFIG_GPIO_SYSFS=y
CONFIG_I2C_BCM2835=y
CONFIG_SPI_BCM2835=y
CONFIG_SPI_BCM2835AUX=y
CONFIG_PWM=y
CONFIG_PWM_BCM2835=y

# Networking
CONFIG_PACKET=y
CONFIG_UNIX=y
CONFIG_INET=y
CONFIG_WIRELESS=y
CONFIG_CFG80211=y
CONFIG_MAC80211=y
CONFIG_NETFILTER=y

# Filesystem
CONFIG_EXT4_FS=y
CONFIG_SQUASHFS=y
CONFIG_OVERLAY_FS=y
CONFIG_TMPFS=y
CONFIG_CONFIGFS_FS=y
EOF
    
    # Validate config
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} olddefconfig
    
    echo -e "${GREEN}✓ Kernel configured${NC}\n"
}

# ============================================================================
# STEP 5: BUILD KERNEL
# ============================================================================

build_kernel() {
    echo -e "${YELLOW}[5/10] Building kernel (this will take time)...${NC}"
    
    cd "${KERNEL_DIR}"
    
    # Build kernel image
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} -j${CORES} Image.gz
    
    # Build device tree blobs
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} -j${CORES} dtbs
    
    # Build modules
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} -j${CORES} modules
    
    echo -e "${GREEN}✓ Kernel built successfully${NC}\n"
}

# ============================================================================
# STEP 6: BUILD U-BOOT
# ============================================================================

build_uboot() {
    echo -e "${YELLOW}[6/10] Building U-Boot bootloader...${NC}"
    
    if [ -d "${UBOOT_DIR}" ]; then
        echo "U-Boot directory exists, updating..."
        cd "${UBOOT_DIR}"
        git pull
    else
        git clone --depth=1 --branch v2024.01 \
            https://github.com/u-boot/u-boot.git "${UBOOT_DIR}"
    fi
    
    cd "${UBOOT_DIR}"
    
    # Configure for Raspberry Pi 5
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} rpi_arm64_defconfig
    
    # Build U-Boot
    make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} -j${CORES}
    
    echo -e "${GREEN}✓ U-Boot built${NC}\n"
}

# ============================================================================
# STEP 7: CREATE MINIMAL ROOTFS WITH DEBOOTSTRAP
# ============================================================================

create_rootfs() {
    echo -e "${YELLOW}[7/10] Creating minimal rootfs...${NC}"
    
    sudo rm -rf "${ROOTFS_DIR}"
    mkdir -p "${ROOTFS_DIR}"
    
    # Create base Debian arm64 rootfs
    sudo debootstrap --arch=arm64 --variant=minbase \
        bookworm "${ROOTFS_DIR}" http://deb.debian.org/debian
    
    # Install essential packages
    sudo chroot "${ROOTFS_DIR}" /bin/bash << 'CHROOT_SCRIPT'
set -e

# Update package list
apt update

# Install minimal required packages
apt install -y --no-install-recommends \
    systemd systemd-sysv udev kmod \
    bash coreutils util-linux \
    ifupdown iproute2 iputils-ping \
    ca-certificates \
    python3-minimal python3-pip \
    openssh-server \
    nano less

# Clean up
apt clean
rm -rf /var/lib/apt/lists/*

# Set root password
echo "root:sdv2024" | chpasswd

# Enable SSH
systemctl enable ssh

# Create SDV user
useradd -m -s /bin/bash -G sudo pi
echo "pi:sdv2024" | chpasswd

CHROOT_SCRIPT
    
    # Copy SDV software
    echo "Installing SDV software..."
    
    sudo mkdir -p "${ROOTFS_DIR}/opt/sdv"
    sudo cp -r ../raspberry_pi/* "${ROOTFS_DIR}/opt/sdv/" 2>/dev/null || true
    
    # Create fstab for read-only root
    sudo tee "${ROOTFS_DIR}/etc/fstab" > /dev/null << EOF
# SDV Embedded Linux - Read-only root filesystem
proc            /proc           proc    defaults          0       0
devpts          /dev/pts        devpts  rw,gid=5,mode=620 0       0
tmpfs           /run            tmpfs   defaults,noatime  0       0
tmpfs           /tmp            tmpfs   defaults,noatime  0       0
tmpfs           /var/log        tmpfs   defaults,noatime  0       0
tmpfs           /var/tmp        tmpfs   defaults,noatime  0       0

# Boot partition
/dev/mmcblk0p1  /boot/firmware  vfat    ro,defaults       0       2

# Root partition (read-only by default)
/dev/mmcblk0p2  /               ext4    ro,defaults       0       1

# Writable data partition
/dev/mmcblk0p3  /data           ext4    rw,defaults       0       2
EOF
    
    # Configure network
    sudo tee "${ROOTFS_DIR}/etc/network/interfaces" > /dev/null << EOF
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF
    
    echo -e "${GREEN}✓ Rootfs created${NC}\n"
}

# ============================================================================
# STEP 8: CREATE INITRAMFS
# ============================================================================

create_initramfs() {
    echo -e "${YELLOW}[8/10] Creating initramfs...${NC}"
    
    mkdir -p "${INITRAMFS_DIR}"/{bin,sbin,etc,proc,sys,dev,newroot,run}
    
    # Copy busybox
    sudo cp /bin/busybox "${INITRAMFS_DIR}/bin/"
    
    # Create symlinks for busybox applets
    cd "${INITRAMFS_DIR}/bin"
    sudo ./busybox --install -s .
    cd -
    
    # Create init script
    sudo tee "${INITRAMFS_DIR}/init" > /dev/null << 'INIT_SCRIPT'
#!/bin/busybox sh

# Mount essential filesystems
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

# Wait for root device
echo "Waiting for root device..."
for i in $(seq 1 10); do
    if [ -e /dev/mmcblk0p2 ]; then
        break
    fi
    sleep 1
done

# Check root filesystem
echo "Checking root filesystem..."
/bin/fsck -y /dev/mmcblk0p2 || true

# Mount root filesystem (read-only)
echo "Mounting root filesystem..."
mount -o ro /dev/mmcblk0p2 /newroot

# Switch to new root
echo "Switching to real root..."
exec switch_root /newroot /sbin/init
INIT_SCRIPT
    
    sudo chmod +x "${INITRAMFS_DIR}/init"
    
    # Create initramfs image
    cd "${INITRAMFS_DIR}"
    sudo find . | sudo cpio -o -H newc | gzip > "${OUTPUT_DIR}/initramfs.gz"
    cd -
    
    echo -e "${GREEN}✓ Initramfs created${NC}\n"
}

# ============================================================================
# STEP 9: INSTALL TO OUTPUT DIRECTORY
# ============================================================================

install_output() {
    echo -e "${YELLOW}[9/10] Installing to output directory...${NC}"
    
    mkdir -p "${OUTPUT_DIR}/boot"
    mkdir -p "${OUTPUT_DIR}/rootfs"
    
    # Copy kernel
    cp "${KERNEL_DIR}/arch/arm64/boot/Image.gz" "${OUTPUT_DIR}/boot/${KERNEL_IMAGE}"
    
    # Copy device trees
    cp "${KERNEL_DIR}/arch/arm64/boot/dts/broadcom/${RPI5_DTB}" "${OUTPUT_DIR}/boot/"
    cp -r "${KERNEL_DIR}/arch/arm64/boot/dts/broadcom/overlays" "${OUTPUT_DIR}/boot/"
    
    # Install kernel modules to rootfs
    cd "${KERNEL_DIR}"
    sudo make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} \
        INSTALL_MOD_PATH="${ROOTFS_DIR}" modules_install
    
    # Copy U-Boot
    cp "${UBOOT_DIR}/u-boot.bin" "${OUTPUT_DIR}/boot/"
    
    # Create boot config
    tee "${OUTPUT_DIR}/boot/config.txt" > /dev/null << EOF
# SDV Embedded Linux - Raspberry Pi 5 Configuration

[pi5]
kernel=u-boot.bin

[all]
arm_64bit=1
enable_uart=1
uart_2ndstage=1

# GPU memory (minimal for headless)
gpu_mem=64

# Disable camera LED
disable_camera_led=1

# Enable I2C, SPI, UART
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1

# Performance
arm_freq=2400
over_voltage=2
EOF
    
    # Create U-Boot boot script
    tee "${OUTPUT_DIR}/boot/boot.cmd" > /dev/null << EOF
# U-Boot boot script for SDV

setenv bootargs "console=serial0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 rootwait ro quiet"
load mmc 0:1 \${kernel_addr_r} ${KERNEL_IMAGE}
load mmc 0:1 \${fdt_addr_r} ${RPI5_DTB}
load mmc 0:1 \${ramdisk_addr_r} initramfs.gz
booti \${kernel_addr_r} \${ramdisk_addr_r} \${fdt_addr_r}
EOF
    
    # Compile boot script
    mkimage -C none -A arm64 -T script -d "${OUTPUT_DIR}/boot/boot.cmd" \
        "${OUTPUT_DIR}/boot/boot.scr"
    
    echo -e "${GREEN}✓ Output directory prepared${NC}\n"
}

# ============================================================================
# STEP 10: CREATE SD CARD IMAGE
# ============================================================================

create_sd_image() {
    echo -e "${YELLOW}[10/10] Creating SD card image...${NC}"
    
    IMAGE_FILE="${OUTPUT_DIR}/sdv_embedded_pi5.img"
    IMAGE_SIZE="4G"
    
    # Create empty image
    dd if=/dev/zero of="${IMAGE_FILE}" bs=1 count=0 seek="${IMAGE_SIZE}" status=progress
    
    # Create partition table
    parted -s "${IMAGE_FILE}" mklabel msdos
    parted -s "${IMAGE_FILE}" mkpart primary fat32 1MiB 512MiB
    parted -s "${IMAGE_FILE}" mkpart primary ext4 512MiB 3584MiB
    parted -s "${IMAGE_FILE}" mkpart primary ext4 3584MiB 100%
    parted -s "${IMAGE_FILE}" set 1 boot on
    
    # Setup loop device
    LOOP_DEV=$(sudo losetup -f --show -P "${IMAGE_FILE}")
    
    # Format partitions
    sudo mkfs.vfat -F 32 -n BOOT "${LOOP_DEV}p1"
    sudo mkfs.ext4 -L rootfs "${LOOP_DEV}p2"
    sudo mkfs.ext4 -L data "${LOOP_DEV}p3"
    
    # Mount and copy files
    MOUNT_BOOT="/tmp/sdv_boot"
    MOUNT_ROOT="/tmp/sdv_root"
    
    mkdir -p "${MOUNT_BOOT}" "${MOUNT_ROOT}"
    
    sudo mount "${LOOP_DEV}p1" "${MOUNT_BOOT}"
    sudo mount "${LOOP_DEV}p2" "${MOUNT_ROOT}"
    
    # Copy boot files
    sudo cp -r "${OUTPUT_DIR}/boot/"* "${MOUNT_BOOT}/"
    
    # Copy rootfs
    sudo cp -a "${ROOTFS_DIR}/"* "${MOUNT_ROOT}/"
    
    # Sync and unmount
    sync
    sudo umount "${MOUNT_BOOT}"
    sudo umount "${MOUNT_ROOT}"
    sudo losetup -d "${LOOP_DEV}"
    
    # Compress image
    echo "Compressing image..."
    xz -9 -T0 "${IMAGE_FILE}"
    
    echo -e "${GREEN}✓ SD card image created: ${IMAGE_FILE}.xz${NC}\n"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo -e "${BLUE}Starting embedded Linux build...${NC}\n"
    
    prepare_environment
    download_kernel
    apply_rt_patches
    configure_kernel
    build_kernel
    build_uboot
    create_rootfs
    create_initramfs
    install_output
    create_sd_image
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}║   ✓ Embedded Linux Build Complete!                    ║${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Output files:${NC}"
    echo "  Image: ${OUTPUT_DIR}/sdv_embedded_pi5.img.xz"
    echo "  Boot: ${OUTPUT_DIR}/boot/"
    echo "  Rootfs: ${ROOTFS_DIR}/"
    echo ""
    echo -e "${BLUE}To flash to SD card:${NC}"
    echo "  xz -d ${OUTPUT_DIR}/sdv_embedded_pi5.img.xz"
    echo "  sudo dd if=${OUTPUT_DIR}/sdv_embedded_pi5.img of=${SD_CARD} bs=4M status=progress"
    echo "  sync"
    echo ""
    echo -e "${BLUE}Login credentials:${NC}"
    echo "  Username: pi"
    echo "  Password: sdv2024"
    echo ""
    echo -e "${YELLOW}Features included:${NC}"
    echo "  ✓ Custom Linux kernel ${LINUX_VERSION}"
    echo "  ✓ PREEMPT_RT real-time patches"
    echo "  ✓ U-Boot bootloader"
    echo "  ✓ Custom initramfs"
    echo "  ✓ Read-only root filesystem"
    echo "  ✓ Minimal Debian rootfs"
    echo "  ✓ SDV software integrated"
    echo ""
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi