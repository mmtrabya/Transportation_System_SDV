#!/usr/bin/env python3
"""
Raspberry Pi V2X Communication Interface
Handles communication with ESP32 V2X module via Serial
"""

import serial
import json
import time
import threading
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('V2X_Interface')

# ==================== DATA CLASSES ====================

@dataclass
class VehicleState:
    """Current vehicle state"""
    latitude: float
    longitude: float
    altitude: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    acceleration: float = 0.0
    braking_status: int = 0
    emergency_active: bool = False
    emergency_type: int = 0

@dataclass
class NearbyVehicle:
    """Information about a nearby vehicle"""
    vehicle_id: str
    latitude: float
    longitude: float
    speed: float
    heading: float = 0.0
    last_seen: float = 0.0
    is_emergency: bool = False
    distance: float = 0.0  # Calculated distance from our vehicle

@dataclass
class HazardWarning:
    """Hazard warning from another vehicle"""
    vehicle_id: str
    hazard_type: int  # 1=accident, 2=ice, 3=construction, 4=debris
    latitude: float
    longitude: float
    description: str
    timestamp: float
    distance: float = 0.0

@dataclass
class TrafficSignal:
    """Traffic signal information"""
    intersection_id: str
    current_phase: int  # 0=red, 1=yellow, 2=green
    time_remaining: int
    next_phase: int
    timestamp: float

@dataclass
class V2XStatistics:
    """V2X communication statistics"""
    bsm_sent: int = 0
    bsm_received: int = 0
    hazards_received: int = 0
    emergencies_received: int = 0
    packets_dropped: int = 0
    nearby_vehicles: int = 0

# ==================== V2X INTERFACE CLASS ====================

class V2XInterface:
    """Main V2X communication interface"""
    
    def __init__(self, serial_port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        
        # Data storage
        self.vehicle_state = VehicleState(30.0444, 31.2357)
        self.nearby_vehicles: Dict[str, NearbyVehicle] = {}
        self.hazard_warnings: List[HazardWarning] = []
        self.traffic_signals: Dict[str, TrafficSignal] = {}
        self.statistics = V2XStatistics()
        
        # Threading
        self.running = False
        self.read_thread: Optional[threading.Thread] = None
        self.update_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.callbacks = {
            'bsm_received': [],
            'hazard_received': [],
            'emergency_received': [],
            'signal_received': []
        }
        
        # Timing
        self.last_update_time = time.time()
        self.update_interval = 0.1  # 10Hz updates to ESP32
    
    def connect(self) -> bool:
        """Connect to ESP32 via serial"""
        try:
            self.serial_conn = serial.Serial(
                self.serial_port,
                self.baudrate,
                timeout=1
            )
            logger.info(f"Connected to ESP32 on {self.serial_port}")
            time.sleep(2)  # Wait for ESP32 to initialize
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ESP32: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from ESP32"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        if self.update_thread:
            self.update_thread.join(timeout=2)
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from ESP32")
    
    def start(self):
        """Start communication threads"""
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return False
        
        self.running = True
        
        # Start read thread
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info("V2X Interface started")
        return True
    
    def _read_loop(self):
        """Read data from ESP32"""
        while self.running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        self._parse_message(line)
            except Exception as e:
                logger.error(f"Error reading from serial: {e}")
                time.sleep(0.1)
    
    def _update_loop(self):
        """Send vehicle state updates to ESP32"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_update_time >= self.update_interval:
                    self._send_vehicle_update()
                    self.last_update_time = current_time
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(0.1)
    
    def _parse_message(self, message: str):
        """Parse incoming message from ESP32"""
        try:
            if message.startswith("V2V_BSM:"):
                self._handle_bsm(message[8:])
            elif message.startswith("V2V_HAZARD:"):
                self._handle_hazard(message[11:])
            elif message.startswith("V2V_EMERGENCY:"):
                self._handle_emergency(message[14:])
            elif message.startswith("SIGNAL:"):
                self._handle_signal(message[7:])
            elif message.startswith("==="):
                logger.info(message)
            else:
                logger.debug(f"Unknown message: {message}")
        except Exception as e:
            logger.error(f"Error parsing message '{message}': {e}")
    
    def _handle_bsm(self, data: str):
        """Handle Basic Safety Message"""
        try:
            parts = data.split(',')
            vehicle_id = parts[0]
            latitude = float(parts[1])
            longitude = float(parts[2])
            speed = float(parts[3])
            
            # Calculate distance from our vehicle
            distance = self._calculate_distance(
                self.vehicle_state.latitude,
                self.vehicle_state.longitude,
                latitude,
                longitude
            )
            
            # Update or create nearby vehicle entry
            self.nearby_vehicles[vehicle_id] = NearbyVehicle(
                vehicle_id=vehicle_id,
                latitude=latitude,
                longitude=longitude,
                speed=speed,
                last_seen=time.time(),
                distance=distance
            )
            
            # Trigger callbacks
            self._trigger_callback('bsm_received', self.nearby_vehicles[vehicle_id])
            
            logger.debug(f"BSM from {vehicle_id}: {distance:.1f}m away, {speed:.1f} km/h")
            
        except Exception as e:
            logger.error(f"Error handling BSM: {e}")
    
    def _handle_hazard(self, data: str):
        """Handle Hazard Warning"""
        try:
            parts = data.split(',')
            vehicle_id = parts[0]
            hazard_type = int(parts[1])
            latitude = float(parts[2])
            longitude = float(parts[3])
            description = parts[4] if len(parts) > 4 else "Unknown hazard"
            
            distance = self._calculate_distance(
                self.vehicle_state.latitude,
                self.vehicle_state.longitude,
                latitude,
                longitude
            )
            
            hazard = HazardWarning(
                vehicle_id=vehicle_id,
                hazard_type=hazard_type,
                latitude=latitude,
                longitude=longitude,
                description=description,
                timestamp=time.time(),
                distance=distance
            )
            
            self.hazard_warnings.append(hazard)
            
            # Keep only recent hazards (last 10 minutes)
            self.hazard_warnings = [
                h for h in self.hazard_warnings
                if time.time() - h.timestamp < 600
            ]
            
            self._trigger_callback('hazard_received', hazard)
            
            hazard_types = {1: "Accident", 2: "Ice", 3: "Construction", 4: "Debris"}
            logger.warning(
                f"HAZARD ALERT: {hazard_types.get(hazard_type, 'Unknown')} "
                f"{distance:.0f}m ahead - {description}"
            )
            
        except Exception as e:
            logger.error(f"Error handling hazard: {e}")
    
    def _handle_emergency(self, data: str):
        """Handle Emergency Vehicle Alert"""
        try:
            parts = data.split(',')
            vehicle_id = parts[0]
            emergency_type = int(parts[1])
            latitude = float(parts[2])
            longitude = float(parts[3])
            
            distance = self._calculate_distance(
                self.vehicle_state.latitude,
                self.vehicle_state.longitude,
                latitude,
                longitude
            )
            
            # Mark vehicle as emergency
            if vehicle_id in self.nearby_vehicles:
                self.nearby_vehicles[vehicle_id].is_emergency = True
            
            emergency_types = {1: "Ambulance", 2: "Fire Truck", 3: "Police"}
            logger.warning(
                f"EMERGENCY VEHICLE: {emergency_types.get(emergency_type, 'Unknown')} "
                f"{distance:.0f}m away - CLEAR THE WAY!"
            )
            
            self._trigger_callback('emergency_received', {
                'vehicle_id': vehicle_id,
                'type': emergency_type,
                'distance': distance
            })
            
        except Exception as e:
            logger.error(f"Error handling emergency: {e}")
    
    def _handle_signal(self, data: str):
        """Handle Traffic Signal information"""
        try:
            parts = data.split(',')
            intersection_id = parts[0]
            current_phase = int(parts[1])
            time_remaining = int(parts[2])
            
            signal = TrafficSignal(
                intersection_id=intersection_id,
                current_phase=current_phase,
                time_remaining=time_remaining,
                next_phase=(current_phase + 1) % 3,
                timestamp=time.time()
            )
            
            self.traffic_signals[intersection_id] = signal
            
            phases = {0: "RED", 1: "YELLOW", 2: "GREEN"}
            logger.info(
                f"Traffic Signal [{intersection_id}]: {phases[current_phase]} "
                f"for {time_remaining}s"
            )
            
            self._trigger_callback('signal_received', signal)
            
        except Exception as e:
            logger.error(f"Error handling signal: {e}")
    
    def _send_vehicle_update(self):
        """Send vehicle state update to ESP32"""
        try:
            message = f"UPDATE:{self.vehicle_state.latitude:.6f}," \
                     f"{self.vehicle_state.longitude:.6f}," \
                     f"{self.vehicle_state.speed:.2f}," \
                     f"{self.vehicle_state.heading:.2f}," \
                     f"{self.vehicle_state.acceleration:.2f}\n"
            
            self.serial_conn.write(message.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error sending vehicle update: {e}")
    
    def update_vehicle_state(self, **kwargs):
        """Update vehicle state from ADAS/localization system"""
        for key, value in kwargs.items():
            if hasattr(self.vehicle_state, key):
                setattr(self.vehicle_state, key, value)
    
    def send_hazard_warning(self, hazard_type: int, description: str):
        """Send hazard warning to nearby vehicles"""
        try:
            message = f"HAZARD:{hazard_type},{description}\n"
            self.serial_conn.write(message.encode('utf-8'))
            logger.info(f"Sent hazard warning: {description}")
        except Exception as e:
            logger.error(f"Error sending hazard warning: {e}")
    
    def send_emergency_alert(self):
        """Activate emergency vehicle alert"""
        try:
            message = "EMERGENCY\n"
            self.serial_conn.write(message.encode('utf-8'))
            self.vehicle_state.emergency_active = True
            logger.warning("Emergency alert activated!")
        except Exception as e:
            logger.error(f"Error sending emergency alert: {e}")
    
    def request_statistics(self):
        """Request statistics from ESP32"""
        try:
            self.serial_conn.write(b"STATS\n")
        except Exception as e:
            logger.error(f"Error requesting statistics: {e}")
    
    def get_nearby_vehicles(self, max_distance: float = None) -> List[NearbyVehicle]:
        """Get list of nearby vehicles, optionally filtered by distance"""
        current_time = time.time()
        
        # Remove stale vehicles (not seen for 5 seconds)
        self.nearby_vehicles = {
            vid: vehicle for vid, vehicle in self.nearby_vehicles.items()
            if current_time - vehicle.last_seen < 5.0
        }
        
        vehicles = list(self.nearby_vehicles.values())
        
        if max_distance is not None:
            vehicles = [v for v in vehicles if v.distance <= max_distance]
        
        # Sort by distance
        vehicles.sort(key=lambda v: v.distance)
        
        return vehicles
    
    def get_hazards_ahead(self, max_distance: float = 500.0) -> List[HazardWarning]:
        """Get hazards ahead of vehicle within specified distance"""
        hazards = [h for h in self.hazard_warnings if h.distance <= max_distance]
        hazards.sort(key=lambda h: h.distance)
        return hazards
    
    def get_emergency_vehicles_nearby(self, max_distance: float = 200.0) -> List[NearbyVehicle]:
        """Get emergency vehicles within specified distance"""
        vehicles = self.get_nearby_vehicles(max_distance)
        return [v for v in vehicles if v.is_emergency]
    
    def register_callback(self, event_type: str, callback):
        """Register callback for V2X events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    def _trigger_callback(self, event_type: str, data):
        """Trigger all callbacks for an event"""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        return distance
    
    def get_status_summary(self) -> Dict:
        """Get comprehensive status summary"""
        return {
            'vehicle_state': asdict(self.vehicle_state),
            'nearby_vehicles_count': len(self.nearby_vehicles),
            'emergency_vehicles_nearby': len(self.get_emergency_vehicles_nearby()),
            'hazards_count': len(self.hazard_warnings),
            'traffic_signals_count': len(self.traffic_signals),
            'statistics': asdict(self.statistics)
        }


# ==================== EXAMPLE USAGE ====================

def on_bsm_received(vehicle: NearbyVehicle):
    """Callback when BSM is received"""
    if vehicle.distance < 50:  # Within 50 meters
        print(f"⚠️  Close vehicle: {vehicle.vehicle_id} at {vehicle.distance:.1f}m")

def on_hazard_received(hazard: HazardWarning):
    """Callback when hazard warning is received"""
    print(f"🚨 HAZARD: {hazard.description} at {hazard.distance:.0f}m")

def on_emergency_received(data: Dict):
    """Callback when emergency vehicle is detected"""
    print(f"🚑 EMERGENCY VEHICLE {data['distance']:.0f}m away - YIELD!")

def main():
    """Example main function"""
    # Initialize V2X interface
    v2x = V2XInterface(serial_port='/dev/ttyUSB0', baudrate=115200)
    
    # Register callbacks
    v2x.register_callback('bsm_received', on_bsm_received)
    v2x.register_callback('hazard_received', on_hazard_received)
    v2x.register_callback('emergency_received', on_emergency_received)
    
    # Connect and start
    if v2x.connect():
        v2x.start()
        
        try:
            while True:
                # Update vehicle state (from your ADAS/GPS system)
                v2x.update_vehicle_state(
                    latitude=30.0444,
                    longitude=31.2357,
                    speed=25.5,
                    heading=45.0,
                    acceleration=0.5
                )
                
                # Check for nearby vehicles
                nearby = v2x.get_nearby_vehicles(max_distance=100)
                if nearby:
                    print(f"\n📍 {len(nearby)} vehicles within 100m:")
                    for vehicle in nearby[:5]:  # Show top 5
                        print(f"   {vehicle.vehicle_id}: {vehicle.distance:.1f}m, "
                              f"{vehicle.speed:.1f} km/h")
                
                # Check for hazards ahead
                hazards = v2x.get_hazards_ahead(max_distance=500)
                if hazards:
                    print(f"\n⚠️  {len(hazards)} hazards ahead:")
                    for hazard in hazards:
                        print(f"   {hazard.description} at {hazard.distance:.0f}m")
                
                # Check for emergency vehicles
                emergency_vehicles = v2x.get_emergency_vehicles_nearby(max_distance=200)
                if emergency_vehicles:
                    print(f"\n🚑 {len(emergency_vehicles)} emergency vehicles nearby!")
                
                # Example: Send hazard if we detect something
                # v2x.send_hazard_warning(hazard_type=4, description="Debris on road")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            v2x.disconnect()
    else:
        print("Failed to connect to ESP32")

if __name__ == "__main__":
    main()