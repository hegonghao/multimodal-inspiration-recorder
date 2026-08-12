/// Text input page for direct text entry with AI summarization.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants.dart';
import '../../core/themes.dart';
import '../providers/inspiration_provider.dart';
import '../widgets/text_editor.dart';
import '../widgets/common/loading_indicator.dart';

/// TextInputPage provides direct text input interface
///
/// Features:
/// - Rich text editing with validation
/// - Auto-save after user stops typing
/// - AI-powered summary and abstract generation
/// - Character counter with validation feedback
/// - Save/discard actions
///
/// Corresponds to User Story 3: Text Input
class TextInputPage extends StatefulWidget {
  const TextInputPage({super.key});

  @override
  State<TextInputPage> createState() => _TextInputPageState();
}

class _TextInputPageState extends State<TextInputPage> {
  String _currentText = '';
  bool _isProcessing = false;
  bool _hasProcessedResult = false;
  String? _errorMessage;

  // AI processing results
  String? _generatedTitle;
  String? _summary;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('文字输入'),
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline_rounded),
            tooltip: '帮助',
            onPressed: _showHelpDialog,
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(UIConstants.paddingMedium),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Instructions
              _buildInstructions(),

              const SizedBox(height: UIConstants.paddingMedium),

              // Scrollable content area with flexible text editor
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Text editor with minimum height
                      ConstrainedBox(
                        constraints: BoxConstraints(
                          minHeight: 200,
                          maxHeight: MediaQuery.of(context).size.height * 0.4,
                        ),
                        child: TextEditorWidget(
                          initialText: _currentText,
                          onTextChanged: _onTextChanged,
                          placeholder: '输入您的灵感、想法或笔记...\n\n系统将自动生成总结和摘要。',
                        ),
                      ),

                      const SizedBox(height: UIConstants.paddingMedium),

                      // Processing indicator or results
                      if (_isProcessing)
                        _buildProcessingIndicator()
                      else if (_hasProcessedResult)
                        _buildResults()
                      else if (_errorMessage != null)
                        _buildErrorMessage(),

                      const SizedBox(height: UIConstants.paddingMedium),
                    ],
                  ),
                ),
              ),

              // Action buttons (fixed at bottom)
              _buildActionButtons(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInstructions() {
    return Container(
      padding: const EdgeInsets.all(UIConstants.paddingMedium),
      decoration: BoxDecoration(
        color: AppColors.textBackground,
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusMedium),
      ),
      child: Row(
        children: [
          Icon(
            Icons.lightbulb_outline_rounded,
            color: AppColors.textActive,
            size: UIConstants.iconSizeLarge,
          ),
          const SizedBox(width: UIConstants.paddingMedium),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '直接输入文字',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.textActive,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  '输入至少10个字符，系统将自动生成总结和摘要',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textActive.withOpacity(0.8),
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProcessingIndicator() {
    return Container(
      padding: const EdgeInsets.all(UIConstants.paddingMedium),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusMedium),
      ),
      child: LoadingIndicator(
        style: LoadingStyle.dots,
        size: 40.0,
        message: '正在分析内容...\n正在生成总结和摘要',
      ),
    );
  }

  Widget _buildResults() {
    return Container(
      padding: const EdgeInsets.all(UIConstants.paddingMedium),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusMedium),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.auto_awesome_rounded,
                size: UIConstants.iconSizeSmall,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'AI 分析结果',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),

          const SizedBox(height: UIConstants.paddingSmall),

          if (_generatedTitle != null && _generatedTitle!.isNotEmpty) ...[
            Text(
              '总结',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.6),
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              _generatedTitle!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: UIConstants.paddingSmall),
          ],

          if (_summary != null && _summary!.isNotEmpty) ...[
            Text(
              '摘要',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.6),
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              _summary!,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorMessage() {
    return Container(
      padding: const EdgeInsets.all(UIConstants.paddingMedium),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusMedium),
      ),
      child: Row(
        children: [
          Icon(
            Icons.error_outline_rounded,
            color: Theme.of(context).colorScheme.error,
            size: UIConstants.iconSizeMedium,
          ),
          const SizedBox(width: UIConstants.paddingMedium),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '处理失败',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.error,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  _errorMessage!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.error,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    final provider = context.watch<InspirationProvider>();
    final canSave =
        _currentText.trim().length >= TextConstants.minContentLength &&
            _currentText.trim().length <= TextConstants.maxContentLength;

    return Row(
      children: [
        // Discard button
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _onDiscard,
            icon: const Icon(Icons.delete_outline_rounded),
            label: const Text('丢弃'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
          ),
        ),

        const SizedBox(width: UIConstants.paddingMedium),

        // Process/Save button with loading state
        Expanded(
          flex: 2,
          child: LoadingButton(
            onPressed: canSave && !_isProcessing && !provider.isLoading
                ? _onProcessAndSave
                : null,
            isLoading: _isProcessing || provider.isLoading,
            loadingSize: 20.0,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  _hasProcessedResult
                      ? Icons.save_rounded
                      : Icons.auto_awesome_rounded,
                ),
                const SizedBox(width: 8),
                Text(_hasProcessedResult ? '保存记录' : '分析并保存'),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // Event handlers
  void _onTextChanged(String text) {
    setState(() {
      final contentChanged = text != _currentText;
      _currentText = text;
      if (_hasProcessedResult && contentChanged) {
        _hasProcessedResult = false;
        _generatedTitle = null;
        _summary = null;
      }
    });
  }

  Future<void> _onProcessAndSave() async {
    final provider = context.read<InspirationProvider>();

    // Validate text
    final trimmedText = _currentText.trim();
    if (trimmedText.length < TextConstants.minContentLength) {
      _showError('内容过短，请输入至少${TextConstants.minContentLength}个字符');
      return;
    }

    if (trimmedText.length > TextConstants.maxContentLength) {
      _showError('内容过长，请控制在${TextConstants.maxContentLength}个字符以内');
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      // Create text record with AI processing
      final success = await provider.createTextRecord(
        content: trimmedText,
        language: 'zh',
        autoProcess: true,
      );

      if (success && mounted) {
        setState(() {
          _isProcessing = false;

          // Extract AI results from the last created record
          if (provider.records.isNotEmpty) {
            final record = provider.records.first;
            final aiStatus = record.aiProcessingStatus;

            // AI processing states: 0=PENDING, 1=FAILED, 2=COMPLETED
            if (aiStatus == 2) {
              // AI processing completed successfully
              _hasProcessedResult = true;
              _generatedTitle = record.title;
              _summary = record.summary;
            } else if (aiStatus == 1) {
              // AI processing failed
              _hasProcessedResult = false;
              _errorMessage =
                  'AI分析失败: ${record.aiErrorMessage ?? "未知错误"}。记录已保存，但未生成总结和摘要。';
            } else {
              // AI processing still pending (shouldn't happen after sync)
              _hasProcessedResult = false;
              _errorMessage = 'AI分析超时。记录已保存，总结和摘要可能需要稍后查看。';
            }
          }
        });

        // Show success message based on AI processing status
        if (mounted) {
          final aiSucceeded = provider.records.isNotEmpty &&
              provider.records.first.aiProcessingStatus == 2;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(aiSucceeded ? '✓ 记录已保存并分析完成' : '✓ 记录已保存（AI分析未完成）'),
              backgroundColor: aiSucceeded
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.error,
              duration: const Duration(seconds: 3),
            ),
          );

          // Only navigate back if AI succeeded or wait for user acknowledgment
          if (aiSucceeded) {
            await Future.delayed(const Duration(seconds: 2));
            if (mounted) {
              Navigator.pop(context);
            }
          }
          // If AI failed, stay on page to let user see error message
        }
      } else if (mounted) {
        setState(() {
          _isProcessing = false;
          _errorMessage = provider.error ?? '保存失败，请重试';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isProcessing = false;
          _errorMessage = '处理失败: ${e.toString()}';
        });
      }
    }
  }

  void _onDiscard() {
    if (_currentText.trim().isEmpty) {
      Navigator.pop(context);
      return;
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('丢弃内容'),
        content: const Text('确定要丢弃当前内容吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Close page
            },
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('丢弃'),
          ),
        ],
      ),
    );
  }

  void _showError(String message) {
    setState(() {
      _errorMessage = message;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }

  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('使用帮助'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildHelpItem(
                icon: Icons.edit_rounded,
                title: '输入文字',
                description: '在编辑框中输入您的灵感、想法或笔记',
              ),
              const SizedBox(height: 12),
              _buildHelpItem(
                icon: Icons.auto_awesome_rounded,
                title: 'AI 分析',
                description: '系统自动生成简短总结和摘要，帮助您整理内容',
              ),
              const SizedBox(height: 12),
              _buildHelpItem(
                icon: Icons.save_rounded,
                title: '保存记录',
                description: '内容会保存到本地，并自动同步到云端',
              ),
              const SizedBox(height: 12),
              _buildHelpItem(
                icon: Icons.info_outline_rounded,
                title: '最低要求',
                description: '至少输入${TextConstants.minContentLength}个字符才能保存',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  Widget _buildHelpItem({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: UIConstants.iconSizeMedium,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
