import 'package:flutter/material.dart';

class AppColors {
  // Primary Blue Gradient
  static const Color primaryBlue = Color(0xFF1976D2);
  static const Color secondaryBlue = Color(0xFF42A5F5);
  static const Color tertiaryBlue = Color(0xFF64B5F6);

  // Background Colors
  static const Color lightBackground = Color(0xFFF5F7FA);
  static const Color darkBackground = Color(0xFF121212);
  static const Color darkSurface = Color(0xFF1E1E1E);

  // Status Colors
  static const Color success = Colors.green;
  static const Color error = Color(0xFFD32F2F);
  static const Color warning = Colors.amber;

  // Gradients
  static const LinearGradient blueGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primaryBlue, secondaryBlue, tertiaryBlue],
  );

  static LinearGradient blueGradientWithOpacity(double opacity) {
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        primaryBlue.withOpacity(opacity * 0.9),
        secondaryBlue.withOpacity(opacity * 0.8),
        tertiaryBlue.withOpacity(opacity * 0.7),
      ],
    );
  }
}