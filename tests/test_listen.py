#!/usr/bin/env python3
"""
DEBUG VERSION - ATmega32 Communication Test
Shows exactly what's being sent and received
"""

import serial
import serial.tools.list_ports
import struct
import time
import sys

# Protocol constants
START_BYTE = 0xAA
END_BYTE = 0x55

print("\n" + "="*70)
print("   ATmega32 <-> PC Communication Test [DEBUG MODE]")
print("="*70)

# ==================== UTILITIES ====================

def hex_dump(data, label=""):
    """Pretty print hex data"""
    if label:
        print(f"{label}: ", end="")
    print(" ".join(f"{b:02X}" for b in data))

def bytes_to_hex(data):
    """Convert bytes to hex string"""
    return " ".join(f"{b:02X}" for b in data)

# ==================== FIND SERIAL PORT ====================

def find_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No serial ports found!")
        print("\nTroubleshooting:")
        print("  1. Check USB-TTL adapter is connected")
        print("  2. Verify ATmega32 has power")
        print("  3. Try a different USB port")
        print("  4. Check device manager (Windows) or dmesg (Linux)")
        sys.exit(1)
    
    print("\n📡 Available Serial Ports:")
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port.device}")
        print(f"     Description: {port.description}")
        if port.manufacturer:
            print(f"     Manufacturer: {port.manufacturer}")
    
    return ports

ports = find_ports()

# Select port
if len(ports) == 1:
    selected = ports[0].device
    print(f"\n✓ Auto-selected: {selected}")
else:
    try:
        choice = input(f"\nSelect port (1-{len(ports)}) or Enter for first: ").strip()
        idx = int(choice) - 1 if choice else 0
        selected = ports[idx].device
    except:
        selected = ports[0].device
    print(f"✓ Selected: {selected}")

# ==================== CONNECT ====================

print(f"\n🔌 Connecting to {selected} at 115200 baud...")
print("   (This may take 2-3 seconds for ATmega32 to reset)")

try:
    ser = serial.Serial(
        port=selected,
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )
    time.sleep(2.5)  # Wait for ATmega32 bootloader/reset
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("✓ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# ==================== READ STARTUP MESSAGE ====================

print("\n📨 Reading startup messages...")
time.sleep(1)

startup_data = bytearray()
while ser.in_waiting > 0:
    startup_data.extend(ser.read(ser.in_waiting))
    time.sleep(0.1)

if startup_data:
    print("\n" + "─" * 70)
    try:
        text = startup_data.decode('ascii', errors='replace')
        print(text)
    except:
        print(f"Raw bytes: {bytes_to_hex(startup_data)}")
    print("─" * 70)
else:
    print("⚠️  No startup message received")
    print("   ATmega32 might not be running the debug firmware")

# ==================== PROTOCOL FUNCTIONS ====================

def create_packet(cmd, data=b''):
    """Create protocol packet with checksum"""
    length = len(data)
    checksum = (cmd + length + sum(data)) & 0xFF
    packet = bytes([START_BYTE, cmd, length]) + data + bytes([checksum, END_BYTE])
    return packet

def parse_packet(data):
    """Parse and validate packet"""
    if len(data) < 5:
        return None, None, "Too short"
    
    if data[0] != START_BYTE:
        return None, None, f"Bad start: 0x{data[0]:02X}"
    
    if data[-1] != END_BYTE:
        return None, None, f"Bad end: 0x{data[-1]:02X}"
    
    cmd = data[1]
    length = data[2]
    
    if len(data) < length + 5:
        return None, None, f"Incomplete: need {length+5}, got {len(data)}"
    
    payload = data[3:3+length]
    checksum_rx = data[3+length]
    
    checksum_calc = (cmd + length + sum(payload)) & 0xFF
    
    if checksum_rx != checksum_calc:
        return None, None, f"Checksum: got 0x{checksum_rx:02X}, expected 0x{checksum_calc:02X}"
    
    return cmd, payload, "OK"

def send_command(cmd, data=b'', label=""):
    """Send command and show what's sent"""
    packet = create_packet(cmd, data)
    
    if label:
        print(f"\n📤 {label}")
    print(f"   CMD: 0x{cmd:02X} | Data: {len(data)} bytes")
    print(f"   Packet: {bytes_to_hex(packet)}")
    
    ser.write(packet)
    ser.flush()
    return time.time()

def receive_response(timeout=1.0, expect_cmd=None):
    """Receive and parse response"""
    start = time.time()
    buffer = bytearray()
    
    while time.time() - start < timeout:
        if ser.in_waiting > 0:
            new_data = ser.read(ser.in_waiting)
            buffer.extend(new_data)
            
            # Show any text messages (debug output from ATmega32)
            try:
                text = new_data.decode('ascii', errors='ignore')
                if text.isprintable() or '\r' in text or '\n' in text:
                    if text.strip():
                        print(f"   📝 Debug: {text.strip()}")
            except:
                pass
            
            # Try to find packet
            if START_BYTE in buffer:
                start_idx = buffer.index(START_BYTE)
                
                if len(buffer) >= start_idx + 5:
                    length = buffer[start_idx + 2]
                    packet_size = length + 5
                    
                    if len(buffer) >= start_idx + packet_size:
                        packet = bytes(buffer[start_idx:start_idx + packet_size])
                        cmd, payload, status = parse_packet(packet)
                        
                        if status == "OK":
                            print(f"   📥 Response: 0x{cmd:02X} | {len(payload)} bytes")
                            if len(payload) <= 20:
                                print(f"      Data: {bytes_to_hex(payload)}")
                            return cmd, payload
                        else:
                            print(f"   ⚠️  Parse error: {status}")
                            print(f"      Packet: {bytes_to_hex(packet)}")
                            # Remove bad packet and continue
                            buffer = buffer[start_idx + 1:]
                            continue
        
        time.sleep(0.01)
    
    if buffer:
        print(f"   ⏱️  Timeout - buffer has {len(buffer)} bytes:")
        print(f"      {bytes_to_hex(buffer[:50])}")
    else:
        print(f"   ⏱️  Timeout - no data received")
    
    return None, None

# ==================== BASIC TESTS ====================

print("\n" + "="*70)
print("   Basic Communication Tests")
print("="*70)

# Test 1: System Status
print("\n[TEST 1] System Status Request (0x22)")
send_command(0x22, label="Requesting system status")
cmd, data = receive_response(timeout=2.0, expect_cmd=0xB4)

if cmd == 0xB4 and len(data) >= 10:
    try:
        uptime, voltage, cpu_load, errors = struct.unpack('<IfBB', data[:10])
        print(f"   ✓ SUCCESS!")
        print(f"      Uptime: {uptime} seconds")
        print(f"      Battery: {voltage:.2f} V")
        print(f"      CPU Load: {cpu_load}%")
        print(f"      Errors: {errors}")
    except Exception as e:
        print(f"   ⚠️  Parse error: {e}")
else:
    print(f"   ❌ FAILED - Expected 0xB4, got {f'0x{cmd:02X}' if cmd else 'nothing'}")

time.sleep(0.5)

# Test 2: GPS Data
print("\n[TEST 2] GPS Data Request (0x10)")
send_command(0x10, label="Requesting GPS data")
cmd, data = receive_response(timeout=2.0, expect_cmd=0xB0)

if cmd == 0xB0 and len(data) >= 19:
    try:
        lat, lon, alt, speed, sats, fix, valid = struct.unpack('<ffffBBB', data[:19])
        print(f"   ✓ SUCCESS!")
        print(f"      Location: {lat:.6f}°N, {lon:.6f}°E")
        print(f"      Altitude: {alt:.1f} m")
        print(f"      Speed: {speed:.1f} km/h")
        print(f"      Satellites: {sats}")
        print(f"      Valid: {'Yes' if valid else 'No'}")
    except Exception as e:
        print(f"   ⚠️  Parse error: {e}")
else:
    print(f"   ❌ FAILED - Expected 0xB0, got {f'0x{cmd:02X}' if cmd else 'nothing'}")

time.sleep(0.5)

# Test 3: IMU Data
print("\n[TEST 3] IMU Data Request (0x11)")
send_command(0x11, label="Requesting IMU data")
cmd, data = receive_response(timeout=2.0, expect_cmd=0xB1)

if cmd == 0xB1 and len(data) >= 48:
    try:
        values = struct.unpack('<12f', data[:48])
        print(f"   ✓ SUCCESS!")
        print(f"      Accel: X={values[0]:.2f} Y={values[1]:.2f} Z={values[2]:.2f} m/s²")
        print(f"      Gyro:  X={values[3]:.2f} Y={values[4]:.2f} Z={values[5]:.2f} °/s")
        print(f"      Orientation: Roll={values[9]:.1f}° Pitch={values[10]:.1f}° Yaw={values[11]:.1f}°")
    except Exception as e:
        print(f"   ⚠️  Parse error: {e}")
else:
    print(f"   ❌ FAILED - Expected 0xB1, got {f'0x{cmd:02X}' if cmd else 'nothing'}")

time.sleep(0.5)

# Test 4: Ultrasonic
print("\n[TEST 4] Ultrasonic Data Request (0x12)")
send_command(0x12, label="Requesting ultrasonic data")
cmd, data = receive_response(timeout=2.0, expect_cmd=0xB2)

if cmd == 0xB2 and len(data) >= 16:
    try:
        front, rear, left, right = struct.unpack('<4f', data[:16])
        print(f"   ✓ SUCCESS!")
        print(f"      Front: {front:.1f} cm")
        print(f"      Rear:  {rear:.1f} cm")
        print(f"      Left:  {left:.1f} cm")
        print(f"      Right: {right:.1f} cm")
    except Exception as e:
        print(f"   ⚠️  Parse error: {e}")
else:
    print(f"   ❌ FAILED - Expected 0xB2, got {f'0x{cmd:02X}' if cmd else 'nothing'}")

# ==================== INTERACTIVE MODE ====================

print("\n" + "="*70)
print("   Interactive Mode")
print("="*70)
print("\nCommands:")
print("  1 - GPS data")
print("  2 - IMU data")
print("  3 - Ultrasonic data")
print("  4 - All sensors")
print("  5 - System status")
print("  m - Monitor mode (continuous)")
print("  r - Raw receive (show everything)")
print("  q - Quit")

try:
    while True:
        choice = input("\n> ").strip().lower()
        
        if choice == 'q':
            break
        
        elif choice == '1':
            send_command(0x10, label="GPS Request")
            receive_response(timeout=1.5)
        
        elif choice == '2':
            send_command(0x11, label="IMU Request")
            receive_response(timeout=1.5)
        
        elif choice == '3':
            send_command(0x12, label="Ultrasonic Request")
            receive_response(timeout=1.5)
        
        elif choice == '4':
            send_command(0x13, label="All Sensors Request")
            print("   Waiting for multiple responses...")
            time.sleep(0.5)
            
            # Try to read multiple packets
            for i in range(3):
                cmd, data = receive_response(timeout=1.0)
                if cmd:
                    if cmd == 0xB0:
                        print("      ✓ GPS packet")
                    elif cmd == 0xB1:
                        print("      ✓ IMU packet")
                    elif cmd == 0xB2:
                        print("      ✓ Ultrasonic packet")
                time.sleep(0.1)
        
        elif choice == '5':
            send_command(0x22, label="Status Request")
            receive_response(timeout=1.5)
        
        elif choice == 'm':
            print("\n📊 Monitor Mode (Press Ctrl+C to stop)")
            print("   Requesting all sensors every 2 seconds...\n")
            
            count = 0
            try:
                while True:
                    count += 1
                    print(f"\n[{count}] ───────────────────────────────────")
                    
                    send_command(0x13)
                    time.sleep(0.5)
                    
                    # Collect all responses
                    start = time.time()
                    while time.time() - start < 1.0:
                        cmd, data = receive_response(timeout=0.5)
                        
                        if cmd == 0xB0 and data:  # GPS
                            try:
                                lat, lon = struct.unpack('<ff', data[:8])
                                print(f"   📍 GPS: {lat:.4f}°N, {lon:.4f}°E")
                            except:
                                pass
                        
                        elif cmd == 0xB1 and data:  # IMU
                            try:
                                values = struct.unpack('<12f', data[:48])
                                print(f"   🧭 IMU: Roll={values[9]:.1f}° Pitch={values[10]:.1f}° Yaw={values[11]:.1f}°")
                            except:
                                pass
                        
                        elif cmd == 0xB2 and data:  # Ultrasonic
                            try:
                                front, rear, left, right = struct.unpack('<4f', data[:16])
                                print(f"   📏 Dist: F={front:.0f} R={rear:.0f} L={left:.0f} R={right:.0f} cm")
                            except:
                                pass
                    
                    time.sleep(1.5)
            
            except KeyboardInterrupt:
                print("\n   Monitor stopped")
        
        elif choice == 'r':
            print("\n📡 Raw Receive Mode (Press Ctrl+C to stop)")
            print("   Showing all incoming data...\n")
            
            try:
                while True:
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        
                        # Try to decode as text
                        try:
                            text = data.decode('ascii', errors='replace')
                            if any(c.isprintable() or c in '\r\n\t' for c in text):
                                print(f"TEXT: {text}", end='')
                                continue
                        except:
                            pass
                        
                        # Show as hex
                        hex_dump(data, "HEX")
                    
                    time.sleep(0.05)
            
            except KeyboardInterrupt:
                print("\n   Raw mode stopped")
        
        else:
            print("   Unknown command")

except KeyboardInterrupt:
    print("\n")

# ==================== CLEANUP ====================

print("\n" + "="*70)
print("   Closing Connection")
print("="*70)

ser.close()
print("✓ Disconnected")
print("\nTest completed!")
print("="*70 + "\n")