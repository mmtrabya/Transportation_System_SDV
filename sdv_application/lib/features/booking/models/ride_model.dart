enum RideStatus { none, searching, confirmed, inProgress, completed }

class Ride {
  final String? vehicleId;
  final String? vehicleType;
  final String pickup;
  final String dropoff;
  final double estimatedPrice;
  final int estimatedDuration;
  final double distance;
  final RideStatus status;
  final int? arrivalTime;

  Ride({
    this.vehicleId,
    this.vehicleType,
    required this.pickup,
    required this.dropoff,
    required this.estimatedPrice,
    required this.estimatedDuration,
    required this.distance,
    required this.status,
    this.arrivalTime,
  });

  Ride copyWith({
    String? vehicleId,
    String? vehicleType,
    String? pickup,
    String? dropoff,
    double? estimatedPrice,
    int? estimatedDuration,
    double? distance,
    RideStatus? status,
    int? arrivalTime,
  }) {
    return Ride(
      vehicleId: vehicleId ?? this.vehicleId,
      vehicleType: vehicleType ?? this.vehicleType,
      pickup: pickup ?? this.pickup,
      dropoff: dropoff ?? this.dropoff,
      estimatedPrice: estimatedPrice ?? this.estimatedPrice,
      estimatedDuration: estimatedDuration ?? this.estimatedDuration,
      distance: distance ?? this.distance,
      status: status ?? this.status,
      arrivalTime: arrivalTime ?? this.arrivalTime,
    );
  }
}