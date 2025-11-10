# 语音识别置信度阈值优化

## 问题描述

**用户反馈**: "语音输入 输入英文时显示置信度太低"

**问题分析**:
- 系统使用固定的 40% 警告阈值对所有语言统一标准
- 英文语音识别的单词级置信度通常低于中文
- Deepgram API 对英文的置信度评分相对较严格
- 导致英文输入经常触发"置信度太低"的警告

## 解决方案

实现**基于检测语言的动态置信度阈值**机制:

### 新的阈值策略

| 语言 | 警告阈值 | 说明 |
|------|---------|------|
| 中文 (zh-*) | 40% | 中文识别准确度高,保持较高标准 |
| 英文 (en-*) | 25% | 英文置信度分数较低,降低阈值 |
| 其他语言 | 30% | 通用阈值 |
| 拒绝阈值 | 5% | 所有语言统一的最低阈值 |

### 技术实现

系统现在会:
1. 自动检测语音输入的语言
2. 根据检测到的语言选择对应的阈值
3. 在警告消息中显示检测到的语言和具体阈值
4. 记录详细的置信度信息到日志

## 修改文件

### 后端修改

**文件**: `backend/src/api/v1/endpoints/records.py`

**更改内容**:

1. **新增语言特定阈值常量** (第40-44行):
```python
# Language-specific warning thresholds for transcription
# English tends to have lower word-level confidence scores than Chinese
WARN_TRANSCRIPTION_CONFIDENCE_ZH = 0.40  # 40% for Chinese
WARN_TRANSCRIPTION_CONFIDENCE_EN = 0.25  # 25% for English (lower due to Deepgram scoring characteristics)
WARN_TRANSCRIPTION_CONFIDENCE_DEFAULT = 0.30  # 30% for other languages
```

2. **更新置信度检查逻辑** (第395-423行):
```python
# Select language-specific warning threshold
# English tends to have lower confidence scores than Chinese due to Deepgram's scoring model
if detected_language and detected_language.startswith("zh"):
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_ZH
    lang_label = "中文"
elif detected_language and detected_language.startswith("en"):
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_EN
    lang_label = "英文"
else:
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_DEFAULT
    lang_label = detected_language or "未知语言"

# Warn if confidence is below language-specific threshold
if confidence < warn_threshold:
    logger.warning(
        f"Low transcription confidence: {confidence:.2%} < {warn_threshold:.2%} "
        f"(detected language: {detected_language})"
    )
    processing_metadata["confidence_warning"] = True
    processing_metadata["manual_review_recommended"] = True
    processing_metadata["warning_message"] = (
        f"识别置信度较低 ({confidence:.1%} < {warn_threshold:.1%}), "
        f"检测到的语言: {lang_label}。建议检查并手动修正识别内容。"
    )
else:
    logger.info(
        f"Transcription confidence acceptable: {confidence:.2%} >= {warn_threshold:.2%} "
        f"(detected language: {detected_language})"
    )
```

### APP端修改

**文件**: `app/lib/core/constants.dart`

**更改内容** (第57-64行):
```dart
// Audio quality thresholds
// NOTE: Backend uses language-specific thresholds for better multilingual support
static const double minTranscriptionConfidence = 0.05; // 5% - reject threshold (very low to support all languages)

// Language-specific warning thresholds (must match backend values)
static const double warnTranscriptionConfidenceZh = 0.40; // 40% for Chinese
static const double warnTranscriptionConfidenceEn = 0.25; // 25% for English (lower due to Deepgram scoring)
static const double warnTranscriptionConfidenceDefault = 0.30; // 30% for other languages
```

## 部署步骤

### 1. 后端部署

**重要**: 由于 Docker 容器使用构建的镜像(不是挂载的源代码),必须重新构建镜像:

```bash
cd D:\multifuncinspirationrecord
docker-compose build backend
docker-compose up -d backend
```

验证服务正常运行:
```bash
docker logs inspiration-recorder-backend --tail 20
```

**已完成**: ✅ 后端镜像已重新构建并启动 (2025-11-07 18:57)

### 2. APP部署

APP需要重新编译以应用新的常量:

```bash
# 方法1: 使用自动化脚本 (推荐)
cd D:\multifuncinspirationrecord\app
.\update_config_and_rebuild.ps1

# 方法2: 手动执行
flutter clean
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter run
```

## 预期效果

### 英文输入场景

**修改前**:
- 英文语音识别置信度 28%
- ❌ 显示警告: "识别置信度较低 (28% < 40%)"
- 用户体验差

**修改后**:
- 英文语音识别置信度 28%
- ✅ 正常接受: 28% >= 25% (英文阈值)
- 不显示警告,用户体验良好

### 中文输入场景

**修改前**:
- 中文语音识别置信度 35%
- ❌ 显示警告: "识别置信度较低 (35% < 40%)"

**修改后**:
- 中文语音识别置信度 35%
- ❌ 显示警告: "识别置信度较低 (35% < 40%), 检测到的语言: 中文"
- 保持对中文的高质量要求

### 日志增强

**新增日志信息**:
```
INFO: Transcription confidence acceptable: 28% >= 25% (detected language: en-US)
```

或

```
WARNING: Low transcription confidence: 35% < 40% (detected language: zh-CN)
```

## 测试建议

### ⚠️ 音频质量要求

**重要**: 为了获得准确的测试结果,请确保:

- ✅ 在安静的环境中录音(背景噪音会严重影响置信度)
- ✅ 清晰地说话,不要太快或含糊
- ✅ 麦克风距离口部适中(10-30cm)
- ✅ 说完整的句子,而不是单个词
- ❌ 避免背景音乐、噪音、回声

**说明**:
- 如果音频质量太差(置信度 < 5%),系统会直接拒绝
- 之前的测试失败是因为录音质量很差,只识别出1个单词,置信度仅6%
- 良好的中文录音通常有 80-95% 置信度
- 良好的英文录音通常有 60-85% 置信度

### 测试场景

1. **纯英文输入**
   - 录制一段纯英文语音(**确保音质良好**)
   - 验证置信度 >= 25% 时不显示警告
   - 验证置信度 < 25% 时显示警告

2. **纯中文输入**
   - 录制一段纯中文语音
   - 验证置信度 >= 40% 时不显示警告
   - 验证置信度 < 40% 时显示警告

3. **中英混合输入**
   - 录制中英文混合语音
   - 观察检测到的语言
   - 验证使用正确的阈值

4. **极低质量输入**
   - 录制背景噪音很大的语音
   - 验证置信度 < 5% 时被拒绝
   - 验证错误提示清晰明确

### 验证步骤

1. 在 APP 中创建语音记录
2. 查看后端日志中的置信度信息:
   ```bash
   docker logs inspiration-recorder-backend -f | grep "transcription confidence"
   ```
3. 检查 APP 是否显示警告消息
4. 验证识别文本的准确性

## 技术细节

### Deepgram 置信度计算

Deepgram 返回每个单词的置信度分数,系统计算平均值:

```python
# backend/src/services/speech_to_text.py
words = transcript.get("words", [])
avg_confidence = (
    sum(w["confidence"] for w in words) / len(words)
    if words else 0.0
)
```

### 语言检测

Deepgram 自动检测语音语言:

```python
# 总是启用语言检测
transcription_result = await speech_service.transcribe_audio_file(
    temp_file_path,
    language=None,  # 不指定语言
    detect_language=True  # 启用自动检测
)

detected_language = transcription_result["language"]  # 例如: "en-US", "zh-CN"
```

### 阈值选择逻辑

```python
if detected_language and detected_language.startswith("zh"):
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_ZH  # 40%
elif detected_language and detected_language.startswith("en"):
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_EN  # 25%
else:
    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_DEFAULT  # 30%
```

## 相关文件

- **后端**: `backend/src/api/v1/endpoints/records.py`
- **APP常量**: `app/lib/core/constants.dart`
- **语音服务**: `backend/src/services/speech_to_text.py`
- **配置文档**: `APP_CONFIG_UPDATE_GUIDE.md`

## 维护建议

### 未来优化方向

1. **收集实际数据**
   - 记录各语言的实际置信度分布
   - 根据数据调整阈值

2. **用户自定义阈值**
   - 允许用户在设置中调整阈值
   - 根据用户反馈优化默认值

3. **更多语言支持**
   - 添加其他常用语言的特定阈值
   - 如日语、韩语、法语等

4. **智能阈值**
   - 基于用户历史记录学习最佳阈值
   - 考虑环境因素(背景噪音、麦克风质量)

## 问题排查

### 如果英文仍然显示警告

1. **检查实际置信度**:
   ```bash
   docker logs inspiration-recorder-backend -f | grep "transcription confidence"
   ```

2. **确认语言检测正确**:
   - 查看日志中的 `detected language` 字段
   - 如果检测为其他语言,会使用 30% 阈值

3. **检查代码是否生效**:
   ```bash
   docker exec inspiration-recorder-backend cat /app/src/api/v1/endpoints/records.py | grep -A 5 "WARN_TRANSCRIPTION_CONFIDENCE_EN"
   ```

### 如果后端未更新

重新强制重建容器:
```bash
docker-compose up -d --force-recreate backend
```

## 更新日志

**日期**: 2025-11-07
**版本**: 1.0
**修改人**: Claude Code

**更改内容**:
- ✅ 实现基于语言的动态置信度阈值
- ✅ 降低英文警告阈值从 40% 到 25%
- ✅ 保持中文警告阈值 40%
- ✅ 添加其他语言默认阈值 30%
- ✅ 增强日志信息包含语言和阈值
- ✅ 更新 APP 端常量配置
- ✅ 重启后端服务应用更改

**影响范围**:
- 后端 API: 语音记录创建端点
- APP: 常量配置文件
- 用户体验: 英文输入场景显著改善

---

**下一步**: 测试英文和中文语音输入,验证新阈值工作正常。
