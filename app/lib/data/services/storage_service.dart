import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import 'package:logger/logger.dart';

/// Local Storage Service
///
/// Provides unified interface for storing data locally using:
/// - SharedPreferences for non-sensitive data
/// - FlutterSecureStorage for sensitive data (tokens, credentials)
class StorageService {
  static StorageService? _instance;
  static SharedPreferences? _prefs;
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  final Logger _logger = Logger();

  StorageService._();

  /// Get singleton instance
  static Future<StorageService> getInstance() async {
    if (_instance == null) {
      _instance = StorageService._();
      _prefs = await SharedPreferences.getInstance();
    }
    return _instance!;
  }

  // ==================== General Storage (SharedPreferences) ====================

  /// Save string value
  Future<bool> setString(String key, String value) async {
    try {
      return await _prefs!.setString(key, value);
    } catch (e) {
      _logger.e('Error saving string: $e');
      return false;
    }
  }

  /// Get string value
  String? getString(String key, {String? defaultValue}) {
    try {
      return _prefs!.getString(key) ?? defaultValue;
    } catch (e) {
      _logger.e('Error getting string: $e');
      return defaultValue;
    }
  }

  /// Save int value
  Future<bool> setInt(String key, int value) async {
    try {
      return await _prefs!.setInt(key, value);
    } catch (e) {
      _logger.e('Error saving int: $e');
      return false;
    }
  }

  /// Get int value
  int? getInt(String key, {int? defaultValue}) {
    try {
      return _prefs!.getInt(key) ?? defaultValue;
    } catch (e) {
      _logger.e('Error getting int: $e');
      return defaultValue;
    }
  }

  /// Save bool value
  Future<bool> setBool(String key, bool value) async {
    try {
      return await _prefs!.setBool(key, value);
    } catch (e) {
      _logger.e('Error saving bool: $e');
      return false;
    }
  }

  /// Get bool value
  bool? getBool(String key, {bool? defaultValue}) {
    try {
      return _prefs!.getBool(key) ?? defaultValue;
    } catch (e) {
      _logger.e('Error getting bool: $e');
      return defaultValue;
    }
  }

  /// Save double value
  Future<bool> setDouble(String key, double value) async {
    try {
      return await _prefs!.setDouble(key, value);
    } catch (e) {
      _logger.e('Error saving double: $e');
      return false;
    }
  }

  /// Get double value
  double? getDouble(String key, {double? defaultValue}) {
    try {
      return _prefs!.getDouble(key) ?? defaultValue;
    } catch (e) {
      _logger.e('Error getting double: $e');
      return defaultValue;
    }
  }

  /// Save list of strings
  Future<bool> setStringList(String key, List<String> value) async {
    try {
      return await _prefs!.setStringList(key, value);
    } catch (e) {
      _logger.e('Error saving string list: $e');
      return false;
    }
  }

  /// Get list of strings
  List<String>? getStringList(String key, {List<String>? defaultValue}) {
    try {
      return _prefs!.getStringList(key) ?? defaultValue;
    } catch (e) {
      _logger.e('Error getting string list: $e');
      return defaultValue;
    }
  }

  /// Save JSON object
  Future<bool> setJSON(String key, Map<String, dynamic> value) async {
    try {
      final jsonString = jsonEncode(value);
      return await _prefs!.setString(key, jsonString);
    } catch (e) {
      _logger.e('Error saving JSON: $e');
      return false;
    }
  }

  /// Get JSON object
  Map<String, dynamic>? getJSON(String key) {
    try {
      final jsonString = _prefs!.getString(key);
      if (jsonString == null) return null;
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      _logger.e('Error getting JSON: $e');
      return null;
    }
  }

  /// Remove value
  Future<bool> remove(String key) async {
    try {
      return await _prefs!.remove(key);
    } catch (e) {
      _logger.e('Error removing key: $e');
      return false;
    }
  }

  /// Clear all data
  Future<bool> clear() async {
    try {
      return await _prefs!.clear();
    } catch (e) {
      _logger.e('Error clearing storage: $e');
      return false;
    }
  }

  /// Check if key exists
  bool containsKey(String key) {
    try {
      return _prefs!.containsKey(key);
    } catch (e) {
      _logger.e('Error checking key existence: $e');
      return false;
    }
  }

  // ==================== Secure Storage (FlutterSecureStorage) ====================

  /// Save secure string value
  Future<void> setSecureString(String key, String value) async {
    try {
      await _secureStorage.write(key: key, value: value);
    } catch (e) {
      _logger.e('Error saving secure string: $e');
      rethrow;
    }
  }

  /// Get secure string value
  Future<String?> getSecureString(String key) async {
    try {
      return await _secureStorage.read(key: key);
    } catch (e) {
      _logger.e('Error reading secure string: $e');
      return null;
    }
  }

  /// Save secure JSON object
  Future<void> setSecureJSON(String key, Map<String, dynamic> value) async {
    try {
      final jsonString = jsonEncode(value);
      await _secureStorage.write(key: key, value: jsonString);
    } catch (e) {
      _logger.e('Error saving secure JSON: $e');
      rethrow;
    }
  }

  /// Get secure JSON object
  Future<Map<String, dynamic>?> getSecureJSON(String key) async {
    try {
      final jsonString = await _secureStorage.read(key: key);
      if (jsonString == null) return null;
      return jsonDecode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      _logger.e('Error reading secure JSON: $e');
      return null;
    }
  }

  /// Remove secure value
  Future<void> removeSecure(String key) async {
    try {
      await _secureStorage.delete(key: key);
    } catch (e) {
      _logger.e('Error removing secure key: $e');
      rethrow;
    }
  }

  /// Clear all secure data
  Future<void> clearSecure() async {
    try {
      await _secureStorage.deleteAll();
    } catch (e) {
      _logger.e('Error clearing secure storage: $e');
      rethrow;
    }
  }

  /// Check if secure key exists
  Future<bool> containsSecureKey(String key) async {
    try {
      return await _secureStorage.containsKey(key: key);
    } catch (e) {
      _logger.e('Error checking secure key existence: $e');
      return false;
    }
  }

  // ==================== App-Specific Storage Keys ====================

  // User Preferences
  static const String keyApiBaseUrl = 'api_base_url';
  static const String keyThemeMode = 'theme_mode';
  static const String keyLanguage = 'language';
  static const String keyAutoSync = 'auto_sync';
  static const String keySyncInterval = 'sync_interval';
  static const String keyMaxVoiceDuration = 'max_voice_duration';
  static const String keyAutoClassify = 'auto_classify';
  static const String keyAutoSummarize = 'auto_summarize';

  // Secure Storage Keys
  static const String keyNotionToken = 'notion_token';
  static const String keyNotionDatabaseId = 'notion_database_id';
  static const String keyOpenAIApiKey = 'openai_api_key';
  static const String keyEncryptionKey = 'encryption_key';

  // App State
  static const String keyLastSyncTime = 'last_sync_time';
  static const String keyFirstLaunch = 'first_launch';
  static const String keyOnboardingCompleted = 'onboarding_completed';

  // ==================== Helper Methods ====================

  /// Save user preferences
  Future<bool> saveUserPreferences(Map<String, dynamic> preferences) async {
    try {
      // Save non-sensitive preferences
      if (preferences.containsKey('api_base_url')) {
        await setString(keyApiBaseUrl, preferences['api_base_url'] as String);
      }
      if (preferences.containsKey('theme_mode')) {
        await setString(keyThemeMode, preferences['theme_mode'] as String);
      }
      if (preferences.containsKey('language')) {
        await setString(keyLanguage, preferences['language'] as String);
      }
      if (preferences.containsKey('auto_sync')) {
        await setBool(keyAutoSync, preferences['auto_sync'] as bool);
      }
      if (preferences.containsKey('sync_interval')) {
        await setInt(keySyncInterval, preferences['sync_interval'] as int);
      }
      if (preferences.containsKey('max_voice_duration')) {
        await setInt(
          keyMaxVoiceDuration,
          preferences['max_voice_duration'] as int,
        );
      }
      if (preferences.containsKey('auto_classify')) {
        await setBool(keyAutoClassify, preferences['auto_classify'] as bool);
      }
      if (preferences.containsKey('auto_summarize')) {
        await setBool(
          keyAutoSummarize,
          preferences['auto_summarize'] as bool,
        );
      }

      // Save sensitive preferences securely
      if (preferences.containsKey('notion_token')) {
        await setSecureString(
          keyNotionToken,
          preferences['notion_token'] as String,
        );
      }
      if (preferences.containsKey('notion_database_id')) {
        await setSecureString(
          keyNotionDatabaseId,
          preferences['notion_database_id'] as String,
        );
      }
      if (preferences.containsKey('openai_api_key')) {
        await setSecureString(
          keyOpenAIApiKey,
          preferences['openai_api_key'] as String,
        );
      }

      return true;
    } catch (e) {
      _logger.e('Error saving user preferences: $e');
      return false;
    }
  }

  /// Get user preferences
  Future<Map<String, dynamic>> getUserPreferences() async {
    try {
      return {
        'api_base_url': getString(keyApiBaseUrl, defaultValue: 'http://localhost:8000'),
        'theme_mode': getString(keyThemeMode, defaultValue: 'system'),
        'language': getString(keyLanguage, defaultValue: 'zh_CN'),
        'auto_sync': getBool(keyAutoSync, defaultValue: true),
        'sync_interval': getInt(keySyncInterval, defaultValue: 1800),
        'max_voice_duration': getInt(keyMaxVoiceDuration, defaultValue: 300),
        'auto_classify': getBool(keyAutoClassify, defaultValue: true),
        'auto_summarize': getBool(keyAutoSummarize, defaultValue: true),
        'notion_token': await getSecureString(keyNotionToken),
        'notion_database_id': await getSecureString(keyNotionDatabaseId),
        'openai_api_key': await getSecureString(keyOpenAIApiKey),
      };
    } catch (e) {
      _logger.e('Error getting user preferences: $e');
      return {};
    }
  }

  /// Clear all user data (including secure storage)
  Future<void> clearAllData() async {
    try {
      await clear();
      await clearSecure();
      _logger.i('All user data cleared');
    } catch (e) {
      _logger.e('Error clearing all data: $e');
      rethrow;
    }
  }

  /// Check if this is first launch
  Future<bool> isFirstLaunch() async {
    final firstLaunch = getBool(keyFirstLaunch);
    if (firstLaunch == null) {
      await setBool(keyFirstLaunch, false);
      return true;
    }
    return false;
  }

  /// Mark onboarding as completed
  Future<void> completeOnboarding() async {
    await setBool(keyOnboardingCompleted, true);
  }

  /// Check if onboarding is completed
  bool isOnboardingCompleted() {
    return getBool(keyOnboardingCompleted, defaultValue: false) ?? false;
  }

  /// Save last sync time
  Future<void> saveLastSyncTime() async {
    await setString(keyLastSyncTime, DateTime.now().toIso8601String());
  }

  /// Get last sync time
  DateTime? getLastSyncTime() {
    final timeString = getString(keyLastSyncTime);
    if (timeString == null) return null;
    try {
      return DateTime.parse(timeString);
    } catch (e) {
      _logger.e('Error parsing last sync time: $e');
      return null;
    }
  }
}
