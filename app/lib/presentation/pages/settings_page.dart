import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:drift/drift.dart' hide Column;

import '../../core/constants.dart';
import '../../core/themes.dart';
import '../../data/database.dart';
import '../../data/services/api_service.dart';
import '../../data/services/app_update_service.dart';
import '../../data/services/storage_service.dart';
import '../../data/services/sync/connectivity_service.dart';
import '../../data/services/sync/sync_service.dart';
import '../widgets/sync/sync_indicator.dart';

/// Settings page for app configuration
/// Includes Notion sync, AI, and general preferences
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _database = AppDatabase();
  UserPreference? _preferences;
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isCheckingUpdate = false;

  // Controllers for text fields
  final _backendUrlController = TextEditingController(); // Backend API URL
  final _notionTokenController = TextEditingController();
  final _notionDatabaseIdController = TextEditingController();
  final _openaiApiKeyController = TextEditingController();
  final _openaiBaseUrlController = TextEditingController();
  final _openaiModelController = TextEditingController();
  final _deepgramApiKeyController = TextEditingController();

  // Obscure text state
  bool _obscureNotionToken = true;
  bool _obscureOpenaiKey = true;
  bool _obscureDeepgramKey = true;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  @override
  void dispose() {
    _backendUrlController.dispose();
    _notionTokenController.dispose();
    _notionDatabaseIdController.dispose();
    _openaiApiKeyController.dispose();
    _openaiBaseUrlController.dispose();
    _openaiModelController.dispose();
    _deepgramApiKeyController.dispose();
    super.dispose();
  }

  Future<void> _loadPreferences() async {
    setState(() => _isLoading = true);

    final prefs = await _database.getPreferences();

    if (prefs != null && mounted) {
      // Load Backend URL from StorageService
      final storageService = await StorageService.getInstance();
      final backendUrl = storageService.getString(StorageService.keyApiBaseUrl,
          defaultValue: ApiConstants.defaultBaseUrl);

      setState(() {
        _preferences = prefs;
        _backendUrlController.text = backendUrl ?? ApiConstants.defaultBaseUrl;
        _notionTokenController.text = prefs.notionToken ?? '';
        _notionDatabaseIdController.text = prefs.notionDatabaseId ?? '';
        _openaiApiKeyController.text = prefs.openaiApiKey ?? '';
        _openaiBaseUrlController.text = prefs.openaiBaseUrl;
        _openaiModelController.text = prefs.openaiModel;
        _deepgramApiKeyController.text = prefs.deepgramApiKey;
        _isLoading = false;
      });
    }
  }

  Future<void> _savePreferences() async {
    if (_preferences == null) return;

    setState(() => _isSaving = true);

    try {
      // 1. Save to local database
      await _database.updatePreferences(
        UserPreferencesCompanion(
          id: const Value(1),
          notionToken: Value(
            _notionTokenController.text.trim().isEmpty
                ? null
                : _notionTokenController.text.trim(),
          ),
          notionDatabaseId: Value(
            _notionDatabaseIdController.text.trim().isEmpty
                ? null
                : _notionDatabaseIdController.text.trim(),
          ),
          openaiApiKey: Value(
            _openaiApiKeyController.text.trim().isEmpty
                ? null
                : _openaiApiKeyController.text.trim(),
          ),
          openaiBaseUrl: Value(_openaiBaseUrlController.text.trim()),
          openaiModel: Value(_openaiModelController.text.trim()),
          deepgramApiKey: Value(_deepgramApiKeyController.text.trim()),
          updatedAt: Value(DateTime.now()),
        ),
      );

      // 2. Save Backend URL to StorageService and update ApiService immediately
      final backendUrl = _backendUrlController.text.trim();
      if (backendUrl.isNotEmpty) {
        final storageService = await StorageService.getInstance();
        await storageService.setString(
            StorageService.keyApiBaseUrl, backendUrl);

        // Update ApiService baseUrl immediately without restarting app
        final apiService = Provider.of<ApiService>(context, listen: false);
        apiService.updateBaseUrl(backendUrl);
        debugPrint('Backend URL updated to: $backendUrl');
      }

      // 3. Sync to backend API
      try {
        final apiService = Provider.of<ApiService>(context, listen: false);
        final updateData = <String, dynamic>{};

        // Only include non-empty values
        // IMPORTANT: Empty values won't be sent to backend, so backend .env defaults won't be overridden
        final notionToken = _notionTokenController.text.trim();
        if (notionToken.isNotEmpty) {
          updateData['notion_token'] = notionToken;
        }

        final notionDatabaseId = _notionDatabaseIdController.text.trim();
        if (notionDatabaseId.isNotEmpty) {
          updateData['notion_database_id'] = notionDatabaseId;
        }

        // NOTE: LLM and STT configs are managed by backend .env
        // Mobile app should NOT override these unless explicitly provided
        final openaiApiKey = _openaiApiKeyController.text.trim();
        if (openaiApiKey.isNotEmpty) {
          updateData['openai_api_key'] = openaiApiKey;
        }

        final openaiBaseUrl = _openaiBaseUrlController.text.trim();
        if (openaiBaseUrl.isNotEmpty) {
          updateData['openai_base_url'] = openaiBaseUrl;
        }

        final openaiModel = _openaiModelController.text.trim();
        if (openaiModel.isNotEmpty) {
          updateData['openai_model'] = openaiModel;
        }

        final deepgramApiKey = _deepgramApiKeyController.text.trim();
        if (deepgramApiKey.isNotEmpty) {
          updateData['deepgram_api_key'] = deepgramApiKey;
        }

        // Sync to backend if there are changes
        if (updateData.isNotEmpty) {
          await apiService.updatePreferences(updateData);
        }
      } catch (apiError) {
        // Log API sync error but don't fail the save operation
        debugPrint('Failed to sync preferences to backend: $apiError');
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('设置已保存'),
            backgroundColor: AppColors.success,
          ),
        );

        // Reload preferences
        await _loadPreferences();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('保存失败: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
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
                _buildBackendSection(),
                const SizedBox(height: 24),
                _buildAppUpdateSection(),
                const SizedBox(height: 24),
                _buildNotionSection(),
                const SizedBox(height: 24),
                _buildAISection(),
                const SizedBox(height: 24),
                _buildSyncSection(),
                const SizedBox(height: 24),
                _buildGeneralSection(),
                const SizedBox(height: 24),
                _buildSaveButton(),
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

  /// Backend API configuration section
  Widget _buildBackendSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.cloud_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  'Backend 服务器',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              '配置后端服务器地址(保存后立即生效)',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _backendUrlController,
              decoration: const InputDecoration(
                labelText: 'Backend URL',
                hintText: 'https://api.example.com',
                prefixIcon: Icon(Icons.dns_rounded),
                border: OutlineInputBorder(),
                helperText: '手机和电脑需在同一WiFi网络',
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.success.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline_rounded,
                      size: 16, color: AppColors.success),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '保存后立即生效,无需重启。确保地址格式正确：http://IP:端口',
                      style: TextStyle(
                          fontSize: 11, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Notion sync configuration section
  Widget _buildNotionSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.article_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  'Notion 同步',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              '配置 Notion Integration 以自动同步灵感记录',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _notionTokenController,
              decoration: InputDecoration(
                labelText: 'Notion Integration Token',
                hintText: 'secret_xxx...',
                prefixIcon: const Icon(Icons.key_rounded),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscureNotionToken
                        ? Icons.visibility_rounded
                        : Icons.visibility_off_rounded,
                  ),
                  onPressed: () {
                    setState(() => _obscureNotionToken = !_obscureNotionToken);
                  },
                ),
                border: const OutlineInputBorder(),
              ),
              obscureText: _obscureNotionToken,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notionDatabaseIdController,
              decoration: const InputDecoration(
                labelText: 'Notion Database ID',
                hintText: 'xxx-xxx-xxx-xxx',
                prefixIcon: Icon(Icons.storage_rounded),
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            _buildNotionHelp(),
          ],
        ),
      ),
    );
  }

  Widget _buildNotionHelp() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.info_outline_rounded,
                size: 16,
                color: AppColors.primary,
              ),
              SizedBox(width: 8),
              Text(
                '如何获取 Notion Integration?',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            '1. 访问 notion.so/my-integrations\n'
            '2. 创建新的 Integration\n'
            '3. 复制 Internal Integration Token\n'
            '4. 在 Notion 数据库中添加 Integration 连接',
            style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  /// AI configuration section
  Widget _buildAISection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.psychology_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  'AI 服务配置',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              '配置 OpenAI 兼容 API 用于智能分类和摘要',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _openaiBaseUrlController,
              decoration: const InputDecoration(
                labelText: 'API Base URL',
                hintText: 'http://localhost:11434/v1',
                prefixIcon: Icon(Icons.link_rounded),
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _openaiModelController,
              decoration: const InputDecoration(
                labelText: '模型名称',
                hintText: 'llama3.1, qwen2.5, gpt-4o-mini',
                prefixIcon: Icon(Icons.smart_toy_rounded),
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _openaiApiKeyController,
              decoration: InputDecoration(
                labelText: 'API Key (可选)',
                hintText: 'sk-...',
                prefixIcon: const Icon(Icons.vpn_key_rounded),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscureOpenaiKey
                        ? Icons.visibility_rounded
                        : Icons.visibility_off_rounded,
                  ),
                  onPressed: () {
                    setState(() => _obscureOpenaiKey = !_obscureOpenaiKey);
                  },
                ),
                border: const OutlineInputBorder(),
              ),
              obscureText: _obscureOpenaiKey,
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 4),
            const Text(
              '语音转文字服务配置',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _deepgramApiKeyController,
              decoration: InputDecoration(
                labelText: 'Deepgram API Key',
                hintText: '44e90ac460009a2a7cd9adfee1a65de28aba654b',
                prefixIcon: const Icon(Icons.mic_rounded),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscureDeepgramKey
                        ? Icons.visibility_rounded
                        : Icons.visibility_off_rounded,
                  ),
                  onPressed: () {
                    setState(() => _obscureDeepgramKey = !_obscureDeepgramKey);
                  },
                ),
                border: const OutlineInputBorder(),
              ),
              obscureText: _obscureDeepgramKey,
            ),
          ],
        ),
      ),
    );
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
              title: const Text('自动分类'),
              subtitle: const Text('使用 AI 自动为灵感添加分类标签'),
              value: _preferences!.autoClassify,
              onChanged: (value) async {
                await _database.updatePreferences(
                  UserPreferencesCompanion(
                    id: const Value(1),
                    autoClassify: Value(value),
                    updatedAt: Value(DateTime.now()),
                  ),
                );
                await _loadPreferences();
              },
            ),
            const Divider(),
            SwitchListTile(
              title: const Text('自动摘要'),
              subtitle: const Text('使用 AI 自动生成灵感摘要'),
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

  /// Save button
  Widget _buildSaveButton() {
    return FilledButton.icon(
      onPressed: _isSaving ? null : _savePreferences,
      icon: _isSaving
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.save_rounded),
      label: Text(_isSaving ? '保存中...' : '保存设置'),
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(48),
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
