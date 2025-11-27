#!/usr/bin/env python3
"""
Firebase Manager - SIMPLIFIED AND FIXED
"""
import os
import time
from config import Config

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("⚠ Firebase not available")

class FirebaseManager:
    """Simplified Firebase Manager"""
    
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.db = None
        self.connected = False
        
        if not FIREBASE_AVAILABLE:
            print("❌ Firebase library not installed")
            return
        
        if not os.path.exists(Config.FIREBASE_CREDENTIALS):
            print(f"❌ Credentials not found: {Config.FIREBASE_CREDENTIALS}")
            return
        
        self._initialize()
    
    def _initialize(self):
        """Initialize Firebase - SIMPLIFIED"""
        try:
            print("🔄 Initializing Firebase...")
            
            # Initialize app if not already done
            if not firebase_admin._apps:
                cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
                firebase_admin.initialize_app(cred)
                print("✓ Firebase app initialized")
            
            # Get Firestore client
            self.db = firestore.client()
            print("✓ Firestore client created")
            
            # Simple connection test
            test_ref = self.db.collection('vehicles').document(self.vehicle_id)
            test_ref.get()  # This will throw if connection fails
            
            self.connected = True
            print(f"✅ Firebase connected for vehicle {self.vehicle_id}")
            
        except Exception as e:
            self.connected = False
            print(f"❌ Firebase initialization failed: {e}")
    
    def get_active_booking(self):
        """
        Get active booking - SIMPLIFIED
        Returns booking dict or None
        """
        if not self.connected:
            print("⚠ Firebase not connected")
            return None
        
        try:
            print(f"\n🔍 Searching for booking for vehicle: {self.vehicle_id}")
            
            # Method 1: Check vehicle document's currentBooking
            vehicle_ref = self.db.collection('vehicles').document(self.vehicle_id)
            vehicle_doc = vehicle_ref.get()
            
            if vehicle_doc.exists:
                vehicle_data = vehicle_doc.to_dict()
                print(f"✓ Vehicle document found")
                print(f"  Status: {vehicle_data.get('status')}")
                print(f"  Has currentBooking: {'currentBooking' in vehicle_data}")
                
                # Check if there's a currentBooking
                if 'currentBooking' in vehicle_data:
                    current_booking = vehicle_data['currentBooking']
                    
                    # If it's a dict with the booking data
                    if isinstance(current_booking, dict):
                        print(f"  Booking found in vehicle doc:")
                        print(f"    Status: {current_booking.get('status')}")
                        print(f"    Unlock Code: {current_booking.get('unlockCode')}")
                        
                        if current_booking.get('status') == 'confirmed':
                            return current_booking
            
            # Method 2: Query bookings collection
            print("🔍 Checking bookings collection...")
            bookings_ref = self.db.collection('bookings')
            query = bookings_ref.where('vehicleId', '==', self.vehicle_id).where('status', '==', 'confirmed').limit(1)
            
            results = query.get()
            for doc in results:
                booking_data = doc.to_dict()
                booking_data['bookingId'] = doc.id
                print(f"✅ Booking found in bookings collection:")
                print(f"   ID: {doc.id}")
                print(f"   Unlock Code: {booking_data.get('unlockCode')}")
                return booking_data
            
            print("⚠ No active booking found")
            return None
            
        except Exception as e:
            print(f"❌ Error getting booking: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_vehicle_status(self, status, is_online=True):
        """Update vehicle status"""
        if not self.connected:
            return False
        
        try:
            self.db.collection('vehicles').document(self.vehicle_id).update({
                'status': status,
                'isOnline': is_online,
                'last_seen': firestore.SERVER_TIMESTAMP
            })
            return True
        except:
            return False
    
    def start_booking(self, booking_id):
        """Mark booking as active"""
        if not self.connected:
            return False
        
        try:
            self.db.collection('bookings').document(booking_id).update({
                'status': 'active',
                'actualStartTime': firestore.SERVER_TIMESTAMP
            })
            return True
        except:
            return False
    
    def end_booking(self, booking_id, duration_mins, distance_km, cost):
        """Mark booking as completed"""
        if not self.connected:
            return False
        
        try:
            self.db.collection('bookings').document(booking_id).update({
                'status': 'completed',
                'actualEndTime': firestore.SERVER_TIMESTAMP,
                'actualDuration': duration_mins,
                'actualDistance': distance_km,
                'actualPrice': cost
            })
            return True
        except:
            return False