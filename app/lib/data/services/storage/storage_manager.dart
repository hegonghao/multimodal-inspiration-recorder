import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../database.dart';
import '../../repositories/inspiration_repository.dart';
import '../notification_service.dart';

/// Service for managing local storage limits and cleanup
/// Implements 1000-record limit with intelligent cleanup strategies
class StorageManager extends ChangeNotifier {
  final InspirationRepository _repository;
  final AppDatabase _database;
  final NotificationService _notificationService;

  static const int maxRecords = 1000;
  static const int cleanupThreshold = 950; // Start warning at 95%
  static const int cleanupBatchSize = 100; // Delete 100 oldest records

  bool _lastWarningShown = false;

  StorageManager({
    required InspirationRepository repository,
    required AppDatabase database,
    NotificationService? notificationService,
  })  : _repository = repository,
        _database = database,
        _notificationService = notificationService ?? NotificationService();

  // ==================== Storage Status ====================

  /// Get current storage usage statistics
  Future<StorageStatus> getStorageStatus() async {
    final totalRecords = await _repository.getRecordCount();
    final unsyncedCount = (await _repository.getUnsyncedRecords()).length;
    final syncedCount =
        (await _repository.getAllRecords(syncStatus: SyncStatus.synced.value))
            .length;

    final status = StorageStatus(
      totalRecords: totalRecords,
      maxRecords: maxRecords,
      unsyncedCount: unsyncedCount,
      syncedCount: syncedCount,
      usagePercentage: (totalRecords / maxRecords * 100).toInt(),
      needsCleanup: totalRecords >= cleanupThreshold,
      isNearLimit: totalRecords >= cleanupThreshold,
      isFull: totalRecords >= maxRecords,
    );

    // Show warning notification if storage is near limit (only once)
    if (status.isNearLimit && !_lastWarningShown) {
      await _notificationService.showStorageLimitWarning(
        currentCount: totalRecords,
        maxCount: maxRecords,
      );
      _lastWarningShown = true;
    }

    // Reset warning flag if storage drops below threshold
    if (!status.isNearLimit && _lastWarningShown) {
      _lastWarningShown = false;
    }

    return status;
  }

  /// Check if storage limit is reached
  Future<bool> isStorageFull() async {
    final count = await _repository.getRecordCount();
    return count >= maxRecords;
  }

  /// Check if storage needs cleanup
  Future<bool> needsCleanup() async {
    final count = await _repository.getRecordCount();
    return count >= cleanupThreshold;
  }

  // ==================== Cleanup Operations ====================

  /// Perform automatic cleanup of old synced records
  /// Deletes oldest synced records to free up space
  Future<CleanupResult> performAutoCleanup() async {
    final status = await getStorageStatus();

    if (!status.needsCleanup) {
      return CleanupResult(
        success: true,
        message: '存储空间充足，无需清理',
        deletedCount: 0,
        freedSpace: 0,
      );
    }

    try {
      // Get oldest synced records (already backed up to Notion)
      final oldestSynced = await _database.getOldestSyncedRecords(
        limit: cleanupBatchSize,
      );

      if (oldestSynced.isEmpty) {
        // No synced records to delete, need to delete unsynced
        return _cleanupUnsyncedRecords();
      }

      // Delete oldest synced records
      int deletedCount = 0;
      for (final record in oldestSynced) {
        final success = await _repository.deleteRecord(record.id);
        if (success) deletedCount++;
      }

      debugPrint('Auto-cleanup completed: $deletedCount records deleted');

      return CleanupResult(
        success: true,
        message: '已清理 $deletedCount 条旧记录',
        deletedCount: deletedCount,
        freedSpace: deletedCount,
      );
    } catch (e) {
      debugPrint('Auto-cleanup failed: $e');
      return CleanupResult(
        success: false,
        message: '清理失败: $e',
        deletedCount: 0,
        freedSpace: 0,
      );
    }
  }

  /// Cleanup unsynced records (last resort)
  /// Only used when storage is full and no synced records to delete
  Future<CleanupResult> _cleanupUnsyncedRecords() async {
    // Get oldest unsynced records (WARNING: data loss risk)
    final oldestUnsynced = await _database.getOldestUnsyncedRecords(
      limit: cleanupBatchSize ~/ 2, // Delete fewer unsynced records
    );

    if (oldestUnsynced.isEmpty) {
      return CleanupResult(
        success: false,
        message: '无可清理记录',
        deletedCount: 0,
        freedSpace: 0,
      );
    }

    // Delete oldest unsynced records
    int deletedCount = 0;
    for (final record in oldestUnsynced) {
      await _repository.deleteRecord(record.id);
      deletedCount++;
    }

    debugPrint(
      'Emergency cleanup: $deletedCount unsynced records deleted',
    );

    return CleanupResult(
      success: true,
      message: '紧急清理: 已删除 $deletedCount 条未同步记录',
      deletedCount: deletedCount,
      freedSpace: deletedCount,
      warning: '部分未同步记录已被删除',
    );
  }

  /// Manually cleanup records by criteria
  Future<CleanupResult> cleanupByCriteria({
    bool deleteSynced = true,
    bool deleteUnsynced = false,
    Duration? olderThan,
    int? maxCount,
  }) async {
    try {
      int deletedCount = 0;

      if (deleteSynced) {
        final syncedRecords = await _repository.getAllRecords(
          syncStatus: SyncStatus.synced.value,
          limit: maxCount,
        );

        for (final record in syncedRecords) {
          if (olderThan != null) {
            final age = DateTime.now().difference(record.createdAt);
            if (age < olderThan) continue;
          }

          final success = await _repository.deleteRecord(record.id);
          if (success) deletedCount++;
        }
      }

      if (deleteUnsynced) {
        final unsyncedRecords = await _repository.getUnsyncedRecords();

        for (final record in unsyncedRecords) {
          if (olderThan != null) {
            final age = DateTime.now().difference(record.createdAt);
            if (age < olderThan) continue;
          }

          if (maxCount != null && deletedCount >= maxCount) break;

          await _repository.deleteRecord(record.id);
          deletedCount++;
        }
      }

      return CleanupResult(
        success: true,
        message: '已清理 $deletedCount 条记录',
        deletedCount: deletedCount,
        freedSpace: deletedCount,
      );
    } catch (e) {
      return CleanupResult(
        success: false,
        message: '清理失败: $e',
        deletedCount: 0,
        freedSpace: 0,
      );
    }
  }

  /// Delete all records (nuclear option)
  Future<CleanupResult> deleteAllRecords({
    bool includeSynced = true,
    bool includeUnsynced = false,
  }) async {
    try {
      final allRecords = await _repository.getAllRecords();
      int deletedCount = 0;

      for (final record in allRecords) {
        final isSynced = record.syncStatus == SyncStatus.synced.value;

        if (isSynced && includeSynced) {
          await _repository.deleteRecord(record.id);
          deletedCount++;
        } else if (!isSynced && includeUnsynced) {
          await _repository.deleteRecord(record.id);
          deletedCount++;
        }
      }

      return CleanupResult(
        success: true,
        message: '已删除 $deletedCount 条记录',
        deletedCount: deletedCount,
        freedSpace: deletedCount,
      );
    } catch (e) {
      return CleanupResult(
        success: false,
        message: '删除失败: $e',
        deletedCount: 0,
        freedSpace: 0,
      );
    }
  }

  // ==================== Storage Checks ====================

  /// Check if can create new record
  Future<bool> canCreateRecord() async {
    final count = await _repository.getRecordCount();
    return count < maxRecords;
  }

  /// Get remaining storage capacity
  Future<int> getRemainingCapacity() async {
    final count = await _repository.getRecordCount();
    return maxRecords - count;
  }
}

/// Storage status data class
class StorageStatus {
  final int totalRecords;
  final int maxRecords;
  final int unsyncedCount;
  final int syncedCount;
  final int usagePercentage;
  final bool needsCleanup;
  final bool isNearLimit;
  final bool isFull;

  const StorageStatus({
    required this.totalRecords,
    required this.maxRecords,
    required this.unsyncedCount,
    required this.syncedCount,
    required this.usagePercentage,
    required this.needsCleanup,
    required this.isNearLimit,
    required this.isFull,
  });

  int get remainingCapacity => maxRecords - totalRecords;

  String get usageMessage {
    if (isFull) return '存储已满';
    if (isNearLimit) return '存储接近上限';
    return '存储正常';
  }

  Color get statusColor {
    if (isFull) return const Color(0xFFD32F2F); // Red
    if (isNearLimit) return const Color(0xFFFF9800); // Orange
    return const Color(0xFF4CAF50); // Green
  }

  @override
  String toString() {
    return 'StorageStatus($totalRecords/$maxRecords, '
        '${usagePercentage}% used, '
        'synced: $syncedCount, unsynced: $unsyncedCount)';
  }
}

/// Cleanup result data class
class CleanupResult {
  final bool success;
  final String message;
  final int deletedCount;
  final int freedSpace;
  final String? warning;

  const CleanupResult({
    required this.success,
    required this.message,
    required this.deletedCount,
    required this.freedSpace,
    this.warning,
  });

  @override
  String toString() {
    return 'CleanupResult(success: $success, deleted: $deletedCount, '
        'message: $message${warning != null ? ', warning: $warning' : ''})';
  }
}
