#!/usr/bin/env python3
"""
ATmega32 Interface for Raspberry Pi
Handles serial communication with ATmega32 microcontroller
Location: ~/Graduation_Project_SDV/atmega32_interface.py
"""

import serial
import struct
import time
import threading
from typing import Optional, Tuple, Callable, Dict
from dataclasses import dataclass
from enum import IntEnum
import logging

logging.basicConfig(level=logging.INFO)
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

# ==================== DATA STRUCTURES ====================

@dataclass
class GPSData:
    """GPS data structure"""
    latitude: float
    longitude: float
    altitude: float
    speed: float
    satellites: int
    fix_quality: int
    valid: bool

@dataclass
class IMUData:
    """IMU 9DOF data structure"""
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
    """Ultrasonic sensor data"""
    front: float  # cm
    rear: float   # cm
    left: float   # cm
    right: float  # cm

@dataclass
class SystemStatus:
    """ATmega32 system status"""
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

# ==================== ATMEGA32 INTERFACE ====================

class ATmega32Interface:
    """Main interface for communicating with ATmega32"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        """
        Initialize ATmega32 interface
        
        Args:
            port: Serial port (default: /dev/ttyUSB0)
            baudrate: Baud rate (default: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        
        # Latest sensor data
        self.gps_data: Optional[GPSData] = None
        self.imu_data: Optional[IMUData] = None
        self.ultrasonic_data: Optional[UltrasonicData] = None
        self.system_status: Optional[SystemStatus] = None
        
        # Callbacks
        self.callbacks: Dict[int, list] = {}
        
        # Threading
        self.running = False
        self.read_thread: Optional[threading.Thread] = None
        
        logger.info(f"ATmega32 Interface initialized on {port} @ {baudrate}")
    
    def connect(self) -> bool:
        """Connect to ATmega32"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=ProtocolConstants.TIMEOUT,
                write_timeout=ProtocolConstants.TIMEOUT
            )
            time.sleep(2)  # Wait for connection to stabilize
            
            # Test connection with system status request
            if self.request_system_status():
                logger.info("Connected to ATmega32")
                return True
            else:
                logger.warning("Connected but no response from ATmega32")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from ATmega32"""
        self.running = False
        
        if self.read_thread:
            self.read_thread.join(timeout=2)
        
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
                            self._handle_response(cmd, data)
                
                time.sleep(0.01)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                time.sleep(0.1)
    
    def _handle_response(self, cmd: int, data: bytes):
        """Handle received response from ATmega32"""
        try:
            if cmd == CommandCode.RESP_GPS_DATA:
                self.gps_data = self._parse_gps_data(data)
                self._trigger_callbacks(cmd, self.gps_data)
                
            elif cmd == CommandCode.RESP_IMU_DATA:
                self.imu_data = self._parse_imu_data(data)
                self._trigger_callbacks(cmd, self.imu_data)
                
            elif cmd == CommandCode.RESP_ULTRASONIC_DATA:
                self.ultrasonic_data = self._parse_ultrasonic_data(data)
                self._trigger_callbacks(cmd, self.ultrasonic_data)
                
            elif cmd == CommandCode.RESP_SYSTEM_STATUS:
                self.system_status = self._parse_system_status(data)
                self._trigger_callbacks(cmd, self.system_status)
                
            elif cmd == CommandCode.RESP_ACK:
                logger.debug("Received ACK")
                
            elif cmd == CommandCode.RESP_NACK:
                logger.warning("Received NACK")
                
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    # ==================== PARSING FUNCTIONS ====================
    
    def _parse_gps_data(self, data: bytes) -> GPSData:
        """Parse GPS data from bytes"""
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
            packet = Packet.create(cmd, data)
            self.serial.write(packet)
            logger.debug(f"Sent command 0x{cmd:02X}, {len(data)} bytes")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
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
    
    def request_gps_data(self) -> bool:
        """Request GPS data from ATmega32"""
        return self.send_command(CommandCode.CMD_GPS_REQUEST)
    
    def request_imu_data(self) -> bool:
        """Request IMU data from ATmega32"""
        return self.send_command(CommandCode.CMD_IMU_REQUEST)
    
    def request_ultrasonic_data(self) -> bool:
        """Request ultrasonic sensor data"""
        return self.send_command(CommandCode.CMD_ULTRASONIC_REQUEST)
    
    def request_all_sensors(self) -> bool:
        """Request all sensor data"""
        return self.send_command(CommandCode.CMD_ALL_SENSORS_REQUEST)
    
    def request_system_status(self) -> bool:
        """Request system status"""
        return self.send_command(CommandCode.CMD_SYSTEM_STATUS)
    
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
        return self.send_command(CommandCode.CMD_RESET)
    
    # ==================== CALLBACK SYSTEM ====================
    
    def register_callback(self, response_type: int, callback: Callable):
        """Register callback for specific response type"""
        if response_type not in self.callbacks:
            self.callbacks[response_type] = []
        self.callbacks[response_type].append(callback)
    
    def _trigger_callbacks(self, response_type: int, data):
        """Trigger registered callbacks"""
        if response_type in self.callbacks:
            for callback in self.callbacks[response_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage"""
    
    # Initialize interface
    atmega = ATmega32Interface('/dev/ttyUSB0', 115200)
    
    # Connect
    if not atmega.connect():
        print("Failed to connect to ATmega32")
        return
    
    # Start reading thread
    atmega.start_reading()
    
    # Register callbacks
    def on_gps_data(gps: GPSData):
        if gps.valid:
            print(f"GPS: {gps.latitude:.6f}, {gps.longitude:.6f}, {gps.speed:.1f} km/h")
    
    def on_imu_data(imu: IMUData):
        print(f"IMU: Roll={imu.roll:.1f}°, Pitch={imu.pitch:.1f}°, Yaw={imu.yaw:.1f}°")
    
    atmega.register_callback(CommandCode.RESP_GPS_DATA, on_gps_data)
    atmega.register_callback(CommandCode.RESP_IMU_DATA, on_imu_data)
    
    try:
        while True:
            # Request sensor data
            atmega.request_gps_data()
            time.sleep(0.5)
            
            atmega.request_imu_data()
            time.sleep(0.5)
            
            # Control motors (example)
            atmega.set_motor_speed(50, 50)  # Forward at 50%
            time.sleep(2)
            
            atmega.stop_motors()
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        atmega.emergency_stop()
        atmega.disconnect()

if __name__ == "__main__":
    main()