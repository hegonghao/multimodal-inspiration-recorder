import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

/// API Service for backend communication
///
/// Provides methods for interacting with the FastAPI backend,
/// including error handling, retries, and request/response logging.
class ApiService {

  ApiService({
    required String baseUrl,
    int connectTimeout = 30000,
    int receiveTimeout = 30000,
  }) : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: Duration(milliseconds: connectTimeout),
            receiveTimeout: Duration(milliseconds: receiveTimeout),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        ) {
    _setupInterceptors();
  }
  final Dio _dio;
  final Logger _logger = Logger();

  /// Update the base URL dynamically
  /// This allows changing the backend server without restarting the app
  void updateBaseUrl(String newBaseUrl) {
    _dio.options.baseUrl = newBaseUrl;
    _logger.i('API Service base URL updated to: $newBaseUrl');
  }

  /// Get current base URL
  String get baseUrl => _dio.options.baseUrl;

  void _setupInterceptors() {
    // Request interceptor
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          _logger.d('REQUEST[${options.method}] => ${options.uri}');
          _logger.d('Headers: ${options.headers}');
          if (options.data != null) {
            _logger.d('Body: ${options.data}');
          }
          return handler.next(options);
        },
        onResponse: (response, handler) {
          _logger.i(
            'RESPONSE[${response.statusCode}] => ${response.requestOptions.uri}',
          );
          return handler.next(response);
        },
        onError: (error, handler) {
          _logger.e(
            'ERROR[${error.response?.statusCode}] => ${error.requestOptions.uri}',
          );
          _logger.e('Error message: ${error.message}');
          if (error.response?.data != null) {
            _logger.e('Error response: ${error.response?.data}');
          }
          return handler.next(error);
        },
      ),
    );
  }

  // ==================== Inspiration Records API ====================

  /// Get list of inspiration records
  Future<Map<String, dynamic>> getRecords({
    int page = 1,
    int pageSize = 20,
    String? inputType,
    int? syncStatus,
    String? search,
    String sortBy = 'created_at',
    String sortOrder = 'desc',
  }) async {
    try {
      final response = await _dio.get(
        '/api/v1/records',
        queryParameters: {
          'page': page,
          'page_size': pageSize,
          if (inputType != null) 'input_type': inputType,
          if (syncStatus != null) 'sync_status': syncStatus,
          if (search != null) 'search': search,
          'sort_by': sortBy,
          'sort_order': sortOrder,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get single inspiration record by ID
  Future<Map<String, dynamic>> getRecord(int recordId) async {
    try {
      final response = await _dio.get('/api/v1/records/$recordId');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Create new inspiration record
  Future<Map<String, dynamic>> createRecord(
    Map<String, dynamic> recordData,
  ) async {
    try {
      final response = await _dio.post(
        '/api/v1/records',
        data: recordData,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Update existing inspiration record
  Future<Map<String, dynamic>> updateRecord(
    int recordId,
    Map<String, dynamic> updateData,
  ) async {
    try {
      final response = await _dio.put(
        '/api/v1/records/$recordId',
        data: updateData,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Delete inspiration record
  Future<void> deleteRecord(int recordId) async {
    try {
      await _dio.delete('/api/v1/records/$recordId');
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Upload audio file with record
  Future<Map<String, dynamic>> uploadAudioRecord({
    required String title,
    required String content,
    required File audioFile,
    String language = 'auto',  // Support 'auto', 'zh', 'en'
    bool autoProcess = true,
  }) async {
    try {
      final formData = FormData.fromMap({
        'title': title,
        'content': content,
        'input_type': 'voice',
        'language': language,
        'auto_process': autoProcess,
        'file': await MultipartFile.fromFile(
          audioFile.path,
          filename: audioFile.path.split('/').last,
        ),
      });

      final response = await _dio.post(
        '/api/v1/records/upload',
        data: formData,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Upload image or PDF file with record
  ///
  /// Automatically detects file type based on extension:
  /// - .pdf -> input_type: 'pdf'
  /// - .jpg, .jpeg, .png, .webp -> input_type: 'image'
  Future<Map<String, dynamic>> uploadImageRecord({
    required String title,
    required String content,
    required File imageFile,
    double? ocrConfidence,
  }) async {
    try {
      // Detect file type based on extension
      final filePath = imageFile.path.toLowerCase();
      final inputType = filePath.endsWith('.pdf') ? 'pdf' : 'image';

      final formData = FormData.fromMap({
        'title': title,
        'content': content,
        'input_type': inputType,
        'file': await MultipartFile.fromFile(
          imageFile.path,
          filename: imageFile.path.split('/').last,
        ),
        if (ocrConfidence != null) 'ocr_confidence': ocrConfidence,
      });

      final response = await _dio.post(
        '/api/v1/records/upload',
        data: formData,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Create text record with AI processing
  Future<Map<String, dynamic>> createTextRecordWithAI({
    required String content,
    String language = 'zh',
    bool autoProcess = true,
  }) async {
    try {
      final formData = FormData.fromMap({
        'input_type': 'text',
        'content': content,
        'language': language,
        'auto_process': autoProcess,
      });

      final response = await _dio.post(
        '/api/v1/records/upload',
        data: formData,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // ==================== AI Processing API ====================

  /// Classify content using LLM
  Future<Map<String, dynamic>> classifyContent(String content) async {
    try {
      final response = await _dio.post(
        '/api/v1/ai/classify',
        data: {'content': content},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Generate summary using LLM
  Future<Map<String, dynamic>> summarizeContent(
    String content, {
    int maxLength = 50,
  }) async {
    try {
      final response = await _dio.post(
        '/api/v1/ai/summarize',
        data: {
          'content': content,
          'max_length': maxLength,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Process content (classify + summarize)
  Future<Map<String, dynamic>> processContent(
    String content,
    String inputType, {
    int maxSummaryLength = 50,
  }) async {
    try {
      final response = await _dio.post(
        '/api/v1/ai/process',
        data: {
          'content': content,
          'input_type': inputType,
          'max_summary_length': maxSummaryLength,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // ==================== Sync API ====================

  /// Get sync status
  Future<Map<String, dynamic>> getSyncStatus() async {
    try {
      final response = await _dio.get('/api/v1/sync/status');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Trigger manual sync
  Future<Map<String, dynamic>> triggerSync({List<int>? recordIds}) async {
    try {
      final response = await _dio.post(
        '/api/v1/sync/trigger',
        data: recordIds != null ? {'record_ids': recordIds} : null,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get sync queue
  Future<Map<String, dynamic>> getSyncQueue({
    int? status,
    int limit = 50,
  }) async {
    try {
      final response = await _dio.get(
        '/api/v1/sync/queue',
        queryParameters: {
          if (status != null) 'status': status,
          'limit': limit,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Retry failed sync tasks
  Future<Map<String, dynamic>> retryFailedSync() async {
    try {
      final response = await _dio.post('/api/v1/sync/retry-failed');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // ==================== Preferences API ====================

  /// Get user preferences
  Future<Map<String, dynamic>> getPreferences() async {
    try {
      final response = await _dio.get('/api/v1/preferences');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Update user preferences
  Future<Map<String, dynamic>> updatePreferences(
    Map<String, dynamic> preferences,
  ) async {
    try {
      final response = await _dio.put(
        '/api/v1/preferences',
        data: preferences,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Test Notion connection
  Future<Map<String, dynamic>> testNotionConnection({
    required String notionToken,
    required String notionDatabaseId,
  }) async {
    try {
      final response = await _dio.post(
        '/api/v1/preferences/test-notion',
        data: {
          'notion_token': notionToken,
          'notion_database_id': notionDatabaseId,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Test LLM connection
  Future<Map<String, dynamic>> testLLMConnection({
    required String openaiBaseUrl,
    required String openaiModel, String? openaiApiKey,
  }) async {
    try {
      final response = await _dio.post(
        '/api/v1/preferences/test-llm',
        data: {
          'openai_base_url': openaiBaseUrl,
          if (openaiApiKey != null) 'openai_api_key': openaiApiKey,
          'openai_model': openaiModel,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // ==================== Health Check API ====================

  /// Basic health check
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await _dio.get('/api/v1/health');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Detailed health check
  Future<Map<String, dynamic>> detailedHealthCheck() async {
    try {
      final response = await _dio.get('/api/v1/health/detailed');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // ==================== Error Handling ====================

  Exception _handleError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(
          'Connection timeout. Please check your internet connection.',
          type: ApiExceptionType.timeout,
        );

      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final data = error.response?.data;

        if (statusCode != null) {
          // Extract error message (handle both String and nested Map)
          String errorMessage;
          if (data?['message'] is String) {
            errorMessage = data!['message'] as String;
          } else if (data?['message'] is Map) {
            // Nested error object (e.g., {error: "...", message: "..."})
            final nestedMessage = data!['message'] as Map<String, dynamic>;
            errorMessage = nestedMessage['message'] as String? ??
                          nestedMessage['error'] as String? ??
                          'Unknown error';
          } else {
            errorMessage = statusCode >= 500
                ? 'Server error occurred'
                : 'Request failed';
          }

          if (statusCode >= 500) {
            return ApiException(
              errorMessage,
              type: ApiExceptionType.server,
              statusCode: statusCode,
              data: data,
            );
          } else if (statusCode >= 400) {
            return ApiException(
              errorMessage,
              type: ApiExceptionType.client,
              statusCode: statusCode,
              data: data,
            );
          }
        }
        return ApiException(
          'Unexpected error occurred',
          type: ApiExceptionType.unknown,
        );

      case DioExceptionType.cancel:
        return ApiException(
          'Request was cancelled',
          type: ApiExceptionType.cancelled,
        );

      case DioExceptionType.unknown:
        if (error.error is SocketException) {
          return ApiException(
            'No internet connection',
            type: ApiExceptionType.network,
          );
        }
        return ApiException(
          error.message ?? 'Unknown error occurred',
          type: ApiExceptionType.unknown,
        );

      default:
        return ApiException(
          'Unexpected error occurred',
          type: ApiExceptionType.unknown,
        );
    }
  }
}

// ==================== Custom Exceptions ====================

enum ApiExceptionType {
  timeout,
  network,
  server,
  client,
  cancelled,
  unknown,
}

class ApiException implements Exception {

  ApiException(
    this.message, {
    required this.type,
    this.statusCode,
    this.data,
  });
  final String message;
  final ApiExceptionType type;
  final int? statusCode;
  final dynamic data;

  @override
  String toString() => 'ApiException: $message (type: $type, statusCode: $statusCode)';
}
