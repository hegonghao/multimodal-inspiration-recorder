import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

/// Service for monitoring network connectivity status
/// Provides real-time network status updates for sync operations
class ConnectivityService extends ChangeNotifier {

  ConnectivityService() {
    _initConnectivity();
  }
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _subscription;

  bool _isConnected = false;
  ConnectivityResult _currentConnection = ConnectivityResult.none;
  DateTime? _lastConnectedAt;
  DateTime? _lastDisconnectedAt;

  // ==================== Getters ====================

  /// Whether device has active network connection
  bool get isConnected => _isConnected;

  /// Current connection type
  ConnectivityResult get currentConnection => _currentConnection;

  /// Whether connected via WiFi
  bool get isWifi => _currentConnection == ConnectivityResult.wifi;

  /// Whether connected via mobile data
  bool get isMobile => _currentConnection == ConnectivityResult.mobile;

  /// Whether connected via ethernet
  bool get isEthernet => _currentConnection == ConnectivityResult.ethernet;

  /// Last time device was connected
  DateTime? get lastConnectedAt => _lastConnectedAt;

  /// Last time device was disconnected
  DateTime? get lastDisconnectedAt => _lastDisconnectedAt;

  /// Duration since last connection status change
  Duration? get timeSinceLastChange {
    final lastChange = _isConnected ? _lastConnectedAt : _lastDisconnectedAt;
    if (lastChange == null) return null;
    return DateTime.now().difference(lastChange);
  }

  /// Human-readable connection status
  String get connectionStatus {
    if (!_isConnected) return '离线';

    switch (_currentConnection) {
      case ConnectivityResult.wifi:
        return 'WiFi已连接';
      case ConnectivityResult.mobile:
        return '移动网络已连接';
      case ConnectivityResult.ethernet:
        return '以太网已连接';
      case ConnectivityResult.vpn:
        return 'VPN已连接';
      case ConnectivityResult.bluetooth:
        return '蓝牙已连接';
      case ConnectivityResult.other:
        return '其他网络已连接';
      case ConnectivityResult.none:
        return '离线';
    }
  }

  // ==================== Initialization ====================

  /// Initialize connectivity monitoring
  Future<void> _initConnectivity() async {
    try {
      // Get initial connection status
      final results = await _connectivity.checkConnectivity();
      _updateConnectionStatus(results);

      // Listen to connectivity changes
      _subscription = _connectivity.onConnectivityChanged.listen(
        _updateConnectionStatus,
        onError: (error) {
          debugPrint('Connectivity error: $error');
        },
      );
    } catch (e) {
      debugPrint('Failed to initialize connectivity service: $e');
      _isConnected = false;
      _currentConnection = ConnectivityResult.none;
    }
  }

  /// Update connection status when connectivity changes
  void _updateConnectionStatus(List<ConnectivityResult> results) {
    final wasConnected = _isConnected;

    // Consider connected if any connection type is not "none"
    _isConnected = results.any((result) => result != ConnectivityResult.none);

    // Pick the primary connection type (prioritize WiFi > Ethernet > Mobile > Other)
    _currentConnection = _selectPrimaryConnection(results);

    // Track connection state changes
    if (_isConnected && !wasConnected) {
      _lastConnectedAt = DateTime.now();
      debugPrint('Network connected: $_currentConnection');
    } else if (!_isConnected && wasConnected) {
      _lastDisconnectedAt = DateTime.now();
      debugPrint('Network disconnected');
    }

    // Notify listeners of status change
    notifyListeners();
  }

  /// Select primary connection from multiple results
  ConnectivityResult _selectPrimaryConnection(List<ConnectivityResult> results) {
    if (results.isEmpty) return ConnectivityResult.none;

    // Priority order: WiFi > Ethernet > Mobile > VPN > Other
    if (results.contains(ConnectivityResult.wifi)) {
      return ConnectivityResult.wifi;
    } else if (results.contains(ConnectivityResult.ethernet)) {
      return ConnectivityResult.ethernet;
    } else if (results.contains(ConnectivityResult.mobile)) {
      return ConnectivityResult.mobile;
    } else if (results.contains(ConnectivityResult.vpn)) {
      return ConnectivityResult.vpn;
    } else if (results.contains(ConnectivityResult.bluetooth)) {
      return ConnectivityResult.bluetooth;
    } else if (results.contains(ConnectivityResult.other)) {
      return ConnectivityResult.other;
    }

    return ConnectivityResult.none;
  }

  // ==================== Public Methods ====================

  /// Manually check current connectivity status
  Future<bool> checkConnectivity() async {
    try {
      final results = await _connectivity.checkConnectivity();
      _updateConnectionStatus(results);
      return _isConnected;
    } catch (e) {
      debugPrint('Failed to check connectivity: $e');
      return false;
    }
  }

  /// Wait for network connection (with timeout)
  Future<bool> waitForConnection({
    Duration timeout = const Duration(seconds: 30),
  }) async {
    if (_isConnected) return true;

    final completer = Completer<bool>();
    StreamSubscription? subscription;

    // Set up listener for connection
    subscription = _connectivity.onConnectivityChanged.listen((results) {
      final connected = results.any((r) => r != ConnectivityResult.none);
      if (connected && !completer.isCompleted) {
        completer.complete(true);
        subscription?.cancel();
      }
    });

    // Set up timeout
    Timer(timeout, () {
      if (!completer.isCompleted) {
        completer.complete(false);
        subscription?.cancel();
      }
    });

    return completer.future;
  }

  /// Check if should sync based on user preferences
  /// Useful for implementing "WiFi-only sync" feature
  bool shouldSync({bool wifiOnly = false}) {
    if (!_isConnected) return false;
    if (!wifiOnly) return true;
    return isWifi || isEthernet;
  }

  // ==================== Lifecycle ====================

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}

/// Extension for connection quality estimation
extension ConnectivityQuality on ConnectivityResult {
  /// Estimate connection quality (subjective)
  ConnectionQuality get quality {
    switch (this) {
      case ConnectivityResult.wifi:
      case ConnectivityResult.ethernet:
        return ConnectionQuality.excellent;
      case ConnectivityResult.mobile:
        return ConnectionQuality.good;
      case ConnectivityResult.vpn:
        return ConnectionQuality.moderate;
      case ConnectivityResult.bluetooth:
      case ConnectivityResult.other:
        return ConnectionQuality.poor;
      case ConnectivityResult.none:
        return ConnectionQuality.none;
    }
  }
}

/// Connection quality enum
enum ConnectionQuality {
  none,
  poor,
  moderate,
  good,
  excellent;

  /// Whether quality is good enough for sync
  bool get isGoodForSync => index >= ConnectionQuality.moderate.index;
}
