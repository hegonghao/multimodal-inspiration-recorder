import 'dart:async';
import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:logger/logger.dart';

/// Audio Recording Service
///
/// Provides voice recording functionality with features:
/// - Record audio with configurable settings
/// - 5-minute duration limit
/// - Pause/resume support
/// - Real-time duration tracking
/// - AAC-LC encoding for optimal quality/size ratio
class AudioService {
  final AudioRecorder _recorder = AudioRecorder();
  final Logger _logger = Logger();

  bool _isRecording = false;
  bool _isPaused = false;
  DateTime? _recordingStartTime;
  Timer? _durationTimer;
  File? _currentRecordingFile;

  // Constants
  static const int maxDurationSeconds = 300; // 5 minutes
  static const String audioFormat = 'm4a'; // M4A (AAC in MP4 container) - best compatibility

  // Streams for real-time updates
  final StreamController<Duration> _durationController = StreamController<Duration>.broadcast();
  final StreamController<bool> _recordingStateController = StreamController<bool>.broadcast();
  final StreamController<double> _amplitudeController = StreamController<double>.broadcast();

  Stream<Duration> get durationStream => _durationController.stream;
  Stream<bool> get recordingStateStream => _recordingStateController.stream;
  Stream<double> get amplitudeStream => _amplitudeController.stream;

  bool get isRecording => _isRecording;
  bool get isPaused => _isPaused;
  Duration? get currentDuration => _recordingStartTime != null
      ? DateTime.now().difference(_recordingStartTime!)
      : null;

  /// Initialize the audio service
  Future<void> initialize() async {
    _logger.i('Initializing audio service');
  }

  /// Check and request microphone permission
  Future<bool> requestPermission() async {
    try {
      final status = await Permission.microphone.status;

      if (status.isGranted) {
        _logger.i('Microphone permission already granted');
        return true;
      }

      if (status.isDenied) {
        final result = await Permission.microphone.request();
        if (result.isGranted) {
          _logger.i('Microphone permission granted');
          return true;
        } else {
          _logger.w('Microphone permission denied');
          return false;
        }
      }

      if (status.isPermanentlyDenied) {
        _logger.e('Microphone permission permanently denied');
        // Guide user to app settings
        await openAppSettings();
        return false;
      }

      return false;
    } catch (e) {
      _logger.e('Error requesting microphone permission: $e');
      return false;
    }
  }

  /// Start recording audio
  Future<RecordingResult> startRecording() async {
    try {
      // Check permission
      final hasPermission = await requestPermission();
      if (!hasPermission) {
        return RecordingResult.error('Microphone permission not granted');
      }

      // Check if already recording
      if (_isRecording) {
        return RecordingResult.error('Recording already in progress');
      }

      // Check if device supports recording
      final isSupported = await _recorder.hasPermission();
      if (!isSupported) {
        return RecordingResult.error('Device does not support recording');
      }

      // Generate file path
      final directory = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final filePath = '${directory.path}/voice_$timestamp.$audioFormat';
      _currentRecordingFile = File(filePath);

      // Configure recording settings for M4A (AAC)
      // FIXED: Re-enable echo cancellation and noise suppression for better quality
      // These were causing low/no volume on Android emulators
      const config = RecordConfig(
        encoder: AudioEncoder.aacLc, // AAC-LC encoding (widely supported)
        bitRate: 128000, // 128kbps for good quality
        sampleRate: 44100, // 44.1kHz for better quality (Android works better with this)
        numChannels: 1, // Mono
        autoGain: true, // Enable automatic gain control - critical for emulators
        echoCancel: true, // CHANGED: Enable to prevent audio feedback
        noiseSuppress: true, // CHANGED: Enable to filter background noise
      );

      // Start recording
      await _recorder.start(config, path: filePath);

      _isRecording = true;
      _isPaused = false;
      _recordingStartTime = DateTime.now();
      _recordingStateController.add(true);

      // Start duration timer
      _startDurationTimer();

      // Start amplitude monitoring
      _startAmplitudeMonitoring();

      _logger.i('Recording started: $filePath');
      return RecordingResult.success(filePath);

    } catch (e) {
      _logger.e('Error starting recording: $e');
      return RecordingResult.error('Failed to start recording: $e');
    }
  }

  /// Stop recording and return the file path
  Future<RecordingResult> stopRecording() async {
    try {
      if (!_isRecording) {
        return RecordingResult.error('No recording in progress');
      }

      // Stop recording
      final path = await _recorder.stop();

      _isRecording = false;
      _isPaused = false;
      _recordingStartTime = null;
      _recordingStateController.add(false);

      // Stop timers
      _stopDurationTimer();

      if (path == null) {
        _logger.e('Recording stopped but no file path returned');
        return RecordingResult.error('Recording failed - no file created');
      }

      // Verify file exists and has content
      final file = File(path);
      if (!await file.exists()) {
        _logger.e('Recording file does not exist: $path');
        return RecordingResult.error('Recording file not found');
      }

      final fileSize = await file.length();
      if (fileSize == 0) {
        _logger.e('Recording file is empty: $path');
        return RecordingResult.error('Recording file is empty');
      }

      _logger.i('Recording stopped successfully: $path (${fileSize} bytes)');
      return RecordingResult.success(path, fileSize: fileSize);

    } catch (e) {
      _logger.e('Error stopping recording: $e');
      return RecordingResult.error('Failed to stop recording: $e');
    }
  }

  /// Pause recording
  Future<bool> pauseRecording() async {
    try {
      if (!_isRecording || _isPaused) {
        _logger.w('Cannot pause - not recording or already paused');
        return false;
      }

      await _recorder.pause();
      _isPaused = true;
      _stopDurationTimer();

      _logger.i('Recording paused');
      return true;

    } catch (e) {
      _logger.e('Error pausing recording: $e');
      return false;
    }
  }

  /// Resume recording
  Future<bool> resumeRecording() async {
    try {
      if (!_isRecording || !_isPaused) {
        _logger.w('Cannot resume - not paused');
        return false;
      }

      await _recorder.resume();
      _isPaused = false;
      _startDurationTimer();

      _logger.i('Recording resumed');
      return true;

    } catch (e) {
      _logger.e('Error resuming recording: $e');
      return false;
    }
  }

  /// Cancel recording and delete the file
  Future<void> cancelRecording() async {
    try {
      if (_isRecording) {
        await _recorder.stop();
        _isRecording = false;
        _isPaused = false;
        _recordingStartTime = null;
        _recordingStateController.add(false);
        _stopDurationTimer();
      }

      // Delete the recording file
      if (_currentRecordingFile != null && await _currentRecordingFile!.exists()) {
        await _currentRecordingFile!.delete();
        _logger.i('Recording file deleted');
      }

      _currentRecordingFile = null;
      _logger.i('Recording cancelled');

    } catch (e) {
      _logger.e('Error cancelling recording: $e');
    }
  }

  /// Check if recording duration exceeds maximum
  bool hasExceededMaxDuration() {
    if (_recordingStartTime == null) return false;
    final duration = DateTime.now().difference(_recordingStartTime!);
    return duration.inSeconds >= maxDurationSeconds;
  }

  /// Get remaining recording time in seconds
  int getRemainingSeconds() {
    if (_recordingStartTime == null) return maxDurationSeconds;
    final elapsed = DateTime.now().difference(_recordingStartTime!).inSeconds;
    return maxDurationSeconds - elapsed;
  }

  /// Start duration timer for real-time updates
  void _startDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_recordingStartTime != null) {
        final duration = DateTime.now().difference(_recordingStartTime!);
        _durationController.add(duration);

        // Auto-stop if max duration reached
        if (duration.inSeconds >= maxDurationSeconds) {
          _logger.w('Max recording duration reached, stopping automatically');
          stopRecording();
          timer.cancel();
        }
      }
    });
  }

  /// Stop duration timer
  void _stopDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
  }

  /// Start amplitude monitoring for visual feedback
  void _startAmplitudeMonitoring() {
    Timer.periodic(const Duration(milliseconds: 100), (timer) async {
      if (!_isRecording || _isPaused) {
        timer.cancel();
        return;
      }

      try {
        final amplitude = await _recorder.getAmplitude();
        final normalizedAmplitude = amplitude.current.clamp(-50.0, 0.0);
        final percentage = (normalizedAmplitude + 50.0) / 50.0;
        _amplitudeController.add(percentage);
      } catch (e) {
        // Ignore amplitude errors
      }
    });
  }

  /// Dispose resources
  void dispose() {
    _durationTimer?.cancel();
    _durationController.close();
    _recordingStateController.close();
    _amplitudeController.close();
    _recorder.dispose();
    _logger.i('Audio service disposed');
  }
}

/// Result of a recording operation
class RecordingResult {
  final bool success;
  final String? filePath;
  final String? error;
  final int? fileSize;

  RecordingResult._({
    required this.success,
    this.filePath,
    this.error,
    this.fileSize,
  });

  factory RecordingResult.success(String filePath, {int? fileSize}) {
    return RecordingResult._(
      success: true,
      filePath: filePath,
      fileSize: fileSize,
    );
  }

  factory RecordingResult.error(String error) {
    return RecordingResult._(
      success: false,
      error: error,
    );
  }

  @override
  String toString() {
    if (success) {
      return 'RecordingResult(success: true, filePath: $filePath, fileSize: $fileSize)';
    } else {
      return 'RecordingResult(success: false, error: $error)';
    }
  }
}
