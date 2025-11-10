import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

/// Accessibility service for managing app-wide accessibility features
/// Provides screen reader support, semantic labels, and accessibility announcements
class AccessibilityService {
  static final AccessibilityService _instance = AccessibilityService._internal();
  factory AccessibilityService() => _instance;
  AccessibilityService._internal();

  // Track if screen reader is enabled
  bool _isScreenReaderEnabled = false;

  /// Check if screen reader is currently enabled
  bool get isScreenReaderEnabled => _isScreenReaderEnabled;

  // ==================== Initialization ====================

  /// Initialize accessibility service
  /// Call this in main.dart before runApp()
  Future<void> initialize() async {
    // Check initial screen reader status
    _isScreenReaderEnabled = await _checkScreenReaderStatus();
    debugPrint('Accessibility service initialized. Screen reader: $_isScreenReaderEnabled');
  }

  /// Check if screen reader is enabled on the device
  Future<bool> _checkScreenReaderStatus() async {
    try {
      // Access platform-specific screen reader status
      final SemanticsBinding? binding = SemanticsBinding.instance;
      return binding?.accessibilityFeatures.accessibleNavigation ?? false;
    } catch (e) {
      debugPrint('Error checking screen reader status: $e');
      return false;
    }
  }

  /// Update screen reader status
  void updateScreenReaderStatus(bool enabled) {
    _isScreenReaderEnabled = enabled;
    debugPrint('Screen reader status updated: $enabled');
  }

  // ==================== Accessibility Announcements ====================

  /// Announce a message to screen readers
  /// Used for important status updates, errors, or completion messages
  void announce(BuildContext context, String message, {bool polite = true}) {
    if (!_isScreenReaderEnabled) return;

    // Use SemanticsService to announce to screen readers
    SemanticsService.announce(
      message,
      polite ? TextDirection.ltr : TextDirection.ltr,
    );

    debugPrint('Accessibility announcement: $message');
  }

  /// Announce success message
  void announceSuccess(BuildContext context, String message) {
    announce(context, '成功: $message', polite: false);
  }

  /// Announce error message
  void announceError(BuildContext context, String message) {
    announce(context, '错误: $message', polite: false);
  }

  /// Announce loading state
  void announceLoading(BuildContext context, String message) {
    announce(context, '加载中: $message');
  }

  /// Announce completion
  void announceComplete(BuildContext context, String message) {
    announce(context, '完成: $message', polite: false);
  }

  // ==================== Focus Management ====================

  /// Move focus to next focusable element
  void focusNext(BuildContext context) {
    FocusScope.of(context).nextFocus();
  }

  /// Move focus to previous focusable element
  void focusPrevious(BuildContext context) {
    FocusScope.of(context).previousFocus();
  }

  /// Request focus for a specific node
  void requestFocus(BuildContext context, FocusNode node) {
    node.requestFocus();
  }

  /// Unfocus current element
  void unfocus(BuildContext context) {
    FocusScope.of(context).unfocus();
  }

  // ==================== Semantic Helpers ====================

  /// Get semantic label for recording status
  String getRecordingStatusLabel(bool isRecording, Duration? duration) {
    if (!isRecording) return '未录音';

    if (duration != null) {
      final minutes = duration.inMinutes;
      final seconds = duration.inSeconds % 60;
      return '录音中，已录制 $minutes 分 $seconds 秒';
    }

    return '录音中';
  }

  /// Get semantic label for sync status
  String getSyncStatusLabel(String status) {
    switch (status) {
      case 'syncing':
        return '正在同步到云端';
      case 'synced':
        return '已同步到云端';
      case 'failed':
        return '同步失败';
      case 'pending':
        return '等待同步';
      default:
        return status;
    }
  }

  /// Get semantic label for image picker
  String getImagePickerLabel(bool hasImage) {
    return hasImage ? '已选择图片，点击更换' : '点击选择图片';
  }

  /// Get semantic label for text editor
  String getTextEditorLabel(int characterCount, int minLength, int maxLength) {
    if (characterCount < minLength) {
      return '文本输入框，已输入 $characterCount 字符，还需 ${minLength - characterCount} 字符';
    }

    if (characterCount > maxLength) {
      return '文本输入框，已输入 $characterCount 字符，超出限制 ${characterCount - maxLength} 字符';
    }

    return '文本输入框，已输入 $characterCount 字符';
  }

  /// Get semantic label for progress
  String getProgressLabel(double progress, {String? context}) {
    final percentage = (progress * 100).toInt();
    final baseLabel = '进度 $percentage%';

    if (context != null) {
      return '$context $baseLabel';
    }

    return baseLabel;
  }

  // ==================== Touch Target Validation ====================

  /// Minimum recommended touch target size (48x48 dp)
  static const double minTouchTargetSize = 48.0;

  /// Check if a size meets accessibility touch target guidelines
  bool isTouchTargetSizeValid(Size size) {
    return size.width >= minTouchTargetSize && size.height >= minTouchTargetSize;
  }

  /// Get recommended touch target padding
  EdgeInsets getRecommendedTouchPadding(Size currentSize) {
    final widthPadding = (minTouchTargetSize - currentSize.width) / 2;
    final heightPadding = (minTouchTargetSize - currentSize.height) / 2;

    return EdgeInsets.symmetric(
      horizontal: widthPadding > 0 ? widthPadding : 0,
      vertical: heightPadding > 0 ? heightPadding : 0,
    );
  }

  // ==================== Color Contrast ====================

  /// Calculate contrast ratio between two colors
  /// WCAG AA requires 4.5:1 for normal text, 3:1 for large text
  double getContrastRatio(Color color1, Color color2) {
    final luminance1 = color1.computeLuminance();
    final luminance2 = color2.computeLuminance();

    final lighter = luminance1 > luminance2 ? luminance1 : luminance2;
    final darker = luminance1 > luminance2 ? luminance2 : luminance1;

    return (lighter + 0.05) / (darker + 0.05);
  }

  /// Check if color contrast meets WCAG AA standards
  bool hasValidContrast(Color foreground, Color background, {bool isLargeText = false}) {
    final contrast = getContrastRatio(foreground, background);
    final requiredContrast = isLargeText ? 3.0 : 4.5;

    return contrast >= requiredContrast;
  }

  // ==================== Text Scaling ====================

  /// Get scaled text size based on accessibility settings
  double getScaledTextSize(BuildContext context, double baseSize) {
    final mediaQuery = MediaQuery.of(context);
    return baseSize * mediaQuery.textScaleFactor;
  }

  /// Check if text scaling is enabled
  bool isTextScalingEnabled(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    return mediaQuery.textScaleFactor > 1.0;
  }

  /// Get maximum text scale factor (typically 2.0 for accessibility)
  double getMaxTextScaleFactor() {
    return 2.0;
  }

  // ==================== Platform-Specific Features ====================

  /// Get platform-specific accessibility features
  AccessibilityFeatures? getPlatformAccessibilityFeatures() {
    return SemanticsBinding.instance?.accessibilityFeatures;
  }

  /// Check if high contrast mode is enabled
  bool isHighContrastEnabled() {
    return SemanticsBinding.instance?.accessibilityFeatures.highContrast ?? false;
  }

  /// Check if bold text is enabled
  bool isBoldTextEnabled() {
    return SemanticsBinding.instance?.accessibilityFeatures.boldText ?? false;
  }

  /// Check if reduce motion is enabled
  bool isReduceMotionEnabled() {
    return SemanticsBinding.instance?.accessibilityFeatures.disableAnimations ?? false;
  }

  // ==================== Voice Input Accessibility ====================

  /// Get semantic label for voice recording button
  String getVoiceRecordingButtonLabel({
    required bool isRecording,
    required bool isPaused,
    Duration? duration,
  }) {
    if (isRecording && !isPaused) {
      if (duration != null) {
        final minutes = duration.inMinutes;
        final seconds = duration.inSeconds % 60;
        return '停止录音按钮，当前正在录音，已录制 $minutes 分 $seconds 秒';
      }
      return '停止录音按钮，当前正在录音';
    }

    if (isPaused) {
      return '继续录音按钮，录音已暂停';
    }

    return '开始录音按钮';
  }

  /// Get hint for voice recording
  String getVoiceRecordingHint({required bool isRecording}) {
    if (isRecording) {
      return '点击停止当前录音';
    }
    return '点击开始录音，最长可录制5分钟';
  }

  // ==================== Image OCR Accessibility ====================

  /// Get semantic label for image selection
  String getImageSelectionLabel({
    required bool hasImage,
    String? imagePath,
  }) {
    if (hasImage && imagePath != null) {
      final fileName = imagePath.split('/').last;
      return '已选择图片 $fileName，点击更换图片';
    }
    return '选择图片按钮，点击从相机拍照或从相册选择';
  }

  /// Get hint for image OCR
  String getImageOCRHint() {
    return '选择包含文字的清晰图片，系统将自动识别文字内容';
  }

  // ==================== Text Input Accessibility ====================

  /// Get semantic label for text input field
  String getTextInputLabel({
    required int characterCount,
    required int minLength,
    required int maxLength,
  }) {
    final remaining = maxLength - characterCount;

    if (characterCount < minLength) {
      return '文本输入区域，已输入 $characterCount 字符，还需至少 ${minLength - characterCount} 字符';
    }

    if (remaining < 50) {
      return '文本输入区域，已输入 $characterCount 字符，剩余 $remaining 字符';
    }

    return '文本输入区域，已输入 $characterCount 字符';
  }

  /// Get hint for text input
  String getTextInputHint() {
    return '输入您的灵感内容，至少10个字符，系统将自动生成分类和摘要';
  }

  // ==================== Sync Accessibility ====================

  /// Get semantic label for sync indicator
  String getSyncIndicatorLabel({
    required bool isSyncing,
    required bool isConnected,
    int? pendingCount,
  }) {
    if (isSyncing && pendingCount != null) {
      return '正在同步 $pendingCount 条记录到云端';
    }

    if (isSyncing) {
      return '正在同步到云端';
    }

    if (!isConnected) {
      if (pendingCount != null && pendingCount > 0) {
        return '网络未连接，有 $pendingCount 条记录等待同步';
      }
      return '网络未连接';
    }

    return '已同步到云端';
  }

  /// Get hint for manual sync button
  String getManualSyncHint({required bool canSync}) {
    if (canSync) {
      return '点击手动同步所有待同步记录到云端';
    }
    return '当前无法同步，请检查网络连接';
  }
}

/// Extension for adding accessibility features to widgets
extension AccessibilityWidgetExtension on Widget {
  /// Wrap widget with semantic label
  Widget withSemantics({
    required String label,
    String? hint,
    bool? isButton,
    bool? isEnabled,
    VoidCallback? onTap,
  }) {
    return Semantics(
      label: label,
      hint: hint,
      button: isButton ?? false,
      enabled: isEnabled ?? true,
      onTap: onTap,
      child: this,
    );
  }

  /// Wrap widget with minimum touch target size
  Widget withMinTouchTarget({double minSize = 48.0}) {
    return ConstrainedBox(
      constraints: BoxConstraints(
        minWidth: minSize,
        minHeight: minSize,
      ),
      child: this,
    );
  }

  /// Exclude from semantics tree
  Widget excludeSemantics() {
    return ExcludeSemantics(child: this);
  }
}
