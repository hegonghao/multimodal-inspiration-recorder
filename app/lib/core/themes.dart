/// Theme configuration for the multimodal inspiration recorder
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// App themes
class AppThemes {
  AppThemes._();

  /// Light theme configuration
  static ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: _lightColorScheme,
    scaffoldBackgroundColor: _lightColorScheme.surface,
    appBarTheme: _lightAppBarTheme,
    cardTheme: _cardTheme,
    elevatedButtonTheme: _elevatedButtonTheme,
    textButtonTheme: _textButtonTheme,
    outlinedButtonTheme: _outlinedButtonTheme,
    floatingActionButtonTheme: _fabTheme,
    inputDecorationTheme: _inputDecorationTheme,
    dividerTheme: _dividerTheme,
    chipTheme: _chipTheme,
    snackBarTheme: _snackBarTheme,
    dialogTheme: _dialogTheme,
    bottomNavigationBarTheme: _bottomNavTheme,
    textTheme: _textTheme,
  );

  /// Dark theme configuration
  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: _darkColorScheme,
    scaffoldBackgroundColor: _darkColorScheme.surface,
    appBarTheme: _darkAppBarTheme,
    cardTheme: _cardTheme,
    elevatedButtonTheme: _elevatedButtonTheme,
    textButtonTheme: _textButtonTheme,
    outlinedButtonTheme: _outlinedButtonTheme,
    floatingActionButtonTheme: _fabTheme,
    inputDecorationTheme: _inputDecorationTheme,
    dividerTheme: _dividerTheme,
    chipTheme: _chipTheme,
    snackBarTheme: _snackBarTheme,
    dialogTheme: _dialogTheme,
    bottomNavigationBarTheme: _bottomNavTheme,
    textTheme: _textTheme,
  );

  // Color schemes
  static const ColorScheme _lightColorScheme = ColorScheme.light(
    primary: Color(0xFF1976D2), // Blue 700
    primaryContainer: Color(0xFFBBDEFB), // Blue 100
    onPrimaryContainer: Color(0xFF0D47A1), // Blue 900
    secondary: Color(0xFF43A047), // Green 600
    onSecondary: Colors.white,
    secondaryContainer: Color(0xFFC8E6C9), // Green 100
    onSecondaryContainer: Color(0xFF1B5E20), // Green 900
    tertiary: Color(0xFFF57C00), // Orange 700
    onTertiary: Colors.white,
    tertiaryContainer: Color(0xFFFFE0B2), // Orange 100
    onTertiaryContainer: Color(0xFFE65100), // Orange 900
    error: Color(0xFFD32F2F), // Red 700
    errorContainer: Color(0xFFFFCDD2), // Red 100
    onErrorContainer: Color(0xFFB71C1C), // Red 900
    surface: Color(0xFFFAFAFA), // Grey 50
    onSurface: Color(0xFF212121), // Grey 900
    surfaceContainerHighest: Color(0xFFEEEEEE), // Grey 200
    outline: Color(0xFFBDBDBD), // Grey 400
    shadow: Color(0x1F000000),
  );

  static const ColorScheme _darkColorScheme = ColorScheme.dark(
    primary: Color(0xFF64B5F6), // Blue 300
    onPrimary: Color(0xFF0D47A1), // Blue 900
    primaryContainer: Color(0xFF1565C0), // Blue 800
    onPrimaryContainer: Color(0xFFBBDEFB), // Blue 100
    secondary: Color(0xFF81C784), // Green 300
    onSecondary: Color(0xFF1B5E20), // Green 900
    secondaryContainer: Color(0xFF2E7D32), // Green 800
    onSecondaryContainer: Color(0xFFC8E6C9), // Green 100
    tertiary: Color(0xFFFFB74D), // Orange 300
    onTertiary: Color(0xFFE65100), // Orange 900
    tertiaryContainer: Color(0xFFF57C00), // Orange 700
    onTertiaryContainer: Color(0xFFFFE0B2), // Orange 100
    error: Color(0xFFEF5350), // Red 400
    onError: Color(0xFFB71C1C), // Red 900
    errorContainer: Color(0xFFC62828), // Red 800
    onErrorContainer: Color(0xFFFFCDD2), // Red 100
    onSurface: Color(0xFFE0E0E0), // Light text
    surfaceContainerHighest: Color(0xFF2C2C2C), // Elevated surface
    outline: Color(0xFF757575), // Grey 600
    shadow: Color(0x3F000000),
  );

  // AppBar themes
  static const AppBarTheme _lightAppBarTheme = AppBarTheme(
    centerTitle: true,
    elevation: 0,
    scrolledUnderElevation: 3,
    systemOverlayStyle: SystemUiOverlayStyle.dark,
  );

  static const AppBarTheme _darkAppBarTheme = AppBarTheme(
    centerTitle: true,
    elevation: 0,
    scrolledUnderElevation: 3,
    systemOverlayStyle: SystemUiOverlayStyle.light,
  );

  // Card theme
  static const CardThemeData _cardTheme = CardThemeData(
    elevation: 2,
    margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(16)),
    ),
  );

  // Button themes
  static final ElevatedButtonThemeData _elevatedButtonTheme = ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      elevation: 2,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      minimumSize: const Size(88, 48),
    ),
  );

  static final TextButtonThemeData _textButtonTheme = TextButtonThemeData(
    style: TextButton.styleFrom(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
    ),
  );

  static final OutlinedButtonThemeData _outlinedButtonTheme = OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      minimumSize: const Size(88, 48),
      side: const BorderSide(width: 1.5),
    ),
  );

  // FloatingActionButton theme
  static const FloatingActionButtonThemeData _fabTheme =
      FloatingActionButtonThemeData(
    elevation: 4,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(16)),
    ),
  );

  // Input decoration theme
  static final InputDecorationTheme _inputDecorationTheme = InputDecorationTheme(
    filled: true,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide.none,
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide.none,
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(width: 2),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: Color(0xFFD32F2F), width: 1.5),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: Color(0xFFD32F2F), width: 2),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
  );

  // Divider theme
  static const DividerThemeData _dividerTheme = DividerThemeData(
    thickness: 1,
    space: 1,
  );

  // Chip theme
  static final ChipThemeData _chipTheme = ChipThemeData(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    labelStyle: const TextStyle(fontSize: 14),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(8),
    ),
  );

  // SnackBar theme
  static const SnackBarThemeData _snackBarTheme = SnackBarThemeData(
    behavior: SnackBarBehavior.floating,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(8)),
    ),
  );

  // Dialog theme
  static final DialogThemeData _dialogTheme = DialogThemeData(
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(16),
    ),
  );

  // Bottom navigation bar theme
  static const BottomNavigationBarThemeData _bottomNavTheme =
      BottomNavigationBarThemeData(
    type: BottomNavigationBarType.fixed,
    elevation: 8,
    selectedItemColor: Color(0xFF1976D2),
    unselectedItemColor: Color(0xFF757575),
    showUnselectedLabels: true,
  );

  // Text theme
  static const TextTheme _textTheme = TextTheme(
    displayLarge: TextStyle(
      fontSize: 57,
      fontWeight: FontWeight.w400,
      letterSpacing: -0.25,
    ),
    displayMedium: TextStyle(
      fontSize: 45,
      fontWeight: FontWeight.w400,
    ),
    displaySmall: TextStyle(
      fontSize: 36,
      fontWeight: FontWeight.w400,
    ),
    headlineLarge: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w400,
    ),
    headlineMedium: TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.w400,
    ),
    headlineSmall: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w400,
    ),
    titleLarge: TextStyle(
      fontSize: 22,
      fontWeight: FontWeight.w500,
      letterSpacing: 0,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.15,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.1,
    ),
    bodyLarge: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      letterSpacing: 0.5,
    ),
    bodyMedium: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      letterSpacing: 0.25,
    ),
    bodySmall: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w400,
      letterSpacing: 0.4,
    ),
    labelLarge: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.1,
    ),
    labelMedium: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.5,
    ),
    labelSmall: TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.5,
    ),
  );
}

/// Custom colors not in Material Design color scheme
class AppColors {
  AppColors._();

  // Basic colors
  static const Color primary = Color(0xFF1976D2); // Blue 700
  static const Color success = Color(0xFF43A047); // Green 600
  static const Color warning = Color(0xFFF57C00); // Orange 700
  static const Color error = Color(0xFFD32F2F); // Red 700

  // Text colors
  static const Color textPrimary = Color(0xFF212121); // Grey 900
  static const Color textSecondary = Color(0xFF757575); // Grey 600

  // Voice recording colors
  static const Color voiceRecording = Color(0xFFE3F2FD); // Light blue
  static const Color voiceActive = Color(0xFF1976D2); // Blue 700
  static const Color voiceError = Color(0xFFD32F2F); // Red 700

  // Image picker colors
  static const Color imageBackground = Color(0xFFE8F5E9); // Light green
  static const Color imageActive = Color(0xFF43A047); // Green 600

  // Text input colors
  static const Color textBackground = Color(0xFFFFF3E0); // Light orange
  static const Color textActive = Color(0xFFF57C00); // Orange 700

  // Sync status colors
  static const Color syncPending = Color(0xFFFFF176); // Yellow 300
  static const Color syncInProgress = Color(0xFF64B5F6); // Blue 300
  static const Color syncCompleted = Color(0xFF81C784); // Green 300
  static const Color syncFailed = Color(0xFFEF5350); // Red 400

  // Category colors (for tag chips)
  static const List<Color> categoryColors = [
    Color(0xFFE3F2FD), // Blue
    Color(0xFFE8F5E9), // Green
    Color(0xFFFFF3E0), // Orange
    Color(0xFFF3E5F5), // Purple
    Color(0xFFFFF9C4), // Yellow
    Color(0xFFFFE0B2), // Deep Orange
    Color(0xFFE0F2F1), // Teal
    Color(0xFFFCE4EC), // Pink
  ];
}
