#!/usr/bin/env python3
"""
FOTA/SOTA Update Manager
Handles Over-The-Air updates for firmware (ESP32/ATmega32) and software (Pi apps/models)
With signature verification, rollback support, and secure delivery
"""

import os
import json
import hashlib
import requests
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('FOTA_SOTA_Manager')

# ==================== CONFIGURATION ====================

class UpdateConfig:
    """Update manager configuration"""
    
    # Server configuration
    UPDATE_SERVER = "https://your-update-server.com"
    API_ENDPOINT = f"{UPDATE_SERVER}/api/v1"
    
    # Local paths
    BASE_DIR = Path("/opt/sdv")
    UPDATES_DIR = BASE_DIR / "updates"
    BACKUP_DIR = BASE_DIR / "backups"
    KEYS_DIR = BASE_DIR / "keys"
    
    # Manifest and version files
    MANIFEST_FILE = BASE_DIR / "manifest.json"
    VERSION_FILE = BASE_DIR / "version.json"
    
    # FOTA targets
    ESP32_PORT = "/dev/ttyUSB0"
    ATMEGA32_PORT = "/dev/ttyACM0"
    
    # SOTA targets
    SOFTWARE_DIR = BASE_DIR / "software"
    MODELS_DIR = BASE_DIR / "models"
    
    # Update settings
    CHECK_INTERVAL = 3600  # Check every hour
    MAX_RETRIES = 3
    TIMEOUT = 300  # 5 minutes
    
    # Vehicle info
    VEHICLE_ID = "SDV_001"
    HARDWARE_VERSION = "1.0"

# ==================== CRYPTO UTILITIES ====================

class CryptoManager:
    """Handles cryptographic operations for update verification"""
    
    def __init__(self, keys_dir: Path):
        self.keys_dir = keys_dir
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        self.public_key_file = self.keys_dir / "public_key.pem"
        self.private_key_file = self.keys_dir / "private_key.pem"
        
        # Load or generate keys
        if not self.public_key_file.exists():
            logger.warning("Public key not found. Generate keys on server first!")
            self.public_key = None
        else:
            self.public_key = self._load_public_key()
    
    def _load_public_key(self):
        """Load public key from file"""
        try:
            with open(self.public_key_file, 'rb') as f:
                return serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            return None
    
    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify digital signature"""
        if not self.public_key:
            logger.error("No public key available for verification")
            return False
        
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    @staticmethod
    def calculate_hash(file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate file hash"""
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def generate_key_pair():
        """Generate RSA key pair (run on server)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        return private_key, public_key

# ==================== VERSION MANAGER ====================

class VersionManager:
    """Manages version tracking and manifest"""
    
    def __init__(self, version_file: Path, manifest_file: Path):
        self.version_file = version_file
        self.manifest_file = manifest_file
        
        self.current_version = self._load_version()
        self.manifest = self._load_manifest()
    
    def _load_version(self) -> Dict:
        """Load current version information"""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                return json.load(f)
        
        # Default version
        return {
            'software_version': '1.0.0',
            'esp32_firmware': '1.0.0',
            'atmega32_firmware': '1.0.0',
            'adas_model': '1.0.0',
            'last_update': None
        }
    
    def _load_manifest(self) -> Dict:
        """Load update manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_version(self):
        """Save current version to file"""
        self.current_version['last_update'] = datetime.now().isoformat()
        with open(self.version_file, 'w') as f:
            json.dump(self.current_version, f, indent=2)
    
    def save_manifest(self):
        """Save manifest to file"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def update_component_version(self, component: str, version: str):
        """Update version for a specific component"""
        self.current_version[component] = version
        self.save_version()

# ==================== FOTA MANAGER ====================

class FOTAManager:
    """Firmware Over-The-Air update manager"""
    
    def __init__(self, config: UpdateConfig, crypto: CryptoManager):
        self.config = config
        self.crypto = crypto
    
    def flash_esp32(self, firmware_file: Path) -> bool:
        """Flash ESP32 firmware using esptool"""
        try:
            logger.info(f"Flashing ESP32 firmware: {firmware_file}")
            
            # Verify file exists
            if not firmware_file.exists():
                logger.error("Firmware file not found")
                return False
            
            # Flash using esptool
            cmd = [
                'esptool.py',
                '--port', self.config.ESP32_PORT,
                '--baud', '460800',
                'write_flash',
                '0x1000', str(firmware_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("ESP32 flashed successfully")
                return True
            else:
                logger.error(f"ESP32 flash failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error flashing ESP32: {e}")
            return False
    
    def flash_atmega32(self, firmware_file: Path) -> bool:
        """Flash ATmega32 firmware using avrdude"""
        try:
            logger.info(f"Flashing ATmega32 firmware: {firmware_file}")
            
            if not firmware_file.exists():
                logger.error("Firmware file not found")
                return False
            
            # Flash using avrdude
            cmd = [
                'avrdude',
                '-p', 'atmega32',
                '-c', 'arduino',
                '-P', self.config.ATMEGA32_PORT,
                '-b', '115200',
                '-U', f'flash:w:{firmware_file}:i'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("ATmega32 flashed successfully")
                return True
            else:
                logger.error(f"ATmega32 flash failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error flashing ATmega32: {e}")
            return False
    
    def verify_firmware(self, firmware_file: Path, expected_hash: str) -> bool:
        """Verify firmware integrity"""
        actual_hash = self.crypto.calculate_hash(firmware_file)
        
        if actual_hash == expected_hash:
            logger.info("Firmware hash verified")
            return True
        else:
            logger.error(f"Hash mismatch! Expected: {expected_hash}, Got: {actual_hash}")
            return False

# ==================== SOTA MANAGER ====================

class SOTAManager:
    """Software Over-The-Air update manager"""
    
    def __init__(self, config: UpdateConfig, crypto: CryptoManager):
        self.config = config
        self.crypto = crypto
    
    def update_software(self, package_file: Path, install_script: Path = None) -> bool:
        """Update software package"""
        try:
            logger.info(f"Installing software update: {package_file}")
            
            # Extract package
            extract_dir = self.config.UPDATES_DIR / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            if package_file.suffix == '.tar.gz':
                subprocess.run(['tar', '-xzf', str(package_file), '-C', str(extract_dir)])
            elif package_file.suffix == '.zip':
                subprocess.run(['unzip', '-o', str(package_file), '-d', str(extract_dir)])
            else:
                logger.error("Unsupported package format")
                return False
            
            # Run install script if provided
            if install_script and install_script.exists():
                logger.info("Running install script")
                result = subprocess.run(
                    ['bash', str(install_script)],
                    cwd=extract_dir,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    logger.error(f"Install script failed: {result.stderr}")
                    return False
            else:
                # Copy files to software directory
                for item in extract_dir.iterdir():
                    dest = self.config.SOFTWARE_DIR / item.name
                    if item.is_file():
                        shutil.copy2(item, dest)
                    else:
                        shutil.copytree(item, dest, dirs_exist_ok=True)
            
            logger.info("Software update installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating software: {e}")
            return False
    
    def update_model(self, model_file: Path, model_name: str) -> bool:
        """Update ONNX model"""
        try:
            logger.info(f"Installing model update: {model_name}")
            
            dest = self.config.MODELS_DIR / model_name
            shutil.copy2(model_file, dest)
            
            logger.info(f"Model {model_name} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return False

# ==================== BACKUP MANAGER ====================

class BackupManager:
    """Manages backups for rollback support"""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, source: Path, component: str) -> Optional[Path]:
        """Create backup of component"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{component}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            if source.is_file():
                shutil.copy2(source, backup_path)
            else:
                shutil.copytree(source, backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_path: Path, destination: Path) -> bool:
        """Restore from backup"""
        try:
            if backup_path.is_file():
                shutil.copy2(backup_path, destination)
            else:
                shutil.copytree(backup_path, destination, dirs_exist_ok=True)
            
            logger.info(f"Restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """Keep only recent backups"""
        backups = sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime)
        
        if len(backups) > keep_count:
            for backup in backups[:-keep_count]:
                if backup.is_file():
                    backup.unlink()
                else:
                    shutil.rmtree(backup)
                logger.info(f"Removed old backup: {backup}")

# ==================== MAIN UPDATE MANAGER ====================

class UpdateManager:
    """Main update manager coordinating FOTA and SOTA"""
    
    def __init__(self, config: UpdateConfig = None):
        self.config = config or UpdateConfig()
        
        # Create directories
        self.config.UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        self.config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.config.SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
        self.config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.crypto = CryptoManager(self.config.KEYS_DIR)
        self.version = VersionManager(self.config.VERSION_FILE, self.config.MANIFEST_FILE)
        self.fota = FOTAManager(self.config, self.crypto)
        self.sota = SOTAManager(self.config, self.crypto)
        self.backup = BackupManager(self.config.BACKUP_DIR)
        
        logger.info("Update Manager initialized")
    
    def check_for_updates(self) -> Dict:
        """Check server for available updates"""
        try:
            url = f"{self.config.API_ENDPOINT}/updates/check"
            params = {
                'vehicle_id': self.config.VEHICLE_ID,
                'hardware_version': self.config.HARDWARE_VERSION,
                'current_versions': json.dumps(self.version.current_version)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            updates = response.json()
            logger.info(f"Updates available: {updates}")
            
            return updates
            
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return {}
    
    def download_update(self, update_info: Dict) -> Optional[Path]:
        """Download update file"""
        try:
            url = update_info['download_url']
            filename = update_info['filename']
            expected_hash = update_info['hash']
            
            download_path = self.config.UPDATES_DIR / filename
            
            logger.info(f"Downloading {filename}...")
            
            response = requests.get(url, stream=True, timeout=self.config.TIMEOUT)
            response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify hash
            actual_hash = self.crypto.calculate_hash(download_path)
            if actual_hash != expected_hash:
                logger.error("Hash verification failed")
                download_path.unlink()
                return None
            
            # Verify signature if provided
            if 'signature' in update_info:
                signature = bytes.fromhex(update_info['signature'])
                with open(download_path, 'rb') as f:
                    data = f.read()
                
                if not self.crypto.verify_signature(data, signature):
                    logger.error("Signature verification failed")
                    download_path.unlink()
                    return None
            
            logger.info(f"Downloaded and verified: {filename}")
            return download_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def apply_update(self, update_type: str, update_file: Path, component: str) -> bool:
        """Apply downloaded update"""
        try:
            # Create backup
            if update_type == 'software':
                backup_source = self.config.SOFTWARE_DIR
            elif update_type == 'model':
                backup_source = self.config.MODELS_DIR / component
            else:
                backup_source = None
            
            if backup_source and backup_source.exists():
                backup_path = self.backup.create_backup(backup_source, component)
                if not backup_path:
                    logger.warning("Backup creation failed, proceeding anyway")
            
            # Apply update based on type
            success = False
            
            if update_type == 'esp32_firmware':
                success = self.fota.flash_esp32(update_file)
            elif update_type == 'atmega32_firmware':
                success = self.fota.flash_atmega32(update_file)
            elif update_type == 'software':
                success = self.sota.update_software(update_file)
            elif update_type == 'model':
                success = self.sota.update_model(update_file, component)
            
            if success:
                logger.info(f"Update applied successfully: {component}")
                return True
            else:
                logger.error(f"Update failed: {component}")
                # Rollback if backup exists
                if backup_path and backup_source:
                    logger.info("Attempting rollback...")
                    self.backup.restore_backup(backup_path, backup_source)
                return False
                
        except Exception as e:
            logger.error(f"Error applying update: {e}")
            return False
    
    def run_update_cycle(self):
        """Run complete update check and apply cycle"""
        logger.info("Starting update cycle...")
        
        # Check for updates
        updates = self.check_for_updates()
        
        if not updates:
            logger.info("No updates available")
            return
        
        # Process each update
        for update_type, update_info in updates.items():
            logger.info(f"Processing {update_type} update...")
            
            # Download update
            update_file = self.download_update(update_info)
            if not update_file:
                continue
            
            # Apply update
            component = update_info.get('component', update_type)
            success = self.apply_update(update_type, update_file, component)
            
            if success:
                # Update version
                new_version = update_info.get('version')
                if new_version:
                    self.version.update_component_version(component, new_version)
            
            # Cleanup
            update_file.unlink()
        
        # Cleanup old backups
        self.backup.cleanup_old_backups(keep_count=3)
        
        logger.info("Update cycle completed")

# ==================== CLI ====================

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FOTA/SOTA Update Manager')
    parser.add_argument('--check', action='store_true', help='Check for updates')
    parser.add_argument('--apply', action='store_true', help='Apply available updates')
    parser.add_argument('--version', action='store_true', help='Show current versions')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    manager = UpdateManager()
    
    if args.version:
        print(json.dumps(manager.version.current_version, indent=2))
    
    elif args.check:
        updates = manager.check_for_updates()
        print(json.dumps(updates, indent=2))
    
    elif args.apply:
        manager.run_update_cycle()
    
    elif args.daemon:
        logger.info("Starting update daemon...")
        while True:
            try:
                manager.run_update_cycle()
            except Exception as e:
                logger.error(f"Error in update cycle: {e}")
            
            time.sleep(UpdateConfig.CHECK_INTERVAL)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()