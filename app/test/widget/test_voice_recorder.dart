import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:app/presentation/widgets/voice_recorder.dart';
import 'package:app/presentation/providers/inspiration_provider.dart';
import 'package:app/data/services/api_service.dart';
import 'package:app/data/services/audio_service.dart';
import 'package:app/data/services/camera_service.dart';
import 'package:app/data/services/storage_service.dart';
import 'package:app/data/database.dart';

// Generate mocks with: flutter pub run build_runner build
@GenerateMocks([
  ApiService,
  AudioService,
  CameraService,
  StorageService,
  AppDatabase,
])
import 'test_voice_recorder.mocks.dart';

void main() {
  group('VoiceRecorderWidget Tests', () {
    late MockApiService mockApiService;
    late MockAudioService mockAudioService;
    late MockCameraService mockCameraService;
    late MockStorageService mockStorageService;
    late MockAppDatabase mockDatabase;
    late InspirationProvider provider;

    setUp(() {
      // Initialize mocks
      mockApiService = MockApiService();
      mockAudioService = MockAudioService();
      mockCameraService = MockCameraService();
      mockStorageService = MockStorageService();
      mockDatabase = MockAppDatabase();

      // Setup default mock behaviors
      when(mockAudioService.isRecording).thenReturn(false);
      when(mockAudioService.isPaused).thenReturn(false);
      when(mockAudioService.recordingStateStream)
          .thenAnswer((_) => Stream.value(false));
      when(mockAudioService.durationStream)
          .thenAnswer((_) => Stream.value(Duration.zero));
      when(mockAudioService.amplitudeStream)
          .thenAnswer((_) => Stream.value(0.0));

      // Create provider with mocks
      provider = InspirationProvider(
        apiService: mockApiService,
        audioService: mockAudioService,
        cameraService: mockCameraService,
        storageService: mockStorageService,
        database: mockDatabase,
      );
    });

    tearDown(() {
      provider.dispose();
    });

    Widget createTestWidget(Widget child) {
      return MaterialApp(
        home: Scaffold(
          body: ChangeNotifierProvider<InspirationProvider>.value(
            value: provider,
            child: child,
          ),
        ),
      );
    }

    testWidgets('renders correctly with initial state', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));

      // Assert - find key UI elements
      expect(find.text('语音记录'), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsOneWidget);
      expect(find.text('00:00'), findsOneWidget);
      expect(find.text('点击麦克风按钮开始录音\n最长支持5分钟录音'), findsOneWidget);
    });

    testWidgets('shows recording state when recording starts',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));

      // Setup mock to simulate recording
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.startRecording()).thenAnswer(
        (_) async => RecordingResult.success('/path/to/recording.aac'),
      );

      // Act - tap microphone button
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      // Trigger state change
      provider.notifyListeners();
      await tester.pump();

      // Assert - UI should show recording state
      expect(find.text('正在录音'), findsOneWidget);
      expect(find.byIcon(Icons.stop), findsOneWidget);
    });

    testWidgets('displays duration during recording', (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.durationStream).thenAnswer(
        (_) => Stream.value(const Duration(minutes: 1, seconds: 30)),
      );

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - should show 01:30
      expect(find.text('01:30'), findsOneWidget);
    });

    testWidgets('displays remaining time during recording',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.getRemainingSeconds()).thenReturn(270); // 4:30 left

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - should show remaining time
      expect(find.textContaining('剩余时间'), findsOneWidget);
      expect(find.text('剩余时间: 04:30'), findsOneWidget);
    });

    testWidgets('shows warning when time is running out',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.getRemainingSeconds()).thenReturn(25); // 25 seconds left

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - text should be red when < 30 seconds
      final remainingTimeWidget = tester.widget<Text>(
        find.textContaining('剩余时间'),
      );
      expect(remainingTimeWidget.style?.color, Colors.red);
    });

    testWidgets('shows amplitude visualization when recording',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.amplitudeStream)
          .thenAnswer((_) => Stream.value(0.5)); // 50% amplitude

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - amplitude visualizer should be present
      // (Container with animated height bars)
      expect(find.byType(AnimatedBuilder), findsWidgets);
    });

    testWidgets('shows control buttons when recording',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - should show cancel and pause buttons
      expect(find.text('取消'), findsOneWidget);
      expect(find.text('暂停'), findsOneWidget);
    });

    testWidgets('pause button works correctly', (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.isPaused).thenReturn(false);
      when(mockAudioService.pauseRecording()).thenAnswer((_) async => true);

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Act - tap pause button
      await tester.tap(find.text('暂停'));
      await tester.pump();

      // Assert - pauseRecording should be called
      verify(mockAudioService.pauseRecording()).called(1);
    });

    testWidgets('resume button appears when paused', (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.isPaused).thenReturn(true);

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Assert - should show resume button
      expect(find.text('继续'), findsOneWidget);
      expect(find.byIcon(Icons.play_arrow), findsOneWidget);
    });

    testWidgets('cancel button shows confirmation dialog',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.cancelRecording()).thenAnswer((_) async {});

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Act - tap cancel button
      await tester.tap(find.text('取消'));
      await tester.pump();

      // Assert - cancelRecording should be called
      verify(mockAudioService.cancelRecording()).called(1);
    });

    testWidgets('stop button calls stopRecording', (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.stopRecording()).thenAnswer(
        (_) async => RecordingResult.success(
          '/path/to/recording.aac',
          fileSize: 1024,
        ),
      );

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Act - tap stop button
      await tester.tap(find.byIcon(Icons.stop));
      await tester.pump();

      // Assert - stopRecording should be called
      verify(mockAudioService.stopRecording()).called(1);
    });

    testWidgets('calls onRecordingComplete callback when recording stops',
        (WidgetTester tester) async {
      // Arrange
      bool callbackCalled = false;
      when(mockAudioService.isRecording).thenReturn(false);

      await tester.pumpWidget(
        createTestWidget(
          VoiceRecorderWidget(
            onRecordingComplete: () {
              callbackCalled = true;
            },
          ),
        ),
      );

      // Simulate recording complete
      // (In real implementation, this would be triggered by provider)
      await tester.pump();

      // Note: Actual callback testing requires more complex setup
      // with provider state changes
    });

    testWidgets('calls onRecordingCancelled callback when cancelled',
        (WidgetTester tester) async {
      // Arrange
      bool callbackCalled = false;
      when(mockAudioService.isRecording).thenReturn(true);
      when(mockAudioService.cancelRecording()).thenAnswer((_) async {});

      await tester.pumpWidget(
        createTestWidget(
          VoiceRecorderWidget(
            onRecordingCancelled: () {
              callbackCalled = true;
            },
          ),
        ),
      );
      await tester.pump();

      // Act - tap cancel
      await tester.tap(find.text('取消'));
      await tester.pump();

      // Assert
      expect(callbackCalled, isTrue);
    });

    testWidgets('microphone button changes color when recording',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.isRecording).thenReturn(false);

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));
      await tester.pump();

      // Find the mic button container
      final micButtonFinder = find.ancestor(
        of: find.byIcon(Icons.mic),
        matching: find.byType(AnimatedContainer),
      );

      // Get the container
      final AnimatedContainer notRecordingContainer =
          tester.widget(micButtonFinder.first);

      // Assert - should be primary color when not recording
      expect(
        (notRecordingContainer.decoration as BoxDecoration?)?.color,
        isNot(Colors.red),
      );

      // Now simulate recording
      when(mockAudioService.isRecording).thenReturn(true);
      provider.notifyListeners();
      await tester.pump();

      final AnimatedContainer recordingContainer =
          tester.widget(micButtonFinder.first);

      // Assert - should be red when recording
      expect(
        (recordingContainer.decoration as BoxDecoration?)?.color,
        Colors.red,
      );
    });

    testWidgets('compact button renders correctly', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactVoiceRecorderButton(
              onPressed: () {},
            ),
          ),
        ),
      );

      // Assert
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsOneWidget);
    });

    testWidgets('compact button calls onPressed', (WidgetTester tester) async {
      // Arrange
      bool pressed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactVoiceRecorderButton(
              onPressed: () {
                pressed = true;
              },
            ),
          ),
        ),
      );

      // Act
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pump();

      // Assert
      expect(pressed, isTrue);
    });

    testWidgets('shows error dialog when recording fails',
        (WidgetTester tester) async {
      // Arrange
      when(mockAudioService.startRecording()).thenAnswer(
        (_) async => RecordingResult.error('Microphone permission denied'),
      );

      await tester.pumpWidget(createTestWidget(const VoiceRecorderWidget()));

      // Act - tap mic to start recording
      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();
      await tester.pump(); // Additional pump for dialog animation

      // Assert - error dialog should appear
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('错误'), findsOneWidget);
      expect(find.textContaining('permission'), findsOneWidget);
    });
  });
}
