#!/usr/bin/env python3
"""
Register Test Vehicles in Firebase
Adds vehicles near your actual location in Cairo, Egypt
"""

import firebase_admin
from firebase_admin import credentials, firestore
import sys

# Firebase configuration
FIREBASE_CREDENTIALS = "sdv_firebase_key.json"

# Test vehicles in CAIRO, EGYPT (near location: 30.0754999, 31.6591487)
TEST_VEHICLES_CAIRO = [
    {
        'vehicleId': 'SDV_CAI_001',
        'model': 'Tesla Model S',
        'category': 'luxury',
        'licensePlate': 'CAI-001-EG',
        'color': 'Silver',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 100.0,
        'range': 600.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 85,
        'location': {
            'latitude': 30.0754999,   # Your exact location in Cairo
            'longitude': 31.6591487
        },
        'pricePerHour': 15.0,
        'pricePerKm': 0.5,
    },
    {
        'vehicleId': 'SDV_CAI_002',
        'model': 'BMW i4',
        'category': 'luxury',
        'licensePlate': 'CAI-002-EG',
        'color': 'Blue',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 80.0,
        'range': 500.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 92,
        'location': {
            'latitude': 30.0760,      # 0.6 km away
            'longitude': 31.6595
        },
        'pricePerHour': 18.0,
        'pricePerKm': 0.6,
    },
    {
        'vehicleId': 'SDV_CAI_003',
        'model': 'Nissan Leaf',
        'category': 'compact',
        'licensePlate': 'CAI-003-EG',
        'color': 'White',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 62.0,
        'range': 350.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 78,
        'location': {
            'latitude': 30.0750,      # 0.8 km away
            'longitude': 31.6585
        },
        'pricePerHour': 12.0,
        'pricePerKm': 0.4,
    },
    {
        'vehicleId': 'SDV_CAI_004',
        'model': 'Audi e-tron',
        'category': 'luxury',
        'licensePlate': 'CAI-004-EG',
        'color': 'Black',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 95.0,
        'range': 550.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 95,
        'location': {
            'latitude': 30.0765,      # 1.2 km away
            'longitude': 31.6600
        },
        'pricePerHour': 20.0,
        'pricePerKm': 0.7,
    },
    {
        'vehicleId': 'SDV_CAI_005',
        'model': 'Mercedes EQS',
        'category': 'luxury',
        'licensePlate': 'CAI-005-EG',
        'color': 'White',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 108.0,
        'range': 700.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 88,
        'location': {
            'latitude': 30.0745,      # 1.5 km away
            'longitude': 31.6580
        },
        'pricePerHour': 25.0,
        'pricePerKm': 0.8,
    },
    {
        'vehicleId': 'SDV_CAI_006',
        'model': 'Chevrolet Bolt',
        'category': 'compact',
        'licensePlate': 'CAI-006-EG',
        'color': 'Red',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 65.0,
        'range': 400.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 72,
        'location': {
            'latitude': 30.0770,      # 2.0 km away
            'longitude': 31.6605
        },
        'pricePerHour': 10.0,
        'pricePerKm': 0.3,
    },
    {
        'vehicleId': 'SDV_CAI_007',
        'model': 'Porsche Taycan',
        'category': 'luxury',
        'licensePlate': 'CAI-007-EG',
        'color': 'Gray',
        'year': 2024,
        'seats': 4,
        'batteryCapacity': 93.4,
        'range': 500.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 90,
        'location': {
            'latitude': 30.0740,      # 2.5 km away
            'longitude': 31.6575
        },
        'pricePerHour': 30.0,
        'pricePerKm': 1.0,
    },
    {
        'vehicleId': 'SDV_CAI_008',
        'model': 'Hyundai Ioniq 5',
        'category': 'compact',
        'licensePlate': 'CAI-008-EG',
        'color': 'Green',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 72.6,
        'range': 400.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 82,
        'location': {
            'latitude': 30.0755,      # 0.4 km away
            'longitude': 31.6588
        },
        'pricePerHour': 14.0,
        'pricePerKm': 0.45,
    },
]

# Test vehicles in MANSOURA, EGYPT (near location: 31.0309571, 31.3901344)
TEST_VEHICLES_MANSOURA = [
    {
        'vehicleId': 'SDV_MNS_001',
        'model': 'Tesla Model 3',
        'category': 'luxury',
        'licensePlate': 'MNS-001-EG',
        'color': 'Red',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 75.0,
        'range': 450.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 90,
        'location': {
            'latitude': 31.0309571,   # Exact location in Mansoura
            'longitude': 31.3901344
        },
        'pricePerHour': 15.0,
        'pricePerKm': 0.5,
    },
    {
        'vehicleId': 'SDV_MNS_002',
        'model': 'BMW iX',
        'category': 'luxury',
        'licensePlate': 'MNS-002-EG',
        'color': 'Black',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 111.5,
        'range': 630.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 88,
        'location': {
            'latitude': 31.0315,      # 0.6 km away
            'longitude': 31.3905
        },
        'pricePerHour': 22.0,
        'pricePerKm': 0.7,
    },
    {
        'vehicleId': 'SDV_MNS_003',
        'model': 'Volkswagen ID.4',
        'category': 'compact',
        'licensePlate': 'MNS-003-EG',
        'color': 'Blue',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 77.0,
        'range': 420.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 75,
        'location': {
            'latitude': 31.0305,      # 0.8 km away
            'longitude': 31.3895
        },
        'pricePerHour': 13.0,
        'pricePerKm': 0.4,
    },
    {
        'vehicleId': 'SDV_MNS_004',
        'model': 'Ford Mustang Mach-E',
        'category': 'luxury',
        'licensePlate': 'MNS-004-EG',
        'color': 'White',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 98.8,
        'range': 480.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 92,
        'location': {
            'latitude': 31.0320,      # 1.2 km away
            'longitude': 31.3910
        },
        'pricePerHour': 19.0,
        'pricePerKm': 0.6,
    },
    {
        'vehicleId': 'SDV_MNS_005',
        'model': 'Kia EV6',
        'category': 'compact',
        'licensePlate': 'MNS-005-EG',
        'color': 'Gray',
        'year': 2023,
        'seats': 5,
        'batteryCapacity': 77.4,
        'range': 430.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 80,
        'location': {
            'latitude': 31.0300,      # 1.5 km away
            'longitude': 31.3890
        },
        'pricePerHour': 16.0,
        'pricePerKm': 0.5,
    },
    {
        'vehicleId': 'SDV_MNS_006',
        'model': 'Polestar 2',
        'category': 'luxury',
        'licensePlate': 'MNS-006-EG',
        'color': 'Silver',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 78.0,
        'range': 470.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 85,
        'location': {
            'latitude': 31.0312,      # 0.5 km away
            'longitude': 31.3908
        },
        'pricePerHour': 17.0,
        'pricePerKm': 0.55,
    },
    {
        'vehicleId': 'SDV_MNS_007',
        'model': 'Rivian R1S',
        'category': 'luxury',
        'licensePlate': 'MNS-007-EG',
        'color': 'Green',
        'year': 2024,
        'seats': 7,
        'batteryCapacity': 135.0,
        'range': 510.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 94,
        'location': {
            'latitude': 31.0318,      # 1.0 km away
            'longitude': 31.3912
        },
        'pricePerHour': 28.0,
        'pricePerKm': 0.9,
    },
    {
        'vehicleId': 'SDV_MNS_008',
        'model': 'Genesis GV60',
        'category': 'luxury',
        'licensePlate': 'MNS-008-EG',
        'color': 'Orange',
        'year': 2024,
        'seats': 5,
        'batteryCapacity': 77.4,
        'range': 400.0,
        'status': 'available',
        'isOnline': True,
        'batteryLevel': 87,
        'location': {
            'latitude': 31.0307,      # 0.3 km away
            'longitude': 31.3898
        },
        'pricePerHour': 21.0,
        'pricePerKm': 0.65,
    },
]


def register_vehicles(location='cairo'):
    """Register test vehicles in Firestore"""
    try:
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Select vehicle set
        if location == 'cairo':
            vehicles = TEST_VEHICLES_CAIRO
            location_name = "Cairo, Egypt"
            user_location = "(30.0754999, 31.6591487)"
        else:
            vehicles = TEST_VEHICLES_MANSOURA
            location_name = "Mansoura, Egypt"
            user_location = "(31.0309571, 31.3901344)"
        
        print("=" * 60)
        print(f"🚗 Registering Test Vehicles in {location_name}")
        print(f"📍 Your location: {user_location}")
        print("=" * 60)
        
        for vehicle in vehicles:
            vehicle_id = vehicle['vehicleId']
            
            # Register vehicle
            db.collection('vehicles').document(vehicle_id).set(vehicle, merge=True)
            
            # Calculate distance from user
            from math import radians, sin, cos, sqrt, atan2
            
            if location == 'cairo':
                user_lat, user_lng = 30.0754999, 31.6591487
            else:
                user_lat, user_lng = 31.0309571, 31.3901344
            
            lat = vehicle['location']['latitude']
            lng = vehicle['location']['longitude']
            
            R = 6371  # Earth radius in km
            dlat = radians(lat - user_lat)
            dlng = radians(lng - user_lng)
            a = sin(dlat/2)**2 + cos(radians(user_lat)) * cos(radians(lat)) * sin(dlng/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            print(f"\n✅ Registered: {vehicle['model']}")
            print(f"   - ID: {vehicle_id}")
            print(f"   - License: {vehicle['licensePlate']}")
            print(f"   - Location: ({lat}, {lng})")
            print(f"   - Distance from you: {distance:.2f} km")
            print(f"   - Status: {vehicle['status']}")
            print(f"   - Battery: {vehicle['batteryLevel']}%")
            print(f"   - Price: ${vehicle['pricePerHour']}/hr")
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully registered {len(vehicles)} vehicles in {location_name}")
        print("=" * 60)
        print(f"\n📱 Now open your mobile app and search for vehicles")
        print(f"📍 Make sure location permission is enabled")
        print(f"🔄 Pull down to refresh if needed")
        
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
                
                # Calculate distance from Cairo
                from math import radians, sin, cos, sqrt, atan2
                
                user_lat = 30.0754999
                user_lng = 31.6591487
                
                R = 6371
                dlat = radians(lat - user_lat)
                dlng = radians(lng - user_lng)
                a = sin(dlat/2)**2 + cos(radians(user_lat)) * cos(radians(lat)) * sin(dlng/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                
                print(f"   - Distance from Cairo: {distance:.2f} km")
        
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


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   SDV Vehicle Registration Tool                           ║
    ║   Manage test vehicles in Firebase                        ║
    ║   Your Location: Cairo (30.0754999, 31.6591487)          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("Options:")
    print("  1. Register Cairo vehicles (8 vehicles)")
    print("  2. Register Mansoura vehicles (8 vehicles)")
    print("  3. Register BOTH Cairo + Mansoura vehicles (16 vehicles)")
    print("  4. List all registered vehicles")
    print("  5. Clear all vehicles")
    print("  6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        register_vehicles('cairo')
    elif choice == '2':
        register_vehicles('mansoura')
    elif choice == '3':
        print("\n📍 Registering vehicles in both locations...")
        register_vehicles('cairo')
        print("\n")
        register_vehicles('mansoura')
    elif choice == '4':
        list_vehicles()
    elif choice == '5':
        confirm = input("⚠️  Are you sure? This will delete ALL vehicles (yes/no): ")
        if confirm.lower() == 'yes':
            clear_vehicles()
    elif choice == '6':
        print("Goodbye!")
    else:
        print("Invalid choice")