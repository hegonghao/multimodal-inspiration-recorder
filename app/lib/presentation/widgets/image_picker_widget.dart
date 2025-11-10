import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';

import '../providers/inspiration_provider.dart';

/// Image Picker Widget
///
/// Provides image selection interface with:
/// - Camera capture
/// - Gallery selection
/// - Image preview
/// - Image dimensions and size info
class ImagePickerWidget extends StatefulWidget {
  final Function(File)? onImageSelected;
  final Function()? onImageCleared;

  const ImagePickerWidget({
    Key? key,
    this.onImageSelected,
    this.onImageCleared,
  }) : super(key: key);

  @override
  State<ImagePickerWidget> createState() => _ImagePickerWidgetState();
}

class _ImagePickerWidgetState extends State<ImagePickerWidget> {
  File? _selectedImage;
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Title
          Text(
            '图片/文档识别',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 24),

          // Image Preview or Placeholder
          if (_selectedImage != null)
            _buildImagePreview(context)
          else
            _buildImagePlaceholder(context),

          const SizedBox(height: 24),

          // Loading Indicator
          if (_isLoading)
            const CircularProgressIndicator()
          else if (_selectedImage == null)
            _buildPickerButtons(context)
          else
            _buildActionButtons(context),

          const SizedBox(height: 16),

          // Info Text
          _buildInfoText(context),
        ],
      ),
    );
  }

  /// Check if selected file is a PDF
  bool _isPdfFile() {
    if (_selectedImage == null) return false;
    return _selectedImage!.path.toLowerCase().endsWith('.pdf');
  }

  /// Build image or document preview
  Widget _buildImagePreview(BuildContext context) {
    final isPdf = _isPdfFile();

    return Stack(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: isPdf
              ? Container(
                  height: 200,
                  width: double.infinity,
                  color: Colors.orange.shade50,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.picture_as_pdf,
                        size: 80,
                        color: Colors.orange.shade700,
                      ),
                      const SizedBox(height: 16),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Text(
                          _selectedImage!.path.split('/').last,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: Colors.orange.shade900,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'PDF 文档',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.orange.shade700,
                        ),
                      ),
                    ],
                  ),
                )
              : Image.file(
                  _selectedImage!,
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
        ),
        // Clear button
        Positioned(
          top: 8,
          right: 8,
          child: IconButton(
            icon: const Icon(Icons.close),
            color: isPdf ? Colors.orange.shade900 : Colors.white,
            style: IconButton.styleFrom(
              backgroundColor: isPdf
                  ? Colors.orange.shade100
                  : Colors.black.withOpacity(0.5),
            ),
            onPressed: _clearImage,
          ),
        ),
      ],
    );
  }

  /// Build image placeholder
  Widget _buildImagePlaceholder(BuildContext context) {
    return Container(
      height: 200,
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.grey[200],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.grey[400]!,
          width: 2,
          style: BorderStyle.solid,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.image_outlined,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 8),
          Text(
            '选择图片或PDF文档以识别文字',
            style: TextStyle(
              color: Colors.grey[600],
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  /// Build picker buttons (camera, gallery, and document)
  Widget _buildPickerButtons(BuildContext context) {
    return Consumer<InspirationProvider>(
      builder: (context, provider, child) {
        return Column(
          children: [
            Row(
              children: [
                // Camera Button
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _pickImageFromCamera(provider),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('拍照'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(width: 12),

                // Gallery Button
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pickImageFromGallery(provider),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('相册'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Document Button (PDF)
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _pickDocument,
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('选择PDF文档'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  foregroundColor: Colors.orange,
                  side: const BorderSide(color: Colors.orange),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  /// Build action buttons (use image or retake)
  Widget _buildActionButtons(BuildContext context) {
    return Row(
      children: [
        // Retake Button
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _clearImage,
            icon: const Icon(Icons.refresh),
            label: const Text('重新选择'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),
        const SizedBox(width: 12),

        // Confirm Button
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              widget.onImageSelected?.call(_selectedImage!);
            },
            icon: const Icon(Icons.check),
            label: const Text('使用图片'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),
      ],
    );
  }

  /// Build info text
  Widget _buildInfoText(BuildContext context) {
    if (_selectedImage != null) {
      return FutureBuilder<FileStat>(
        future: _selectedImage!.stat(),
        builder: (context, snapshot) {
          if (!snapshot.hasData) return const SizedBox.shrink();

          final sizeKB = (snapshot.data!.size / 1024).toStringAsFixed(1);
          return Text(
            '图片大小: $sizeKB KB',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey[600],
                ),
          );
        },
      );
    }

    return Text(
      '支持格式: JPG, PNG, WEBP, PDF\n最大5MB',
      textAlign: TextAlign.center,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.grey[600],
          ),
    );
  }

  /// Pick image from camera
  Future<void> _pickImageFromCamera(InspirationProvider provider) async {
    setState(() {
      _isLoading = true;
    });

    final imageFile = await provider.takePhoto();

    setState(() {
      _isLoading = false;
      if (imageFile != null) {
        _selectedImage = imageFile;
      }
    });

    if (provider.error != null) {
      _showError(context, provider.error!);
      provider.clearError();
    }
  }

  /// Pick image from gallery
  Future<void> _pickImageFromGallery(InspirationProvider provider) async {
    setState(() {
      _isLoading = true;
    });

    final imageFile = await provider.pickImage();

    setState(() {
      _isLoading = false;
      if (imageFile != null) {
        _selectedImage = imageFile;
      }
    });

    if (provider.error != null) {
      _showError(context, provider.error!);
      provider.clearError();
    }
  }

  /// Pick PDF document
  Future<void> _pickDocument() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf'],
        allowMultiple: false,
      );

      setState(() {
        _isLoading = false;
        if (result != null && result.files.isNotEmpty) {
          final filePath = result.files.single.path;
          if (filePath != null) {
            _selectedImage = File(filePath);
          }
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showError(context, '选择文档失败: $e');
    }
  }

  /// Clear selected image
  void _clearImage() {
    setState(() {
      _selectedImage = null;
    });
    widget.onImageCleared?.call();
  }

  /// Show error dialog
  void _showError(BuildContext context, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('错误'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }
}

/// Compact Image Picker Button
///
/// A simplified button for quick image selection
class CompactImagePickerButton extends StatelessWidget {
  final VoidCallback onPressed;

  const CompactImagePickerButton({
    Key? key,
    required this.onPressed,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton(
      onPressed: onPressed,
      tooltip: '图片识别',
      child: const Icon(Icons.image),
    );
  }
}

/// Image Preview Card
///
/// Displays selected image with metadata
class ImagePreviewCard extends StatelessWidget {
  final File imageFile;
  final VoidCallback? onRemove;

  const ImagePreviewCard({
    Key? key,
    required this.imageFile,
    this.onRemove,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Image
          Stack(
            children: [
              Image.file(
                imageFile,
                height: 200,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
              if (onRemove != null)
                Positioned(
                  top: 8,
                  right: 8,
                  child: IconButton(
                    icon: const Icon(Icons.close),
                    color: Colors.white,
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.black.withOpacity(0.5),
                    ),
                    onPressed: onRemove,
                  ),
                ),
            ],
          ),

          // Metadata
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  imageFile.path.split('/').last,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                FutureBuilder<FileStat>(
                  future: imageFile.stat(),
                  builder: (context, snapshot) {
                    if (!snapshot.hasData) {
                      return const SizedBox.shrink();
                    }

                    final sizeKB = (snapshot.data!.size / 1024).toStringAsFixed(1);
                    return Text(
                      '大小: $sizeKB KB',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
