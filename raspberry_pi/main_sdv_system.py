#!/usr/bin/env python3
"""
Master SDV System Integration with Dual Camera Setup
- ADAS: Xbox Kinect (road monitoring)
- DMS: Pi Camera v2 (driver monitoring)
Location: ~/Graduation_Project_SDV/raspberry_pi/main_sdv_system.py
"""
import numpy as np
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Optional
import threading
import cv2

# Import all modules
try:
    from atmega32_interface import ATmega32Interface, IMUData
    from gps_interface import GPSInterface, GPSData
    from adas_inference import AdasSystem
    from driver_inference import DriverMonitoringSystem, DriverState
    from v2x_interface import V2XInterface
    from iot_publish import IntegratedTelemetrySystem
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
    
    GPS_PORT = None  # Auto-detect
    GPS_BAUDRATE = 9600
    
    ESP32_PORT = '/dev/ttyUSB1'
    ESP32_BAUDRATE = 115200
    
    # ONNX Models - ADAS (Road Monitoring)
    BASE_DIR = Path.home() / "Graduation_Project_SDV"
    MODELS_DIR = BASE_DIR / "models"
    
    LANE_MODEL = MODELS_DIR / "lane_detection.onnx"
    OBJECT_MODEL = MODELS_DIR / "yolov8n.onnx"
    SIGN_MODEL = MODELS_DIR / "traffic_signs.onnx"
    
    # ONNX Models - DMS (Driver Monitoring)
    EMOTION_MODEL = MODELS_DIR / "emotion_recognition.onnx"
    FACE_MODEL = None  # Will use Haar Cascade
    
    # Camera settings
    USE_KINECT = True  # Xbox Kinect for ADAS
    USE_PI_CAMERA = True  # Pi Camera v2 for DMS
    
    # System settings
    MAIN_LOOP_RATE = 0.1  # 10 Hz
    SENSOR_UPDATE_RATE = 0.5  # 2 Hz
    GPS_WAIT_TIMEOUT = 60
    
    # Display settings
    SHOW_ADAS_WINDOW = True
    SHOW_DMS_WINDOW = True
    DISPLAY_COMBINED = True  # Show both feeds in one window
    
    # Feature flags
    ENABLE_ATMEGA32 = True
    ENABLE_GPS = True
    ENABLE_V2X = True
    ENABLE_ADAS = True
    ENABLE_DMS = True
    ENABLE_TELEMETRY = True
    ENABLE_SECURITY = True
    
    # Alert thresholds
    DRIVER_ALERT_BUZZER = True  # Sound buzzer on driver alerts
    COLLISION_WARNING_DISTANCE = 5.0  # meters

# ==================== MAIN SDV SYSTEM ====================

class SDVSystem:
    """Main Software-Defined Vehicle System with dual camera setup"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        
        # System state
        self.running = False
        self.initialization_complete = False
        
        # Subsystems
        self.atmega32: Optional[ATmega32Interface] = None
        self.gps: Optional[GPSInterface] = None
        self.v2x: Optional[V2XInterface] = None
        self.adas: Optional[AdasSystem] = None
        self.dms: Optional[DriverMonitoringSystem] = None
        self.telemetry: Optional[IntegratedTelemetrySystem] = None
        self.security: Optional[AutomotiveSecurity] = None
        
        # Fallback cameras
        self.adas_fallback_camera = None
        self.dms_fallback_camera = None
        
        # Current state
        self.gps_data: Optional[GPSData] = None
        self.imu_data: Optional[IMUData] = None
        self.adas_results = None
        self.dms_results = None
        
        # Statistics
        self.stats = {
            'start_time': time.time(),
            'adas_frames_processed': 0,
            'dms_frames_processed': 0,
            'sensors_read': 0,
            'v2x_messages': 0,
            'driver_alerts': 0,
            'collision_warnings': 0,
            'errors': 0
        }
        
        logger.info("SDV System initialized with dual camera setup")
    
    def initialize(self) -> bool:
        """Initialize all subsystems"""
        logger.info("=" * 60)
        logger.info("Initializing Software-Defined Vehicle System")
        logger.info("Dual Camera Configuration:")
        logger.info("  - ADAS: Xbox Kinect (Road Monitoring)")
        logger.info("  - DMS: Pi Camera v2 (Driver Monitoring)")
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
        
        # 2. Initialize GPS Interface
        if self.config.ENABLE_GPS:
            try:
                logger.info("Initializing GPS Interface...")
                self.gps = GPSInterface(
                    port=self.config.GPS_PORT,
                    baudrate=self.config.GPS_BAUDRATE,
                    enable_logging=True
                )
                
                if self.gps.connect():
                    self.gps.start_reading()
                    self._register_gps_callbacks()
                    logger.info("✓ GPS connected")
                    
                    logger.info(f"Waiting for GPS fix (timeout: {self.config.GPS_WAIT_TIMEOUT}s)...")
                    if self.gps.wait_for_fix(timeout=self.config.GPS_WAIT_TIMEOUT):
                        logger.info("✓ GPS fix acquired")
                    else:
                        logger.warning("⚠ GPS fix not acquired (continuing anyway)")
                else:
                    logger.warning("✗ GPS not connected")
                    self.gps = None
            except Exception as e:
                logger.error(f"✗ GPS initialization failed: {e}")
                self.gps = None
        
        # 3. Initialize ATmega32 Interface
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
                    logger.warning("✗ ATmega32 not connected")
                    self.atmega32 = None
            except Exception as e:
                logger.error(f"✗ ATmega32 initialization failed: {e}")
                self.atmega32 = None
        
        # 4. Initialize V2X Communication
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
                    logger.warning("✗ V2X not available")
                    self.v2x = None
            except Exception as e:
                logger.error(f"✗ V2X initialization failed: {e}")
                self.v2x = None
        
        # 5. Initialize ADAS System (Xbox Kinect)
        if self.config.ENABLE_ADAS:
            try:
                logger.info("Initializing ADAS System (Xbox Kinect)...")
                
                if not all([
                    self.config.LANE_MODEL.exists(),
                    self.config.OBJECT_MODEL.exists(),
                    self.config.SIGN_MODEL.exists()
                ]):
                    logger.warning("✗ ADAS models not found")
                    self.adas = None
                else:
                    self.adas = AdasSystem(
                        str(self.config.LANE_MODEL),
                        str(self.config.OBJECT_MODEL),
                        str(self.config.SIGN_MODEL),
                        use_kinect=self.config.USE_KINECT
                    )
                    
                    if not self.adas.use_kinect:
                        # Fallback to USB camera
                        logger.info("Setting up fallback camera for ADAS...")
                        self.adas_fallback_camera = cv2.VideoCapture(0)
                        self.adas_fallback_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        self.adas_fallback_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    
                    logger.info("✓ ADAS System ready")
                        
            except Exception as e:
                logger.error(f"✗ ADAS initialization failed: {e}")
                self.adas = None
        
        # 6. Initialize Driver Monitoring System (Pi Camera v2)
        if self.config.ENABLE_DMS:
            try:
                logger.info("Initializing Driver Monitoring System (Pi Camera v2)...")
                
                if not self.config.EMOTION_MODEL.exists():
                    logger.warning("✗ Emotion model not found")
                    self.dms = None
                else:
                    self.dms = DriverMonitoringSystem(
                        str(self.config.EMOTION_MODEL),
                        self.config.FACE_MODEL,
                        use_pi_camera=self.config.USE_PI_CAMERA
                    )
                    
                    if not self.dms.use_pi_camera:
                        # Fallback to USB camera
                        logger.info("Setting up fallback camera for DMS...")
                        self.dms_fallback_camera = cv2.VideoCapture(1)  # Second camera
                        self.dms_fallback_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.dms_fallback_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    logger.info("✓ Driver Monitoring System ready")
                        
            except Exception as e:
                logger.error(f"✗ DMS initialization failed: {e}")
                self.dms = None
        
        # 7. Initialize Telemetry System
        if self.config.ENABLE_TELEMETRY:
            try:
                logger.info("Initializing Telemetry System...")
                self.telemetry = IntegratedTelemetrySystem()
                
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
        logger.info(f"  GPS: {'✓' if self.gps else '✗'}")
        logger.info(f"  ATmega32: {'✓' if self.atmega32 else '✗'}")
        logger.info(f"  V2X: {'✓' if self.v2x else '✗'}")
        logger.info(f"  ADAS (Kinect): {'✓' if self.adas else '✗'}")
        logger.info(f"  DMS (Pi Cam): {'✓' if self.dms else '✗'}")
        logger.info(f"  Telemetry: {'✓' if self.telemetry else '✗'}")
        logger.info("=" * 60)
        
        self.initialization_complete = True
        return success
    
    def _register_gps_callbacks(self):
        """Register callbacks for GPS data"""
        def on_gps(gps: GPSData):
            self.gps_data = gps
            self.stats['sensors_read'] += 1
            
            if self.v2x and gps.valid:
                self.v2x.update_vehicle_state(
                    latitude=gps.latitude,
                    longitude=gps.longitude,
                    speed=gps.speed,
                    heading=gps.heading
                )
        
        self.gps.register_callback(on_gps)
    
    def _register_atmega32_callbacks(self):
        """Register callbacks for ATmega32 data"""
        from atmega32_interface import CommandCode
        
        def on_imu(imu: IMUData):
            self.imu_data = imu
            self.stats['sensors_read'] += 1
            
            if self.v2x and not self.gps_data:
                self.v2x.update_vehicle_state(heading=imu.yaw)
        
        self.atmega32.register_callback(CommandCode.RESP_IMU_DATA, on_imu)
    
    def _register_v2x_callbacks(self):
        """Register callbacks for V2X events"""
        def on_emergency(data):
            logger.warning(f"Emergency vehicle detected: {data['distance']:.0f}m away")
            if self.atmega32 and self.config.DRIVER_ALERT_BUZZER:
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
        logger.info("Press 'q' to quit")
        
        last_sensor_update = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # 1. Request sensor data from ATmega32
                if self.atmega32 and (time.time() - last_sensor_update) >= self.config.SENSOR_UPDATE_RATE:
                    self.atmega32.request_imu_data()
                    self.atmega32.request_ultrasonic_data()
                    last_sensor_update = time.time()
                
                # 2. Process ADAS frame (Road Monitoring - Kinect)
                adas_frame = None
                if self.adas:
                    if self.adas.use_kinect:
                        rgb_frame, depth_frame = self.adas.get_frame()
                        if rgb_frame is not None:
                            adas_frame, self.adas_results = self.adas.process_frame(rgb_frame, depth_frame)
                            self.stats['adas_frames_processed'] += 1
                    elif self.adas_fallback_camera and self.adas_fallback_camera.isOpened():
                        ret, rgb_frame = self.adas_fallback_camera.read()
                        if ret:
                            adas_frame, self.adas_results = self.adas.process_frame(rgb_frame)
                            self.stats['adas_frames_processed'] += 1
                
                # 3. Process DMS frame (Driver Monitoring - Pi Camera)
                dms_frame = None
                if self.dms:
                    if self.dms.use_pi_camera:
                        frame = self.dms.get_frame()
                        if frame is not None:
                            dms_frame, self.dms_results = self.dms.process_frame(frame)
                            self.stats['dms_frames_processed'] += 1
                    elif self.dms_fallback_camera and self.dms_fallback_camera.isOpened():
                        ret, frame = self.dms_fallback_camera.read()
                        if ret:
                            dms_frame, self.dms_results = self.dms.process_frame(frame)
                            self.stats['dms_frames_processed'] += 1
                
                # 4. Handle driver alerts
                if self.dms_results and self.dms_results.alert_level > 0:
                    self._handle_driver_alert(self.dms_results)
                
                # 5. Handle collision warnings
                if self.adas_results:
                    self._handle_collision_warnings(self.adas_results)
                
                # 6. Update telemetry
                if self.telemetry:
                    self._update_telemetry()
                
                # 7. Display frames
                if self.config.DISPLAY_COMBINED:
                    self._display_combined(adas_frame, dms_frame)
                else:
                    if self.config.SHOW_ADAS_WINDOW and adas_frame is not None:
                        cv2.imshow('ADAS - Road Monitoring', adas_frame)
                    if self.config.SHOW_DMS_WINDOW and dms_frame is not None:
                        cv2.imshow('DMS - Driver Monitoring', dms_frame)
                
                # 8. Make driving decisions
                self._make_decisions()
                
                # 9. Log statistics periodically
                if int(time.time()) % 10 == 0:
                    self._log_statistics()
                
                # Check for quit command
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Quit command received")
                    break
                
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
    
    def _handle_driver_alert(self, dms_result):
        """Handle driver monitoring alerts"""
        self.stats['driver_alerts'] += 1
        
        if dms_result.alert_level == 2:  # Critical
            logger.warning(f"CRITICAL DRIVER ALERT: {dms_result.driver_state.value}")
            
            if self.atmega32 and self.config.DRIVER_ALERT_BUZZER:
                # Sound buzzer pattern for critical alert
                for _ in range(3):
                    self.atmega32.set_buzzer(True)
                    time.sleep(0.2)
                    self.atmega32.set_buzzer(False)
                    time.sleep(0.1)
            
            # Could also slow down or stop vehicle in critical cases
            if dms_result.driver_state in [DriverState.DROWSY, DriverState.EYES_CLOSED]:
                logger.warning("Driver appears drowsy - consider stopping vehicle")
                # self.atmega32.stop_motors()  # Uncomment for autonomous stop
        
        elif dms_result.alert_level == 1:  # Warning
            logger.info(f"Driver warning: {dms_result.driver_state.value}")
    
    def _handle_collision_warnings(self, adas_results):
        """Handle collision warnings from ADAS"""
        if 'objects' in adas_results:
            for obj in adas_results['objects']:
                if obj.distance and obj.distance < self.config.COLLISION_WARNING_DISTANCE:
                    self.stats['collision_warnings'] += 1
                    logger.warning(f"Collision warning: {obj.class_name} at {obj.distance:.1f}m")
                    
                    if self.atmega32 and self.config.DRIVER_ALERT_BUZZER:
                        self.atmega32.set_buzzer(True)
                        time.sleep(0.1)
                        self.atmega32.set_buzzer(False)
                    
                    # Emergency stop if very close
                    if obj.distance < 2.0:
                        logger.error(f"EMERGENCY: Object too close!")
                        if self.atmega32:
                            self.atmega32.emergency_stop()
    
    def _display_combined(self, adas_frame, dms_frame):
        """Display both camera feeds in one window"""
        if adas_frame is None and dms_frame is None:
            return
        
        # Resize frames to same height
        target_height = 480
        
        if adas_frame is not None:
            h, w = adas_frame.shape[:2]
            scale = target_height / h
            adas_resized = cv2.resize(adas_frame, (int(w * scale), target_height))
        else:
            adas_resized = np.zeros((target_height, 640, 3), dtype=np.uint8)
            cv2.putText(adas_resized, "ADAS: No Feed", (200, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        if dms_frame is not None:
            h, w = dms_frame.shape[:2]
            scale = target_height / h
            dms_resized = cv2.resize(dms_frame, (int(w * scale), target_height))
        else:
            dms_resized = np.zeros((target_height, 640, 3), dtype=np.uint8)
            cv2.putText(dms_resized, "DMS: No Feed", (200, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Combine horizontally
        combined = np.hstack([adas_resized, dms_resized])
        
        # Add separator line
        h, w = combined.shape[:2]
        cv2.line(combined, (w//2, 0), (w//2, h), (255, 255, 255), 2)
        
        # Add labels
        cv2.putText(combined, "ROAD MONITORING (Kinect)", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(combined, "DRIVER MONITORING (Pi Cam)", (w//2 + 10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('SDV System - Dual Camera Feed', combined)
    
    def _update_telemetry(self):
        """Update telemetry with current data"""
        gps_dict = None
        if self.gps_data and self.gps_data.valid:
            gps_dict = {
                'lat': self.gps_data.latitude,
                'lon': self.gps_data.longitude,
                'alt': self.gps_data.altitude,
                'speed': self.gps_data.speed,
                'heading': self.gps_data.heading
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
            adas_results=self.adas_results if self.adas else None
        )
        
        # Add DMS data to telemetry
        if self.dms_results:
            self.telemetry.publisher.update_adas_data(
                lane_departure=self.adas_results['lane'].lane_departure if self.adas_results else 0,
                objects_detected=len(self.adas_results['objects']) if self.adas_results else 0,
                traffic_sign=self.adas_results['sign'].sign_type if self.adas_results else None,
                confidence=self.adas_results['sign'].confidence if self.adas_results else 0
            )
    
    def _make_decisions(self):
        """Make driving decisions based on all inputs"""
        # Combine ADAS and DMS for comprehensive decision making
        
        # 1. Check driver state - if critical, reduce speed or stop
        if self.dms_results and self.dms_results.alert_level == 2:
            if self.dms_results.driver_state in [DriverState.DROWSY, DriverState.EYES_CLOSED]:
                logger.warning("Driver incapacitated - implementing safety measures")
                # Could implement gradual stop, pull over, etc.
        
        # 2. Check ADAS obstacles
        if self.adas_results and 'objects' in self.adas_results:
            for obj in self.adas_results['objects']:
                if obj.distance and obj.distance < 2.0:
                    if self.atmega32:
                        self.atmega32.emergency_stop()
                    return
        
        # 3. Check lane departure
        if self.adas_results and 'lane' in self.adas_results:
            lane = self.adas_results['lane']
            if abs(lane.lane_departure) > 0.3:
                logger.warning(f"Lane departure: {lane.lane_departure:.2f}")
                # Could implement steering correction
        
        # 4. Check V2X hazards
        if self.v2x:
            hazards = self.v2x.get_hazards_ahead(max_distance=100)
            if hazards:
                logger.info(f"Hazards ahead: {len(hazards)}")
    
    def _log_statistics(self):
        """Log system statistics"""
        uptime = time.time() - self.stats['start_time']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"System Statistics - Uptime: {uptime:.0f}s")
        logger.info(f"  ADAS Frames: {self.stats['adas_frames_processed']}")
        logger.info(f"  DMS Frames: {self.stats['dms_frames_processed']}")
        logger.info(f"  Sensors Read: {self.stats['sensors_read']}")
        logger.info(f"  Driver Alerts: {self.stats['driver_alerts']}")
        logger.info(f"  Collision Warnings: {self.stats['collision_warnings']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        
        if self.gps_data and self.gps_data.valid:
            logger.info(f"  GPS: {self.gps_data.latitude:.6f}, {self.gps_data.longitude:.6f}")
        
        if self.security:
            status = self.security.get_status()
            logger.info(f"  Security Score: {status['security_score']:.1f}/100")
        
        logger.info(f"{'='*60}\n")
    
    def shutdown(self):
        """Graceful shutdown of all subsystems"""
        logger.info("Shutting down SDV System...")
        
        self.running = False
        
        # Stop motors
        if self.atmega32:
            logger.info("Stopping motors...")
            self.atmega32.emergency_stop()
            self.atmega32.disconnect()
        
        # Stop GPS
        if self.gps:
            logger.info("Disconnecting GPS...")
            self.gps.disconnect()
        
        # Stop V2X
        if self.v2x:
            logger.info("Disconnecting V2X...")
            self.v2x.disconnect()
        
        # Stop telemetry
        if self.telemetry:
            logger.info("Stopping telemetry...")
            self.telemetry.stop()
        
        # Release cameras
        if self.adas:
            logger.info("Releasing ADAS camera...")
            self.adas.release()
        
        if self.dms:
            logger.info("Releasing DMS camera...")
            self.dms.release()
        
        if self.adas_fallback_camera:
            self.adas_fallback_camera.release()
        
        if self.dms_fallback_camera:
            self.dms_fallback_camera.release()
        
        cv2.destroyAllWindows()
        
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
    ║   Software-Defined Vehicle (SDV) System v2.0              ║
    ║   Graduation Project                                      ║
    ║                                                           ║
    ║   Modules:                                                ║
    ║   - GPS Interface (Ublox NEO-6M) [NEW]                    ║
    ║   - ATmega32 Interface (IMU/Ultrasonic/Motors)            ║
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
        print("\nSystem has run successfully")
    else:
        logger.error("System initialization failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())