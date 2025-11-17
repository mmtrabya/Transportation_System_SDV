# vehicle_unlock_system.py
import json
import os
import time
import RPi.GPIO as GPIO

class UnlockSystem:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.db = firestore.client()
        self.current_booking = None
        
        # GPIO setup for door lock
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)  # Door lock pin
        
    def listen_for_bookings(self):
        """Listen for new bookings from Firebase"""
        def on_booking(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                vehicle = doc.to_dict()
                
                if 'currentBooking' in vehicle:
                    booking = vehicle['currentBooking']
                    
                    if booking['status'] == 'confirmed':
                        self.current_booking = booking
                        
                        # Save unlock code to file for infotainment
                        self.save_unlock_code(booking['unlockCode'])
                        
                        print(f"📱 New booking: {booking['bookingId']}")
                        print(f"🔐 Unlock code: {booking['unlockCode']}")
        
        # Watch vehicle document
        self.db.collection('vehicles').document(self.vehicle_id).on_snapshot(on_booking)
    
    def save_unlock_code(self, code):
        """Save unlock code for infotainment system"""
        unlock_data = {
            'code': code,
            'enabled': True,
            'timestamp': time.time(),
            'expires': time.time() + 900  # 15 minutes
        }
        
        with open('/tmp/vehicle_unlock.json', 'w') as f:
            json.dump(unlock_data, f)
    
    def verify_unlock_code(self, entered_code):
        """Verify code entered in infotainment"""
        if not self.current_booking:
            return False, "No active booking"
        
        if entered_code == self.current_booking['unlockCode']:
            # Unlock vehicle
            self.unlock_vehicle()
            
            # Update Firebase
            self.db.collection('bookings').document(
                self.current_booking['bookingId']
            ).update({
                'status': 'active',
                'actualStartTime': firestore.SERVER_TIMESTAMP,
                'vehicleUnlocked': True,
            })
            
            self.db.collection('vehicles').document(self.vehicle_id).update({
                'status': 'in_use',
                'currentBooking.status': 'active',
            })
            
            return True, "Vehicle unlocked successfully"
        
        return False, "Invalid unlock code"
    
    def unlock_vehicle(self):
        """Physically unlock the vehicle"""
        # Unlock door via GPIO
        GPIO.output(17, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(17, GPIO.LOW)
        
        # Enable vehicle systems
        os.system('systemctl start infotainment.service')
        os.system('systemctl start adas.service')
        
        print("🔓 Vehicle unlocked and systems enabled")