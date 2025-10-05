#!/usr/bin/env python3
"""
ATmega32 Interface for Raspberry Pi - Enhanced Version
Handles serial communication with ATmega32 microcontroller
Location: ~/Graduation_Project_SDV/raspberry_pi/atmega32_interface.py

Enhancements:
- Struct size validation
- Auto port detection
- Connection retry logic
- Response timeout handling
- Reconnection on disconnect
- Heartbeat monitoring
- Data logging option
"""

import serial
import serial.tools.list_ports
import struct
import time
import threading
from typing import Optional, Tuple, Callable, Dict, List
from dataclasses import dataclass
from enum import IntEnum
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ATmega32_Interface')

# ==================== PROTOCOL DEFINITION ====================

class CommandCode(IntEnum):
    """Command codes for ATmega32 communication"""
    # Motor control
    CMD_MOTOR_SET_SPEED = 0x01
    CMD_MOTOR_STOP = 0x02
    CMD_MOTOR_EMERGENCY_STOP = 0x03
    
    # Sensor requests
    CMD_GPS_REQUEST = 0x10
    CMD_IMU_REQUEST = 0x11
    CMD_ULTRASONIC_REQUEST = 0x12
    CMD_ALL_SENSORS_REQUEST = 0x13
    
    # System control
    CMD_LED_CONTROL = 0x20
    CMD_BUZZER_CONTROL = 0x21
    CMD_SYSTEM_STATUS = 0x22
    CMD_RESET = 0x23
    
    # Responses (from ATmega32)
    RESP_ACK = 0xA0
    RESP_NACK = 0xA1
    RESP_GPS_DATA = 0xB0
    RESP_IMU_DATA = 0xB1
    RESP_ULTRASONIC_DATA = 0xB2
    RESP_ALL_SENSORS_DATA = 0xB3
    RESP_SYSTEM_STATUS = 0xB4

class ProtocolConstants:
    """Protocol constants"""
    START_BYTE = 0xAA
    END_BYTE = 0x55
    MAX_DATA_LENGTH = 64
    TIMEOUT = 1.0  # seconds
    
    # Expected struct sizes (must match C structs)
    GPS_SIZE = 19       # 4f + 3B
    IMU_SIZE = 48       # 12f
    ULTRASONIC_SIZE = 16  # 4f
    SYSTEM_STATUS_SIZE = 10  # If + 2B

# ==================== DATA STRUCTURES ====================

@dataclass
class GPSData:
    """GPS data structure (19 bytes)"""
    latitude: float
    longitude: float
    altitude: float
    speed: float
    satellites: int
    fix_quality: int
    valid: bool

@dataclass
class IMUData:
    """IMU 9DOF data structure (48 bytes)"""
    # Accelerometer (m/s²)
    accel_x: float
    accel_y: float
    accel_z: float
    
    # Gyroscope (deg/s)
    gyro_x: float
    gyro_y: float
    gyro_z: float
    
    # Magnetometer (µT)
    mag_x: float
    mag_y: float
    mag_z: float
    
    # Calculated orientation (degrees)
    roll: float
    pitch: float
    yaw: float

@dataclass
class UltrasonicData:
    """Ultrasonic sensor data (16 bytes)"""
    front: float  # cm
    rear: float   # cm
    left: float   # cm
    right: float  # cm

@dataclass
class SystemStatus:
    """ATmega32 system status (10 bytes)"""
    uptime: int  # seconds
    battery_voltage: float  # volts
    cpu_load: int  # percentage
    errors: int

# ==================== PACKET STRUCTURE ====================

class Packet:
    """
    Packet structure:
    [START] [CMD] [LENGTH] [DATA...] [CHECKSUM] [END]
    
    START: 1 byte (0xAA)
    CMD: 1 byte (command code)
    LENGTH: 1 byte (data length, 0-64)
    DATA: 0-64 bytes
    CHECKSUM: 1 byte (sum of CMD+LENGTH+DATA)
    END: 1 byte (0x55)
    """
    
    @staticmethod
    def create(cmd: int, data: bytes = b'') -> bytes:
        """Create packet from command and data"""
        if len(data) > ProtocolConstants.MAX_DATA_LENGTH:
            raise ValueError(f"Data too long: {len(data)} > {ProtocolConstants.MAX_DATA_LENGTH}")
        
        packet = bytearray()
        packet.append(ProtocolConstants.START_BYTE)
        packet.append(cmd)
        packet.append(len(data))
        packet.extend(data)
        
        # Calculate checksum
        checksum = (cmd + len(data) + sum(data)) & 0xFF
        packet.append(checksum)
        packet.append(ProtocolConstants.END_BYTE)
        
        return bytes(packet)
    
    @staticmethod
    def parse(raw_data: bytes) -> Optional[Tuple[int, bytes]]:
        """Parse received packet, returns (cmd, data) or None"""
        if len(raw_data) < 5:  # Minimum packet size
            return None
        
        # Check start and end bytes
        if raw_data[0] != ProtocolConstants.START_BYTE:
            return None
        if raw_data[-1] != ProtocolConstants.END_BYTE:
            return None
        
        cmd = raw_data[1]
        length = raw_data[2]
        
        # Check length
        if len(raw_data) != length + 5:  # START+CMD+LEN+DATA+CHK+END
            return None
        
        data = raw_data[3:3+length]
        received_checksum = raw_data[3+length]
        
        # Verify checksum
        calculated_checksum = (cmd + length + sum(data)) & 0xFF
        if received_checksum != calculated_checksum:
            logger.warning("Checksum mismatch")
            return None
        
        return cmd, data

# ==================== PORT DETECTION ====================

def find_atmega_ports() -> List[str]:
    """Auto-detect potential ATmega32 serial ports"""
    ports = []
    for port in serial.tools.list_ports.comports():
        # Look for USB-Serial devices (FTDI, CH340, CP210x, etc.)
        if any(keyword in port.device.upper() for keyword in ['USB', 'ACM', 'SERIAL']):
            ports.append(port.device)
            logger.info(f"Found potential port: {port.device} - {port.description}")
    
    return ports

# ==================== ATMEGA32 INTERFACE ====================

class ATmega32Interface:
    """Enhanced interface for communicating with ATmega32"""
    
    def __init__(self, 
                 port: Optional[str] = None, 
                 baudrate: int = 115200,
                 auto_reconnect: bool = True,
                 enable_logging: bool = False,
                 log_dir: str = "./logs"):
        """
        Initialize ATmega32 interface
        
        Args:
            port: Serial port (default: auto-detect)
            baudrate: Baud rate (default: 115200)
            auto_reconnect: Automatically reconnect on disconnect
            enable_logging: Log all data to files
            log_dir: Directory for log files
        """
        self.port = port
        self.baudrate = baudrate
        self.auto_reconnect = auto_reconnect
        self.serial: Optional[serial.Serial] = None
        
        # Latest sensor data
        self.gps_data: Optional[GPSData] = None
        self.imu_data: Optional[IMUData] = None
        self.ultrasonic_data: Optional[UltrasonicData] = None
        self.system_status: Optional[SystemStatus] = None
        
        # Response events for synchronous requests
        self.response_events: Dict[int, threading.Event] = {}
        self.response_data: Dict[int, any] = {}
        
        # Callbacks
        self.callbacks: Dict[int, list] = {}
        
        # Threading
        self.running = False
        self.connected = False
        self.read_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.errors = 0
        self.last_heartbeat = time.time()
        
        # Data logging
        self.enable_logging = enable_logging
        self.log_dir = Path(log_dir)
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"atmega32_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger.info(f"ATmega32 Interface initialized")
    
    def connect(self, retries: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Connect to ATmega32 with retries
        
        Args:
            retries: Number of connection attempts
            retry_delay: Delay between retries (seconds)
        """
        # Auto-detect port if not specified
        if not self.port:
            ports = find_atmega_ports()
            if not ports:
                logger.error("No serial ports found")
                return False
            self.port = ports[0]
            logger.info(f"Auto-selected port: {self.port}")
        
        for attempt in range(retries):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{retries}...")
                
                # Open serial port
                self.serial = serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=ProtocolConstants.TIMEOUT,
                    write_timeout=ProtocolConstants.TIMEOUT
                )
                time.sleep(2)  # Wait for connection to stabilize
                
                # Test connection with system status request
                self.start_reading()  # Start reading thread first
                time.sleep(0.5)
                
                if self.request_system_status(timeout=2.0):
                    logger.info(f"✓ Connected to ATmega32 on {self.port}")
                    self.connected = True
                    
                    # Start heartbeat monitoring
                    self._start_heartbeat()
                    
                    return True
                else:
                    logger.warning("No response from ATmega32")
                    self.serial.close()
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if self.serial and self.serial.is_open:
                    self.serial.close()
                
            if attempt < retries - 1:
                time.sleep(retry_delay)
        
        logger.error(f"Failed to connect to ATmega32 after {retries} attempts")
        return False
    
    def disconnect(self):
        """Disconnect from ATmega32"""
        logger.info("Disconnecting...")
        self.running = False
        self.connected = False
        
        # Wait for threads
        if self.read_thread:
            self.read_thread.join(timeout=2)
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        
        # Close serial port
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Disconnected from ATmega32")
    
    def start_reading(self):
        """Start background thread for reading responses"""
        if self.running:
            return
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        logger.info("Started reading thread")
    
    def _read_loop(self):
        """Background thread for reading responses"""
        buffer = bytearray()
        
        while self.running:
            try:
                if not self.serial or not self.serial.is_open:
                    if self.auto_reconnect:
                        logger.warning("Serial connection lost, attempting reconnect...")
                        time.sleep(2)
                        if self.connect(retries=3):
                            continue
                    break
                
                if self.serial.in_waiting > 0:
                    # Read available data
                    data = self.serial.read(self.serial.in_waiting)
                    buffer.extend(data)
                    
                    # Look for complete packets
                    while len(buffer) >= 5:
                        # Find start byte
                        start_idx = buffer.find(ProtocolConstants.START_BYTE)
                        if start_idx == -1:
                            buffer.clear()
                            break
                        
                        # Remove data before start byte
                        if start_idx > 0:
                            buffer = buffer[start_idx:]
                        
                        # Check if we have enough data for length field
                        if len(buffer) < 3:
                            break
                        
                        length = buffer[2]
                        packet_size = length + 5
                        
                        # Check if we have complete packet
                        if len(buffer) < packet_size:
                            break
                        
                        # Extract packet
                        packet_data = bytes(buffer[:packet_size])
                        buffer = buffer[packet_size:]
                        
                        # Parse packet
                        result = Packet.parse(packet_data)
                        if result:
                            cmd, data = result
                            self.packets_received += 1
                            self._handle_response(cmd, data)
                        else:
                            self.errors += 1
                
                time.sleep(0.01)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                self.errors += 1
                time.sleep(0.1)
    
    def _handle_response(self, cmd: int, data: bytes):
        """Handle received response from ATmega32"""
        try:
            self.last_heartbeat = time.time()  # Update heartbeat
            
            if cmd == CommandCode.RESP_GPS_DATA:
                self.gps_data = self._parse_gps_data(data)
                self._log_data("GPS", self.gps_data)
                self._signal_response(cmd, self.gps_data)
                self._trigger_callbacks(cmd, self.gps_data)
                
            elif cmd == CommandCode.RESP_IMU_DATA:
                self.imu_data = self._parse_imu_data(data)
                self._log_data("IMU", self.imu_data)
                self._signal_response(cmd, self.imu_data)
                self._trigger_callbacks(cmd, self.imu_data)
                
            elif cmd == CommandCode.RESP_ULTRASONIC_DATA:
                self.ultrasonic_data = self._parse_ultrasonic_data(data)
                self._log_data("ULTRASONIC", self.ultrasonic_data)
                self._signal_response(cmd, self.ultrasonic_data)
                self._trigger_callbacks(cmd, self.ultrasonic_data)
                
            elif cmd == CommandCode.RESP_SYSTEM_STATUS:
                self.system_status = self._parse_system_status(data)
                self._log_data("STATUS", self.system_status)
                self._signal_response(cmd, self.system_status)
                self._trigger_callbacks(cmd, self.system_status)
                
            elif cmd == CommandCode.RESP_ACK:
                logger.debug("Received ACK")
                self._signal_response(cmd, True)
                
            elif cmd == CommandCode.RESP_NACK:
                logger.warning("Received NACK")
                self._signal_response(cmd, False)
                
        except Exception as e:
            logger.error(f"Error handling response: {e}")
            self.errors += 1
    
    # ==================== PARSING FUNCTIONS ====================
    
    def _parse_gps_data(self, data: bytes) -> GPSData:
        """Parse GPS data from bytes"""
        if len(data) != ProtocolConstants.GPS_SIZE:
            raise ValueError(f"GPS data size mismatch: expected {ProtocolConstants.GPS_SIZE}, got {len(data)}")
        
        # Format: lat(f), lon(f), alt(f), speed(f), sats(B), fix(B), valid(B)
        values = struct.unpack('<ffffBBB', data)
        return GPSData(
            latitude=values[0],
            longitude=values[1],
            altitude=values[2],
            speed=values[3],
            satellites=values[4],
            fix_quality=values[5],
            valid=bool(values[6])
        )
    
    def _parse_imu_data(self, data: bytes) -> IMUData:
        """Parse IMU data from bytes"""
        if len(data) != ProtocolConstants.IMU_SIZE:
            raise ValueError(f"IMU data size mismatch: expected {ProtocolConstants.IMU_SIZE}, got {len(data)}")
        
        # Format: 12 floats (accel x,y,z, gyro x,y,z, mag x,y,z, roll, pitch, yaw)
        values = struct.unpack('<12f', data)
        return IMUData(
            accel_x=values[0], accel_y=values[1], accel_z=values[2],
            gyro_x=values[3], gyro_y=values[4], gyro_z=values[5],
            mag_x=values[6], mag_y=values[7], mag_z=values[8],
            roll=values[9], pitch=values[10], yaw=values[11]
        )
    
    def _parse_ultrasonic_data(self, data: bytes) -> UltrasonicData:
        """Parse ultrasonic sensor data"""
        if len(data) != ProtocolConstants.ULTRASONIC_SIZE:
            raise ValueError(f"Ultrasonic data size mismatch: expected {ProtocolConstants.ULTRASONIC_SIZE}, got {len(data)}")
        
        # Format: 4 floats (front, rear, left, right) in cm
        values = struct.unpack('<4f', data)
        return UltrasonicData(
            front=values[0],
            rear=values[1],
            left=values[2],
            right=values[3]
        )
    
    def _parse_system_status(self, data: bytes) -> SystemStatus:
        """Parse system status"""
        if len(data) != ProtocolConstants.SYSTEM_STATUS_SIZE:
            raise ValueError(f"Status data size mismatch: expected {ProtocolConstants.SYSTEM_STATUS_SIZE}, got {len(data)}")
        
        # Format: uptime(I), voltage(f), cpu_load(B), errors(B)
        values = struct.unpack('<IfBB', data)
        return SystemStatus(
            uptime=values[0],
            battery_voltage=values[1],
            cpu_load=values[2],
            errors=values[3]
        )
    
    # ==================== COMMAND FUNCTIONS ====================
    
    def send_command(self, cmd: int, data: bytes = b'') -> bool:
        """Send command to ATmega32"""
        try:
            if not self.serial or not self.serial.is_open:
                logger.error("Serial port not open")
                return False
            
            packet = Packet.create(cmd, data)
            self.serial.write(packet)
            self.packets_sent += 1
            logger.debug(f"Sent command 0x{cmd:02X}, {len(data)} bytes")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            self.errors += 1
            return False
    
    def set_motor_speed(self, left: int, right: int) -> bool:
        """
        Set motor speeds
        
        Args:
            left: Left motor speed (-100 to 100)
            right: Right motor speed (-100 to 100)
        """
        left = max(-100, min(100, left))
        right = max(-100, min(100, right))
        
        data = struct.pack('<bb', left, right)
        return self.send_command(CommandCode.CMD_MOTOR_SET_SPEED, data)
    
    def stop_motors(self) -> bool:
        """Stop both motors"""
        return self.send_command(CommandCode.CMD_MOTOR_STOP)
    
    def emergency_stop(self) -> bool:
        """Emergency stop (immediate)"""
        return self.send_command(CommandCode.CMD_MOTOR_EMERGENCY_STOP)
    
    def request_gps_data(self, timeout: Optional[float] = None) -> Optional[GPSData]:
        """Request GPS data from ATmega32"""
        if timeout:
            return self._request_with_timeout(CommandCode.CMD_GPS_REQUEST, 
                                             CommandCode.RESP_GPS_DATA, timeout)
        else:
            self.send_command(CommandCode.CMD_GPS_REQUEST)
            return None
    
    def request_imu_data(self, timeout: Optional[float] = None) -> Optional[IMUData]:
        """Request IMU data from ATmega32"""
        if timeout:
            return self._request_with_timeout(CommandCode.CMD_IMU_REQUEST, 
                                             CommandCode.RESP_IMU_DATA, timeout)
        else:
            self.send_command(CommandCode.CMD_IMU_REQUEST)
            return None
    
    def request_ultrasonic_data(self, timeout: Optional[float] = None) -> Optional[UltrasonicData]:
        """Request ultrasonic sensor data"""
        if timeout:
            return self._request_with_timeout(CommandCode.CMD_ULTRASONIC_REQUEST, 
                                             CommandCode.RESP_ULTRASONIC_DATA, timeout)
        else:
            self.send_command(CommandCode.CMD_ULTRASONIC_REQUEST)
            return None
    
    def request_all_sensors(self) -> bool:
        """Request all sensor data"""
        return self.send_command(CommandCode.CMD_ALL_SENSORS_REQUEST)
    
    def request_system_status(self, timeout: Optional[float] = None) -> Optional[SystemStatus]:
        """Request system status"""
        if timeout:
            return self._request_with_timeout(CommandCode.CMD_SYSTEM_STATUS, 
                                             CommandCode.RESP_SYSTEM_STATUS, timeout)
        else:
            self.send_command(CommandCode.CMD_SYSTEM_STATUS)
            return None
    
    def set_led(self, state: bool) -> bool:
        """Control LED"""
        data = bytes([1 if state else 0])
        return self.send_command(CommandCode.CMD_LED_CONTROL, data)
    
    def set_buzzer(self, state: bool) -> bool:
        """Control buzzer"""
        data = bytes([1 if state else 0])
        return self.send_command(CommandCode.CMD_BUZZER_CONTROL, data)
    
    def reset_atmega(self) -> bool:
        """Reset ATmega32"""
        result = self.send_command(CommandCode.CMD_RESET)
        time.sleep(3)  # Wait for reset
        return result
    
    # ==================== SYNCHRONOUS REQUEST HANDLING ====================
    
    def _request_with_timeout(self, cmd: int, resp_type: int, timeout: float) -> any:
        """Send request and wait for response with timeout"""
        # Create event for this response type
        if resp_type not in self.response_events:
            self.response_events[resp_type] = threading.Event()
        
        event = self.response_events[resp_type]
        event.clear()
        self.response_data[resp_type] = None
        
        # Send command
        if not self.send_command(cmd):
            return None
        
        # Wait for response
        if event.wait(timeout):
            return self.response_data.get(resp_type)
        else:
            logger.warning(f"Timeout waiting for response 0x{resp_type:02X}")
            return None
    
    def _signal_response(self, resp_type: int, data: any):
        """Signal that a response has been received"""
        if resp_type in self.response_events:
            self.response_data[resp_type] = data
            self.response_events[resp_type].set()
    
    # ==================== CALLBACK SYSTEM ====================
    
    def register_callback(self, response_type: int, callback: Callable):
        """Register callback for specific response type"""
        if response_type not in self.callbacks:
            self.callbacks[response_type] = []
        self.callbacks[response_type].append(callback)
        logger.info(f"Registered callback for response 0x{response_type:02X}")
    
    def _trigger_callbacks(self, response_type: int, data):
        """Trigger registered callbacks"""
        if response_type in self.callbacks:
            for callback in self.callbacks[response_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
    
    # ==================== HEARTBEAT MONITORING ====================
    
    def _start_heartbeat(self):
        """Start heartbeat monitoring thread"""
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info("Started heartbeat monitoring")
    
    def _heartbeat_loop(self):
        """Monitor connection health"""
        heartbeat_interval = 5.0  # seconds
        timeout_threshold = 15.0  # seconds
        
        while self.running and self.connected:
            time.sleep(heartbeat_interval)
            
            # Check if we've received data recently
            time_since_last = time.time() - self.last_heartbeat
            
            if time_since_last > timeout_threshold:
                logger.warning(f"No data received for {time_since_last:.1f}s - connection may be lost")
                
                # Try to ping with status request
                if not self.request_system_status(timeout=2.0):
                    logger.error("Heartbeat failed - connection lost")
                    self.connected = False
                    
                    if self.auto_reconnect:
                        logger.info("Attempting to reconnect...")
                        if self.connect(retries=3):
                            logger.info("Reconnected successfully")
                        else:
                            logger.error("Reconnection failed")
                            break
    
    # ==================== DATA LOGGING ====================
    
    def _log_data(self, sensor_type: str, data):
        """Log sensor data to file"""
        if not self.enable_logging:
            return
        
        try:
            with open(self.log_file, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                f.write(f"{timestamp} | {sensor_type} | {data}\n")
        except Exception as e:
            logger.error(f"Failed to log data: {e}")
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict:
        """Get communication statistics"""
        return {
            'connected': self.connected,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'errors': self.errors,
            'uptime': time.time() - self.last_heartbeat if self.connected else 0
        }

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage with enhanced features"""
    
    # Initialize interface with auto-reconnect and logging
    atmega = ATmega32Interface(
        port=None,  # Auto-detect
        baudrate=115200,
        auto_reconnect=True,
        enable_logging=True
    )
    
    # Connect with retries
    if not atmega.connect(retries=3):
        print("Failed to connect to ATmega32")
        return
    
    # Register callbacks for asynchronous updates
    def on_gps_data(gps: GPSData):
        if gps.valid:
            print(f"GPS: {gps.latitude:.6f}, {gps.longitude:.6f}, Speed: {gps.speed:.1f} km/h, Sats: {gps.satellites}")
    
    def on_imu_data(imu: IMUData):
        print(f"IMU: Roll={imu.roll:.1f}°, Pitch={imu.pitch:.1f}°, Yaw={imu.yaw:.1f}°")
    
    def on_ultrasonic_data(ultrasonic: UltrasonicData):
        print(f"Ultrasonic: F={ultrasonic.front:.1f}cm, R={ultrasonic.rear:.1f}cm, L={ultrasonic.left:.1f}cm, R={ultrasonic.right:.1f}cm")
    
    atmega.register_callback(CommandCode.RESP_GPS_DATA, on_gps_data)
    atmega.register_callback(CommandCode.RESP_IMU_DATA, on_imu_data)
    atmega.register_callback(CommandCode.RESP_ULTRASONIC_DATA, on_ultrasonic_data)
    
    try:
        print("Starting sensor monitoring... (Ctrl+C to stop)")
        
        # Example 1: Asynchronous requests
        while True:
            # Request all sensors
            atmega.request_all_sensors()
            time.sleep(1)
            
            # Print statistics every 10 seconds
            stats = atmega.get_statistics()
            if stats['packets_received'] % 10 == 0:
                print(f"\nStats: Sent={stats['packets_sent']}, Received={stats['packets_received']}, Errors={stats['errors']}")
        
        # Example 2: Synchronous request with timeout
        # gps = atmega.request_gps_data(timeout=2.0)
        # if gps:
        #     print(f"GPS (sync): {gps.latitude}, {gps.longitude}")
        
        # Example 3: Motor control
        # atmega.set_motor_speed(50, 50)  # Forward at 50%
        # time.sleep(2)
        # atmega.stop_motors()
        
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        atmega.emergency_stop()
        atmega.disconnect()
        print("Disconnected")

if __name__ == "__main__":
    main()