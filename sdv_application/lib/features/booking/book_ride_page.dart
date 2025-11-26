import 'package:flutter/material.dart';
import 'dart:async';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../config/constants.dart';
import '../../core/utils/haptic_feedback.dart';
import '../../core/utils/animations.dart';
import 'models/ride_model.dart';
import 'widgets/location_field.dart';
import 'widgets/vehicle_card.dart';
import 'widgets/price_estimator.dart';
import 'widgets/map_section.dart';
import 'widgets/ride_status_screens.dart';

class BookRidePage extends StatefulWidget {
  final VoidCallback onThemeToggle;
  const BookRidePage({Key? key, required this.onThemeToggle}) : super(key: key);

  @override
  State<BookRidePage> createState() => _BookRidePageState();
}

class _BookRidePageState extends State<BookRidePage>
    with TickerProviderStateMixin {
  final TextEditingController _pickupController = TextEditingController();
  final TextEditingController _dropoffController = TextEditingController();
  String? _selectedVehicleType;
  RideStatus _rideStatus = RideStatus.none;
  int _arrivalTime = AppConstants.defaultArrivalTime;
  Timer? _timer;
  GoogleMapController? _mapController;

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  double _estimatedPrice = 15.50;
  int _rating = 0;

  final LatLng _currentLocation = const LatLng(37.7749, -122.4194);
  final Set<Marker> _markers = {};

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: Duration(milliseconds: AppConstants.pulseAnimationDuration),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = AppAnimations.createPulseAnimation(_pulseController);
    _initializeMap();
  }

  void _initializeMap() {
    _markers.add(
      Marker(
        markerId: const MarkerId('current'),
        position: _currentLocation,
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueBlue),
        infoWindow: const InfoWindow(title: 'Your Location'),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    _pickupController.dispose();
    _dropoffController.dispose();
    _mapController?.dispose();
    super.dispose();
  }

  void _calculatePrice() {
    double basePrice = AppConstants.standardBasePrice;
    switch (_selectedVehicleType) {
      case 'Standard':
        basePrice = AppConstants.standardBasePrice;
        break;
      case 'Comfort':
        basePrice = AppConstants.comfortBasePrice;
        break;
      case 'Luxury':
        basePrice = AppConstants.luxuryBasePrice;
        break;
    }

    double distance = 8.5;
    setState(() {
      _estimatedPrice = basePrice + (distance * AppConstants.pricePerKm);
    });
  }

  void _showSnackBar(String message, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _searchForRide() {
    if (_pickupController.text.isEmpty || _dropoffController.text.isEmpty) {
      _showSnackBar('Please enter both pickup and drop-off locations',
          isError: true);
      return;
    }
    if (_selectedVehicleType == null) {
      _showSnackBar('Please select a vehicle type', isError: true);
      return;
    }

    AppHaptics.medium();
    setState(() => _rideStatus = RideStatus.searching);

    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        AppHaptics.heavy();
        setState(() {
          _rideStatus = RideStatus.confirmed;
          _arrivalTime = AppConstants.defaultArrivalTime;
        });
        _startCountdown();
      }
    });
  }

  void _startCountdown() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (_arrivalTime > 0) {
          _arrivalTime--;
        } else {
          timer.cancel();
          AppHaptics.heavy();
          _rideStatus = RideStatus.inProgress;
        }
      });
    });
  }

  void _cancelRide() {
    AppHaptics.medium();
    _timer?.cancel();
    setState(() => _rideStatus = RideStatus.none);
    _showSnackBar('Ride cancelled', isError: false);
  }

  void _completeRide() {
    AppHaptics.heavy();
    setState(() => _rideStatus = RideStatus.completed);
  }

  void _resetRide() {
    setState(() {
      _rideStatus = RideStatus.none;
      _pickupController.clear();
      _dropoffController.clear();
      _selectedVehicleType = null;
      _rating = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Book Your Ride',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: Icon(
              Theme.of(context).brightness == Brightness.light
                  ? Icons.dark_mode_outlined
                  : Icons.light_mode_outlined,
            ),
            onPressed: widget.onThemeToggle,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    switch (_rideStatus) {
      case RideStatus.searching:
        return SearchingScreen(
          pulseAnimation: _pulseAnimation,
          onCancel: _cancelRide,
        );
      case RideStatus.confirmed:
        return _buildConfirmedScreen();
      case RideStatus.inProgress:
        return _buildInProgressScreen();
      case RideStatus.completed:
        return _buildCompletedScreen();
      default:
        return _buildBookingForm();
    }
  }

  Widget _buildBookingForm() {
    return RefreshIndicator(
      onRefresh: () async {
        AppHaptics.light();
        await Future.delayed(const Duration(seconds: 1));
        _showSnackBar('Location refreshed', isError: false);
      },
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: Column(
          children: [
            MapSection(
              currentLocation: _currentLocation,
              markers: _markers,
              onMapCreated: (controller) => _mapController = controller,
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Where to?',
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 24),
                  LocationField(
                    controller: _pickupController,
                    label: 'Pickup Location',
                    icon: Icons.my_location,
                    hint: 'Enter pickup address',
                  ),
                  const SizedBox(height: 16),
                  LocationField(
                    controller: _dropoffController,
                    label: 'Drop-off Location',
                    icon: Icons.location_on,
                    hint: 'Where do you want to go?',
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Select Vehicle Type',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  _buildVehicleTypes(),
                  if (_selectedVehicleType != null) ...[
                    const SizedBox(height: 24),
                    PriceEstimator(price: _estimatedPrice),
                  ],
                  const SizedBox(height: 24),
                  _buildActionButton(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVehicleTypes() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: VehicleCard(
                name: 'Standard',
                icon: Icons.directions_car,
                capacity: '4 seats',
                price: '\$8-12',
                isSelected: _selectedVehicleType == 'Standard',
                onTap: () {
                  setState(() {
                    _selectedVehicleType = 'Standard';
                    _calculatePrice();
                  });
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: VehicleCard(
                name: 'Comfort',
                icon: Icons.airport_shuttle,
                capacity: '6 seats',
                price: '\$12-18',
                isSelected: _selectedVehicleType == 'Comfort',
                onTap: () {
                  setState(() {
                    _selectedVehicleType = 'Comfort';
                    _calculatePrice();
                  });
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: VehicleCard(
                name: 'Luxury',
                icon: Icons.car_rental,
                capacity: '4 seats',
                price: '\$20-30',
                isSelected: _selectedVehicleType == 'Luxury',
                onTap: () {
                  setState(() {
                    _selectedVehicleType = 'Luxury';
                    _calculatePrice();
                  });
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Theme.of(context)
                      .colorScheme
                      .surface
                      .withOpacity(0.5),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.grey.withOpacity(0.3)),
                ),
                child: const Column(
                  children: [
                    Icon(Icons.add_circle_outline, size: 40, color: Colors.grey),
                    SizedBox(height: 8),
                    Text('More', style: TextStyle(color: Colors.grey)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildActionButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _searchForRide,
        style: ElevatedButton.styleFrom(
          backgroundColor: Theme.of(context).colorScheme.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 18),
          elevation: 8,
          shadowColor:
          Theme.of(context).colorScheme.primary.withOpacity(0.5),
        ),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search),
            SizedBox(width: 8),
            Text(
              'Find Available Vehicles',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfirmedScreen() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  const SizedBox(height: 20),
                  ScaleTransition(
                    scale: _pulseAnimation,
                    child: Container(
                      width: 150,
                      height: 150,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            Theme.of(context).colorScheme.primary,
                            Theme.of(context).colorScheme.secondary,
                          ],
                        ),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Theme.of(context)
                                .colorScheme
                                .primary
                                .withOpacity(0.4),
                            blurRadius: 30,
                            spreadRadius: 5,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.directions_car,
                        size: 80,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text(
                    'Vehicle Found!',
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context).colorScheme.primary,
                          Theme.of(context).colorScheme.secondary,
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'SDV-${DateTime.now().millisecond.toString().padLeft(3, '0')}',
                      style: const TextStyle(
                        fontSize: 20,
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context)
                              .colorScheme
                              .primary
                              .withOpacity(0.1),
                          Theme.of(context)
                              .colorScheme
                              .secondary
                              .withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Column(
                      children: [
                        const Text(
                          'Arriving in',
                          style: TextStyle(fontSize: 16, color: Colors.grey),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '$_arrivalTime',
                          style: TextStyle(
                            fontSize: 64,
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                        const Text(
                          'minutes',
                          style: TextStyle(fontSize: 18, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),
                  InfoRow(
                    icon: Icons.local_offer,
                    label: 'Estimated Fare',
                    value: '\$${_estimatedPrice.toStringAsFixed(2)}',
                  ),
                  const SizedBox(height: 12),
                  const InfoRow(
                    icon: Icons.access_time,
                    label: 'Trip Duration',
                    value: '18 min',
                  ),
                  const SizedBox(height: 12),
                  const InfoRow(
                    icon: Icons.route,
                    label: 'Distance',
                    value: '8.5 km',
                  ),
                ],
              ),
            ),
          ),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _cancelRide,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    side: const BorderSide(color: Colors.red),
                  ),
                  child: const Text(
                    'Cancel',
                    style: TextStyle(color: Colors.red),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ElevatedButton(
                  onPressed: () {},
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: const Text('Contact'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInProgressScreen() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  const SizedBox(height: 20),
                  Container(
                    width: 200,
                    height: 200,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context).colorScheme.primary,
                          Theme.of(context).colorScheme.secondary,
                          Theme.of(context).colorScheme.tertiary,
                        ],
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Theme.of(context)
                              .colorScheme
                              .primary
                              .withOpacity(0.4),
                          blurRadius: 40,
                          spreadRadius: 10,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.navigation,
                      size: 100,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text(
                    'En Route to Destination',
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Enjoy your autonomous ride!',
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                  const SizedBox(height: 48),
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context)
                              .colorScheme
                              .primary
                              .withOpacity(0.1),
                          Theme.of(context)
                              .colorScheme
                              .secondary
                              .withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildStat('12 min', 'ETA'),
                        Container(
                          width: 1,
                          height: 50,
                          color: Colors.grey.withOpacity(0.3),
                        ),
                        _buildStat('5.2 km', 'Distance'),
                        Container(
                          width: 1,
                          height: 50,
                          color: Colors.grey.withOpacity(0.3),
                        ),
                        _buildStat('45 km/h', 'Speed'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.green.withOpacity(0.1),
                          Colors.green.withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(16),
                      border:
                      Border.all(color: Colors.green.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.green.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(
                            Icons.security,
                            color: Colors.green[700],
                            size: 32,
                          ),
                        ),
                        const SizedBox(width: 16),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'AI Safety Systems Active',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 15,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Lane Detection • Obstacle Avoidance',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  OutlinedButton.icon(
                    onPressed: _completeRide,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Simulate Arrival'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 32,
                        vertical: 16,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                AppHaptics.heavy();
                _showSnackBar('Emergency stop initiated!', isError: true);
              },
              icon: const Icon(Icons.warning_rounded),
              label: const Text('Emergency Stop'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red[400],
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 18),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStat(String value, String label) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: Colors.grey),
        ),
      ],
    );
  }

  Widget _buildCompletedScreen() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  Container(
                    width: 150,
                    height: 150,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.green.withOpacity(0.2),
                          Colors.green.withOpacity(0.1),
                        ],
                      ),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.check_circle,
                      size: 100,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text(
                    'Trip Completed!',
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Thank you for riding with us',
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                  const SizedBox(height: 48),
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context)
                              .colorScheme
                              .primary
                              .withOpacity(0.1),
                          Theme.of(context)
                              .colorScheme
                              .secondary
                              .withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'Total Fare',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              '\$${_estimatedPrice.toStringAsFixed(2)}',
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ],
                        ),
                        const Divider(height: 32),
                        _buildSummaryRow('Distance', '8.5 km'),
                        const SizedBox(height: 12),
                        _buildSummaryRow('Duration', '18 min'),
                        const SizedBox(height: 12),
                        _buildSummaryRow(
                          'Vehicle',
                          _selectedVehicleType ?? 'Standard',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text(
                    'Rate Your Experience',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(
                      5,
                          (index) => GestureDetector(
                        onTap: () {
                          AppHaptics.selection();
                          setState(() => _rating = index + 1);
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Icon(
                            _rating > index ? Icons.star : Icons.star_border,
                            color: Colors.amber,
                            size: 45,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                AppHaptics.medium();
                if (_rating > 0) {
                  _showSnackBar('Thank you for your feedback!',
                      isError: false);
                }
                _resetRide();
              },
              icon: const Icon(Icons.add_circle_outline),
              label: const Text(
                'Book Another Ride',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 18),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 16, color: Colors.grey)),
        Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}