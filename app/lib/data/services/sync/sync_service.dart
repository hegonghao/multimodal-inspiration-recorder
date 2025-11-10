import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../database.dart';
import '../../repositories/inspiration_repository.dart';
import '../api_service.dart';
import '../notification_service.dart';
import 'connectivity_service.dart';

/// Service for managing synchronization between local database and Notion
/// Implements offline-first strategy with background sync
class SyncService extends ChangeNotifier {
  final InspirationRepository _repository;
  final ApiService _apiService;
  final ConnectivityService _connectivityService;
  final AppDatabase _database;
  final NotificationService _notificationService;

  Timer? _periodicSyncTimer;
  bool _isSyncing = false;
  DateTime? _lastSyncAt;
  SyncStatus _syncStatus = SyncStatus.pending;
  String? _lastSyncError;
  int _syncedCount = 0;
  int _failedCount = 0;

  SyncService({
    required InspirationRepository repository,
    required ApiService apiService,
    required ConnectivityService connectivityService,
    required AppDatabase database,
    NotificationService? notificationService,
  })  : _repository = repository,
        _apiService = apiService,
        _connectivityService = connectivityService,
        _database = database,
        _notificationService = notificationService ?? NotificationService() {
    _initSync();
  }

  // ==================== Getters ====================

  /// Whether sync is currently in progress
  bool get isSyncing => _isSyncing;

  /// Last successful sync timestamp
  DateTime? get lastSyncAt => _lastSyncAt;

  /// Current sync status
  SyncStatus get syncStatus => _syncStatus;

  /// Last sync error message
  String? get lastSyncError => _lastSyncError;

  /// Count of successfully synced records in last sync
  int get syncedCount => _syncedCount;

  /// Count of failed records in last sync
  int get failedCount => _failedCount;

  /// Whether sync is enabled (has network + not already syncing)
  bool get canSync => _connectivityService.isConnected && !_isSyncing;

  /// Human-readable sync status message
  String get syncStatusMessage {
    if (_isSyncing) return '同步中...';
    if (_lastSyncError != null) return '同步失败: $_lastSyncError';
    if (_lastSyncAt == null) return '未同步';

    final duration = DateTime.now().difference(_lastSyncAt!);
    if (duration.inMinutes < 1) return '刚刚同步';
    if (duration.inHours < 1) return '${duration.inMinutes}分钟前同步';
    if (duration.inDays < 1) return '${duration.inHours}小时前同步';
    return '${duration.inDays}天前同步';
  }

  // ==================== Initialization ====================

  /// Initialize sync service with periodic sync
  void _initSync() {
    // Listen to connectivity changes for auto-sync
    _connectivityService.addListener(_onConnectivityChanged);

    // Start periodic sync timer (every 15 minutes)
    _startPeriodicSync(interval: const Duration(minutes: 15));
  }

  /// Handle connectivity changes
  void _onConnectivityChanged() {
    if (_connectivityService.isConnected && !_isSyncing) {
      // Network became available, trigger sync
      debugPrint('Network available, triggering auto-sync');
      triggerSync();
    }
  }

  /// Start periodic sync timer
  void _startPeriodicSync({required Duration interval}) {
    _periodicSyncTimer?.cancel();
    _periodicSyncTimer = Timer.periodic(interval, (timer) {
      if (canSync) {
        debugPrint('Periodic sync triggered');
        triggerSync();
      }
    });
  }

  // ==================== Sync Operations ====================

  /// Manually trigger sync
  Future<SyncResult> triggerSync({bool force = false}) async {
    if (_isSyncing && !force) {
      return SyncResult(
        success: false,
        message: '同步已在进行中',
        syncedCount: 0,
        failedCount: 0,
      );
    }

    if (!_connectivityService.isConnected) {
      return SyncResult(
        success: false,
        message: '无网络连接',
        syncedCount: 0,
        failedCount: 0,
      );
    }

    _isSyncing = true;
    _syncStatus = SyncStatus.syncing;
    _lastSyncError = null;
    _syncedCount = 0;
    _failedCount = 0;
    notifyListeners();

    try {
      // Get pending sync tasks from local database
      final pendingTasks = await _repository.getPendingSyncTasks();

      if (pendingTasks.isEmpty) {
        _completeSyncSuccess(message: '没有待同步记录');
        return SyncResult(
          success: true,
          message: '没有待同步记录',
          syncedCount: 0,
          failedCount: 0,
        );
      }

      debugPrint('Starting sync: ${pendingTasks.length} tasks pending');

      // Show sync in progress notification
      await _notificationService.showSyncInProgress(
        pendingCount: pendingTasks.length,
      );

      // Process each sync task
      for (final task in pendingTasks) {
        try {
          await _processSyncTask(task);
          _syncedCount++;
        } catch (e) {
          debugPrint('Sync task failed: ${task.id} - $e');
          _failedCount++;
          _lastSyncError = e.toString();
        }
      }

      // Update sync status
      if (_failedCount == 0) {
        _completeSyncSuccess(
          message: '成功同步 $_syncedCount 条记录',
        );
        return SyncResult(
          success: true,
          message: '成功同步 $_syncedCount 条记录',
          syncedCount: _syncedCount,
          failedCount: 0,
        );
      } else {
        _completeSyncWithErrors(
          message: '同步完成: $_syncedCount 成功, $_failedCount 失败',
        );
        return SyncResult(
          success: false,
          message: '同步完成: $_syncedCount 成功, $_failedCount 失败',
          syncedCount: _syncedCount,
          failedCount: _failedCount,
        );
      }
    } catch (e) {
      debugPrint('Sync failed: $e');
      _completeSyncError(error: e.toString());
      return SyncResult(
        success: false,
        message: '同步失败: $e',
        syncedCount: _syncedCount,
        failedCount: _failedCount + 1,
      );
    }
  }

  /// Process a single sync task
  Future<void> _processSyncTask(SyncQueueData task) async {
    final record = await _repository.getRecordById(task.recordId);
    if (record == null) {
      // Record deleted locally, remove sync task
      await _database.deleteSyncTask(task.id);
      return;
    }

    final operation = SyncOperation.fromValue(task.operation);

    switch (operation) {
      case SyncOperation.create:
        await _syncCreate(record, task);
        break;
      case SyncOperation.update:
        await _syncUpdate(record, task);
        break;
      case SyncOperation.delete:
        await _syncDelete(record, task);
        break;
    }
  }

  /// Sync create operation
  Future<void> _syncCreate(
    InspirationRecord record,
    SyncQueueData task,
  ) async {
    // Call backend API to trigger Notion sync
    final response = await _apiService.triggerSync(recordIds: [record.id]);

    // Sync enqueued on backend, mark as syncing locally
    await _repository.updateSyncStatus(
      id: record.id,
      status: SyncStatus.syncing,
    );

    // Remove local sync task (backend will handle it)
    await _database.deleteSyncTask(task.id);

    // Poll sync status after a delay
    Future.delayed(const Duration(seconds: 5), () async {
      await _checkSyncStatus(record.id);
    });
  }

  /// Sync update operation
  Future<void> _syncUpdate(
    InspirationRecord record,
    SyncQueueData task,
  ) async {
    // Similar to create, but for updates
    await _syncCreate(record, task);
  }

  /// Sync delete operation
  Future<void> _syncDelete(
    InspirationRecord record,
    SyncQueueData task,
  ) async {
    // Similar to create, but for deletes
    await _syncCreate(record, task);
  }

  /// Check sync status from backend
  Future<void> _checkSyncStatus(int recordId) async {
    try {
      final response = await _apiService.getSyncQueue();
      final tasks = response['tasks'] as List?;

      if (tasks != null && tasks.isNotEmpty) {
        // Find task for this record
        final recordTask = tasks.where((t) => t['record_id'] == recordId).toList();
        if (recordTask.isNotEmpty) {
          final latestTask = recordTask.first;
          final status = latestTask['status'] as int;

          // Update local record based on backend status
          if (status == 2) {
            // Completed
            await _repository.updateSyncStatus(
              id: recordId,
              status: SyncStatus.synced,
              notionPageId: latestTask['notion_page_id'] as String?,
            );
          } else if (status == 3) {
            // Failed
            await _repository.updateSyncStatus(
              id: recordId,
              status: SyncStatus.failed,
            );
          }
        }
      }
    } catch (e) {
      debugPrint('Failed to check sync status: $e');
    }
  }

  /// Complete sync successfully
  void _completeSyncSuccess({required String message}) {
    _isSyncing = false;
    _syncStatus = SyncStatus.synced;
    _lastSyncAt = DateTime.now();
    _lastSyncError = null;
    debugPrint('Sync completed successfully: $message');

    // Show success notification (silent if no records synced)
    _notificationService.showSyncSuccess(
      syncedCount: _syncedCount,
      silent: _syncedCount == 0,
    );

    notifyListeners();
  }

  /// Complete sync with errors
  void _completeSyncWithErrors({required String message}) {
    _isSyncing = false;
    _syncStatus = SyncStatus.failed;
    _lastSyncAt = DateTime.now();
    debugPrint('Sync completed with errors: $message');

    // Show partial success notification
    _notificationService.showSyncPartialSuccess(
      syncedCount: _syncedCount,
      failedCount: _failedCount,
    );

    notifyListeners();
  }

  /// Complete sync with error
  void _completeSyncError({required String error}) {
    _isSyncing = false;
    _syncStatus = SyncStatus.failed;
    _lastSyncError = error;
    debugPrint('Sync error: $error');

    // Show error notification
    _notificationService.showSyncError(
      error: error,
      failedCount: _failedCount > 0 ? _failedCount : null,
    );

    notifyListeners();
  }

  // ==================== Status Queries ====================

  /// Get sync statistics from repository
  Future<SyncStatistics> getSyncStatistics() {
    return _repository.getSyncStatistics();
  }

  /// Get sync status from backend API
  Future<Map<String, dynamic>?> getBackendSyncStatus() async {
    try {
      return await _apiService.getSyncStatus();
    } catch (e) {
      debugPrint('Failed to get backend sync status: $e');
    }
    return null;
  }

  // ==================== Lifecycle ====================

  @override
  void dispose() {
    _periodicSyncTimer?.cancel();
    _connectivityService.removeListener(_onConnectivityChanged);
    super.dispose();
  }
}

/// Sync result data class
class SyncResult {
  final bool success;
  final String message;
  final int syncedCount;
  final int failedCount;

  const SyncResult({
    required this.success,
    required this.message,
    required this.syncedCount,
    required this.failedCount,
  });

  @override
  String toString() {
    return 'SyncResult(success: $success, message: $message, '
        'synced: $syncedCount, failed: $failedCount)';
  }
}
