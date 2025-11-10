import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:math' as math;

import '../providers/inspiration_provider.dart';
import '../../data/services/accessibility_service.dart';

/// Voice Recorder Widget
///
/// Interactive voice recording interface with:
/// - Record/Pause/Resume/Stop controls
/// - Real-time duration display
/// - Audio amplitude visualization
/// - 5-minute countdown
/// - Cancel option
class VoiceRecorderWidget extends StatefulWidget {
  final void Function(File audioFile)? onRecordingComplete;
  final VoidCallback? onRecordingCancelled;

  const VoiceRecorderWidget({
    Key? key,
    this.onRecordingComplete,
    this.onRecordingCancelled,
  }) : super(key: key);

  @override
  State<VoiceRecorderWidget> createState() => _VoiceRecorderWidgetState();
}

class _VoiceRecorderWidgetState extends State<VoiceRecorderWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  final AccessibilityService _a11y = AccessibilityService();

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<InspirationProvider>(
      builder: (context, provider, child) {
        final isRecording = provider.isRecording;
        final duration = provider.recordingDuration;
        final amplitude = provider.audioAmplitude;
        final remainingSeconds = provider.getRemainingSeconds();

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
              // Title with semantic label
              Semantics(
                label: isRecording ? '正在录音' : '语音记录',
                header: true,
                child: Text(
                  isRecording ? '正在录音' : '语音记录',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ),
              const SizedBox(height: 32),

              // Amplitude Visualization (decorative, excluded from semantics)
              if (isRecording)
                ExcludeSemantics(
                  child: _buildAmplitudeVisualizer(amplitude),
                ),
              if (isRecording) const SizedBox(height: 32),

              // Record Button
              _buildRecordButton(context, provider, isRecording),
              const SizedBox(height: 24),

              // Duration Display with semantic label
              Semantics(
                label: _a11y.getRecordingStatusLabel(isRecording, duration),
                liveRegion: true,
                child: Text(
                  _formatDuration(duration),
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
              const SizedBox(height: 8),

              // Remaining Time
              if (isRecording)
                Text(
                  '剩余时间: ${_formatSeconds(remainingSeconds)}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: remainingSeconds < 30
                            ? Colors.red
                            : Colors.grey[600],
                      ),
                ),
              const SizedBox(height: 24),

              // Control Buttons
              if (isRecording) _buildControlButtons(context, provider),

              // Info Text
              if (!isRecording)
                Text(
                  '点击麦克风按钮开始录音\n最长支持5分钟录音',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                      ),
                ),
            ],
          ),
        );
      },
    );
  }

  /// Build amplitude visualizer (waveform)
  Widget _buildAmplitudeVisualizer(double amplitude) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        return Container(
          height: 80,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: List.generate(20, (index) {
              // Create wave effect
              final offset = (index - 10).abs() / 10.0;
              final wave = math.sin(
                (_pulseController.value * 2 * math.pi) + (index * 0.3),
              );
              final height = 20 + (amplitude * 60 * (1 - offset)) + (wave * 10);

              return Container(
                width: 4,
                height: height.clamp(10.0, 80.0),
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: Theme.of(context).primaryColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              );
            }),
          ),
        );
      },
    );
  }

  /// Build record button (mic icon)
  Widget _buildRecordButton(
    BuildContext context,
    InspirationProvider provider,
    bool isRecording,
  ) {
    final duration = provider.recordingDuration;
    final label = _a11y.getVoiceRecordingButtonLabel(
      isRecording: isRecording,
      isPaused: false,
      duration: duration,
    );
    final hint = _a11y.getVoiceRecordingHint(isRecording: isRecording);

    return Semantics(
      label: label,
      hint: hint,
      button: true,
      enabled: true,
      onTap: () async {
        if (!isRecording) {
          final success = await provider.startRecording();
          if (success) {
            _a11y.announce(context, '开始录音');
          } else if (provider.error != null) {
            _a11y.announceError(context, provider.error!);
            _showError(context, provider.error!);
          }
        } else {
          final audioFile = await provider.stopRecording();
          if (audioFile != null) {
            _a11y.announceComplete(context, '录音已完成');
            widget.onRecordingComplete?.call(audioFile);
          } else if (provider.error != null) {
            _a11y.announceError(context, provider.error!);
            _showError(context, provider.error!);
          }
        }
      },
      child: GestureDetector(
        onTap: () async {
          if (!isRecording) {
            final success = await provider.startRecording();
            if (success) {
              _a11y.announce(context, '开始录音');
            } else if (provider.error != null) {
              _a11y.announceError(context, provider.error!);
              _showError(context, provider.error!);
            }
          } else {
            final audioFile = await provider.stopRecording();
            if (audioFile != null) {
              _a11y.announceComplete(context, '录音已完成');
              widget.onRecordingComplete?.call(audioFile);
            } else if (provider.error != null) {
              _a11y.announceError(context, provider.error!);
              _showError(context, provider.error!);
            }
          }
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isRecording ? Colors.red : Theme.of(context).primaryColor,
            boxShadow: [
              BoxShadow(
                color: (isRecording ? Colors.red : Theme.of(context).primaryColor)
                    .withOpacity(0.3),
                blurRadius: 20,
                spreadRadius: isRecording ? 5 : 0,
              ),
            ],
          ),
          child: Icon(
            isRecording ? Icons.stop : Icons.mic,
            size: 48,
            color: Colors.white,
          ),
        ),
      ),
    );
  }

  /// Build control buttons (pause/resume/cancel)
  Widget _buildControlButtons(
    BuildContext context,
    InspirationProvider provider,
  ) {
    final isPaused = provider.isRecording && provider.recordingDuration.inSeconds == 0;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        // Cancel Button with accessibility
        Semantics(
          label: '取消录音按钮',
          hint: '点击取消当前录音',
          button: true,
          child: OutlinedButton.icon(
            onPressed: () async {
              await provider.cancelRecording();
              _a11y.announce(context, '录音已取消');
              widget.onRecordingCancelled?.call();
            },
            icon: const Icon(Icons.close),
            label: const Text('取消'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.red,
              side: const BorderSide(color: Colors.red),
            ),
          ),
        ),

        // Pause/Resume Button with accessibility
        Semantics(
          label: isPaused ? '继续录音按钮' : '暂停录音按钮',
          hint: isPaused ? '点击继续录音' : '点击暂停录音',
          button: true,
          child: OutlinedButton.icon(
            onPressed: () async {
              if (isPaused) {
                await provider.resumeRecording();
                _a11y.announce(context, '录音已继续');
              } else {
                await provider.pauseRecording();
                _a11y.announce(context, '录音已暂停');
              }
            },
            icon: Icon(isPaused ? Icons.play_arrow : Icons.pause),
            label: Text(isPaused ? '继续' : '暂停'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Theme.of(context).primaryColor,
            ),
          ),
        ),
      ],
    );
  }

  /// Format duration as MM:SS
  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  /// Format seconds as MM:SS
  String _formatSeconds(int totalSeconds) {
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
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

/// Compact Voice Recorder Button
///
/// A simplified button for quick voice recording access
class CompactVoiceRecorderButton extends StatelessWidget {
  final VoidCallback onPressed;

  const CompactVoiceRecorderButton({
    Key? key,
    required this.onPressed,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton(
      onPressed: onPressed,
      tooltip: '语音记录',
      child: const Icon(Icons.mic),
    );
  }
}
