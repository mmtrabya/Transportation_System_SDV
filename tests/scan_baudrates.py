#!/usr/bin/env python3
"""
Baud Rate Scanner - Automatically tests common baud rates
Helps identify if ATmega32 is running at a different baud rate
"""

import serial
import time
import sys

# List of common baud rates to test
BAUD_RATES = [
    9600,      # Very common, very reliable
    19200,     # Common
    38400,     # Common
    57600,     # Common
    115200,    # What we want
    4800,      # Sometimes used
    14400,     # Less common
    28800,     # Less common
    76800,     # Less common
    # Wrong clock calculations
    7200,      # 8MHz/16/115200-1 (wrong calc)
    3600,      # Half of wrong calc
]

print("=" * 70)
print("   ATmega32 Baud Rate Scanner")
print("=" * 70)
print("\nThis will test multiple baud rates to find the correct one")
print("Looking for text output from ATmega32...\n")

port = "/dev/ttyUSB0"  # Change if needed

print(f"Testing port: {port}\n")
print("-" * 70)

for baud in BAUD_RATES:
    print(f"\n[{baud:6d} baud] ", end="", flush=True)
    
    try:
        # Open port with current baud rate
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5
        )
        
        time.sleep(0.3)  # Let it settle
        
        # Clear any existing data
        ser.reset_input_buffer()
        
        # Wait a bit for data
        time.sleep(1.5)
        
        # Read what's available
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            
            # Try to decode as ASCII
            try:
                text = data.decode('ascii', errors='replace')
                
                # Check if it looks like readable text
                readable_chars = sum(1 for c in text if c.isprintable() or c in '\r\n\t')
                readability = (readable_chars / len(text)) * 100 if len(text) > 0 else 0
                
                if readability > 70:  # More than 70% readable
                    print(f"✓ FOUND READABLE DATA! ({readability:.0f}% readable)")
                    print(f"\nReceived {len(data)} bytes:")
                    print("-" * 70)
                    print(text)
                    print("-" * 70)
                    print(f"\n🎯 SUCCESS! ATmega32 is likely using {baud} baud")
                    print(f"\nUpdate your code to use {baud} baud or fix UBRR calculation")
                    ser.close()
                    sys.exit(0)
                else:
                    print(f"Got {len(data)} bytes but looks like garbage ({readability:.0f}% readable)")
                    # Show first few bytes
                    hex_str = " ".join(f"{b:02X}" for b in data[:20])
                    print(f"   First bytes: {hex_str}")
            except:
                print(f"Got {len(data)} bytes but can't decode")
                hex_str = " ".join(f"{b:02X}" for b in data[:20])
                print(f"   Hex: {hex_str}")
        else:
            print("No data received")
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(0.2)  # Small delay between tests

print("\n" + "=" * 70)
print("❌ No readable data found at any common baud rate")
print("=" * 70)
print("\nPossible issues:")
print("  1. ATmega32 is not running (no firmware uploaded)")
print("  2. ATmega32 is not powered")
print("  3. TX/RX wires are swapped or disconnected")
print("  4. Using an uncommon baud rate not in the list")
print("  5. Fuse bits are wrong (clock not configured)")
print("\nNext steps:")
print("  1. Check if LED blinks (confirms firmware is running)")
print("  2. Verify wiring: ATmega32 TX → USB-TTL RX")
print("  3. Check power supply to ATmega32")
print("  4. Try uploading the simple_uart_test.c firmware")
print("=" * 70)