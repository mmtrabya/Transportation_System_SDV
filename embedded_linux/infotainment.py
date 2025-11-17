#!/usr/bin/env python3
"""
SDV Driver Dashboard & Infotainment System with Firebase Integration
Complete in-vehicle display system with Qt5 and Firebase backend
Location: ~/Graduation_Project_SDV/embedded_linux/infotainment.py

Features:
- Digital Instrument Cluster
- Navigation Display
- ADAS Warnings
- Media Player
- Climate Control
- Vehicle Settings
- V2X Alerts
- Firebase Cloud Integration
- Vehicle Unlock System
"""

import sys
import os
import time
import json
import random
import math
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, db as firebase_db, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Firebase not available - running in simulation mode")
    print("Install with: pip install firebase-admin")

# ==================== CONFIGURATION ====================

class InfotainmentConfig:
    """System Configuration"""
    # Display
    FULLSCREEN = False
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    
    # Firebase
    FIREBASE_CREDENTIALS = "sdv_firebase_key.json"
    FIREBASE_DATABASE_URL = "https://sdv-ota-system-default-rtdb.europe-west1.firebasedatabase.app"
    VEHICLE_ID = "SDV_001"
    
    # Theme
    THEME_DARK = True
    PRIMARY_COLOR = "#FFD6FF3F"  # Custom yellow-green
    WARNING_COLOR = "#FFC107"
    DANGER_COLOR = "#F44336"
    SUCCESS_COLOR = "#4CAF50"
    BG_COLOR = "#121212"
    PANEL_COLOR = "#1E1E1E"
    TEXT_COLOR = "#FFFFFF"
    
    # Fonts
    FONT_MAIN = "Roboto"
    FONT_DIGITAL = "DS-Digital"
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY = "AIzaSyAYBEhbP3Zf0-z7Y5QKedoR1YIK6P4oLkE"

# ==================== FIREBASE MANAGER ====================

class FirebaseManager:
    """Manage Firebase connections and operations"""
    
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.firestore_db = None
        self.realtime_db = None
        self.storage_bucket = None
        self.connected = False
        
        if FIREBASE_AVAILABLE:
            self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(InfotainmentConfig.FIREBASE_CREDENTIALS)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': InfotainmentConfig.FIREBASE_DATABASE_URL,
                    'storageBucket': 'sdv-ota-system.firebasestorage.app'
                })
            
            self.firestore_db = firestore.client()
            self.realtime_db = firebase_db.reference()
            self.storage_bucket = storage.bucket()
            self.connected = True
            
            print(f"✓ Firebase connected for vehicle {self.vehicle_id}")
            
            # Register vehicle
            self._register_vehicle()
            
        except Exception as e:
            print(f"✗ Firebase initialization failed: {e}")
            self.connected = False
    
    # In infotainment.py, line ~75
    def _register_vehicle(self):
        """Register vehicle in Firestore"""
        try:
            vehicle_ref = self.firestore_db.collection('vehicles').document(self.vehicle_id)
            vehicle_ref.set({
                'vehicleId': self.vehicle_id,
                'model': 'Tesla Model S',
                'category': 'luxury',
                'licensePlate': 'SDV-001-EG',
                'color': 'Silver',
                'year': 2024,
                'seats': 5,
                'batteryCapacity': 100.0,
                'range': 600.0,
                'status': 'available',  # ← IMPORTANT: Must be "available"
                'isOnline': True,        # ← IMPORTANT: Must be True
                'batteryLevel': 85,
                'location': {            # ← EXACT Cairo coordinates
                    'latitude': 30.0444,
                    'longitude': 31.2357
                },
                'pricePerHour': 15.0,
                'pricePerKm': 0.5,
                'current_versions': {
                    'esp32_firmware': '1.0.0',
                    'atmega32_firmware': '1.0.0',
                    'software_version': '1.0.0'
                },
                'update_status': 'idle',
                'last_seen': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            print(f"✓ Vehicle {self.vehicle_id} registered at Cairo (30.0444, 31.2357)")
            
        except Exception as e:
            print(f"✗ Vehicle registration failed: {e}")
    
    def update_vehicle_data(self, data):
        """Update vehicle data in Firebase"""
        if not self.connected:
            return
        
        try:
            # Update Firestore
            vehicle_ref = self.firestore_db.collection('vehicles').document(self.vehicle_id)
            vehicle_ref.update({
                'last_seen': firestore.SERVER_TIMESTAMP,
                'status': 'online',
                'location': {
                    'latitude': data.get('gps', {}).get('lat', 0),
                    'longitude': data.get('gps', {}).get('lon', 0),
                    'speed': data.get('gps', {}).get('speed', 0),
                    'heading': data.get('gps', {}).get('heading', 0)
                }
            })
            
            # Update Realtime Database (for V2X)
            self.realtime_db.child('v2x/bsm').child(self.vehicle_id).set({
                'latitude': data.get('gps', {}).get('lat', 0),
                'longitude': data.get('gps', {}).get('lon', 0),
                'speed': data.get('gps', {}).get('speed', 0),
                'heading': data.get('gps', {}).get('heading', 0),
                'timestamp': int(time.time() * 1000)
            })
            
        except Exception as e:
            print(f"Error updating vehicle data: {e}")
    
    def check_for_updates(self):
        """Check for available OTA updates"""
        if not self.connected:
            return []
        
        try:
            updates_ref = self.firestore_db.collection('updates').where('active', '==', True)
            updates = []
            
            for doc in updates_ref.stream():
                update = doc.to_dict()
                updates.append(update)
            
            return updates
            
        except Exception as e:
            print(f"Error checking updates: {e}")
            return []
    
    def get_v2x_messages(self):
        """Get V2X messages for this vehicle"""
        if not self.connected:
            return []
        
        try:
            messages_ref = self.realtime_db.child('v2x/messages').child(self.vehicle_id)
            messages = messages_ref.get() or {}
            
            return list(messages.values())
            
        except Exception as e:
            print(f"Error getting V2X messages: {e}")
            return []
    
    def send_v2x_message(self, message_type, data):
        """Send V2X message"""
        if not self.connected:
            return
        
        try:
            timestamp = int(time.time() * 1000)
            
            if message_type == 'emergency':
                # Broadcast emergency
                self.realtime_db.child('v2x/emergency').child(str(timestamp)).set({
                    'from': self.vehicle_id,
                    'data': data,
                    'timestamp': timestamp
                })
            else:
                # Regular BSM
                self.realtime_db.child('v2x/bsm').child(self.vehicle_id).set({
                    **data,
                    'timestamp': timestamp
                })
            
        except Exception as e:
            print(f"Error sending V2X message: {e}")

# ==================== UNLOCK SCREEN ====================

class UnlockScreen(QWidget):
    """Vehicle unlock screen"""
    
    unlocked = pyqtSignal()
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.unlock_code = None
        self.attempts = 0
        self.max_attempts = 3
        self.initUI()
        self.check_unlock_required()
    
    def check_unlock_required(self):
        """Check if unlock is required from Firebase"""
        try:
            unlock_file = '/tmp/vehicle_unlock.json'
            if os.path.exists(unlock_file):
                with open(unlock_file, 'r') as f:
                    data = json.load(f)
                    
                    if data.get('enabled') and time.time() < data.get('expires', 0):
                        self.unlock_code = data.get('code')
                        return True
            
            # Check Firebase
            if self.firebase_manager.connected:
                doc = self.firebase_manager.firestore_db.collection('vehicle_locks').document(
                    self.firebase_manager.vehicle_id
                ).get()
                
                if doc.exists:
                    lock_data = doc.to_dict()
                    if lock_data.get('enabled') and time.time() < lock_data.get('expires', 0):
                        self.unlock_code = lock_data.get('code')
                        return True
            
            # No unlock required, emit signal immediately
            QTimer.singleShot(100, self.unlocked.emit)
            return False
            
        except Exception as e:
            print(f"Error checking unlock: {e}")
            QTimer.singleShot(100, self.unlocked.emit)
            return False
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Vehicle logo/icon
        logo = QLabel("🚗")
        logo.setStyleSheet("font-size: 72px;")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        
        # Title
        title = QLabel("Vehicle Locked")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #FFD6FF3F;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Enter Unlock Code")
        subtitle.setStyleSheet("font-size: 18px; color: #999;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Code input
        input_container = QWidget()
        input_layout = QHBoxLayout()
        input_container.setLayout(input_layout)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("____")
        self.code_input.setMaxLength(4)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setEchoMode(QLineEdit.Password)
        self.code_input.setStyleSheet("""
            QLineEdit {
                font-size: 72px;
                font-weight: bold;
                padding: 20px;
                background: #2D2D2D;
                border: 3px solid #FFD6FF3F;
                border-radius: 15px;
                letter-spacing: 20px;
                color: #FFD6FF3F;
            }
        """)
        input_layout.addStretch()
        input_layout.addWidget(self.code_input)
        input_layout.addStretch()
        
        layout.addWidget(input_container)
        
        # Numpad
        numpad_widget = QWidget()
        numpad_layout = QGridLayout()
        numpad_layout.setSpacing(10)
        numpad_widget.setLayout(numpad_layout)
        
        buttons = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['C', '0', '✓']
        ]
        
        for i, row in enumerate(buttons):
            for j, btn_text in enumerate(row):
                btn = QPushButton(btn_text)
                btn.setMinimumSize(100, 100)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 32px;
                        font-weight: bold;
                        background: #2D2D2D;
                        border-radius: 15px;
                        color: white;
                    }
                    QPushButton:hover {
                        background: #3D3D3D;
                    }
                    QPushButton:pressed {
                        background: #FFD6FF3F;
                        color: #000;
                    }
                """)
                
                if btn_text == 'C':
                    btn.clicked.connect(self.clear_input)
                elif btn_text == '✓':
                    btn.clicked.connect(self.verify_code)
                    btn.setStyleSheet(btn.styleSheet() + """
                        QPushButton {
                            background: #4CAF50;
                        }
                        QPushButton:hover {
                            background: #45a049;
                        }
                    """)
                else:
                    btn.clicked.connect(lambda checked, t=btn_text: self.add_digit(t))
                
                numpad_layout.addWidget(btn, i, j)
        
        layout.addWidget(numpad_widget)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; padding: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {InfotainmentConfig.BG_COLOR};")
    
    def add_digit(self, digit):
        """Add digit to code input"""
        if len(self.code_input.text()) < 4:
            self.code_input.setText(self.code_input.text() + digit)
    
    def clear_input(self):
        """Clear input"""
        self.code_input.clear()
        self.status_label.setText("")
    
    def verify_code(self):
        """Verify entered code"""
        entered_code = self.code_input.text()
        
        if len(entered_code) != 4:
            self.status_label.setText("Please enter 4 digits")
            self.status_label.setStyleSheet("font-size: 18px; color: #FFC107;")
            return
        
        # Verify code
        success = False
        message = ""
        
        if self.unlock_code and entered_code == str(self.unlock_code):
            success = True
            message = "Vehicle Unlocked!"
        else:
            success = False
            message = "Invalid Code"
        
        if success:
            self.status_label.setText("✓ " + message)
            self.status_label.setStyleSheet("font-size: 24px; color: #4CAF50; font-weight: bold;")
            
            # Log unlock event
            try:
                if self.firebase_manager.connected:
                    self.firebase_manager.firestore_db.collection('unlock_logs').add({
                        'vehicle_id': self.firebase_manager.vehicle_id,
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'success': True
                    })
            except:
                pass
            
            # Switch to main dashboard after 2 seconds
            QTimer.singleShot(2000, self.unlocked.emit)
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if remaining > 0:
                self.status_label.setText(f"✗ {message}. {remaining} attempts left")
                self.status_label.setStyleSheet("font-size: 18px; color: #F44336;")
                self.code_input.clear()
            else:
                self.status_label.setText("Too many failed attempts. Vehicle locked.")
                self.status_label.setStyleSheet("font-size: 18px; color: #F44336; font-weight: bold;")
                self.code_input.setEnabled(False)
                
                # Log failed unlock
                try:
                    if self.firebase_manager.connected:
                        self.firebase_manager.firestore_db.collection('unlock_logs').add({
                            'vehicle_id': self.firebase_manager.vehicle_id,
                            'timestamp': firestore.SERVER_TIMESTAMP,
                            'success': False,
                            'attempts': self.attempts
                        })
                except:
                    pass

# ==================== CUSTOM WIDGETS ====================

class DigitalSpeedometer(QWidget):
    """Digital speedometer with large numbers"""
    
    def __init__(self):
        super().__init__()
        self.speed = 0
        self.speed_limit = 80
        self.setMinimumSize(300, 300)
    
    def setSpeed(self, speed):
        self.speed = speed
        self.update()
    
    def setSpeedLimit(self, limit):
        self.speed_limit = limit
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        cx, cy = width // 2, height // 2
        
        # Speed ring
        radius = min(width, height) // 2 - 20
        color = QColor(InfotainmentConfig.SUCCESS_COLOR)
        
        if self.speed > self.speed_limit:
            color = QColor(InfotainmentConfig.DANGER_COLOR)
        elif self.speed > self.speed_limit * 0.9:
            color = QColor(InfotainmentConfig.WARNING_COLOR)
        
        # Draw outer ring
        painter.setPen(QPen(QColor("#333"), 8))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        
        # Draw speed arc
        percent = min(self.speed / 200.0, 1.0)
        angle = int(percent * 300 * 16)
        
        painter.setPen(QPen(color, 12))
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2,
                       120 * 16, -angle)
        
        # Draw speed value
        painter.setPen(QColor(InfotainmentConfig.TEXT_COLOR))
        font = QFont(InfotainmentConfig.FONT_DIGITAL, 72, QFont.Bold)
        painter.setFont(font)
        text = f"{int(self.speed)}"
        painter.drawText(cx - 100, cy - 40, 200, 80, Qt.AlignCenter, text)
        
        # Draw unit
        painter.setFont(QFont(InfotainmentConfig.FONT_MAIN, 16))
        painter.drawText(cx - 50, cy + 40, 100, 30, Qt.AlignCenter, "km/h")
        
        # Draw speed limit indicator
        if self.speed_limit > 0:
            painter.setPen(QPen(QColor("#666"), 2))
            painter.setBrush(QBrush(QColor("#2D2D2D")))
            painter.drawRoundedRect(cx - 40, cy - radius - 50, 80, 40, 5, 5)
            
            painter.setPen(QColor("white"))
            painter.setFont(QFont(InfotainmentConfig.FONT_MAIN, 20, QFont.Bold))
            painter.drawText(cx - 40, cy - radius - 50, 80, 40, 
                           Qt.AlignCenter, str(self.speed_limit))

class ADASWarningPanel(QWidget):
    """ADAS warnings and alerts"""
    
    def __init__(self):
        super().__init__()
        self.warnings = []
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        
        layout = QVBoxLayout()
        self.warning_label = QLabel("No Warnings")
        self.warning_label.setStyleSheet(f"""
            QLabel {{
                color: {InfotainmentConfig.SUCCESS_COLOR};
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
            }}
        """)
        self.warning_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.warning_label)
        
        self.setLayout(layout)
    
    def addWarning(self, warning_type, message):
        """Add warning message"""
        self.warnings.append({
            'type': warning_type,
            'message': message,
            'time': datetime.now()
        })
        
        self.warnings = self.warnings[-5:]
        self._updateDisplay()
    
    def clearWarnings(self):
        """Clear all warnings"""
        self.warnings = []
        self._updateDisplay()
    
    def _updateDisplay(self):
        """Update warning display"""
        if not self.warnings:
            self.warning_label.setText("No Warnings")
            self.warning_label.setStyleSheet(f"""
                QLabel {{
                    color: {InfotainmentConfig.SUCCESS_COLOR};
                    font-size: 18px;
                    font-weight: bold;
                    padding: 10px;
                }}
            """)
        else:
            latest = self.warnings[-1]
            color = InfotainmentConfig.WARNING_COLOR
            
            if latest['type'] in ['collision', 'emergency']:
                color = InfotainmentConfig.DANGER_COLOR
            
            self.warning_label.setText(f"⚠ {latest['message']}")
            self.warning_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 20px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: rgba(255, 0, 0, 0.1);
                    border: 2px solid {color};
                    border-radius: 5px;
                }}
            """)

# ==================== MAIN PAGES ====================

class InstrumentClusterPage(QWidget):
    """Main instrument cluster page"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Top bar
        top_bar = self._createTopBar()
        layout.addWidget(top_bar)
        
        # ADAS warnings
        self.adas_panel = ADASWarningPanel()
        layout.addWidget(self.adas_panel)
        
        # Main gauges
        gauges_layout = QHBoxLayout()
        
        # Speedometer
        self.speedometer = DigitalSpeedometer()
        gauges_layout.addWidget(self.speedometer, 1)
        
        # Info panel
        info_panel = self._createInfoPanel()
        gauges_layout.addWidget(info_panel)
        
        layout.addLayout(gauges_layout)
        
        # Bottom bar
        bottom_bar = self._createBottomBar()
        layout.addWidget(bottom_bar)
        
        self.setLayout(layout)
    
    def _createTopBar(self):
        """Create top status bar"""
        widget = QWidget()
        widget.setMaximumHeight(60)
        layout = QHBoxLayout()
        
        self.time_label = QLabel(datetime.now().strftime("%H:%M"))
        self.time_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.time_label)
        
        layout.addStretch()
        
        # Firebase status
        self.firebase_status = QLabel("☁ Cloud")
        self.firebase_status.setStyleSheet("font-size: 18px; color: #4CAF50;")
        layout.addWidget(self.firebase_status)
        
        temp_label = QLabel("🌡 22°C")
        temp_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(temp_label)
        
        battery_label = QLabel("🔋 85%")
        battery_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(battery_label)
        
        gps_label = QLabel("📡 GPS")
        gps_label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        layout.addWidget(gps_label)
        
        widget.setLayout(layout)
        return widget
    
    def _createInfoPanel(self):
        """Create info panel"""
        widget = QWidget()
        widget.setMaximumWidth(250)
        layout = QVBoxLayout()
        
        # Trip info
        trip_group = QGroupBox("Trip Info")
        trip_layout = QVBoxLayout()
        
        self.distance_label = QLabel("Distance: 0 km")
        self.avg_speed_label = QLabel("Avg Speed: 0 km/h")
        self.trip_time_label = QLabel("Time: 00:00")
        
        for label in [self.distance_label, self.avg_speed_label, self.trip_time_label]:
            label.setStyleSheet("font-size: 14px; padding: 5px;")
            trip_layout.addWidget(label)
        
        trip_group.setLayout(trip_layout)
        layout.addWidget(trip_group)
        
        # V2X info
        v2x_group = QGroupBox("V2X")
        v2x_layout = QVBoxLayout()
        
        self.nearby_vehicles_label = QLabel("Nearby: 0")
        self.hazards_label = QLabel("Hazards: 0")
        
        for label in [self.nearby_vehicles_label, self.hazards_label]:
            label.setStyleSheet("font-size: 14px; padding: 5px;")
            v2x_layout.addWidget(label)
        
        v2x_group.setLayout(v2x_layout)
        layout.addWidget(v2x_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _createBottomBar(self):
        """Create bottom bar"""
        widget = QWidget()
        widget.setMaximumHeight(80)
        layout = QHBoxLayout()
        
        self.gear_label = QLabel("P")
        self.gear_label.setStyleSheet("""
            font-size: 48px; 
            font-weight: bold;
            color: #00BCD4;
            padding: 10px;
        """)
        layout.addWidget(self.gear_label)
        
        layout.addStretch()
        
        mode_label = QLabel("🚗 NORMAL")
        mode_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(mode_label)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def updateData(self, data):
        """Update with new vehicle data"""
        speed = data.get('gps', {}).get('speed', 0)
        self.speedometer.setSpeed(speed)
        
        self.time_label.setText(datetime.now().strftime("%H:%M"))
        
        v2x = data.get('v2x', {})
        self.nearby_vehicles_label.setText(f"Nearby: {v2x.get('nearby', 0)}")
        self.hazards_label.setText(f"Hazards: {v2x.get('hazards', 0)}")
    
    def setFirebaseStatus(self, connected):
        """Update Firebase connection status"""
        if connected:
            self.firebase_status.setText("☁ Cloud")
            self.firebase_status.setStyleSheet("font-size: 18px; color: #4CAF50;")
        else:
            self.firebase_status.setText("☁ Offline")
            self.firebase_status.setStyleSheet("font-size: 18px; color: #F44336;")

# Simplified NavigationPage, MediaPage, ClimateControlPage, SettingsPage
# (keeping only essential structure to fit within limits)

class NavigationPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Navigation\n(Maps integration)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        self.setLayout(layout)
    
    def updateData(self, data):
        pass

class MediaPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Media Player\n(Android Auto / CarPlay)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        self.setLayout(layout)

class ClimateControlPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Climate Control")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        self.setLayout(layout)

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Settings")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        self.setLayout(layout)

# ==================== DATA THREAD ====================

class DataThread(QThread):
    """Data acquisition thread with Firebase"""
    
    dataUpdated = pyqtSignal(dict)
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.running = False
        self.data = {
            'gps': {'lat': 30.0444, 'lon': 31.2357, 'speed': 0, 'heading': 0},
            'adas': {'lane_departure': 0, 'objects': 0},
            'v2x': {'nearby': 0, 'hazards': 0},
            'system': {'cpu': 0, 'memory': 0}
        }
    
    def run(self):
        """Main data loop"""
        self.running = True
        
        while self.running:
            self._simulate_data()
            
            # Update Firebase
            if self.firebase_manager.connected:
                self.firebase_manager.update_vehicle_data(self.data)
                
                # Check for V2X messages
                v2x_messages = self.firebase_manager.get_v2x_messages()
                if v2x_messages:
                    self.data['v2x']['nearby'] = len(v2x_messages)
            
            self.dataUpdated.emit(self.data.copy())
            time.sleep(0.1)
    
    def _simulate_data(self):
        """Simulate vehicle data"""
        # GPS
        self.data['gps']['speed'] += random.uniform(-2, 2)
        self.data['gps']['speed'] = max(0, min(120, self.data['gps']['speed']))
        self.data['gps']['heading'] = (self.data['gps']['heading'] + random.uniform(-2, 2)) % 360
        self.data['gps']['lat'] += random.uniform(-0.0001, 0.0001)
        self.data['gps']['lon'] += random.uniform(-0.0001, 0.0001)
        
        # ADAS
        self.data['adas']['lane_departure'] = random.uniform(-0.3, 0.3)
        self.data['adas']['objects'] = random.randint(0, 5)
        
        # V2X
        self.data['v2x']['nearby'] = random.randint(0, 8)
        self.data['v2x']['hazards'] = random.randint(0, 2)
        
        # System
        self.data['system']['cpu'] = random.randint(20, 60)
        self.data['system']['memory'] = random.randint(40, 80)
    
    def stop(self):
        """Stop thread"""
        self.running = False

# ==================== MAIN WINDOW ====================

class InfotainmentSystem(QMainWindow):
    """Main infotainment system window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize Firebase
        self.firebase_manager = FirebaseManager(InfotainmentConfig.VEHICLE_ID)
        
        # Create unlock screen
        self.unlock_screen = UnlockScreen(self.firebase_manager)
        self.unlock_screen.unlocked.connect(self.show_dashboard)
        
        # Create dashboard
        self.dashboard_widget = None
        
        # Show unlock screen
        self.setCentralWidget(self.unlock_screen)
        
        self.setWindowTitle("SDV Infotainment System")
        self.setGeometry(100, 100, 
                        InfotainmentConfig.SCREEN_WIDTH, 
                        InfotainmentConfig.SCREEN_HEIGHT)
        
        self.apply_theme()
        
        if InfotainmentConfig.FULLSCREEN:
            self.showFullScreen()
    
    def show_dashboard(self):
        """Show main dashboard after unlock"""
        if self.dashboard_widget is None:
            self.dashboard_widget = self.create_dashboard()
        
        self.setCentralWidget(self.dashboard_widget)
        
        # Start data thread
        self.data_thread = DataThread(self.firebase_manager)
        self.data_thread.dataUpdated.connect(self.updateData)
        self.data_thread.start()
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateUI)
        self.timer.start(100)
        
        # Check for updates periodically
        self.update_check_timer = QTimer()
        self.update_check_timer.timeout.connect(self.check_for_updates)
        self.update_check_timer.start(60000)  # Every minute
    
    def create_dashboard(self):
        """Create main dashboard widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #2D2D2D;
                color: white;
                padding: 15px 25px;
                margin: 2px;
                border-radius: 5px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #00BCD4;
            }
        """)
        
        # Create pages
        self.cluster_page = InstrumentClusterPage()
        self.nav_page = NavigationPage()
        self.media_page = MediaPage()
        self.climate_page = ClimateControlPage()
        self.settings_page = SettingsPage()
        
        # Add pages to tabs
        self.tabs.addTab(self.cluster_page, "🚗 Drive")
        self.tabs.addTab(self.nav_page, "🗺 Navigate")
        self.tabs.addTab(self.media_page, "🎵 Media")
        self.tabs.addTab(self.climate_page, "❄ Climate")
        self.tabs.addTab(self.settings_page, "⚙ Settings")
        
        layout.addWidget(self.tabs)
        
        # Update Firebase status
        self.cluster_page.setFirebaseStatus(self.firebase_manager.connected)
        
        return widget
    
    def apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {InfotainmentConfig.BG_COLOR};
                color: {InfotainmentConfig.TEXT_COLOR};
            }}
            QWidget {{
                background-color: {InfotainmentConfig.BG_COLOR};
                color: {InfotainmentConfig.TEXT_COLOR};
            }}
            QGroupBox {{
                border: 2px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QPushButton {{
                background-color: {InfotainmentConfig.PANEL_COLOR};
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #3D3D3D;
            }}
            QPushButton:pressed {{
                background-color: {InfotainmentConfig.PRIMARY_COLOR};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #333;
                height: 8px;
                background: #2D2D2D;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {InfotainmentConfig.PRIMARY_COLOR};
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QProgressBar {{
                border: none;
                background-color: #2D2D2D;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {InfotainmentConfig.PRIMARY_COLOR};
                border-radius: 2px;
            }}
        """)
    
    def updateData(self, data):
        """Update all pages with new data"""
        if self.dashboard_widget:
            self.cluster_page.updateData(data)
            self.nav_page.updateData(data)
            
            # Check for warnings
            adas = data.get('adas', {})
            if abs(adas.get('lane_departure', 0)) > 0.25:
                self.cluster_page.adas_panel.addWarning('lane', 'Lane Departure Warning')
            
            if adas.get('objects', 0) > 3:
                self.cluster_page.adas_panel.addWarning('collision', 'Multiple Objects Detected')
            
            v2x = data.get('v2x', {})
            if v2x.get('hazards', 0) > 0:
                self.cluster_page.adas_panel.addWarning('hazard', 'Hazard Ahead')
    
    def updateUI(self):
        """Periodic UI updates"""
        pass
    
    def check_for_updates(self):
        """Check for OTA updates"""
        if self.firebase_manager.connected:
            updates = self.firebase_manager.check_for_updates()
            
            if updates:
                self.show_update_notification(len(updates))
    
    def show_update_notification(self, count):
        """Show update notification"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Updates Available")
        msg.setText(f"{count} update(s) available for your vehicle")
        msg.setInformativeText("Would you like to install them now?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setIcon(QMessageBox.Information)
        
        if msg.exec_() == QMessageBox.Yes:
            self.install_updates()
    
    def install_updates(self):
        """Install OTA updates"""
        # Show progress dialog
        progress = QProgressDialog("Installing updates...", "Cancel", 0, 100, self)
        progress.setWindowTitle("OTA Update")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        for i in range(101):
            progress.setValue(i)
            QApplication.processEvents()
            time.sleep(0.05)
        
        QMessageBox.information(self, "Update Complete", 
                              "Updates installed successfully!\nVehicle will restart.")
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_1 and self.dashboard_widget:
            self.tabs.setCurrentIndex(0)
        elif event.key() == Qt.Key_2 and self.dashboard_widget:
            self.tabs.setCurrentIndex(1)
        elif event.key() == Qt.Key_3 and self.dashboard_widget:
            self.tabs.setCurrentIndex(2)
    
    def closeEvent(self, event):
        """Handle window close"""
        if hasattr(self, 'data_thread'):
            self.data_thread.stop()
            self.data_thread.wait()
        
        # Update vehicle status
        if self.firebase_manager.connected:
            try:
                self.firebase_manager.firestore_db.collection('vehicles').document(
                    InfotainmentConfig.VEHICLE_ID
                ).update({
                    'status': 'offline',
                    'last_seen': firestore.SERVER_TIMESTAMP
                })
            except:
                pass
        
        event.accept()

# ==================== MAIN ====================

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application-wide font
    font = QFont(InfotainmentConfig.FONT_MAIN, 10)
    app.setFont(font)
    
    # Create and show window
    window = InfotainmentSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Infotainment System with Firebase                  ║
    ║   Driver Dashboard & Control Center                       ║
    ║                                                           ║
    ║   Features:                                               ║
    ║   - Firebase Cloud Integration                            ║
    ║   - OTA Updates (FOTA/SOTA)                              ║
    ║   - V2X Communication                                     ║
    ║   - Vehicle Unlock System                                 ║
    ║   - Real-time Data Sync                                   ║
    ║                                                           ║
    ║   Controls:                                               ║
    ║   - ESC: Exit                                             ║
    ║   - F11: Toggle fullscreen                                ║
    ║   - 1-5: Quick page switch                                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies
    if not FIREBASE_AVAILABLE:
        print("\n⚠ Warning: Firebase not installed")
        print("Install with: pip install firebase-admin")
        print("Running in simulation mode...\n")
    
    # Check for Firebase credentials
    if not os.path.exists(InfotainmentConfig.FIREBASE_CREDENTIALS):
        print(f"\n⚠ Warning: Firebase credentials not found")
        print(f"Expected file: {InfotainmentConfig.FIREBASE_CREDENTIALS}")
        print("Place your Firebase service account key in this location.\n")
    
    main()