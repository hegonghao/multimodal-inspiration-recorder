import 'dart:io';

import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:logger/logger.dart';
import 'package:image/image.dart' as img;

/// Camera and Image Picker Service
///
/// Provides image capture and selection functionality:
/// - Take photo with camera
/// - Select image from gallery
/// - Image preprocessing for OCR optimization
/// - Compress and resize images
class CameraService {
  final ImagePicker _picker = ImagePicker();
  final Logger _logger = Logger();

  // Image quality and size constraints
  static const int maxImageWidth = 1920;
  static const int maxImageHeight = 1080;
  static const int imageQuality = 85; // JPEG quality (0-100)
  static const int maxFileSizeBytes = 5 * 1024 * 1024; // 5MB

  /// Check and request camera permission
  Future<bool> requestCameraPermission() async {
    try {
      final status = await Permission.camera.status;

      if (status.isGranted) {
        _logger.i('Camera permission already granted');
        return true;
      }

      if (status.isDenied) {
        final result = await Permission.camera.request();
        if (result.isGranted) {
          _logger.i('Camera permission granted');
          return true;
        } else {
          _logger.w('Camera permission denied');
          return false;
        }
      }

      if (status.isPermanentlyDenied) {
        _logger.e('Camera permission permanently denied');
        await openAppSettings();
        return false;
      }

      return false;
    } catch (e) {
      _logger.e('Error requesting camera permission: $e');
      return false;
    }
  }

  /// Check and request photo library permission (iOS)
  Future<bool> requestPhotosPermission() async {
    try {
      if (Platform.isIOS) {
        final status = await Permission.photos.status;

        if (status.isGranted || status.isLimited) {
          _logger.i('Photos permission granted');
          return true;
        }

        if (status.isDenied) {
          final result = await Permission.photos.request();
          if (result.isGranted || result.isLimited) {
            _logger.i('Photos permission granted');
            return true;
          } else {
            _logger.w('Photos permission denied');
            return false;
          }
        }

        if (status.isPermanentlyDenied) {
          _logger.e('Photos permission permanently denied');
          await openAppSettings();
          return false;
        }
      }

      // Android doesn't require special permission for gallery access
      return true;
    } catch (e) {
      _logger.e('Error requesting photos permission: $e');
      return false;
    }
  }

  /// Take photo with camera
  Future<ImageResult> takePhoto() async {
    try {
      // Request permission
      final hasPermission = await requestCameraPermission();
      if (!hasPermission) {
        return ImageResult.error('Camera permission not granted');
      }

      // Capture photo
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: maxImageWidth.toDouble(),
        maxHeight: maxImageHeight.toDouble(),
        imageQuality: imageQuality,
      );

      if (photo == null) {
        _logger.i('User cancelled photo capture');
        return ImageResult.cancelled();
      }

      final file = File(photo.path);
      final fileSize = await file.length();

      // Check file size
      if (fileSize > maxFileSizeBytes) {
        _logger.w('Image file too large: $fileSize bytes');
        // Compress further if needed
        final compressed = await _compressImage(file);
        return ImageResult.success(compressed, fileSize: await compressed.length());
      }

      _logger.i('Photo captured: ${photo.path} ($fileSize bytes)');
      return ImageResult.success(file, fileSize: fileSize);

    } catch (e) {
      _logger.e('Error taking photo: $e');
      return ImageResult.error('Failed to take photo: $e');
    }
  }

  /// Select image from gallery
  Future<ImageResult> pickImage() async {
    try {
      // Request permission (iOS only)
      final hasPermission = await requestPhotosPermission();
      if (!hasPermission) {
        return ImageResult.error('Photos permission not granted');
      }

      // Pick image
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: maxImageWidth.toDouble(),
        maxHeight: maxImageHeight.toDouble(),
        imageQuality: imageQuality,
      );

      if (image == null) {
        _logger.i('User cancelled image selection');
        return ImageResult.cancelled();
      }

      final file = File(image.path);
      final fileSize = await file.length();

      // Check file size
      if (fileSize > maxFileSizeBytes) {
        _logger.w('Image file too large: $fileSize bytes');
        final compressed = await _compressImage(file);
        return ImageResult.success(compressed, fileSize: await compressed.length());
      }

      _logger.i('Image selected: ${image.path} ($fileSize bytes)');
      return ImageResult.success(file, fileSize: fileSize);

    } catch (e) {
      _logger.e('Error picking image: $e');
      return ImageResult.error('Failed to pick image: $e');
    }
  }

  /// Select multiple images from gallery
  Future<MultiImageResult> pickMultipleImages({int maxImages = 5}) async {
    try {
      // Request permission
      final hasPermission = await requestPhotosPermission();
      if (!hasPermission) {
        return MultiImageResult.error('Photos permission not granted');
      }

      // Pick multiple images
      final List<XFile> images = await _picker.pickMultiImage(
        maxWidth: maxImageWidth.toDouble(),
        maxHeight: maxImageHeight.toDouble(),
        imageQuality: imageQuality,
      );

      if (images.isEmpty) {
        _logger.i('User cancelled image selection');
        return MultiImageResult.cancelled();
      }

      // Limit number of images
      final limitedImages = images.take(maxImages).toList();

      // Convert to File objects
      final files = <File>[];
      for (final image in limitedImages) {
        final file = File(image.path);
        final fileSize = await file.length();

        if (fileSize > maxFileSizeBytes) {
          final compressed = await _compressImage(file);
          files.add(compressed);
        } else {
          files.add(file);
        }
      }

      _logger.i('${files.length} images selected');
      return MultiImageResult.success(files);

    } catch (e) {
      _logger.e('Error picking multiple images: $e');
      return MultiImageResult.error('Failed to pick images: $e');
    }
  }

  /// Preprocess image for OCR optimization
  ///
  /// Applies the following enhancements:
  /// - Grayscale conversion
  /// - Contrast enhancement
  /// - Gaussian blur for noise reduction
  /// - Resolution check (minimum 640x480)
  Future<File> preprocessImageForOCR(File imageFile) async {
    try {
      _logger.i('Preprocessing image for OCR: ${imageFile.path}');

      // Read image
      final bytes = await imageFile.readAsBytes();
      final image = img.decodeImage(bytes);

      if (image == null) {
        _logger.e('Failed to decode image');
        return imageFile;
      }

      // 1. Grayscale conversion (reduces color noise)
      var processed = img.grayscale(image);

      // 2. Contrast enhancement (makes text clearer)
      processed = img.contrast(processed, contrast: 175);

      // 3. Gaussian blur for noise reduction (smooths small imperfections)
      processed = img.gaussianBlur(processed, radius: 1);

      // 4. Resolution check (ensure minimum 640x480)
      if (processed.width < 640) {
        processed = img.copyResize(processed, width: 640);
      }

      // Save processed image
      final processedPath = imageFile.path.replaceAll(
        '.jpg',
        '_processed.jpg',
      );
      final processedFile = File(processedPath);
      await processedFile.writeAsBytes(img.encodeJpg(processed, quality: 90));

      _logger.i('Image preprocessing complete: $processedPath');
      return processedFile;

    } catch (e) {
      _logger.e('Error preprocessing image: $e');
      // Return original file if preprocessing fails
      return imageFile;
    }
  }

  /// Compress image to reduce file size
  Future<File> _compressImage(File imageFile) async {
    try {
      _logger.i('Compressing image: ${imageFile.path}');

      final bytes = await imageFile.readAsBytes();
      final image = img.decodeImage(bytes);

      if (image == null) {
        _logger.e('Failed to decode image for compression');
        return imageFile;
      }

      // Resize if too large
      img.Image resized = image;
      if (image.width > maxImageWidth || image.height > maxImageHeight) {
        resized = img.copyResize(
          image,
          width: image.width > maxImageWidth ? maxImageWidth : null,
          height: image.height > maxImageHeight ? maxImageHeight : null,
        );
      }

      // Compress with lower quality
      final compressedBytes = img.encodeJpg(resized, quality: 70);

      // Save compressed image
      final compressedPath = imageFile.path.replaceAll('.jpg', '_compressed.jpg');
      final compressedFile = File(compressedPath);
      await compressedFile.writeAsBytes(compressedBytes);

      final originalSize = await imageFile.length();
      final compressedSize = compressedBytes.length;
      final ratio = ((1 - compressedSize / originalSize) * 100).toStringAsFixed(1);

      _logger.i(
        'Image compressed: $originalSize -> $compressedSize bytes ($ratio% reduction)',
      );

      return compressedFile;

    } catch (e) {
      _logger.e('Error compressing image: $e');
      return imageFile;
    }
  }

  /// Create thumbnail for image preview
  Future<File> createThumbnail(File imageFile, {int size = 200}) async {
    try {
      final bytes = await imageFile.readAsBytes();
      final image = img.decodeImage(bytes);

      if (image == null) {
        _logger.e('Failed to decode image for thumbnail');
        return imageFile;
      }

      // Create square thumbnail
      final thumbnail = img.copyResizeCropSquare(image, size: size);

      // Save thumbnail
      final thumbnailPath = imageFile.path.replaceAll('.jpg', '_thumb.jpg');
      final thumbnailFile = File(thumbnailPath);
      await thumbnailFile.writeAsBytes(img.encodeJpg(thumbnail, quality: 85));

      _logger.i('Thumbnail created: $thumbnailPath (${size}x$size)');
      return thumbnailFile;

    } catch (e) {
      _logger.e('Error creating thumbnail: $e');
      return imageFile;
    }
  }

  /// Get image dimensions
  Future<ImageDimensions?> getImageDimensions(File imageFile) async {
    try {
      final bytes = await imageFile.readAsBytes();
      final image = img.decodeImage(bytes);

      if (image == null) {
        return null;
      }

      return ImageDimensions(
        width: image.width,
        height: image.height,
      );
    } catch (e) {
      _logger.e('Error getting image dimensions: $e');
      return null;
    }
  }
}

/// Result of an image operation
class ImageResult {

  ImageResult._({
    required this.success,
    this.file,
    this.error,
    this.fileSize,
    this.cancelled = false,
  });

  factory ImageResult.success(File file, {int? fileSize}) {
    return ImageResult._(
      success: true,
      file: file,
      fileSize: fileSize,
    );
  }

  factory ImageResult.error(String error) {
    return ImageResult._(
      success: false,
      error: error,
    );
  }

  factory ImageResult.cancelled() {
    return ImageResult._(
      success: false,
      cancelled: true,
    );
  }
  final bool success;
  final File? file;
  final String? error;
  final int? fileSize;
  final bool cancelled;

  @override
  String toString() {
    if (success) {
      return 'ImageResult(success: true, path: ${file?.path}, fileSize: $fileSize)';
    } else if (cancelled) {
      return 'ImageResult(cancelled: true)';
    } else {
      return 'ImageResult(success: false, error: $error)';
    }
  }
}

/// Result of multiple image selection
class MultiImageResult {

  MultiImageResult._({
    required this.success,
    this.files,
    this.error,
    this.cancelled = false,
  });

  factory MultiImageResult.success(List<File> files) {
    return MultiImageResult._(
      success: true,
      files: files,
    );
  }

  factory MultiImageResult.error(String error) {
    return MultiImageResult._(
      success: false,
      error: error,
    );
  }

  factory MultiImageResult.cancelled() {
    return MultiImageResult._(
      success: false,
      cancelled: true,
    );
  }
  final bool success;
  final List<File>? files;
  final String? error;
  final bool cancelled;
}

/// Image dimensions
class ImageDimensions {

  ImageDimensions({
    required this.width,
    required this.height,
  });
  final int width;
  final int height;

  double get aspectRatio => width / height;

  @override
  String toString() => '${width}x$height';
}
