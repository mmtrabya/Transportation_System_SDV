#!/usr/bin/env python3
"""
Configuration for SDV Infotainment System
"""
from pathlib import Path

class Config:
    """System Configuration"""
    # Display Settings
    FULLSCREEN = False
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600
    
    # Firebase Settings
    FIREBASE_CREDENTIALS = str(Path.home() / "sdv_firebase_key.json")
    FIREBASE_DATABASE_URL = "https://sdv-ota-system-default-rtdb.europe-west1.firebasedatabase.app"
    VEHICLE_ID = "SDV_CAI_001"
    
    # UI Colors
    PRIMARY_COLOR = "#00BCD4"
    WARNING_COLOR = "#FFC107"
    DANGER_COLOR = "#F44336"
    SUCCESS_COLOR = "#4CAF50"
    BG_COLOR = "#121212"
    PANEL_COLOR = "#1E1E1E"
    TEXT_COLOR = "#FFFFFF"
    
    # Pricing
    PRICE_PER_HOUR = 15.0
    PRICE_PER_KM = 0.5
    
    # Test mode (when Firebase fails)
    TEST_MODE_UNLOCK_CODE = "1234"