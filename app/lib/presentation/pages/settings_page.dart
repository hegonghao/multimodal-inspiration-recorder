import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drift/drift.dart' hide Column;

import '../../core/themes.dart';
import '../../data/database.dart';
import '../../data/services/api_service.dart';
import '../../data/services/app_update_service.dart';
import '../../data/services/sync/connectivity_service.dart';
import '../../data/services/sync/sync_service.dart';
import '../widgets/sync/sync_indicator.dart';

/// Settings page for app configuration
/// Includes app updates, sync behavior, and general preferences.
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _database = AppDatabase();
  UserPreference? _preferences;
  bool _isLoading = true;
  bool _isCheckingUpdate = false;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    setState(() => _isLoading = true);

    final prefs = await _database.getPreferences();

    if (prefs != null && mounted) {
      setState(() {
        _preferences = prefs;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('设置'),
        actions: const [
          SyncIndicator(),
          SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildAppUpdateSection(),
                const SizedBox(height: 24),
                _buildSyncSection(),
                const SizedBox(height: 24),
                _buildGeneralSection(),
              ],
            ),
    );
  }

  Widget _buildAppUpdateSection() {
    return Card(
      child: ListTile(
        leading:
            const Icon(Icons.system_update_rounded, color: AppColors.primary),
        title: const Text('应用更新'),
        subtitle: Text(
          Platform.isAndroid ? '检查并下载最新 Android 版本' : '请通过应用商店或 TestFlight 更新',
        ),
        trailing: _isCheckingUpdate
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.chevron_right_rounded),
        onTap: _isCheckingUpdate ? null : _checkForAppUpdate,
      ),
    );
  }

  Future<void> _checkForAppUpdate() async {
    if (!Platform.isAndroid) {
      _showMessage('Android APK 更新仅支持 Android，iOS 请通过应用商店或 TestFlight 更新');
      return;
    }

    setState(() => _isCheckingUpdate = true);
    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      final updateService = AppUpdateService(apiService: apiService);
      final update = await updateService.checkForUpdate();

      if (!update.hasUpdate) {
        _showMessage(
            '当前已经是最新版本（${update.currentVersion}+${update.currentBuild}）');
        return;
      }

      if (update.downloadUrl == null || update.downloadUrl!.trim().isEmpty) {
        _showMessage('检测到新版本，但服务器尚未配置 APK 下载地址');
        return;
      }

      if (!mounted) return;
      final confirmed = await showDialog<bool>(
        context: context,
        barrierDismissible: !update.forceUpdate,
        builder: (dialogContext) => AlertDialog(
          title: Text('发现新版本 ${update.latestVersion}'),
          content: Text(
            update.releaseNotes.isEmpty ? '是否下载并安装新版本？' : update.releaseNotes,
          ),
          actions: [
            if (!update.forceUpdate)
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('稍后'),
              ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('立即更新'),
            ),
          ],
        ),
      );

      if (confirmed != true || !mounted) return;
      final apkPath = await updateService.downloadApk(update);
      await updateService.installApk(apkPath);
      _showMessage('已打开系统安装程序，请确认安装');
    } catch (e) {
      _showMessage('检查更新失败：$e');
    } finally {
      if (mounted) setState(() => _isCheckingUpdate = false);
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  /// Sync preferences section
  Widget _buildSyncSection() {
    if (_preferences == null) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.sync_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  '同步设置',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('网络可用时自动同步'),
              subtitle: const Text('检测到网络连接时自动触发同步'),
              value: _preferences!.syncOnNetwork,
              onChanged: (value) async {
                await _database.updatePreferences(
                  UserPreferencesCompanion(
                    id: const Value(1),
                    syncOnNetwork: Value(value),
                    updatedAt: Value(DateTime.now()),
                  ),
                );
                await _loadPreferences();
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.schedule_rounded),
              title: const Text('同步间隔'),
              subtitle: Text(
                '每 ${(_preferences!.syncInterval / 60).toInt()} 分钟自动同步一次',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: _showSyncIntervalPicker,
            ),
            const Divider(),
            Consumer<SyncService>(
              builder: (context, syncService, child) {
                return ListTile(
                  leading: Icon(
                    syncService.isSyncing
                        ? Icons.sync_rounded
                        : Icons.sync_disabled_rounded,
                    color: syncService.canSync
                        ? AppColors.primary
                        : AppColors.textSecondary,
                  ),
                  title: const Text('立即同步'),
                  subtitle: Text(syncService.syncStatusMessage),
                  trailing: syncService.isSyncing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right_rounded),
                  enabled: syncService.canSync,
                  onTap: () async {
                    await syncService.triggerSync();
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  /// General settings section
  Widget _buildGeneralSection() {
    if (_preferences == null) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.settings_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  '通用设置',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('自动整理'),
              subtitle: const Text('使用 AI 自动生成总结和摘要'),
              value: _preferences!.autoSummarize,
              onChanged: (value) async {
                await _database.updatePreferences(
                  UserPreferencesCompanion(
                    id: const Value(1),
                    autoSummarize: Value(value),
                    updatedAt: Value(DateTime.now()),
                  ),
                );
                await _loadPreferences();
              },
            ),
            const Divider(),
            Consumer<ConnectivityService>(
              builder: (context, connectivity, child) {
                return ListTile(
                  leading: Icon(
                    connectivity.isConnected
                        ? Icons.wifi_rounded
                        : Icons.wifi_off_rounded,
                    color: connectivity.isConnected
                        ? AppColors.success
                        : AppColors.error,
                  ),
                  title: const Text('网络状态'),
                  subtitle: Text(connectivity.connectionStatus),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () async {
                    await connectivity.checkConnectivity();
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Show sync interval picker dialog
  void _showSyncIntervalPicker() {
    if (_preferences == null) return;

    final intervals = [
      (300, '5 分钟'),
      (600, '10 分钟'),
      (900, '15 分钟'),
      (1800, '30 分钟'),
      (3600, '1 小时'),
    ];

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('选择同步间隔'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: intervals.map((interval) {
            final (seconds, label) = interval;
            final isSelected = _preferences!.syncInterval == seconds;

            return RadioListTile<int>(
              title: Text(label),
              value: seconds,
              groupValue: _preferences!.syncInterval,
              selected: isSelected,
              onChanged: (value) async {
                if (value != null) {
                  await _database.updatePreferences(
                    UserPreferencesCompanion(
                      id: const Value(1),
                      syncInterval: Value(value),
                      updatedAt: Value(DateTime.now()),
                    ),
                  );
                  await _loadPreferences();
                  if (context.mounted) {
                    Navigator.pop(context);
                  }
                }
              },
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
        ],
      ),
    );
  }
}
