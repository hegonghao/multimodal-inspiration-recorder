# PaddleOCR v6 配置与验证

当前后端已使用 PaddleOCR v6 的异步 Jobs API，不再使用旧的 Base64 JSON `layout-parsing` 接口。

## 环境变量

在项目根目录 `.env` 设置，Token 不要提交 Git：

```env
PADDLEOCR_API_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
PADDLEOCR_TOKEN=你的新Token
PADDLEOCR_MODEL=PP-OCRv6
PADDLEOCR_POLL_INTERVAL=5
PADDLEOCR_JOB_TIMEOUT=300
PADDLEOCR_REQUEST_TIMEOUT=60
```

如果之前使用过旧的 `layout-parsing` 地址或 Token，必须同时替换 URL 和 Token。旧 Token 返回 `401` 时不会自动降级到旧协议。

## 后端调用流程

1. 本地文件使用 multipart `POST /api/v2/ocr/jobs`。
2. 远程文件使用 JSON `fileUrl` 提交。
3. 请求头使用 `Authorization: bearer <TOKEN>`。
4. 读取 `data.jobId`，轮询 `/jobs/{jobId}`。
5. `state=done` 后下载 `data.resultUrl.jsonUrl` 指向的 JSONL。
6. 从 `ocrResults.prunedResult.rec_texts` 等 V6 字段提取文本，并转换为现有业务层返回格式。

`content_markdown` 字段仍保留以兼容数据库和客户端，但 PP-OCRv6 纯 OCR 输出没有旧版版面 Markdown 时，该字段会使用纯文本内容。

## 验证

离线协议回归测试：

```bash
cd backend
python -m unittest tests.unit.test_ocr_service_v6 -v
```

使用仓库测试图片做真实验证（会调用外部 API）：

```bash
cd backend
python test_ocr_with_real_image.py
```

不要把 Token 写入命令历史、日志或代码；真实验证后如 Token 曾公开粘贴，应在 PaddleOCR 控制台轮换。
