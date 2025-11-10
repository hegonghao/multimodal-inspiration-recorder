"""
Application Constants
应用常量定义

This module defines all magic numbers and configuration constants
used throughout the application.
"""

# ==================== API Configuration ====================

# API版本
API_V1_PREFIX = "/api/v1"

# 路由前缀
RECORDS_PREFIX = f"{API_V1_PREFIX}/records"
SYNC_PREFIX = f"{API_V1_PREFIX}/sync"
PREFERENCES_PREFIX = f"{API_V1_PREFIX}/preferences"

# ==================== Rate Limiting ====================

# 速率限制（requests per minute）
DEFAULT_RATE_LIMIT = 100      # 普通API请求
UPLOAD_RATE_LIMIT = 20        # 文件上传请求
AUTH_RATE_LIMIT = 10          # 认证请求（如需要）

# 速率限制窗口（秒）
DEFAULT_RATE_WINDOW = 60      # 1分钟
UPLOAD_RATE_WINDOW = 60       # 1分钟

# ==================== File Size Limits ====================

# 文件大小限制（字节）
MAX_AUDIO_SIZE = 50 * 1024 * 1024     # 50MB
MAX_IMAGE_SIZE = 50 * 1024 * 1024     # 50MB
MAX_REQUEST_SIZE = 50 * 1024 * 1024   # 50MB

# 支持的文件类型
SUPPORTED_AUDIO_FORMATS = [".m4a", ".mp3", ".wav", ".aac"]
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".webp"]

# ==================== Recording Constraints ====================

# 录音时长限制（秒）
MIN_VOICE_DURATION = 1        # 最短1秒
MAX_VOICE_DURATION = 300      # 最长5分钟
DEFAULT_VOICE_DURATION = 300  # 默认5分钟

# 自动保存延迟（秒）
AUTO_SAVE_DELAY_VOICE = 3     # 语音停止后3秒
AUTO_SAVE_DELAY_TEXT = 2      # 文字停止后2秒

# ==================== Content Validation ====================

# 文本内容限制（字符数）
MIN_CONTENT_LENGTH = 10       # 最短10字符
MAX_CONTENT_LENGTH = 10000    # 最长10000字符
MIN_TITLE_LENGTH = 1          # 最短1字符
MAX_TITLE_LENGTH = 200        # 最长200字符

# ==================== Storage Limits ====================

# 存储记录数限制
MAX_RECORDS = 1000            # 最多保存1000条记录
CLEANUP_THRESHOLD = 950       # 达到950条时开始清理

# ==================== Sync Configuration ====================

# 同步间隔（秒）
MIN_SYNC_INTERVAL = 300       # 最短5分钟
DEFAULT_SYNC_INTERVAL = 1800  # 默认30分钟
MAX_SYNC_INTERVAL = 86400     # 最长24小时

# 同步重试配置
MAX_SYNC_RETRIES = 5          # 最多重试5次
SYNC_RETRY_BASE_DELAY = 4     # 基础延迟4秒
SYNC_RETRY_MAX_DELAY = 60     # 最大延迟60秒

# 同步批量大小
SYNC_BATCH_SIZE = 10          # 每批10条记录

# ==================== AI Processing ====================

# AI处理超时（秒）
AI_PROCESSING_TIMEOUT = 30    # 30秒超时

# LLM默认配置
LLM_DEFAULT_MAX_TOKENS = 1000
LLM_DEFAULT_TEMPERATURE = 0.7

# OCR配置
OCR_CONFIDENCE_THRESHOLD = 0.7  # 70%置信度阈值
OCR_TIMEOUT = 10                # 10秒超时

# 语音转写配置
STT_CONFIDENCE_THRESHOLD = 0.6  # 60%置信度阈值
STT_TIMEOUT = 30                # 30秒超时

# ==================== Performance Targets ====================

# 性能目标（秒）
TARGET_UI_RESPONSE_TIME = 1.0      # UI响应 <1s
TARGET_RECORDING_START_TIME = 5.0  # 录音启动 <5s
TARGET_VOICE_TRANSCRIBE_TIME = 10.0 # 语音转写 <10s
TARGET_OCR_TIME = 5.0              # OCR识别 <5s
TARGET_AI_PROCESSING_TIME = 3.0    # AI处理 <3s
TARGET_SYNC_TIME = 30.0            # Notion同步 <30s

# ==================== Database ====================

# 数据库配置
DB_POOL_SIZE = 5              # 连接池大小
DB_MAX_OVERFLOW = 10          # 最大溢出连接
DB_POOL_RECYCLE = 3600        # 连接回收时间（秒）

# 批量操作配置
BATCH_INSERT_CHUNK_SIZE = 100  # 批量插入分块大小
BATCH_UPDATE_CHUNK_SIZE = 100  # 批量更新分块大小

# ==================== Caching ====================

# 缓存TTL（秒）
CACHE_TTL_SHORT = 300         # 5分钟（短期）
CACHE_TTL_MEDIUM = 1800       # 30分钟（中期）
CACHE_TTL_LONG = 3600         # 1小时（长期）

# ==================== Logging ====================

# 日志级别
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# ==================== HTTP Status Codes ====================

# 常用状态码（FastAPI已内置，此处仅作文档参考）
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_409_CONFLICT = 409
HTTP_413_REQUEST_TOO_LARGE = 413
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_502_BAD_GATEWAY = 502
HTTP_503_SERVICE_UNAVAILABLE = 503

# ==================== Notion Integration ====================

# Notion API配置
NOTION_RATE_LIMIT = 3         # 3 requests per second
NOTION_BATCH_SIZE = 10        # 批量操作大小
NOTION_TIMEOUT = 30           # 请求超时（秒）

# ==================== Security ====================

# 密码策略
MIN_PASSWORD_LENGTH = 8       # 最短密码长度
MAX_PASSWORD_LENGTH = 128     # 最长密码长度

# Token配置
ACCESS_TOKEN_EXPIRE_MINUTES = 30    # Access token过期时间
REFRESH_TOKEN_EXPIRE_DAYS = 7       # Refresh token过期时间

# API Key配置
MIN_API_KEY_LENGTH = 20       # 最短API密钥长度

# ==================== Feature Flags ====================

# 功能开关（可通过配置动态调整）
FEATURE_VOICE_RECORDING = True
FEATURE_IMAGE_OCR = True
FEATURE_TEXT_INPUT = True
FEATURE_NOTION_SYNC = True
FEATURE_REAL_TIME_TRANSCRIPTION = False  # 实时转写（需要streaming API）

# ==================== Error Messages ====================

# 常用错误信息
ERROR_RECORD_NOT_FOUND = "灵感记录不存在"
ERROR_INVALID_INPUT_TYPE = "无效的输入类型"
ERROR_FILE_TOO_LARGE = "文件过大"
ERROR_CONTENT_TOO_SHORT = "内容过短"
ERROR_CONTENT_TOO_LONG = "内容过长"
ERROR_SYNC_FAILED = "同步失败"
ERROR_AI_PROCESSING_FAILED = "AI处理失败"
ERROR_RATE_LIMIT_EXCEEDED = "请求过于频繁"

# ==================== Success Messages ====================

# 常用成功信息
SUCCESS_RECORD_CREATED = "灵感记录创建成功"
SUCCESS_RECORD_UPDATED = "灵感记录更新成功"
SUCCESS_RECORD_DELETED = "灵感记录删除成功"
SUCCESS_SYNC_TRIGGERED = "同步已触发"
SUCCESS_CONNECTION_TEST_PASSED = "连接测试成功"

# ==================== Version Information ====================

# 应用版本
APP_VERSION = "1.0.0"
API_VERSION = "v1"
MIN_CLIENT_VERSION = "1.0.0"  # 最低支持的客户端版本
