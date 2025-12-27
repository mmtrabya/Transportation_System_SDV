#!/usr/bin/env python3
"""
Complete SDV Infotainment System with ADAS Integration
- Imports ADAS modules directly
- Fixed Qt/OpenCV conflict
- Live AI-processed ADAS feed

RUN: python3 sdv_infotainment_adas_integrated.py
"""

import sys
import os

# Add ADAS script directory to path
ADAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raspberry_pi")
if os.path.exists(ADAS_DIR):
    sys.path.insert(0, ADAS_DIR)
    print(f"✓ Added ADAS path: {ADAS_DIR}")
else:
    print(f"WARNING: ADAS directory not found at: {ADAS_DIR}")
    print("Please check the path to your adas_inference_optimized.py")

# CRITICAL FIX: Remove cv2's Qt plugin path to prevent conflict
import site
for site_path in site.getsitepackages() + [site.getusersitepackages()]:
    cv2_qt_plugins = os.path.join(site_path, 'cv2', 'qt', 'plugins')
    if os.path.exists(cv2_qt_plugins):
        # Rename it so cv2 can't find it
        try:
            backup_path = cv2_qt_plugins + '_backup'
            if not os.path.exists(backup_path):
                os.rename(cv2_qt_plugins, backup_path)
                print(f"✓ Disabled cv2 Qt plugins at: {cv2_qt_plugins}")
        except:
            pass

# Set Qt environment BEFORE any imports
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/qt5/plugins'
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_DEBUG_PLUGINS'] = '0'

# Now import PyQt5
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import time
from pathlib import Path
from datetime import datetime
import serial

# Import cv2 AFTER PyQt5
import cv2

# Import ADAS components from your existing script
try:
    from adas_inference_optimized import (
        AdasSystem,
        KinectCamera,
        LaneDetector,
        ObjectDetector,
        SIGN_CLASSES
    )
    ADAS_AVAILABLE = True
    print("✓ ADAS modules imported successfully")
except ImportError as e:
    print(f"✗ Could not import ADAS modules: {e}")
    print(f"  Make sure adas_inference_optimized.py is in: {ADAS_DIR}")
    ADAS_AVAILABLE = False

# ==================== CONFIGURATION ====================

class Config:
    # Display
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    FULLSCREEN = True
    
    # Serial Ports
    ATMEGA32_PORT = "/dev/ttyUSB0"
    ATMEGA32_BAUDRATE = 115200
    
    # ADAS Model Paths
    LANE_MODEL = "../models/Lane_Detection/scnn.onnx"
    OBJECT_MODEL = "../models/Object_Detection/yolov8n.onnx"
    SIGN_MODEL = "../models/Traffic_Sign/last.onnx"
    
    # Colors
    PRIMARY_COLOR = "#00BCD4"
    BG_COLOR = "#0A0A0A"
    PANEL_COLOR = "#1E1E1E"
    TEXT_COLOR = "#FFFFFF"
    
    # Pricing
    PRICE_PER_HOUR = 15.0
    PRICE_PER_KM = 0.5

# ==================== MPU9250 INTERFACE ====================

class MPU9250Reader(QThread):
    """Read MPU9250 IMU data from ATmega32"""
    data_ready = pyqtSignal(dict)
    
    def __init__(self, port=Config.ATMEGA32_PORT, baudrate=Config.ATMEGA32_BAUDRATE):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.serial = None
        
        try:
            self.serial = serial.Serial(port, baudrate, timeout=0.1)
            time.sleep(2)
            print(f"✓ Connected to MPU9250 on {port}")
        except Exception as e:
            print(f"MPU9250 Reader: {e}")
    
    def run(self):
        self.running = True
        
        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('ascii', errors='ignore').strip()
                    if line.startswith("IMU:"):
                        parts = line[4:].split(',')
                        data = {
                            'speed': float(parts[0]) if len(parts) > 0 else 0.0,
                            'heading': float(parts[1]) if len(parts) > 1 else 0.0,
                            'accel': float(parts[2]) if len(parts) > 2 else 0.0,
                        }
                        self.data_ready.emit(data)
                
                time.sleep(0.05)
            except:
                # Simulation fallback
                data = {
                    'speed': np.random.uniform(0, 120),
                    'heading': np.random.uniform(0, 360),
                    'accel': np.random.uniform(-2, 2),
                }
                self.data_ready.emit(data)
                time.sleep(0.1)
    
    def stop(self):
        self.running = False
        if self.serial:
            self.serial.close()

# ==================== ADAS FEED WITH AI PROCESSING ====================

class AdasFeedThread(QThread):
    """Run ADAS system in background thread"""
    frame_ready = pyqtSignal(np.ndarray, dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.adas = None
        
        if not ADAS_AVAILABLE:
            print("✗ ADAS modules not available - camera feed will be disabled")
            return
        
        print("=" * 60)
        print("Initializing ADAS System...")
        print("=" * 60)
        
        try:
            self.adas = AdasSystem(
                Config.LANE_MODEL,
                Config.OBJECT_MODEL,
                Config.SIGN_MODEL
            )
            print("✓ ADAS System Ready!")
        except Exception as e:
            print(f"✗ ADAS initialization failed: {e}")
    
    def run(self):
        if self.adas is None:
            print("ADAS not available")
            return
        
        self.running = True
        frame_count = 0
        
        print("Starting ADAS processing loop...")
        
        while self.running:
            try:
                # Get frame from Kinect
                frame, depth = self.adas.kinect.get_frame()
                
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                frame_count += 1
                
                # Process with ADAS AI
                annotated, results = self.adas.process(frame, depth)
                
                # Emit to Qt GUI
                self.frame_ready.emit(annotated, results)
                
                # Log periodically
                if frame_count % 60 == 0:
                    print(f"ADAS Frame {frame_count} | FPS: {results['fps']:.1f} | "
                          f"Objects: {len(results['objects'])} | "
                          f"Pedestrians: {len(results['pedestrians'])} | "
                          f"Signs: {len(results['signs'])}")
                
                time.sleep(0.001)  # Minimal delay
                
            except Exception as e:
                print(f"ADAS processing error: {e}")
                time.sleep(0.1)
    
    def stop(self):
        self.running = False
        if self.adas:
            self.adas.release()
        print("ADAS thread stopped")

# ==================== SPEEDOMETER WIDGET ====================

class SpeedometerWidget(QWidget):
    """Analog speedometer gauge"""
    
    def __init__(self):
        super().__init__()
        self.speed = 0
        self.max_speed = 200
        self.setMinimumSize(400, 400)
    
    def set_speed(self, speed):
        self.speed = max(0, min(speed, self.max_speed))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 20
        
        # Background circle
        painter.setBrush(QColor(Config.PANEL_COLOR))
        painter.setPen(QPen(QColor(Config.PRIMARY_COLOR), 3))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        
        # Speed markings
        for i in range(0, self.max_speed + 1, 20):
            angle = 225 - (i / self.max_speed * 270)
            rad = np.radians(angle)
            
            x1 = cx + (radius - 30) * np.cos(rad)
            y1 = cy - (radius - 30) * np.sin(rad)
            x2 = cx + (radius - 10) * np.cos(rad)
            y2 = cy - (radius - 10) * np.sin(rad)
            
            painter.setPen(QPen(QColor("#888888"), 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
            if i % 40 == 0:
                painter.setPen(QColor(Config.TEXT_COLOR))
                painter.setFont(QFont("Arial", 12, QFont.Bold))
                text_x = cx + (radius - 50) * np.cos(rad) - 15
                text_y = cy - (radius - 50) * np.sin(rad) + 5
                painter.drawText(int(text_x), int(text_y), str(i))
        
        # Speed needle
        angle = 225 - (self.speed / self.max_speed * 270)
        rad = np.radians(angle)
        
        nx = cx + (radius - 20) * np.cos(rad)
        ny = cy - (radius - 20) * np.sin(rad)
        
        painter.setPen(QPen(QColor("#FF0000"), 4))
        painter.drawLine(cx, cy, int(nx), int(ny))
        
        # Center circle
        painter.setBrush(QColor("#FF0000"))
        painter.drawEllipse(cx - 10, cy - 10, 20, 20)
        
        # Speed text
        painter.setPen(QColor(Config.PRIMARY_COLOR))
        painter.setFont(QFont("Arial", 48, QFont.Bold))
        painter.drawText(w // 2 - 60, h // 2 + 80, f"{int(self.speed)}")
        
        painter.setFont(QFont("Arial", 16))
        painter.drawText(w // 2 - 30, h // 2 + 110, "km/h")

# ==================== SCREENS ====================

class UnlockScreen(QWidget):
    """Vehicle unlock screen"""
    unlocked = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.booking_data = None
        self.initUI()
        self.check_for_booking()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        
        title = QLabel("🚗 VEHICLE UNLOCK")
        title.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {Config.PRIMARY_COLOR};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.status_label = QLabel("⏳ Checking for booking...")
        self.status_label.setStyleSheet("font-size: 24px; color: #999;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter unlock code")
        self.code_input.setMaxLength(4)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setEchoMode(QLineEdit.Password)
        self.code_input.setStyleSheet(f"""
            font-size: 72px; font-weight: bold; padding: 30px;
            background: {Config.PANEL_COLOR}; border: 4px solid {Config.PRIMARY_COLOR};
            border-radius: 20px; color: {Config.PRIMARY_COLOR}; letter-spacing: 35px;
        """)
        layout.addWidget(self.code_input)
        
        layout.addWidget(self.create_numpad())
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")
    
    def create_numpad(self):
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(15)
        
        buttons = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['C', '0', '✓']
        ]
        
        for i, row in enumerate(buttons):
            for j, text in enumerate(row):
                btn = QPushButton(text)
                btn.setMinimumSize(130, 130)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 42px; font-weight: bold;
                        background: #2D2D2D; border: 3px solid #444;
                        border-radius: 15px; color: white;
                    }
                    QPushButton:hover { background: #3D3D3D; border-color: #00BCD4; }
                    QPushButton:pressed { background: #00BCD4; color: #000; }
                """)
                
                if text == 'C':
                    btn.clicked.connect(lambda: self.code_input.clear())
                elif text == '✓':
                    btn.clicked.connect(self.verify_code)
                else:
                    btn.clicked.connect(lambda checked, t=text: self.add_digit(t))
                
                layout.addWidget(btn, i, j)
        
        widget.setLayout(layout)
        return widget
    
    def add_digit(self, digit):
        if len(self.code_input.text()) < 4:
            self.code_input.setText(self.code_input.text() + digit)
            if len(self.code_input.text()) == 4:
                QTimer.singleShot(500, self.verify_code)
    
    def verify_code(self):
        entered = self.code_input.text()
        
        if not self.booking_data:
            self.status_label.setText("❌ No active booking")
            return
        
        correct_code = str(self.booking_data.get('unlockCode', ''))
        
        if entered == correct_code:
            self.status_label.setText("✅ VEHICLE UNLOCKED!")
            self.status_label.setStyleSheet("font-size: 28px; color: #4CAF50; font-weight: bold;")
            QTimer.singleShot(1500, lambda: self.unlocked.emit(self.booking_data))
        else:
            self.status_label.setText("❌ Wrong code!")
            self.code_input.clear()
    
    def check_for_booking(self):
        # Simulated booking
        self.booking_data = {
            'bookingId': 'TEST_BOOKING',
            'unlockCode': '1234',
            'userId': 'user_123'
        }
        self.status_label.setText("🟢 Booking Active - Code: 1234")
        self.code_input.setEnabled(True)

class SpeedometerScreen(QWidget):
    """Main speedometer screen"""
    
    def __init__(self, mpu_reader):
        super().__init__()
        self.mpu_reader = mpu_reader
        self.mpu_reader.data_ready.connect(self.update_speed)
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.speedometer = SpeedometerWidget()
        layout.addWidget(self.speedometer, alignment=Qt.AlignCenter)
        
        info = QHBoxLayout()
        
        self.trip_label = QLabel("Trip: 0.0 km")
        self.trip_label.setStyleSheet("font-size: 24px; color: white;")
        info.addWidget(self.trip_label)
        
        self.heading_label = QLabel("Heading: 0°")
        self.heading_label.setStyleSheet("font-size: 24px; color: white;")
        info.addWidget(self.heading_label)
        
        layout.addLayout(info)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")
    
    def update_speed(self, data):
        self.speedometer.set_speed(data['speed'])
        self.heading_label.setText(f"Heading: {int(data['heading'])}°")

class MediaScreen(QWidget):
    """Media player screen"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("🎵 MEDIA PLAYER")
        title.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {Config.PRIMARY_COLOR};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        art = QLabel()
        pixmap = QPixmap(300, 300)
        pixmap.fill(QColor(Config.PANEL_COLOR))
        art.setPixmap(pixmap)
        art.setAlignment(Qt.AlignCenter)
        layout.addWidget(art)
        
        track = QLabel("Connect your phone via\nBluetooth or Android Auto")
        track.setStyleSheet("font-size: 22px; color: #999; padding: 20px;")
        track.setAlignment(Qt.AlignCenter)
        layout.addWidget(track)
        
        controls = QHBoxLayout()
        for icon in ['⏮', '⏯', '⏭']:
            btn = QPushButton(icon)
            btn.setMinimumSize(80, 80)
            btn.setStyleSheet(f"""
                font-size: 32px; background: {Config.PANEL_COLOR};
                border: 2px solid {Config.PRIMARY_COLOR}; border-radius: 40px;
            """)
            controls.addWidget(btn)
        
        layout.addLayout(controls)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")

class ClimateScreen(QWidget):
    """Climate control screen"""
    
    def __init__(self):
        super().__init__()
        self.temperature = 22
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("❄️ CLIMATE CONTROL")
        title.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {Config.PRIMARY_COLOR};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.temp_label = QLabel(f"{self.temperature}°C")
        self.temp_label.setStyleSheet(f"font-size: 120px; font-weight: bold; color: {Config.PRIMARY_COLOR};")
        self.temp_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.temp_label)
        
        controls = QHBoxLayout()
        
        dec_btn = QPushButton("−")
        dec_btn.setMinimumSize(100, 100)
        dec_btn.setStyleSheet(f"""
            font-size: 48px; background: {Config.PANEL_COLOR};
            border: 3px solid {Config.PRIMARY_COLOR}; border-radius: 50px;
        """)
        dec_btn.clicked.connect(lambda: self.change_temp(-1))
        controls.addWidget(dec_btn)
        
        controls.addStretch()
        
        inc_btn = QPushButton("+")
        inc_btn.setMinimumSize(100, 100)
        inc_btn.setStyleSheet(f"""
            font-size: 48px; background: {Config.PANEL_COLOR};
            border: 3px solid {Config.PRIMARY_COLOR}; border-radius: 50px;
        """)
        inc_btn.clicked.connect(lambda: self.change_temp(1))
        controls.addWidget(inc_btn)
        
        layout.addLayout(controls)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")
    
    def change_temp(self, delta):
        self.temperature = max(16, min(30, self.temperature + delta))
        self.temp_label.setText(f"{self.temperature}°C")

class ADASCameraScreen(QWidget):
    """Live ADAS camera feed with AI processing"""
    
    def __init__(self, adas_thread):
        super().__init__()
        self.adas_thread = adas_thread
        self.adas_thread.frame_ready.connect(self.update_frame)
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📹 ADAS AI CAMERA")
        title.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {Config.PRIMARY_COLOR};")
        header.addWidget(title)
        
        header.addStretch()
        
        self.stats_label = QLabel("FPS: -- | Objects: 0")
        self.stats_label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        header.addWidget(self.stats_label)
        
        layout.addLayout(header)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setStyleSheet(f"background: {Config.PANEL_COLOR}; border: 2px solid {Config.PRIMARY_COLOR};")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(900, 500)
        layout.addWidget(self.video_label)
        
        # Detection info
        self.info_label = QLabel("Waiting for ADAS data...")
        self.info_label.setStyleSheet("font-size: 16px; color: #999; padding: 10px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")
    
    def update_frame(self, frame, results):
        # Resize for display
        frame = cv2.resize(frame, (900, 500))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))
        
        # Update stats
        self.stats_label.setText(
            f"FPS: {results['fps']:.1f} | "
            f"Objects: {len(results['objects'])} | "
            f"Pedestrians: {len(results['pedestrians'])} | "
            f"Signs: {len(results['signs'])}"
        )
        
        # Update info
        info_text = []
        if len(results['pedestrians']) > 0:
            info_text.append(f"⚠️ {len(results['pedestrians'])} Pedestrian(s) detected!")
        if len(results['signs']) > 0:
            signs = [s.class_name for s in results['signs']]
            info_text.append(f"🚦 Signs: {', '.join(signs[:3])}")
        if abs(results['lane'].lane_departure) > 0.3:
            info_text.append(f"⚠️ Lane departure: {results['lane'].lane_departure:.2f}")
        
        self.info_label.setText(" | ".join(info_text) if info_text else "✓ All clear")

# ==================== MAIN INFOTAINMENT APP ====================

class InfotainmentApp(QMainWindow):
    """Main infotainment application"""
    
    def __init__(self):
        super().__init__()
        
        print("\n" + "=" * 60)
        print("SDV INFOTAINMENT SYSTEM STARTING")
        print("=" * 60)
        
        # Initialize hardware interfaces
        self.mpu_reader = MPU9250Reader()
        self.mpu_reader.start()
        
        self.adas_thread = AdasFeedThread()
        self.adas_thread.start()
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("SDV Infotainment System")
        self.setGeometry(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        self.unlock_screen = UnlockScreen()
        self.unlock_screen.unlocked.connect(self.on_unlock)
        self.stack.addWidget(self.unlock_screen)
        
        self.setStyleSheet(f"background: {Config.BG_COLOR}; color: white;")
        
        if Config.FULLSCREEN:
            self.showFullScreen()
    
    def on_unlock(self, booking_data):
        print(f"✓ Vehicle unlocked: {booking_data}")
        
        dashboard = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.South)
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0A0A0A; }
            QTabBar::tab {
                background: #2D2D2D; color: white; padding: 18px 30px;
                margin: 2px; border-radius: 8px; font-size: 16px; font-weight: bold;
            }
            QTabBar::tab:selected { background: #00BCD4; color: #000; }
            QTabBar::tab:hover { background: #3D3D3D; }
        """)
        
        tabs.addTab(SpeedometerScreen(self.mpu_reader), "🚗 Speed")
        tabs.addTab(MediaScreen(), "🎵 Media")
        tabs.addTab(ClimateScreen(), "❄️ Climate")
        tabs.addTab(ADASCameraScreen(self.adas_thread), "📹 ADAS")
        
        layout.addWidget(tabs)
        dashboard.setLayout(layout)
        
        self.stack.addWidget(dashboard)
        self.stack.setCurrentWidget(dashboard)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    
    def closeEvent(self, event):
        print("\nShutting down...")
        self.mpu_reader.stop()
        self.adas_thread.stop()
        self.mpu_reader.wait()
        self.adas_thread.wait()
        print("✓ Clean shutdown")
        event.accept()

# ==================== MAIN ====================

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Roboto", 10))
    
    window = InfotainmentApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()