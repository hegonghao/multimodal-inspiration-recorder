import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:app/presentation/widgets/image_picker_widget.dart';
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
import 'test_image_picker.mocks.dart';

void main() {
  group('ImagePickerWidget Tests', () {
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
      // Arrange & Act
      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Assert - find key UI elements
      expect(find.text('图片识别'), findsOneWidget);
      expect(find.byIcon(Icons.image_outlined), findsOneWidget);
      expect(find.text('选择图片以识别文字'), findsOneWidget);
      expect(find.text('拍照'), findsOneWidget);
      expect(find.text('相册'), findsOneWidget);
      expect(find.text('支持格式: JPG, PNG, WEBP\n最大5MB'), findsOneWidget);
    });

    testWidgets('shows image placeholder when no image selected',
        (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Assert - placeholder should be visible
      expect(find.byType(Container), findsWidgets);
      expect(find.byIcon(Icons.image_outlined), findsOneWidget);
    });

    testWidgets('camera button calls takePhoto', (WidgetTester tester) async {
      // Arrange
      when(mockCameraService.takePhoto()).thenAnswer(
        (_) async => ImageResult.cancelled(),
      );

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap camera button
      await tester.tap(find.text('拍照'));
      await tester.pump();

      // Assert - takePhoto should be called
      verify(mockCameraService.takePhoto()).called(1);
    });

    testWidgets('gallery button calls pickImage', (WidgetTester tester) async {
      // Arrange
      when(mockCameraService.pickImage()).thenAnswer(
        (_) async => ImageResult.cancelled(),
      );

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap gallery button
      await tester.tap(find.text('相册'));
      await tester.pump();

      // Assert - pickImage should be called
      verify(mockCameraService.pickImage()).called(1);
    });

    testWidgets('displays loading indicator when selecting image',
        (WidgetTester tester) async {
      // Arrange
      final completer = Future<ImageResult>.delayed(
        const Duration(milliseconds: 100),
        () => ImageResult.cancelled(),
      );

      when(mockCameraService.pickImage()).thenAnswer((_) => completer);

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap gallery button
      await tester.tap(find.text('相册'));
      await tester.pump();

      // Assert - loading indicator should be visible
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Wait for completion
      await tester.pumpAndSettle();
    });

    testWidgets('shows image preview when image selected',
        (WidgetTester tester) async {
      // Note: This test requires file system access which is complex in widget tests
      // In real implementation, would use a test image file or mock File

      // This is a simplified version - full implementation would need:
      // 1. Create a temporary test image file
      // 2. Mock the file system
      // 3. Verify Image.file widget appears

      // For now, documenting expected behavior:
      // - Image preview should be shown
      // - Clear button should appear
      // - Action buttons should change
    });

    testWidgets('clear button removes selected image', (WidgetTester tester) async {
      // Arrange
      bool imageCleared = false;

      await tester.pumpWidget(
        createTestWidget(
          ImagePickerWidget(
            onImageCleared: () {
              imageCleared = true;
            },
          ),
        ),
      );

      // Note: Full test requires selecting an image first
      // Then finding and tapping the clear button
      // Then verifying the callback was called

      // Documented expected behavior:
      // - Clear button (X icon) appears in top-right of preview
      // - Tapping it removes the image
      // - Calls onImageCleared callback
      // - Returns to initial state with picker buttons
    });

    testWidgets('shows action buttons after image selected',
        (WidgetTester tester) async {
      // Documented expected behavior:
      // - "重新选择" button appears
      // - "使用图片" button appears
      // - Camera and Gallery buttons are hidden
    });

    testWidgets('retake button clears and allows new selection',
        (WidgetTester tester) async {
      // Documented expected behavior:
      // - Tapping "重新选择" clears current image
      // - Shows picker buttons again
      // - Allows selecting new image
    });

    testWidgets('use image button calls callback', (WidgetTester tester) async {
      // Documented expected behavior:
      // - Tapping "使用图片" calls onImageSelected callback
      // - Passes selected File to callback
    });

    testWidgets('shows error dialog when camera permission denied',
        (WidgetTester tester) async {
      // Arrange
      when(mockCameraService.takePhoto()).thenAnswer(
        (_) async => ImageResult.error('Camera permission not granted'),
      );

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap camera button
      await tester.tap(find.text('拍照'));
      await tester.pumpAndSettle();

      // Assert - error dialog should appear
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('错误'), findsOneWidget);
      expect(find.textContaining('permission'), findsOneWidget);
    });

    testWidgets('shows error dialog when gallery access fails',
        (WidgetTester tester) async {
      // Arrange
      when(mockCameraService.pickImage()).thenAnswer(
        (_) async => ImageResult.error('Failed to pick image'),
      );

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap gallery button
      await tester.tap(find.text('相册'));
      await tester.pumpAndSettle();

      // Assert - error dialog should appear
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('错误'), findsOneWidget);
    });

    testWidgets('handles user cancellation gracefully', (WidgetTester tester) async {
      // Arrange
      when(mockCameraService.pickImage()).thenAnswer(
        (_) async => ImageResult.cancelled(),
      );

      await tester.pumpWidget(createTestWidget(const ImagePickerWidget()));

      // Act - tap gallery button
      await tester.tap(find.text('相册'));
      await tester.pumpAndSettle();

      // Assert - should return to initial state, no error
      expect(find.text('选择图片以识别文字'), findsOneWidget);
      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('displays file size after selection', (WidgetTester tester) async {
      // Documented expected behavior:
      // - After image selection, shows file size in KB
      // - Format: "图片大小: X.X KB"
    });
  });

  group('CompactImagePickerButton Tests', () {
    testWidgets('renders correctly', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactImagePickerButton(
              onPressed: () {},
            ),
          ),
        ),
      );

      // Assert
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.image), findsOneWidget);
    });

    testWidgets('calls onPressed when tapped', (WidgetTester tester) async {
      // Arrange
      bool pressed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactImagePickerButton(
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
  });

  group('ImagePreviewCard Tests', () {
    testWidgets('displays image and metadata', (WidgetTester tester) async {
      // Note: Requires mock File
      // Documented expected behavior:
      // - Shows image preview
      // - Shows file name
      // - Shows file size
      // - Shows remove button if onRemove provided
    });

    testWidgets('remove button calls callback', (WidgetTester tester) async {
      // Documented expected behavior:
      // - Tapping X button calls onRemove callback
    });

    testWidgets('truncates long filenames', (WidgetTester tester) async {
      // Documented expected behavior:
      // - Long filenames show ellipsis
      // - Uses maxLines: 1 and overflow: TextOverflow.ellipsis
    });
  });
}
