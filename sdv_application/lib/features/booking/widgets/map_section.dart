import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../../config/constants.dart';

class MapSection extends StatelessWidget {
  final LatLng currentLocation;
  final Set<Marker> markers;
  final Function(GoogleMapController) onMapCreated;

  const MapSection({
    Key? key,
    required this.currentLocation,
    required this.markers,
    required this.onMapCreated,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: AppConstants.defaultMapHeight,
      width: double.infinity,
      child: GoogleMap(
        initialCameraPosition: CameraPosition(
          target: currentLocation,
          zoom: AppConstants.defaultZoom,
        ),
        markers: markers,
        myLocationEnabled: true,
        myLocationButtonEnabled: true,
        zoomControlsEnabled: false,
        onMapCreated: onMapCreated,
      ),
    );
  }
}