#!/usr/bin/env python3
"""
Complete SDV Infotainment System
Unlock Screen → Dashboard → Trip Tracking
Location: embedded_linux/complete_infotainment_system.py

Features:
- Vehicle unlock with 4-digit code
- Full infotainment dashboard
- Real-time trip tracking (duration, distance, cost)
- Firebase integration
- V2X communication
- OTA updates
"""

import sys
import os
import time
import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, db as firebase_db, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("⚠ Firebase not available - running in simulation mode")

# ==================== CONFIGURATION ====================

class Config:
    """System Configuration"""
    FULLSCREEN = False
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    
    FIREBASE_CREDENTIALS = str(Path.home() / "sdv_firebase_key.json")
    FIREBASE_DATABASE_URL = "https://sdv-ota-system-default-rtdb.europe-west1.firebasedatabase.app"
    VEHICLE_ID = "SDV_001"
    
    PRIMARY_COLOR = "#00BCD4"
    WARNING_COLOR = "#FFC107"
    DANGER_COLOR = "#F44336"
    SUCCESS_COLOR = "#4CAF50"
    BG_COLOR = "#121212"
    PANEL_COLOR = "#1E1E1E"
    TEXT_COLOR = "#FFFFFF"

# ==================== FIREBASE MANAGER ====================

class FirebaseManager:
    """Manage Firebase connections"""
    
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.firestore_db = None
        self.realtime_db = None
        self.connected = False
        
        if FIREBASE_AVAILABLE:
            self._initialize()
    
    def _initialize(self):
        """Initialize Firebase"""
        try:
            if not firebase_admin._apps:
                if os.path.exists(Config.FIREBASE_CREDENTIALS):
                    cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': Config.FIREBASE_DATABASE_URL,
                        'storageBucket': 'sdv-ota-system.firebasestorage.app'
                    })
                else:
                    print(f"⚠ Firebase credentials not found: {Config.FIREBASE_CREDENTIALS}")
                    return
            
            self.firestore_db = firestore.client()
            self.realtime_db = firebase_db.reference()
            self.connected = True
            
            print(f"✓ Firebase connected for vehicle {self.vehicle_id}")
            self._register_vehicle()
            
        except Exception as e:
            print(f"✗ Firebase initialization failed: {e}")
            self.connected = False
    
    def _register_vehicle(self):
        """Register vehicle in Firestore"""
        try:
            vehicle_ref = self.firestore_db.collection('vehicles').document(self.vehicle_id)
            vehicle_ref.set({
                'vehicleId': self.vehicle_id,
                'model': 'Tesla Model S',
                'category': 'luxury',
                'licensePlate': 'SDV-001-EG',
                'status': 'available',
                'isOnline': True,
                'batteryLevel': 85,
                'location': {
                    'latitude': 30.0444,
                    'longitude': 31.2357
                },
                'pricePerHour': 15.0,
                'pricePerKm': 0.5,
                'last_seen': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            print(f"✓ Vehicle registered at Cairo (30.0444, 31.2357)")
            
        except Exception as e:
            print(f"✗ Vehicle registration failed: {e}")
    
    def update_vehicle_data(self, data):
        """Update vehicle data in Firebase"""
        if not self.connected:
            return
        
        try:
            vehicle_ref = self.firestore_db.collection('vehicles').document(self.vehicle_id)
            vehicle_ref.update({
                'last_seen': firestore.SERVER_TIMESTAMP,
                'location': {
                    'latitude': data.get('gps', {}).get('lat', 0),
                    'longitude': data.get('gps', {}).get('lon', 0),
                    'speed': data.get('gps', {}).get('speed', 0)
                }
            })
        except Exception as e:
            pass

# ==================== TRIP TRACKER ====================

class TripTracker:
    """Track trip duration, distance, and cost"""
    
    def __init__(self, booking_id, vehicle_id, firebase_manager):
        self.booking_id = booking_id
        self.vehicle_id = vehicle_id
        self.firebase_manager = firebase_manager
        self.start_time = None
        self.total_distance = 0.0
        self.last_position = None
        self.running = False
        
        # Pricing
        self.price_per_hour = 15.0
        self.price_per_km = 0.5
    
    def start(self, start_lat, start_lon):
        """Start trip tracking"""
        self.start_time = time.time()
        self.last_position = (start_lat, start_lon)
        self.running = True
        
        if self.firebase_manager.connected:
            try:
                self.firebase_manager.firestore_db.collection('bookings').document(self.booking_id).update({
                    'status': 'active',
                    'actualStartTime': firestore.SERVER_TIMESTAMP,
                    'startLocation': {'latitude': start_lat, 'longitude': start_lon}
                })
            except:
                pass
    
    def update_position(self, lat, lon):
        """Update position and calculate distance"""
        if not self.running or not self.last_position:
            return
        
        # Haversine formula
        R = 6371  # Earth radius in km
        
        lat1, lon1 = math.radians(self.last_position[0]), math.radians(self.last_position[1])
        lat2, lon2 = math.radians(lat), math.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        if distance > 0.01:  # Ignore GPS noise < 10m
            self.total_distance += distance
            self.last_position = (lat, lon)
    
    def get_duration(self):
        """Get trip duration in seconds"""
        if not self.start_time:
            return 0
        return int(time.time() - self.start_time)
    
    def get_distance(self):
        """Get trip distance in km"""
        return self.total_distance
    
    def get_current_cost(self):
        """Get current estimated cost"""
        duration_hours = self.get_duration() / 3600
        return (duration_hours * self.price_per_hour) + (self.total_distance * self.price_per_km)
    
    def end_trip(self, end_lat, end_lon):
        """End trip and return summary"""
        if not self.running:
            return None
        
        self.running = False
        
        duration_minutes = self.get_duration() / 60
        cost = self.get_current_cost()
        
        result = {
            'duration_minutes': int(duration_minutes),
            'distance_km': round(self.total_distance, 2),
            'cost': round(cost, 2)
        }
        
        if self.firebase_manager.connected:
            try:
                self.firebase_manager.firestore_db.collection('bookings').document(self.booking_id).update({
                    'status': 'completed',
                    'actualEndTime': firestore.SERVER_TIMESTAMP,
                    'actualDuration': int(duration_minutes),
                    'actualDistance': result['distance_km'],
                    'actualPrice': result['cost'],
                    'endLocation': {'latitude': end_lat, 'longitude': end_lon}
                })
            except:
                pass
        
        return result

# ==================== UNLOCK SCREEN ====================

class UnlockScreen(QWidget):
    """Vehicle unlock screen with keypad"""
    
    unlocked = pyqtSignal(dict)  # Emits booking data
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.booking_data = None
        self.unlock_code = None
        self.code_expires = None
        self.attempts = 0
        self.max_attempts = 3
        
        self.initUI()
        self.check_booking()
        
        # Check for bookings every 5 seconds
        self.booking_timer = QTimer()
        self.booking_timer.timeout.connect(self.check_booking)
        self.booking_timer.start(5000)
        
        # Update countdown every second
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)
    
    def check_booking(self):
        """Check Firebase for active booking"""
        if not self.firebase_manager.connected:
            return
        
        try:
            vehicle_doc = self.firebase_manager.firestore_db.collection('vehicles').document(
                Config.VEHICLE_ID
            ).get()
            
            if vehicle_doc.exists:
                vehicle_data = vehicle_doc.to_dict()
                
                if 'currentBooking' in vehicle_data:
                    booking = vehicle_data['currentBooking']
                    
                    if booking['status'] == 'confirmed':
                        self.booking_data = booking
                        self.unlock_code = booking['unlockCode']
                        
                        # Get expiry (10 minutes from creation)
                        booking_doc = self.firebase_manager.firestore_db.collection('bookings').document(
                            booking['bookingId']
                        ).get()
                        
                        if booking_doc.exists:
                            booking_full = booking_doc.to_dict()
                            created_at = booking_full.get('createdAt')
                            if created_at:
                                self.code_expires = created_at.timestamp() + (10 * 60)
                        
                        self.status_label.setText("🟢 Booking Active - Enter Code")
                        self.status_label.setStyleSheet("color: #4CAF50; font-size: 22px; font-weight: bold;")
                        return
            
            # No active booking
            if self.booking_data:
                self.booking_data = None
                self.unlock_code = None
                self.code_expires = None
                self.status_label.setText("⏳ Waiting for Booking...")
                self.status_label.setStyleSheet("color: #FFC107; font-size: 20px;")
                self.code_input.clear()
                self.code_input.setEnabled(True)
                self.attempts = 0
        
        except Exception as e:
            print(f"Error checking booking: {e}")
    
    def update_countdown(self):
        """Update expiry countdown"""
        if not self.code_expires:
            self.countdown_label.setText("")
            return
        
        remaining = self.code_expires - time.time()
        
        if remaining <= 0:
            self.countdown_label.setText("⏰ CODE EXPIRED")
            self.countdown_label.setStyleSheet("color: #F44336; font-size: 18px; font-weight: bold;")
            self.code_input.setEnabled(False)
            return
        
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        self.countdown_label.setText(f"⏰ Code expires in: {mins:02d}:{secs:02d}")
        
        if remaining < 120:
            self.countdown_label.setStyleSheet("color: #FF5722; font-size: 18px; font-weight: bold;")
        else:
            self.countdown_label.setStyleSheet("color: #FFC107; font-size: 18px;")
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(50, 40, 50, 40)
        
        # Title
        title = QLabel("🚗 VEHICLE UNLOCK")
        title.setStyleSheet("font-size: 44px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status
        self.status_label = QLabel("⏳ Waiting for Booking...")
        self.status_label.setStyleSheet("color: #999; font-size: 20px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Countdown
        self.countdown_label = QLabel("")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.countdown_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 4-digit code")
        self.code_input.setMaxLength(4)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setEchoMode(QLineEdit.Password)
        self.code_input.setStyleSheet("""
            QLineEdit {
                font-size: 64px;
                font-weight: bold;
                padding: 25px;
                background: #1E1E1E;
                border: 4px solid #00BCD4;
                border-radius: 20px;
                letter-spacing: 30px;
                color: #00BCD4;
            }
        """)
        layout.addWidget(self.code_input)
        
        # Numpad
        numpad_widget = QWidget()
        numpad_layout = QGridLayout()
        numpad_layout.setSpacing(15)
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
                btn.setMinimumSize(120, 120)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 36px;
                        font-weight: bold;
                        background: #2D2D2D;
                        border: 3px solid #444;
                        border-radius: 15px;
                        color: white;
                    }
                    QPushButton:hover {
                        background: #3D3D3D;
                        border-color: #00BCD4;
                    }
                    QPushButton:pressed {
                        background: #00BCD4;
                        color: #000;
                    }
                """)
                
                if btn_text == 'C':
                    btn.clicked.connect(self.clear_input)
                    btn.setStyleSheet(btn.styleSheet() + "QPushButton { background: #F44336; }")
                elif btn_text == '✓':
                    btn.clicked.connect(self.verify_code)
                    btn.setStyleSheet(btn.styleSheet() + "QPushButton { background: #4CAF50; }")
                else:
                    btn.clicked.connect(lambda checked, t=btn_text: self.add_digit(t))
                
                numpad_layout.addWidget(btn, i, j)
        
        layout.addWidget(numpad_widget)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")
    
    def add_digit(self, digit):
        if len(self.code_input.text()) < 4:
            self.code_input.setText(self.code_input.text() + digit)
            
            if len(self.code_input.text()) == 4:
                QTimer.singleShot(300, self.verify_code)
    
    def clear_input(self):
        self.code_input.clear()
        self.info_label.setText("")
    
    def verify_code(self):
        entered_code = self.code_input.text()
        
        if len(entered_code) != 4:
            self.show_error("Please enter 4 digits")
            return
        
        if not self.unlock_code:
            self.show_error("No active booking")
            return
        
        if self.code_expires and time.time() > self.code_expires:
            self.show_error("Booking expired - Please book again")
            self.code_input.setEnabled(False)
            return
        
        if entered_code == str(self.unlock_code):
            self.show_success()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if remaining > 0:
                self.show_error(f"Invalid code - {remaining} attempts left")
                self.code_input.clear()
            else:
                self.show_error("Too many failed attempts - Vehicle locked")
                self.code_input.setEnabled(False)
    
    def show_error(self, message):
        self.info_label.setText(f"✗ {message}")
        self.info_label.setStyleSheet("font-size: 20px; color: #F44336; font-weight: bold;")
    
    def show_success(self):
        self.info_label.setText("✓ VEHICLE UNLOCKED!")
        self.info_label.setStyleSheet("font-size: 28px; color: #4CAF50; font-weight: bold;")
        
        QTimer.singleShot(2000, lambda: self.unlocked.emit(self.booking_data))

# ==================== TRIP SCREEN ====================

class TripScreen(QWidget):
    """Active trip display"""
    
    trip_ended = pyqtSignal(dict)
    
    def __init__(self, booking_data, firebase_manager):
        super().__init__()
        self.booking_data = booking_data
        self.tracker = TripTracker(
            booking_data['bookingId'],
            Config.VEHICLE_ID,
            firebase_manager
        )
        
        self.initUI()
        
        # Start trip
        self.tracker.start(30.0444, 31.2357)
        
        # Update display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)
        
        # Simulate GPS movement
        self.gps_timer = QTimer()
        self.gps_timer.timeout.connect(self.simulate_gps)
        self.gps_timer.start(5000)
    
    def simulate_gps(self):
        """Simulate GPS position updates"""
        if self.tracker.last_position:
            lat, lon = self.tracker.last_position
            # Add small random movement
            new_lat = lat + random.uniform(-0.001, 0.001)
            new_lon = lon + random.uniform(-0.001, 0.001)
            self.tracker.update_position(new_lat, new_lon)
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(40)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Title
        title = QLabel("🚗 TRIP IN PROGRESS")
        title.setStyleSheet("font-size: 42px; font-weight: bold; color: #4CAF50; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Stats
        stats_widget = QWidget()
        stats_layout = QHBoxLayout()
        stats_widget.setLayout(stats_layout)
        
        # Duration
        duration_container = QWidget()
        duration_layout = QVBoxLayout()
        duration_container.setLayout(duration_layout)
        
        duration_label = QLabel("⏱ DURATION")
        duration_label.setStyleSheet("font-size: 20px; color: #999;")
        duration_label.setAlignment(Qt.AlignCenter)
        duration_layout.addWidget(duration_label)
        
        self.duration_value = QLabel("00:00:00")
        self.duration_value.setStyleSheet("""
            font-size: 56px;
            font-weight: bold;
            color: #00BCD4;
            font-family: 'Courier New';
        """)
        self.duration_value.setAlignment(Qt.AlignCenter)
        duration_layout.addWidget(self.duration_value)
        
        stats_layout.addWidget(duration_container)
        
        # Distance
        distance_container = QWidget()
        distance_layout = QVBoxLayout()
        distance_container.setLayout(distance_layout)
        
        distance_label = QLabel("📍 DISTANCE")
        distance_label.setStyleSheet("font-size: 20px; color: #999;")
        distance_label.setAlignment(Qt.AlignCenter)
        distance_layout.addWidget(distance_label)
        
        self.distance_value = QLabel("0.00 km")
        self.distance_value.setStyleSheet("""
            font-size: 56px;
            font-weight: bold;
            color: #00BCD4;
            font-family: 'Courier New';
        """)
        self.distance_value.setAlignment(Qt.AlignCenter)
        distance_layout.addWidget(self.distance_value)
        
        stats_layout.addWidget(distance_container)
        
        layout.addWidget(stats_widget)
        
        # Cost estimate
        self.cost_label = QLabel("Estimated Cost: $0.00")
        self.cost_label.setStyleSheet("""
            font-size: 32px;
            color: #FFC107;
            padding: 20px;
            background: rgba(255, 193, 7, 0.1);
            border: 3px solid #FFC107;
            border-radius: 15px;
        """)
        self.cost_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cost_label)
        
        # Pricing info
        pricing_info = QLabel("$15/hour + $0.50/km")
        pricing_info.setStyleSheet("font-size: 16px; color: #999; padding: 10px;")
        pricing_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(pricing_info)
        
        # End trip button
        end_btn = QPushButton("END TRIP")
        end_btn.setMinimumHeight(100)
        end_btn.clicked.connect(self.end_trip)
        end_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                font-weight: bold;
                background: #F44336;
                color: white;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #D32F2F;
            }
        """)
        layout.addWidget(end_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")
    
    def update_display(self):
        """Update trip display"""
        seconds = self.tracker.get_duration()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        self.duration_value.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")
        
        distance = self.tracker.get_distance()
        self.distance_value.setText(f"{distance:.2f} km")
        
        cost = self.tracker.get_current_cost()
        self.cost_label.setText(f"Estimated Cost: ${cost:.2f}")
    
    def end_trip(self):
        reply = QMessageBox.question(
            self,
            'End Trip',
            'Are you sure you want to end this trip?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = self.tracker.end_trip(30.0454, 31.2367)
            
            if result:
                self.trip_ended.emit(result)

# ==================== TRIP SUMMARY ====================

class TripSummaryScreen(QWidget):
    """Trip summary after completion"""
    
    finished = pyqtSignal()
    
    def __init__(self, trip_result):
        super().__init__()
        self.trip_result = trip_result
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Title
        title = QLabel("✓ TRIP COMPLETED")
        title.setStyleSheet("font-size: 42px; font-weight: bold; color: #4CAF50; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Summary card
        summary_card = QWidget()
        summary_card.setStyleSheet("""
            background: #1E1E1E;
            border: 3px solid #00BCD4;
            border-radius: 20px;
            padding: 30px;
        """)
        summary_layout = QVBoxLayout()
        summary_card.setLayout(summary_layout)
        
        # Duration
        duration_mins = self.trip_result['duration_minutes']
        hours = duration_mins // 60
        mins = duration_mins % 60
        
        duration_text = f"⏱ Duration: {hours}h {mins}m" if hours > 0 else f"⏱ Duration: {mins} minutes"
        duration_label = QLabel(duration_text)
        duration_label.setStyleSheet("font-size: 28px; color: white; padding: 15px;")
        summary_layout.addWidget(duration_label)
        
        # Distance
        distance_label = QLabel(f"📍 Distance: {self.trip_result['distance_km']} km")
        distance_label.setStyleSheet("font-size: 28px; color: white; padding: 15px;")
        summary_layout.addWidget(distance_label)
        
        # Cost
        cost_label = QLabel(f"💰 Total Cost: ${self.trip_result['cost']}")
        cost_label.setStyleSheet("font-size: 42px; font-weight: bold; color: #00BCD4; padding: 20px;")
        cost_label.setAlignment(Qt.AlignCenter)
        summary_layout.addWidget(cost_label)
        
        layout.addWidget(summary_card)
        
        # Info
        info = QLabel("Payment will be processed automatically\nThank you for using Smart City Transport!")
        info.setStyleSheet("font-size: 20px; color: #999; padding: 20px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        # Return to dashboard button
        return_btn = QPushButton("RETURN TO DASHBOARD")
        return_btn.setMinimumHeight(80)
        return_btn.clicked.connect(self.finished.emit)
        return_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background: #4CAF50;
                color: white;
                border-radius: 15px;
            }
        """)
        layout.addWidget(return_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")

# ==================== INFOTAINMENT DASHBOARD ====================

class InstrumentClusterPage(QWidget):
    """Main instrument cluster"""
    
    start_trip_requested = pyqtSignal()
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🚗 VEHICLE DASHBOARD")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Stats
        stats_widget = QWidget()
        stats_layout = QGridLayout()
        stats_widget.setLayout(stats_layout)
        
        # Speed
        speed_label = QLabel("Speed")
        speed_label.setStyleSheet("font-size: 18px; color: #999;")
        stats_layout.addWidget(speed_label, 0, 0)
        
        self.speed_value = QLabel("0 km/h")
        self.speed_value.setStyleSheet("font-size: 42px; font-weight: bold; color: #00BCD4;")
        stats_layout.addWidget(self.speed_value, 1, 0)
        
        # Battery
        battery_label = QLabel("Battery")
        battery_label.setStyleSheet("font-size: 18px; color: #999;")
        stats_layout.addWidget(battery_label, 0, 1)
        
        self.battery_value = QLabel("85%")
        self.battery_value.setStyleSheet("font-size: 42px; font-weight: bold; color: #4CAF50;")
        stats_layout.addWidget(self.battery_value, 1, 1)
        
        # Range
        range_label = QLabel("Range")
        range_label.setStyleSheet("font-size: 18px; color: #999;")
        stats_layout.addWidget(range_label, 0, 2)
        
        self.range_value = QLabel("450 km")
        self.range_value.setStyleSheet("font-size: 42px; font-weight: bold; color: #FFC107;")
        stats_layout.addWidget(self.range_value, 1, 2)
        
        layout.addWidget(stats_widget)
        
        layout.addSpacing(30)
        
        # Status info
        status_group = QGroupBox("Vehicle Status")
        status_layout = QVBoxLayout()
        
        self.firebase_status = QLabel("☁ Firebase: Connected" if self.firebase_manager.connected else "☁ Firebase: Offline")
        self.firebase_status.setStyleSheet(f"font-size: 16px; color: {'#4CAF50' if self.firebase_manager.connected else '#F44336'};")
        status_layout.addWidget(self.firebase_status)
        
        self.location_label = QLabel("📍 Location: Cairo, Egypt (30.0444, 31.2357)")
        self.location_label.setStyleSheet("font-size: 16px; color: #999;")
        status_layout.addWidget(self.location_label)
        
        self.time_label = QLabel(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
        self.time_label.setStyleSheet("font-size: 16px; color: #999;")
        status_layout.addWidget(self.time_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addSpacing(20)
        
        # Start trip button
        start_trip_btn = QPushButton("START NEW TRIP")
        start_trip_btn.setMinimumHeight(80)
        start_trip_btn.clicked.connect(self.start_trip_requested.emit)
        start_trip_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background: #4CAF50;
                color: white;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)
        layout.addWidget(start_trip_btn)
        
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")
    
    def updateData(self, data):
        """Update dashboard with vehicle data"""
        speed = data.get('gps', {}).get('speed', 0)
        self.speed_value.setText(f"{int(speed)} km/h")
        
        self.time_label.setText(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")

class NavigationPage(QWidget):
    """Navigation page"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        title = QLabel("🗺 NAVIGATION")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel("Google Maps Integration\n\nComing Soon...")
        info.setStyleSheet("font-size: 24px; color: #999; padding: 40px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")
    
    def updateData(self, data):
        pass

class MediaPage(QWidget):
    """Media player page"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        title = QLabel("🎵 MEDIA")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel("Android Auto / Apple CarPlay\n\nComing Soon...")
        info.setStyleSheet("font-size: 24px; color: #999; padding: 40px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")

class SettingsPage(QWidget):
    """Settings page"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        title = QLabel("⚙ SETTINGS")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        settings_group = QGroupBox("Vehicle Settings")
        settings_layout = QVBoxLayout()
        
        setting1 = QLabel("• Display Brightness: Auto")
        setting1.setStyleSheet("font-size: 18px; padding: 10px;")
        settings_layout.addWidget(setting1)
        
        setting2 = QLabel("• Sound Volume: 70%")
        setting2.setStyleSheet("font-size: 18px; padding: 10px;")
        settings_layout.addWidget(setting2)
        
        setting3 = QLabel("• Climate Control: 22°C")
        setting3.setStyleSheet("font-size: 18px; padding: 10px;")
        settings_layout.addWidget(setting3)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")

# ==================== DATA THREAD ====================

class DataThread(QThread):
    """Background data acquisition"""
    
    dataUpdated = pyqtSignal(dict)
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.running = False
        self.data = {
            'gps': {'lat': 30.0444, 'lon': 31.2357, 'speed': 0, 'heading': 0},
            'battery': 85,
            'range': 450
        }
    
    def run(self):
        self.running = True
        
        while self.running:
            # Simulate vehicle movement
            self.data['gps']['speed'] += random.uniform(-2, 2)
            self.data['gps']['speed'] = max(0, min(120, self.data['gps']['speed']))
            
            self.data['gps']['lat'] += random.uniform(-0.0001, 0.0001)
            self.data['gps']['lon'] += random.uniform(-0.0001, 0.0001)
            
            # Update Firebase
            if self.firebase_manager.connected:
                self.firebase_manager.update_vehicle_data(self.data)
            
            self.dataUpdated.emit(self.data.copy())
            time.sleep(0.5)
    
    def stop(self):
        self.running = False

# ==================== MAIN WINDOW ====================

class CompleteInfotainmentSystem(QMainWindow):
    """Main system window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize Firebase
        self.firebase_manager = FirebaseManager(Config.VEHICLE_ID)
        
        # Create stack for different screens
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create unlock screen
        self.unlock_screen = UnlockScreen(self.firebase_manager)
        self.unlock_screen.unlocked.connect(self.show_dashboard)
        self.stack.addWidget(self.unlock_screen)
        
        # Dashboard will be created after unlock
        self.dashboard_widget = None
        self.data_thread = None
        
        self.setWindowTitle("SDV Complete Infotainment System")
        self.setGeometry(100, 100, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
        
        self.apply_theme()
        
        if Config.FULLSCREEN:
            self.showFullScreen()
    
    def show_dashboard(self, booking_data):
        """Show dashboard after successful unlock"""
        self.booking_data = booking_data
        
        if self.dashboard_widget is None:
            self.dashboard_widget = self.create_dashboard()
            self.stack.addWidget(self.dashboard_widget)
        
        self.stack.setCurrentWidget(self.dashboard_widget)
        
        # Start data thread
        self.data_thread = DataThread(self.firebase_manager)
        self.data_thread.dataUpdated.connect(self.updateData)
        self.data_thread.start()
    
    def create_dashboard(self):
        """Create dashboard with tabs"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Tab widget
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
        self.cluster_page = InstrumentClusterPage(self.firebase_manager)
        self.cluster_page.start_trip_requested.connect(self.start_trip)
        
        self.nav_page = NavigationPage()
        self.media_page = MediaPage()
        self.settings_page = SettingsPage()
        
        # Add tabs
        self.tabs.addTab(self.cluster_page, "🚗 Dashboard")
        self.tabs.addTab(self.nav_page, "🗺 Navigate")
        self.tabs.addTab(self.media_page, "🎵 Media")
        self.tabs.addTab(self.settings_page, "⚙ Settings")
        
        layout.addWidget(self.tabs)
        
        return widget
    
    def start_trip(self):
        """Start a new trip"""
        if not hasattr(self, 'booking_data'):
            QMessageBox.warning(self, "No Booking", "No active booking available")
            return
        
        # Create trip screen
        trip_screen = TripScreen(self.booking_data, self.firebase_manager)
        trip_screen.trip_ended.connect(self.show_trip_summary)
        
        self.stack.addWidget(trip_screen)
        self.stack.setCurrentWidget(trip_screen)
    
    def show_trip_summary(self, trip_result):
        """Show trip summary"""
        summary_screen = TripSummaryScreen(trip_result)
        summary_screen.finished.connect(self.return_to_dashboard)
        
        self.stack.addWidget(summary_screen)
        self.stack.setCurrentWidget(summary_screen)
    
    def return_to_dashboard(self):
        """Return to dashboard"""
        # Remove trip screens
        while self.stack.count() > 2:
            widget = self.stack.widget(2)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        
        # Return to dashboard
        if self.dashboard_widget:
            self.stack.setCurrentWidget(self.dashboard_widget)
    
    def updateData(self, data):
        """Update dashboard with new data"""
        if self.dashboard_widget and hasattr(self, 'cluster_page'):
            self.cluster_page.updateData(data)
            self.nav_page.updateData(data)
    
    def apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Config.BG_COLOR};
                color: {Config.TEXT_COLOR};
            }}
            QWidget {{
                background-color: {Config.BG_COLOR};
                color: {Config.TEXT_COLOR};
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
        """)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.data_thread:
            self.data_thread.stop()
            self.data_thread.wait()
        
        # Update vehicle status
        if self.firebase_manager.connected:
            try:
                self.firebase_manager.firestore_db.collection('vehicles').document(
                    Config.VEHICLE_ID
                ).update({
                    'status': 'available',
                    'isOnline': False,
                    'last_seen': firestore.SERVER_TIMESTAMP
                })
            except:
                pass
        
        event.accept()

# ==================== MAIN ====================

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set font
    font = QFont("Roboto", 10)
    app.setFont(font)
    
    window = CompleteInfotainmentSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Complete Infotainment System                        ║
    ║   Unlock → Dashboard → Trip Tracking                      ║
    ║                                                           ║
    ║   Features:                                               ║
    ║   ✓ Vehicle unlock with 4-digit code                     ║
    ║   ✓ Real-time trip tracking (duration, distance, cost)   ║
    ║   ✓ Firebase cloud integration                            ║
    ║   ✓ Multi-page dashboard                                  ║
    ║   ✓ Trip summary with cost breakdown                      ║
    ║                                                           ║
    ║   Flow:                                                   ║
    ║   1. Enter unlock code from mobile app booking           ║
    ║   2. Access vehicle dashboard                             ║
    ║   3. Start trip (tracks time, distance, cost)            ║
    ║   4. End trip and view summary                            ║
    ║   5. Return to dashboard                                  ║
    ║                                                           ║
    ║   Pricing: $15/hour + $0.50/km                           ║
    ║                                                           ║
    ║   Controls:                                               ║
    ║   - ESC: Exit                                             ║
    ║   - F11: Toggle fullscreen                                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if not FIREBASE_AVAILABLE:
        print("⚠ Warning: Firebase not installed")
        print("Install with: pip install firebase-admin")
        print("Running in simulation mode...\n")
    
    if not os.path.exists(Config.FIREBASE_CREDENTIALS):
        print(f"⚠ Warning: Firebase credentials not found")
        print(f"Expected: {Config.FIREBASE_CREDENTIALS}")
        print("Place your Firebase service account key there.\n")
    
    main()