/// Home page - main input mode selection interface
library;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/constants.dart';
import '../../core/themes.dart';
import '../../core/routes.dart';
import '../../debug/mic_test.dart';
import '../providers/inspiration_provider.dart';
import '../widgets/sync/sync_indicator.dart';
import 'voice_input_page.dart';
import 'image_input_page.dart';
import 'text_input_page.dart';
import 'record_list_page.dart';

/// HomePage displays the main input mode selection interface
///
/// Provides three input modes:
/// 1. Voice Recording - Quick audio capture with real-time transcription
/// 2. Image Capture - Photo OCR text recognition
/// 3. Text Input - Direct text entry (coming soon)
///
/// Corresponds to User Stories 1, 2, 3 in spec.md
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(AppConstants.appName),
        centerTitle: true,
        actions: [
          const SyncIndicator(compact: true),
          // Debug: Microphone test tool (only visible in debug mode)
          if (kDebugMode)
            IconButton(
              icon: const Icon(Icons.bug_report_outlined),
              tooltip: '麦克风测试 (调试)',
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const MicTestPage(),
                  ),
                );
              },
            ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: '设置',
            onPressed: () {
              AppRouter.navigateTo(context, Routes.settings);
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(UIConstants.paddingLarge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Welcome section
              _buildWelcomeSection(),

              const SizedBox(height: UIConstants.paddingExtraLarge),

              // Input mode selection cards
              Expanded(
                child: Center(
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildInputModeCard(
                          context: context,
                          title: '语音记录',
                          subtitle: '实时转写，快速捕捉灵感',
                          icon: Icons.mic_rounded,
                          color: AppColors.voiceActive,
                          backgroundColor: AppColors.voiceRecording,
                          onTap: () => _navigateToVoiceInput(context),
                        ),
                        const SizedBox(height: UIConstants.paddingMedium),
                        _buildInputModeCard(
                          context: context,
                          title: '图片识别',
                          subtitle: 'OCR文字提取，自动摘要',
                          icon: Icons.image_rounded,
                          color: AppColors.imageActive,
                          backgroundColor: AppColors.imageBackground,
                          onTap: () => _navigateToImageInput(context),
                        ),
                        const SizedBox(height: UIConstants.paddingMedium),
                        _buildInputModeCard(
                          context: context,
                          title: '文字输入',
                          subtitle: '直接输入，自动整理',
                          icon: Icons.edit_note_rounded,
                          color: AppColors.textActive,
                          backgroundColor: AppColors.textBackground,
                          onTap: () => _navigateToTextInput(context),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              const SizedBox(height: UIConstants.paddingLarge),

              // Recent records section (placeholder)
              _buildRecentRecordsButton(context),

              const SizedBox(height: UIConstants.paddingMedium),

              // Sync status indicator
              _buildSyncStatusIndicator(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWelcomeSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '选择输入方式',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: UIConstants.paddingSmall),
        Text(
          '快速记录，自动摘要，自动同步',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
        ),
      ],
    );
  }

  Widget _buildInputModeCard({
    required BuildContext context,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required Color backgroundColor,
    required VoidCallback onTap,
    bool isEnabled = true,
  }) {
    return Card(
      elevation: isEnabled ? 4 : 1,
      color: isEnabled ? backgroundColor : Colors.grey[200],
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusLarge),
      ),
      child: InkWell(
        onTap: isEnabled ? onTap : null,
        borderRadius: BorderRadius.circular(UIConstants.borderRadiusLarge),
        child: Padding(
          padding: const EdgeInsets.all(UIConstants.paddingLarge),
          child: Row(
            children: [
              // Icon
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: isEnabled ? color.withOpacity(0.15) : Colors.grey[300],
                  borderRadius:
                      BorderRadius.circular(UIConstants.borderRadiusMedium),
                ),
                child: Icon(
                  icon,
                  size: UIConstants.iconSizeExtraLarge,
                  color: isEnabled ? color : Colors.grey[500],
                ),
              ),
              const SizedBox(width: UIConstants.paddingMedium),

              // Text content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          title,
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: isEnabled
                                    ? Theme.of(context).colorScheme.onSurface
                                    : Colors.grey[600],
                              ),
                        ),
                        if (!isEnabled) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.grey[400],
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              '即将推出',
                              style: Theme.of(context)
                                  .textTheme
                                  .labelSmall
                                  ?.copyWith(
                                    color: Colors.white,
                                  ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: isEnabled
                                ? Theme.of(context)
                                    .colorScheme
                                    .onSurface
                                    .withOpacity(0.7)
                                : Colors.grey[500],
                          ),
                    ),
                  ],
                ),
              ),

              // Arrow icon
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: UIConstants.iconSizeMedium,
                color: isEnabled ? color : Colors.grey[400],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRecentRecordsButton(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => const RecordListPage(),
          ),
        );
      },
      icon: const Icon(Icons.history_rounded),
      label: const Text('查看历史记录'),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(
          horizontal: UIConstants.paddingLarge,
          vertical: UIConstants.paddingMedium,
        ),
      ),
    );
  }

  Widget _buildSyncStatusIndicator() {
    return const Center(
      child: SyncIndicator(compact: false),
    );
  }

  // Navigation methods
  void _navigateToVoiceInput(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const VoiceInputPage(),
      ),
    );
  }

  void _navigateToImageInput(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const ImageInputPage(),
      ),
    );
  }

  void _navigateToTextInput(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const TextInputPage(),
      ),
    );
  }
}
