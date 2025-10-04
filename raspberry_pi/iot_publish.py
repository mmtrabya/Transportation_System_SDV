#!/usr/bin/env python3
"""
IoT Telemetry Publisher
Collects data from all systems and publishes to MQTT broker for cloud dashboard
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import logging

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Installing paho-mqtt...")
    import subprocess
    subprocess.check_call(['pip3', 'install', 'paho-mqtt'])
    import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TelemetryPublisher')

# ==================== CONFIGURATION ====================

class TelemetryConfig:
    """Telemetry configuration"""
    
    # MQTT Broker
    MQTT_BROKER = "localhost"  # Public broker for testing
    MQTT_PORT = 1883
    MQTT_KEEPALIVE = 60
    
    # Vehicle Info
    VEHICLE_ID = "SDV_001"
    
    # Publishing intervals (seconds)
    GPS_INTERVAL = 0.5          # 2 Hz - GPS/position data
    ADAS_INTERVAL = 0.1         # 10 Hz - ADAS detections
    V2X_INTERVAL = 0.1          # 10 Hz - V2X messages
    SYSTEM_INTERVAL = 5.0       # 0.2 Hz - System health
    
    # MQTT Topics
    TOPIC_GPS = f"sdv/{VEHICLE_ID}/gps"
    TOPIC_ADAS = f"sdv/{VEHICLE_ID}/adas"
    TOPIC_V2X = f"sdv/{VEHICLE_ID}/v2x"
    TOPIC_SYSTEM = f"sdv/{VEHICLE_ID}/system"
    TOPIC_ALERTS = f"sdv/{VEHICLE_ID}/alerts"
    TOPIC_STATUS = f"sdv/{VEHICLE_ID}/status"

# ==================== TELEMETRY PUBLISHER ====================

class TelemetryPublisher:
    """Main telemetry publisher"""
    
    def __init__(self, config: TelemetryConfig = None):
        self.config = config or TelemetryConfig()
        
        # MQTT Client
        self.client = mqtt.Client(client_id=f"telemetry_{self.config.VEHICLE_ID}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Connection state
        self.connected = False
        self.reconnect_delay = 5
        
        # Data storage
        self.last_gps_data = {}
        self.last_adas_data = {}
        self.last_v2x_data = {}
        self.last_system_data = {}
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'start_time': time.time(),
            'last_publish': time.time()
        }
        
        # Threading
        self.running = False
        self.publish_threads = []
        
        logger.info(f"Telemetry Publisher initialized for {self.config.VEHICLE_ID}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
            self.client.connect(
                self.config.MQTT_BROKER,
                self.config.MQTT_PORT,
                self.config.MQTT_KEEPALIVE
            )
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("Successfully connected to MQTT broker")
                return True
            else:
                logger.error("Connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.publish_threads:
            thread.join(timeout=2)
        
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")
    
    def start(self):
        """Start telemetry publishing"""
        if not self.connected:
            logger.error("Not connected to broker. Call connect() first.")
            return False
        
        self.running = True
        
        # Start publishing threads for different data types
        threads = [
            threading.Thread(target=self._publish_gps_loop, daemon=True),
            threading.Thread(target=self._publish_adas_loop, daemon=True),
            threading.Thread(target=self._publish_v2x_loop, daemon=True),
            threading.Thread(target=self._publish_system_loop, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
            self.publish_threads.append(thread)
        
        logger.info("Telemetry publishing started")
        return True
    
    # ==================== MQTT CALLBACKS ====================
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            
            # Publish initial status
            self._publish_message(
                self.config.TOPIC_STATUS,
                {
                    'vehicle_id': self.config.VEHICLE_ID,
                    'status': 'online',
                    'timestamp': time.time()
                }
            )
        else:
            self.connected = False
            logger.error(f"Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection (code {rc}). Reconnecting...")
    
    def _on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        self.stats['last_publish'] = time.time()
    
    # ==================== PUBLISHING LOOPS ====================
    
    def _publish_gps_loop(self):
        """Publish GPS/position data"""
        while self.running:
            try:
                if self.last_gps_data:
                    self._publish_message(
                        self.config.TOPIC_GPS,
                        self.last_gps_data
                    )
                time.sleep(self.config.GPS_INTERVAL)
            except Exception as e:
                logger.error(f"Error in GPS publish loop: {e}")
                time.sleep(1)
    
    def _publish_adas_loop(self):
        """Publish ADAS detection data"""
        while self.running:
            try:
                if self.last_adas_data:
                    self._publish_message(
                        self.config.TOPIC_ADAS,
                        self.last_adas_data
                    )
                time.sleep(self.config.ADAS_INTERVAL)
            except Exception as e:
                logger.error(f"Error in ADAS publish loop: {e}")
                time.sleep(1)
    
    def _publish_v2x_loop(self):
        """Publish V2X communication data"""
        while self.running:
            try:
                if self.last_v2x_data:
                    self._publish_message(
                        self.config.TOPIC_V2X,
                        self.last_v2x_data
                    )
                time.sleep(self.config.V2X_INTERVAL)
            except Exception as e:
                logger.error(f"Error in V2X publish loop: {e}")
                time.sleep(1)
    
    def _publish_system_loop(self):
        """Publish system health data"""
        while self.running:
            try:
                system_data = self._collect_system_health()
                self._publish_message(
                    self.config.TOPIC_SYSTEM,
                    system_data
                )
                time.sleep(self.config.SYSTEM_INTERVAL)
            except Exception as e:
                logger.error(f"Error in system publish loop: {e}")
                time.sleep(1)
    
    # ==================== DATA UPDATES ====================
    
    def update_gps_data(self, latitude: float, longitude: float, altitude: float = 0,
                       speed: float = 0, heading: float = 0):
        """Update GPS data"""
        self.last_gps_data = {
            'vehicle_id': self.config.VEHICLE_ID,
            'timestamp': time.time(),
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude,
            'speed': speed,
            'heading': heading
        }
    
    def update_adas_data(self, lane_departure: float, objects_detected: int,
                        traffic_sign: str = None, confidence: float = 0):
        """Update ADAS data"""
        self.last_adas_data = {
            'vehicle_id': self.config.VEHICLE_ID,
            'timestamp': time.time(),
            'lane_departure': lane_departure,
            'objects_detected': objects_detected,
            'traffic_sign': traffic_sign,
            'sign_confidence': confidence
        }
    
    def update_v2x_data(self, nearby_vehicles: int, hazards: int,
                       emergency_vehicles: int, messages_received: int):
        """Update V2X data"""
        self.last_v2x_data = {
            'vehicle_id': self.config.VEHICLE_ID,
            'timestamp': time.time(),
            'nearby_vehicles': nearby_vehicles,
            'hazards_detected': hazards,
            'emergency_vehicles': emergency_vehicles,
            'messages_received': messages_received
        }
    
    def publish_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Publish alert/warning"""
        alert_data = {
            'vehicle_id': self.config.VEHICLE_ID,
            'timestamp': time.time(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        self._publish_message(self.config.TOPIC_ALERTS, alert_data)
        logger.warning(f"Alert published: {alert_type} - {message}")
    
    # ==================== INTERNAL METHODS ====================
    
    def _publish_message(self, topic: str, data: Dict[str, Any]):
        """Publish message to MQTT broker"""
        try:
            # Add metadata
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Convert to JSON
            payload = json.dumps(data)
            
            # Publish
            result = self.client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.stats['messages_sent'] += 1
            else:
                self.stats['messages_failed'] += 1
                logger.error(f"Failed to publish to {topic}")
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            self.stats['messages_failed'] += 1
    
    def _collect_system_health(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        import psutil
        
        uptime = time.time() - self.stats['start_time']
        
        return {
            'vehicle_id': self.config.VEHICLE_ID,
            'timestamp': time.time(),
            'uptime': uptime,
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'temperature': self._get_cpu_temperature(),
            'messages_sent': self.stats['messages_sent'],
            'messages_failed': self.stats['messages_failed'],
            'mqtt_connected': self.connected
        }
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature (Raspberry Pi)"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except:
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get publishing statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            'uptime': uptime,
            'messages_sent': self.stats['messages_sent'],
            'messages_failed': self.stats['messages_failed'],
            'success_rate': (self.stats['messages_sent'] / 
                           max(1, self.stats['messages_sent'] + self.stats['messages_failed']) * 100),
            'avg_rate': self.stats['messages_sent'] / max(1, uptime),
            'connected': self.connected
        }

# ==================== INTEGRATED TELEMETRY SYSTEM ====================

class IntegratedTelemetrySystem:
    """Integrated telemetry system with V2X and ADAS"""
    
    def __init__(self):
        self.publisher = TelemetryPublisher()
        
        # Optional: Import V2X and ADAS if available
        self.v2x = None
        self.adas = None
        
        logger.info("Integrated Telemetry System initialized")
    
    def connect_v2x(self, v2x_interface):
        """Connect V2X interface"""
        self.v2x = v2x_interface
        
        # Register callbacks
        self.v2x.register_callback('bsm_received', self._on_v2x_bsm)
        self.v2x.register_callback('hazard_received', self._on_v2x_hazard)
        self.v2x.register_callback('emergency_received', self._on_v2x_emergency)
        
        logger.info("V2X interface connected to telemetry")
    
    def connect_adas(self, adas_system):
        """Connect ADAS system"""
        self.adas = adas_system
        logger.info("ADAS system connected to telemetry")
    
    def start(self):
        """Start integrated system"""
        # Connect to broker
        if not self.publisher.connect():
            logger.error("Failed to connect to MQTT broker")
            return False
        
        # Start publishing
        self.publisher.start()
        
        logger.info("Integrated telemetry system started")
        return True
    
    def stop(self):
        """Stop integrated system"""
        self.publisher.disconnect()
        logger.info("Integrated telemetry system stopped")
    
    def update_from_sources(self, gps_data=None, imu_data=None, adas_results=None):
        """Update telemetry from various sources"""
        
        # Update GPS data
        if gps_data:
            self.publisher.update_gps_data(
                latitude=gps_data.get('lat', 0),
                longitude=gps_data.get('lon', 0),
                altitude=gps_data.get('alt', 0),
                speed=gps_data.get('speed', 0),
                heading=gps_data.get('heading', 0)
            )
        
        # Update ADAS data
        if adas_results:
            lane = adas_results.get('lane')
            objects = adas_results.get('objects', [])
            sign = adas_results.get('sign')
            
            self.publisher.update_adas_data(
                lane_departure=lane.lane_departure if lane else 0,
                objects_detected=len(objects),
                traffic_sign=sign.sign_type if sign else None,
                confidence=sign.confidence if sign else 0
            )
            
            # Check for alerts
            if lane and abs(lane.lane_departure) > 0.3:
                self.publisher.publish_alert(
                    'lane_departure',
                    f'Lane departure: {lane.lane_departure:.2f}',
                    'warning'
                )
            
            for obj in objects:
                if obj.distance and obj.distance < 5:
                    self.publisher.publish_alert(
                        'collision_warning',
                        f'{obj.class_name} detected at {obj.distance:.1f}m',
                        'critical'
                    )
        
        # Update V2X data
        if self.v2x:
            nearby = self.v2x.get_nearby_vehicles()
            hazards = self.v2x.get_hazards_ahead()
            emergency = self.v2x.get_emergency_vehicles_nearby()
            
            self.publisher.update_v2x_data(
                nearby_vehicles=len(nearby),
                hazards=len(hazards),
                emergency_vehicles=len(emergency),
                messages_received=self.v2x.statistics.bsm_received
            )
    
    # V2X Callbacks
    def _on_v2x_bsm(self, vehicle):
        """Handle V2X BSM received"""
        if vehicle.distance < 20:
            self.publisher.publish_alert(
                'nearby_vehicle',
                f'Vehicle {vehicle.vehicle_id} at {vehicle.distance:.1f}m',
                'info'
            )
    
    def _on_v2x_hazard(self, hazard):
        """Handle V2X hazard received"""
        self.publisher.publish_alert(
            'hazard_warning',
            f'{hazard.description} at {hazard.distance:.0f}m',
            'warning'
        )
    
    def _on_v2x_emergency(self, data):
        """Handle V2X emergency vehicle"""
        self.publisher.publish_alert(
            'emergency_vehicle',
            f'Emergency vehicle at {data["distance"]:.0f}m',
            'critical'
        )

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage with simulated data"""
    
    # Create telemetry publisher
    telemetry = TelemetryPublisher()
    
    # Connect to broker
    if not telemetry.connect():
        logger.error("Failed to connect. Check MQTT broker settings.")
        return
    
    # Start publishing
    telemetry.start()
    
    try:
        logger.info("Publishing telemetry data... (Press Ctrl+C to stop)")
        
        # Simulate vehicle movement
        lat, lon = 30.0444, 31.2357
        heading = 45.0
        speed = 25.0
        
        while True:
            # Simulate GPS movement
            lat += 0.0001 * (speed / 100)
            lon += 0.0001 * (speed / 100)
            heading = (heading + 1) % 360
            
            # Update GPS
            telemetry.update_gps_data(
                latitude=lat,
                longitude=lon,
                altitude=74.5,
                speed=speed,
                heading=heading
            )
            
            # Update ADAS (simulated)
            telemetry.update_adas_data(
                lane_departure=0.05,
                objects_detected=3,
                traffic_sign="Speed limit (50km/h)",
                confidence=0.95
            )
            
            # Update V2X (simulated)
            telemetry.update_v2x_data(
                nearby_vehicles=2,
                hazards=0,
                emergency_vehicles=0,
                messages_received=125
            )
            
            # Print statistics
            stats = telemetry.get_statistics()
            print(f"\rMessages sent: {stats['messages_sent']} | "
                  f"Rate: {stats['avg_rate']:.1f} msg/s | "
                  f"Success: {stats['success_rate']:.1f}%", end='')
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nStopping telemetry...")
    finally:
        telemetry.disconnect()
        logger.info("Telemetry stopped")

if __name__ == "__main__":
    main()