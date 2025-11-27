#!/usr/bin/env python3
"""
SDV Infotainment System - Main Application
RUN THIS FILE: python3 main.py
"""
import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Import our modules
from config import Config
from firebase_manager import FirebaseManager
from unlock_screen import UnlockScreen
from dashboard import DashboardScreen
from trip_tracker import TripScreen, TripSummaryScreen

class InfotainmentApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        print("\n" + "="*60)
        print("🚀 SDV INFOTAINMENT SYSTEM STARTING")
        print("="*60 + "\n")
        
        # Create UI first (fast)
        self.setup_ui()
        
        # Initialize Firebase in background (after 1 second)
        self.firebase_manager = None
        QTimer.singleShot(1000, self.init_firebase)
        
        print("✅ UI Ready!")
        print("⏳ Firebase initializing in background...\n")
    
    def setup_ui(self):
        """Setup UI components"""
        # Create stack for screens
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create unlock screen (without Firebase initially)
        self.unlock_screen = UnlockScreen(None)
        self.unlock_screen.unlocked.connect(self.on_unlock)
        self.stack.addWidget(self.unlock_screen)
        
        # Window settings
        self.setWindowTitle("SDV Infotainment System")
        self.setGeometry(100, 100, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
        
        # Apply theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {Config.BG_COLOR};
                color: white;
            }}
        """)
        
        if Config.FULLSCREEN:
            self.showFullScreen()
    
    def init_firebase(self):
        """Initialize Firebase (runs in background)"""
        print("🔄 Initializing Firebase...")
        self.firebase_manager = FirebaseManager(Config.VEHICLE_ID)
        
        # Connect Firebase to unlock screen
        self.unlock_screen.firebase_manager = self.firebase_manager
        
        if self.firebase_manager.connected:
            print("✅ Firebase connected!\n")
        else:
            print("⚠️  Firebase offline - using test mode\n")
        
        # Trigger booking check
        self.unlock_screen.check_for_booking()
    
    def on_unlock(self, booking_data):
        """Handle successful unlock"""
        print("\n🔓 VEHICLE UNLOCKED!")
        print(f"   Booking: {booking_data.get('bookingId')}")
        
        self.booking_data = booking_data
        
        # Create dashboard
        dashboard = DashboardScreen(self.firebase_manager, booking_data)
        dashboard.start_trip.connect(self.on_start_trip)
        
        self.stack.addWidget(dashboard)
        self.stack.setCurrentWidget(dashboard)
    
    def on_start_trip(self):
        """Start a new trip"""
        print("\n🚗 Starting trip...")
        
        trip_screen = TripScreen(self.booking_data, self.firebase_manager)
        trip_screen.trip_ended.connect(self.on_trip_ended)
        
        self.stack.addWidget(trip_screen)
        self.stack.setCurrentWidget(trip_screen)
    
    def on_trip_ended(self, trip_result):
        """Show trip summary"""
        print("\n✅ Trip ended!")
        print(f"   Duration: {trip_result['duration_minutes']} mins")
        print(f"   Distance: {trip_result['distance_km']} km")
        print(f"   Cost: ${trip_result['cost']}")
        
        summary = TripSummaryScreen(trip_result)
        summary.finished.connect(self.return_to_dashboard)
        
        self.stack.addWidget(summary)
        self.stack.setCurrentWidget(summary)
    
    def return_to_dashboard(self):
        """Return to dashboard"""
        print("\n🏠 Returning to dashboard...")
        
        # Remove trip screens
        while self.stack.count() > 2:
            widget = self.stack.widget(2)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        
        # Go to dashboard
        self.stack.setCurrentIndex(1)
    
    def keyPressEvent(self, event):
        """Keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    
    def closeEvent(self, event):
        """Clean shutdown"""
        print("\n👋 Shutting down...")
        
        if self.firebase_manager:
            self.firebase_manager.update_vehicle_status('available', False)
        
        event.accept()


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          SDV INFOTAINMENT SYSTEM v2.0                     ║
║          Modular Architecture                             ║
║                                                           ║
║  Features:                                                ║
║  ✓ Vehicle unlock with code                               ║
║  ✓ Real-time trip tracking                                ║
║  ✓ Dashboard with tabs                                    ║
║  ✓ Firebase integration                                   ║
║  ✓ Trip cost calculation                                  ║
║                                                           ║
║  Pricing: $15/hour + $0.50/km                             ║
║                                                           ║
║  Controls:                                                ║
║  - ESC: Exit                                              ║
║  - F11: Fullscreen                                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Force X11
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    # Check Firebase
    if not os.path.exists(Config.FIREBASE_CREDENTIALS):
        print(f"⚠️  Firebase credentials not found:")
        print(f"   {Config.FIREBASE_CREDENTIALS}")
        print(f"   System will run in TEST MODE (code: {Config.TEST_MODE_UNLOCK_CODE})\n")
    
    # Create app
    app = QApplication(sys.argv)
    app.setFont(QFont("Roboto", 10))
    
    # Create window
    window = InfotainmentApp()
    window.show()
    
    print("="*60)
    print("✅ SYSTEM RUNNING")
    print("="*60 + "\n")
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()