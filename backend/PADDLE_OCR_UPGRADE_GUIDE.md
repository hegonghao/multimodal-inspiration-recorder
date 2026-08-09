# PaddleOCR 功能升级指南

> 实现已更新为 PaddleOCR v6 异步 Jobs API。旧版同步版面解析示例不适用于当前
> `backend/src/services/ocr_service.py`，请先阅读 `../PADDLEOCR_V6_MIGRATION.md`。

## 升级概述

本次升级将图片识别模块从 Google Cloud Vision 迁移到 PaddleOCR-VL，并新增多项高级功能。

## 新增功能

### 1. Markdown 结构化输出

**原功能：** 只保存纯文本
```json
{
  "content": "标题\n这是段落内容..."
}
```

**新功能：** 同时保存纯文本和 Markdown
```json
{
  "content": "标题\n这是段落内容...",
  "content_markdown": "# 标题\n\n这是段落内容..."
}
```

**优势：**
- 保留文档结构（标题、段落、列表）
- 更好的排版和阅读体验
- AI 分析更准确

### 2. PDF 文档支持

**新功能：** 支持 PDF 文件上传和多页处理

```bash
# API 调用示例
curl -X POST /api/v1/records/upload \
  -F "input_type=pdf" \
  -F "file=@document.pdf" \
  -F "use_chart_recognition=true"
```

**特性：**
- 自动处理多页 PDF
- 页数统计 (`page_count`)
- 每页内容自动合并

### 3. 图表识别

**新功能：** 自动识别并转换图表

```bash
# 启用图表识别
curl -X POST /api/v1/records/upload \
  -F "input_type=image" \
  -F "file=@chart.png" \
  -F "use_chart_recognition=true"
```

**支持类型：**
- 柱状图
- 饼图
- 折线图
- 表格

### 4. 文档矫正

**新功能：** 自动矫正扭曲和倾斜的文档

```bash
# 启用文档矫正
curl -X POST /api/v1/records/upload \
  -F "input_type=image" \
  -F "file=@skewed.jpg" \
  -F "use_orientation_classify=true" \
  -F "use_unwarping=true"
```

**矫正功能：**
- `use_orientation_classify`: 自动旋转 (0°/90°/180°/270°)
- `use_unwarping`: 扭曲矫正（褶皱、倾斜）

## 数据库变更

### 新增字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `content_markdown` | TEXT | Markdown 格式内容 |
| `pdf_file_path` | VARCHAR(500) | PDF 文件路径 |
| `page_count` | INTEGER | 页数（PDF）|
| `processing_options` | TEXT | OCR 选项（JSON）|

### 迁移脚本

```bash
cd backend
alembic upgrade head  # 运行迁移
```

或手动运行：
```bash
python -m alembic upgrade 002
```

## API 变更

### 请求参数

#### 新增参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_chart_recognition` | boolean | false | 启用图表识别 |
| `use_orientation_classify` | boolean | false | 启用方向矫正 |
| `use_unwarping` | boolean | false | 启用扭曲矫正 |

#### 支持的 input_type

- `text` - 文本输入
- `voice` - 语音输入
- `image` - 图片输入 ✨ **增强**
- `pdf` - PDF 输入 🆕 **新增**

### 响应格式

#### 新增字段

```json
{
  "id": 1,
  "title": "文档标题",
  "content": "纯文本内容...",
  "content_markdown": "# 文档标题\n\n内容...",
  "input_type": "pdf",
  "page_count": 5,
  "ocr_confidence": 0.95,
  "processing_options": "{\"chart_recognition\": true}"
}
```

## 使用示例

### 1. 基础图片 OCR

```python
import requests

# 上传图片
with open("screenshot.png", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/records/upload",
        files={"file": f},
        data={
            "input_type": "image",
            "language": "zh",
            "auto_process": True
        }
    )

result = response.json()
print(f"纯文本: {result['content']}")
print(f"Markdown: {result['content_markdown']}")
```

### 2. PDF 文档处理

```python
# 上传 PDF
with open("report.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/records/upload",
        files={"file": f},
        data={
            "input_type": "pdf",
            "language": "zh",
            "use_chart_recognition": True
        }
    )

result = response.json()
print(f"页数: {result['page_count']}")
print(f"内容: {result['content_markdown']}")
```

### 3. 图表识别

```python
# 识别图表
with open("chart.png", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/records/upload",
        files={"file": f},
        data={
            "input_type": "image",
            "use_chart_recognition": True
        }
    )

# Markdown 中包含识别的表格
result = response.json()
print(result['content_markdown'])
```

### 4. 文档矫正

```python
# 处理扭曲图片
with open("skewed.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/records/upload",
        files={"file": f},
        data={
            "input_type": "image",
            "use_orientation_classify": True,
            "use_unwarping": True
        }
    )
```

## 性能对比

| 指标 | Google Vision | PaddleOCR-VL |
|------|---------------|--------------|
| 纯文本识别 | ✓ | ✓ |
| Markdown 输出 | ✗ | ✓ |
| PDF 支持 | ✗ | ✓ |
| 图表识别 | ✗ | ✓ |
| 文档矫正 | ✗ | ✓ |
| 多页处理 | ✗ | ✓ |

## AI 处理增强

### Markdown 内容优先

AI 处理器现在优先使用 Markdown 内容：

```python
# 自动选择最佳格式
content_for_ai = content_markdown if content_markdown else content

# 生成标题和分类
ai_result = await ai_processor.process_content(
    content_for_ai,
    input_type=input_type,
    language=language
)
```

**优势：**
- 更好的段落识别
- 更准确的标题提取
- 更合理的分类

## 向后兼容性

### 完全兼容

所有现有 API 调用无需修改：

```python
# 旧代码 - 继续工作
response = requests.post(
    "/api/v1/records/upload",
    files={"file": image_file},
    data={"input_type": "image"}
)
```

### 可选功能

新功能通过可选参数启用：

```python
# 新代码 - 启用新功能
response = requests.post(
    "/api/v1/records/upload",
    files={"file": image_file},
    data={
        "input_type": "image",
        "use_chart_recognition": True  # 可选
    }
)
```

## 故障排查

### 问题 1：迁移失败

**症状：** `alembic upgrade` 报错

**解决：**
```bash
# 检查当前版本
alembic current

# 如果卡在旧版本，强制升级
alembic stamp head
alembic upgrade 002
```

### 问题 2：PDF 上传失败

**症状：** PDF 文件无法识别

**检查：**
1. 文件大小是否超限
2. PDF 是否为扫描版（图片）而非文本版
3. PaddleOCR API 配置是否正确

**解决：**
```python
# 检查 PDF 类型
import PyPDF2
with open("test.pdf", "rb") as f:
    pdf = PyPDF2.PdfReader(f)
    # 如果无法提取文本，说明是扫描版，需要 OCR
```

### 问题 3：Markdown 内容为空

**症状：** `content_markdown` 字段为 null

**原因：** PaddleOCR 可能未返回 Markdown

**解决：**
- 旧记录：`content_markdown` 可能为空（正常）
- 新记录：检查 PaddleOCR API 响应
- 降级方案：使用 `content` 字段（纯文本）

## 测试清单

- [ ] 图片 OCR 基本功能
- [ ] PDF 文档识别
- [ ] Markdown 格式保存
- [ ] 图表识别功能
- [ ] 文档矫正功能
- [ ] 多页 PDF 处理
- [ ] AI 分析 Markdown 内容
- [ ] 向后兼容性测试

## 相关文档

- [OCR 服务迁移指南](OCR_MIGRATION_GUIDE.md)
- [PaddleOCR API 文档](PaddleOCR-VL 服务化部署调用示例及 API 介绍.txt)
- [数据库迁移脚本](alembic/versions/002_add_paddle_ocr_fields.py)

---

**升级完成时间：** 2025-11-07
**维护者：** Claude Code (Linus Torvalds Mode) 🐧
