import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:workmanager/workmanager.dart';

import '../../database.dart';
import '../../repositories/inspiration_repository.dart';
import '../api_service.dart';
import '../storage_service.dart';
import '../../../core/constants.dart';
import 'connectivity_service.dart';
import 'sync_service.dart';

/// Service for managing background synchronization
/// Uses WorkManager for Android and BackgroundFetch for iOS
class BackgroundSyncService {
  static const String syncTaskName = 'com.inspiration.recorder.sync';
  static const String uniqueSyncTask = 'periodicSync';

  static bool _isInitialized = false;

  /// Initialize background sync service
  /// Must be called during app initialization
  static Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // Initialize WorkManager for background tasks
      await Workmanager().initialize(
        callbackDispatcher,
        isInDebugMode: kDebugMode,
      );

      _isInitialized = true;
      debugPrint('Background sync service initialized');
    } catch (e) {
      debugPrint('Failed to initialize background sync: $e');
    }
  }

  /// Register periodic sync task
  /// Will run in background according to interval
  static Future<void> registerPeriodicSync({
    Duration interval = const Duration(minutes: 15),
    bool requiresNetwork = true,
    bool requiresCharging = false,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    try {
      // Cancel any existing periodic tasks
      await Workmanager().cancelByUniqueName(uniqueSyncTask);

      // Register new periodic task
      await Workmanager().registerPeriodicTask(
        uniqueSyncTask,
        syncTaskName,
        frequency: interval,
        constraints: Constraints(
          networkType: requiresNetwork ? NetworkType.connected : NetworkType.notRequired,
          requiresCharging: requiresCharging,
          requiresBatteryNotLow: true,
        ),
        existingWorkPolicy: ExistingPeriodicWorkPolicy.replace,
        initialDelay: const Duration(minutes: 1), // First sync after 1 minute
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(minutes: 5),
      );

      debugPrint('Periodic sync registered: interval=${interval.inMinutes}min');
    } catch (e) {
      debugPrint('Failed to register periodic sync: $e');
    }
  }

  /// Register one-time sync task
  /// Will run once in background
  static Future<void> triggerOneTimeSync({
    Duration? delay,
    bool requiresNetwork = true,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    try {
      await Workmanager().registerOneOffTask(
        'oneTimeSync_${DateTime.now().millisecondsSinceEpoch}',
        syncTaskName,
        initialDelay: delay ?? Duration.zero,
        constraints: Constraints(
          networkType: requiresNetwork ? NetworkType.connected : NetworkType.notRequired,
          requiresBatteryNotLow: true,
        ),
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(minutes: 5),
      );

      debugPrint('One-time sync triggered');
    } catch (e) {
      debugPrint('Failed to trigger one-time sync: $e');
    }
  }

  /// Cancel all background sync tasks
  static Future<void> cancelAll() async {
    try {
      await Workmanager().cancelAll();
      debugPrint('All background sync tasks cancelled');
    } catch (e) {
      debugPrint('Failed to cancel background tasks: $e');
    }
  }

  /// Cancel periodic sync task
  static Future<void> cancelPeriodicSync() async {
    try {
      await Workmanager().cancelByUniqueName(uniqueSyncTask);
      debugPrint('Periodic sync cancelled');
    } catch (e) {
      debugPrint('Failed to cancel periodic sync: $e');
    }
  }

  /// Update sync interval
  static Future<void> updateSyncInterval(Duration interval) async {
    await registerPeriodicSync(interval: interval);
  }

  /// Check if background sync is supported on this platform
  static bool get isSupported {
    // WorkManager is supported on Android and iOS
    return !kIsWeb;
  }
}

/// Background task callback dispatcher
/// This function runs in separate isolate
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    debugPrint('Background sync task started: $task');

    try {
      // Initialize database in background isolate
      final database = AppDatabase();
      final repository = InspirationRepository(database);

      // Check if we have pending sync tasks
      final pendingTasks = await repository.getPendingSyncTasks();

      if (pendingTasks.isEmpty) {
        debugPrint('No pending sync tasks');
        await database.close();
        return Future.value(true);
      }

      // Check network connectivity
      final connectivityService = ConnectivityService();
      await Future.delayed(const Duration(seconds: 1)); // Wait for connectivity check

      if (!connectivityService.isConnected) {
        debugPrint('No network connection, skipping sync');
        connectivityService.dispose();
        await database.close();
        return Future.value(false); // Retry later
      }

      // Initialize API service
      final preferences = await database.getPreferences();
      if (preferences == null) {
        debugPrint('No preferences found');
        connectivityService.dispose();
        await database.close();
        return Future.value(false);
      }

      // Background isolates must use the same endpoint configured in the app.
      // localhost points to the phone/emulator itself in production deployments.
      final storageService = await StorageService.getInstance();
      final apiService = ApiService(
        baseUrl: storageService.getString(
              StorageService.keyApiBaseUrl,
              defaultValue: ApiConstants.defaultBaseUrl,
            ) ??
            ApiConstants.defaultBaseUrl,
      );

      // Create sync service
      final syncService = SyncService(
        repository: repository,
        apiService: apiService,
        connectivityService: connectivityService,
        database: database,
      );

      // Perform sync
      final result = await syncService.triggerSync();

      debugPrint('Background sync result: ${result.message}');

      // Cleanup
      syncService.dispose();
      connectivityService.dispose();
      await database.close();

      return Future.value(result.success);
    } catch (e) {
      debugPrint('Background sync failed: $e');
      return Future.value(false); // Retry with backoff
    }
  });
}

/// Background sync manager for UI integration
/// Provides high-level API for managing background sync from UI
class BackgroundSyncManager extends ChangeNotifier {
  final AppDatabase _database;

  bool _isEnabled = true;
  Duration _syncInterval = const Duration(minutes: 15);
  bool _requiresWifi = false;
  DateTime? _lastBackgroundSync;

  BackgroundSyncManager({required AppDatabase database}) : _database = database {
    _loadPreferences();
  }

  // ==================== Getters ====================

  bool get isEnabled => _isEnabled;
  Duration get syncInterval => _syncInterval;
  bool get requiresWifi => _requiresWifi;
  DateTime? get lastBackgroundSync => _lastBackgroundSync;

  String get syncIntervalLabel {
    final minutes = _syncInterval.inMinutes;
    if (minutes < 60) return '$minutes 分钟';
    final hours = minutes ~/ 60;
    return '$hours 小时';
  }

  // ==================== Settings ====================

  Future<void> _loadPreferences() async {
    final prefs = await _database.getPreferences();
    if (prefs != null) {
      _syncInterval = Duration(seconds: prefs.syncInterval);
      // requiresWifi would be added to preferences if needed
      notifyListeners();
    }
  }

  /// Enable background sync
  Future<void> enable() async {
    _isEnabled = true;
    await BackgroundSyncService.registerPeriodicSync(
      interval: _syncInterval,
      requiresNetwork: true,
    );
    notifyListeners();
  }

  /// Disable background sync
  Future<void> disable() async {
    _isEnabled = false;
    await BackgroundSyncService.cancelPeriodicSync();
    notifyListeners();
  }

  /// Update sync interval
  Future<void> setSyncInterval(Duration interval) async {
    _syncInterval = interval;
    if (_isEnabled) {
      await BackgroundSyncService.updateSyncInterval(interval);
    }
    notifyListeners();
  }

  /// Set WiFi-only sync requirement
  Future<void> setRequiresWifi(bool value) async {
    _requiresWifi = value;
    if (_isEnabled) {
      await BackgroundSyncService.registerPeriodicSync(
        interval: _syncInterval,
        requiresNetwork: true,
      );
    }
    notifyListeners();
  }

  /// Trigger immediate background sync
  Future<void> triggerNow() async {
    await BackgroundSyncService.triggerOneTimeSync();
    _lastBackgroundSync = DateTime.now();
    notifyListeners();
  }

  /// Get background sync statistics
  Future<BackgroundSyncStats> getStats() async {
    final pendingTasks = await _database.getSyncQueueCount(status: 0);
    final failedTasks = await _database.getSyncQueueCount(status: 3);

    return BackgroundSyncStats(
      isEnabled: _isEnabled,
      syncInterval: _syncInterval,
      requiresWifi: _requiresWifi,
      lastSync: _lastBackgroundSync,
      pendingTasks: pendingTasks,
      failedTasks: failedTasks,
    );
  }
}

/// Background sync statistics
class BackgroundSyncStats {
  final bool isEnabled;
  final Duration syncInterval;
  final bool requiresWifi;
  final DateTime? lastSync;
  final int pendingTasks;
  final int failedTasks;

  const BackgroundSyncStats({
    required this.isEnabled,
    required this.syncInterval,
    required this.requiresWifi,
    required this.lastSync,
    required this.pendingTasks,
    required this.failedTasks,
  });

  bool get hasWork => pendingTasks > 0 || failedTasks > 0;

  String get statusMessage {
    if (!isEnabled) return '后台同步已禁用';
    if (pendingTasks > 0) return '$pendingTasks 个任务待同步';
    return '后台同步正常';
  }

  @override
  String toString() {
    return 'BackgroundSyncStats(enabled: $isEnabled, interval: ${syncInterval.inMinutes}min, '
        'pending: $pendingTasks, failed: $failedTasks)';
  }
}
