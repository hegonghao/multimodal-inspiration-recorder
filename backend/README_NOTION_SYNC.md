# Notion Sync Implementation Guide

## Overview

This document describes the Notion synchronization system implemented for the Multi-Modal Inspiration Recorder. The system provides offline-first functionality with automatic background synchronization to Notion.

## Architecture

### Components

1. **Notion API Client** (`backend/src/services/notion_sync.py`)
   - Handles API communication with Notion
   - Implements rate limiting (3 req/s = 400ms delay)
   - Exponential backoff retry (4s min, 60s max, 5 attempts)
   - Respects Retry-After headers for 429 responses

2. **ARQ Task Queue Worker** (`backend/src/app/worker.py`)
   - Processes sync tasks asynchronously
   - Scheduled job runs every minute to check for pending tasks
   - Handles create/update/delete operations
   - Updates database after successful sync

3. **Sync Queue Service** (`backend/src/services/sync_service.py`)
   - Manages sync task queue
   - Enqueues tasks with priority handling
   - Tracks sync status and statistics
   - Cleanup old completed tasks

4. **Sync API Endpoints** (`backend/src/api/v1/endpoints/sync.py`)
   - `GET /sync/status` - Get overall sync status
   - `POST /sync/trigger` - Manually trigger sync
   - `GET /sync/queue` - View sync queue
   - `POST /sync/retry-failed` - Retry failed tasks
   - `GET /sync/tasks/{id}` - Get task details
   - `GET /sync/tasks/record/{id}` - Get tasks for a record

## Database Models

### SyncQueue Table
```sql
- id: Primary key
- record_id: Foreign key to inspiration_records
- operation: create | update | delete
- status: 0=PENDING | 1=PROCESSING | 2=COMPLETED | 3=FAILED
- priority: 0=NORMAL | 1=HIGH | 2=URGENT
- retry_count: Current retry attempt
- max_retries: Maximum retry attempts (default: 5)
- next_retry_at: Scheduled retry timestamp
- error_message: Last error message
- created_at: Task creation time
- completed_at: Task completion time
```

### InspirationRecord Sync Fields
```sql
- notion_page_id: Notion page ID (unique)
- sync_status: 0=PENDING | 1=SYNCING | 2=SYNCED | 3=FAILED | 4=CONFLICT
```

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Notion Integration
NOTION_TOKEN=secret_xxx...
NOTION_DATABASE_ID=xxx-xxx-xxx-xxx
NOTION_SYNC_ENABLED=true
NOTION_SYNC_INTERVAL_MINUTES=15
NOTION_SYNC_BATCH_SIZE=10

# Redis for ARQ
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=
```

### Settings (backend/src/config.py)
```python
NOTION_TOKEN: Optional[str] = None
NOTION_DATABASE_ID: Optional[str] = None
NOTION_SYNC_ENABLED: bool = False
NOTION_SYNC_INTERVAL_MINUTES: int = 15
NOTION_SYNC_BATCH_SIZE: int = 10
```

## Sync Strategy

### Mixed Sync Mode

The system uses a combination of sync strategies:

1. **Immediate Sync** (High Priority)
   - User manually triggers sync
   - New records with auto-sync enabled
   - Priority = HIGH, enqueued immediately

2. **Scheduled Sync** (Background)
   - ARQ worker checks every 1 minute
   - Processes pending tasks in batches
   - Batch size: configurable (default: 10)

3. **Batch Processing**
   - Processes multiple tasks efficiently
   - Rate limiting compliance (400ms between requests)
   - Priority ordering: URGENT > HIGH > NORMAL

4. **Network Recovery**
   - Failed tasks use exponential backoff
   - Retry schedule: 4s, 8s, 16s, 32s, 60s (max)
   - Max retry attempts: 5

## Retry Logic

### Exponential Backoff

Implemented in two layers:

**1. Notion API Level** (notion_sync.py)
```python
@retry(
    retry=retry_if_exception_type(APIResponseError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
```

**2. Task Queue Level** (sync_queue.py)
```python
def calculate_next_retry(self) -> datetime:
    """Exponential backoff: 4s, 8s, 16s, 32s, 60s (capped)"""
    delay_seconds = min(4 * (2 ** self.retry_count), 60)
    return datetime.utcnow() + timedelta(seconds=delay_seconds)
```

### Retry-After Header Support

When Notion returns 429 rate limit:
1. Extract `Retry-After` header (default: 10s)
2. Sleep for specified duration
3. Re-raise exception for tenacity retry
4. Continues exponential backoff

## Notion Database Schema

### Required Properties

The Notion database must have these properties:

| Property Name | Type | Description |
|--------------|------|-------------|
| 名称 | Title | Record title |
| 内容 | Rich Text | Original content |
| 输入方式 | Select | voice \| 文字 \| 图片 |
| 分类 | Multi-select | AI-generated categories |
| 摘要 | Rich Text | AI-generated summary |
| 创建时间 | Date | Creation timestamp |
| 更新时间 | Date | Update timestamp |
| 来源 | Select | "灵感记录器" marker |

### Property Limits

- Title: 100 characters (Notion limit)
- Rich Text: 2000 characters (Notion limit)
- Multi-select: Max 5 categories

## Running the Worker

### Start ARQ Worker

```bash
# Development
cd backend
arq src.app.worker.WorkerSettingsClass

# Production with multiple workers
arq src.app.worker.WorkerSettingsClass --max-jobs 20
```

### Worker Configuration

```python
class WorkerSettingsClass:
    functions = [sync_inspiration_to_notion]
    cron_jobs = [scheduled_sync_check]  # Runs every minute

    max_jobs = 10          # Concurrent jobs
    job_timeout = 300      # 5 minutes
    max_tries = 5          # Max retry attempts
    keep_result = 3600     # Keep results for 1 hour
```

## API Usage Examples

### Get Sync Status

```bash
GET /api/v1/sync/status

Response:
{
  "total_records": 100,
  "synced_count": 85,
  "pending_count": 10,
  "failed_count": 5,
  "last_sync_at": "2025-10-27T10:00:00Z",
  "next_sync_at": "2025-10-27T10:15:00Z",
  "sync_enabled": true
}
```

### Trigger Manual Sync

```bash
POST /api/v1/sync/trigger?batch_size=20

Response:
{
  "status": "success",
  "enqueued_count": 15,
  "failed_count": 0,
  "total_pending": 15
}
```

### Sync Specific Records

```bash
POST /api/v1/sync/trigger
Content-Type: application/json

{
  "record_ids": [1, 2, 3]
}

Response:
{
  "status": "success",
  "enqueued_count": 3,
  "failed_count": 0,
  "enqueued_task_ids": [10, 11, 12],
  "failed_record_ids": []
}
```

### View Sync Queue

```bash
GET /api/v1/sync/queue?status_filter=0&limit=50

Response:
{
  "tasks": [
    {
      "id": 1,
      "record_id": 1,
      "operation": "create",
      "status": 0,
      "retry_count": 0,
      "max_retries": 5,
      "priority": 1,
      "created_at": "2025-10-27T10:30:05Z"
    }
  ],
  "total_count": 10
}
```

### Retry Failed Tasks

```bash
POST /api/v1/sync/retry-failed

Response:
{
  "status": "success",
  "reset_count": 5,
  "message": "5 failed tasks reset for retry"
}
```

## Error Handling

### Common Errors

1. **Notion Token Invalid**
   - Error: `APIResponseError 401 Unauthorized`
   - Solution: Check `NOTION_TOKEN` in `.env`

2. **Database ID Invalid**
   - Error: `APIResponseError 404 Not Found`
   - Solution: Check `NOTION_DATABASE_ID` in `.env`

3. **Rate Limit Exceeded**
   - Error: `APIResponseError 429 Too Many Requests`
   - Handling: Automatic retry with Retry-After header

4. **Network Timeout**
   - Error: `TimeoutError` or `ConnectionError`
   - Handling: Exponential backoff retry

5. **Invalid Property Schema**
   - Error: `APIResponseError 400 Bad Request`
   - Solution: Verify Notion database properties match schema

### Logging

Structured logging with `structlog`:

```python
logger.info("sync_task_completed",
    sync_task_id=task_id,
    operation=operation,
    record_id=record_id,
    notion_page_id=page_id)

logger.error("notion_create_failed",
    record_id=record_id,
    error=str(e),
    status_code=e.status)
```

## Monitoring

### Key Metrics

- Total sync tasks (pending/processing/completed/failed)
- Sync success rate
- Average sync latency
- Retry frequency
- Queue backlog size

### Health Checks

```bash
# Verify Notion connection
GET /api/v1/health

# Check ARQ worker status
arq src.app.worker.WorkerSettingsClass --check
```

## Conflict Resolution

### Last-Write-Wins (LWW) Strategy

- Client updates always overwrite Notion data
- No automatic merge or conflict detection
- User notifications for manual intervention:
  - Record updated in Notion: Show warning
  - Sync failed after max retries: Mark as CONFLICT
  - User can resolve by re-syncing or manual edit

## Performance Optimization

### Rate Limiting Compliance

- 3 requests per second limit
- 400ms delay between requests
- Batch processing to minimize API calls

### Connection Pooling

- Redis connection pool for ARQ
- Async database sessions
- Notion client session reuse

### Database Indexing

```sql
CREATE INDEX idx_sync_pending ON sync_queue (status, updated_at DESC);
CREATE INDEX idx_queue_processing ON sync_queue (status, priority DESC, created_at ASC);
CREATE INDEX idx_retry_schedule ON sync_queue (next_retry_at);
```

## Testing

### Unit Tests

```bash
pytest backend/tests/unit/test_notion_sync.py
pytest backend/tests/unit/test_sync_service.py
pytest backend/tests/unit/test_worker.py
```

### Integration Tests

```bash
pytest backend/tests/integration/test_sync_workflow.py
```

### Manual Testing

1. Create test record
2. Trigger sync
3. Verify Notion page created
4. Update record
5. Verify Notion page updated
6. Delete record
7. Verify Notion page archived

## Troubleshooting

### Worker Not Processing Tasks

1. Check Redis connection: `redis-cli ping`
2. Check worker logs: `tail -f logs/worker.log`
3. Verify `NOTION_SYNC_ENABLED=true`
4. Check database for pending tasks: `SELECT * FROM sync_queue WHERE status=0`

### Sync Always Failing

1. Test Notion connection manually
2. Verify database schema matches requirements
3. Check error messages in `sync_queue.error_message`
4. Review API response in logs

### High Queue Backlog

1. Increase `max_jobs` in worker settings
2. Increase `NOTION_SYNC_BATCH_SIZE`
3. Run multiple worker instances
4. Optimize rate limiting delay

## Future Enhancements

- [ ] Bidirectional sync (Notion → App)
- [ ] Incremental sync (only changed records)
- [ ] Conflict detection UI
- [ ] Sync status real-time notifications (WebSocket)
- [ ] Bulk operations optimization
- [ ] Sync metrics dashboard
- [ ] Auto-cleanup old sync tasks
- [ ] Webhook support for Notion changes
