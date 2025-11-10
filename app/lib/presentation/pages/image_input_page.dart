import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/inspiration_provider.dart';
import '../widgets/image_picker_widget.dart';
import '../widgets/common/loading_indicator.dart';

/// Image Input Page
///
/// Full-screen image OCR interface for capturing inspiration from images.
///
/// Features:
/// - Camera capture and gallery selection
/// - Image preview with metadata
/// - OCR text extraction with 95%+ accuracy
/// - AI categorization and summarization
/// - Manual text editing option
class ImageInputPage extends StatefulWidget {
  const ImageInputPage({Key? key}) : super(key: key);

  @override
  State<ImageInputPage> createState() => _ImageInputPageState();
}

class _ImageInputPageState extends State<ImageInputPage> {
  File? _selectedImage;
  bool _isProcessing = false;
  String _status = '';
  String? _extractedText;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('图片/文档识别'),
        centerTitle: true,
        actions: [
          // Help button
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: () => _showHelp(context),
            tooltip: '帮助',
          ),
        ],
      ),
      body: SafeArea(
        child: Consumer<InspirationProvider>(
          builder: (context, provider, child) {
            return Column(
              children: [
                // Status bar
                if (_status.isNotEmpty || provider.error != null)
                  _buildStatusBanner(context, provider),

                // Main content
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Instructions
                        if (_selectedImage == null && _extractedText == null)
                          _buildInstructions(context),

                        const SizedBox(height: 24),

                        // Image Picker Widget
                        ImagePickerWidget(
                          onImageSelected: (image) => _handleImageSelected(image),
                          onImageCleared: () => _handleImageCleared(),
                        ),

                        const SizedBox(height: 24),

                        // Processing indicator
                        if (_isProcessing || provider.isCreating)
                          _buildProcessingIndicator(context),

                        // Extracted text preview
                        if (_extractedText != null && !_isProcessing)
                          _buildExtractedTextPreview(context),

                        const SizedBox(height: 24),

                        // Action buttons
                        if (_selectedImage != null && !_isProcessing)
                          _buildActionButtons(context, provider),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  /// Build status banner (error or success message)
  Widget _buildStatusBanner(BuildContext context, InspirationProvider provider) {
    final error = provider.error;
    final isError = error != null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: isError ? Colors.red.shade100 : Colors.green.shade100,
      child: Row(
        children: [
          Icon(
            isError ? Icons.error_outline : Icons.check_circle_outline,
            color: isError ? Colors.red.shade900 : Colors.green.shade900,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              isError ? error : _status,
              style: TextStyle(
                color: isError ? Colors.red.shade900 : Colors.green.shade900,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          if (isError)
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => provider.clearError(),
              color: Colors.red.shade900,
            ),
        ],
      ),
    );
  }

  /// Build instructions card
  Widget _buildInstructions(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).primaryColor.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  color: Theme.of(context).primaryColor,
                ),
                const SizedBox(width: 8),
                Text(
                  '使用提示',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).primaryColor,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildInstructionItem('拍照、从相册选择图片或选择PDF文档'),
            _buildInstructionItem('系统会自动识别图片/PDF中的文字'),
            _buildInstructionItem('支持中英文印刷体，准确率95%+'),
            _buildInstructionItem('PDF支持多页自动识别和结构化输出'),
            _buildInstructionItem('识别后可以手动编辑文字'),
            _buildInstructionItem('系统会自动分类和生成摘要'),
          ],
        ),
      ),
    );
  }

  Widget _buildInstructionItem(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('• ', style: TextStyle(fontSize: 16)),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  /// Build processing indicator
  Widget _buildProcessingIndicator(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: LoadingIndicator(
          style: LoadingStyle.ripple,
          size: 50.0,
          message: '正在处理图片...\n正在进行文字识别和智能分类',
        ),
      ),
    );
  }

  /// Build extracted text preview card
  Widget _buildExtractedTextPreview(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '识别的文字',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  onPressed: () => _showEditTextDialog(context),
                  icon: const Icon(Icons.edit, size: 16),
                  label: const Text('编辑'),
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            Text(
              _extractedText!,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            Text(
              '字数: ${_extractedText!.length}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build action buttons (save/retry/discard)
  Widget _buildActionButtons(BuildContext context, InspirationProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Process and Save button with loading state
        LoadingButton(
          onPressed: () => _handleSaveImage(provider),
          isLoading: _isProcessing || provider.isCreating,
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.save),
              SizedBox(width: 8),
              Text('识别并保存'),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Discard button
        OutlinedButton.icon(
          onPressed: _handleDiscardImage,
          icon: const Icon(Icons.delete_outline),
          label: const Text('丢弃图片'),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.red,
            side: const BorderSide(color: Colors.red),
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ],
    );
  }

  /// Handle image selected
  void _handleImageSelected(File image) {
    setState(() {
      _selectedImage = image;
      _extractedText = null;
      _status = '图片已选择，点击"识别并保存"开始处理';
    });
  }

  /// Handle image cleared
  void _handleImageCleared() {
    setState(() {
      _selectedImage = null;
      _extractedText = null;
      _status = '';
    });
  }

  /// Handle save image
  Future<void> _handleSaveImage(InspirationProvider provider) async {
    if (_selectedImage == null) return;

    setState(() {
      _isProcessing = true;
      _status = '正在识别图片中的文字...';
    });

    final success = await provider.createImageRecord(
      imageFile: _selectedImage!,
      language: 'zh',
      autoProcess: true,
    );

    setState(() {
      _isProcessing = false;
    });

    if (success) {
      setState(() {
        _status = '灵感已保存！';
      });

      // Show success message and navigate back
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('图片已成功识别并保存'),
          backgroundColor: Colors.green,
        ),
      );

      // Wait a bit then navigate back
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) {
        Navigator.of(context).pop();
      }
    } else {
      // Error is shown in status banner via provider
      setState(() {
        _status = '';
      });
    }
  }

  /// Handle discard image
  void _handleDiscardImage() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认丢弃'),
        content: const Text('确定要丢弃这张图片吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _selectedImage = null;
                _extractedText = null;
                _status = '';
              });

              Navigator.of(context).pop();

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('图片已丢弃')),
              );
            },
            child: const Text('确定', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  /// Show edit text dialog
  void _showEditTextDialog(BuildContext context) {
    final controller = TextEditingController(text: _extractedText);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('编辑识别的文字'),
        content: TextField(
          controller: controller,
          maxLines: 10,
          decoration: const InputDecoration(
            hintText: '编辑文字...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _extractedText = controller.text;
              });
              Navigator.of(context).pop();

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('文字已更新')),
              );
            },
            child: const Text('保存'),
          ),
        ],
      ),
    );
  }

  /// Show help dialog
  void _showHelp(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('使用帮助'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                '图片/文档识别功能说明',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              const Text('• 支持拍照、相册选择或PDF文档上传'),
              const Text('• 自动识别图片/PDF中的文字内容'),
              const Text('• 支持中英文印刷体，准确率95%+'),
              const Text('• PDF支持多页识别和Markdown输出'),
              const Text('• 识别后可手动编辑文字'),
              const Text('• 自动生成分类标签和摘要'),
              const SizedBox(height: 16),
              const Text(
                '最佳实践',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              const Text('• 确保图片清晰，光线充足'),
              const Text('• 文字大小适中，避免过小'),
              const Text('• 避免图片模糊或反光'),
              const Text('• 尽量保持文字方向正确'),
              const Text('• 支持的格式: JPG, PNG, WEBP, PDF'),
              const Text('• 最大文件大小: 5MB'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }
}
