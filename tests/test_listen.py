#!/usr/bin/env python3
# save as: test_listen.py

import serial
import time

print("Opening serial port...")
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

# Flush buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

time.sleep(2)

print("Listening for any data from ATmega32...")
print("(ATmega32 should send startup message if firmware is running)")
print("Press Ctrl+C to stop\n")

try:
    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            # Try to decode as text
            try:
                text = data.decode('ascii', errors='ignore')
                print(f"TEXT: {text}", end='')
            except:
                pass
            # Show hex
            print(f"HEX: {' '.join(f'{b:02X}' for b in data)}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped")
finally:
    ser.close()