import 'dart:io';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:drift/drift.dart';

import '../../data/services/api_service.dart';
import '../../data/services/audio_service.dart';
import '../../data/services/camera_service.dart';
import '../../data/services/storage_service.dart';
import '../../data/database.dart';

/// State management for inspiration records
///
/// Manages the entire lifecycle of inspiration records:
/// - Creating records from voice, image, or text input
/// - Loading and caching records
/// - Syncing with backend
/// - Offline-first architecture
class InspirationProvider with ChangeNotifier {
  final ApiService _apiService;
  final AudioService _audioService;
  final CameraService _cameraService;
  final StorageService _storageService;
  final AppDatabase _database;
  final Logger _logger = Logger();

  // State
  List<InspirationRecord> _records = [];
  String? _activeInputType;
  bool _isLoading = false;
  bool _isCreating = false;
  String? _error;

  // Recording state
  bool _isRecording = false;
  Duration _recordingDuration = Duration.zero;
  double _audioAmplitude = 0.0;

  // Debouncing for notifyListeners
  Timer? _debounceTimer;
  bool _hasPendingNotification = false;

  // Getters
  List<InspirationRecord> get records => _records;
  bool get isLoading => _isLoading;
  bool get isCreating => _isCreating;
  String? get error => _error;
  bool get isRecording => _isRecording;
  Duration get recordingDuration => _recordingDuration;
  double get audioAmplitude => _audioAmplitude;

  InspirationProvider({
    required ApiService apiService,
    required AudioService audioService,
    required CameraService cameraService,
    required StorageService storageService,
    required AppDatabase database,
  })  : _apiService = apiService,
        _audioService = audioService,
        _cameraService = cameraService,
        _storageService = storageService,
        _database = database {
    _initialize();
  }

  /// Initialize provider and load records
  void _initialize() {
    _logger.i('Initializing InspirationProvider');

    // Subscribe to audio service streams with debouncing
    // Note: recordingStateStream removed to prevent race conditions
    // State is now managed synchronously in start/stop methods

    _audioService.durationStream.listen((duration) {
      _recordingDuration = duration;
      _notifyListenersDebounced();
    });

    _audioService.amplitudeStream.listen((amplitude) {
      _audioAmplitude = amplitude;
      _notifyListenersDebounced();
    });

    // Load initial records asynchronously (non-blocking)
    Future.microtask(() => loadRecords());
  }

  /// Debounced notifyListeners to prevent excessive UI rebuilds
  void _notifyListenersDebounced() {
    _hasPendingNotification = true;
    _debounceTimer?.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 100), () {
      if (_hasPendingNotification) {
        _hasPendingNotification = false;
        notifyListeners();
      }
    });
  }

  /// Load records from local database
  Future<void> loadRecords({
    int page = 1,
    int pageSize = 20,
    String? inputType,
    String? search,
    bool triggerSync = true,
  }) async {
    try {
      // Keep the list view's current filter when a background sync reloads
      // records after fetching the authoritative backend state.
      _activeInputType = inputType;
      _isLoading = true;
      _error = null;
      notifyListeners();

      _logger.i('Loading records: page=$page, pageSize=$pageSize');

      // Load from local database with pagination for better performance
      final offset = (page - 1) * pageSize;
      final localRecords = await _database.getAllRecords(
        limit: pageSize,
        offset: offset,
        inputType: inputType,
      );

      _records = localRecords;

      _isLoading = false;
      notifyListeners();

      // Try to fetch from API in background ONLY if explicitly requested
      // Use unawaited to avoid blocking (requires dart:async import)
      if (triggerSync) {
        Future.microtask(() => _syncWithBackend());
      }
    } catch (e) {
      _logger.e('Failed to load records: $e');
      _error = 'Failed to load records: $e';
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Create record from voice input
  Future<bool> createVoiceRecord({
    required File audioFile,
    String language = 'zh',
    bool autoProcess = true,
  }) async {
    try {
      _isCreating = true;
      _error = null;
      notifyListeners();

      _logger.i('Creating voice record: ${audioFile.path}');

      // Upload to API using uploadAudioRecord method
      final response = await _apiService.uploadAudioRecord(
        title: 'Voice Recording',
        content: '',
        audioFile: audioFile,
        language: language,
        autoProcess: autoProcess,
      );

      // Save to local database
      await _saveRecordToDatabase(response);

      _isCreating = false;
      notifyListeners();

      // Reload records
      await loadRecords();

      _logger.i('Voice record created successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to create voice record: $e');
      _error = 'Failed to create voice record: $e';
      _isCreating = false;
      notifyListeners();
      return false;
    }
  }

  /// Create record from image input
  Future<bool> createImageRecord({
    required File imageFile,
    String language = 'zh',
    bool autoProcess = true,
  }) async {
    try {
      _isCreating = true;
      _error = null;
      notifyListeners();

      _logger.i('Creating image record: ${imageFile.path}');

      // Preprocess image for OCR
      final processedImage =
          await _cameraService.preprocessImageForOCR(imageFile);

      // Upload to API using uploadImageRecord method
      final response = await _apiService.uploadImageRecord(
        title: 'Image Capture',
        content: '',
        imageFile: processedImage,
      );

      // Save to local database
      await _saveRecordToDatabase(response);

      _isCreating = false;
      notifyListeners();

      // Reload records
      await loadRecords();

      _logger.i('Image record created successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to create image record: $e');
      _error = 'Failed to create image record: $e';
      _isCreating = false;
      notifyListeners();
      return false;
    }
  }

  /// Create record from text input
  Future<bool> createTextRecord({
    required String content,
    String language = 'zh',
    bool autoProcess = true,
  }) async {
    try {
      _isCreating = true;
      _error = null;
      notifyListeners();

      _logger.i(
          'Creating text record: ${content.substring(0, content.length > 50 ? 50 : content.length)}...');

      // Use new API method that calls /upload endpoint with AI processing
      final response = await _apiService.createTextRecordWithAI(
        content: content,
        language: language,
        autoProcess: autoProcess,
      );

      // Save to local database
      await _saveRecordToDatabase(response);

      _isCreating = false;
      notifyListeners();

      // Reload records
      await loadRecords();

      _logger.i('Text record created successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to create text record: $e');
      _error = 'Failed to create text record: $e';
      _isCreating = false;
      notifyListeners();
      return false;
    }
  }

  /// Start audio recording
  Future<bool> startRecording() async {
    try {
      // Prevent duplicate calls
      if (_isRecording) {
        _logger
            .w('Recording already in progress, ignoring duplicate start call');
        return true;
      }

      _logger.i('Starting audio recording');

      // Optimistically update state before async call
      _isRecording = true;
      notifyListeners();

      final result = await _audioService.startRecording();

      if (!result.success) {
        // Rollback state on failure
        _isRecording = false;
        _error = result.error ?? 'Failed to start recording';
        notifyListeners();
        return false;
      }

      _logger.i('Audio recording started successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to start recording: $e');
      _isRecording = false;
      _error = 'Failed to start recording: $e';
      notifyListeners();
      return false;
    }
  }

  /// Stop audio recording and return file
  Future<File?> stopRecording() async {
    try {
      // Prevent duplicate calls
      if (!_isRecording) {
        _logger.w('No recording in progress, ignoring duplicate stop call');
        return null;
      }

      _logger.i('Stopping audio recording');

      // Update state immediately to prevent race conditions
      _isRecording = false;
      _recordingDuration = Duration.zero;
      notifyListeners();

      final result = await _audioService.stopRecording();

      if (!result.success || result.filePath == null) {
        _error = result.error ?? 'Failed to stop recording';
        notifyListeners();
        return null;
      }

      _logger.i('Audio recording stopped successfully');
      return File(result.filePath!);
    } catch (e) {
      _logger.e('Failed to stop recording: $e');
      _error = 'Failed to stop recording: $e';
      _isRecording = false;
      notifyListeners();
      return null;
    }
  }

  /// Pause audio recording
  Future<bool> pauseRecording() async {
    final success = await _audioService.pauseRecording();
    if (success) {
      notifyListeners();
    }
    return success;
  }

  /// Resume audio recording
  Future<bool> resumeRecording() async {
    final success = await _audioService.resumeRecording();
    if (success) {
      notifyListeners();
    }
    return success;
  }

  /// Cancel audio recording
  Future<void> cancelRecording() async {
    if (!_isRecording) {
      _logger.w('No recording in progress, ignoring cancel call');
      return;
    }

    _logger.i('Cancelling audio recording');

    // Update state immediately
    _isRecording = false;
    _recordingDuration = Duration.zero;
    notifyListeners();

    await _audioService.cancelRecording();
    _logger.i('Audio recording cancelled successfully');
  }

  /// Take photo with camera
  Future<File?> takePhoto() async {
    try {
      final result = await _cameraService.takePhoto();

      if (!result.success) {
        _error = result.error ?? 'Failed to take photo';
        notifyListeners();
        return null;
      }

      return result.file;
    } catch (e) {
      _logger.e('Failed to take photo: $e');
      _error = 'Failed to take photo: $e';
      notifyListeners();
      return null;
    }
  }

  /// Pick image from gallery
  Future<File?> pickImage() async {
    try {
      final result = await _cameraService.pickImage();

      if (!result.success) {
        if (result.cancelled) {
          _logger.i('User cancelled image selection');
          return null;
        }
        _error = result.error ?? 'Failed to pick image';
        notifyListeners();
        return null;
      }

      return result.file;
    } catch (e) {
      _logger.e('Failed to pick image: $e');
      _error = 'Failed to pick image: $e';
      notifyListeners();
      return null;
    }
  }

  /// Delete a record
  Future<bool> deleteRecord(int recordId) async {
    try {
      _logger.i('Deleting record: $recordId');

      // Delete from API
      await _apiService.deleteRecord(recordId);

      // Delete from local database
      await _database.deleteRecord(recordId);

      // Reload records
      await loadRecords();

      _logger.i('Record deleted successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to delete record: $e');
      _error = 'Failed to delete record: $e';
      notifyListeners();
      return false;
    }
  }

  /// Update a record
  Future<bool> updateRecord({
    required int recordId,
    String? title,
    String? content,
    String? categoryTags,
    String? summary,
  }) async {
    try {
      _logger.i('Updating record: $recordId');

      // Build update data
      final updateData = <String, dynamic>{};
      if (title != null) updateData['title'] = title;
      if (content != null) updateData['content'] = content;
      if (categoryTags != null) updateData['category_tags'] = categoryTags;
      if (summary != null) updateData['summary'] = summary;

      // Update via API
      final response = await _apiService.updateRecord(
        recordId,
        updateData,
      );

      // Update local database
      await _saveRecordToDatabase(response);

      // Reload records
      await loadRecords();

      _logger.i('Record updated successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to update record: $e');
      _error = 'Failed to update record: $e';
      notifyListeners();
      return false;
    }
  }

  /// Trigger manual sync with backend
  Future<void> syncWithBackend() async {
    await _syncWithBackend();
  }

  /// Sync all records from backend (full sync)
  /// This will fetch all records from backend and update local database
  Future<bool> syncAllFromBackend() async {
    try {
      _isLoading = true;
      _error = null;
      notifyListeners();

      _logger.i('Starting full sync from backend');

      // Fetch all records from backend with pagination
      int page = 1;
      int pageSize = 100; // Fetch 100 records per page
      List<Map<String, dynamic>> allBackendRecords = [];
      var fetchCompleted = false;

      while (true) {
        try {
          // Fetch page of records from backend
          final response = await _apiService.getRecords(
            page: page,
            pageSize: pageSize,
          );

          final data = response['data'] as List<dynamic>?;
          if (data == null || data.isEmpty) {
            fetchCompleted = true;
            break; // No more records
          }

          allBackendRecords.addAll(data.cast<Map<String, dynamic>>());

          final pagination = response['pagination'] as Map<String, dynamic>?;
          final hasNext = pagination?['has_next'] as bool? ?? false;

          if (!hasNext) {
            fetchCompleted = true;
            break; // Last page reached
          }

          page++;
        } catch (e) {
          _logger.e('Failed to fetch page $page: $e');
          break;
        }
      }

      _logger.i('Fetched ${allBackendRecords.length} records from backend');

      // Update local database with backend records
      int updatedCount = 0;
      int errorCount = 0;

      for (final apiRecord in allBackendRecords) {
        try {
          // Check if record exists locally
          final existingRecord =
              await _database.getRecordById(apiRecord['id'] as int);

          if (existingRecord != null) {
            // Update existing record
            await _database.updateRecord(
              InspirationRecordsCompanion(
                id: Value(apiRecord['id'] as int),
                title: Value(apiRecord['title'] as String),
                content: Value(apiRecord['content'] as String),
                inputType: Value(apiRecord['input_type'] as String),
                categoryTags:
                    Value(_serializeCategoryTags(apiRecord['category_tags'])),
                summary: Value(apiRecord['summary'] as String?),
                notionPageId: Value(apiRecord['notion_page_id'] as String?),
                syncStatus: Value(apiRecord['sync_status'] as int? ?? 0),
                version: Value(apiRecord['version'] as int? ?? 1),
                audioFilePath: Value(apiRecord['audio_file_path'] as String?),
                imageFilePath: Value(apiRecord['image_file_path'] as String?),
                ocrConfidence: Value(apiRecord['ocr_confidence'] as double?),
                aiProcessingStatus:
                    Value(apiRecord['ai_processing_status'] as int? ?? 0),
                aiErrorMessage: Value(apiRecord['ai_error_message'] as String?),
                createdAt:
                    Value(DateTime.parse(apiRecord['created_at'] as String)),
                updatedAt:
                    Value(DateTime.parse(apiRecord['updated_at'] as String)),
              ),
            );
          } else {
            // Insert new record
            await _saveRecordToDatabase(apiRecord);
          }

          updatedCount++;
        } catch (e) {
          _logger.e('Failed to sync record ${apiRecord['id']}: $e');
          errorCount++;
        }
      }

      // The backend is authoritative for records already linked to Notion.
      // Do this only after every page was fetched successfully, otherwise a
      // transient network error could make valid local records look deleted.
      if (fetchCompleted) {
        final serverRecordIds = allBackendRecords
            .map((record) => record['id'])
            .whereType<int>()
            .toSet();
        final removedCount = await _database.deleteRemoteRecordsMissingFrom(
          serverRecordIds,
        );
        if (removedCount > 0) {
          _logger.i('Removed $removedCount remotely deleted records locally');
        }
      } else {
        _logger.w(
            'Skipped remote deletion reconciliation because full fetch failed');
      }

      _logger.i(
          'Full sync completed: $updatedCount records synced, $errorCount errors');

      // Reload records from local database
      await loadRecords(
        inputType: _activeInputType,
        triggerSync: false,
      );

      _isLoading = false;
      notifyListeners();

      return true;
    } catch (e) {
      _logger.e('Full sync failed: $e');
      _error = 'Failed to sync from backend: $e';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Internal method to sync with backend
  Future<void> _syncWithBackend() async {
    try {
      _logger.i('Syncing with backend');

      // Get all local records
      final localRecords = await _database.getAllRecords();

      // Trigger sync via API
      await _apiService.triggerSync();

      // Fetch updated records from backend and update local database
      for (final localRecord in localRecords) {
        try {
          // Poll for AI processing completion if needed
          int maxAttempts = 15; // Max 15 attempts * 500ms = 7.5 seconds
          int attempt = 0;
          Map<String, dynamic>? response;

          while (attempt < maxAttempts) {
            // Fetch latest record from API
            response = await _apiService.getRecord(localRecord.id);

            final aiStatus = response['ai_processing_status'] as int? ?? 0;

            // AI processing states: 0=PENDING, 1=FAILED, 2=COMPLETED
            if (aiStatus == 2 || aiStatus == 1) {
              // AI processing completed or failed, stop polling
              _logger.i(
                  'AI processing finished for record ${localRecord.id}: status=$aiStatus');
              break;
            }

            // Still pending, wait and retry
            if (attempt < maxAttempts - 1) {
              await Future.delayed(const Duration(milliseconds: 500));
            }
            attempt++;
          }

          if (response == null) {
            _logger.w('Failed to fetch record ${localRecord.id} after polling');
            continue;
          }

          // Log warning if AI processing timed out
          if (attempt >= maxAttempts) {
            _logger.w(
                'AI processing timeout for record ${localRecord.id}, syncing current state');
          }

          // Update local database with latest sync status and other fields
          await _database.updateRecord(
            InspirationRecordsCompanion(
              id: Value(localRecord.id),
              title: Value(response['title'] as String? ?? localRecord.title),
              content:
                  Value(response['content'] as String? ?? localRecord.content),
              inputType: Value(
                  response['input_type'] as String? ?? localRecord.inputType),
              syncStatus: Value(
                  response['sync_status'] as int? ?? localRecord.syncStatus),
              notionPageId: response['notion_page_id'] != null
                  ? Value(response['notion_page_id'] as String)
                  : Value(localRecord.notionPageId),
              categoryTags: response['category_tags'] != null
                  ? Value(_serializeCategoryTags(response['category_tags']))
                  : Value(localRecord.categoryTags),
              summary: response['summary'] != null
                  ? Value(response['summary'] as String)
                  : Value(localRecord.summary),
              aiProcessingStatus: Value(
                  response['ai_processing_status'] as int? ??
                      localRecord.aiProcessingStatus),
              aiErrorMessage: response['ai_error_message'] != null
                  ? Value(response['ai_error_message'] as String)
                  : Value(localRecord.aiErrorMessage),
              updatedAt:
                  Value(DateTime.parse(response['updated_at'] as String)),
            ),
          );
        } catch (e) {
          _logger.w('Failed to sync record ${localRecord.id}: $e');
          // Continue with next record
        }
      }

      // Finish with an authoritative full-list reconciliation. This removes
      // locally cached records that were deleted in Notion and then removed
      // by the backend worker.
      await syncAllFromBackend();

      _logger.i('Backend sync completed');
    } catch (e) {
      _logger.w('Background sync failed: $e');
      // Don't show error to user for background sync
    }
  }

  /// Convert category_tags to JSON string for database storage
  String? _serializeCategoryTags(dynamic tags) {
    if (tags == null) return null;
    if (tags is String) return tags;
    if (tags is List) {
      return jsonEncode(tags);
    }
    return null;
  }

  /// Save API response to local database
  Future<void> _saveRecordToDatabase(Map<String, dynamic> apiResponse) async {
    try {
      final record = InspirationRecordsCompanion.insert(
        title: apiResponse['title'] as String,
        content: apiResponse['content'] as String,
        inputType: apiResponse['input_type'] as String,
        id: Value(apiResponse['id'] as int),
        categoryTags:
            Value(_serializeCategoryTags(apiResponse['category_tags'])),
        summary: Value(apiResponse['summary'] as String?),
        notionPageId: Value(apiResponse['notion_page_id'] as String?),
        syncStatus: Value(apiResponse['sync_status'] as int? ?? 0),
        version: Value(apiResponse['version'] as int? ?? 1),
        audioFilePath: Value(apiResponse['audio_file_path'] as String?),
        imageFilePath: Value(apiResponse['image_file_path'] as String?),
        ocrConfidence: Value(apiResponse['ocr_confidence'] as double?),
        aiProcessingStatus:
            Value(apiResponse['ai_processing_status'] as int? ?? 0),
        aiErrorMessage: Value(apiResponse['ai_error_message'] as String?),
        createdAt: Value(DateTime.parse(apiResponse['created_at'] as String)),
        updatedAt: Value(DateTime.parse(apiResponse['updated_at'] as String)),
      );

      await _database.insertRecord(record);
      _logger.i('Record saved to local database');
    } catch (e) {
      _logger.e('Failed to save record to database: $e');
      throw Exception('Failed to save record locally: $e');
    }
  }

  /// Clear error message
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Check if recording has exceeded max duration
  bool hasExceededMaxDuration() {
    return _audioService.hasExceededMaxDuration();
  }

  /// Get remaining recording time in seconds
  int getRemainingSeconds() {
    return _audioService.getRemainingSeconds();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _audioService.dispose();
    super.dispose();
  }
}
