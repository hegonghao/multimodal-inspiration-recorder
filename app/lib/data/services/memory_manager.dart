import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Memory management service
/// Monitors and optimizes app memory usage
class MemoryManager {
  static final MemoryManager _instance = MemoryManager._internal();
  factory MemoryManager() => _instance;
  MemoryManager._internal();

  Timer? _monitorTimer;
  final List<MemorySnapshot> _snapshots = [];
  final Map<String, CachedValue> _cache = {};

  // Memory thresholds
  static const int warningThreshold = 100 * 1024 * 1024; // 100MB
  static const int criticalThreshold = 150 * 1024 * 1024; // 150MB

  // Cache limits
  static const int maxCacheSize = 50;
  static const Duration cacheExpiration = Duration(minutes: 30);

  /// Initialize memory manager
  void initialize() {
    debugPrint('💾 Memory manager initialized');

    // Start periodic monitoring in debug mode
    if (kDebugMode) {
      startMonitoring();
    }
  }

  // ==================== Memory Monitoring ====================

  /// Start memory monitoring
  void startMonitoring({Duration interval = const Duration(minutes: 1)}) {
    _monitorTimer?.cancel();

    _monitorTimer = Timer.periodic(interval, (_) {
      _checkMemoryStatus();
    });

    debugPrint('📊 Memory monitoring started (interval: $interval)');
  }

  /// Stop memory monitoring
  void stopMonitoring() {
    _monitorTimer?.cancel();
    debugPrint('⏸️ Memory monitoring stopped');
  }

  /// Check current memory status
  void _checkMemoryStatus() {
    // Take snapshot
    final snapshot = _takeSnapshot();
    _snapshots.add(snapshot);

    // Keep only last 100 snapshots
    if (_snapshots.length > 100) {
      _snapshots.removeAt(0);
    }

    // Check thresholds
    if (snapshot.estimatedUsage > criticalThreshold) {
      debugPrint('🚨 CRITICAL: Memory usage high (${_formatBytes(snapshot.estimatedUsage)})');
      performAggressiveCleanup();
    } else if (snapshot.estimatedUsage > warningThreshold) {
      debugPrint('⚠️ WARNING: Memory usage elevated (${_formatBytes(snapshot.estimatedUsage)})');
      performLightCleanup();
    }
  }

  /// Take memory snapshot
  MemorySnapshot _takeSnapshot() {
    final imageCache = PaintingBinding.instance.imageCache;

    // Estimate memory usage based on caches
    final imageCacheMemory = imageCache.currentSizeBytes;
    final appCacheMemory = _estimateCacheMemory();

    return MemorySnapshot(
      timestamp: DateTime.now(),
      imageCacheSize: imageCache.currentSize,
      imageCacheBytes: imageCacheMemory,
      appCacheSize: _cache.length,
      appCacheBytes: appCacheMemory,
      estimatedUsage: imageCacheMemory + appCacheMemory,
    );
  }

  /// Estimate app cache memory usage
  int _estimateCacheMemory() {
    // Rough estimation: 1KB per cache entry
    return _cache.length * 1024;
  }

  // ==================== Memory Cleanup ====================

  /// Perform light cleanup
  void performLightCleanup() {
    debugPrint('🧹 Performing light cleanup...');

    // Clear expired cache entries
    _cleanupExpiredCache();

    // Clear live images from image cache
    PaintingBinding.instance.imageCache.clearLiveImages();

    debugPrint('✓ Light cleanup complete');
  }

  /// Perform aggressive cleanup
  void performAggressiveCleanup() {
    debugPrint('🧹 Performing aggressive cleanup...');

    // Clear all caches
    clearAllCaches();

    // Clear image cache
    PaintingBinding.instance.imageCache.clear();

    // Force garbage collection (if available)
    _forceGarbageCollection();

    debugPrint('✓ Aggressive cleanup complete');
  }

  /// Force garbage collection (best effort)
  void _forceGarbageCollection() {
    // Note: Dart doesn't expose direct GC control
    // This is a placeholder for potential future implementation
    debugPrint('🗑️ Garbage collection requested');
  }

  // ==================== Cache Management ====================

  /// Store value in memory cache
  void cacheValue(String key, dynamic value, {Duration? ttl}) {
    _cache[key] = CachedValue(
      value: value,
      timestamp: DateTime.now(),
      ttl: ttl ?? cacheExpiration,
    );

    // Check cache size
    if (_cache.length > maxCacheSize) {
      _evictOldestEntry();
    }
  }

  /// Get value from memory cache
  T? getCachedValue<T>(String key) {
    final cached = _cache[key];

    if (cached == null) return null;

    // Check if expired
    if (_isCacheExpired(cached)) {
      _cache.remove(key);
      return null;
    }

    return cached.value as T?;
  }

  /// Check if cache entry is expired
  bool _isCacheExpired(CachedValue cached) {
    final age = DateTime.now().difference(cached.timestamp);
    return age > cached.ttl;
  }

  /// Remove value from cache
  void removeCachedValue(String key) {
    _cache.remove(key);
  }

  /// Clear all cache entries
  void clearAllCaches() {
    _cache.clear();
    debugPrint('🗑️ All caches cleared');
  }

  /// Clean up expired cache entries
  void _cleanupExpiredCache() {
    final keysToRemove = <String>[];

    _cache.forEach((key, value) {
      if (_isCacheExpired(value)) {
        keysToRemove.add(key);
      }
    });

    keysToRemove.forEach(_cache.remove);

    if (keysToRemove.isNotEmpty) {
      debugPrint('🗑️ Removed ${keysToRemove.length} expired cache entries');
    }
  }

  /// Evict oldest cache entry
  void _evictOldestEntry() {
    if (_cache.isEmpty) return;

    String? oldestKey;
    DateTime? oldestTime;

    _cache.forEach((key, value) {
      if (oldestTime == null || value.timestamp.isBefore(oldestTime!)) {
        oldestKey = key;
        oldestTime = value.timestamp;
      }
    });

    if (oldestKey != null) {
      _cache.remove(oldestKey);
      debugPrint('🗑️ Evicted oldest cache entry: $oldestKey');
    }
  }

  // ==================== Memory Statistics ====================

  /// Get current memory statistics
  MemoryStatistics getMemoryStatistics() {
    final imageCache = PaintingBinding.instance.imageCache;

    return MemoryStatistics(
      imageCacheSize: imageCache.currentSize,
      imageCacheBytes: imageCache.currentSizeBytes,
      imageCacheMaxSize: imageCache.maximumSize,
      imageCacheMaxBytes: imageCache.maximumSizeBytes,
      appCacheSize: _cache.length,
      appCacheBytes: _estimateCacheMemory(),
      snapshotCount: _snapshots.length,
    );
  }

  /// Get memory usage history
  List<MemorySnapshot> getMemoryHistory({int? limit}) {
    if (limit == null) return List.unmodifiable(_snapshots);

    final startIndex = _snapshots.length > limit ? _snapshots.length - limit : 0;
    return List.unmodifiable(_snapshots.sublist(startIndex));
  }

  /// Get peak memory usage
  int getPeakMemoryUsage() {
    if (_snapshots.isEmpty) return 0;

    return _snapshots.map((s) => s.estimatedUsage).reduce(
          (a, b) => a > b ? a : b,
        );
  }

  /// Get average memory usage
  int getAverageMemoryUsage() {
    if (_snapshots.isEmpty) return 0;

    final total = _snapshots.fold<int>(
      0,
      (sum, snapshot) => sum + snapshot.estimatedUsage,
    );

    return total ~/ _snapshots.length;
  }

  // ==================== Memory Report ====================

  /// Generate memory report
  Map<String, dynamic> generateMemoryReport() {
    final stats = getMemoryStatistics();
    final peak = getPeakMemoryUsage();
    final average = getAverageMemoryUsage();

    return {
      'current': {
        'image_cache_images': stats.imageCacheSize,
        'image_cache_bytes': stats.imageCacheBytes,
        'image_cache_usage': _formatBytes(stats.imageCacheBytes),
        'app_cache_entries': stats.appCacheSize,
        'app_cache_bytes': stats.appCacheBytes,
        'app_cache_usage': _formatBytes(stats.appCacheBytes),
      },
      'limits': {
        'image_cache_max_images': stats.imageCacheMaxSize,
        'image_cache_max_bytes': stats.imageCacheMaxBytes,
        'image_cache_max_usage': _formatBytes(stats.imageCacheMaxBytes),
      },
      'history': {
        'snapshots': stats.snapshotCount,
        'peak_usage': _formatBytes(peak),
        'average_usage': _formatBytes(average),
      },
    };
  }

  /// Print memory report
  void printMemoryReport() {
    final report = generateMemoryReport();

    debugPrint('\n' + '=' * 60);
    debugPrint('💾 MEMORY REPORT');
    debugPrint('=' * 60);

    debugPrint('\n📊 CURRENT USAGE:');
    debugPrint('  Image Cache: ${report['current']['image_cache_images']} images, '
        '${report['current']['image_cache_usage']}');
    debugPrint('  App Cache: ${report['current']['app_cache_entries']} entries, '
        '${report['current']['app_cache_usage']}');

    debugPrint('\n📈 LIMITS:');
    debugPrint('  Image Cache Max: ${report['limits']['image_cache_max_images']} images, '
        '${report['limits']['image_cache_max_usage']}');

    debugPrint('\n📉 HISTORY:');
    debugPrint('  Snapshots: ${report['history']['snapshots']}');
    debugPrint('  Peak Usage: ${report['history']['peak_usage']}');
    debugPrint('  Average Usage: ${report['history']['average_usage']}');

    debugPrint('\n' + '=' * 60 + '\n');
  }

  // ==================== Utilities ====================

  /// Format bytes to human-readable string
  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  /// Dispose and cleanup
  void dispose() {
    stopMonitoring();
    clearAllCaches();
    _snapshots.clear();
    debugPrint('🧹 Memory manager disposed');
  }
}

/// Memory snapshot
class MemorySnapshot {
  final DateTime timestamp;
  final int imageCacheSize;
  final int imageCacheBytes;
  final int appCacheSize;
  final int appCacheBytes;
  final int estimatedUsage;

  MemorySnapshot({
    required this.timestamp,
    required this.imageCacheSize,
    required this.imageCacheBytes,
    required this.appCacheSize,
    required this.appCacheBytes,
    required this.estimatedUsage,
  });

  @override
  String toString() {
    return 'MemorySnapshot(${timestamp.toIso8601String()}, '
        'images: $imageCacheSize, '
        'cache: $appCacheSize, '
        'total: ${(estimatedUsage / (1024 * 1024)).toStringAsFixed(1)} MB)';
  }
}

/// Memory statistics
class MemoryStatistics {
  final int imageCacheSize;
  final int imageCacheBytes;
  final int imageCacheMaxSize;
  final int imageCacheMaxBytes;
  final int appCacheSize;
  final int appCacheBytes;
  final int snapshotCount;

  MemoryStatistics({
    required this.imageCacheSize,
    required this.imageCacheBytes,
    required this.imageCacheMaxSize,
    required this.imageCacheMaxBytes,
    required this.appCacheSize,
    required this.appCacheBytes,
    required this.snapshotCount,
  });
}

/// Cached value with TTL
class CachedValue {
  final dynamic value;
  final DateTime timestamp;
  final Duration ttl;

  CachedValue({
    required this.value,
    required this.timestamp,
    required this.ttl,
  });
}
