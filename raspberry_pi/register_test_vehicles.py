#!/usr/bin/env python3
"""
Register Test Vehicles in Firebase
Manually adds vehicles to Firestore for mobile app testing
"""

import firebase_admin
from firebase_admin import credentials, firestore
import sys

# Firebase configuration
FIREBASE_CREDENTIALS = "sdv_firebase_key.json"

# Test vehicles in Mansoura, Egypt (near your location: 31.0309571, 31.3901344)
TEST_VEHICLES = [
    {
        'vehicleId': 'SDV_001',
        'model': 'Tesla Model S',
        'category': 'luxury',
        'licensePlate': 'MNS-001-EG',
        'color': 'Silver',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 100.0,
        'range': 600.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 85,
        'location': {
            'latitude': 31.0309571,   # Your exact location in Mansoura
            'longitude': 31.3901344
        },
        'pricePerHour': 15.0,
        'pricePerKm': 0.5,
    },
    {
        'vehicleId': 'SDV_002',
        'model': 'BMW i4',
        'category': 'luxury',
        'licensePlate': 'MNS-002-EG',
        'color': 'Blue',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 80.0,
        'range': 500.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 92,
        'location': {
            'latitude': 31.0315,      # 0.6 km away from you
            'longitude': 31.3905
        },
        'pricePerHour': 18.0,
        'pricePerKm': 0.6,
    },
    {
        'vehicleId': 'SDV_003',
        'model': 'Nissan Leaf',
        'category': 'compact',
        'licensePlate': 'MNS-003-EG',
        'color': 'White',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 62.0,
        'range': 350.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 78,
        'location': {
            'latitude': 31.0300,      # 1.2 km away from you
            'longitude': 31.3895
        },
        'pricePerHour': 12.0,
        'pricePerKm': 0.4,
    },
    {
        'vehicleId': 'SDV_004',
        'model': 'Audi e-tron',
        'category': 'luxury',
        'licensePlate': 'MNS-004-EG',
        'color': 'Black',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 95.0,
        'range': 550.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 95,
        'location': {
            'latitude': 31.0320,      # 1.5 km away from you
            'longitude': 31.3910
        },
        'pricePerHour': 20.0,
        'pricePerKm': 0.7,
    },
    {
        'vehicleId': 'SDV_005',
        'model': 'Mercedes EQS',
        'category': 'luxury',
        'licensePlate': 'MNS-005-EG',
        'color': 'White',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 108.0,
        'range': 700.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 88,
        'location': {
            'latitude': 31.0305,      # 0.8 km away from you
            'longitude': 31.3898
        },
        'pricePerHour': 25.0,
        'pricePerKm': 0.8,
    },
    {
        'vehicleId': 'SDV_006',
        'model': 'Chevrolet Bolt',
        'category': 'compact',
        'licensePlate': 'MNS-006-EG',
        'color': 'Red',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 65.0,
        'range': 400.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 72,
        'location': {
            'latitude': 31.0312,      # 1.0 km away from you
            'longitude': 31.3908
        },
        'pricePerHour': 10.0,
        'pricePerKm': 0.3,
    },
]

# OLD Cairo vehicles (kept for reference, not registered by default)
CAIRO_VEHICLES = [
    {
        'vehicleId': 'SDV_CAIRO_001',
        'model': 'Tesla Model 3',
        'category': 'luxury',
        'licensePlate': 'CAI-001-EG',
        'color': 'Red',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 75.0,
        'range': 450.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 90,
        'location': {
            'latitude': 30.0444,
            'longitude': 31.2357
        },
        'pricePerHour': 15.0,
        'pricePerKm': 0.5,
    },
]


def register_vehicles(location='mansoura'):
    """Register test vehicles in Firestore"""
    try:
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Select vehicle set
        vehicles = TEST_VEHICLES if location == 'mansoura' else CAIRO_VEHICLES
        location_name = "Mansoura, Egypt" if location == 'mansoura' else "Cairo, Egypt"
        
        print("=" * 60)
        print(f"🚗 Registering Test Vehicles in {location_name}")
        print("=" * 60)
        
        for vehicle in vehicles:
            vehicle_id = vehicle['vehicleId']
            
            # Register vehicle
            db.collection('vehicles').document(vehicle_id).set(vehicle, merge=True)
            
            print(f"\n✅ Registered: {vehicle['model']}")
            print(f"   - ID: {vehicle_id}")
            print(f"   - License: {vehicle['licensePlate']}")
            print(f"   - Location: ({vehicle['location']['latitude']}, {vehicle['location']['longitude']})")
            print(f"   - Status: {vehicle['status']}")
            print(f"   - Battery: {vehicle['batteryLevel']}%")
            print(f"   - Price: ${vehicle['pricePerHour']}/hr")
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully registered {len(vehicles)} vehicles in {location_name}")
        print("=" * 60)
        print(f"\n📱 Now open your mobile app and search for vehicles in {location_name}")
        print(f"📍 Your location: 31.0309571, 31.3901344 (Mansoura)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def list_vehicles():
    """List all registered vehicles"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        vehicles_ref = db.collection('vehicles')
        vehicles = vehicles_ref.stream()
        
        print("\n" + "=" * 60)
        print("📋 Currently Registered Vehicles")
        print("=" * 60)
        
        count = 0
        for vehicle in vehicles:
            data = vehicle.to_dict()
            count += 1
            
            print(f"\n{count}. {data.get('model', 'Unknown')}")
            print(f"   - ID: {vehicle.id}")
            print(f"   - License: {data.get('licensePlate', 'N/A')}")
            print(f"   - Status: {data.get('status', 'Unknown')}")
            print(f"   - Online: {data.get('isOnline', False)}")
            print(f"   - Battery: {data.get('batteryLevel', 0)}%")
            
            location = data.get('location')
            if location:
                lat = location.get('latitude')
                lng = location.get('longitude')
                print(f"   - Location: ({lat}, {lng})")
                
                # Calculate distance from Mansoura
                from math import radians, sin, cos, sqrt, atan2
                
                # Your location in Mansoura
                user_lat = 31.0309571
                user_lng = 31.3901344
                
                # Haversine formula
                R = 6371  # Earth radius in km
                
                dlat = radians(lat - user_lat)
                dlng = radians(lng - user_lng)
                
                a = sin(dlat/2)**2 + cos(radians(user_lat)) * cos(radians(lat)) * sin(dlng/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                
                print(f"   - Distance from you: {distance:.2f} km")
        
        if count == 0:
            print("\n⚠️  No vehicles found in database")
        else:
            print(f"\n📊 Total vehicles: {count}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def clear_vehicles():
    """Clear all test vehicles"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        vehicles_ref = db.collection('vehicles')
        vehicles = vehicles_ref.stream()
        
        count = 0
        for vehicle in vehicles:
            vehicle.reference.delete()
            count += 1
            print(f"❌ Deleted: {vehicle.id}")
        
        print(f"\n✅ Deleted {count} vehicles")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def update_vehicle_location(vehicle_id, latitude, longitude):
    """Update a specific vehicle's location"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        db.collection('vehicles').document(vehicle_id).update({
            'location': {
                'latitude': latitude,
                'longitude': longitude
            }
        })
        
        print(f"✅ Updated {vehicle_id} location to ({latitude}, {longitude})")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Vehicle Registration Tool                           ║
    ║   Manage test vehicles in Firebase                        ║
    ║   Location: Mansoura, Egypt (31.0309571, 31.3901344)     ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("Options:")
    print("  1. Register Mansoura vehicles (near you - 6 vehicles)")
    print("  2. Register Cairo vehicles (110 km away)")
    print("  3. List all registered vehicles")
    print("  4. Clear all vehicles")
    print("  5. Update specific vehicle location")
    print("  6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        register_vehicles('mansoura')
    elif choice == '2':
        register_vehicles('cairo')
    elif choice == '3':
        list_vehicles()
    elif choice == '4':
        confirm = input("⚠️  Are you sure? This will delete ALL vehicles (yes/no): ")
        if confirm.lower() == 'yes':
            clear_vehicles()
    elif choice == '5':
        vehicle_id = input("Enter vehicle ID: ").strip()
        lat = float(input("Enter latitude: ").strip())
        lng = float(input("Enter longitude: ").strip())
        update_vehicle_location(vehicle_id, lat, lng)
    elif choice == '6':
        print("Goodbye!")
    else:
        print("Invalid choice")