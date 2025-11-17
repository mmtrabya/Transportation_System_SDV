#!/usr/bin/env python3
"""
Firebase-Based FOTA/SOTA Update Manager
Handles OTA updates using Firebase Cloud Storage and Firestore
"""

import os
import json
import hashlib
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging
import time
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import FieldFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Firebase_FOTA_SOTA')

# ==================== CONFIGURATION ====================

class FirebaseConfig:
    """Firebase configuration"""
    
    # Firebase credentials
    CREDENTIALS_FILE = Path.home() / "sdv_firebase_key.json"
    STORAGE_BUCKET = "sdv-ota-system.firebasestorage.app"
    
    # Device info
    VEHICLE_ID = "SDV_001"  # Match your ESP32 VEHICLE_ID
    HARDWARE_VERSION = "1.0"
    
    # Local paths
    BASE_DIR = Path.home() / "sdv"
    UPDATES_DIR = BASE_DIR / "updates"
    BACKUP_DIR = BASE_DIR / "backups"
    
    # Version file
    VERSION_FILE = BASE_DIR / "version.json"
    
    # FOTA targets
    ESP32_PORT = "/dev/ttyUSB0"
    ATMEGA32_PORT = "/dev/ttyACM0"
    
    # SOTA targets
    SOFTWARE_DIR = BASE_DIR / "software"
    MODELS_DIR = BASE_DIR / "models"
    
    # Update settings
    CHECK_INTERVAL = 60  # Check every minute for demo
    MAX_RETRIES = 3

# ==================== FIREBASE MANAGER ====================

class FirebaseManager:
    """Handles all Firebase operations"""
    
    def __init__(self, config: FirebaseConfig):
        self.config = config
        
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(config.CREDENTIALS_FILE))
            firebase_admin.initialize_app(cred, {
                'storageBucket': config.STORAGE_BUCKET
            })
        
        self.db = firestore.client()
        self.bucket = storage.bucket()
        
        logger.info("Firebase initialized successfully")
    
    def register_device(self, version_info: Dict):
        """Register device in Firestore"""
        try:
            device_ref = self.db.collection('vehicles').document(self.config.VEHICLE_ID)
            
            device_data = {
                'vehicle_id': self.config.VEHICLE_ID,
                'hardware_version': self.config.HARDWARE_VERSION,
                'current_versions': version_info,
                'status': 'online',
                'last_seen': firestore.SERVER_TIMESTAMP,
                'update_status': 'idle',
                'location': {
                    'latitude': 30.0444,
                    'longitude': 31.2357
                }
            }
            
            device_ref.set(device_data, merge=True)
            logger.info(f"Device {self.config.VEHICLE_ID} registered")
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
    
    def check_for_updates(self, current_versions: Dict) -> Dict:
        """Check Firestore for available updates"""
        try:
            updates_ref = self.db.collection('updates')
            
            available_updates = {}
            
            # Query each component
            for component, current_version in current_versions.items():
                if component in ['last_update', 'hardware_version']:
                    continue
                
                # Query for updates newer than current version
                query = updates_ref.where(
                    filter=FieldFilter('component', '==', component)
                ).where(
                    filter=FieldFilter('active', '==', True)
                ).order_by('version', direction=firestore.Query.DESCENDING).limit(1)
                
                docs = query.stream()
                
                for doc in docs:
                    update_info = doc.to_dict()
                    if self._compare_versions(update_info['version'], current_version) > 0:
                        available_updates[component] = update_info
                        logger.info(f"Update found for {component}: {current_version} -> {update_info['version']}")
            
            return available_updates
            
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return {}
    
    def download_update(self, update_info: Dict) -> Optional[Path]:
        """Download update from Cloud Storage"""
        try:
            filename = update_info['filename']
            storage_path = update_info['storage_path']
            
            download_path = self.config.UPDATES_DIR / filename
            download_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading {filename} from Firebase Storage...")
            
            # Download from Cloud Storage
            blob = self.bucket.blob(storage_path)
            blob.download_to_filename(str(download_path))
            
            # Verify hash
            actual_hash = self._calculate_hash(download_path)
            expected_hash = update_info['hash']
            
            if actual_hash != expected_hash:
                logger.error(f"Hash mismatch! Expected: {expected_hash}, Got: {actual_hash}")
                download_path.unlink()
                return None
            
            logger.info(f"Downloaded and verified: {filename}")
            return download_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def update_device_status(self, status: str, details: Dict = None):
        """Update device status in Firestore"""
        try:
            device_ref = self.db.collection('vehicles').document(self.config.VEHICLE_ID)
            
            update_data = {
                'update_status': status,
                'last_seen': firestore.SERVER_TIMESTAMP
            }
            
            if details:
                update_data['update_details'] = details
            
            device_ref.update(update_data)
            
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
    
    def log_update_event(self, event_type: str, component: str, details: Dict):
        """Log update event to Firestore"""
        try:
            log_ref = self.db.collection('update_logs').document()
            
            log_data = {
                'vehicle_id': self.config.VEHICLE_ID,
                'event_type': event_type,
                'component': component,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'details': details
            }
            
            log_ref.set(log_data)
            
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    @staticmethod
    def _calculate_hash(file_path: Path) -> str:
        """Calculate SHA256 hash"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare semantic versions"""
        try:
            parts1 = [int(x) for x in str(v1).split('.')]
            parts2 = [int(x) for x in str(v2).split('.')]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            return 0
        except:
            return 0

# ==================== VERSION MANAGER ====================

class VersionManager:
    """Manages local version tracking"""
    
    def __init__(self, version_file: Path):
        self.version_file = version_file
        self.current_version = self._load_version()
    
    def _load_version(self) -> Dict:
        """Load current version"""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                return json.load(f)
        
        return {
            'software_version': '1.0.0',
            'esp32_firmware': '1.0.0',
            'atmega32_firmware': '1.0.0',
            'adas_model': '1.0.0',
            'last_update': None
        }
    
    def save_version(self):
        """Save version to file"""
        self.current_version['last_update'] = datetime.now().isoformat()
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.version_file, 'w') as f:
            json.dump(self.current_version, f, indent=2)
    
    def update_component(self, component: str, version: str):
        """Update component version"""
        self.current_version[component] = version
        self.save_version()

# ==================== FOTA MANAGER ====================

class FOTAManager:
    """Firmware Over-The-Air updates"""
    
    def __init__(self, config: FirebaseConfig):
        self.config = config
    
    def flash_esp32(self, firmware_file: Path) -> bool:
        """Flash ESP32 firmware"""
        try:
            logger.info(f"Flashing ESP32: {firmware_file}")
            
            if not firmware_file.exists():
                logger.error("Firmware file not found")
                return False
            
            cmd = [
                'esptool.py',
                '--port', self.config.ESP32_PORT,
                '--baud', '460800',
                'write_flash',
                '0x1000', str(firmware_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("ESP32 flashed successfully")
                return True
            else:
                logger.error(f"Flash failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error flashing ESP32: {e}")
            return False
    
    def flash_atmega32(self, firmware_file: Path) -> bool:
        """Flash ATmega32 firmware"""
        try:
            logger.info(f"Flashing ATmega32: {firmware_file}")
            
            if not firmware_file.exists():
                return False
            
            cmd = [
                'avrdude',
                '-p', 'atmega32',
                '-c', 'arduino',
                '-P', self.config.ATMEGA32_PORT,
                '-b', '115200',
                '-U', f'flash:w:{firmware_file}:i'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error flashing ATmega32: {e}")
            return False

# ==================== SOTA MANAGER ====================

class SOTAManager:
    """Software Over-The-Air updates"""
    
    def __init__(self, config: FirebaseConfig):
        self.config = config
    
    def update_software(self, package_file: Path) -> bool:
        """Update software package"""
        try:
            logger.info(f"Installing software: {package_file}")
            
            extract_dir = self.config.UPDATES_DIR / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            if package_file.suffix == '.tar.gz':
                subprocess.run(['tar', '-xzf', str(package_file), '-C', str(extract_dir)])
            elif package_file.suffix == '.zip':
                subprocess.run(['unzip', '-o', str(package_file), '-d', str(extract_dir)])
            
            # Copy to software directory
            self.config.SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
            for item in extract_dir.iterdir():
                dest = self.config.SOFTWARE_DIR / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                else:
                    shutil.copytree(item, dest, dirs_exist_ok=True)
            
            logger.info("Software updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating software: {e}")
            return False
    
    def update_model(self, model_file: Path, model_name: str) -> bool:
        """Update ONNX model"""
        try:
            logger.info(f"Installing model: {model_name}")
            
            self.config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            dest = self.config.MODELS_DIR / model_name
            shutil.copy2(model_file, dest)
            
            logger.info(f"Model {model_name} updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return False

# ==================== BACKUP MANAGER ====================

class BackupManager:
    """Backup management for rollback"""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, source: Path, component: str) -> Optional[Path]:
        """Create backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{component}_{timestamp}"
            
            if source.exists():
                if source.is_file():
                    shutil.copy2(source, backup_path)
                else:
                    shutil.copytree(source, backup_path)
                
                logger.info(f"Backup created: {backup_path}")
                return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
        
        return None
    
    def restore_backup(self, backup_path: Path, destination: Path) -> bool:
        """Restore from backup"""
        try:
            if backup_path.is_file():
                shutil.copy2(backup_path, destination)
            else:
                shutil.copytree(backup_path, destination, dirs_exist_ok=True)
            
            logger.info(f"Restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

# ==================== MAIN UPDATE MANAGER ====================

class UpdateManager:
    """Main update orchestrator"""
    
    def __init__(self, config: FirebaseConfig = None):
        self.config = config or FirebaseConfig()
        
        # Create directories
        self.config.UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        self.config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.firebase = FirebaseManager(self.config)
        self.version = VersionManager(self.config.VERSION_FILE)
        self.fota = FOTAManager(self.config)
        self.sota = SOTAManager(self.config)
        self.backup = BackupManager(self.config.BACKUP_DIR)
        
        # Register device
        self.firebase.register_device(self.version.current_version)
        
        logger.info("Update Manager initialized")
    
    def run_update_cycle(self):
        """Check and apply updates"""
        logger.info("=== Starting Update Cycle ===")
        
        self.firebase.update_device_status('checking')
        
        # Check for updates
        updates = self.firebase.check_for_updates(self.version.current_version)
        
        if not updates:
            logger.info("No updates available")
            self.firebase.update_device_status('idle')
            return
        
        logger.info(f"Found {len(updates)} update(s)")
        
        # Process each update
        for component, update_info in updates.items():
            logger.info(f"Processing {component} update...")
            
            self.firebase.update_device_status('downloading', {
                'component': component,
                'version': update_info['version']
            })
            
            # Download
            update_file = self.firebase.download_update(update_info)
            if not update_file:
                logger.error(f"Download failed for {component}")
                continue
            
            # Create backup
            backup_path = None
            if update_info['update_type'] == 'software':
                backup_path = self.backup.create_backup(self.config.SOFTWARE_DIR, component)
            
            # Apply update
            self.firebase.update_device_status('installing', {
                'component': component,
                'version': update_info['version']
            })
            
            success = self._apply_update(update_info['update_type'], update_file, component)
            
            if success:
                logger.info(f"✓ Update successful: {component}")
                self.version.update_component(component, update_info['version'])
                
                self.firebase.log_update_event('success', component, {
                    'old_version': self.version.current_version.get(component),
                    'new_version': update_info['version']
                })
            else:
                logger.error(f"✗ Update failed: {component}")
                
                # Rollback
                if backup_path:
                    logger.info("Attempting rollback...")
                    self.backup.restore_backup(backup_path, self.config.SOFTWARE_DIR)
                
                self.firebase.log_update_event('failed', component, {
                    'error': 'Installation failed'
                })
            
            # Cleanup
            if update_file.exists():
                update_file.unlink()
        
        self.firebase.update_device_status('idle')
        self.firebase.register_device(self.version.current_version)
        
        logger.info("=== Update Cycle Complete ===")
    
    def _apply_update(self, update_type: str, update_file: Path, component: str) -> bool:
        """Apply update based on type"""
        try:
            if update_type == 'esp32_firmware':
                return self.fota.flash_esp32(update_file)
            elif update_type == 'atmega32_firmware':
                return self.fota.flash_atmega32(update_file)
            elif update_type == 'software':
                return self.sota.update_software(update_file)
            elif update_type == 'model':
                return self.sota.update_model(update_file, component)
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying update: {e}")
            return False

class OTAManager:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.db = firestore.client()
        
    def check_for_updates(self):
        """Check for available updates"""
        # Get current versions
        version_file = Path.home() / 'sdv' / 'version.json'
        with open(version_file, 'r') as f:
            current_versions = json.load(f)
        
        # Query Firestore for updates
        updates_ref = self.db.collection('updates').where('active', '==', True)
        
        for doc in updates_ref.stream():
            update = doc.to_dict()
            component = update['component']
            new_version = update['version']
            current_version = current_versions.get(component, '0.0.0')
            
            if self.compare_versions(new_version, current_version) > 0:
                print(f"Update available for {component}: {current_version} -> {new_version}")
                self.download_and_install(update)
# ==================== CLI ====================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Firebase FOTA/SOTA Manager')
    parser.add_argument('--check', action='store_true', help='Check for updates once')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--version', action='store_true', help='Show current versions')
    
    args = parser.parse_args()
    
    manager = UpdateManager()
    
    if args.version:
        print(json.dumps(manager.version.current_version, indent=2))
    
    elif args.check:
        manager.run_update_cycle()
    
    elif args.daemon:
        logger.info("Starting update daemon...")
        while True:
            try:
                manager.run_update_cycle()
            except Exception as e:
                logger.error(f"Error in cycle: {e}")
            
            time.sleep(FirebaseConfig.CHECK_INTERVAL)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()