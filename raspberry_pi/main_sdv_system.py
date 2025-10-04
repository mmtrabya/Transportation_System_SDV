#!/usr/bin/env python3
"""
Master SDV System Integration
Main entry point that coordinates all subsystems
Location: ~/Graduation_Project_SDV/raspberry_pi/main_sdv_system.py
"""

import sys
import time
import signal
import logging
from pathlib import Path
from typing import Optional
import threading

# Import all modules
try:
    from atmega32_interface import ATmega32Interface, GPSData, IMUData
    from adas_inference import AdasSystem
    from v2x_interface import V2XInterface
    from iot_telemetry_publisher import IntegratedTelemetrySystem
    from automotive_cybersecurity import AutomotiveSecurity
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all modules are in the same directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sdv_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SDV_System')

# ==================== CONFIGURATION ====================

class SystemConfig:
    """System-wide configuration"""
    
    # Hardware ports
    ATMEGA32_PORT = '/dev/ttyUSB0'
    ATMEGA32_BAUDRATE = 115200
    
    ESP32_PORT = '/dev/ttyUSB1'
    ESP32_BAUDRATE = 115200
    
    # ONNX Models
    BASE_DIR = Path.home() / "Graduation_Project_SDV"
    MODELS_DIR = BASE_DIR / "models"
    
    LANE_MODEL = MODELS_DIR / "lane_detection.onnx"
    OBJECT_MODEL = MODELS_DIR / "yolov8n.onnx"
    SIGN_MODEL = MODELS_DIR / "traffic_signs.onnx"
    
    # Camera
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    
    # System settings
    MAIN_LOOP_RATE = 0.1  # 10 Hz
    SENSOR_UPDATE_RATE = 0.5  # 2 Hz
    
    # Feature flags (enable/disable subsystems)
    ENABLE_ATMEGA32 = True
    ENABLE_V2X = True
    ENABLE_ADAS = True
    ENABLE_TELEMETRY = True
    ENABLE_SECURITY = True

# ==================== MAIN SDV SYSTEM ====================

class SDVSystem:
    """Main Software-Defined Vehicle System"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        
        # System state
        self.running = False
        self.initialization_complete = False
        
        # Subsystems
        self.atmega32: Optional[ATmega32Interface] = None
        self.v2x: Optional[V2XInterface] = None
        self.adas: Optional[AdasSystem] = None
        self.telemetry: Optional[IntegratedTelemetrySystem] = None
        self.security: Optional[AutomotiveSecurity] = None
        
        # Camera
        self.camera = None
        
        # Current state
        self.gps_data: Optional[GPSData] = None
        self.imu_data: Optional[IMUData] = None
        self.adas_results = None
        
        # Statistics
        self.stats = {
            'start_time': time.time(),
            'frames_processed': 0,
            'sensors_read': 0,
            'v2x_messages': 0,
            'errors': 0
        }
        
        logger.info("SDV System initialized")
    
    def initialize(self) -> bool:
        """Initialize all subsystems"""
        logger.info("=" * 60)
        logger.info("Initializing Software-Defined Vehicle System")
        logger.info("=" * 60)
        
        success = True
        
        # 1. Initialize Security System
        if self.config.ENABLE_SECURITY:
            try:
                logger.info("Initializing Security System...")
                self.security = AutomotiveSecurity()
                logger.info("✓ Security System ready")
            except Exception as e:
                logger.error(f"✗ Security System failed: {e}")
                success = False
        
        # 2. Initialize ATmega32 Interface
        if self.config.ENABLE_ATMEGA32:
            try:
                logger.info("Initializing ATmega32 Interface...")
                self.atmega32 = ATmega32Interface(
                    self.config.ATMEGA32_PORT,
                    self.config.ATMEGA32_BAUDRATE
                )
                
                if self.atmega32.connect():
                    self.atmega32.start_reading()
                    self._register_atmega32_callbacks()
                    logger.info("✓ ATmega32 connected")
                else:
                    logger.warning("✗ ATmega32 not connected (hardware not available)")
                    self.atmega32 = None
            except Exception as e:
                logger.error(f"✗ ATmega32 initialization failed: {e}")
                self.atmega32 = None
        
        # 3. Initialize V2X Communication
        if self.config.ENABLE_V2X:
            try:
                logger.info("Initializing V2X Communication...")
                self.v2x = V2XInterface(
                    self.config.ESP32_PORT,
                    self.config.ESP32_BAUDRATE
                )
                
                if self.v2x.connect():
                    self.v2x.start()
                    self._register_v2x_callbacks()
                    logger.info("✓ V2X Communication ready")
                else:
                    logger.warning("✗ V2X not available (ESP32 not connected)")
                    self.v2x = None
            except Exception as e:
                logger.error(f"✗ V2X initialization failed: {e}")
                self.v2x = None
        
        # 4. Initialize ADAS System
        if self.config.ENABLE_ADAS:
            try:
                logger.info("Initializing ADAS System...")
                
                # Check if models exist
                if not all([
                    self.config.LANE_MODEL.exists(),
                    self.config.OBJECT_MODEL.exists(),
                    self.config.SIGN_MODEL.exists()
                ]):
                    logger.warning("✗ ADAS models not found (training in progress)")
                    self.adas = None
                else:
                    self.adas = AdasSystem(
                        str(self.config.LANE_MODEL),
                        str(self.config.OBJECT_MODEL),
                        str(self.config.SIGN_MODEL)
                    )
                    logger.info("✓ ADAS System ready")
                    
                    # Initialize camera
                    try:
                        import cv2
                        self.camera = cv2.VideoCapture(self.config.CAMERA_INDEX)
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.CAMERA_WIDTH)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.CAMERA_HEIGHT)
                        
                        if self.camera.isOpened():
                            logger.info("✓ Camera initialized")
                        else:
                            logger.warning("✗ Camera not available")
                            self.camera = None
                            self.adas = None
                    except:
                        logger.warning("✗ OpenCV not available")
                        self.camera = None
                        self.adas = None
                        
            except Exception as e:
                logger.error(f"✗ ADAS initialization failed: {e}")
                self.adas = None
        
        # 5. Initialize Telemetry System
        if self.config.ENABLE_TELEMETRY:
            try:
                logger.info("Initializing Telemetry System...")
                self.telemetry = IntegratedTelemetrySystem()
                
                # Connect subsystems
                if self.v2x:
                    self.telemetry.connect_v2x(self.v2x)
                if self.adas:
                    self.telemetry.connect_adas(self.adas)
                
                if self.telemetry.start():
                    logger.info("✓ Telemetry System ready")
                else:
                    logger.warning("✗ Telemetry failed to start")
                    self.telemetry = None
            except Exception as e:
                logger.error(f"✗ Telemetry initialization failed: {e}")
                self.telemetry = None
        
        logger.info("=" * 60)
        logger.info("System Initialization Summary:")
        logger.info(f"  Security: {'✓' if self.security else '✗'}")
        logger.info(f"  ATmega32: {'✓' if self.atmega32 else '✗'}")
        logger.info(f"  V2X: {'✓' if self.v2x else '✗'}")
        logger.info(f"  ADAS: {'✓' if self.adas else '✗'}")
        logger.info(f"  Telemetry: {'✓' if self.telemetry else '✗'}")
        logger.info("=" * 60)
        
        self.initialization_complete = True
        return success
    
    def _register_atmega32_callbacks(self):
        """Register callbacks for ATmega32 data"""
        from atmega32_interface import CommandCode
        
        def on_gps(gps: GPSData):
            self.gps_data = gps
            self.stats['sensors_read'] += 1
        
        def on_imu(imu: IMUData):
            self.imu_data = imu
            self.stats['sensors_read'] += 1
        
        self.atmega32.register_callback(CommandCode.RESP_GPS_DATA, on_gps)
        self.atmega32.register_callback(CommandCode.RESP_IMU_DATA, on_imu)
    
    def _register_v2x_callbacks(self):
        """Register callbacks for V2X events"""
        def on_emergency(data):
            logger.warning(f"Emergency vehicle detected: {data['distance']:.0f}m away")
            if self.atmega32:
                self.atmega32.set_buzzer(True)
                time.sleep(0.5)
                self.atmega32.set_buzzer(False)
        
        def on_hazard(hazard):
            logger.warning(f"Hazard: {hazard.description} at {hazard.distance:.0f}m")
        
        self.v2x.register_callback('emergency_received', on_emergency)
        self.v2x.register_callback('hazard_received', on_hazard)
    
    def run(self):
        """Main system loop"""
        if not self.initialization_complete:
            logger.error("System not initialized. Call initialize() first.")
            return
        
        self.running = True
        logger.info("Starting main system loop...")
        logger.info("Press Ctrl+C to stop")
        
        last_sensor_update = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # 1. Request sensor data from ATmega32
                if self.atmega32 and (time.time() - last_sensor_update) >= self.config.SENSOR_UPDATE_RATE:
                    self.atmega32.request_gps_data()
                    self.atmega32.request_imu_data()
                    self.atmega32.request_ultrasonic_data()
                    last_sensor_update = time.time()
                
                # 2. Process camera frame with ADAS
                if self.adas and self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret:
                        self.adas_results, results = self.adas.process_frame(frame)
                        self.stats['frames_processed'] += 1
                        
                        # Display frame (optional)
                        # cv2.imshow('ADAS', self.adas_results)
                        # cv2.waitKey(1)
                
                # 3. Update telemetry
                if self.telemetry:
                    gps_dict = None
                    if self.gps_data and self.gps_data.valid:
                        gps_dict = {
                            'lat': self.gps_data.latitude,
                            'lon': self.gps_data.longitude,
                            'alt': self.gps_data.altitude,
                            'speed': self.gps_data.speed,
                            'heading': self.imu_data.yaw if self.imu_data else 0
                        }
                    
                    imu_dict = None
                    if self.imu_data:
                        imu_dict = {
                            'heading': self.imu_data.yaw,
                            'acceleration': self.imu_data.accel_x
                        }
                    
                    self.telemetry.update_from_sources(
                        gps_data=gps_dict,
                        imu_data=imu_dict,
                        adas_results=results if self.adas else None
                    )
                
                # 4. Make driving decisions (placeholder)
                self._make_decisions()
                
                # 5. Log statistics periodically
                if int(time.time()) % 10 == 0:
                    self._log_statistics()
                
                # Maintain loop rate
                elapsed = time.time() - loop_start
                if elapsed < self.config.MAIN_LOOP_RATE:
                    time.sleep(self.config.MAIN_LOOP_RATE - elapsed)
                
        except KeyboardInterrupt:
            logger.info("\nShutdown requested by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            self.stats['errors'] += 1
        finally:
            self.shutdown()
    
    def _make_decisions(self):
        """Make driving decisions based on all inputs"""
        # This is where ADAS, V2X, and sensor data come together
        
        # Example: Emergency stop if object too close
        if self.adas_results:
            for obj in self.adas_results.get('objects', []):
                if obj.distance and obj.distance < 2.0:  # 2 meters
                    logger.warning(f"Object too close: {obj.class_name} at {obj.distance:.1f}m")
                    if self.atmega32:
                        self.atmega32.emergency_stop()
                    return
        
        # Example: Slow down for hazards
        if self.v2x:
            hazards = self.v2x.get_hazards_ahead(max_distance=100)
            if hazards:
                logger.info(f"Hazards ahead: {len(hazards)}")
                # Reduce speed
        
        # Example: Normal driving based on lane detection
        if self.adas_results:
            lane_result = self.adas_results.get('lane')
            if lane_result and abs(lane_result.lane_departure) > 0.3:
                logger.warning(f"Lane departure: {lane_result.lane_departure:.2f}")
                # Adjust steering
    
    def _log_statistics(self):
        """Log system statistics"""
        uptime = time.time() - self.stats['start_time']
        
        logger.info(f"System Stats - Uptime: {uptime:.0f}s, "
                   f"Frames: {self.stats['frames_processed']}, "
                   f"Sensors: {self.stats['sensors_read']}, "
                   f"Errors: {self.stats['errors']}")
        
        if self.security:
            status = self.security.get_status()
            logger.info(f"Security Score: {status['security_score']:.1f}/100")
    
    def shutdown(self):
        """Graceful shutdown of all subsystems"""
        logger.info("Shutting down SDV System...")
        
        self.running = False
        
        # Stop motors
        if self.atmega32:
            logger.info("Stopping motors...")
            self.atmega32.emergency_stop()
            self.atmega32.disconnect()
        
        # Stop V2X
        if self.v2x:
            logger.info("Disconnecting V2X...")
            self.v2x.disconnect()
        
        # Stop telemetry
        if self.telemetry:
            logger.info("Stopping telemetry...")
            self.telemetry.stop()
        
        # Release camera
        if self.camera:
            logger.info("Releasing camera...")
            self.camera.release()
        
        # Final statistics
        logger.info("=" * 60)
        logger.info("Final System Statistics:")
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)
        
        logger.info("SDV System shutdown complete")

# ==================== MAIN ====================

def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   Software-Defined Vehicle (SDV) System                   ║
    ║   Graduation Project                                      ║
    ║                                                           ║
    ║   Modules:                                                ║
    ║   - ATmega32 Interface (GPS/IMU/Motors)                   ║
    ║   - V2X Communication (ESP32)                             ║
    ║   - ADAS (Lane/Object/Sign Detection)                     ║
    ║   - IoT Telemetry                                         ║
    ║   - Automotive Cybersecurity                              ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Create system with configuration
    config = SystemConfig()
    sdv = SDVSystem(config)
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\nReceived shutdown signal")
        sdv.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and run
    if sdv.initialize():
        sdv.run()
        print("system has run successfully")
    else:
        logger.error("System initialization failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())