#!/usr/bin/env python3
"""
Firebase Configuration and Connection Manager
Handles Firebase Realtime Database connections for all components
Location: ~/Graduation_Project_SDV/raspberry_pi/firebase_config.py
"""

import firebase_admin
from firebase_admin import credentials, db
import logging
import os
from typing import Optional, Dict, Any
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Firebase_Config')

# ==================== FIREBASE CONFIGURATION ====================

class FirebaseConfig:
    """Firebase configuration and connection manager"""
    
    def __init__(self, 
                 credentials_path: str = "./sdv_firebase_key.json",
                 database_url: str = None):
        """
        Initialize Firebase configuration
        
        Args:
            credentials_path: Path to Firebase service account credentials
            database_url: Firebase Realtime Database URL
        """
        self.credentials_path = credentials_path
        self.database_url = database_url
        self.app = None
        self.connected = False
        
        # Vehicle configuration
        self.vehicle_id = "SDV001"  # Default, can be changed
        
        # Firebase paths structure
        self.paths = {
            'v2x_bsm': f'/v2x/bsm/{self.vehicle_id}',
            'v2x_nearby': f'/v2x/nearby_vehicles/{self.vehicle_id}',
            'v2x_hazards': f'/v2x/hazards/{self.vehicle_id}',
            'v2x_emergency': f'/v2x/emergency/{self.vehicle_id}',
            'gps': f'/gps/{self.vehicle_id}',
            'telemetry': f'/telemetry/{self.vehicle_id}',
            'system_status': f'/system_status/{self.vehicle_id}',
            'adas': f'/adas/{self.vehicle_id}',
            'alerts': f'/alerts/{self.vehicle_id}'
        }
        
        logger.info("Firebase Config initialized")
    
    def connect(self) -> bool:
        """
        Connect to Firebase Realtime Database
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Check if credentials file exists
            if not os.path.exists(self.credentials_path):
                logger.error(f"Credentials file not found: {self.credentials_path}")
                logger.info("Please download your Firebase service account key from:")
                logger.info("Firebase Console -> Project Settings -> Service Accounts")
                return False
            
            # Load credentials
            cred = credentials.Certificate(self.credentials_path)
            
            # Initialize Firebase Admin SDK
            if not self.database_url:
                logger.error("Database URL not provided")
                return False
            
            self.app = firebase_admin.initialize_app(cred, {
                'databaseURL': self.database_url
            })
            
            # Test connection by reading root
            ref = db.reference('/')
            ref.get()
            
            self.connected = True
            logger.info(f"✓ Connected to Firebase: {self.database_url}")
            logger.info(f"✓ Vehicle ID: {self.vehicle_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Firebase: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Firebase"""
        if self.app:
            try:
                firebase_admin.delete_app(self.app)
                self.connected = False
                logger.info("Disconnected from Firebase")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    def set_vehicle_id(self, vehicle_id: str):
        """Update vehicle ID and regenerate paths"""
        self.vehicle_id = vehicle_id
        self.paths = {
            'v2x_bsm': f'/v2x/bsm/{self.vehicle_id}',
            'v2x_nearby': f'/v2x/nearby_vehicles/{self.vehicle_id}',
            'v2x_hazards': f'/v2x/hazards/{self.vehicle_id}',
            'v2x_emergency': f'/v2x/emergency/{self.vehicle_id}',
            'gps': f'/gps/{self.vehicle_id}',
            'telemetry': f'/telemetry/{self.vehicle_id}',
            'system_status': f'/system_status/{self.vehicle_id}',
            'adas': f'/adas/{self.vehicle_id}',
            'alerts': f'/alerts/{self.vehicle_id}'
        }
        logger.info(f"Vehicle ID updated to: {vehicle_id}")
    
    def get_reference(self, path_key: str = None, custom_path: str = None):
        """
        Get Firebase database reference
        
        Args:
            path_key: Key from self.paths dictionary
            custom_path: Custom path if not using predefined paths
            
        Returns:
            Firebase database reference
        """
        if not self.connected:
            logger.error("Not connected to Firebase")
            return None
        
        try:
            if custom_path:
                return db.reference(custom_path)
            elif path_key and path_key in self.paths:
                return db.reference(self.paths[path_key])
            else:
                logger.error(f"Invalid path key: {path_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting reference: {e}")
            return None
    
    def upload_data(self, path_key: str, data: Dict[str, Any], 
                   custom_path: str = None) -> bool:
        """
        Upload data to Firebase
        
        Args:
            path_key: Key from self.paths dictionary
            data: Data to upload
            custom_path: Optional custom path
            
        Returns:
            bool: True if successful
        """
        try:
            ref = self.get_reference(path_key, custom_path)
            if ref is None:
                return False
            
            ref.set(data)
            return True
            
        except Exception as e:
            logger.error(f"Error uploading data to {path_key}: {e}")
            return False
    
    def update_data(self, path_key: str, data: Dict[str, Any],
                   custom_path: str = None) -> bool:
        """
        Update data in Firebase (merges with existing data)
        
        Args:
            path_key: Key from self.paths dictionary
            data: Data to update
            custom_path: Optional custom path
            
        Returns:
            bool: True if successful
        """
        try:
            ref = self.get_reference(path_key, custom_path)
            if ref is None:
                return False
            
            ref.update(data)
            return True
            
        except Exception as e:
            logger.error(f"Error updating data at {path_key}: {e}")
            return False
    
    def read_data(self, path_key: str, custom_path: str = None) -> Optional[Any]:
        """
        Read data from Firebase
        
        Args:
            path_key: Key from self.paths dictionary
            custom_path: Optional custom path
            
        Returns:
            Data from Firebase or None
        """
        try:
            ref = self.get_reference(path_key, custom_path)
            if ref is None:
                return None
            
            return ref.get()
            
        except Exception as e:
            logger.error(f"Error reading data from {path_key}: {e}")
            return None
    
    def delete_data(self, path_key: str, custom_path: str = None) -> bool:
        """
        Delete data from Firebase
        
        Args:
            path_key: Key from self.paths dictionary
            custom_path: Optional custom path
            
        Returns:
            bool: True if successful
        """
        try:
            ref = self.get_reference(path_key, custom_path)
            if ref is None:
                return False
            
            ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting data at {path_key}: {e}")
            return False
    
    def listen(self, path_key: str, callback, custom_path: str = None):
        """
        Listen for changes on a Firebase path
        
        Args:
            path_key: Key from self.paths dictionary
            callback: Function to call when data changes
            custom_path: Optional custom path
        """
        try:
            ref = self.get_reference(path_key, custom_path)
            if ref is None:
                return
            
            ref.listen(callback)
            logger.info(f"Listening for changes on {path_key or custom_path}")
            
        except Exception as e:
            logger.error(f"Error setting up listener: {e}")


# ==================== HELPER FUNCTIONS ====================

def create_credentials_template():
    """Create template for Firebase credentials"""
    template = {
        "type": "service_account",
        "project_id": "YOUR_PROJECT_ID",
        "private_key_id": "YOUR_PRIVATE_KEY_ID",
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-xxxxx@YOUR_PROJECT_ID.iam.gserviceaccount.com",
        "client_id": "YOUR_CLIENT_ID",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40YOUR_PROJECT_ID.iam.gserviceaccount.com"
    }
    
    with open('firebase_credentials_template.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print("Created firebase_credentials_template.json")
    print("\nTo use Firebase:")
    print("1. Go to Firebase Console -> Project Settings -> Service Accounts")
    print("2. Click 'Generate new private key'")
    print("3. Save as 'firebase_credentials.json' in this directory")
    print("4. Update the database URL in your code")


# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage"""
    
    # Check if credentials exist
    if not os.path.exists('firebase_credentials.json'):
        print("Firebase credentials not found!")
        create_credentials_template()
        return
    
    # Initialize Firebase
    firebase = FirebaseConfig(
        credentials_path='./firebase_credentials.json',
        database_url='https://YOUR_PROJECT_ID.firebaseio.com'  # Update this!
    )
    
    # Connect
    if not firebase.connect():
        print("Failed to connect to Firebase")
        return
    
    # Set vehicle ID
    firebase.set_vehicle_id("SDV001")
    
    # Example: Upload GPS data
    gps_data = {
        'latitude': 30.0444,
        'longitude': 31.2357,
        'altitude': 74.5,
        'speed': 25.5,
        'heading': 90.0,
        'timestamp': int(time.time() * 1000)
    }
    
    if firebase.upload_data('gps', gps_data):
        print("✓ GPS data uploaded")
    
    # Example: Update telemetry
    telemetry_data = {
        'battery_level': 85,
        'temperature': 45.2,
        'timestamp': int(time.time() * 1000)
    }
    
    if firebase.update_data('telemetry', telemetry_data):
        print("✓ Telemetry updated")
    
    # Example: Read data
    status = firebase.read_data('system_status')
    print(f"System status: {status}")
    
    # Example: Listen for changes
    def on_alert_change(event):
        print(f"Alert changed: {event.data}")
    
    firebase.listen('alerts', on_alert_change)
    
    # Keep running
    try:
        print("\nFirebase connection active. Press Ctrl+C to stop.")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        firebase.disconnect()


if __name__ == "__main__":
    import time
    main()