import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'config/theme/app_theme.dart';
import 'features/splash/splash_screen.dart';
import 'features/home/home_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const SmartCityTransportApp());
}

class SmartCityTransportApp extends StatefulWidget {
  const SmartCityTransportApp({Key? key}) : super(key: key);

  @override
  State<SmartCityTransportApp> createState() => _SmartCityTransportAppState();
}

class _SmartCityTransportAppState extends State<SmartCityTransportApp> {
  ThemeMode _themeMode = ThemeMode.light;
  bool _showSplash = true;

  @override
  void initState() {
    super.initState();
    _initApp();
  }

  Future<void> _initApp() async {
    await Future.delayed(const Duration(seconds: 3));
    if (mounted) {
      setState(() => _showSplash = false);
    }
  }

  void _toggleTheme() {
    setState(() {
      _themeMode = _themeMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart City Transport',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme(),
      darkTheme: AppTheme.darkTheme(),
      themeMode: _themeMode,
      home: _showSplash
          ? const SplashScreen()
          : HomePage(onThemeToggle: _toggleTheme),
    );
  }
}