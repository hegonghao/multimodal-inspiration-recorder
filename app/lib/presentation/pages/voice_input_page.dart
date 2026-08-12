import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drift/drift.dart' hide Column;

import '../providers/inspiration_provider.dart';
import '../widgets/voice_recorder.dart';
import '../widgets/common/loading_indicator.dart';
import '../../data/database.dart';

/// Voice Input Page
///
/// Full-screen voice recording interface for capturing inspiration.
///
/// Features:
/// - Voice recorder widget with real-time feedback
/// - Auto-save 3 seconds after recording stops
/// - AI summary and abstract generation
/// - Error handling and retry
class VoiceInputPage extends StatefulWidget {
  const VoiceInputPage({Key? key}) : super(key: key);

  @override
  State<VoiceInputPage> createState() => _VoiceInputPageState();
}

class _VoiceInputPageState extends State<VoiceInputPage> {
  File? _recordedAudioFile;
  bool _isProcessing = false;
  String _status = '';

  // Voice input preferences (loaded from database)
  String _selectedLanguage = 'auto'; // 'auto', 'zh', 'en'
  bool _autoProcessEnabled = true;

  final _database = AppDatabase();

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  @override
  void dispose() {
    _database.close();
    super.dispose();
  }

  /// Load voice input preferences from database
  Future<void> _loadPreferences() async {
    final prefs = await _database.getPreferences();
    if (prefs != null && mounted) {
      setState(() {
        _selectedLanguage = prefs.voiceInputLanguage;
        _autoProcessEnabled = prefs.autoProcessVoice;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('语音记录'),
        centerTitle: true,
        actions: [
          // Settings button
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showSettings(context),
            tooltip: '设置',
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
                        if (!provider.isRecording && _recordedAudioFile == null)
                          _buildInstructions(context),

                        const SizedBox(height: 24),

                        // Voice Recorder Widget
                        VoiceRecorderWidget(
                          onRecordingComplete: (audioFile) =>
                              _handleRecordingComplete(audioFile),
                          onRecordingCancelled: () =>
                              _handleRecordingCancelled(),
                        ),

                        const SizedBox(height: 24),

                        // Processing indicator
                        if (_isProcessing || provider.isCreating)
                          _buildProcessingIndicator(context),

                        // Recorded audio info
                        if (_recordedAudioFile != null && !_isProcessing)
                          _buildRecordedAudioInfo(context),

                        const SizedBox(height: 24),

                        // Action buttons
                        if (_recordedAudioFile != null && !_isProcessing)
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
  Widget _buildStatusBanner(
      BuildContext context, InspirationProvider provider) {
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
            _buildInstructionItem('点击麦克风按钮开始录音'),
            _buildInstructionItem('再次点击停止录音'),
            _buildInstructionItem('支持暂停和继续录音'),
            _buildInstructionItem('最长支持5分钟录音'),
            _buildInstructionItem('系统会自动转写并生成总结'),
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
          style: LoadingStyle.wave,
          size: 50.0,
          message: '正在处理音频...\n正在进行语音识别并生成摘要',
        ),
      ),
    );
  }

  /// Build recorded audio info card
  Widget _buildRecordedAudioInfo(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.check_circle,
                  color: Colors.green,
                ),
                const SizedBox(width: 8),
                Text(
                  '录音完成',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '文件路径: ${_recordedAudioFile!.path.split('/').last}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 4),
            FutureBuilder<int>(
              future: _recordedAudioFile!.length(),
              builder: (context, snapshot) {
                if (snapshot.hasData) {
                  final sizeKB = (snapshot.data! / 1024).toStringAsFixed(1);
                  return Text(
                    '文件大小: $sizeKB KB',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Build action buttons (save/retry/discard)
  Widget _buildActionButtons(
      BuildContext context, InspirationProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Save button with loading state
        LoadingButton(
          onPressed: () => _handleSaveRecording(provider),
          isLoading: _isProcessing || provider.isCreating,
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.save),
              SizedBox(width: 8),
              Text('保存灵感'),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Discard button
        OutlinedButton.icon(
          onPressed: _handleDiscardRecording,
          icon: const Icon(Icons.delete_outline),
          label: const Text('丢弃录音'),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.red,
            side: const BorderSide(color: Colors.red),
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ],
    );
  }

  /// Handle recording complete
  Future<void> _handleRecordingComplete(File audioFile) async {
    setState(() {
      _recordedAudioFile = audioFile;
      _status = '录音已完成，请选择保存或丢弃';
    });

    // Auto-save option (could be configurable)
    // Uncomment to enable auto-save 3 seconds after recording stops
    // await Future.delayed(const Duration(seconds: 3));
    // await _handleSaveRecording(context.read<InspirationProvider>());
  }

  /// Handle recording cancelled
  void _handleRecordingCancelled() {
    setState(() {
      _recordedAudioFile = null;
      _status = '';
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('录音已取消')),
    );
  }

  /// Handle save recording
  Future<void> _handleSaveRecording(InspirationProvider provider) async {
    if (_recordedAudioFile == null) return;

    setState(() {
      _isProcessing = true;
      _status = '正在保存...';
    });

    final success = await provider.createVoiceRecord(
      audioFile: _recordedAudioFile!,
      language: _selectedLanguage,
      autoProcess: _autoProcessEnabled,
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
          content: Text('灵感已成功保存'),
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

  /// Handle discard recording
  void _handleDiscardRecording() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认丢弃'),
        content: const Text('确定要丢弃这段录音吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              // Delete file
              if (_recordedAudioFile != null &&
                  _recordedAudioFile!.existsSync()) {
                _recordedAudioFile!.deleteSync();
              }

              setState(() {
                _recordedAudioFile = null;
                _status = '';
              });

              Navigator.of(context).pop();

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('录音已丢弃')),
              );
            },
            child: const Text('确定', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  /// Show settings dialog
  void _showSettings(BuildContext context) {
    // Local state for dialog
    String tempLanguage = _selectedLanguage;
    bool tempAutoProcess = _autoProcessEnabled;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('录音设置'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('语言设置',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                DropdownButton<String>(
                  value: tempLanguage,
                  isExpanded: true,
                  items: const [
                    DropdownMenuItem(value: 'auto', child: Text('自动检测 (推荐)')),
                    DropdownMenuItem(value: 'zh', child: Text('中文')),
                    DropdownMenuItem(value: 'en', child: Text('English')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        tempLanguage = value;
                      });
                    }
                  },
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  title: const Text('自动AI处理'),
                  subtitle: const Text('录音后自动生成总结和摘要'),
                  value: tempAutoProcess,
                  contentPadding: EdgeInsets.zero,
                  onChanged: (value) {
                    setState(() {
                      tempAutoProcess = value;
                    });
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () async {
                // Save to database
                await _database.updatePreferences(
                  UserPreferencesCompanion(
                    id: const Value(1),
                    voiceInputLanguage: Value(tempLanguage),
                    autoProcessVoice: Value(tempAutoProcess),
                    updatedAt: Value(DateTime.now()),
                  ),
                );

                // Update local state
                if (mounted) {
                  this.setState(() {
                    _selectedLanguage = tempLanguage;
                    _autoProcessEnabled = tempAutoProcess;
                  });
                }

                // Show success message
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('设置已保存'),
                    backgroundColor: Colors.green,
                  ),
                );

                Navigator.of(context).pop();
              },
              child: const Text('保存'),
            ),
          ],
        ),
      ),
    );
  }
}
