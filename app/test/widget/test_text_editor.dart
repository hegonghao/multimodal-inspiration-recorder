import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'package:multimodal_inspiration_recorder/presentation/widgets/text_editor.dart';
import 'package:multimodal_inspiration_recorder/core/constants.dart';

void main() {
  group('TextEditorWidget Tests', () {
    testWidgets('renders correctly with initial state', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      // Assert - key UI elements
      expect(find.text('在此输入您的灵感...'), findsOneWidget);
      expect(find.text('0 / ${TextConstants.maxContentLength}'), findsOneWidget);
      expect(find.text('开始输入以记录您的灵感'), findsOneWidget);
    });

    testWidgets('displays character counter correctly', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      // Act - type some text
      await tester.enterText(
        find.byType(TextField),
        '测试内容',
      );
      await tester.pump();

      // Assert - counter updates
      expect(find.textContaining('4 / ${TextConstants.maxContentLength}'), findsOneWidget);
    });

    testWidgets('shows validation message when below minimum', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              minLength: 10,
            ),
          ),
        ),
      );

      // Act - type short text (5 characters)
      await tester.enterText(find.byType(TextField), '五个字符');
      await tester.pump();

      // Assert - shows remaining characters message
      expect(find.textContaining('还需输入至少'), findsOneWidget);
      expect(find.textContaining('个字符'), findsOneWidget);
    });

    testWidgets('shows validation icon for valid text', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              minLength: 10,
            ),
          ),
        ),
      );

      // Act - type valid text (>10 characters)
      await tester.enterText(find.byType(TextField), '这是一段足够长的有效文本内容');
      await tester.pump();

      // Assert - check icon present (valid)
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    });

    testWidgets('shows info icon for invalid text', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              minLength: 10,
            ),
          ),
        ),
      );

      // Act - type short text
      await tester.enterText(find.byType(TextField), '短文本');
      await tester.pump();

      // Assert - info icon shown
      expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);
    });

    testWidgets('calls onTextChanged callback', (WidgetTester tester) async {
      // Arrange
      String? changedText;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              onTextChanged: (text) {
                changedText = text;
              },
            ),
          ),
        ),
      );

      // Act - type text
      const testText = '测试回调';
      await tester.enterText(find.byType(TextField), testText);
      await tester.pump();

      // Assert - callback called
      expect(changedText, testText);
    });

    testWidgets('shows clear button when text is entered', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      // Initially no clear button
      expect(find.byIcon(Icons.clear_rounded), findsNothing);

      // Act - type text
      await tester.enterText(find.byType(TextField), '测试内容');
      await tester.pump();

      // Assert - clear button appears
      expect(find.byIcon(Icons.clear_rounded), findsOneWidget);
    });

    testWidgets('clear button shows confirmation dialog', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '测试内容');
      await tester.pump();

      // Act - tap clear button
      await tester.tap(find.byIcon(Icons.clear_rounded));
      await tester.pumpAndSettle();

      // Assert - confirmation dialog appears
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('清空内容'), findsOneWidget);
      expect(find.text('确定要清空所有内容吗？此操作无法撤销。'), findsOneWidget);
    });

    testWidgets('clear button clears text after confirmation', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '测试内容');
      await tester.pump();

      // Act - tap clear button
      await tester.tap(find.byIcon(Icons.clear_rounded));
      await tester.pumpAndSettle();

      // Confirm
      await tester.tap(find.text('清空'));
      await tester.pumpAndSettle();

      // Assert - text is cleared
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.controller?.text, isEmpty);
    });

    testWidgets('cancel button in clear dialog keeps text', (WidgetTester tester) async {
      // Arrange
      const testText = '测试内容';
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), testText);
      await tester.pump();

      // Act - tap clear button
      await tester.tap(find.byIcon(Icons.clear_rounded));
      await tester.pumpAndSettle();

      // Cancel
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();

      // Assert - text is not cleared
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.controller?.text, testText);
    });

    testWidgets('displays initial text when provided', (WidgetTester tester) async {
      // Arrange & Act
      const initialText = '初始文本内容';
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              initialText: initialText,
            ),
          ),
        ),
      );

      // Assert - initial text is displayed
      expect(find.text(initialText), findsOneWidget);
    });

    testWidgets('shows warning when approaching maximum length', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              maxLength: 100,
            ),
          ),
        ),
      );

      // Act - type text close to max (95 characters)
      final longText = '测' * 95;
      await tester.enterText(find.byType(TextField), longText);
      await tester.pump();

      // Assert - counter should show warning color (orange)
      // Counter should display "95 / 100"
      expect(find.textContaining('95 / 100'), findsOneWidget);
    });

    testWidgets('read-only mode disables editing', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              initialText: '只读内容',
              readOnly: true,
            ),
          ),
        ),
      );

      // Assert - text field is read-only
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.readOnly, true);

      // Clear button should not appear in read-only mode
      expect(find.byIcon(Icons.clear_rounded), findsNothing);
    });

    testWidgets('handles multi-line text correctly', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(),
          ),
        ),
      );

      // Act - enter multi-line text
      const multiLineText = '第一行\n第二行\n第三行';
      await tester.enterText(find.byType(TextField), multiLineText);
      await tester.pump();

      // Assert - text with newlines is preserved
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.controller?.text, multiLineText);
    });

    testWidgets('shows correct validation message for maximum exceeded', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              maxLength: 20,
            ),
          ),
        ),
      );

      // Act - type text exceeding max
      final tooLongText = '测' * 25;  // 25 characters, max is 20
      await tester.enterText(find.byType(TextField), tooLongText);
      await tester.pump();

      // Assert - shows exceeded message
      expect(find.textContaining('已超出最大长度'), findsOneWidget);
      expect(find.textContaining('个字符'), findsOneWidget);
    });
  });

  group('CompactTextEditorButton Tests', () {
    testWidgets('renders correctly', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactTextEditorButton(
              onPressed: () {},
            ),
          ),
        ),
      );

      // Assert
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.edit_note_rounded), findsOneWidget);
    });

    testWidgets('calls onPressed when tapped', (WidgetTester tester) async {
      // Arrange
      bool pressed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactTextEditorButton(
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

    testWidgets('has correct tooltip', (WidgetTester tester) async {
      // Arrange & Act
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompactTextEditorButton(
              onPressed: () {},
            ),
          ),
        ),
      );

      // Assert - tooltip is set
      final fab = tester.widget<FloatingActionButton>(find.byType(FloatingActionButton));
      expect(fab.tooltip, '文字输入');
    });
  });

  group('TextEditorWidget Integration Tests', () {
    testWidgets('validation state changes as user types', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TextEditorWidget(
              minLength: 10,
            ),
          ),
        ),
      );

      // Act & Assert - type progressively

      // 1. Empty - info icon
      expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);

      // 2. Type short text - still invalid
      await tester.enterText(find.byType(TextField), '短文本');
      await tester.pump();
      expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);
      expect(find.textContaining('还需输入至少'), findsOneWidget);

      // 3. Type more to reach minimum - becomes valid
      await tester.enterText(find.byType(TextField), '这是一段足够长的有效文本');
      await tester.pump();
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    });
  });
}
