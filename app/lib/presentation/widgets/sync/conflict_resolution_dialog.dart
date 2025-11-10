import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/themes.dart';
import '../../../data/database.dart';

/// Dialog for resolving sync conflicts
/// Implements Last-Write-Wins strategy with user override option
class ConflictResolutionDialog extends StatelessWidget {
  final InspirationRecord localRecord;
  final Map<String, dynamic> remoteRecord;
  final VoidCallback? onKeepLocal;
  final VoidCallback? onKeepRemote;
  final VoidCallback? onMerge;

  const ConflictResolutionDialog({
    super.key,
    required this.localRecord,
    required this.remoteRecord,
    this.onKeepLocal,
    this.onKeepRemote,
    this.onMerge,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.warning_rounded, color: AppColors.warning),
          SizedBox(width: 8),
          Text('同步冲突'),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '本地版本和 Notion 版本存在差异，请选择保留哪个版本：',
              style: TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 16),
            _buildVersionCard(
              context,
              title: '本地版本',
              icon: Icons.phone_android_rounded,
              iconColor: AppColors.primary,
              content: localRecord.content,
              timestamp: localRecord.updatedAt,
              version: localRecord.version,
            ),
            const SizedBox(height: 12),
            _buildVersionCard(
              context,
              title: 'Notion 版本',
              icon: Icons.cloud_rounded,
              iconColor: AppColors.success,
              content: remoteRecord['content'] as String? ?? '',
              timestamp: DateTime.tryParse(
                    remoteRecord['updated_at'] as String? ?? '',
                  ) ??
                  DateTime.now(),
              version: remoteRecord['version'] as int? ?? 1,
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.info_outline_rounded,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '推荐使用"保留最新"，系统将自动选择更新时间较晚的版本',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: onKeepLocal,
          child: const Text('保留本地'),
        ),
        TextButton(
          onPressed: onKeepRemote,
          child: const Text('保留 Notion'),
        ),
        FilledButton.icon(
          onPressed: onMerge ?? _autoResolveByTimestamp,
          icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
          label: const Text('保留最新'),
        ),
      ],
    );
  }

  Widget _buildVersionCard(
    BuildContext context, {
    required String title,
    required IconData icon,
    required Color iconColor,
    required String content,
    required DateTime timestamp,
    required int version,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: iconColor),
              const SizedBox(width: 6),
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Text(
                'v$version',
                style: TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            content.length > 100 ? '${content.substring(0, 100)}...' : content,
            style: const TextStyle(fontSize: 12),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                Icons.access_time_rounded,
                size: 12,
                color: AppColors.textSecondary,
              ),
              const SizedBox(width: 4),
              Text(
                _formatTimestamp(timestamp),
                style: TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _autoResolveByTimestamp() {
    final localTimestamp = localRecord.updatedAt;
    final remoteTimestamp = DateTime.tryParse(
          remoteRecord['updated_at'] as String? ?? '',
        ) ??
        DateTime.now();

    // Keep whichever is newer (Last-Write-Wins)
    if (localTimestamp.isAfter(remoteTimestamp)) {
      onKeepLocal?.call();
    } else {
      onKeepRemote?.call();
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) return '刚刚';
    if (difference.inHours < 1) return '${difference.inMinutes}分钟前';
    if (difference.inDays < 1) return '${difference.inHours}小时前';
    if (difference.inDays < 7) return '${difference.inDays}天前';

    return '${timestamp.year}-${timestamp.month.toString().padLeft(2, '0')}-${timestamp.day.toString().padLeft(2, '0')} '
        '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  }
}

/// Extension for showing conflict resolution dialog
extension ConflictResolution on BuildContext {
  /// Show conflict resolution dialog
  Future<ConflictResolutionResult?> showConflictDialog({
    required InspirationRecord localRecord,
    required Map<String, dynamic> remoteRecord,
  }) {
    return showDialog<ConflictResolutionResult>(
      context: this,
      barrierDismissible: false,
      builder: (context) => ConflictResolutionDialog(
        localRecord: localRecord,
        remoteRecord: remoteRecord,
        onKeepLocal: () {
          Navigator.of(context).pop(ConflictResolutionResult.keepLocal);
        },
        onKeepRemote: () {
          Navigator.of(context).pop(ConflictResolutionResult.keepRemote);
        },
        onMerge: () {
          // Auto-resolve by timestamp (Last-Write-Wins)
          final localTimestamp = localRecord.updatedAt;
          final remoteTimestamp = DateTime.tryParse(
                remoteRecord['updated_at'] as String? ?? '',
              ) ??
              DateTime.now();

          if (localTimestamp.isAfter(remoteTimestamp)) {
            Navigator.of(context).pop(ConflictResolutionResult.keepLocal);
          } else {
            Navigator.of(context).pop(ConflictResolutionResult.keepRemote);
          }
        },
      ),
    );
  }
}

/// Result of conflict resolution
enum ConflictResolutionResult {
  keepLocal,
  keepRemote,
  merge, // Reserved for future manual merge feature
}
