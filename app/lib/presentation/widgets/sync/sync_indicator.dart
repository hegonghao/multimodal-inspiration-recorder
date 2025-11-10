import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants.dart';
import '../../../core/themes.dart';
import '../../../data/database.dart';
import '../../../data/repositories/inspiration_repository.dart';
import '../../../data/services/sync/connectivity_service.dart';
import '../../../data/services/sync/sync_service.dart';
import '../common/loading_indicator.dart';

/// Sync status indicator widget for showing sync progress
/// Displays in app bar or as floating widget
class SyncIndicator extends StatelessWidget {
  final bool compact;
  final VoidCallback? onTap;

  const SyncIndicator({
    super.key,
    this.compact = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Consumer2<SyncService, ConnectivityService>(
      builder: (context, syncService, connectivityService, child) {
        return InkWell(
          onTap: onTap ?? () => _showSyncDetails(context, syncService),
          borderRadius: BorderRadius.circular(20),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildSyncIcon(syncService, connectivityService),
                if (!compact) ...[
                  const SizedBox(width: 8),
                  _buildSyncText(syncService, connectivityService),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  /// Build sync status icon
  Widget _buildSyncIcon(
    SyncService syncService,
    ConnectivityService connectivityService,
  ) {
    if (syncService.isSyncing) {
      return const InlineLoadingIndicator(
        size: 16.0,
        color: AppColors.syncInProgress,
      );
    }

    if (!connectivityService.isConnected) {
      return const Icon(
        Icons.cloud_off_rounded,
        size: 18,
        color: AppColors.syncPending,
      );
    }

    final syncStatus = syncService.syncStatus;
    switch (syncStatus) {
      case SyncStatus.synced:
        return const Icon(
          Icons.cloud_done_rounded,
          size: 18,
          color: AppColors.syncCompleted,
        );
      case SyncStatus.pending:
      case SyncStatus.syncing:
        return const Icon(
          Icons.cloud_sync_rounded,
          size: 18,
          color: AppColors.syncInProgress,
        );
      case SyncStatus.failed:
      case SyncStatus.conflict:
        return const Icon(
          Icons.cloud_off_rounded,
          size: 18,
          color: AppColors.syncFailed,
        );
    }
  }

  /// Build sync status text
  Widget _buildSyncText(
    SyncService syncService,
    ConnectivityService connectivityService,
  ) {
    String text;
    Color color;

    if (syncService.isSyncing) {
      text = '同步中';
      color = AppColors.syncInProgress;
    } else if (!connectivityService.isConnected) {
      text = '离线';
      color = AppColors.syncPending;
    } else {
      text = syncService.syncStatusMessage;
      color = syncService.syncStatus == SyncStatus.failed
          ? AppColors.syncFailed
          : AppColors.textSecondary;
    }

    return Text(
      text,
      style: TextStyle(
        fontSize: 12,
        color: color,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  /// Show detailed sync status dialog
  void _showSyncDetails(
    BuildContext context,
    SyncService syncService,
  ) {
    showDialog(
      context: context,
      builder: (context) => SyncDetailsDialog(syncService: syncService),
    );
  }
}

/// Detailed sync status dialog
class SyncDetailsDialog extends StatefulWidget {
  final SyncService syncService;

  const SyncDetailsDialog({
    super.key,
    required this.syncService,
  });

  @override
  State<SyncDetailsDialog> createState() => _SyncDetailsDialogState();
}

class _SyncDetailsDialogState extends State<SyncDetailsDialog> {
  bool _isLoading = true;
  SyncStatistics? _stats;
  Map<String, dynamic>? _backendStatus;

  @override
  void initState() {
    super.initState();
    _loadSyncDetails();
  }

  Future<void> _loadSyncDetails() async {
    setState(() => _isLoading = true);

    final stats = await widget.syncService.getSyncStatistics();
    final backendStatus = await widget.syncService.getBackendSyncStatus();

    if (mounted) {
      setState(() {
        _stats = stats;
        _backendStatus = backendStatus;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.sync_rounded, color: AppColors.primary),
          SizedBox(width: 8),
          Text('同步状态'),
        ],
      ),
      content: _isLoading
          ? const SizedBox(
              height: 200,
              child: LoadingIndicator(
                style: LoadingStyle.spinner,
                size: 50.0,
                message: '加载中...',
              ),
            )
          : SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildLocalStats(),
                  const Divider(height: 24),
                  _buildBackendStatus(),
                  const Divider(height: 24),
                  _buildLastSyncInfo(),
                ],
              ),
            ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('关闭'),
        ),
        FilledButton.icon(
          onPressed: widget.syncService.canSync
              ? () async {
                  // Trigger sync and show result
                  final result = await widget.syncService.triggerSync();

                  if (context.mounted) {
                    // Close dialog
                    Navigator.pop(context);

                    // Show result snackbar
                    final scaffoldMessenger = ScaffoldMessenger.of(context);
                    scaffoldMessenger.showSnackBar(
                      SnackBar(
                        content: Row(
                          children: [
                            Icon(
                              result.success ? Icons.check_circle : Icons.error,
                              color: Colors.white,
                              size: 20,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(result.message),
                            ),
                          ],
                        ),
                        backgroundColor: result.success
                            ? AppColors.success
                            : AppColors.error,
                        duration: const Duration(seconds: 3),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  }
                }
              : null,
          icon: const Icon(Icons.sync_rounded, size: 18),
          label: const Text('立即同步'),
        ),
      ],
    );
  }

  Widget _buildLocalStats() {
    if (_stats == null) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '本地统计',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        _buildStatRow('总记录数', '${_stats!.totalRecords}', Icons.article_rounded),
        _buildStatRow('已同步', '${_stats!.syncedCount}', Icons.cloud_done_rounded,
            color: AppColors.syncCompleted),
        _buildStatRow('待同步', '${_stats!.unsyncedCount}', Icons.cloud_sync_rounded,
            color: AppColors.syncInProgress),
        _buildStatRow('同步失败', '${_stats!.failedCount}', Icons.error_outline_rounded,
            color: AppColors.syncFailed),
        if (_stats!.pendingTasks > 0)
          _buildStatRow('待处理任务', '${_stats!.pendingTasks}', Icons.pending_actions_rounded,
              color: AppColors.syncPending),
      ],
    );
  }

  Widget _buildBackendStatus() {
    if (_backendStatus == null) {
      return Text(
        '无法获取后端同步状态',
        style: TextStyle(
          color: AppColors.textSecondary,
          fontSize: 12,
        ),
      );
    }

    final syncEnabled = _backendStatus!['sync_enabled'] as bool? ?? false;
    final pendingCount = _backendStatus!['pending_count'] as int? ?? 0;
    final failedCount = _backendStatus!['failed_count'] as int? ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '后端状态',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        _buildStatRow(
          'Notion 同步',
          syncEnabled ? '已启用' : '已禁用',
          syncEnabled ? Icons.check_circle_rounded : Icons.cancel_rounded,
          color: syncEnabled ? AppColors.success : AppColors.error,
        ),
        if (syncEnabled) ...[
          _buildStatRow('后端待处理', '$pendingCount', Icons.hourglass_empty_rounded,
              color: AppColors.syncPending),
          if (failedCount > 0)
            _buildStatRow('后端失败', '$failedCount', Icons.error_outline_rounded,
                color: AppColors.syncFailed),
        ],
      ],
    );
  }

  Widget _buildLastSyncInfo() {
    final lastSyncAt = widget.syncService.lastSyncAt;
    final lastError = widget.syncService.lastSyncError;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '最近同步',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        if (lastSyncAt != null) ...[
          _buildInfoRow('时间', _formatDateTime(lastSyncAt)),
          _buildInfoRow('成功', '${widget.syncService.syncedCount} 条'),
          if (widget.syncService.failedCount > 0)
            _buildInfoRow('失败', '${widget.syncService.failedCount} 条',
                valueColor: AppColors.syncFailed),
        ] else
          const Text(
            '尚未同步',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
        if (lastError != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.syncFailed.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded,
                    size: 16, color: AppColors.syncFailed),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    lastError,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.syncFailed,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatRow(String label, String value, IconData icon,
      {Color? color}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color ?? AppColors.textSecondary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 13),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color ?? AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              color: valueColor ?? AppColors.textPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) return '刚刚';
    if (difference.inHours < 1) return '${difference.inMinutes}分钟前';
    if (difference.inDays < 1) return '${difference.inHours}小时前';
    if (difference.inDays < 7) return '${difference.inDays}天前';

    return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')} '
        '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
