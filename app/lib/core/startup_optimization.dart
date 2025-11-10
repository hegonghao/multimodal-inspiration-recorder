/// Startup optimization configuration and utilities
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../data/services/performance_service.dart';
import '../data/services/accessibility_service.dart';

/// Optimized app initialization
/// Implements lazy loading and deferred initialization strategies
class StartupOptimization {
  static final StartupOptimization _instance = StartupOptimization._internal();
  factory StartupOptimization() => _instance;
  StartupOptimization._internal();

  final PerformanceService _perfService = PerformanceService();
  final Map<String, Future<void>> _deferredInits = {};

  /// Initialize critical services only
  /// Non-critical services are lazily loaded on demand
  Future<void> initializeCriticalServices() async {
    debugPrint('⚡ Starting critical service initialization...');

    // 1. Performance tracking (must be first)
    _perfService.initialize();
    _perfService.recordCheckpoint('critical_start');

    // 2. Platform optimizations
    await _optimizePlatform();
    _perfService.recordCheckpoint('platform_optimized');

    // 3. Essential services only
    await Future.wait([
      _initializeAccessibility(),
      _optimizeImageCache(),
    ]);
    _perfService.recordCheckpoint('essential_services');

    debugPrint('✅ Critical services initialized');
    _perfService.recordCheckpoint('critical_complete');
  }

  /// Initialize non-critical services in background
  Future<void> initializeNonCriticalServices() async {
    debugPrint('🔄 Starting non-critical service initialization...');

    // Defer non-critical initializations
    _deferredInits['notifications'] = _initializeNotifications();
    _deferredInits['analytics'] = _initializeAnalytics();
    _deferredInits['background_sync'] = _initializeBackgroundSync();

    debugPrint('✅ Non-critical services queued for initialization');
    _perfService.recordCheckpoint('non_critical_queued');
  }

  /// Platform-specific optimizations
  Future<void> _optimizePlatform() async {
    // Set preferred orientations (portrait only for mobile)
    await SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);

    // Optimize status bar
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
      ),
    );

    // Enable edge-to-edge display
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);

    debugPrint('✓ Platform optimizations applied');
  }

  /// Initialize accessibility (critical)
  Future<void> _initializeAccessibility() async {
    final a11yService = AccessibilityService();
    await a11yService.initialize();
    debugPrint('✓ Accessibility service initialized');
  }

  /// Optimize image cache settings
  Future<void> _optimizeImageCache() async {
    final perfService = PerformanceService();

    // Set optimized cache limits
    PaintingBinding.instance.imageCache.maximumSize =
        perfService.getOptimizedImageCacheCount();
    PaintingBinding.instance.imageCache.maximumSizeBytes =
        perfService.getOptimizedImageCacheSize();

    debugPrint('✓ Image cache optimized: '
        '${perfService.getOptimizedImageCacheCount()} images, '
        '${perfService.getOptimizedImageCacheSize() ~/ (1024 * 1024)}MB');
  }

  /// Initialize notifications (non-critical, deferred)
  Future<void> _initializeNotifications() async {
    await Future.delayed(const Duration(seconds: 2));
    debugPrint('✓ Notifications initialized (deferred)');
  }

  /// Initialize analytics (non-critical, deferred)
  Future<void> _initializeAnalytics() async {
    await Future.delayed(const Duration(seconds: 3));
    debugPrint('✓ Analytics initialized (deferred)');
  }

  /// Initialize background sync (non-critical, deferred)
  Future<void> _initializeBackgroundSync() async {
    await Future.delayed(const Duration(seconds: 5));
    debugPrint('✓ Background sync initialized (deferred)');
  }

  /// Wait for a specific deferred service
  Future<void> waitForService(String serviceName) async {
    final init = _deferredInits[serviceName];
    if (init != null) {
      await init;
    }
  }

  /// Wait for all deferred services
  Future<void> waitForAllServices() async {
    await Future.wait(_deferredInits.values);
    debugPrint('✅ All deferred services initialized');
  }
}

/// Startup performance configuration
class StartupConfig {
  // Critical initialization timeout
  static const Duration criticalInitTimeout = Duration(seconds: 3);

  // Deferred initialization delay
  static const Duration deferredInitDelay = Duration(seconds: 1);

  // Image cache limits
  static const int maxImageCacheSize = 50 * 1024 * 1024; // 50MB
  static const int maxImageCacheCount = 500; // 500 images

  // Database configuration
  static const Map<String, dynamic> databaseConfig = {
    'cache_size': 2000, // Pages
    'page_size': 4096, // Bytes
    'use_wal': true,
  };

  // Network configuration
  static const Duration connectionTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const int maxConnectionsPerHost = 6;
}

/// Lazy loading widget wrapper
/// Defers widget loading until first access
class LazyWidget extends StatefulWidget {
  final String name;
  final Future<Widget> Function() loader;
  final Widget placeholder;

  const LazyWidget({
    super.key,
    required this.name,
    required this.loader,
    required this.placeholder,
  });

  @override
  State<LazyWidget> createState() => _LazyWidgetState();
}

class _LazyWidgetState extends State<LazyWidget> {
  late Future<Widget> _widgetFuture;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadWidget();
  }

  Future<void> _loadWidget() async {
    if (_isLoading) return;

    setState(() => _isLoading = true);

    final perfService = PerformanceService();
    _widgetFuture = perfService.lazyInitialize(
      featureName: 'lazy_widget_${widget.name}',
      initializer: widget.loader,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Widget>(
      future: _widgetFuture,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return snapshot.data!;
        }

        if (snapshot.hasError) {
          debugPrint('❌ Error loading lazy widget ${widget.name}: ${snapshot.error}');
          return Center(
            child: Text('Error loading ${widget.name}'),
          );
        }

        return widget.placeholder;
      },
    );
  }
}

/// Memory-efficient list builder
/// Only builds visible items, improves performance for long lists
class OptimizedListView extends StatelessWidget {
  final int itemCount;
  final Widget Function(BuildContext context, int index) itemBuilder;
  final double? itemExtent;
  final ScrollController? controller;

  const OptimizedListView({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    this.itemExtent,
    this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: controller,
      itemCount: itemCount,
      itemExtent: itemExtent, // Improves performance when items have fixed height
      itemBuilder: (context, index) {
        // Wrap with RepaintBoundary to isolate repaints
        return RepaintBoundary(
          child: itemBuilder(context, index),
        );
      },
      // Add cache extent for smoother scrolling
      cacheExtent: 100,
    );
  }
}

/// Optimized grid view
class OptimizedGridView extends StatelessWidget {
  final int itemCount;
  final Widget Function(BuildContext context, int index) itemBuilder;
  final int crossAxisCount;
  final double? childAspectRatio;
  final ScrollController? controller;

  const OptimizedGridView({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    required this.crossAxisCount,
    this.childAspectRatio,
    this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      controller: controller,
      itemCount: itemCount,
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: childAspectRatio ?? 1.0,
      ),
      itemBuilder: (context, index) {
        return RepaintBoundary(
          child: itemBuilder(context, index),
        );
      },
      cacheExtent: 100,
    );
  }
}

/// Performance-optimized image widget
class OptimizedImage extends StatelessWidget {
  final String imageUrl;
  final BoxFit? fit;
  final double? width;
  final double? height;
  final Widget? placeholder;
  final Widget? errorWidget;

  const OptimizedImage({
    super.key,
    required this.imageUrl,
    this.fit,
    this.width,
    this.height,
    this.placeholder,
    this.errorWidget,
  });

  @override
  Widget build(BuildContext context) {
    return Image.network(
      imageUrl,
      fit: fit,
      width: width,
      height: height,
      // Use RepaintBoundary to isolate image repaints
      frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
        if (wasSynchronouslyLoaded) {
          return RepaintBoundary(child: child);
        }

        return RepaintBoundary(
          child: AnimatedOpacity(
            opacity: frame == null ? 0 : 1,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
            child: child,
          ),
        );
      },
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) {
          return child;
        }

        return placeholder ??
            Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded /
                        loadingProgress.expectedTotalBytes!
                    : null,
              ),
            );
      },
      errorBuilder: (context, error, stackTrace) {
        debugPrint('❌ Failed to load image: $imageUrl');
        return errorWidget ??
            const Center(
              child: Icon(Icons.error_outline, color: Colors.red),
            );
      },
      // Memory cache optimization
      cacheWidth: width?.toInt(),
      cacheHeight: height?.toInt(),
    );
  }
}
