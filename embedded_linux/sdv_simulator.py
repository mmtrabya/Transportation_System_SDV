#!/usr/bin/env python3
"""
SDV Vehicle Simulator
Physics-based vehicle simulation with environment
Location: ~/Graduation_Project_SDV/embedded_linux/sdv_simulator.py

Features:
- Realistic vehicle dynamics
- Traffic simulation
- Road obstacles
- Weather conditions
- GPS simulation
- Sensor data generation
"""

import sys
import random
import math
import time
import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except:
    MQTT_AVAILABLE = False

# ==================== CONFIGURATION ====================

class SimConfig:
    """Simulator configuration"""
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 800
    FPS = 60
    
    # Physics
    MAX_SPEED = 150  # km/h
    ACCELERATION = 5.0  # m/s²
    BRAKING = 8.0  # m/s²
    TURN_RATE = 90  # degrees/second
    
    # World
    WORLD_WIDTH = 5000
    WORLD_HEIGHT = 5000
    
    # MQTT
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    VEHICLE_ID = "SDV_001"

# ==================== VEHICLE CLASS ====================

class Vehicle:
    """Simulated vehicle with physics"""
    
    def __init__(self, x, y, vehicle_id="SDV_001"):
        self.id = vehicle_id
        self.x = x
        self.y = y
        self.speed = 0  # km/h
        self.heading = 0  # degrees (0 = North)
        self.acceleration = 0
        
        # Vehicle properties
        self.width = 40
        self.height = 80
        self.color = QColor(0, 120, 215)
        
        # Sensors
        self.ultrasonic = {'front': 100, 'rear': 100, 'left': 100, 'right': 100}
        self.imu = {'accel_x': 0, 'accel_y': 0, 'gyro_z': 0, 'yaw': 0}
        
        # GPS (lat/lon simulation)
        self.lat = 30.0444
        self.lon = 31.2357
        
        # State
        self.throttle = 0
        self.brake = 0
        self.steering = 0
        self.gear = 'P'
        
        # Trip
        self.trip_distance = 0
        self.trip_time = 0
    
    def update(self, dt):
        """Update vehicle physics"""
        # Calculate acceleration
        if self.gear in ['D', 'R']:
            target_accel = self.throttle * SimConfig.ACCELERATION
            if self.brake > 0:
                target_accel = -self.brake * SimConfig.BRAKING
            
            self.acceleration = target_accel
            
            # Update speed
            speed_ms = self.speed / 3.6  # Convert to m/s
            speed_ms += self.acceleration * dt
            speed_ms = max(0, speed_ms)
            
            # Reverse
            if self.gear == 'R':
                speed_ms = -abs(speed_ms)
                speed_ms = max(-20/3.6, speed_ms)  # Max reverse: 20 km/h
            else:
                speed_ms = min(SimConfig.MAX_SPEED/3.6, speed_ms)
            
            self.speed = speed_ms * 3.6  # Convert back to km/h
            
            # Update heading (steering)
            if abs(self.speed) > 1:
                turn_rate = self.steering * SimConfig.TURN_RATE * (abs(self.speed) / 50)
                self.heading += turn_rate * dt
                self.heading %= 360
            
            # Update position
            speed_ms = self.speed / 3.6
            heading_rad = math.radians(self.heading)
            
            dx = math.sin(heading_rad) * speed_ms * dt
            dy = -math.cos(heading_rad) * speed_ms * dt
            
            self.x += dx
            self.y += dy
            
            # Update GPS (simplified: 1 pixel = 1 meter)
            # Rough: 111km per degree latitude
            self.lat += (dy / 111000.0)
            self.lon += (dx / (111000.0 * math.cos(math.radians(self.lat))))
            
            # Update trip
            distance = math.sqrt(dx*dx + dy*dy)
            self.trip_distance += distance
            self.trip_time += dt
        
        # Update IMU
        self.imu['accel_x'] = self.acceleration
        self.imu['yaw'] = self.heading
        self.imu['gyro_z'] = self.steering * 10
    
    def setThrottle(self, value):
        """Set throttle (0-1)"""
        self.throttle = max(0, min(1, value))
        self.brake = 0
    
    def setBrake(self, value):
        """Set brake (0-1)"""
        self.brake = max(0, min(1, value))
        self.throttle = 0
    
    def setSteering(self, value):
        """Set steering (-1 to 1)"""
        self.steering = max(-1, min(1, value))
    
    def setGear(self, gear):
        """Set gear (P, R, N, D)"""
        if gear in ['P', 'R', 'N', 'D']:
            self.gear = gear
            if gear == 'P':
                self.speed = 0
    
    def draw(self, painter, camera_x, camera_y):
        """Draw vehicle"""
        painter.save()
        
        # Transform to screen coordinates
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        
        painter.translate(screen_x, screen_y)
        painter.rotate(self.heading)
        
        # Draw vehicle body
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(Qt.white, 2))
        painter.drawRoundedRect(-self.width//2, -self.height//2, 
                               self.width, self.height, 5, 5)
        
        # Draw direction indicator
        painter.setBrush(QBrush(Qt.yellow))
        painter.drawPolygon(QPolygon([
            QPoint(0, -self.height//2 - 5),
            QPoint(-5, -self.height//2),
            QPoint(5, -self.height//2)
        ]))
        
        # Draw windows
        painter.setBrush(QBrush(QColor(150, 200, 255, 100)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(-self.width//2 + 5, -self.height//2 + 10, 
                        self.width - 10, 20)
        
        painter.restore()

# ==================== OTHER VEHICLES ====================

class TrafficVehicle:
    """AI-controlled traffic vehicle"""
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = random.uniform(40, 80)
        self.heading = random.randint(0, 360)
        self.width = 35
        self.height = 70
        self.color = QColor(random.randint(100, 200), 
                          random.randint(100, 200), 
                          random.randint(100, 200))
    
    def update(self, dt):
        """Update traffic vehicle"""
        # Simple straight-line motion
        heading_rad = math.radians(self.heading)
        speed_ms = self.speed / 3.6
        
        dx = math.sin(heading_rad) * speed_ms * dt
        dy = -math.cos(heading_rad) * speed_ms * dt
        
        self.x += dx
        self.y += dy
    
    def draw(self, painter, camera_x, camera_y):
        """Draw traffic vehicle"""
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        
        painter.save()
        painter.translate(screen_x, screen_y)
        painter.rotate(self.heading)
        
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(-self.width//2, -self.height//2, 
                        self.width, self.height)
        
        painter.restore()

# ==================== OBSTACLES ====================

class Obstacle:
    """Road obstacle"""
    
    def __init__(self, x, y, obstacle_type='cone'):
        self.x = x
        self.y = y
        self.type = obstacle_type
        self.size = 20
    
    def draw(self, painter, camera_x, camera_y):
        """Draw obstacle"""
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        
        if self.type == 'cone':
            painter.setBrush(QBrush(QColor(255, 140, 0)))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygon([
                QPoint(int(screen_x), int(screen_y - self.size)),
                QPoint(int(screen_x - self.size//2), int(screen_y + self.size//2)),
                QPoint(int(screen_x + self.size//2), int(screen_y + self.size//2))
            ]))
        elif self.type == 'barrier':
            painter.setBrush(QBrush(Qt.red))
            painter.drawRect(int(screen_x - 30), int(screen_y - 5), 60, 10)

# ==================== SIMULATOR WIDGET ====================

class SimulatorWidget(QWidget):
    """Main simulator display"""
    
    dataGenerated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # World
        self.vehicle = Vehicle(SimConfig.WORLD_WIDTH//2, SimConfig.WORLD_HEIGHT//2)
        self.traffic = []
        self.obstacles = []
        
        # Generate traffic
        for _ in range(10):
            x = random.randint(0, SimConfig.WORLD_WIDTH)
            y = random.randint(0, SimConfig.WORLD_HEIGHT)
            self.traffic.append(TrafficVehicle(x, y))
        
        # Generate obstacles
        for _ in range(20):
            x = random.randint(0, SimConfig.WORLD_WIDTH)
            y = random.randint(0, SimConfig.WORLD_HEIGHT)
            self.obstacles.append(Obstacle(x, y, random.choice(['cone', 'barrier'])))
        
        # Camera
        self.camera_x = self.vehicle.x
        self.camera_y = self.vehicle.y
        
        # Input
        self.keys_pressed = set()
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(1000 // SimConfig.FPS)
        
        self.last_time = time.time()
    
    def update_simulation(self):
        """Update simulation"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Handle input
        self._handle_input()
        
        # Update vehicle
        self.vehicle.update(dt)
        
        # Update traffic
        for car in self.traffic:
            car.update(dt)
            
            # Respawn if too far
            dist = math.sqrt((car.x - self.vehicle.x)**2 + (car.y - self.vehicle.y)**2)
            if dist > 1000:
                angle = random.uniform(0, 2 * math.pi)
                car.x = self.vehicle.x + math.cos(angle) * 500
                car.y = self.vehicle.y + math.sin(angle) * 500
        
        # Update camera (follow vehicle)
        self.camera_x = self.vehicle.x
        self.camera_y = self.vehicle.y
        
        # Emit data for telemetry
        self._emit_data()
        
        # Redraw
        self.update()
    
    def _handle_input(self):
        """Handle keyboard input"""
        # Throttle/Brake
        if Qt.Key_W in self.keys_pressed or Qt.Key_Up in self.keys_pressed:
            self.vehicle.setThrottle(0.7)
        elif Qt.Key_S in self.keys_pressed or Qt.Key_Down in self.keys_pressed:
            self.vehicle.setBrake(0.8)
        else:
            self.vehicle.setThrottle(0)
            self.vehicle.setBrake(0.1)  # Gentle coast braking
        
        # Steering
        if Qt.Key_A in self.keys_pressed or Qt.Key_Left in self.keys_pressed:
            self.vehicle.setSteering(-0.6)
        elif Qt.Key_D in self.keys_pressed or Qt.Key_Right in self.keys_pressed:
            self.vehicle.setSteering(0.6)
        else:
            self.vehicle.setSteering(0)
        
        # Gear changes
        if Qt.Key_1 in self.keys_pressed:
            self.vehicle.setGear('P')
        elif Qt.Key_2 in self.keys_pressed:
            self.vehicle.setGear('R')
        elif Qt.Key_3 in self.keys_pressed:
            self.vehicle.setGear('N')
        elif Qt.Key_4 in self.keys_pressed:
            self.vehicle.setGear('D')
    
    def _emit_data(self):
        """Emit vehicle data for telemetry"""
        # Count nearby vehicles
        nearby = 0
        for car in self.traffic:
            dist = math.sqrt((car.x - self.vehicle.x)**2 + (car.y - self.vehicle.y)**2)
            if dist < 200:
                nearby += 1
        
        data = {
            'gps': {
                'lat': self.vehicle.lat,
                'lon': self.vehicle.lon,
                'speed': abs(self.vehicle.speed),
                'heading': self.vehicle.heading,
                'alt': 74.5
            },
            'adas': {
                'lane_departure': random.uniform(-0.1, 0.1),
                'objects': nearby,
                'sign': 'Speed Limit 80',
                'confidence': 0.95
            },
            'v2x': {
                'nearby': nearby,
                'hazards': len([o for o in self.obstacles 
                               if math.sqrt((o.x - self.vehicle.x)**2 + 
                                          (o.y - self.vehicle.y)**2) < 200]),
                'emergency': 0,
                'messages': random.randint(100, 150)
            },
            'system': {
                'cpu': random.randint(30, 50),
                'memory': random.randint(40, 60),
                'temp': random.randint(42, 55)
            },
            'vehicle': {
                'gear': self.vehicle.gear,
                'throttle': self.vehicle.throttle,
                'brake': self.vehicle.brake,
                'steering': self.vehicle.steering,
                'trip_distance': self.vehicle.trip_distance / 1000,  # km
                'trip_time': self.vehicle.trip_time
            }
        }
        
        self.dataGenerated.emit(data)
    
    def paintEvent(self, event):
        """Draw simulation"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background (grass)
        painter.fillRect(0, 0, width, height, QColor(34, 139, 34))
        
        # Draw grid (roads)
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        grid_size = 200
        
        start_x = int((self.camera_x - width//2) // grid_size * grid_size)
        start_y = int((self.camera_y - height//2) // grid_size * grid_size)
        
        for x in range(start_x, start_x + width + grid_size, grid_size):
            screen_x = x - self.camera_x + width//2
            painter.fillRect(int(screen_x - 25), 0, 50, height, QColor(80, 80, 80))
        
        for y in range(start_y, start_y + height + grid_size, grid_size):
            screen_y = y - self.camera_y + height//2
            painter.fillRect(0, int(screen_y - 25), width, 50, QColor(80, 80, 80))
        
        # Draw road markings
        painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
        for x in range(start_x, start_x + width + grid_size, grid_size):
            screen_x = x - self.camera_x + width//2
            painter.drawLine(int(screen_x), 0, int(screen_x), height)
        
        for y in range(start_y, start_y + height + grid_size, grid_size):
            screen_y = y - self.camera_y + height//2
            painter.drawLine(0, int(screen_y), width, int(screen_y))
        
        # Draw obstacles
        for obstacle in self.obstacles:
            obstacle.draw(painter, self.camera_x - width//2, self.camera_y - height//2)
        
        # Draw traffic
        for car in self.traffic:
            car.draw(painter, self.camera_x - width//2, self.camera_y - height//2)
        
        # Draw player vehicle
        self.vehicle.draw(painter, self.camera_x - width//2, self.camera_y - height//2)
        
        # Draw HUD
        self._draw_hud(painter)
    
    def _draw_hud(self, painter):
        """Draw heads-up display"""
        width = self.width()
        height = self.height()
        
        # Semi-transparent background
        painter.fillRect(0, 0, width, 60, QColor(0, 0, 0, 180))
        painter.fillRect(0, height - 80, width, 80, QColor(0, 0, 0, 180))
        
        # Speed
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 32, QFont.Bold))
        painter.drawText(20, 45, f"{abs(self.vehicle.speed):.0f}")
        painter.setFont(QFont('Arial', 14))
        painter.drawText(20, 55, "km/h")
        
        # Gear
        painter.setFont(QFont('Arial', 36, QFont.Bold))
        gear_color = QColor(0, 200, 0) if self.vehicle.gear == 'D' else Qt.white
        painter.setPen(gear_color)
        painter.drawText(120, 45, self.vehicle.gear)
        
        # Heading
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 16))
        painter.drawText(200, 40, f"HDG: {self.vehicle.heading:.0f}°")
        
        # Position
        painter.drawText(width - 250, 40, 
                        f"GPS: {self.vehicle.lat:.4f}, {self.vehicle.lon:.4f}")
        
        # Controls hint
        painter.setFont(QFont('Arial', 12))
        painter.drawText(20, height - 60, "Controls:")
        painter.drawText(20, height - 40, "W/↑: Throttle  S/↓: Brake")
        painter.drawText(20, height - 20, "A/←: Left  D/→: Right")
        
        painter.drawText(250, height - 40, "Gears:")
        painter.drawText(250, height - 20, "1:Park  2:Reverse  3:Neutral  4:Drive")
        
        # Trip info
        painter.drawText(width - 200, height - 40, 
                        f"Trip: {self.vehicle.trip_distance/1000:.1f} km")
        mins = int(self.vehicle.trip_time // 60)
        secs = int(self.vehicle.trip_time % 60)
        painter.drawText(width - 200, height - 20, f"Time: {mins}:{secs:02d}")
    
    def keyPressEvent(self, event):
        """Handle key press"""
        self.keys_pressed.add(event.key())
    
    def keyReleaseEvent(self, event):
        """Handle key release"""
        self.keys_pressed.discard(event.key())

# ==================== MAIN WINDOW ====================

class SimulatorWindow(QMainWindow):
    """Main simulator window"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # MQTT client
        self.mqtt_client = None
        if MQTT_AVAILABLE:
            self._setup_mqtt()
    
    def initUI(self):
        """Initialize UI"""
        self.setWindowTitle("SDV Vehicle Simulator")
        self.setGeometry(100, 100, SimConfig.WINDOW_WIDTH, SimConfig.WINDOW_HEIGHT)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Simulator widget
        self.simulator = SimulatorWidget()
        self.simulator.dataGenerated.connect(self._on_data_generated)
        layout.addWidget(self.simulator)
        
        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
    
    def _create_control_panel(self):
        """Create control panel"""
        panel = QWidget()
        panel.setMaximumHeight(100)
        layout = QHBoxLayout()
        panel.setLayout(layout)
        
        # Reset button
        reset_btn = QPushButton("🔄 Reset Position")
        reset_btn.clicked.connect(self._reset_position)
        layout.addWidget(reset_btn)
        
        # Add traffic button
        traffic_btn = QPushButton("🚗 Add Traffic")
        traffic_btn.clicked.connect(self._add_traffic)
        layout.addWidget(traffic_btn)
        
        # Spawn obstacle button
        obstacle_btn = QPushButton("⚠ Add Obstacle")
        obstacle_btn.clicked.connect(self._add_obstacle)
        layout.addWidget(obstacle_btn)
        
        layout.addStretch()
        
        # MQTT status
        self.mqtt_label = QLabel("MQTT: Disconnected")
        layout.addWidget(self.mqtt_label)
        
        return panel
    
    def _setup_mqtt(self):
        """Setup MQTT publishing"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(SimConfig.MQTT_BROKER, SimConfig.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            self.mqtt_label.setText("MQTT: Connected ✓")
        except:
            self.mqtt_label.setText("MQTT: Failed ✗")
    
    def _on_data_generated(self, data):
        """Handle generated data"""
        # Publish to MQTT
        if self.mqtt_client:
            try:
                topics = {
                    'gps': f"sdv/{SimConfig.VEHICLE_ID}/gps",
                    'adas': f"sdv/{SimConfig.VEHICLE_ID}/adas",
                    'v2x': f"sdv/{SimConfig.VEHICLE_ID}/v2x",
                    'system': f"sdv/{SimConfig.VEHICLE_ID}/system",
                }
                
                for key, topic in topics.items():
                    if key in data:
                        payload = json.dumps(data[key])
                        self.mqtt_client.publish(topic, payload)
            except:
                pass
    
    def _reset_position(self):
        """Reset vehicle position"""
        self.simulator.vehicle.x = SimConfig.WORLD_WIDTH // 2
        self.simulator.vehicle.y = SimConfig.WORLD_HEIGHT // 2
        self.simulator.vehicle.speed = 0
        self.simulator.vehicle.heading = 0
    
    def _add_traffic(self):
        """Add traffic vehicle"""
        angle = random.uniform(0, 2 * math.pi)
        x = self.simulator.vehicle.x + math.cos(angle) * 300
        y = self.simulator.vehicle.y + math.sin(angle) * 300
        self.simulator.traffic.append(TrafficVehicle(x, y))
    
    def _add_obstacle(self):
        """Add obstacle"""
        angle = random.uniform(0, 2 * math.pi)
        x = self.simulator.vehicle.x + math.cos(angle) * 150
        y = self.simulator.vehicle.y + math.sin(angle) * 150
        self.simulator.obstacles.append(Obstacle(x, y, random.choice(['cone', 'barrier'])))
    
    def closeEvent(self, event):
        """Handle close"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        event.accept()

# ==================== MAIN ====================

def main():
    app = QApplication(sys.argv)
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Vehicle Simulator                                   ║
    ║   Physics-based Driving Simulation                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    window = SimulatorWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()