#!/usr/bin/env python3
"""
Trip Tracking Logic and UI
"""
import time
import math
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from config import Config

class TripTracker:
    """Trip tracking logic"""
    
    def __init__(self, booking_id, firebase_manager):
        self.booking_id = booking_id
        self.firebase_manager = firebase_manager
        self.start_time = None
        self.distance_km = 0.0
        self.last_pos = None
        self.running = False
    
    def start(self, lat, lon):
        """Start trip"""
        self.start_time = time.time()
        self.last_pos = (lat, lon)
        self.running = True
        
        if self.firebase_manager:
            self.firebase_manager.start_booking(self.booking_id)
    
    def update_position(self, lat, lon):
        """Update GPS position"""
        if not self.running or not self.last_pos:
            return
        
        # Haversine distance
        R = 6371  # Earth radius km
        lat1, lon1 = math.radians(self.last_pos[0]), math.radians(self.last_pos[1])
        lat2, lon2 = math.radians(lat), math.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        if distance > 0.01:  # > 10m
            self.distance_km += distance
            self.last_pos = (lat, lon)
    
    def get_duration_seconds(self):
        """Get duration in seconds"""
        if not self.start_time:
            return 0
        return int(time.time() - self.start_time)
    
    def get_cost(self):
        """Calculate current cost"""
        hours = self.get_duration_seconds() / 3600
        return (hours * Config.PRICE_PER_HOUR) + (self.distance_km * Config.PRICE_PER_KM)
    
    def end(self):
        """End trip"""
        if not self.running:
            return None
        
        self.running = False
        
        duration_mins = self.get_duration_seconds() / 60
        cost = self.get_cost()
        
        result = {
            'duration_minutes': int(duration_mins),
            'distance_km': round(self.distance_km, 2),
            'cost': round(cost, 2)
        }
        
        if self.firebase_manager:
            self.firebase_manager.end_booking(
                self.booking_id,
                result['duration_minutes'],
                result['distance_km'],
                result['cost']
            )
        
        return result


class TripScreen(QWidget):
    """Active trip UI"""
    
    trip_ended = pyqtSignal(dict)
    
    def __init__(self, booking_data, firebase_manager):
        super().__init__()
        self.tracker = TripTracker(booking_data['bookingId'], firebase_manager)
        self.initUI()
        
        # Start tracking
        self.tracker.start(30.0444, 31.2357)
        
        # Update display every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)
        
        # Simulate GPS movement
        self.gps_timer = QTimer()
        self.gps_timer.timeout.connect(self.simulate_movement)
        self.gps_timer.start(5000)
    
    def simulate_movement(self):
        """Simulate GPS updates"""
        if self.tracker.last_pos:
            lat, lon = self.tracker.last_pos
            new_lat = lat + random.uniform(-0.001, 0.001)
            new_lon = lon + random.uniform(-0.001, 0.001)
            self.tracker.update_position(new_lat, new_lon)
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Title
        title = QLabel("🚗 TRIP IN PROGRESS")
        title.setStyleSheet("font-size: 42px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Stats container
        stats = QWidget()
        stats_layout = QHBoxLayout()
        stats.setLayout(stats_layout)
        
        # Duration
        duration_box = self.create_stat_box("⏱", "Duration", "00:00:00", "#00BCD4")
        self.duration_label = duration_box.findChild(QLabel, "value")
        stats_layout.addWidget(duration_box)
        
        # Distance
        distance_box = self.create_stat_box("📍", "Distance", "0.00 km", "#FFC107")
        self.distance_label = distance_box.findChild(QLabel, "value")
        stats_layout.addWidget(distance_box)
        
        layout.addWidget(stats)
        
        # Cost display
        self.cost_label = QLabel("Estimated Cost: $0.00")
        self.cost_label.setStyleSheet("""
            font-size: 38px;
            font-weight: bold;
            color: #FFC107;
            background: rgba(255, 193, 7, 0.15);
            border: 4px solid #FFC107;
            border-radius: 20px;
            padding: 30px;
        """)
        self.cost_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cost_label)
        
        # Pricing info
        pricing = QLabel(f"${Config.PRICE_PER_HOUR}/hour + ${Config.PRICE_PER_KM}/km")
        pricing.setStyleSheet("font-size: 18px; color: #999; padding: 10px;")
        pricing.setAlignment(Qt.AlignCenter)
        layout.addWidget(pricing)
        
        # End trip button
        end_btn = QPushButton("🛑 END TRIP")
        end_btn.setMinimumHeight(100)
        end_btn.clicked.connect(self.confirm_end_trip)
        end_btn.setStyleSheet("""
            QPushButton {
                font-size: 32px;
                font-weight: bold;
                background: #F44336;
                color: white;
                border-radius: 20px;
            }
            QPushButton:hover {
                background: #D32F2F;
            }
        """)
        layout.addWidget(end_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")
    
    def create_stat_box(self, icon, label, value, color):
        """Create stat display box"""
        box = QWidget()
        box.setStyleSheet(f"""
            background: #1E1E1E;
            border: 3px solid {color};
            border-radius: 15px;
            padding: 25px;
        """)
        
        layout = QVBoxLayout()
        box.setLayout(layout)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 20px; color: #999;")
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)
        
        # Value
        value_widget = QLabel(value)
        value_widget.setObjectName("value")
        value_widget.setStyleSheet(f"""
            font-size: 56px;
            font-weight: bold;
            color: {color};
            font-family: 'Courier New';
        """)
        value_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_widget)
        
        return box
    
    def update_display(self):
        """Update trip display"""
        # Duration
        seconds = self.tracker.get_duration_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")
        
        # Distance
        distance = self.tracker.distance_km
        self.distance_label.setText(f"{distance:.2f} km")
        
        # Cost
        cost = self.tracker.get_cost()
        self.cost_label.setText(f"Estimated Cost: ${cost:.2f}")
    
    def confirm_end_trip(self):
        """Confirm end trip"""
        reply = QMessageBox.question(
            self,
            'End Trip',
            'Are you sure you want to end this trip?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = self.tracker.end()
            if result:
                self.trip_ended.emit(result)


class TripSummaryScreen(QWidget):
    """Trip summary after completion"""
    
    finished = pyqtSignal()
    
    def __init__(self, trip_result):
        super().__init__()
        self.result = trip_result
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # Title
        title = QLabel("✅ TRIP COMPLETED")
        title.setStyleSheet("font-size: 48px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Summary card
        card = QWidget()
        card.setStyleSheet("""
            background: #1E1E1E;
            border: 4px solid #00BCD4;
            border-radius: 25px;
            padding: 40px;
        """)
        card_layout = QVBoxLayout()
        card.setLayout(card_layout)
        
        # Duration
        duration_mins = self.result['duration_minutes']
        hours = duration_mins // 60
        mins = duration_mins % 60
        duration_text = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"
        
        duration_label = QLabel(f"⏱️ Duration: {duration_text}")
        duration_label.setStyleSheet("font-size: 32px; color: white; padding: 15px;")
        card_layout.addWidget(duration_label)
        
        # Distance
        distance_label = QLabel(f"📍 Distance: {self.result['distance_km']} km")
        distance_label.setStyleSheet("font-size: 32px; color: white; padding: 15px;")
        card_layout.addWidget(distance_label)
        
        # Cost
        cost_label = QLabel(f"💰 Total Cost: ${self.result['cost']}")
        cost_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #00BCD4; padding: 20px;")
        cost_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(cost_label)
        
        layout.addWidget(card)
        
        # Thank you message
        thanks = QLabel("Payment will be processed automatically\n\nThank you for using Smart City Transport!")
        thanks.setStyleSheet("font-size: 22px; color: #999; padding: 25px;")
        thanks.setAlignment(Qt.AlignCenter)
        layout.addWidget(thanks)
        
        # Return button
        return_btn = QPushButton("RETURN TO DASHBOARD")
        return_btn.setMinimumHeight(90)
        return_btn.clicked.connect(self.finished.emit)
        return_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                font-weight: bold;
                background: #4CAF50;
                color: white;
                border-radius: 20px;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)
        layout.addWidget(return_btn)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR};")