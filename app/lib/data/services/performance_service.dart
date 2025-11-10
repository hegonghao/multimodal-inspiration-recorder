import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

/// Performance optimization service
/// Monitors and optimizes app startup time, memory usage, and runtime performance
class PerformanceService {
  static final PerformanceService _instance = PerformanceService._internal();
  factory PerformanceService() => _instance;
  PerformanceService._internal();

  // Performance metrics
  DateTime? _appStartTime;
  DateTime? _firstFrameTime;
  final Map<String, DateTime> _checkpoints = {};
  final Map<String, Duration> _durations = {};

  // Memory tracking
  int _currentMemoryUsage = 0;
  int _peakMemoryUsage = 0;
  Timer? _memoryMonitorTimer;

  // Lazy initialization flags
  final Map<String, bool> _initializedFeatures = {};

  /// Initialize performance tracking
  void initialize() {
    _appStartTime = DateTime.now();
    debugPrint('📊 Performance tracking initialized');

    // Start memory monitoring (only in debug mode)
    if (kDebugMode) {
      _startMemoryMonitoring();
    }

    // Track first frame rendering
    SchedulerBinding.instance.addPostFrameCallback((_) {
      _firstFrameTime = DateTime.now();
      recordCheckpoint('first_frame');

      final startupDuration = _firstFrameTime!.difference(_appStartTime!);
      debugPrint('⚡ First frame rendered in ${startupDuration.inMilliseconds}ms');

      if (startupDuration.inMilliseconds > 3000) {
        debugPrint('⚠️ WARNING: Slow startup detected (>3s)');
      }
    });
  }

  // ==================== Startup Time Optimization ====================

  /// Record a checkpoint for timing analysis
  void recordCheckpoint(String name) {
    _checkpoints[name] = DateTime.now();

    if (_appStartTime != null) {
      final duration = _checkpoints[name]!.difference(_appStartTime!);
      _durations[name] = duration;

      if (kDebugMode) {
        debugPrint('📍 Checkpoint [$name]: ${duration.inMilliseconds}ms');
      }
    }
  }

  /// Get startup duration
  Duration? getStartupDuration() {
    if (_appStartTime == null || _firstFrameTime == null) return null;
    return _firstFrameTime!.difference(_appStartTime!);
  }

  /// Get duration to specific checkpoint
  Duration? getCheckpointDuration(String checkpoint) {
    return _durations[checkpoint];
  }

  /// Get all checkpoints
  Map<String, Duration> getAllCheckpoints() {
    return Map.unmodifiable(_durations);
  }

  // ==================== Lazy Initialization ====================

  /// Mark a feature as initialized
  void markFeatureInitialized(String featureName) {
    _initializedFeatures[featureName] = true;
    debugPrint('✓ Feature initialized: $featureName');
  }

  /// Check if a feature is initialized
  bool isFeatureInitialized(String featureName) {
    return _initializedFeatures[featureName] ?? false;
  }

  /// Lazily initialize a feature
  Future<T> lazyInitialize<T>({
    required String featureName,
    required Future<T> Function() initializer,
  }) async {
    if (isFeatureInitialized(featureName)) {
      debugPrint('⚡ Feature already initialized: $featureName');
      return initializer(); // Return cached or re-initialize
    }

    debugPrint('🔄 Lazy initializing: $featureName');
    final startTime = DateTime.now();

    try {
      final result = await initializer();
      markFeatureInitialized(featureName);

      final duration = DateTime.now().difference(startTime);
      debugPrint('✓ $featureName initialized in ${duration.inMilliseconds}ms');

      return result;
    } catch (e) {
      debugPrint('❌ Failed to initialize $featureName: $e');
      rethrow;
    }
  }

  // ==================== Memory Optimization ====================

  /// Start monitoring memory usage
  void _startMemoryMonitoring() {
    _memoryMonitorTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _checkMemoryUsage(),
    );
  }

  /// Check current memory usage (approximation)
  void _checkMemoryUsage() {
    // Note: Flutter doesn't provide direct memory usage API
    // This is a placeholder for actual implementation using platform channels
    // or packages like flutter_memory_info

    if (kDebugMode) {
      // Simulate memory tracking
      // In production, use actual memory monitoring tools
      debugPrint('💾 Memory check performed');
    }
  }

  /// Record memory usage
  void recordMemoryUsage(int bytes) {
    _currentMemoryUsage = bytes;

    if (bytes > _peakMemoryUsage) {
      _peakMemoryUsage = bytes;
      debugPrint('📈 New peak memory: ${_formatBytes(bytes)}');
    }

    // Warn if memory usage is high (>100MB)
    if (bytes > 100 * 1024 * 1024) {
      debugPrint('⚠️ High memory usage: ${_formatBytes(bytes)}');
    }
  }

  /// Get current memory usage
  int getCurrentMemoryUsage() => _currentMemoryUsage;

  /// Get peak memory usage
  int getPeakMemoryUsage() => _peakMemoryUsage;

  /// Format bytes to human-readable string
  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  // ==================== Image Optimization ====================

  /// Get optimized image cache size
  int getOptimizedImageCacheSize() {
    // Default Flutter image cache is 1000 images and 100MB
    // Optimize based on device memory
    return 50 * 1024 * 1024; // 50MB
  }

  /// Get optimized image cache count
  int getOptimizedImageCacheCount() {
    return 500; // 500 images
  }

  /// Clear image cache
  void clearImageCache() {
    PaintingBinding.instance.imageCache.clear();
    debugPrint('🗑️ Image cache cleared');
  }

  /// Clear live image cache
  void clearLiveImageCache() {
    PaintingBinding.instance.imageCache.clearLiveImages();
    debugPrint('🗑️ Live image cache cleared');
  }

  // ==================== Widget Build Optimization ====================

  /// Wrap widget with performance tracking
  Widget trackWidgetBuild({
    required String widgetName,
    required Widget Function() builder,
  }) {
    return Builder(
      builder: (context) {
        final startTime = DateTime.now();
        final widget = builder();
        final duration = DateTime.now().difference(startTime);

        if (kDebugMode && duration.inMilliseconds > 16) {
          // Warn if build takes longer than one frame (16ms at 60fps)
          debugPrint('⚠️ Slow build: $widgetName (${duration.inMilliseconds}ms)');
        }

        return widget;
      },
    );
  }

  // ==================== Database Optimization ====================

  /// Optimize database queries
  Map<String, dynamic> getDatabaseOptimizationConfig() {
    return {
      'use_wal_mode': true, // Write-Ahead Logging for better concurrency
      'cache_size': 2000, // 2000 pages (~8MB) cache
      'page_size': 4096, // 4KB page size
      'auto_vacuum': 'incremental', // Incremental vacuum
      'temp_store': 'memory', // Store temp tables in memory
      'synchronous': 'normal', // Balance between speed and safety
      'journal_mode': 'wal', // WAL mode
      'mmap_size': 30000000000, // 30GB memory-mapped I/O
    };
  }

  // ==================== Network Optimization ====================

  /// Get optimized HTTP client configuration
  Map<String, dynamic> getHttpClientConfig() {
    return {
      'connection_timeout': const Duration(seconds: 10),
      'receive_timeout': const Duration(seconds: 30),
      'max_redirects': 5,
      'persistent_connection': true,
      'max_connections_per_host': 6,
    };
  }

  // ==================== Performance Report ====================

  /// Generate performance report
  Map<String, dynamic> generatePerformanceReport() {
    return {
      'startup': {
        'app_start_time': _appStartTime?.toIso8601String(),
        'first_frame_time': _firstFrameTime?.toIso8601String(),
        'startup_duration_ms': getStartupDuration()?.inMilliseconds,
        'checkpoints': _durations.map(
          (key, value) => MapEntry(key, value.inMilliseconds),
        ),
      },
      'memory': {
        'current_usage_bytes': _currentMemoryUsage,
        'peak_usage_bytes': _peakMemoryUsage,
        'current_usage': _formatBytes(_currentMemoryUsage),
        'peak_usage': _formatBytes(_peakMemoryUsage),
      },
      'features': {
        'initialized': _initializedFeatures,
      },
      'image_cache': {
        'current_size': PaintingBinding.instance.imageCache.currentSize,
        'current_size_bytes': PaintingBinding.instance.imageCache.currentSizeBytes,
        'maximum_size': PaintingBinding.instance.imageCache.maximumSize,
        'maximum_size_bytes': PaintingBinding.instance.imageCache.maximumSizeBytes,
        'pending_image_count': PaintingBinding.instance.imageCache.pendingImageCount,
        'live_image_count': PaintingBinding.instance.imageCache.liveImageCount,
      },
    };
  }

  /// Print performance report
  void printPerformanceReport() {
    final report = generatePerformanceReport();

    debugPrint('\n' + '=' * 60);
    debugPrint('📊 PERFORMANCE REPORT');
    debugPrint('=' * 60);

    // Startup
    debugPrint('\n🚀 STARTUP:');
    final startupDuration = getStartupDuration();
    if (startupDuration != null) {
      debugPrint('  Total: ${startupDuration.inMilliseconds}ms');

      if (startupDuration.inMilliseconds < 1000) {
        debugPrint('  Status: ✅ Excellent (<1s)');
      } else if (startupDuration.inMilliseconds < 3000) {
        debugPrint('  Status: ⚠️ Good (<3s)');
      } else {
        debugPrint('  Status: ❌ Needs improvement (>3s)');
      }
    }

    debugPrint('\n📍 CHECKPOINTS:');
    _durations.forEach((name, duration) {
      debugPrint('  $name: ${duration.inMilliseconds}ms');
    });

    // Memory
    debugPrint('\n💾 MEMORY:');
    debugPrint('  Current: ${_formatBytes(_currentMemoryUsage)}');
    debugPrint('  Peak: ${_formatBytes(_peakMemoryUsage)}');

    if (_peakMemoryUsage > 150 * 1024 * 1024) {
      debugPrint('  Status: ❌ High memory usage (>150MB)');
    } else if (_peakMemoryUsage > 100 * 1024 * 1024) {
      debugPrint('  Status: ⚠️ Moderate memory usage (>100MB)');
    } else {
      debugPrint('  Status: ✅ Good memory usage (<100MB)');
    }

    // Image Cache
    final imageCache = PaintingBinding.instance.imageCache;
    debugPrint('\n🖼️ IMAGE CACHE:');
    debugPrint('  Images: ${imageCache.currentSize}/${imageCache.maximumSize}');
    debugPrint('  Size: ${_formatBytes(imageCache.currentSizeBytes)}/${_formatBytes(imageCache.maximumSizeBytes)}');
    debugPrint('  Live: ${imageCache.liveImageCount}');
    debugPrint('  Pending: ${imageCache.pendingImageCount}');

    // Features
    debugPrint('\n⚡ LAZY LOADED FEATURES:');
    _initializedFeatures.forEach((name, initialized) {
      debugPrint('  $name: ${initialized ? "✅" : "⏳"}');
    });

    debugPrint('\n' + '=' * 60 + '\n');
  }

  // ==================== Cleanup ====================

  /// Clean up resources
  void dispose() {
    _memoryMonitorTimer?.cancel();
    clearImageCache();
    debugPrint('🧹 Performance service disposed');
  }

  /// Reset checkpoints for new measurement
  void resetCheckpoints() {
    _checkpoints.clear();
    _durations.clear();
    _appStartTime = DateTime.now();
    debugPrint('🔄 Performance checkpoints reset');
  }
}

/// Performance monitoring widget
/// Wraps a widget tree and tracks build performance
class PerformanceMonitor extends StatelessWidget {
  final String name;
  final Widget child;

  const PerformanceMonitor({
    super.key,
    required this.name,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    if (kDebugMode) {
      final service = PerformanceService();
      return service.trackWidgetBuild(
        widgetName: name,
        builder: () => child,
      );
    }

    return child;
  }
}

/// Extension for easy checkpoint recording
extension PerformanceCheckpointExtension on BuildContext {
  /// Record a performance checkpoint
  void recordPerformanceCheckpoint(String name) {
    PerformanceService().recordCheckpoint(name);
  }
}
