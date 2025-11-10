/// Text editor widget with validation and auto-save
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/constants.dart';

/// TextEditorWidget provides a rich text editing experience
///
/// Features:
/// - Character counter with validation
/// - Minimum/maximum length constraints
/// - Real-time validation feedback
/// - Clear button
///
/// Corresponds to User Story 3: Text Input
class TextEditorWidget extends StatefulWidget {
  const TextEditorWidget({
    super.key,
    this.initialText,
    this.onTextChanged,
    this.minLength = TextConstants.minContentLength,
    this.maxLength = TextConstants.maxContentLength,
    this.placeholder = '在此输入您的灵感...',
    this.readOnly = false,
  });

  /// Initial text content
  final String? initialText;

  /// Callback when text changes
  final ValueChanged<String>? onTextChanged;

  /// Minimum required length
  final int minLength;

  /// Maximum allowed length
  final int maxLength;

  /// Placeholder text
  final String placeholder;

  /// Whether the editor is read-only
  final bool readOnly;

  @override
  State<TextEditorWidget> createState() => _TextEditorWidgetState();
}

class _TextEditorWidgetState extends State<TextEditorWidget> {
  late TextEditingController _controller;
  late FocusNode _focusNode;
  late ValueNotifier<String> _textNotifier;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialText);
    _focusNode = FocusNode();
    _textNotifier = ValueNotifier<String>(_controller.text);

    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _textNotifier.dispose();
    super.dispose();
  }

  void _onTextChanged() {
    final text = _controller.text;

    // Notify parent of text changes
    widget.onTextChanged?.call(text);

    // Update notifier for character counter (no full widget rebuild)
    _textNotifier.value = text;
  }

  bool _isValidForSave(String text) {
    final trimmed = text.trim();
    return trimmed.length >= widget.minLength &&
        trimmed.length <= widget.maxLength;
  }

  void _clearText() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清空内容'),
        content: const Text('确定要清空所有内容吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              _controller.clear();
              Navigator.pop(context);
            },
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('清空'),
          ),
        ],
      ),
    );
  }

  Color _getCounterColorForLength(int length) {
    if (length < widget.minLength) {
      return Theme.of(context).colorScheme.error;
    } else if (length > widget.maxLength * 0.9) {
      return Colors.orange;
    } else {
      return Theme.of(context).colorScheme.onSurface.withOpacity(0.6);
    }
  }

  String _getValidationMessageForLength(int length) {
    if (length == 0) {
      return '开始输入以记录您的灵感';
    } else if (length < widget.minLength) {
      final remaining = widget.minLength - length;
      return '还需输入至少 $remaining 个字符';
    } else if (length > widget.maxLength) {
      final excess = length - widget.maxLength;
      return '已超出最大长度 $excess 个字符';
    } else {
      return '继续输入或保存内容';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Editor field
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(UIConstants.borderRadiusMedium),
              border: Border.all(
                color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
              ),
            ),
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              readOnly: widget.readOnly,
              maxLines: null,
              expands: true,
              textAlignVertical: TextAlignVertical.top,
              style: Theme.of(context).textTheme.bodyLarge,
              decoration: InputDecoration(
                hintText: widget.placeholder,
                hintStyle: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withOpacity(0.4),
                    ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.all(UIConstants.paddingMedium),
                suffixIcon: ValueListenableBuilder<String>(
                  valueListenable: _textNotifier,
                  builder: (context, text, child) {
                    return text.isNotEmpty && !widget.readOnly
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded),
                            onPressed: _clearText,
                            tooltip: '清空',
                          )
                        : const SizedBox.shrink();
                  },
                ),
              ),
            ),
          ),
        ),

        const SizedBox(height: UIConstants.paddingMedium),

        // Character counter and validation
        ValueListenableBuilder<String>(
          valueListenable: _textNotifier,
          builder: (context, text, child) {
            final length = text.trim().length;
            final isValid = _isValidForSave(text);

            return Row(
              children: [
                // Validation icon
                Icon(
                  isValid ? Icons.check_circle_rounded : Icons.info_outline_rounded,
                  size: UIConstants.iconSizeSmall,
                  color: isValid
                      ? Theme.of(context).colorScheme.primary
                      : _getCounterColorForLength(length),
                ),
                const SizedBox(width: 8),

                // Validation message
                Expanded(
                  child: Text(
                    _getValidationMessageForLength(length),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: _getCounterColorForLength(length),
                        ),
                  ),
                ),

                // Character counter
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _getCounterColorForLength(length).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(UIConstants.borderRadiusSmall),
                  ),
                  child: Text(
                    '$length / ${widget.maxLength}',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: _getCounterColorForLength(length),
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

/// Compact text editor button for quick access
class CompactTextEditorButton extends StatelessWidget {
  const CompactTextEditorButton({
    super.key,
    required this.onPressed,
  });

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton(
      onPressed: onPressed,
      tooltip: '文字输入',
      heroTag: 'text_input',
      child: const Icon(Icons.edit_note_rounded),
    );
  }
}
