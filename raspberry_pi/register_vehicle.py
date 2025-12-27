#!/usr/bin/env python3
"""
Vehicle Registration Script for Firebase
Run this ONCE on your Raspberry Pi to register it
"""

import firebase_admin
from firebase_admin import credentials, firestore
import subprocess
import json
from pathlib import Path
import uuid

# Configuration
VEHICLE_ID = "SDV001"  # Change for each vehicle
FIREBASE_CREDS = Path.home() / "sdv_firebase_key.json"

def get_hardware_info():
    """Get Raspberry Pi hardware information"""
    try:
        # Get CPU serial number
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial = line.split(':')[1].strip()
                    break
        
        # Get MAC address
        mac = subprocess.check_output(['cat', '/sys/class/net/eth0/address']).decode().strip()
        
        return {
            'serial': serial,
            'mac_address': mac
        }
    except:
        return {
            'serial': 'unknown',
            'mac_address': 'unknown'
        }

def get_current_versions():
    """Read current firmware/software versions"""
    version_file = Path.home() / "sdv" / "version.json"
    
    if version_file.exists():
        with open(version_file, 'r') as f:
            return json.load(f)
    
    # Default versions for first time
    return {
        'software_version': '1.0.0',
        'esp32_firmware': '1.0.0',
        'atmega32_firmware': '1.0.0',
        'adas_model': '1.0.0',
        'hardware_version': '1.0',
        'last_update': None
    }

def register_vehicle():
    """Register vehicle in Firebase"""
    
    print(f"\n{'='*60}")
    print(f"🚗 Vehicle Registration")
    print(f"{'='*60}\n")
    
    # Initialize Firebase
    if not FIREBASE_CREDS.exists():
        print(f"❌ Error: Firebase credentials not found at {FIREBASE_CREDS}")
        print("   Download service account key from Firebase Console")
        return False
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(FIREBASE_CREDS))
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    # Get system info
    print("📊 Gathering system information...")
    hardware = get_hardware_info()
    versions = get_current_versions()
    
    # Create vehicle document
    vehicle_data = {
        'vehicle_id': VEHICLE_ID,
        'hardware_version': versions.get('hardware_version', '1.0'),
        'current_versions': versions,
        
        # Hardware info
        'serial_number': hardware['serial'],
        'mac_address': hardware['mac_address'],
        
        # Status
        'status': 'online',
        'update_status': 'idle',
        'last_seen': firestore.SERVER_TIMESTAMP,
        
        # Location (will be updated by GPS)
        'location': {
            'latitude': 30.0444,
            'longitude': 31.2357
        },
        
        # Metadata
        'registered_at': firestore.SERVER_TIMESTAMP,
        'device_type': 'raspberry_pi_5'
    }
    
    print(f"\n📝 Registering vehicle: {VEHICLE_ID}")
    print(f"   Serial: {hardware['serial']}")
    print(f"   MAC: {hardware['mac_address']}")
    print(f"   Software: {versions['software_version']}")
    print(f"   ESP32: {versions['esp32_firmware']}")
    print(f"   ATmega32: {versions['atmega32_firmware']}")
    
    # Save to Firestore
    db.collection('vehicles').document(VEHICLE_ID).set(vehicle_data)
    
    print(f"\n✅ Vehicle registered successfully in Firebase!")
    print(f"   You can now send OTA updates to this vehicle")
    
    # Save version file locally
    version_file = Path.home() / "sdv" / "version.json"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(version_file, 'w') as f:
        json.dump(versions, f, indent=2)
    
    print(f"\n📄 Version file saved: {version_file}")
    
    return True

def main():
    if register_vehicle():
        print(f"\n{'='*60}")
        print(f"🎉 Registration Complete!")
        print(f"{'='*60}\n")
        print("Next steps:")
        print("1. Start the OTA manager: python3 fota_sota_manager.py --daemon")
        print("2. Upload updates from your dev machine")
        print("3. Monitor updates in Firebase Console")
    else:
        print("\n❌ Registration failed")

if __name__ == "__main__":
    main()