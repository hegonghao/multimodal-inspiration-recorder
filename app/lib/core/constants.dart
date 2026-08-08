/// App-wide constants for the multimodal inspiration recorder
library;

/// App metadata
class AppConstants {
  AppConstants._();

  static const String appName = '灵感记录器';
  static const String appVersion = '1.0.0';
  static const String appDescription = '支持语音、图片、文字的多模输入灵感记录器';
}

/// API configuration
class ApiConstants {
  ApiConstants._();

  // Set the deployment endpoint at build time, for example:
  // flutter build apk --dart-define=API_BASE_URL=https://api.example.com
  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String apiVersion = 'v1';
  static const int connectionTimeout = 60000; // 60 seconds (for LLM processing)
  static const int receiveTimeout = 60000; // 60 seconds (for LLM processing)

  // Backend configuration (from .env)
  // These are used by backend, APP only needs to know defaultBaseUrl
  static const String backendOpenAIBaseUrl = 'https://cnapi.kksj.org/v1';
  static const String backendOpenAIModel = 'gpt-4o-mini';
  static const String backendEnvironment = 'development';
}

/// Local storage configuration
class StorageConstants {
  StorageConstants._();

  static const String databaseName = 'inspiration_recorder.db';
  static const int databaseVersion = 1;
  static const int maxRecords = 1000; // Maximum records per user
  static const int maxLocalStorageMB = 200; // Maximum 200MB local storage
}

/// Audio recording configuration
class AudioConstants {
  AudioConstants._();

  static const int maxDurationSeconds = 300; // 5 minutes
  static const int sampleRate = 44100; // 44.1kHz
  static const int bitRate = 96000; // 96kbps
  static const int channels = 1; // Mono
  static const String audioFormat = 'aac'; // AAC-LC encoding
  static const String audioExtension = '.aac';

  // Audio quality thresholds
  // NOTE: Backend uses language-specific thresholds for better multilingual support
  static const double minTranscriptionConfidence = 0.05; // 5% - reject threshold (very low to support all languages)

  // Language-specific warning thresholds (must match backend values)
  static const double warnTranscriptionConfidenceZh = 0.40; // 40% for Chinese
  static const double warnTranscriptionConfidenceEn = 0.25; // 25% for English (lower due to Deepgram scoring)
  static const double warnTranscriptionConfidenceDefault = 0.30; // 30% for other languages
}

/// Image configuration
class ImageConstants {
  ImageConstants._();

  static const int maxFileSizeBytes = 5 * 1024 * 1024; // 5MB
  static const double imageQuality = 0.8; // 80% quality for compression
  static const List<String> supportedFormats = ['jpg', 'jpeg', 'png', 'webp'];

  // OCR preprocessing
  static const int minImageWidth = 640;
  static const int minImageHeight = 480;
  static const int ocrContrastLevel = 175;

  // OCR quality thresholds
  static const double minOcrConfidence = 0.4; // 40%
  static const double warnOcrConfidence = 0.6; // 60%
}

/// Text input configuration
class TextConstants {
  TextConstants._();

  static const int minContentLength = 10; // Minimum 10 characters
  static const int maxContentLength = 10000; // Maximum 10,000 characters
  static const int summaryMaxLength = 200; // Summary max 200 characters
}

/// Sync configuration
class SyncConstants {
  SyncConstants._();

  static const int syncIntervalMinutes = 15; // Sync every 15 minutes
  static const int maxRetryAttempts = 3;
  static const int initialBackoffSeconds = 5;
  static const int maxBackoffSeconds = 300; // 5 minutes
  static const int syncBatchSize = 10; // Sync 10 records at a time
}

/// UI configuration
class UIConstants {
  UIConstants._();

  // Performance targets
  static const int maxUiResponseMilliseconds = 1000; // 1 second
  static const int quickActionMilliseconds = 500; // 500ms for simple actions
  static const int maxOcrProcessingSeconds = 5; // 5 seconds for OCR
  static const int maxTranscriptionSeconds = 5; // 5 seconds for transcription

  // Timeouts
  static const int autoSaveDelaySeconds = 3; // Auto-save 3 seconds after speech stops
  static const int toastDurationSeconds = 3;
  static const int snackbarDurationSeconds = 4;

  // Spacing
  static const double paddingSmall = 8;
  static const double paddingMedium = 16;
  static const double paddingLarge = 24;
  static const double paddingExtraLarge = 32;

  // Border radius
  static const double borderRadiusSmall = 4;
  static const double borderRadiusMedium = 8;
  static const double borderRadiusLarge = 16;
  static const double borderRadiusRound = 999;

  // Icon sizes
  static const double iconSizeSmall = 20;
  static const double iconSizeMedium = 24;
  static const double iconSizeLarge = 32;
  static const double iconSizeExtraLarge = 48;

  // Button sizes
  static const double buttonHeightSmall = 36;
  static const double buttonHeightMedium = 48;
  static const double buttonHeightLarge = 56;

  // Animation durations
  static const int animationDurationFast = 150; // 150ms
  static const int animationDurationNormal = 300; // 300ms
  static const int animationDurationSlow = 500; // 500ms
}

/// Error messages
class ErrorMessages {
  ErrorMessages._();

  // Audio errors
  static const String microphonePermissionDenied = '麦克风权限被拒绝，请在设置中启用';
  static const String audioRecordingFailed = '录音失败，请重试';
  static const String transcriptionFailed = '语音转写失败，请检查网络连接';
  static const String lowTranscriptionConfidence = '语音识别置信度较低(中英文混合可能影响准确率)，建议检查并手动编辑';

  // Image errors
  static const String cameraPermissionDenied = '相机权限被拒绝，请在设置中启用';
  static const String imagePickFailed = '图片选择失败，请重试';
  static const String imageProcessingFailed = '图片处理失败，请重试';
  static const String ocrFailed = 'OCR识别失败，请选择清晰的图片';
  static const String lowOcrConfidence = 'OCR识别置信度较低，建议手动编辑';
  static const String imageTooLarge = '图片文件过大，请选择小于5MB的图片';

  // Text errors
  static const String textTooShort = '内容过短，请输入至少10个字符';
  static const String textTooLong = '内容过长，请控制在10,000字符以内';

  // Network errors
  static const String networkError = '网络连接失败，数据已保存到本地';
  static const String apiError = 'API请求失败，请稍后重试';
  static const String timeoutError = '请求超时，请检查网络连接';

  // Sync errors
  static const String syncFailed = '同步失败，将稍后重试';
  static const String notionAuthFailed = 'Notion授权失败，请检查配置';
  static const String conflictDetected = '检测到数据冲突，已保留最新版本';

  // Storage errors
  static const String storageFull = '存储空间不足，请清理部分数据';
  static const String databaseError = '数据库操作失败，请重启应用';
  static const String maxRecordsReached = '已达到最大记录数量(1000条)，请清理旧数据';
}

/// Success messages
class SuccessMessages {
  SuccessMessages._();

  static const String recordSaved = '记录已保存';
  static const String recordSynced = '记录已同步';
  static const String recordDeleted = '记录已删除';
  static const String settingsSaved = '设置已保存';
  static const String syncCompleted = '同步完成';
}

/// Feature flags
class FeatureFlags {
  FeatureFlags._();

  static const bool enablePinProtection = false; // Deferred to post-MVP
  static const bool enableRealtimeTranscription = false; // Requires streaming API
  static const bool enableOfflineOcr = false; // Future enhancement
  static const bool enableBackgroundSync = true;
  static const bool enableNotifications = true;
  static const bool enableAnalytics = true;
}
