import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

part 'database.g.dart';

// ==================== Table Definitions ====================

/// InspirationRecords table definition
/// Stores user inspirations with multimodal input support
class InspirationRecords extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get title => text().withLength(min: 1, max: 200)();
  TextColumn get content => text()();
  TextColumn get inputType => text().withLength(min: 1, max: 20)();
  TextColumn get categoryTags => text().nullable()();
  TextColumn get summary => text().nullable()();
  TextColumn get notionPageId => text().withLength(max: 100).nullable().unique()();
  IntColumn get syncStatus => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get audioFilePath => text().nullable()();
  TextColumn get imageFilePath => text().nullable()();
  RealColumn get ocrConfidence => real().nullable()();
  IntColumn get aiProcessingStatus => integer().withDefault(const Constant(0))();
  TextColumn get aiErrorMessage => text().nullable()();
}

/// SyncQueue table definition
/// Manages background synchronization tasks with retry logic
class SyncQueue extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get recordId => integer().references(InspirationRecords, #id, onDelete: KeyAction.cascade)();
  TextColumn get operation => text().withLength(max: 20)();
  IntColumn get status => integer().withDefault(const Constant(0))();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  IntColumn get maxRetries => integer().withDefault(const Constant(5))();
  DateTimeColumn get lastAttemptAt => dateTime().nullable()();
  DateTimeColumn get nextRetryAt => dateTime().nullable()();
  TextColumn get errorMessage => text().nullable()();
  IntColumn get priority => integer().withDefault(const Constant(0))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get completedAt => dateTime().nullable()();
}

/// UserPreferences table definition
/// Stores user configuration and integration credentials
class UserPreferences extends Table {
  IntColumn get id => integer().withDefault(const Constant(1))();
  TextColumn get notionToken => text().nullable()();
  TextColumn get notionDatabaseId => text().nullable()();
  // LLM API configuration - empty defaults, let backend use .env values
  // Users should NOT need to configure these on mobile app
  TextColumn get openaiBaseUrl => text().withDefault(const Constant(''))();
  TextColumn get openaiApiKey => text().nullable()();
  TextColumn get openaiModel => text().withDefault(const Constant(''))();

  // Speech-to-text API - empty default, let backend use .env values
  TextColumn get deepgramApiKey => text().withDefault(const Constant(''))();
  BoolColumn get encryptionEnabled => boolean().withDefault(const Constant(false))();
  IntColumn get syncInterval => integer().withDefault(const Constant(1800))();
  BoolColumn get syncOnNetwork => boolean().withDefault(const Constant(true))();
  TextColumn get uiLanguage => text().withDefault(const Constant('zh_CN'))();
  TextColumn get themeMode => text().withDefault(const Constant('system'))();
  IntColumn get maxVoiceDuration => integer().withDefault(const Constant(300))();
  BoolColumn get autoClassify => boolean().withDefault(const Constant(true))();
  BoolColumn get autoSummarize => boolean().withDefault(const Constant(true))();
  TextColumn get voiceInputLanguage => text().withDefault(const Constant('auto'))(); // 'auto', 'zh', 'en'
  BoolColumn get autoProcessVoice => boolean().withDefault(const Constant(true))(); // Auto AI processing for voice input
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {id};
}

// ==================== Database Class ====================

@DriftDatabase(tables: [InspirationRecords, SyncQueue, UserPreferences])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 5;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) async {
          await m.createAll();

          // Enable WAL mode for better concurrency
          await customStatement('PRAGMA journal_mode = WAL;');

          // Performance optimization
          await customStatement('PRAGMA synchronous = NORMAL;');
          await customStatement('PRAGMA temp_store = MEMORY;');
          await customStatement('PRAGMA mmap_size = 30000000000;');

          // Create indexes for optimal query performance
          await customStatement(
            'CREATE INDEX idx_inspiration_created_at ON inspiration_records(created_at DESC);',
          );
          await customStatement(
            'CREATE INDEX idx_inspiration_sync_status ON inspiration_records(sync_status);',
          );
          await customStatement(
            'CREATE INDEX idx_inspiration_input_type ON inspiration_records(input_type);',
          );
          await customStatement(
            'CREATE INDEX idx_inspiration_updated_at ON inspiration_records(updated_at DESC);',
          );
          await customStatement(
            'CREATE INDEX idx_inspiration_ai_status ON inspiration_records(ai_processing_status);',
          );

          // Sync queue indexes
          await customStatement(
            'CREATE INDEX idx_sync_queue_status ON sync_queue(status, priority DESC, created_at);',
          );
          await customStatement(
            'CREATE INDEX idx_sync_queue_record ON sync_queue(record_id);',
          );
          await customStatement(
            'CREATE INDEX idx_sync_queue_retry ON sync_queue(next_retry_at) WHERE status = 3;',
          );

          // Insert default user preferences
          await into(userPreferences).insert(
            UserPreferencesCompanion.insert(
              id: const Value(1),
            ),
          );
        },
        onUpgrade: (m, from, to) async {
          // Version 1 -> 2: Add deepgram_api_key field
          if (from < 2) {
            await m.addColumn(userPreferences, userPreferences.deepgramApiKey);
          }

          // Version 2 -> 3: Add voice input settings
          if (from < 3) {
            await m.addColumn(userPreferences, userPreferences.voiceInputLanguage);
            await m.addColumn(userPreferences, userPreferences.autoProcessVoice);
          }

          // Version 3 -> 4: Clear API configurations to use backend .env defaults
          if (from < 4) {
            await customStatement('''
              UPDATE user_preferences
              SET openai_base_url = '',
                  openai_model = '',
                  deepgram_api_key = ''
              WHERE id = 1
            ''');
          }

          // Version 4 -> 5: Clear hardcoded API configs to prevent overriding backend .env
          if (from < 5) {
            await customStatement('''
              UPDATE user_preferences
              SET openai_base_url = '',
                  openai_api_key = NULL,
                  openai_model = '',
                  deepgram_api_key = ''
              WHERE id = 1
            ''');
          }
        },
      );

  // ==================== Query Methods ====================

  // InspirationRecords queries
  Stream<List<InspirationRecord>> watchAllRecords() {
    return (select(inspirationRecords)
          ..orderBy([(t) => OrderingTerm.desc(t.createdAt)]))
        .watch();
  }

  Future<List<InspirationRecord>> getAllRecords({
    int? limit,
    int? offset,
    String? inputType,
    int? syncStatus,
  }) async {
    final query = select(inspirationRecords)..orderBy([(t) => OrderingTerm.desc(t.createdAt)]);

    if (inputType != null) {
      query.where((t) => t.inputType.equals(inputType));
    }

    if (syncStatus != null) {
      query.where((t) => t.syncStatus.equals(syncStatus));
    }

    if (limit != null) {
      query.limit(limit, offset: offset);
    }

    return query.get();
  }

  Future<InspirationRecord?> getRecordById(int id) async {
    return (select(inspirationRecords)..where((t) => t.id.equals(id))).getSingleOrNull();
  }

  Future<int> insertRecord(InspirationRecordsCompanion record) {
    return into(inspirationRecords).insert(record, mode: InsertMode.insertOrReplace);
  }

  Future<bool> updateRecord(InspirationRecordsCompanion record) {
    return update(inspirationRecords).replace(record);
  }

  Future<int> deleteRecord(int id) {
    return (delete(inspirationRecords)..where((t) => t.id.equals(id))).go();
  }

  Future<int> getRecordCount() async {
    final countQuery = selectOnly(inspirationRecords)..addColumns([inspirationRecords.id.count()]);
    final result = await countQuery.getSingle();
    return result.read(inspirationRecords.id.count()) ?? 0;
  }

  // Batch operations for better performance
  Future<void> batchInsertRecords(List<InspirationRecordsCompanion> records) async {
    await batch((batch) {
      batch.insertAll(inspirationRecords, records, mode: InsertMode.insertOrReplace);
    });
  }

  // Storage management queries
  Future<List<InspirationRecord>> getOldestSyncedRecords({required int limit}) async {
    return (select(inspirationRecords)
          ..where((t) => t.syncStatus.equals(SyncStatus.synced.value))
          ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
          ..limit(limit))
        .get();
  }

  Future<List<InspirationRecord>> getOldestUnsyncedRecords({required int limit}) async {
    return (select(inspirationRecords)
          ..where((t) => t.syncStatus.equals(SyncStatus.pending.value) | t.syncStatus.equals(SyncStatus.failed.value))
          ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
          ..limit(limit))
        .get();
  }

  // SyncQueue queries
  Stream<List<SyncQueueData>> watchSyncQueue() {
    return (select(syncQueue)..orderBy([(t) => OrderingTerm.asc(t.priority), (t) => OrderingTerm.asc(t.createdAt)])).watch();
  }

  Future<List<SyncQueueData>> getPendingSyncTasks() async {
    return (select(syncQueue)
          ..where((t) => t.status.equals(0) | t.status.equals(3))
          ..orderBy([(t) => OrderingTerm.desc(t.priority), (t) => OrderingTerm.asc(t.createdAt)]))
        .get();
  }

  Future<int> insertSyncTask(SyncQueueCompanion task) {
    return into(syncQueue).insert(task);
  }

  Future<bool> updateSyncTask(SyncQueueCompanion task) {
    return update(syncQueue).replace(task);
  }

  Future<int> deleteSyncTask(int id) {
    return (delete(syncQueue)..where((t) => t.id.equals(id))).go();
  }

  Future<int> getSyncQueueCount({int? status}) async {
    final countQuery = selectOnly(syncQueue)..addColumns([syncQueue.id.count()]);

    if (status != null) {
      countQuery.where(syncQueue.status.equals(status));
    }

    final result = await countQuery.getSingle();
    return result.read(syncQueue.id.count()) ?? 0;
  }

  // UserPreferences queries
  Stream<UserPreference> watchPreferences() {
    return (select(userPreferences)..where((t) => t.id.equals(1))).watchSingle();
  }

  Future<UserPreference?> getPreferences() async {
    return (select(userPreferences)..where((t) => t.id.equals(1))).getSingleOrNull();
  }

  Future<bool> updatePreferences(UserPreferencesCompanion preferences) {
    return update(userPreferences).replace(preferences);
  }
}

// ==================== Database Connection ====================

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'inspiration_recorder.db'));

    return NativeDatabase.createInBackground(
      file,
      setup: (db) {
        // Enable foreign key constraints
        db.execute('PRAGMA foreign_keys = ON;');
      },
    );
  });
}

// ==================== Enums ====================

/// Input type for inspiration records
enum InputType {
  voice('voice', '语音'),
  text('text', '文字'),
  image('image', '图片');

  const InputType(this.value, this.label);
  final String value;
  final String label;

  static InputType fromValue(String value) {
    return InputType.values.firstWhere((e) => e.value == value);
  }
}

/// Sync status for inspiration records
enum SyncStatus {
  pending(0, '待同步'),
  syncing(1, '同步中'),
  synced(2, '已同步'),
  failed(3, '失败'),
  conflict(4, '冲突');

  const SyncStatus(this.value, this.label);
  final int value;
  final String label;

  static SyncStatus fromValue(int value) {
    return SyncStatus.values.firstWhere((e) => e.value == value);
  }
}

/// AI processing status
/// IMPORTANT: Values must match backend schema
/// Backend: 0=PENDING, 1=FAILED, 2=COMPLETED
enum AIProcessingStatus {
  pending(0, '待处理'),
  failed(1, '失败'),
  completed(2, '已完成');

  const AIProcessingStatus(this.value, this.label);
  final int value;
  final String label;

  static AIProcessingStatus fromValue(int value) {
    return AIProcessingStatus.values.firstWhere((e) => e.value == value);
  }
}

/// Sync operation type
enum SyncOperation {
  create('create', '创建'),
  update('update', '更新'),
  delete('delete', '删除');

  const SyncOperation(this.value, this.label);
  final String value;
  final String label;

  static SyncOperation fromValue(String value) {
    return SyncOperation.values.firstWhere((e) => e.value == value);
  }
}

/// Sync task priority
enum SyncPriority {
  normal(0, '普通'),
  high(1, '高'),
  urgent(2, '紧急');

  const SyncPriority(this.value, this.label);
  final int value;
  final String label;

  static SyncPriority fromValue(int value) {
    return SyncPriority.values.firstWhere((e) => e.value == value);
  }
}
