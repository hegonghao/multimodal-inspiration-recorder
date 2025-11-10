import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Service for managing local notifications
/// Provides sync status updates and other important notifications
class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;
  bool _permissionGranted = false;

  // Notification channel IDs
  static const String _syncChannelId = 'sync_notifications';
  static const String _syncChannelName = '同步通知';
  static const String _syncChannelDescription = 'Notion同步状态更新';

  static const String _generalChannelId = 'general_notifications';
  static const String _generalChannelName = '一般通知';
  static const String _generalChannelDescription = '应用一般通知';

  // Notification IDs
  static const int _syncNotificationId = 1000;
  static const int _syncSuccessNotificationId = 1001;
  static const int _syncErrorNotificationId = 1002;

  // ==================== Initialization ====================

  /// Initialize notification service
  /// Must be called before using any notification features
  Future<bool> initialize() async {
    if (_initialized) return _permissionGranted;

    try {
      // Android initialization settings
      const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');

      // iOS initialization settings
      const iosSettings = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
      );

      // Initialize settings
      final initSettings = InitializationSettings(
        android: androidSettings,
        iOS: iosSettings,
      );

      // Initialize plugin
      final result = await _notifications.initialize(
        initSettings,
        onDidReceiveNotificationResponse: _onNotificationTapped,
      );

      if (result == true) {
        // Create notification channels for Android
        if (Platform.isAndroid) {
          await _createNotificationChannels();
        }

        // Request permissions for iOS
        if (Platform.isIOS) {
          _permissionGranted = await _requestIOSPermissions();
        } else {
          _permissionGranted = true; // Android permissions handled in manifest
        }

        _initialized = true;
        debugPrint('Notification service initialized successfully');
      } else {
        debugPrint('Failed to initialize notification service');
      }

      return _permissionGranted;
    } catch (e) {
      debugPrint('Error initializing notification service: $e');
      return false;
    }
  }

  /// Create notification channels for Android 8.0+
  Future<void> _createNotificationChannels() async {
    // Sync notification channel
    const syncChannel = AndroidNotificationChannel(
      _syncChannelId,
      _syncChannelName,
      description: _syncChannelDescription,
      importance: Importance.low, // Low importance for background sync
      playSound: false,
      enableVibration: false,
      showBadge: true,
    );

    // General notification channel
    const generalChannel = AndroidNotificationChannel(
      _generalChannelId,
      _generalChannelName,
      description: _generalChannelDescription,
      importance: Importance.defaultImportance,
      playSound: true,
      enableVibration: true,
      showBadge: true,
    );

    await _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(syncChannel);

    await _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(generalChannel);
  }

  /// Request iOS notification permissions
  Future<bool> _requestIOSPermissions() async {
    final result = await _notifications
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );

    return result ?? false;
  }

  // ==================== Sync Notifications ====================

  /// Show sync in progress notification
  Future<void> showSyncInProgress({
    required int pendingCount,
    bool showProgress = false,
  }) async {
    if (!_canShowNotification()) return;

    const androidDetails = AndroidNotificationDetails(
      _syncChannelId,
      _syncChannelName,
      channelDescription: _syncChannelDescription,
      importance: Importance.low,
      priority: Priority.low,
      ongoing: true, // Cannot be dismissed while syncing
      autoCancel: false,
      showProgress: true,
      indeterminate: true,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: false,
      presentBadge: true,
      presentSound: false,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      _syncNotificationId,
      '正在同步到Notion',
      pendingCount > 0 ? '正在同步 $pendingCount 条记录...' : '正在同步...',
      details,
    );
  }

  /// Show sync success notification
  Future<void> showSyncSuccess({
    required int syncedCount,
    bool silent = false,
  }) async {
    if (!_canShowNotification()) return;

    // Cancel in-progress notification
    await cancelSyncNotifications();

    // Only show success notification if there were items synced
    if (syncedCount == 0 && silent) return;

    final androidDetails = AndroidNotificationDetails(
      _syncChannelId,
      _syncChannelName,
      channelDescription: _syncChannelDescription,
      importance: silent ? Importance.low : Importance.defaultImportance,
      priority: silent ? Priority.low : Priority.defaultPriority,
      autoCancel: true,
      icon: '@mipmap/ic_launcher',
      styleInformation: syncedCount > 0
          ? BigTextStyleInformation(
              '成功同步 $syncedCount 条记录到Notion',
              contentTitle: '同步完成',
            )
          : null,
    );

    final iosDetails = DarwinNotificationDetails(
      presentAlert: !silent,
      presentBadge: true,
      presentSound: !silent,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      _syncSuccessNotificationId,
      '同步完成',
      syncedCount > 0 ? '成功同步 $syncedCount 条记录' : '所有记录已同步',
      details,
    );

    // Auto-dismiss after 3 seconds
    if (!silent) {
      Future.delayed(const Duration(seconds: 3), () {
        _notifications.cancel(_syncSuccessNotificationId);
      });
    }
  }

  /// Show sync error notification
  Future<void> showSyncError({
    required String error,
    int? failedCount,
  }) async {
    if (!_canShowNotification()) return;

    // Cancel in-progress notification
    await cancelSyncNotifications();

    final androidDetails = AndroidNotificationDetails(
      _syncChannelId,
      _syncChannelName,
      channelDescription: _syncChannelDescription,
      importance: Importance.defaultImportance,
      priority: Priority.defaultPriority,
      autoCancel: true,
      icon: '@mipmap/ic_launcher',
      styleInformation: BigTextStyleInformation(
        error,
        contentTitle: '同步失败',
      ),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    final message = failedCount != null && failedCount > 0
        ? '$failedCount 条记录同步失败'
        : '同步失败，请检查网络连接';

    await _notifications.show(
      _syncErrorNotificationId,
      '同步失败',
      message,
      details,
    );
  }

  /// Show sync completed with partial errors
  Future<void> showSyncPartialSuccess({
    required int syncedCount,
    required int failedCount,
  }) async {
    if (!_canShowNotification()) return;

    // Cancel in-progress notification
    await cancelSyncNotifications();

    final androidDetails = AndroidNotificationDetails(
      _syncChannelId,
      _syncChannelName,
      channelDescription: _syncChannelDescription,
      importance: Importance.defaultImportance,
      priority: Priority.defaultPriority,
      autoCancel: true,
      icon: '@mipmap/ic_launcher',
      styleInformation: BigTextStyleInformation(
        '成功: $syncedCount, 失败: $failedCount',
        contentTitle: '同步部分完成',
      ),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      _syncSuccessNotificationId,
      '同步部分完成',
      '成功 $syncedCount 条，失败 $failedCount 条',
      details,
    );
  }

  /// Cancel all sync-related notifications
  Future<void> cancelSyncNotifications() async {
    await _notifications.cancel(_syncNotificationId);
    await _notifications.cancel(_syncSuccessNotificationId);
    await _notifications.cancel(_syncErrorNotificationId);
  }

  // ==================== General Notifications ====================

  /// Show a general informational notification
  Future<void> showInfo({
    required String title,
    required String message,
    String? payload,
  }) async {
    if (!_canShowNotification()) return;

    const androidDetails = AndroidNotificationDetails(
      _generalChannelId,
      _generalChannelName,
      channelDescription: _generalChannelDescription,
      importance: Importance.defaultImportance,
      priority: Priority.defaultPriority,
      autoCancel: true,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000, // Unique ID
      title,
      message,
      details,
      payload: payload,
    );
  }

  /// Show storage limit warning
  Future<void> showStorageLimitWarning({
    required int currentCount,
    required int maxCount,
  }) async {
    if (!_canShowNotification()) return;

    final androidDetails = AndroidNotificationDetails(
      _generalChannelId,
      _generalChannelName,
      channelDescription: _generalChannelDescription,
      importance: Importance.high,
      priority: Priority.high,
      autoCancel: true,
      icon: '@mipmap/ic_launcher',
      styleInformation: BigTextStyleInformation(
        '当前已存储 $currentCount/$maxCount 条记录。建议清理已同步的旧记录。',
        contentTitle: '存储空间不足',
      ),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(
      2000, // Fixed ID for storage warnings
      '存储空间不足',
      '已使用 $currentCount/$maxCount 条记录',
      details,
    );
  }

  // ==================== Notification Handlers ====================

  /// Handle iOS foreground notifications (iOS <10)
  Future<void> _onDidReceiveLocalNotification(
    int id,
    String? title,
    String? body,
    String? payload,
  ) async {
    debugPrint('iOS notification received: $title - $body');
    // Handle foreground notification on iOS
  }

  /// Handle notification tap
  Future<void> _onNotificationTapped(NotificationResponse response) async {
    final payload = response.payload;
    debugPrint('Notification tapped with payload: $payload');

    // Handle notification tap based on payload
    // You can navigate to specific screens or perform actions
    if (payload != null) {
      // Parse payload and handle accordingly
      // Example: navigate to sync status page
    }
  }

  // ==================== Utility Methods ====================

  /// Check if notifications can be shown
  bool _canShowNotification() {
    if (!_initialized) {
      debugPrint('Notification service not initialized');
      return false;
    }

    if (!_permissionGranted) {
      debugPrint('Notification permission not granted');
      return false;
    }

    return true;
  }

  /// Check if notification permission is granted
  bool get permissionGranted => _permissionGranted;

  /// Check if notification service is initialized
  bool get initialized => _initialized;

  /// Cancel all notifications
  Future<void> cancelAll() async {
    await _notifications.cancelAll();
  }

  /// Cancel specific notification
  Future<void> cancel(int id) async {
    await _notifications.cancel(id);
  }

  /// Get pending notifications
  Future<List<PendingNotificationRequest>> getPendingNotifications() async {
    return await _notifications.pendingNotificationRequests();
  }

  /// Get active notifications (Android only)
  Future<List<ActiveNotification>> getActiveNotifications() async {
    if (!Platform.isAndroid) return [];

    return await _notifications
            .resolvePlatformSpecificImplementation<
                AndroidFlutterLocalNotificationsPlugin>()
            ?.getActiveNotifications() ??
        [];
  }
}
