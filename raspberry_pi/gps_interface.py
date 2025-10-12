#!/usr/bin/env python3
"""
GPS Ublox NEO-6M Interface for Raspberry Pi
Direct serial interface with GPS module
Location: ~/Graduation_Project_SDV/raspberry_pi/gps_interface.py

Features:
- NMEA sentence parsing (GGA, RMC, GSA, GSV)
- Auto port detection
- Data validation
- Threaded reading
- Callback system
- Data logging
"""

import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GPS_Interface')

# ==================== DATA STRUCTURES ====================

@dataclass
class GPSData:
    """GPS data structure"""
    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    
    # Velocity
    speed: float = 0.0  # km/h
    heading: float = 0.0  # degrees (course over ground)
    
    # Quality indicators
    fix_quality: int = 0  # 0=invalid, 1=GPS fix, 2=DGPS fix
    satellites_used: int = 0
    satellites_visible: int = 0
    hdop: float = 99.9  # Horizontal Dilution of Precision
    
    # Time
    utc_time: Optional[str] = None
    date: Optional[str] = None
    
    # Status
    valid: bool = False
    fix_type: str = "No Fix"  # No Fix, 2D Fix, 3D Fix
    
    # Raw data
    last_update: float = 0.0
    nmea_sentences_received: int = 0

# ==================== GPS INTERFACE ====================

class GPSInterface:
    """GPS Ublox NEO-6M Interface"""
    
    def __init__(self,
                 port: Optional[str] = None,
                 baudrate: int = 9600,
                 enable_logging: bool = False,
                 log_dir: str = "./logs"):
        """
        Initialize GPS interface
        
        Args:
            port: Serial port (auto-detect if None)
            baudrate: Baud rate (default 9600 for NEO-6M)
            enable_logging: Log GPS data to file
            log_dir: Directory for log files
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        
        # GPS data
        self.gps_data = GPSData()
        self.last_gga: Dict = {}
        self.last_rmc: Dict = {}
        self.last_gsa: Dict = {}
        
        # Threading
        self.running = False
        self.connected = False
        self.read_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.callbacks: List[Callable[[GPSData], None]] = []
        
        # Statistics
        self.stats = {
            'sentences_parsed': 0,
            'sentences_failed': 0,
            'checksum_errors': 0,
            'start_time': time.time()
        }
        
        # Data logging
        self.enable_logging = enable_logging
        self.log_dir = Path(log_dir)
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"gps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger.info("GPS Interface initialized")
    
    def find_gps_port(self) -> Optional[str]:
        """Auto-detect GPS module port"""
        logger.info("Scanning for GPS module...")
        
        ports = serial.tools.list_ports.comports()
        
        # Try common GPS identifiers
        gps_keywords = ['USB', 'ACM', 'SERIAL', 'GPS', 'UBLOX']
        
        for port in ports:
            port_desc = (port.device + ' ' + port.description).upper()
            if any(keyword in port_desc for keyword in gps_keywords):
                logger.info(f"Found potential GPS port: {port.device} - {port.description}")
                return port.device
        
        # If no specific match, try common ports
        common_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0', '/dev/serial0']
        for port_name in common_ports:
            try:
                test_port = serial.Serial(port_name, self.baudrate, timeout=1)
                test_port.close()
                logger.info(f"Found available port: {port_name}")
                return port_name
            except:
                continue
        
        logger.error("No GPS port found")
        return None
    
    def connect(self, retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Connect to GPS module
        
        Args:
            retries: Number of connection attempts
            retry_delay: Delay between retries
        """
        # Auto-detect port if not specified
        if not self.port:
            self.port = self.find_gps_port()
            if not self.port:
                logger.error("Could not find GPS port")
                return False
        
        for attempt in range(retries):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{retries} to {self.port}...")
                
                # Open serial port
                self.serial = serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=1
                )
                
                # Wait for GPS to initialize
                time.sleep(2)
                
                # Try to read some data
                test_data = self.serial.read(100)
                if b'$' in test_data:  # NMEA sentences start with $
                    logger.info(f"✓ Connected to GPS on {self.port}")
                    self.connected = True
                    return True
                else:
                    logger.warning("No NMEA data received")
                    self.serial.close()
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if self.serial and self.serial.is_open:
                    self.serial.close()
            
            if attempt < retries - 1:
                time.sleep(retry_delay)
        
        logger.error(f"Failed to connect to GPS after {retries} attempts")
        return False
    
    def disconnect(self):
        """Disconnect from GPS"""
        logger.info("Disconnecting GPS...")
        self.running = False
        self.connected = False
        
        if self.read_thread:
            self.read_thread.join(timeout=2)
        
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("GPS disconnected")
    
    def start_reading(self):
        """Start background thread for reading GPS data"""
        if self.running:
            return
        
        if not self.serial or not self.serial.is_open:
            logger.error("GPS not connected")
            return
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        logger.info("GPS reading thread started")
    
    def _read_loop(self):
        """Background thread for reading NMEA sentences"""
        buffer = ""
        
        while self.running:
            try:
                if self.serial.in_waiting > 0:
                    # Read available data
                    data = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                    buffer += data
                    
                    # Process complete sentences
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('$'):
                            self._parse_nmea_sentence(line)
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                self.stats['sentences_failed'] += 1
                time.sleep(0.1)
    
    def _parse_nmea_sentence(self, sentence: str):
        """Parse NMEA sentence"""
        try:
            # Verify checksum
            if not self._verify_checksum(sentence):
                self.stats['checksum_errors'] += 1
                return
            
            # Remove checksum
            if '*' in sentence:
                sentence = sentence.split('*')[0]
            
            # Split sentence
            parts = sentence.split(',')
            sentence_type = parts[0]
            
            # Parse based on type
            if sentence_type == '$GPGGA' or sentence_type == '$GNGGA':
                self._parse_gga(parts)
            elif sentence_type == '$GPRMC' or sentence_type == '$GNRMC':
                self._parse_rmc(parts)
            elif sentence_type == '$GPGSA' or sentence_type == '$GNGSA':
                self._parse_gsa(parts)
            elif sentence_type == '$GPGSV' or sentence_type == '$GNGSV':
                self._parse_gsv(parts)
            
            self.stats['sentences_parsed'] += 1
            self.gps_data.nmea_sentences_received += 1
            self.gps_data.last_update = time.time()
            
            # Update callbacks
            if self.gps_data.valid:
                self._trigger_callbacks()
            
            # Log data
            if self.enable_logging:
                self._log_data(sentence)
                
        except Exception as e:
            logger.debug(f"Error parsing sentence: {e}")
            self.stats['sentences_failed'] += 1
    
    def _parse_gga(self, parts: List[str]):
        """Parse GGA sentence (Global Positioning System Fix Data)"""
        try:
            self.gps_data.utc_time = parts[1] if len(parts) > 1 else None
            
            # Latitude
            if len(parts) > 2 and parts[2]:
                lat = float(parts[2][:2]) + float(parts[2][2:]) / 60.0
                if parts[3] == 'S':
                    lat = -lat
                self.gps_data.latitude = lat
            
            # Longitude
            if len(parts) > 4 and parts[4]:
                lon = float(parts[4][:3]) + float(parts[4][3:]) / 60.0
                if parts[5] == 'W':
                    lon = -lon
                self.gps_data.longitude = lon
            
            # Fix quality
            if len(parts) > 6:
                self.gps_data.fix_quality = int(parts[6]) if parts[6] else 0
                self.gps_data.valid = self.gps_data.fix_quality > 0
            
            # Satellites
            if len(parts) > 7:
                self.gps_data.satellites_used = int(parts[7]) if parts[7] else 0
            
            # HDOP
            if len(parts) > 8:
                self.gps_data.hdop = float(parts[8]) if parts[8] else 99.9
            
            # Altitude
            if len(parts) > 9:
                self.gps_data.altitude = float(parts[9]) if parts[9] else 0.0
            
            self.last_gga = {
                'time': self.gps_data.utc_time,
                'lat': self.gps_data.latitude,
                'lon': self.gps_data.longitude,
                'alt': self.gps_data.altitude,
                'sats': self.gps_data.satellites_used
            }
            
        except Exception as e:
            logger.debug(f"Error parsing GGA: {e}")
    
    def _parse_rmc(self, parts: List[str]):
        """Parse RMC sentence (Recommended Minimum Specific GPS/Transit Data)"""
        try:
            # Status
            if len(parts) > 2:
                status = parts[2]
                self.gps_data.valid = (status == 'A')
            
            # Latitude
            if len(parts) > 3 and parts[3]:
                lat = float(parts[3][:2]) + float(parts[3][2:]) / 60.0
                if parts[4] == 'S':
                    lat = -lat
                self.gps_data.latitude = lat
            
            # Longitude
            if len(parts) > 5 and parts[5]:
                lon = float(parts[5][:3]) + float(parts[5][3:]) / 60.0
                if parts[6] == 'W':
                    lon = -lon
                self.gps_data.longitude = lon
            
            # Speed (knots to km/h)
            if len(parts) > 7 and parts[7]:
                speed_knots = float(parts[7])
                self.gps_data.speed = speed_knots * 1.852
            
            # Heading
            if len(parts) > 8 and parts[8]:
                self.gps_data.heading = float(parts[8])
            
            # Date
            if len(parts) > 9:
                self.gps_data.date = parts[9] if parts[9] else None
            
            self.last_rmc = {
                'speed': self.gps_data.speed,
                'heading': self.gps_data.heading,
                'date': self.gps_data.date
            }
            
        except Exception as e:
            logger.debug(f"Error parsing RMC: {e}")
    
    def _parse_gsa(self, parts: List[str]):
        """Parse GSA sentence (GPS DOP and Active Satellites)"""
        try:
            # Fix type: 1=no fix, 2=2D, 3=3D
            if len(parts) > 2:
                fix_type = int(parts[2]) if parts[2] else 1
                if fix_type == 1:
                    self.gps_data.fix_type = "No Fix"
                elif fix_type == 2:
                    self.gps_data.fix_type = "2D Fix"
                elif fix_type == 3:
                    self.gps_data.fix_type = "3D Fix"
            
            # HDOP
            if len(parts) > 16 and parts[16]:
                self.gps_data.hdop = float(parts[16])
            
            self.last_gsa = {
                'fix_type': self.gps_data.fix_type,
                'hdop': self.gps_data.hdop
            }
            
        except Exception as e:
            logger.debug(f"Error parsing GSA: {e}")
    
    def _parse_gsv(self, parts: List[str]):
        """Parse GSV sentence (Satellites in View)"""
        try:
            # Total satellites in view
            if len(parts) > 3 and parts[3]:
                self.gps_data.satellites_visible = int(parts[3])
        except Exception as e:
            logger.debug(f"Error parsing GSV: {e}")
    
    def _verify_checksum(self, sentence: str) -> bool:
        """Verify NMEA sentence checksum"""
        if '*' not in sentence:
            return False
        
        try:
            data, checksum = sentence.split('*')
            data = data[1:]  # Remove $
            
            calculated = 0
            for char in data:
                calculated ^= ord(char)
            
            return calculated == int(checksum, 16)
        except:
            return False
    
    def get_data(self) -> GPSData:
        """Get current GPS data"""
        return self.gps_data
    
    def is_valid(self) -> bool:
        """Check if GPS has valid fix"""
        return self.gps_data.valid and self.gps_data.fix_quality > 0
    
    def wait_for_fix(self, timeout: float = 60.0) -> bool:
        """Wait for GPS to get valid fix"""
        logger.info("Waiting for GPS fix...")
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.is_valid():
                logger.info(f"✓ GPS fix acquired in {time.time() - start_time:.1f}s")
                logger.info(f"   Position: {self.gps_data.latitude:.6f}, {self.gps_data.longitude:.6f}")
                logger.info(f"   Satellites: {self.gps_data.satellites_used}, HDOP: {self.gps_data.hdop:.1f}")
                return True
            time.sleep(0.5)
        
        logger.warning(f"GPS fix timeout after {timeout}s")
        return False
    
    def register_callback(self, callback: Callable[[GPSData], None]):
        """Register callback for GPS data updates"""
        self.callbacks.append(callback)
        logger.info("GPS callback registered")
    
    def _trigger_callbacks(self):
        """Trigger all registered callbacks"""
        for callback in self.callbacks:
            try:
                callback(self.gps_data)
            except Exception as e:
                logger.error(f"Error in GPS callback: {e}")
    
    def _log_data(self, sentence: str):
        """Log GPS data to file"""
        try:
            with open(self.log_file, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"{timestamp} | {sentence}\n")
        except Exception as e:
            logger.error(f"Failed to log GPS data: {e}")
    
    def get_statistics(self) -> Dict:
        """Get GPS statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            'connected': self.connected,
            'valid_fix': self.is_valid(),
            'sentences_parsed': self.stats['sentences_parsed'],
            'sentences_failed': self.stats['sentences_failed'],
            'checksum_errors': self.stats['checksum_errors'],
            'uptime': uptime,
            'parse_rate': self.stats['sentences_parsed'] / max(1, uptime)
        }
    
    def calculate_distance_to(self, target_lat: float, target_lon: float) -> float:
        """Calculate distance to target position in meters"""
        if not self.is_valid():
            return -1.0
        
        return self._haversine_distance(
            self.gps_data.latitude,
            self.gps_data.longitude,
            target_lat,
            target_lon
        )
    
    def calculate_bearing_to(self, target_lat: float, target_lon: float) -> float:
        """Calculate bearing to target position in degrees"""
        if not self.is_valid():
            return -1.0
        
        lat1 = math.radians(self.gps_data.latitude)
        lat2 = math.radians(target_lat)
        lon_diff = math.radians(target_lon - self.gps_data.longitude)
        
        x = math.sin(lon_diff) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon_diff)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return distance

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage"""
    
    # Create GPS interface with auto-detection
    gps = GPSInterface(
        port=None,  # Auto-detect
        baudrate=9600,
        enable_logging=True
    )
    
    # Register callback
    def on_gps_update(data: GPSData):
        if data.valid:
            print(f"\r📍 GPS: {data.latitude:.6f}, {data.longitude:.6f} | "
                  f"Speed: {data.speed:.1f} km/h | "
                  f"Heading: {data.heading:.1f}° | "
                  f"Sats: {data.satellites_used}/{data.satellites_visible} | "
                  f"Fix: {data.fix_type}", end='')
    
    gps.register_callback(on_gps_update)
    
    # Connect
    if not gps.connect():
        print("Failed to connect to GPS")
        return
    
    # Start reading
    gps.start_reading()
    
    # Wait for fix
    if not gps.wait_for_fix(timeout=60):
        print("No GPS fix - continuing anyway...")
    
    try:
        print("\nGPS monitoring started (Ctrl+C to stop)")
        
        while True:
            time.sleep(1)
            
            # Print statistics every 10 seconds
            if int(time.time()) % 10 == 0:
                stats = gps.get_statistics()
                print(f"\n\nStatistics:")
                print(f"  Valid Fix: {stats['valid_fix']}")
                print(f"  Sentences Parsed: {stats['sentences_parsed']}")
                print(f"  Parse Rate: {stats['parse_rate']:.1f} msg/s")
                print(f"  Checksum Errors: {stats['checksum_errors']}")
                
                # Example: Calculate distance to a waypoint
                # target_lat, target_lon = 30.0500, 31.2400
                # distance = gps.calculate_distance_to(target_lat, target_lon)
                # bearing = gps.calculate_bearing_to(target_lat, target_lon)
                # print(f"  Distance to waypoint: {distance:.1f}m, Bearing: {bearing:.1f}°")
                
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping GPS...")
    finally:
        gps.disconnect()
        print("GPS stopped")

if __name__ == "__main__":
    main()