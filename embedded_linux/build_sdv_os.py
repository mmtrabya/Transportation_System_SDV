#!/usr/bin/env python3
"""
SDV Custom OS Image Builder for Raspberry Pi 5
Creates a bootable image with:
- Vehicle registration on first boot
- Firebase integration
- Multi-screen infotainment system
- Real-time trip tracking
- Media integration (Spotify/Anghami)
- ADAS camera feed
- Climate control
- Speedometer from MPU9250

Usage:
    sudo python3 build_sdv_os.py --output sdv_pi5_v1.img
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SDVOSBuilder:
    """Builds custom SDV OS image for Raspberry Pi 5"""
    
    def __init__(self, output_image="sdv_pi5.img", size_gb=16):
        self.output_image = output_image
        self.size_gb = size_gb
        self.workspace = Path("./sdv_build")
        self.mount_point = self.workspace / "mount"
        
        # Base Raspberry Pi OS
        self.base_image_url = "https://downloads.raspberrypi.org/raspios_lite_arm64/images/"
        
    def check_dependencies(self):
        """Check required tools"""
        logger.info("Checking dependencies...")
        
        required = ['debootstrap', 'parted', 'kpartx', 'qemu-user-static']
        missing = []
        
        for tool in required:
            if shutil.which(tool) is None:
                missing.append(tool)
        
        if missing:
            logger.error(f"Missing tools: {', '.join(missing)}")
            logger.info("Install with: sudo apt install " + ' '.join(missing))
            return False
        
        logger.info("✓ All dependencies found")
        return True
    
    def create_workspace(self):
        """Create build workspace"""
        logger.info("Creating workspace...")
        
        self.workspace.mkdir(exist_ok=True)
        self.mount_point.mkdir(exist_ok=True)
        
        logger.info(f"✓ Workspace: {self.workspace}")
    
    def download_base_image(self):
        """Download Raspberry Pi OS Lite"""
        logger.info("Downloading Raspberry Pi OS Lite (64-bit)...")
        
        # For now, using existing image or download manually
        logger.warning("Please download Raspberry Pi OS Lite 64-bit manually")
        logger.warning("Place it in: ./sdv_build/base.img")
        
        base_image = self.workspace / "base.img"
        if not base_image.exists():
            logger.error("Base image not found!")
            return False
        
        logger.info("✓ Base image ready")
        return True
    
    def create_custom_image(self):
        """Create custom image from base"""
        logger.info(f"Creating {self.size_gb}GB image...")
        
        output = self.workspace / self.output_image
        
        # Create empty image
        subprocess.run([
            'dd', 'if=/dev/zero', f'of={output}',
            f'bs=1G', f'count={self.size_gb}', 'status=progress'
        ], check=True)
        
        # Create partitions
        subprocess.run([
            'parted', '-s', str(output),
            'mklabel', 'msdos',
            'mkpart', 'primary', 'fat32', '1MiB', '512MiB',
            'mkpart', 'primary', 'ext4', '512MiB', '100%',
            'set', '1', 'boot', 'on'
        ], check=True)
        
        logger.info("✓ Image created with partitions")
    
    def mount_image(self):
        """Mount image for modifications"""
        logger.info("Mounting image...")
        
        output = self.workspace / self.output_image
        
        # Setup loop device
        result = subprocess.run(
            ['sudo', 'kpartx', '-av', str(output)],
            capture_output=True, text=True
        )
        
        # Extract loop device name
        loop_dev = result.stdout.split()[2]  # e.g., loop0p1
        
        # Mount partitions
        boot_mount = self.mount_point / "boot"
        root_mount = self.mount_point / "root"
        
        boot_mount.mkdir(exist_ok=True, parents=True)
        root_mount.mkdir(exist_ok=True, parents=True)
        
        subprocess.run(['sudo', 'mount', f'/dev/mapper/{loop_dev}', str(boot_mount)])
        subprocess.run(['sudo', 'mount', f'/dev/mapper/{loop_dev.replace("p1", "p2")}', str(root_mount)])
        
        logger.info("✓ Image mounted")
        return loop_dev
    
    def install_sdv_software(self):
        """Install SDV software stack"""
        logger.info("Installing SDV software...")
        
        root = self.mount_point / "root"
        
        # Create directory structure
        sdv_dirs = [
            'opt/sdv',
            'opt/sdv/bin',
            'opt/sdv/config',
            'opt/sdv/models',
            'opt/sdv/logs',
            'opt/sdv/media',
            'home/pi/sdv'
        ]
        
        for d in sdv_dirs:
            (root / d).mkdir(parents=True, exist_ok=True)
        
        # Copy SDV Python modules
        self._install_python_modules(root)
        
        # Install systemd services
        self._install_systemd_services(root)
        
        # Install GUI application
        self._install_gui_app(root)
        
        logger.info("✓ SDV software installed")
    
    def _install_python_modules(self, root):
        """Install Python modules"""
        logger.info("  Installing Python modules...")
        
        modules = [
            'atmega32_interface.py',
            'gps_interface.py',
            'adas_inference.py',
            'driver_inference.py',
            'v2x_interface.py',
            'iot_publish.py',
            'automotive_cybersecurity.py',
            'fota_sota_manager.py'
        ]
        
        for module in modules:
            src = Path('../raspberry_pi') / module
            if src.exists():
                dst = root / 'opt/sdv/bin' / module
                subprocess.run(['sudo', 'cp', str(src), str(dst)])
    
    def _install_systemd_services(self, root):
        """Install systemd service files"""
        logger.info("  Installing systemd services...")
        
        services_dir = root / 'etc/systemd/system'
        services_dir.mkdir(parents=True, exist_ok=True)
        
        # Create service files
        services = {
            'sdv-firstboot.service': self._generate_firstboot_service(),
            'sdv-infotainment.service': self._generate_infotainment_service(),
            'sdv-vehicle-manager.service': self._generate_vehicle_manager_service(),
            'sdv-adas.service': self._generate_adas_service(),
        }
        
        for name, content in services.items():
            service_file = services_dir / name
            with open(service_file, 'w') as f:
                f.write(content)
    
    def _install_gui_app(self, root):
        """Install GUI infotainment application"""
        logger.info("  Installing GUI application...")
        
        gui_dir = root / 'opt/sdv/gui'
        gui_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy GUI files
        gui_files = [
            'main.py',
            'dashboard.py',
            'unlock_screen.py',
            'trip_tracker.py',
            'config.py'
        ]
        
        for file in gui_files:
            src = Path('../embedded_linux') / file
            if src.exists():
                subprocess.run(['sudo', 'cp', str(src), str(gui_dir)])
    
    def _generate_firstboot_service(self):
        """Generate first boot registration service"""
        return """[Unit]
Description=SDV First Boot Registration
Before=multi-user.target
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/sdv/bin/firstboot_registration.py
RemainAfterExit=yes
StandardOutput=journal

[Install]
WantedBy=multi-user.target
"""
    
    def _generate_infotainment_service(self):
        """Generate infotainment service"""
        return """[Unit]
Description=SDV Infotainment System
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=/usr/bin/python3 /opt/sdv/gui/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
"""
    
    def _generate_vehicle_manager_service(self):
        """Generate vehicle manager service"""
        return """[Unit]
Description=SDV Vehicle Manager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sdv/bin
ExecStart=/usr/bin/python3 /opt/sdv/bin/vehicle_manager_firebase.py
Restart=always
RestartSec=10
StandardOutput=journal

[Install]
WantedBy=multi-user.target
"""
    
    def _generate_adas_service(self):
        """Generate ADAS service"""
        return """[Unit]
Description=SDV ADAS System
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/sdv/bin
ExecStart=/usr/bin/python3 /opt/sdv/bin/adas_inference.py --headless
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    def configure_autostart(self):
        """Configure services to start on boot"""
        logger.info("Configuring autostart...")
        
        root = self.mount_point / "root"
        
        # Enable services
        services = [
            'sdv-firstboot.service',
            'sdv-infotainment.service',
            'sdv-vehicle-manager.service',
            'sdv-adas.service'
        ]
        
        for service in services:
            link = root / f'etc/systemd/system/multi-user.target.wants/{service}'
            target = f'../../../system/{service}'
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.exists():
                link.symlink_to(target)
        
        logger.info("✓ Services configured")
    
    def install_dependencies(self):
        """Install system dependencies"""
        logger.info("Installing system dependencies...")
        
        root = self.mount_point / "root"
        
        # Create package list
        packages = [
            'python3-pip',
            'python3-pyqt5',
            'python3-opencv',
            'python3-serial',
            'python3-firebase-admin',
            'python3-numpy',
            'libfreenect-dev',
            'freenect',
            'python3-freenect',
            'v4l-utils',
            'ffmpeg',
            'mosquitto',
            'mosquitto-clients'
        ]
        
        # Write to firstboot script to install
        firstboot_script = root / 'opt/sdv/bin/install_deps.sh'
        with open(firstboot_script, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('apt update\n')
            f.write(f'apt install -y {" ".join(packages)}\n')
            f.write('pip3 install onnxruntime paho-mqtt streamlit plotly\n')
        
        subprocess.run(['sudo', 'chmod', '+x', str(firstboot_script)])
        
        logger.info("✓ Dependency installation configured")
    
    def unmount_image(self, loop_dev):
        """Unmount image"""
        logger.info("Unmounting image...")
        
        subprocess.run(['sudo', 'umount', str(self.mount_point / "boot")])
        subprocess.run(['sudo', 'umount', str(self.mount_point / "root")])
        subprocess.run(['sudo', 'kpartx', '-d', str(self.workspace / self.output_image)])
        
        logger.info("✓ Image unmounted")
    
    def compress_image(self):
        """Compress final image"""
        logger.info("Compressing image...")
        
        output = self.workspace / self.output_image
        
        subprocess.run([
            'xz', '-9', '-T0', str(output)
        ])
        
        logger.info(f"✓ Image compressed: {output}.xz")
    
    def build(self):
        """Main build process"""
        logger.info("=" * 60)
        logger.info("Starting SDV OS Image Build")
        logger.info("=" * 60)
        
        try:
            if not self.check_dependencies():
                return False
            
            self.create_workspace()
            
            if not self.download_base_image():
                logger.warning("Using existing base image or manual download required")
            
            self.create_custom_image()
            loop_dev = self.mount_image()
            
            self.install_sdv_software()
            self.install_dependencies()
            self.configure_autostart()
            
            self.unmount_image(loop_dev)
            self.compress_image()
            
            logger.info("=" * 60)
            logger.info("✓ SDV OS Image Build Complete!")
            logger.info(f"  Output: {self.workspace / self.output_image}.xz")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Build SDV custom OS image')
    parser.add_argument('--output', default='sdv_pi5_v1.img', help='Output image name')
    parser.add_argument('--size', type=int, default=16, help='Image size in GB')
    
    args = parser.parse_args()
    
    if os.geteuid() != 0:
        logger.error("This script must be run as root (use sudo)")
        sys.exit(1)
    
    builder = SDVOSBuilder(args.output, args.size)
    
    if builder.build():
        print("\n✓ Build successful!")
        print(f"\nTo flash to SD card:")
        print(f"  xz -d {builder.workspace / args.output}.xz")
        print(f"  sudo dd if={builder.workspace / args.output} of=/dev/sdX bs=4M status=progress")
        sys.exit(0)
    else:
        print("\n✗ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()