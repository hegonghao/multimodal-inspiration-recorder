import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../../core/constants.dart';
import '../../core/themes.dart';
import '../../data/database.dart';
import '../providers/inspiration_provider.dart';
import '../widgets/sync/sync_indicator.dart';

/// Record list page - displays all inspiration records
class RecordListPage extends StatefulWidget {
  const RecordListPage({super.key});

  @override
  State<RecordListPage> createState() => _RecordListPageState();
}

class _RecordListPageState extends State<RecordListPage> {
  String? _selectedInputType;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Load records when page opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<InspirationProvider>().loadRecords();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Parse category tags from JSON string or comma-separated string
  List<String> _parseCategoryTags(String? tagsStr) {
    if (tagsStr == null || tagsStr.isEmpty) {
      print('DEBUG: Tags string is null or empty');
      return [];
    }

    print('DEBUG: Parsing tags: $tagsStr');

    try {
      // Try to parse as JSON array
      final decoded = jsonDecode(tagsStr);
      print('DEBUG: Decoded JSON: $decoded (type: ${decoded.runtimeType})');
      if (decoded is List) {
        final result = decoded.map((e) => e.toString()).toList();
        print('DEBUG: Parsed tags result: $result');
        return result;
      }
    } catch (e) {
      print('DEBUG: JSON parse failed: $e, trying comma-separated');
      // If JSON parse fails, try comma-separated
      final result = tagsStr.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
      print('DEBUG: Comma-separated result: $result');
      return result;
    }

    print('DEBUG: Returning empty list');
    return [];
  }

  /// Sync all records from backend
  Future<void> _syncAllFromBackend(BuildContext context) async {
    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('同步所有记录'),
        content: const Text('这将从后端服务器重新下载所有记录，包括AI生成的标签和摘要。是否继续？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).primaryColor,
            ),
            child: const Text('同步'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    // Show loading dialog
    if (!context.mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 16),
                Text('正在同步...'),
              ],
            ),
          ),
        ),
      ),
    );

    // Perform sync
    final provider = context.read<InspirationProvider>();
    final success = await provider.syncAllFromBackend();

    // Close loading dialog
    if (!context.mounted) return;
    Navigator.pop(context);

    // Show result
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? '同步成功！已更新所有记录' : '同步失败，请重试'),
        backgroundColor: success ? Colors.green : Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('历史记录'),
        actions: [
          // Sync button
          IconButton(
            onPressed: () => _syncAllFromBackend(context),
            icon: const Icon(Icons.cloud_download),
            tooltip: '从后端同步所有记录',
          ),
          const SyncIndicator(compact: true),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Filter bar
          _buildFilterBar(),

          // Records list
          Expanded(
            child: Consumer<InspirationProvider>(
              builder: (context, provider, child) {
                if (provider.isLoading && provider.records.isEmpty) {
                  return const Center(
                    child: CircularProgressIndicator(),
                  );
                }

                if (provider.error != null) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 64,
                          color: AppColors.error,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          '加载失败',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          provider.error!,
                          style: Theme.of(context).textTheme.bodyMedium,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton.icon(
                          onPressed: () => provider.loadRecords(
                            inputType: _selectedInputType,
                            triggerSync: false,
                          ),
                          icon: const Icon(Icons.refresh),
                          label: const Text('重试'),
                        ),
                      ],
                    ),
                  );
                }

                if (provider.records.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.inbox_outlined,
                          size: 64,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          '暂无记录',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '开始记录您的灵感吧',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Colors.grey[500],
                          ),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => provider.loadRecords(
                    inputType: _selectedInputType,
                    triggerSync: false,
                  ),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: provider.records.length,
                    itemBuilder: (context, index) {
                      final record = provider.records[index];
                      return _buildRecordCard(context, record, provider);
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            offset: const Offset(0, 2),
            blurRadius: 4,
          ),
        ],
      ),
      child: Row(
        children: [
          // Input type filter
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _selectedInputType,
              decoration: const InputDecoration(
                labelText: '输入方式',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: null, child: Text('全部')),
                DropdownMenuItem(value: 'voice', child: Text('语音')),
                DropdownMenuItem(value: 'image', child: Text('图片')),
                DropdownMenuItem(value: 'text', child: Text('文字')),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedInputType = value;
                });
                context.read<InspirationProvider>().loadRecords(
                  inputType: value,
                  triggerSync: false,
                );
              },
            ),
          ),
          const SizedBox(width: 12),

          // Refresh button
          IconButton(
            onPressed: () {
              context.read<InspirationProvider>().loadRecords(
                inputType: _selectedInputType,
                triggerSync: false,
              );
            },
            icon: const Icon(Icons.refresh),
            tooltip: '刷新',
          ),
        ],
      ),
    );
  }

  Widget _buildRecordCard(
    BuildContext context,
    InspirationRecord record,
    InspirationProvider provider,
  ) {
    final dateFormat = DateFormat('yyyy-MM-dd HH:mm');

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showRecordDetail(context, record),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  _buildInputTypeChip(record.inputType),
                  const Spacer(),
                  _buildSyncStatusIcon(record.syncStatus),
                  const SizedBox(width: 8),
                  Text(
                    dateFormat.format(record.createdAt),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Title
              Text(
                record.title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),

              // Content preview
              Text(
                record.content,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),

              // Tags and summary
              if (record.categoryTags != null || record.summary != null) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (record.categoryTags != null)
                      ..._parseCategoryTags(record.categoryTags).map(
                        (tag) {
                          print('DEBUG: Creating chip for tag: "$tag" (length: ${tag.length})');
                          return Chip(
                            label: Text(
                              tag.trim(),
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.black87,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            backgroundColor: Colors.blue.shade50,
                            visualDensity: VisualDensity.compact,
                          );
                        },
                      ),
                  ],
                ),
              ],

              // Action buttons
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: () => _showDeleteConfirmation(context, record, provider),
                    icon: const Icon(Icons.delete_outline, size: 18),
                    label: const Text('删除'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.error,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInputTypeChip(String inputType) {
    IconData icon;
    Color color;
    String label;

    switch (inputType.toLowerCase()) {
      case 'voice':
        icon = Icons.mic;
        color = AppColors.voiceActive;
        label = '语音';
        break;
      case 'image':
        icon = Icons.image;
        color = AppColors.imageActive;
        label = '图片';
        break;
      case 'text':
        icon = Icons.edit_note;
        color = AppColors.textActive;
        label = '文字';
        break;
      default:
        icon = Icons.article;
        color = AppColors.primary;
        label = inputType;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSyncStatusIcon(int syncStatus) {
    IconData icon;
    Color color;
    String tooltip;

    switch (syncStatus) {
      case 0: // PENDING
        icon = Icons.cloud_upload_outlined;
        color = Colors.orange;
        tooltip = '待同步';
        break;
      case 1: // SYNCING
        icon = Icons.cloud_sync;
        color = Colors.blue;
        tooltip = '同步中';
        break;
      case 2: // SYNCED
        icon = Icons.cloud_done;
        color = AppColors.success;
        tooltip = '已同步';
        break;
      case 3: // FAILED
        icon = Icons.cloud_off;
        color = AppColors.error;
        tooltip = '同步失败';
        break;
      default:
        icon = Icons.cloud_queue;
        color = Colors.grey;
        tooltip = '未知';
    }

    return Tooltip(
      message: tooltip,
      child: Icon(icon, size: 18, color: color),
    );
  }

  void _showRecordDetail(BuildContext context, InspirationRecord record) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        builder: (context, scrollController) {
          return Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(20),
              ),
            ),
            child: Column(
              children: [
                // Handle
                Container(
                  margin: const EdgeInsets.symmetric(vertical: 12),
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),

                // Content
                Expanded(
                  child: ListView(
                    controller: scrollController,
                    padding: const EdgeInsets.all(24),
                    children: [
                      // Type and date
                      Row(
                        children: [
                          _buildInputTypeChip(record.inputType),
                          const Spacer(),
                          Text(
                            DateFormat('yyyy-MM-dd HH:mm').format(record.createdAt),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // Title
                      Text(
                        record.title,
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Content
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surface,
                          border: Border.all(
                            color: Colors.grey[300]!,
                          ),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: SelectableText(
                          record.content,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ),

                      // Summary
                      if (record.summary != null) ...[
                        const SizedBox(height: 16),
                        Text(
                          '摘要',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.05),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            record.summary!,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],

                      // Tags
                      if (record.categoryTags != null) ...[
                        const SizedBox(height: 16),
                        Text(
                          '标签',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _parseCategoryTags(record.categoryTags).map(
                            (tag) {
                              print('DEBUG: Creating detail chip for tag: "$tag"');
                              return Chip(
                                label: Text(
                                  tag.trim(),
                                  style: TextStyle(
                                    color: Colors.black87,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                backgroundColor: Colors.blue.shade50,
                              );
                            },
                          ).toList(),
                        ),
                      ],

                      // Sync status
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Text(
                            '同步状态',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(width: 8),
                          _buildSyncStatusIcon(record.syncStatus),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _showDeleteConfirmation(
    BuildContext context,
    InspirationRecord record,
    InspirationProvider provider,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: const Text('确定要删除这条记录吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);

              final success = await provider.deleteRecord(record.id);

              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(success ? '删除成功' : '删除失败'),
                    backgroundColor: success ? AppColors.success : AppColors.error,
                  ),
                );
              }
            },
            style: TextButton.styleFrom(
              foregroundColor: AppColors.error,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }
}
