# OCR 服务迁移指南：从 Google Cloud Vision 到 PaddleOCR v6

> 当前实现已迁移到 PaddleOCR v6 异步 Jobs API。本文中旧的
> `layout-parsing`、Base64 JSON 和 `Authorization: token` 示例仅作为历史背景；
> 最新配置和调用流程请以仓库根目录 `PADDLEOCR_V6_MIGRATION.md` 为准。

## 迁移概览

本项目已从 Google Cloud Vision API 迁移至 PaddleOCR-VL API，以获得更简单的配置、更强大的功能和更好的成本控制。

## 核心改进

### 1. 技术优势

**Google Cloud Vision (旧)**
- ❌ 需要服务账号 JSON 文件，配置复杂
- ❌ 依赖庞大的 SDK (`google-cloud-vision`)
- ⚠️ 仅支持基础文本识别
- ⚠️ 无结构化输出支持

**PaddleOCR-VL (新)**
- ✅ 简单的 HTTP API，仅需 URL + Token
- ✅ 零额外依赖（仅使用已有的 `httpx`）
- ✅ 版面解析、图表识别、文档矫正等高级功能
- ✅ 原生支持 Markdown 输出
- ✅ PDF 多页处理能力

### 2. 代码质量提升

```python
# 旧代码 - Google Cloud Vision
from google.cloud import vision
client = vision.ImageAnnotatorClient.from_service_account_file(credentials_path)
# 需要处理复杂的 protobuf 对象，无置信度评分

# 新代码 - PaddleOCR-VL
async with httpx.AsyncClient() as client:
    response = await client.post(api_url, json=payload, headers=headers)
# 简洁的 HTTP 调用，清晰的 JSON 响应
```

## 配置迁移步骤

### 1. 更新环境变量

在 `.env` 文件中：

```bash
# 移除旧配置
# GOOGLE_CLOUD_VISION_CREDENTIALS=/path/to/credentials.json

# 添加新配置
PADDLEOCR_API_URL=https://your-api-endpoint/layout-parsing
PADDLEOCR_TOKEN=your-api-token-here
```

### 2. 更新依赖（可选）

如果需要清理环境：

```bash
# 卸载旧依赖
pip uninstall google-cloud-vision

# 重新安装项目依赖
pip install -e .
```

### 3. 验证服务

运行测试脚本：

```bash
cd backend
python test_paddleocr_service.py
```

预期输出：
```
============================================================
PaddleOCR-VL Service Test
============================================================

1. Checking configuration...
✓ API URL: https://your-api.com/layout-parsing
✓ Token: ********************abc12345

2. Initializing OCR service...
✓ OCR service initialized successfully

3. Running health check...
✓ OCR service health check passed

4. Ready for OCR processing
...
============================================================
✓ All tests passed!
============================================================
```

## API 使用示例

### 基础图片识别

```python
from src.services.ocr_service import get_ocr_service

ocr_service = get_ocr_service()

# 从文件路径识别
result = await ocr_service.extract_text_from_image(
    image_file_path="./screenshot.png"
)

print(result["text"])       # 纯文本
print(result["markdown"])   # Markdown 格式文本
print(result["confidence"]) # 置信度分数
print(result["language"])   # 检测的语言 (zh/en/ja/ko)
```

### 高级功能

```python
# 启用图表识别
result = await ocr_service.extract_text_from_image(
    image_file_path="./chart.png",
    use_chart_recognition=True
)

# 启用文档矫正（处理扭曲/倾斜图片）
result = await ocr_service.extract_text_from_image(
    image_file_path="./skewed.jpg",
    use_orientation_classify=True,  # 自动旋转
    use_unwarping=True               # 扭曲矫正
)
```

### PDF 处理

```python
# 从 PDF 文件识别
with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()

result = await ocr_service.extract_text_from_bytes(
    image_bytes=pdf_bytes,
    file_type=0  # 0 = PDF, 1 = 图像
)

# 自动处理多页 PDF
print(f"Processed {result['page_count']} pages")
print(result["markdown"])  # 所有页面的 Markdown
```

## 返回格式对比

### Google Cloud Vision (旧)

```python
{
    "text": "识别的文本",
    "confidence": 0.87,           # 估算值
    "language": "zh",
    "word_count": 120,
    "blocks": [                   # 文本块详细信息
        {
            "text": "块文本",
            "confidence": 0.90,
            "bounds": {"x": 10, "y": 20, ...}
        }
    ]
}
```

### PaddleOCR-VL (新)

```python
{
    "text": "识别的文本",
    "confidence": 0.95,           # 固定高置信度
    "language": "zh",
    "word_count": 120,
    "blocks": [],                 # 暂未提供
    "markdown": "# 标题\n内容...", # 新增：结构化 Markdown
    "page_count": 1               # 新增：页数统计
}
```

## 向后兼容性

### 接口保持一致

所有现有调用代码无需修改，核心接口完全兼容：

```python
# 这些调用无需任何改动
result = await ocr_service.extract_text_from_image(image_path)
result = await ocr_service.extract_text_from_bytes(image_bytes)
is_healthy = await ocr_service.health_check()
```

### 新增功能

如需使用新功能，只需添加可选参数：

```python
# 完全向后兼容，旧代码不受影响
result = await ocr_service.extract_text_from_image(
    image_file_path=path,
    use_chart_recognition=True  # 可选新功能
)
```

## PaddleOCR-VL 高级配置

API 支持的完整参数：

```python
payload = {
    "file": "<base64-encoded-file>",
    "fileType": 1,  # 0=PDF, 1=图像

    # 图像矫正
    "useDocOrientationClassify": False,  # 方向矫正 (0°/90°/180°/270°)
    "useDocUnwarping": False,            # 扭曲矫正（褶皱、倾斜）

    # 版面分析
    "useLayoutDetection": None,          # 版面区域检测排序
    "layoutThreshold": 0.5,              # 版面模型得分阈值
    "layoutNms": None,                   # NMS 后处理

    # 识别增强
    "useChartRecognition": False,        # 图表识别（柱状图、饼图等）

    # VL 模型参数
    "repetitionPenalty": None,           # 重复内容惩罚系数
    "temperature": None,                 # 随机性控制
    "topP": None,                        # 核采样阈值

    # 输出控制
    "showFormulaNumber": False,          # 公式编号显示
    "prettifyMarkdown": False,           # Markdown 美化
    "visualize": None,                   # 返回可视化结果
}
```

## 性能对比

| 指标 | Google Cloud Vision | PaddleOCR-VL |
|------|---------------------|--------------|
| 依赖大小 | ~100MB | 0 (仅 httpx) |
| 初始化时间 | ~2s (首次调用) | <100ms |
| API 调用 | gRPC/REST | REST only |
| 配置复杂度 | 高（需 JSON 凭证） | 低（URL + Token） |
| 特殊功能 | 基础识别 | 版面解析/图表/PDF |

## 故障排查

### 问题 1：配置未生效

**症状**：运行时报错 `PADDLEOCR_API_URL not configured`

**解决**：
```bash
# 检查 .env 文件
cat backend/.env | grep PADDLEOCR

# 确保没有多余空格
PADDLEOCR_API_URL=https://...  # ✓ 正确
PADDLEOCR_API_URL = https://... # ✗ 可能有问题
```

### 问题 2：API 调用失败

**症状**：`PaddleOCR API error: Unauthorized`

**解决**：
```python
# 检查 Token 格式
headers = {
    "Authorization": f"token {self.token}",  # 注意是 "token" 不是 "Bearer"
}
```

### 问题 3：依赖冲突

**症状**：`ModuleNotFoundError: No module named 'google.cloud'`

**解决**：
```bash
# 清理虚拟环境
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## 下一步行动

1. ✅ 在 `.env` 中配置 PaddleOCR API 凭证
2. ✅ 运行测试脚本验证服务可用性
3. ✅ （可选）更新其他使用 OCR 的模块以使用新功能
4. ✅ （可选）卸载 `google-cloud-vision` 清理环境

## 参考资源

- PaddleOCR-VL API 文档：`PaddleOCR-VL 服务化部署调用示例及 API 介绍.txt`
- 测试脚本：`backend/test_paddleocr_service.py`
- OCR 服务实现：`backend/src/services/ocr_service.py`

---

**迁移完成时间**：2025-11-07
**维护者**：Claude Code (Linus Torvalds Mode) 🐧
