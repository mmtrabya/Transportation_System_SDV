#!/usr/bin/env python3
"""
Firebase Update Upload Utility
Easy CLI tool to upload FOTA/SOTA updates to Firebase
"""

import sys
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage, firestore

# Configuration
CREDENTIALS_FILE = Path.home() / "sdv_firebase_key.json"
STORAGE_BUCKET = "sdv-ota-system.firebasestorage.app"  # Change to your bucket

def init_firebase():
    """Initialize Firebase"""
    if not firebase_admin._apps:
        if not CREDENTIALS_FILE.exists():
            print(f"❌ Error: Credentials file not found: {CREDENTIALS_FILE}")
            print("   Download service account key from Firebase Console")
            sys.exit(1)
        
        cred = credentials.Certificate(str(CREDENTIALS_FILE))
        firebase_admin.initialize_app(cred, {
            'storageBucket': STORAGE_BUCKET
        })
        print("✓ Firebase initialized")

def calculate_hash(file_path):
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def upload_update(file_path, component, version, description="", update_type=None):
    """Upload update to Firebase Storage"""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return False
    
    # Auto-detect update type if not specified
    if not update_type:
        if file_path.suffix == '.bin':
            update_type = component
        else:
            update_type = 'software'
    
    print(f"\n📦 Uploading Update")
    print(f"   File: {file_path.name}")
    print(f"   Component: {component}")
    print(f"   Version: {version}")
    print(f"   Type: {update_type}")
    print(f"   Size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Calculate hash
    print("\n🔒 Calculating hash...")
    file_hash = calculate_hash(file_path)
    print(f"   Hash: {file_hash[:16]}...")
    
    # Create update ID
    update_id = f"{component}_{version}".replace(".", "_")
    storage_path = f"updates/{file_path.name}"
    
    # Upload to Storage
    print("\n☁️  Uploading to Firebase Storage...")
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)
    
    # Set metadata
    blob.metadata = {
        'component': component,
        'version': version,
        'update_type': update_type,
        'update_id': update_id,
        'description': description,
        'hash': file_hash
    }
    
    blob.upload_from_filename(str(file_path))
    print("   ✓ Upload complete")
    
    # Create Firestore document
    print("\n📄 Creating Firestore metadata...")
    db = firestore.client()
    
    update_doc = {
        'update_id': update_id,
        'filename': file_path.name,
        'storage_path': storage_path,
        'component': component,
        'version': version,
        'update_type': update_type,
        'hash': file_hash,
        'size': file_path.stat().st_size,
        'uploaded_at': firestore.SERVER_TIMESTAMP,
        'active': True,
        'description': description,
        'hardware_version': 'any'
    }
    
    db.collection('updates').document(update_id).set(update_doc)
    print("   ✓ Metadata saved")
    
    # Log upload
    db.collection('update_logs').add({
        'event_type': 'uploaded',
        'update_id': update_id,
        'component': component,
        'version': version,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    
    print(f"\n✅ Update uploaded successfully!")
    print(f"   Update ID: {update_id}")
    print(f"\n   Download URL: https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{storage_path.replace('/', '%2F')}?alt=media")
    
    return True

def list_updates():
    """List all updates in Firestore"""
    db = firestore.client()
    
    updates = db.collection('updates').where('active', '==', True).stream()
    
    print("\n📦 Available Updates:")
    print("-" * 80)
    
    count = 0
    for doc in updates:
        update = doc.data()
        count += 1
        
        print(f"\n{count}. {update['component']} v{update['version']}")
        print(f"   ID: {update['update_id']}")
        print(f"   Type: {update['update_type']}")
        print(f"   Size: {update.get('size', 0) / 1024 / 1024:.2f} MB")
        print(f"   Hash: {update['hash'][:16]}...")
        if update.get('description'):
            print(f"   Description: {update['description']}")
        if update.get('uploaded_at'):
            print(f"   Uploaded: {update['uploaded_at']}")
    
    if count == 0:
        print("\n   No updates found")
    
    print("\n" + "-" * 80)
    print(f"Total: {count} update(s)")

def delete_update(update_id):
    """Delete/deactivate an update"""
    db = firestore.client()
    
    # Deactivate in Firestore
    db.collection('updates').document(update_id).update({'active': False})
    
    # Log deletion
    db.collection('update_logs').add({
        'event_type': 'deleted',
        'update_id': update_id,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    
    print(f"✓ Update {update_id} deactivated")

def list_vehicles():
    """List registered vehicles"""
    db = firestore.client()
    
    vehicles = db.collection('vehicles').stream()
    
    print("\n🚗 Registered Vehicles:")
    print("-" * 80)
    
    count = 0
    for doc in vehicles:
        vehicle = doc.data()
        count += 1
        
        print(f"\n{count}. {doc.id}")
        print(f"   Status: {vehicle.get('status', 'unknown')}")
        print(f"   Update Status: {vehicle.get('update_status', 'idle')}")
        
        versions = vehicle.get('current_versions', {})
        if versions:
            print(f"   Versions:")
            for component, version in versions.items():
                if component not in ['last_update', 'hardware_version']:
                    print(f"     - {component}: {version}")
        
        if vehicle.get('last_seen'):
            print(f"   Last Seen: {vehicle['last_seen']}")
    
    if count == 0:
        print("\n   No vehicles registered")
    
    print("\n" + "-" * 80)
    print(f"Total: {count} vehicle(s)")

def trigger_update(vehicle_id, update_id):
    """Manually trigger update for specific vehicle"""
    db = firestore.client()
    
    # Check if update exists
    update_doc = db.collection('updates').document(update_id).get()
    if not update_doc.exists:
        print(f"❌ Update {update_id} not found")
        return False
    
    # Check if vehicle exists
    vehicle_doc = db.collection('vehicles').document(vehicle_id).get()
    if not vehicle_doc.exists:
        print(f"❌ Vehicle {vehicle_id} not found")
        return False
    
    # Add notification
    db.collection('vehicles').document(vehicle_id).collection('notifications').add({
        'type': 'update_required',
        'update_id': update_id,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'priority': 'high'
    })
    
    print(f"✓ Update {update_id} triggered for {vehicle_id}")
    return True

def main():
    """Main CLI"""
    parser = argparse.ArgumentParser(
        description='Firebase FOTA/SOTA Update Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload ESP32 firmware:
    %(prog)s upload firmware.bin esp32_firmware 1.1.0 "Bug fixes"
  
  Upload software package:
    %(prog)s upload software.tar.gz software_version 2.0.0 "New features"
  
  List all updates:
    %(prog)s list
  
  List vehicles:
    %(prog)s vehicles
  
  Trigger update:
    %(prog)s trigger SDV002 esp32_firmware_1_1_0
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload new update')
    upload_parser.add_argument('file', help='Update file path')
    upload_parser.add_argument('component', help='Component name (e.g., esp32_firmware)')
    upload_parser.add_argument('version', help='Version number (e.g., 1.1.0)')
    upload_parser.add_argument('description', nargs='?', default='', help='Update description')
    upload_parser.add_argument('--type', help='Update type (auto-detected if not specified)')
    
    # List command
    subparsers.add_parser('list', help='List all updates')
    
    # Vehicles command
    subparsers.add_parser('vehicles', help='List all vehicles')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete/deactivate update')
    delete_parser.add_argument('update_id', help='Update ID to delete')
    
    # Trigger command
    trigger_parser = subparsers.add_parser('trigger', help='Trigger update for vehicle')
    trigger_parser.add_argument('vehicle_id', help='Vehicle ID')
    trigger_parser.add_argument('update_id', help='Update ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize Firebase
    try:
        init_firebase()
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return
    
    # Execute command
    try:
        if args.command == 'upload':
            upload_update(
                args.file,
                args.component,
                args.version,
                args.description,
                args.type
            )
        
        elif args.command == 'list':
            list_updates()
        
        elif args.command == 'vehicles':
            list_vehicles()
        
        elif args.command == 'delete':
            delete_update(args.update_id)
        
        elif args.command == 'trigger':
            trigger_update(args.vehicle_id, args.update_id)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()