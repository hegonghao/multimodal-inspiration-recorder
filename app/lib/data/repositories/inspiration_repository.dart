import 'package:drift/drift.dart';

import '../database.dart';

/// Repository for managing InspirationRecord data access
/// Implements offline-first pattern with local database as source of truth
class InspirationRepository {
  InspirationRepository(this._database);
  final AppDatabase _database;

  // ==================== Read Operations ====================

  /// Watch all records (reactive stream)
  Stream<List<InspirationRecord>> watchAllRecords() {
    return _database.watchAllRecords();
  }

  /// Get all records with optional filters
  Future<List<InspirationRecord>> getAllRecords({
    int? limit,
    int? offset,
    String? inputType,
    int? syncStatus,
  }) {
    return _database.getAllRecords(
      limit: limit,
      offset: offset,
      inputType: inputType,
      syncStatus: syncStatus,
    );
  }

  /// Get record by ID
  Future<InspirationRecord?> getRecordById(int id) {
    return _database.getRecordById(id);
  }

  /// Get total record count
  Future<int> getRecordCount() {
    return _database.getRecordCount();
  }

  /// Get records pending sync
  Future<List<InspirationRecord>> getUnsyncedRecords() {
    return _database.getAllRecords(
      syncStatus: SyncStatus.pending.value,
    );
  }

  /// Get records by input type
  Future<List<InspirationRecord>> getRecordsByType(InputType type) {
    return _database.getAllRecords(inputType: type.value);
  }

  // ==================== Write Operations ====================

  /// Create new record with auto-sync
  Future<int> createRecord({
    required String title,
    required String content,
    required InputType inputType,
    String source = '灵感记录器',
    String? audioFilePath,
    String? imageFilePath,
    double? ocrConfidence,
    bool autoSync = true,
  }) async {
    final recordId = await _database.insertRecord(
      InspirationRecordsCompanion.insert(
        title: title,
        content: content,
        inputType: inputType.value,
        source: Value(source),
        audioFilePath: Value(audioFilePath),
        imageFilePath: Value(imageFilePath),
        ocrConfidence: Value(ocrConfidence),
        syncStatus: Value(
            autoSync ? SyncStatus.pending.value : SyncStatus.synced.value),
        createdAt: Value(DateTime.now()),
        updatedAt: Value(DateTime.now()),
      ),
    );

    // Enqueue sync task if auto-sync enabled
    if (autoSync) {
      await _enqueueSyncTask(
        recordId: recordId,
        operation: SyncOperation.create,
        priority: SyncPriority.normal,
      );
    }

    return recordId;
  }

  /// Update existing record
  Future<bool> updateRecord({
    required int id,
    String? title,
    String? content,
    String? summary,
    int? version,
    int? aiProcessingStatus,
    String? aiErrorMessage,
    bool triggerSync = true,
  }) async {
    final existing = await getRecordById(id);
    if (existing == null) return false;

    final success = await _database.updateRecord(
      InspirationRecordsCompanion(
        id: Value(id),
        title: title != null ? Value(title) : const Value.absent(),
        content: content != null ? Value(content) : const Value.absent(),
        summary: summary != null ? Value(summary) : const Value.absent(),
        version: version != null ? Value(version) : const Value.absent(),
        aiProcessingStatus: aiProcessingStatus != null
            ? Value(aiProcessingStatus)
            : const Value.absent(),
        aiErrorMessage: aiErrorMessage != null
            ? Value(aiErrorMessage)
            : const Value.absent(),
        updatedAt: Value(DateTime.now()),
        syncStatus: triggerSync
            ? const Value(0)
            : const Value.absent(), // Mark as pending if sync needed
      ),
    );

    if (success && triggerSync) {
      await _enqueueSyncTask(
        recordId: id,
        operation: SyncOperation.update,
        priority: SyncPriority.normal,
      );
    }

    return success;
  }

  /// Delete record (soft delete in Notion, hard delete locally)
  Future<bool> deleteRecord(int id) async {
    // Enqueue delete sync task first
    await _enqueueSyncTask(
      recordId: id,
      operation: SyncOperation.delete,
      priority: SyncPriority.high,
    );

    // Delete from local database
    final count = await _database.deleteRecord(id);
    return count > 0;
  }

  /// Update AI processing status
  Future<bool> updateAIStatus({
    required int id,
    required AIProcessingStatus status,
    String? summary,
    String? errorMessage,
  }) {
    return updateRecord(
      id: id,
      aiProcessingStatus: status.value,
      summary: summary,
      aiErrorMessage: errorMessage,
      triggerSync: status ==
          AIProcessingStatus.completed, // Only sync when processing completes
    );
  }

  /// Update sync status
  Future<bool> updateSyncStatus({
    required int id,
    required SyncStatus status,
    String? notionPageId,
  }) async {
    final existing = await getRecordById(id);
    if (existing == null) return false;

    return _database.updateRecord(
      InspirationRecordsCompanion(
        id: Value(id),
        syncStatus: Value(status.value),
        notionPageId:
            notionPageId != null ? Value(notionPageId) : const Value.absent(),
        updatedAt: Value(DateTime.now()),
      ),
    );
  }

  /// Batch insert records (useful for sync/import)
  Future<void> batchInsertRecords(List<InspirationRecordsCompanion> records) {
    return _database.batchInsertRecords(records);
  }

  // ==================== Sync Queue Management ====================

  /// Enqueue sync task for background processing
  Future<void> _enqueueSyncTask({
    required int recordId,
    required SyncOperation operation,
    required SyncPriority priority,
  }) async {
    // Check if task already exists
    final existingTasks = await _database.getPendingSyncTasks();
    final alreadyEnqueued = existingTasks.any(
      (task) => task.recordId == recordId && task.operation == operation.value,
    );

    if (alreadyEnqueued) return;

    await _database.insertSyncTask(
      SyncQueueCompanion.insert(
        recordId: recordId,
        operation: operation.value,
        priority: Value(priority.value),
        createdAt: Value(DateTime.now()),
      ),
    );
  }

  /// Get pending sync tasks
  Future<List<SyncQueueData>> getPendingSyncTasks() {
    return _database.getPendingSyncTasks();
  }

  /// Get sync queue count by status
  Future<int> getSyncQueueCount({int? status}) {
    return _database.getSyncQueueCount(status: status);
  }

  // ==================== Statistics ====================

  /// Get sync statistics
  Future<SyncStatistics> getSyncStatistics() async {
    final totalRecords = await getRecordCount();
    final unsyncedRecords =
        await getAllRecords(syncStatus: SyncStatus.pending.value);
    final syncedRecords =
        await getAllRecords(syncStatus: SyncStatus.synced.value);
    final failedRecords =
        await getAllRecords(syncStatus: SyncStatus.failed.value);
    final pendingSyncTasks = await getSyncQueueCount(status: 0);

    return SyncStatistics(
      totalRecords: totalRecords,
      unsyncedCount: unsyncedRecords.length,
      syncedCount: syncedRecords.length,
      failedCount: failedRecords.length,
      pendingTasks: pendingSyncTasks,
    );
  }
}

/// Sync statistics data class
class SyncStatistics {
  const SyncStatistics({
    required this.totalRecords,
    required this.unsyncedCount,
    required this.syncedCount,
    required this.failedCount,
    required this.pendingTasks,
  });
  final int totalRecords;
  final int unsyncedCount;
  final int syncedCount;
  final int failedCount;
  final int pendingTasks;

  double get syncProgress {
    if (totalRecords == 0) return 1;
    return syncedCount / totalRecords;
  }

  bool get hasPendingSync => unsyncedCount > 0 || pendingTasks > 0;

  bool get hasFailedSync => failedCount > 0;

  @override
  String toString() {
    return 'SyncStats(total: $totalRecords, synced: $syncedCount, '
        'unsynced: $unsyncedCount, failed: $failedCount, '
        'pendingTasks: $pendingTasks)';
  }
}
