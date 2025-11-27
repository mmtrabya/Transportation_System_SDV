#!/usr/bin/env python3
"""
Unlock Screen - SIMPLIFIED
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from config import Config

class UnlockScreen(QWidget):
    """Vehicle unlock screen"""
    
    unlocked = pyqtSignal(dict)  # Emits booking data
    
    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.booking_data = None
        self.attempts = 0
        self.max_attempts = 5
        
        self.initUI()
        
        # Check for booking every 10 seconds
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_for_booking)
        self.check_timer.start(10000)  # 10 seconds
        
        # Do first check after 2 seconds
        QTimer.singleShot(2000, self.check_for_booking)
    
    def check_for_booking(self):
        """Check Firebase for active booking"""
        print("\n" + "="*60)
        print("🔍 CHECKING FOR BOOKING")
        print("="*60)
        
        if not self.firebase_manager:
            print("❌ No Firebase manager")
            self.set_test_mode()
            return
        
        if not self.firebase_manager.connected:
            print("❌ Firebase not connected")
            self.set_test_mode()
            return
        
        # Get booking from Firebase
        booking = self.firebase_manager.get_active_booking()
        
        if booking:
            self.set_active_booking(booking)
        else:
            print("⚠ No booking found - using test mode")
            self.set_test_mode()
    
    def set_active_booking(self, booking):
        """Set active booking"""
        self.booking_data = booking
        unlock_code = booking.get('unlockCode')
        
        print(f"\n✅ BOOKING ACTIVATED:")
        print(f"   Booking ID: {booking.get('bookingId')}")
        print(f"   Unlock Code: {unlock_code}")
        print(f"   User: {booking.get('userId')}")
        
        self.status_label.setText(f"🟢 Booking Active - Code: {unlock_code}")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 24px; font-weight: bold;")
        self.code_input.setEnabled(True)
        self.code_input.setFocus()
    
    def set_test_mode(self):
        """Activate test mode"""
        self.booking_data = {
            'bookingId': 'TEST_BOOKING',
            'unlockCode': Config.TEST_MODE_UNLOCK_CODE,
            'vehicleId': Config.VEHICLE_ID,
            'status': 'confirmed'
        }
        
        self.status_label.setText(f"🟡 Test Mode - Code: {Config.TEST_MODE_UNLOCK_CODE}")
        self.status_label.setStyleSheet("color: #FFC107; font-size: 24px; font-weight: bold;")
        self.code_input.setEnabled(True)
        self.code_input.setFocus()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(50, 40, 50, 40)
        
        # Title
        title = QLabel("🚗 VEHICLE UNLOCK")
        title.setStyleSheet("font-size: 48px; font-weight: bold; color: #00BCD4; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Vehicle ID
        vehicle_label = QLabel(f"Vehicle: {Config.VEHICLE_ID}")
        vehicle_label.setStyleSheet("font-size: 18px; color: #999;")
        vehicle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(vehicle_label)
        
        # Status
        self.status_label = QLabel("⏳ Checking for booking...")
        self.status_label.setStyleSheet("color: #999; font-size: 22px; padding: 20px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter unlock code")
        self.code_input.setMaxLength(4)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setEchoMode(QLineEdit.Password)
        self.code_input.setEnabled(False)
        self.code_input.setStyleSheet("""
            QLineEdit {
                font-size: 72px;
                font-weight: bold;
                padding: 30px;
                background: #1E1E1E;
                border: 4px solid #00BCD4;
                border-radius: 20px;
                letter-spacing: 35px;
                color: #00BCD4;
            }
            QLineEdit:disabled {
                border-color: #555;
                color: #555;
            }
        """)
        layout.addWidget(self.code_input)
        
        # Numpad
        numpad_widget = self.create_numpad()
        layout.addWidget(numpad_widget)
        
        # Info/Error label
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 20px; padding: 15px;")
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {Config.BG_COLOR};")
    
    def create_numpad(self):
        """Create numpad widget"""
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(15)
        widget.setLayout(layout)
        
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
                
                base_style = """
                    QPushButton {
                        font-size: 42px;
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
                """
                
                if text == 'C':
                    btn.clicked.connect(self.clear_code)
                    btn.setStyleSheet(base_style + "QPushButton { background: #F44336; }")
                elif text == '✓':
                    btn.clicked.connect(self.verify_code)
                    btn.setStyleSheet(base_style + "QPushButton { background: #4CAF50; }")
                else:
                    btn.clicked.connect(lambda checked, t=text: self.add_digit(t))
                    btn.setStyleSheet(base_style)
                
                layout.addWidget(btn, i, j)
        
        return widget
    
    def add_digit(self, digit):
        """Add digit to code"""
        if len(self.code_input.text()) < 4:
            self.code_input.setText(self.code_input.text() + digit)
            
            # Auto-verify when 4 digits entered
            if len(self.code_input.text()) == 4:
                QTimer.singleShot(500, self.verify_code)
    
    def clear_code(self):
        """Clear code input"""
        self.code_input.clear()
        self.info_label.setText("")
    
    def verify_code(self):
        """Verify unlock code"""
        entered = self.code_input.text()
        
        if len(entered) != 4:
            self.show_error("Enter 4 digits")
            return
        
        if not self.booking_data:
            self.show_error("No active booking")
            return
        
        correct_code = str(self.booking_data.get('unlockCode', ''))
        
        if entered == correct_code:
            self.show_success()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if remaining > 0:
                self.show_error(f"Wrong code! {remaining} attempts left")
                self.code_input.clear()
            else:
                self.show_error("Too many attempts - Vehicle locked")
                self.code_input.setEnabled(False)
    
    def show_error(self, msg):
        """Show error message"""
        self.info_label.setText(f"❌ {msg}")
        self.info_label.setStyleSheet("font-size: 22px; color: #F44336; font-weight: bold;")
    
    def show_success(self):
        """Show success and unlock"""
        self.info_label.setText("✅ VEHICLE UNLOCKED!")
        self.info_label.setStyleSheet("font-size: 28px; color: #4CAF50; font-weight: bold;")
        
        # Emit unlock signal after 1.5 seconds
        QTimer.singleShot(1500, lambda: self.unlocked.emit(self.booking_data))