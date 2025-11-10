# Flutter Widget Tests

## Overview

Widget tests for the multimodal inspiration recorder Flutter app.

## Test Structure

```
app/test/
├── widget/
│   ├── test_voice_recorder.dart     # Voice recorder widget tests (T024)
│   ├── test_image_picker.dart       # Image picker widget tests (T039)
│   └── test_text_editor.dart        # Text editor widget tests (T051)
└── widget_test_readme.md            # This file
```

## Prerequisites

### Install Dependencies

Add to `pubspec.yaml` dev_dependencies:

```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  mockito: ^5.4.0
  build_runner: ^2.4.0
```

### Install Packages

```bash
cd app
flutter pub get
```

### Generate Mocks

```bash
flutter pub run build_runner build
```

This generates `*.mocks.dart` files for test mocks.

## Running Tests

### Run All Tests

```bash
# Run all widget tests
flutter test

# Run with coverage
flutter test --coverage

# Generate coverage report
genhtml coverage/lcov.info -o coverage/html
```

### Run Specific Tests

```bash
# Run voice recorder tests
flutter test test/widget/test_voice_recorder.dart

# Run image picker tests
flutter test test/widget/test_image_picker.dart

# Run text editor tests
flutter test test/widget/test_text_editor.dart

# Run specific test
flutter test test/widget/test_voice_recorder.dart --name "renders correctly"
```

### Run in Watch Mode

```bash
# Auto-run tests on file changes
flutter test --watch
```

## Test Coverage

### T024: Voice Recorder Widget Tests ✅

**Tested Scenarios:**
- ✅ Initial render with default state
- ✅ Recording state transition (mic → stop icon)
- ✅ Duration display (MM:SS format)
- ✅ Remaining time countdown
- ✅ Warning when time < 30 seconds (red text)
- ✅ Amplitude visualization (animated bars)
- ✅ Control buttons (pause/cancel) appear when recording
- ✅ Pause button functionality
- ✅ Resume button when paused
- ✅ Cancel button clears recording
- ✅ Stop button ends recording
- ✅ Callbacks (onRecordingComplete, onRecordingCancelled)
- ✅ Microphone button color changes (blue → red)
- ✅ Compact button variant
- ✅ Error dialog on permission denial

**Test Count:** 18 tests

### T039: Image Picker Widget Tests ✅

**Tested Scenarios:**
- ✅ Initial render with placeholder
- ✅ Camera button calls takePhoto
- ✅ Gallery button calls pickImage
- ✅ Loading indicator during selection
- ✅ Image preview after selection (documented)
- ✅ Clear button removes image
- ✅ Action buttons after selection
- ✅ Retake functionality
- ✅ Use image callback
- ✅ Error dialog on camera permission denial
- ✅ Error dialog on gallery access failure
- ✅ User cancellation handling
- ✅ File size display
- ✅ Compact button variant
- ✅ ImagePreviewCard component

**Test Count:** 15 tests

### T051: Text Editor Widget Tests ✅

**Tested Scenarios:**
- ✅ Initial render with default state
- ✅ Character counter display (X / 10,000)
- ✅ Validation message when below minimum (10 chars)
- ✅ Validation icon changes (check vs info)
- ✅ Text change callback
- ✅ Auto-save after delay (2 seconds)
- ✅ Unsaved changes indicator with spinner
- ✅ Auto-save skips invalid text
- ✅ Clear button appears when text entered
- ✅ Clear button confirmation dialog
- ✅ Clear button clears text after confirmation
- ✅ Cancel in clear dialog keeps text
- ✅ Initial text display
- ✅ Warning color when approaching maximum
- ✅ Read-only mode disables editing
- ✅ Multi-line text handling
- ✅ Maximum exceeded validation message
- ✅ Auto-save message during countdown
- ✅ CompactTextEditorButton renders correctly
- ✅ CompactTextEditorButton calls onPressed
- ✅ CompactTextEditorButton has correct tooltip
- ✅ Complete workflow integration test
- ✅ Validation state changes as user types

**Test Count:** 27 tests

## Mocking Strategy

### Provider Mocking

```dart
late MockAudioService mockAudioService;

setUp(() {
  mockAudioService = MockAudioService();

  // Setup default behaviors
  when(mockAudioService.isRecording).thenReturn(false);
  when(mockAudioService.recordingStateStream)
      .thenAnswer((_) => Stream.value(false));
});
```

### File Mocking

Note: File system operations are challenging in widget tests. The tests document expected behavior for scenarios requiring actual files.

For full file testing:
1. Use `flutter_test` package features
2. Create temporary test files
3. Mock `File` class if needed

## Limitations & Notes

### Current Limitations

1. **File System Access**
   - Some tests document expected behavior rather than fully testing
   - Requires mock File implementation for complete coverage

2. **Image Rendering**
   - Image.file widget testing requires actual image files
   - Consider using test assets or base64 encoded images

3. **Platform-Specific Features**
   - Camera and permission tests use mocks
   - Real device testing recommended for full validation

### Deferred Tests

Some complex scenarios are documented but not fully implemented:
- Image preview rendering
- File metadata display
- Long filename truncation
- ImagePreviewCard full integration

These can be completed with:
- Test image assets
- Mock file system
- Integration tests on real devices

## Best Practices

### 1. Test Structure

```dart
testWidgets('descriptive test name', (WidgetTester tester) async {
  // Arrange - setup mocks and state

  // Act - perform action

  // Assert - verify results
});
```

### 2. Pump and Settle

```dart
await tester.pump();        // Single frame
await tester.pumpAndSettle(); // All frames until settled
```

### 3. Finder Usage

```dart
find.text('Button Text')
find.byIcon(Icons.mic)
find.byType(CircularProgressIndicator)
find.ancestor(of: finder1, matching: finder2)
```

### 4. Verification

```dart
expect(find.text('Expected'), findsOneWidget);
expect(find.byType(AlertDialog), findsNothing);
verify(mockService.method()).called(1);
```

## Debugging Tests

### Print Widget Tree

```dart
debugDumpApp(); // Print widget tree
debugDumpRenderTree(); // Print render tree
```

### Print Semantics

```dart
debugDumpSemanticsTree(); // Print semantics tree
```

### Run Single Test with Verbose Output

```bash
flutter test --verbose test/widget/test_voice_recorder.dart
```

## Code Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
flutter test --coverage

# Install lcov (if not installed)
# Mac: brew install lcov
# Ubuntu: sudo apt-get install lcov
# Windows: use WSL or download from http://ltp.sourceforge.net/coverage/lcov.php

# Generate HTML report
genhtml coverage/lcov.info -o coverage/html

# Open report
open coverage/html/index.html  # Mac
start coverage/html/index.html # Windows
```

### Coverage Goals

| Component | Target | Status |
|-----------|--------|--------|
| Widgets | 80% | ✅ Core tests |
| Pages | 70% | ⏸️ Deferred |
| Providers | 75% | ⏸️ Integration tests |
| Services | 70% | ✅ Mocked in widget tests |

## Continuous Integration

### GitHub Actions Example

```yaml
name: Flutter Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'

      - name: Install dependencies
        run: flutter pub get
        working-directory: ./app

      - name: Generate mocks
        run: flutter pub run build_runner build
        working-directory: ./app

      - name: Run tests
        run: flutter test --coverage
        working-directory: ./app

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./app/coverage/lcov.info
```

## Troubleshooting

### Issue: Mock Generation Fails

```bash
# Clean and regenerate
flutter pub run build_runner clean
flutter pub run build_runner build --delete-conflicting-outputs
```

### Issue: Tests Timeout

```bash
# Increase timeout
flutter test --timeout=2m
```

### Issue: Widget Not Found

```dart
// Use pumpAndSettle for animations
await tester.pumpAndSettle();

// Or pump specific duration
await tester.pump(Duration(seconds: 1));
```

## Next Steps

- [ ] Add integration tests for complete user flows
- [ ] Add golden tests for UI regression
- [ ] Implement full file system mocking
- [ ] Add performance tests
- [ ] Setup CI/CD pipeline
- [ ] Add screenshot tests

## References

- [Flutter Testing Documentation](https://docs.flutter.dev/testing)
- [Widget Testing Guide](https://docs.flutter.dev/cookbook/testing/widget/introduction)
- [Mockito Documentation](https://pub.dev/packages/mockito)
- [flutter_test Package](https://api.flutter.dev/flutter/flutter_test/flutter_test-library.html)
