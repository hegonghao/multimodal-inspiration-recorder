/// Accessibility configuration and initialization for the app
library;

import 'package:flutter/material.dart';
import '../data/services/accessibility_service.dart';

/// Initialize accessibility features for the app
/// Call this in main.dart before runApp()
Future<void> initializeAccessibility() async {
  final a11yService = AccessibilityService();
  await a11yService.initialize();

  debugPrint('✓ Accessibility initialized');
}

/// Accessibility constants and guidelines
class AccessibilityConstants {
  // Touch target sizes (Material Design guidelines)
  static const double minTouchTargetSize = 48.0;
  static const double recommendedTouchTargetSize = 56.0;

  // Text contrast ratios (WCAG 2.1 AA)
  static const double minContrastRatioNormalText = 4.5;
  static const double minContrastRatioLargeText = 3.0;

  // Text sizes
  static const double minTextSize = 12.0;
  static const double normalTextSize = 14.0;
  static const double largeTextSize = 18.0;

  // Animation durations (consider reduced motion)
  static const Duration normalAnimationDuration = Duration(milliseconds: 300);
  static const Duration reducedAnimationDuration = Duration(milliseconds: 150);

  // Spacing for screen readers
  static const double minSpacingBetweenElements = 8.0;
  static const double recommendedSpacingBetweenElements = 16.0;
}

/// Widget wrapper to ensure minimum touch target size
class AccessibleTouchTarget extends StatelessWidget {
  final Widget child;
  final double minSize;

  const AccessibleTouchTarget({
    super.key,
    required this.child,
    this.minSize = AccessibilityConstants.minTouchTargetSize,
  });

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: BoxConstraints(
        minWidth: minSize,
        minHeight: minSize,
      ),
      child: child,
    );
  }
}

/// Builder that provides accessibility context
class AccessibilityBuilder extends StatelessWidget {
  final Widget Function(
    BuildContext context,
    bool isScreenReaderEnabled,
    bool isHighContrastEnabled,
    bool isBoldTextEnabled,
    bool isReduceMotionEnabled,
  ) builder;

  const AccessibilityBuilder({
    super.key,
    required this.builder,
  });

  @override
  Widget build(BuildContext context) {
    final a11yService = AccessibilityService();
    final features = a11yService.getPlatformAccessibilityFeatures();

    return builder(
      context,
      a11yService.isScreenReaderEnabled,
      features?.highContrast ?? false,
      features?.boldText ?? false,
      features?.disableAnimations ?? false,
    );
  }
}
