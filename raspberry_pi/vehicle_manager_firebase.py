#!/usr/bin/env python3
"""
Firebase Vehicle Manager for Raspberry Pi
Integrates GPS, Booking System, and Infotainment Control
"""

import firebase_admin
from firebase_admin import credentials, firestore
import serial
import pynmea2
import time
import json
import os
import subprocess
from pathlib import Path
import RPi.GPIO as GPIO
import threading

# Configuration
VEHICLE_ID = "SDV_001"
GPS_PORT = "/dev/ttyUSB0"  # Ublox NEO-6M
GPS_BAUDRATE = 9600
DOOR_LOCK_PIN = 17
FIREBASE_CREDS = str(Path.home() / "sdv_firebase_key.json")

class VehicleManager:
    """Main vehicle manager integrating all systems"""
    
    def __init__(self, vehicle_id=VEHICLE_ID):
        self.vehicle_id = vehicle_id
        self.current_booking = None
        self.is_unlocked = False
        self.gps_data = None
        
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDS)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        
        # Initialize GPS
        self.init_gps()
        
        # Initialize GPIO
        self.init_gpio()
        
        # Register vehicle in Firebase
        self.register_vehicle()
        
        print(f"✅ Vehicle Manager initialized for {vehicle_id}")
    
    def init_gps(self):
        """Initialize Ublox NEO-6M GPS module"""
        try:
            self.gps_serial = serial.Serial(GPS_PORT, baudrate=GPS_BAUDRATE, timeout=1)
            print("✅ GPS initialized on", GPS_PORT)
        except Exception as e:
            print(f"❌ GPS initialization failed: {e}")
            self.gps_serial = None
    
    def init_gpio(self):
        """Initialize GPIO for door lock control"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DOOR_LOCK_PIN, GPIO.OUT)
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)  # Ensure locked initially
        print("✅ GPIO initialized")
    
    def register_vehicle(self):
        """Register vehicle in Firebase"""
        vehicle_ref = self.db.collection('vehicles').document(self.vehicle_id)
        
        vehicle_data = {
            'vehicleId': self.vehicle_id,
            'model': 'City Cruiser',
            'category': 'compact',
            'status': 'available',
            'isOnline': True,
            'batteryLevel': 85,
            'lastUpdate': firestore.SERVER_TIMESTAMP,
            'pricePerHour': 15.0,
            'pricePerKm': 0.5,
        }
        
        vehicle_ref.set(vehicle_data, merge=True)
        print(f"✅ Vehicle registered: {self.vehicle_id}")
    
    def read_gps_data(self):
        """Read GPS data from Ublox NEO-6M"""
        if not self.gps_serial:
            return None
        
        try:
            line = self.gps_serial.readline().decode('ascii', errors='ignore').strip()
            
            if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                msg = pynmea2.parse(line)
                
                if msg.latitude and msg.longitude:
                    return {
                        'latitude': msg.latitude,
                        'longitude': msg.longitude,
                        'altitude': msg.altitude if hasattr(msg, 'altitude') else 0,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    }
            
            elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                msg = pynmea2.parse(line)
                
                if hasattr(msg, 'spd_over_grnd') and hasattr(msg, 'true_course'):
                    speed_kmh = msg.spd_over_grnd * 1.852 if msg.spd_over_grnd else 0
                    
                    return {
                        'speed': speed_kmh,
                        'heading': msg.true_course if msg.true_course else 0,
                    }
                    
        except Exception as e:
            print(f"GPS read error: {e}")
        
        return None
    
    def update_vehicle_location(self):
        """Update vehicle location in Firebase from GPS"""
        gps_data = self.read_gps_data()
        
        if gps_data:
            # Merge with existing GPS data
            if self.gps_data:
                self.gps_data.update(gps_data)
            else:
                self.gps_data = gps_data
            
            # Update Firebase
            self.db.collection('vehicles').document(self.vehicle_id).update({
                'location': self.gps_data,
                'isOnline': True,
                'lastUpdate': firestore.SERVER_TIMESTAMP
            })
    
    def listen_for_bookings(self):
        """Listen for new bookings from Firebase"""
        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                vehicle_data = doc.to_dict()
                
                if 'currentBooking' in vehicle_data:
                    booking = vehicle_data['currentBooking']
                    
                    if booking['status'] == 'confirmed' and self.current_booking != booking:
                        self.current_booking = booking
                        
                        print(f"\n📱 NEW BOOKING RECEIVED")
                        print(f"   Booking ID: {booking['bookingId']}")
                        print(f"   Unlock Code: {booking['unlockCode']}")
                        print(f"   User: {booking['userId']}")
                        
                        # Save unlock code for infotainment
                        self.save_unlock_code(booking['unlockCode'])
                        
                        # Notify infotainment to show unlock screen
                        self.notify_infotainment('show_unlock')
        
        # Watch vehicle document for changes
        self.db.collection('vehicles').document(self.vehicle_id).on_snapshot(on_snapshot)
        print("👂 Listening for bookings...")
    
    def save_unlock_code(self, unlock_code):
        """Save unlock code to file for infotainment system"""
        unlock_data = {
            'code': unlock_code,
            'enabled': True,
            'timestamp': time.time(),
            'expires': time.time() + 900,  # 15 minutes
            'vehicle_id': self.vehicle_id,
            'booking_id': self.current_booking['bookingId']
        }
        
        unlock_file = Path('/tmp/vehicle_unlock.json')
        with open(unlock_file, 'w') as f:
            json.dump(unlock_data, f, indent=2)
        
        print(f"🔐 Unlock code saved: {unlock_code}")
    
    def verify_unlock_code(self, entered_code):
        """Verify unlock code entered in infotainment"""
        if not self.current_booking:
            return False, "No active booking"
        
        correct_code = self.current_booking['unlockCode']
        
        if entered_code == correct_code:
            # Unlock vehicle
            self.unlock_vehicle()
            
            # Update booking status in Firebase
            self.db.collection('bookings').document(
                self.current_booking['bookingId']
            ).update({
                'status': 'active',
                'actualStartTime': firestore.SERVER_TIMESTAMP,
                'vehicleUnlocked': True,
            })
            
            # Update vehicle status
            self.db.collection('vehicles').document(self.vehicle_id).update({
                'status': 'in_use',
                'currentBooking.status': 'active',
            })
            
            print("✅ Vehicle unlocked successfully")
            return True, "Vehicle unlocked! Welcome aboard."
        
        print("❌ Invalid unlock code")
        return False, "Invalid unlock code"
    
    def unlock_vehicle(self):
        """Physically unlock the vehicle"""
        # Unlock door via GPIO
        GPIO.output(DOOR_LOCK_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
        
        self.is_unlocked = True
        
        # Enable vehicle systems
        print("🚗 Starting vehicle systems...")
        
        # Start infotainment (if not already running)
        try:
            subprocess.run(['systemctl', 'start', 'infotainment.service'], check=False)
        except:
            pass
        
        # Start ADAS
        try:
            subprocess.run(['systemctl', 'start', 'adas.service'], check=False)
        except:
            pass
        
        # Start V2X
        try:
            subprocess.run(['systemctl', 'start', 'v2x.service'], check=False)
        except:
            pass
        
        print("✅ Vehicle systems enabled")
    
    def lock_vehicle(self):
        """Lock the vehicle"""
        # Lock door via GPIO
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
        
        self.is_unlocked = False
        
        # Update Firebase
        self.db.collection('vehicles').document(self.vehicle_id).update({
            'status': 'available',
            'currentBooking': firestore.DELETE_FIELD,
        })
        
        # Clear current booking
        self.current_booking = None
        
        # Remove unlock file
        unlock_file = Path('/tmp/vehicle_unlock.json')
        if unlock_file.exists():
            unlock_file.unlink()
        
        print("🔒 Vehicle locked")
    
    def notify_infotainment(self, event_type, data=None):
        """Send notification to infotainment system"""
        notification = {
            'type': event_type,
            'timestamp': time.time(),
            'data': data or {}
        }
        
        notification_file = Path('/tmp/infotainment_notification.json')
        with open(notification_file, 'w') as f:
            json.dump(notification, f)
    
    def end_rental(self):
        """End current rental"""
        if not self.current_booking:
            return
        
        booking_id = self.current_booking['bookingId']
        
        # Calculate duration and distance
        # (This would be tracked during the rental)
        actual_duration = 30  # minutes (placeholder)
        actual_distance = 5.0  # km (placeholder)
        
        # Calculate price
        actual_price = (actual_duration / 60 * 15.0) + (actual_distance * 0.5)
        
        # Update booking
        self.db.collection('bookings').document(booking_id).update({
            'status': 'completed',
            'actualEndTime': firestore.SERVER_TIMESTAMP,
            'actualDuration': actual_duration,
            'actualDistance': actual_distance,
            'actualPrice': actual_price,
            'paymentStatus': 'completed',
        })
        
        # Lock vehicle
        self.lock_vehicle()
        
        print(f"✅ Rental ended. Price: ${actual_price:.2f}")
    
    def gps_update_loop(self):
        """Continuously update GPS location"""
        while True:
            try:
                self.update_vehicle_location()
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"GPS update error: {e}")
                time.sleep(5)
    
    def run(self):
        """Main run loop"""
        print(f"\n{'='*60}")
        print(f"🚗 Vehicle Manager Running")
        print(f"   Vehicle ID: {self.vehicle_id}")
        print(f"   Status: {'Unlocked' if self.is_unlocked else 'Locked'}")
        print(f"{'='*60}\n")
        
        # Start GPS update thread
        gps_thread = threading.Thread(target=self.gps_update_loop, daemon=True)
        gps_thread.start()
        
        # Listen for bookings
        self.listen_for_bookings()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            self.lock_vehicle()
            GPIO.cleanup()

# ==================== MAIN ====================

def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Vehicle Manager with Firebase Integration          ║
    ║   - GPS Tracking (Ublox NEO-6M)                          ║
    ║   - Booking Management                                   ║
    ║   - Vehicle Unlock System                                ║
    ║   - Infotainment Control                                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Create and run vehicle manager
    manager = VehicleManager()
    manager.run()

if __name__ == "__main__":
    main()