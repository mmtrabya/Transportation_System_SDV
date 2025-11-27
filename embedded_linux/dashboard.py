#!/usr/bin/env python3
"""
Main Dashboard Screen
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from config import Config

class DashboardScreen(QWidget):
    """Main dashboard with tabs"""
    
    start_trip = pyqtSignal()
    
    def __init__(self, firebase_manager, booking_data):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.booking_data = booking_data
        self.initUI()
        
        # Update time every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #121212;
            }
            QTabBar::tab {
                background: #2D2D2D;
                color: white;
                padding: 18px 30px;
                margin: 2px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #00BCD4;
                color: #000;
            }
            QTabBar::tab:hover {
                background: #3D3D3D;
            }
        """)
        
        # Add pages
        self.tabs.addTab(self.create_home_page(), "🏠 Home")
        self.tabs.addTab(self.create_climate_page(), "❄️ Climate")
        self.tabs.addTab(self.create_media_page(), "🎵 Media")
        self.tabs.addTab(self.create_settings_page(), "⚙️ Settings")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setStyleSheet(f"background: {Config.BG_COLOR}; color: white;")
    
    def create_home_page(self):
        """Home page with vehicle stats"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title = QLabel("🚗 VEHICLE DASHBOARD")
        title.setStyleSheet("font-size: 40px; font-weight: bold; color: #00BCD4;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Stats grid
        stats = QWidget()
        stats_layout = QGridLayout()
        stats_layout.setSpacing(20)
        stats.setLayout(stats_layout)
        
        # Speed
        speed_card = self.create_stat_card("⚡ Speed", "0", "km/h", "#00BCD4")
        stats_layout.addWidget(speed_card, 0, 0)
        
        # Battery
        battery_card = self.create_stat_card("🔋 Battery", "85", "%", "#4CAF50")
        stats_layout.addWidget(battery_card, 0, 1)
        
        # Range
        range_card = self.create_stat_card("📍 Range", "450", "km", "#FFC107")
        stats_layout.addWidget(range_card, 0, 2)
        
        layout.addWidget(stats)
        
        # Status info
        status_box = QWidget()
        status_box.setStyleSheet("""
            background: #1E1E1E;
            border: 2px solid #00BCD4;
            border-radius: 15px;
            padding: 20px;
        """)
        status_layout = QVBoxLayout()
        status_box.setLayout(status_layout)
        
        # Booking info
        booking_label = QLabel(f"📋 Booking: {self.booking_data.get('bookingId', 'N/A')}")
        booking_label.setStyleSheet("font-size: 18px; padding: 8px;")
        status_layout.addWidget(booking_label)
        
        # Time
        self.time_label = QLabel(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        self.time_label.setStyleSheet("font-size: 18px; padding: 8px;")
        status_layout.addWidget(self.time_label)
        
        # Location
        location_label = QLabel("📍 Cairo, Egypt")
        location_label.setStyleSheet("font-size: 18px; padding: 8px;")
        status_layout.addWidget(location_label)
        
        # Firebase status
        fb_status = "Connected" if self.firebase_manager.connected else "Offline"
        fb_color = "#4CAF50" if self.firebase_manager.connected else "#F44336"
        fb_label = QLabel(f"☁️ Firebase: {fb_status}")
        fb_label.setStyleSheet(f"font-size: 18px; padding: 8px; color: {fb_color};")
        status_layout.addWidget(fb_label)
        
        layout.addWidget(status_box)
        
        # Start trip button
        trip_btn = QPushButton("🚀 START NEW TRIP")
        trip_btn.setMinimumHeight(100)
        trip_btn.clicked.connect(self.start_trip.emit)
        trip_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                font-weight: bold;
                background: #4CAF50;
                color: white;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:pressed {
                background: #3d8b40;
            }
        """)
        layout.addWidget(trip_btn)
        
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def create_stat_card(self, label, value, unit, color):
        """Create a stat display card"""
        card = QWidget()
        card.setStyleSheet(f"""
            background: #1E1E1E;
            border: 3px solid {color};
            border-radius: 15px;
            padding: 20px;
        """)
        
        layout = QVBoxLayout()
        card.setLayout(layout)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 20px; color: #999;")
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)
        
        # Value
        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"font-size: 56px; font-weight: bold; color: {color};")
        value_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_widget)
        
        # Unit
        unit_widget = QLabel(unit)
        unit_widget.setStyleSheet("font-size: 18px; color: #999;")
        unit_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(unit_widget)
        
        return card
    
    def create_climate_page(self):
        """Climate control page"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        title = QLabel("❄️ CLIMATE CONTROL")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Temperature display
        temp_display = QLabel("22°C")
        temp_display.setStyleSheet("font-size: 120px; font-weight: bold; color: #00BCD4;")
        temp_display.setAlignment(Qt.AlignCenter)
        layout.addWidget(temp_display)
        
        # Temperature controls
        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls.setLayout(controls_layout)
        
        # Decrease button
        dec_btn = QPushButton("−")
        dec_btn.setMinimumSize(100, 100)
        dec_btn.setStyleSheet("""
            font-size: 48px;
            background: #2D2D2D;
            border: 3px solid #00BCD4;
            border-radius: 50px;
            color: white;
        """)
        controls_layout.addWidget(dec_btn)
        
        controls_layout.addStretch()
        
        # Increase button
        inc_btn = QPushButton("+")
        inc_btn.setMinimumSize(100, 100)
        inc_btn.setStyleSheet("""
            font-size: 48px;
            background: #2D2D2D;
            border: 3px solid #00BCD4;
            border-radius: 50px;
            color: white;
        """)
        controls_layout.addWidget(inc_btn)
        
        layout.addWidget(controls)
        
        # Settings
        settings_label = QLabel("• AC: Auto\n• Fan: Medium\n• Mode: Cool")
        settings_label.setStyleSheet("font-size: 20px; color: #999; padding: 30px;")
        settings_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(settings_label)
        
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def create_media_page(self):
        """Media player page"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("🎵 MEDIA PLAYER")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Album art placeholder
        art = QLabel("🎼")
        art.setStyleSheet("font-size: 120px; padding: 40px;")
        art.setAlignment(Qt.AlignCenter)
        layout.addWidget(art)
        
        # Track info
        track = QLabel("Android Auto / Apple CarPlay\n\nComing Soon...")
        track.setStyleSheet("font-size: 22px; color: #999; padding: 20px;")
        track.setAlignment(Qt.AlignCenter)
        layout.addWidget(track)
        
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def create_settings_page(self):
        """Settings page"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("⚙️ SETTINGS")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #00BCD4;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Settings list
        settings_box = QWidget()
        settings_box.setStyleSheet("""
            background: #1E1E1E;
            border: 2px solid #00BCD4;
            border-radius: 15px;
            padding: 30px;
        """)
        settings_layout = QVBoxLayout()
        settings_box.setLayout(settings_layout)
        
        settings = [
            "• Display Brightness: Auto",
            "• Sound Volume: 70%",
            "• Climate Control: Auto",
            "• Units: Metric",
            "• Language: English"
        ]
        
        for setting in settings:
            label = QLabel(setting)
            label.setStyleSheet("font-size: 20px; padding: 12px;")
            settings_layout.addWidget(label)
        
        layout.addWidget(settings_box)
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def update_time(self):
        """Update time display"""
        self.time_label.setText(f"🕐 {datetime.now().strftime('%H:%M:%S')}")