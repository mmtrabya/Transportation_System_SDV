#!/usr/bin/env python3
"""
Integrated V2X System with GPS and Firebase
Combines GPS, V2X communication, and Firebase telemetry
Location: ~/Graduation_Project_SDV/raspberry_pi/integrated_v2x_system.py

This system:
- Reads GPS data from Ublox NEO-6M
- Communicates with ESP32 V2X module
- Uploads all data to Firebase Realtime Database
- Provides real-time vehicle tracking and V2X messaging
"""

import time
import threading
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Import our modules
from gps_interface import GPSInterface, GPSData
from v2x_interface import V2XInterface, NearbyVehicle, HazardWarning
from firebase_config import FirebaseConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Integrated_V2X')

# ==================== INTEGRATED V2X SYSTEM ====================

class IntegratedV2XSystem:
    """Complete integrated V2X system with GPS and Firebase"""
    
    def __init__(self,
                 vehicle_id: str = "SDV001",
                 gps_port: str = None,  # Auto-detect
                 v2x_port: str = '/dev/ttyUSB0',
                 firebase_credentials: str = './firebase_credentials.json',
                 firebase_url: str = None):
        """
        Initialize integrated system
        
        Args:
            vehicle_id: Unique vehicle identifier
            gps_port: GPS serial port (auto-detect if None)
            v2x_port: V2X ESP32 serial port
            firebase_credentials: Path to Firebase credentials JSON
            firebase_url: Firebase Realtime Database URL
        """
        self.vehicle_id = vehicle_id
        
        # Initialize components
        self.gps = GPSInterface(port=gps_port, baudrate=9600, enable_logging=True)
        self.v2x = V2XInterface(serial_port=v2x_port, baudrate=115200)
        self.firebase = FirebaseConfig(
            credentials_path=firebase_credentials,
            database_url=firebase_url
        )
        
        # Set vehicle ID for Firebase
        self.firebase.set_vehicle_id(vehicle_id)
        
        # System state
        self.running = False
        self.gps_ready = False
        self.v2x_ready = False
        self.firebase_ready = False
        
        # Threading
        self.upload_thread: Optional[threading.Thread] = None
        
        # Upload intervals (seconds)
        self.intervals = {
            'gps': 0.5,           # 2 Hz - GPS position
            'v2x_bsm': 0.1,       # 10 Hz - Real-time BSM
            'v2x_nearby': 1.0,    # 1 Hz - Nearby vehicles list
            'telemetry': 5.0,     # 0.2 Hz - System health
            'status': 10.0        # 0.1 Hz - Online status
        }
        
        # Last upload times
        self.last_upload = {key: 0 for key in self.intervals.keys()}
        
        # Statistics
        self.stats = {
            'gps_updates': 0,
            'v2x_messages': 0,
            'firebase_uploads': 0,
            'firebase_errors': 0,
            'start_time': time.time()
        }
        
        logger.info(f"Integrated V2X System initialized for {vehicle_id}")
    
    def connect_all(self) -> bool:
        """Connect all subsystems"""
        logger.info("Connecting subsystems...")
        
        # Connect GPS
        logger.info("1/3 Connecting GPS...")
        if self.gps.connect():
            self.gps.start_reading()
            self.gps_ready = True
            logger.info("✓ GPS connected")
            
            # Wait for GPS fix
            logger.info("Waiting for GPS fix...")
            if self.gps.wait_for_fix(timeout=60):
                logger.info("✓ GPS fix acquired")
            else:
                logger.warning("⚠ GPS fix timeout - continuing anyway")
        else:
            logger.error("✗ GPS connection failed")
            return False
        
        # Connect V2X
        logger.info("2/3 Connecting V2X (ESP32)...")
        if self.v2x.connect():
            self.v2x.start()
            self.v2x_ready = True
            logger.info("✓ V2X connected")
        else:
            logger.error("✗ V2X connection failed")
            return False
        
        # Connect Firebase
        logger.info("3/3 Connecting Firebase...")
        if self.firebase.connect():
            self.firebase_ready = True
            logger.info("✓ Firebase connected")
        else:
            logger.error("✗ Firebase connection failed")
            return False
        
        # Register callbacks
        self._setup_callbacks()
        
        logger.info("\n✓ All subsystems connected!")
        return True
    
    def _setup_callbacks(self):
        """Setup callbacks for V2X events"""
        
        # BSM received callback
        def on_bsm_received(vehicle: NearbyVehicle):
            logger.debug(f"BSM from {vehicle.vehicle_id}: {vehicle.distance:.1f}m")
            self.stats['v2x_messages'] += 1
            
            # Upload to Firebase immediately if close
            if vehicle.distance < 50:
                self._upload_nearby_vehicle(vehicle)
        
        # Hazard received callback
        def on_hazard_received(hazard: HazardWarning):
            logger.warning(f"HAZARD: {hazard.description} at {hazard.distance:.0f}m")
            self.stats['v2x_messages'] += 1
            
            # Upload hazard to Firebase
            self._upload_hazard(hazard)
            
            # Create alert
            self._create_alert('hazard', hazard.description, 'warning')
        
        # Emergency vehicle callback
        def on_emergency_received(data: Dict):
            logger.warning(f"EMERGENCY VEHICLE at {data['distance']:.0f}m!")
            self.stats['v2x_messages'] += 1
            
            # Upload emergency to Firebase
            self._upload_emergency(data)
            
            # Create critical alert
            self._create_alert('emergency', 
                             f"Emergency vehicle {data['distance']:.0f}m away",
                             'critical')
        
        # GPS update callback
        def on_gps_update(gps_data: GPSData):
            self.stats['gps_updates'] += 1
            
            # Update V2X with current position
            if self.v2x_ready:
                self.v2x.update_vehicle_state(
                    latitude=gps_data.latitude,
                    longitude=gps_data.longitude,
                    altitude=gps_data.altitude,
                    speed=gps_data.speed,
                    heading=gps_data.heading
                )
        
        # Register callbacks
        self.v2x.register_callback('bsm_received', on_bsm_received)
        self.v2x.register_callback('hazard_received', on_hazard_received)
        self.v2x.register_callback('emergency_received', on_emergency_received)
        self.gps.register_callback(on_gps_update)
        
        logger.info("✓ Callbacks registered")
    
    def start(self):
        """Start the integrated system"""
        if not (self.gps_ready and self.v2x_ready and self.firebase_ready):
            logger.error("Not all subsystems ready. Call connect_all() first.")
            return False
        
        self.running = True
        
        # Start upload thread
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.upload_thread.start()
        
        logger.info("✓ Integrated V2X System started")
        return True
    
    def stop(self):
        """Stop the integrated system"""
        logger.info("Stopping integrated system...")
        
        self.running = False
        
        # Wait for upload thread
        if self.upload_thread:
            self.upload_thread.join(timeout=2)
        
        # Disconnect all
        if self.gps_ready:
            self.gps.disconnect()
        if self.v2x_ready:
            self.v2x.disconnect()
        if self.firebase_ready:
            self.firebase.disconnect()
        
        logger.info("✓ Integrated system stopped")
    
    def _upload_loop(self):
        """Background thread for uploading data to Firebase"""
        logger.info("Upload thread started")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Upload GPS data
                if current_time - self.last_upload['gps'] >= self.intervals['gps']:
                    self._upload_gps_data()
                    self.last_upload['gps'] = current_time
                
                # Upload V2X BSM
                if current_time - self.last_upload['v2x_bsm'] >= self.intervals['v2x_bsm']:
                    self._upload_v2x_bsm()
                    self.last_upload['v2x_bsm'] = current_time
                
                # Upload nearby vehicles list
                if current_time - self.last_upload['v2x_nearby'] >= self.intervals['v2x_nearby']:
                    self._upload_nearby_vehicles()
                    self.last_upload['v2x_nearby'] = current_time
                
                # Upload telemetry
                if current_time - self.last_upload['telemetry'] >= self.intervals['telemetry']:
                    self._upload_telemetry()
                    self.last_upload['telemetry'] = current_time
                
                # Upload status
                if current_time - self.last_upload['status'] >= self.intervals['status']:
                    self._upload_status()
                    self.last_upload['status'] = current_time
                
                time.sleep(0.05)  # 20 Hz loop
                
            except Exception as e:
                logger.error(f"Error in upload loop: {e}")
                self.stats['firebase_errors'] += 1
                time.sleep(1)
    
    def _upload_gps_data(self):
        """Upload GPS data to Firebase"""
        if not self.gps.is_valid():
            return
        
        gps_data = self.gps.get_data()
        
        data = {
            'latitude': gps_data.latitude,
            'longitude': gps_data.longitude,
            'altitude': gps_data.altitude,
            'speed': gps_data.speed,
            'heading': gps_data.heading,
            'satellites': gps_data.satellites_used,
            'hdop': gps_data.hdop,
            'fix_type': gps_data.fix_type,
            'timestamp': int(time.time() * 1000)
        }
        
        if self.firebase.update_data('gps', data):
            self.stats['firebase_uploads'] += 1
        else:
            self.stats['firebase_errors'] += 1
    
    def _upload_v2x_bsm(self):
        """Upload V2X Basic Safety Message"""
        if not self.gps.is_valid():
            return
        
        gps_data = self.gps.get_data()
        
        bsm_data = {
            'vehicle_id': self.vehicle_id,
            'latitude': gps_data.latitude,
            'longitude': gps_data.longitude,
            'speed': gps_data.speed,
            'heading': gps_data.heading,
            'timestamp': int(time.time() * 1000)
        }
        
        if self.firebase.update_data('v2x_bsm', bsm_data):
            self.stats['firebase_uploads'] += 1
        else:
            self.stats['firebase_errors'] += 1
    
    def _upload_nearby_vehicles(self):
        """Upload list of nearby vehicles"""
        nearby = self.v2x.get_nearby_vehicles(max_distance=200)
        
        if not nearby:
            return
        
        vehicles_data = {}
        for vehicle in nearby:
            vehicles_data[vehicle.vehicle_id] = {
                'latitude': vehicle.latitude,
                'longitude': vehicle.longitude,
                'speed': vehicle.speed,
                'heading': vehicle.heading,
                'distance': vehicle.distance,
                'is_emergency': vehicle.is_emergency,
                'last_seen': int(vehicle.last_seen * 1000)
            }
        
        if self.firebase.update_data('v2x_nearby', vehicles_data):
            self.stats['firebase_uploads'] += 1
        else:
            self.stats['firebase_errors'] += 1
    
    def _upload_nearby_vehicle(self, vehicle: NearbyVehicle):
        """Upload single nearby vehicle immediately"""
        data = {
            'latitude': vehicle.latitude,
            'longitude': vehicle.longitude,
            'speed': vehicle.speed,
            'distance': vehicle.distance,
            'is_emergency': vehicle.is_emergency,
            'timestamp': int(time.time() * 1000)
        }
        
        custom_path = f'/v2x/nearby_vehicles/{self.vehicle_id}/{vehicle.vehicle_id}'
        self.firebase.update_data(None, data, custom_path=custom_path)
    
    def _upload_hazard(self, hazard: HazardWarning):
        """Upload hazard warning"""
        hazard_data = {
            'vehicle_id': hazard.vehicle_id,
            'type': hazard.hazard_type,
            'latitude': hazard.latitude,
            'longitude': hazard.longitude,
            'description': hazard.description,
            'distance': hazard.distance,
            'timestamp': int(hazard.timestamp * 1000)
        }
        
        # Use push to create unique key for each hazard
        custom_path = f'/v2x/hazards/{self.vehicle_id}'
        ref = self.firebase.get_reference(custom_path=custom_path)
        if ref:
            ref.push(hazard_data)
    
    def _upload_emergency(self, emergency_data: Dict):
        """Upload emergency vehicle alert"""
        data = {
            'vehicle_id': emergency_data['vehicle_id'],
            'type': emergency_data['type'],
            'distance': emergency_data['distance'],
            'timestamp': int(time.time() * 1000)
        }
        
        if self.firebase.update_data('v2x_emergency', data):
            self.stats['firebase_uploads'] += 1
    
    def _upload_telemetry(self):
        """Upload system telemetry"""
        import psutil
        
        gps_data = self.gps.get_data() if self.gps_ready else None
        
        telemetry = {
            'gps': {
                'valid': self.gps.is_valid() if self.gps_ready else False,
                'satellites': gps_data.satellites_used if gps_data else 0,
                'hdop': gps_data.hdop if gps_data else 99.9
            },
            'v2x': {
                'nearby_vehicles': len(self.v2x.nearby_vehicles),
                'messages_received': self.stats['v2x_messages']
            },
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'uptime': time.time() - self.stats['start_time']
            },
            'timestamp': int(time.time() * 1000)
        }
        
        if self.firebase.update_data('telemetry', telemetry):
            self.stats['firebase_uploads'] += 1
        else:
            self.stats['firebase_errors'] += 1
    
    def _upload_status(self):
        """Upload system status"""
        status_data = {
            'online': True,
            'vehicle_id': self.vehicle_id,
            'gps_ready': self.gps_ready,
            'v2x_ready': self.v2x_ready,
            'firebase_ready': self.firebase_ready,
            'last_seen': int(time.time() * 1000),
            'statistics': {
                'gps_updates': self.stats['gps_updates'],
                'v2x_messages': self.stats['v2x_messages'],
                'firebase_uploads': self.stats['firebase_uploads'],
                'firebase_errors': self.stats['firebase_errors']
            }
        }
        
        if self.firebase.update_data('system_status', status_data):
            self.stats['firebase_uploads'] += 1
        else:
            self.stats['firebase_errors'] += 1
    
    def _create_alert(self, alert_type: str, message: str, severity: str):
        """Create and upload alert"""
        alert_data = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': int(time.time() * 1000)
        }
        
        # Push alert with unique key
        ref = self.firebase.get_reference('alerts')
        if ref:
            ref.push(alert_data)
            logger.info(f"Alert created: {alert_type} - {message}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        uptime = time.time() - self.stats['start_time']
        
        return {
            'vehicle_id': self.vehicle_id,
            'uptime': uptime,
            'gps': {
                'ready': self.gps_ready,
                'valid': self.gps.is_valid() if self.gps_ready else False,
                'updates': self.stats['gps_updates'],
                'rate': self.stats['gps_updates'] / max(1, uptime)
            },
            'v2x': {
                'ready': self.v2x_ready,
                'messages': self.stats['v2x_messages'],
                'nearby_vehicles': len(self.v2x.nearby_vehicles) if self.v2x_ready else 0
            },
            'firebase': {
                'ready': self.firebase_ready,
                'uploads': self.stats['firebase_uploads'],
                'errors': self.stats['firebase_errors'],
                'success_rate': (self.stats['firebase_uploads'] / 
                               max(1, self.stats['firebase_uploads'] + self.stats['firebase_errors'])) * 100,
                'upload_rate': self.stats['firebase_uploads'] / max(1, uptime)
            }
        }
    
    def print_status(self):
        """Print system status"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print(f"INTEGRATED V2X SYSTEM STATUS - {self.vehicle_id}")
        print("="*60)
        
        # GPS Status
        print(f"\n📡 GPS:")
        print(f"   Status: {'✓ Ready' if stats['gps']['ready'] else '✗ Not Ready'}")
        print(f"   Fix: {'✓ Valid' if stats['gps']['valid'] else '✗ No Fix'}")
        print(f"   Updates: {stats['gps']['updates']} ({stats['gps']['rate']:.1f}/s)")
        
        if self.gps.is_valid():
            gps_data = self.gps.get_data()
            print(f"   Position: {gps_data.latitude:.6f}, {gps_data.longitude:.6f}")
            print(f"   Speed: {gps_data.speed:.1f} km/h")
            print(f"   Satellites: {gps_data.satellites_used}/{gps_data.satellites_visible}")
        
        # V2X Status
        print(f"\n📻 V2X:")
        print(f"   Status: {'✓ Ready' if stats['v2x']['ready'] else '✗ Not Ready'}")
        print(f"   Messages: {stats['v2x']['messages']}")
        print(f"   Nearby Vehicles: {stats['v2x']['nearby_vehicles']}")
        
        # Firebase Status
        print(f"\n☁️  Firebase:")
        print(f"   Status: {'✓ Connected' if stats['firebase']['ready'] else '✗ Disconnected'}")
        print(f"   Uploads: {stats['firebase']['uploads']}")
        print(f"   Errors: {stats['firebase']['errors']}")
        print(f"   Success Rate: {stats['firebase']['success_rate']:.1f}%")
        print(f"   Upload Rate: {stats['firebase']['upload_rate']:.1f}/s")
        
        print(f"\n⏱️  Uptime: {stats['uptime']:.1f}s")
        print("="*60 + "\n")


# ==================== MAIN ====================

def main():
    """Main function"""
    
    print("\n" + "="*60)
    print("INTEGRATED V2X SYSTEM WITH GPS AND FIREBASE")
    print("="*60 + "\n")
    
    # Create system
    system = IntegratedV2XSystem(
        vehicle_id="SDV001",
        gps_port=None,  # Auto-detect
        v2x_port='/dev/ttyUSB0',
        firebase_credentials='./firebase_credentials.json',
        firebase_url='https://YOUR_PROJECT_ID.firebaseio.com'  # UPDATE THIS!
    )
    
    # Connect all subsystems
    if not system.connect_all():
        logger.error("Failed to connect all subsystems. Exiting.")
        return
    
    # Start system
    if not system.start():
        logger.error("Failed to start system. Exiting.")
        return
    
    try:
        print("\n✓ System running. Press Ctrl+C to stop.\n")
        
        # Main loop - print status every 10 seconds
        while True:
            time.sleep(10)
            system.print_status()
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        system.stop()
        print("✓ System stopped")


if __name__ == "__main__":
    main()