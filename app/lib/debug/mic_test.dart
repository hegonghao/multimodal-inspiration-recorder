import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';

/// Microphone Test Utility
///
/// Use this to debug microphone issues on Android emulators
///
/// Usage: Add a button in your app to navigate to MicTestPage
class MicTestPage extends StatefulWidget {
  const MicTestPage({Key? key}) : super(key: key);

  @override
  State<MicTestPage> createState() => _MicTestPageState();
}

class _MicTestPageState extends State<MicTestPage> {
  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  double _currentAmplitude = 0.0;
  String _statusMessage = '等待开始测试...';
  List<String> _logs = [];

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  void _addLog(String message) {
    setState(() {
      _logs.insert(0, '[${DateTime.now().toString().substring(11, 19)}] $message');
      if (_logs.length > 20) _logs = _logs.sublist(0, 20);
    });
  }

  Future<void> _testMicrophone() async {
    try {
      // Step 1: Check permission
      _addLog('检查麦克风权限...');
      final status = await Permission.microphone.status;
      _addLog('权限状态: ${status.toString()}');

      if (!status.isGranted) {
        _addLog('请求麦克风权限...');
        final result = await Permission.microphone.request();
        _addLog('权限请求结果: ${result.toString()}');

        if (!result.isGranted) {
          setState(() {
            _statusMessage = '❌ 麦克风权限被拒绝';
          });
          return;
        }
      }

      // Step 2: Check device support
      _addLog('检查设备是否支持录音...');
      final hasPermission = await _recorder.hasPermission();
      _addLog('设备支持录音: $hasPermission');

      if (!hasPermission) {
        setState(() {
          _statusMessage = '❌ 设备不支持录音';
        });
        return;
      }

      // Step 3: List available input devices (if supported)
      _addLog('检查可用的音频输入设备...');
      try {
        final devices = await _recorder.listInputDevices();
        _addLog('找到 ${devices.length} 个音频输入设备');
        for (var device in devices) {
          _addLog('  - ${device.label} (${device.id})');
        }
      } catch (e) {
        _addLog('无法列出音频设备 (可能不支持): $e');
      }

      // Step 4: Start test recording
      _addLog('开始测试录音...');
      const config = RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 128000,
        sampleRate: 44100,
        numChannels: 1,
        autoGain: true,
        echoCancel: true,
        noiseSuppress: true,
      );

      await _recorder.start(config, path: 'test_recording.m4a');
      _addLog('✅ 录音已开始');

      setState(() {
        _isRecording = true;
        _statusMessage = '🎤 正在录音... 对着麦克风说话';
      });

      // Step 5: Monitor amplitude
      _monitorAmplitude();

    } catch (e) {
      _addLog('❌ 错误: $e');
      setState(() {
        _statusMessage = '❌ 测试失败: $e';
      });
    }
  }

  Future<void> _stopTest() async {
    try {
      _addLog('停止录音...');
      final path = await _recorder.stop();
      _addLog('录音已停止，文件路径: $path');

      setState(() {
        _isRecording = false;
        _currentAmplitude = 0.0;
        _statusMessage = path != null
            ? '✅ 测试完成，文件保存成功'
            : '⚠️ 录音停止，但未生成文件';
      });
    } catch (e) {
      _addLog('❌ 停止录音失败: $e');
      setState(() {
        _statusMessage = '❌ 停止失败: $e';
      });
    }
  }

  void _monitorAmplitude() async {
    while (_isRecording) {
      try {
        final amplitude = await _recorder.getAmplitude();
        final normalizedAmplitude = amplitude.current.clamp(-50.0, 0.0);
        final percentage = ((normalizedAmplitude + 50.0) / 50.0 * 100).toInt();

        setState(() {
          _currentAmplitude = (normalizedAmplitude + 50.0) / 50.0;
        });

        // Log significant amplitude changes
        if (percentage > 20) {
          _addLog('检测到音量: $percentage%');
        }

        await Future.delayed(const Duration(milliseconds: 100));
      } catch (e) {
        // Ignore amplitude errors
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('麦克风测试工具'),
        backgroundColor: Colors.blue,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Card
            Card(
              color: Colors.blue[50],
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      _statusMessage,
                      style: Theme.of(context).textTheme.titleMedium,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),

                    // Amplitude Indicator
                    if (_isRecording) ...[
                      Text(
                        '音量: ${(_currentAmplitude * 100).toInt()}%',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 8),
                      LinearProgressIndicator(
                        value: _currentAmplitude,
                        minHeight: 10,
                        backgroundColor: Colors.grey[300],
                        valueColor: AlwaysStoppedAnimation<Color>(
                          _currentAmplitude > 0.5 ? Colors.green : Colors.orange,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _currentAmplitude < 0.1
                            ? '⚠️ 未检测到声音输入！'
                            : _currentAmplitude < 0.3
                                ? '音量较低，请大声说话'
                                : '✅ 麦克风工作正常',
                        style: TextStyle(
                          color: _currentAmplitude < 0.1
                              ? Colors.red
                              : _currentAmplitude < 0.3
                                  ? Colors.orange
                                  : Colors.green,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Control Buttons
            ElevatedButton.icon(
              onPressed: _isRecording ? _stopTest : _testMicrophone,
              icon: Icon(_isRecording ? Icons.stop : Icons.mic),
              label: Text(_isRecording ? '停止测试' : '开始测试麦克风'),
              style: ElevatedButton.styleFrom(
                backgroundColor: _isRecording ? Colors.red : Colors.blue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.all(16),
              ),
            ),
            const SizedBox(height: 8),

            OutlinedButton.icon(
              onPressed: () {
                setState(() {
                  _logs.clear();
                  _statusMessage = '日志已清空';
                });
              },
              icon: const Icon(Icons.clear_all),
              label: const Text('清空日志'),
            ),
            const SizedBox(height: 24),

            // Troubleshooting Tips
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '故障排查指南',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text('1. 确保模拟器 AVD 设置中麦克风选项为 "Host audio input"'),
                    Text('2. 检查主机（你的电脑）麦克风是否工作正常'),
                    Text('3. 重启 Android 模拟器'),
                    Text('4. 在 Windows 设置中允许应用访问麦克风'),
                    Text('5. 尝试使用真机测试'),
                    Text('6. 如果音量为0%，说明模拟器麦克风配置有问题'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Logs
            Text(
              '调试日志',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Container(
              height: 300,
              decoration: BoxDecoration(
                color: Colors.grey[900],
                borderRadius: BorderRadius.circular(8),
              ),
              padding: const EdgeInsets.all(12),
              child: ListView.builder(
                itemCount: _logs.length,
                itemBuilder: (context, index) {
                  return Text(
                    _logs[index],
                    style: const TextStyle(
                      color: Colors.greenAccent,
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
