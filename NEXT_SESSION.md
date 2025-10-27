# 下次会话快速开始指南

**当前状态**: Phase 1完成，Phase 2进行中 (1/12任务完成)
**Git提交**: 1ef14b9
**分支**: 1-multimodal-capture
**进度**: 9/104任务 (8.7%)

---

## 🎯 下次会话立即执行

### 从T010开始: Database Connection Management

**任务**: 实现backend/src/database/connection.py

**需要实现的内容**:

```python
"""
backend/src/database/connection.py

1. 创建SQLAlchemy async engine
   - 使用aiosqlite
   - 配置from config.DATABASE_URL
   - 启用WAL模式
   - 设置connection pool

2. 实现AsyncSession factory
   - 使用sessionmaker
   - 配置expire_on_commit=False
   - 支持async context manager

3. 创建依赖注入函数
   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       - 用于FastAPI Depends()
       - 自动commit/rollback
       - 异常处理

4. 实现数据库初始化函数
   async def init_db():
       - 创建所有表
       - 运行Alembic迁移
       - 插入默认数据(UserPreferences)

5. 实现数据库关闭函数
   async def close_db():
       - 清理连接池
       - 关闭engine
```

**参考**:
- `specs/1-multimodal-capture/data-model.md` - 完整的数据模型定义
- `backend/src/config.py` - 现有配置（需扩展DATABASE_URL等）
- SQLAlchemy 2.0 async文档: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

---

## 📋 Phase 2剩余任务清单

完成T010后，按顺序执行：

### **可以并行的任务组**:

**组1**: 数据库相关 (T010-T011)
- ⏳ T010: Backend database connection
- ⏳ T011: Flutter Drift database class

**组2**: Entity模型 (T012-T014) - 依赖T010完成
- ⏳ T012: InspirationRecord entity
- ⏳ T013: SyncQueue entity
- ⏳ T014: UserPreferences entity

**组3**: API基础设施 (T015-T016) - 依赖T012-T014完成
- ⏳ T015: API routing structure
- ⏳ T016: Error handling middleware

**组4**: 配置和服务 (T017-T018)
- ⏳ T017: Logging infrastructure
- ⏳ T018: Environment configuration

**组5**: Flutter客户端服务 (T019-T020) - 可与组3-4并行
- ⏳ T019: API client service
- ⏳ T020: Local storage service

---

## 🚀 快速命令参考

### 检查当前状态
```bash
git status
git log --oneline -5
git diff HEAD~1
```

### 验证开发环境
```bash
# Python后端
cd backend
python --version  # 应该是3.11+
pip list | grep fastapi

# Flutter前端
cd app
flutter --version  # 应该是3.16+
flutter doctor

# Redis
redis-cli ping  # 应返回PONG
```

### 运行代码质量检查
```bash
# Python linting
cd backend
ruff check src/
black --check src/
mypy src/

# Flutter linting
cd app
flutter analyze
```

### 查看设计文档
```bash
# 快速查看关键设计
cat specs/1-multimodal-capture/data-model.md | head -100
cat specs/1-multimodal-capture/tasks.md | grep "T010"
```

---

## 📊 预期完成时间

| 任务范围 | 预计时间 | Token使用 |
|---------|---------|-----------|
| T010 (Database connection) | 30分钟 | ~8K tokens |
| T011 (Drift database) | 45分钟 | ~12K tokens |
| T012-T014 (3个Entity) | 1.5小时 | ~20K tokens |
| T015-T018 (API基础设施) | 1小时 | ~15K tokens |
| T019-T020 (Flutter服务) | 45分钟 | ~10K tokens |
| **Phase 2总计** | **4-5小时** | **~65K tokens** |

---

## 📁 关键文件路径

### 需要创建的文件（按优先级）:
```
backend/src/database/
├── connection.py          # T010 - 下一个任务
├── base.py               # SQLAlchemy Base类
└── migrations/
    └── versions/
        └── 001_initial.py  # Alembic迁移脚本

backend/src/models/
├── inspiration.py        # T012 - InspirationRecord
├── sync_queue.py         # T013 - SyncQueue
└── user_preferences.py   # T014 - UserPreferences

app/lib/data/
├── database.dart         # T011 - Drift database
└── models/
    ├── inspiration_record.dart
    ├── sync_queue.dart
    └── user_preferences.dart
```

### 需要扩展的现有文件:
```
backend/src/config.py     # 添加数据库配置
backend/src/main.py       # 添加数据库初始化
```

---

## 🔍 重要提醒

### 代码规范
1. **Python**: 使用async/await，所有DB操作必须是异步的
2. **类型注解**: Python和Dart都必须有完整类型注解
3. **错误处理**: 所有DB操作都要有try-except
4. **日志**: 使用structlog（backend）和logger（Flutter）

### 数据模型一致性
确保backend和frontend的模型字段完全一致：
- InspirationRecord: 15个字段
- SyncQueue: 11个字段
- UserPreferences: 13个字段

参考 `specs/1-multimodal-capture/data-model.md` 第1-5节

### 测试要求
每完成一个Entity模型，应同时创建对应的单元测试：
```
backend/tests/unit/models/
├── test_inspiration.py
├── test_sync_queue.py
└── test_user_preferences.py
```

---

## 💡 实现建议

### T010实现提示

1. **启用SQLite WAL模式**:
```python
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

2. **异步session管理**:
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

3. **数据库初始化**:
```python
async def init_db():
    async with engine.begin() as conn:
        # 如果表不存在则创建
        await conn.run_sync(Base.metadata.create_all)

    # 插入默认UserPreferences
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        if not result.scalar_one_or_none():
            default_prefs = UserPreferences(id=1)
            session.add(default_prefs)
            await session.commit()
```

---

## 📞 遇到问题时

### 常见问题快速解决

**问题1**: SQLAlchemy导入错误
```bash
pip install sqlalchemy[asyncio] aiosqlite
```

**问题2**: Alembic无法找到模型
- 确保在`alembic/env.py`中导入所有模型
- 设置`target_metadata = Base.metadata`

**问题3**: Drift生成代码错误
```bash
cd app
flutter pub run build_runner build --delete-conflicting-outputs
```

**问题4**: 类型检查失败
```bash
# Python
mypy --install-types
mypy src/database/connection.py

# Flutter
dart analyze
```

---

## ✅ 会话目标检查清单

完成Phase 2前，确保：

- [ ] T010: Backend database connection可以正常创建和关闭
- [ ] T011: Flutter Drift database可以正常初始化
- [ ] T012-T014: 所有3个Entity模型已创建并通过测试
- [ ] T015: FastAPI路由结构就绪
- [ ] T016: 错误处理中间件配置完成
- [ ] T017: 日志系统正常工作
- [ ] T018: 所有环境变量正确加载
- [ ] T019: Flutter API client可以调用后端
- [ ] T020: Flutter本地存储可以读写数据

**验证方式**:
```bash
# Backend健康检查
curl http://localhost:8000/health

# 数据库连接测试
python -m pytest backend/tests/unit/database/

# Flutter构建测试
flutter build apk --debug
```

---

**创建时间**: 2025-10-27
**预计下次会话时长**: 4-5小时
**预计Token使用**: 65K tokens
**建议休息**: 每完成2-3个任务后短暂休息5分钟
