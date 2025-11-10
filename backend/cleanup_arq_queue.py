#!/usr/bin/env python3
"""Clean up ARQ queue to remove stale job references"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from arq import create_pool
from arq.connections import RedisSettings
from src.config import settings


async def cleanup_arq_queue():
    """Clean up ARQ queue"""
    print("\n" + "=" * 60)
    print("Cleanup ARQ Queue")
    print("=" * 60)

    # Create Redis connection
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )

    redis = await create_pool(redis_settings)

    try:
        # Get all ARQ keys
        keys = await redis.keys("arq:*")
        print(f"\n找到 {len(keys)} 个ARQ键:")

        # Group keys by type
        job_keys = [k for k in keys if b":job:" in k]
        queue_keys = [k for k in keys if b":queue" in k]
        result_keys = [k for k in keys if b":result:" in k]
        other_keys = [k for k in keys if k not in job_keys + queue_keys + result_keys]

        print(f"  - Job keys: {len(job_keys)}")
        print(f"  - Queue keys: {len(queue_keys)}")
        print(f"  - Result keys: {len(result_keys)}")
        print(f"  - Other keys: {len(other_keys)}")

        # Show queue contents
        for queue_key in queue_keys:
            queue_key_str = queue_key.decode('utf-8')
            queue_length = await redis.llen(queue_key)
            print(f"\n  Queue: {queue_key_str}")
            print(f"    Length: {queue_length}")

            if queue_length > 0 and queue_length < 20:
                items = await redis.lrange(queue_key, 0, -1)
                print(f"    Items: {[item.decode('utf-8') for item in items]}")

        # Clean up old job and result keys
        if job_keys or result_keys:
            print(f"\n🗑️  清理 {len(job_keys)} 个job键和 {len(result_keys)} 个result键...")

            deleted_count = 0
            for key in job_keys + result_keys:
                await redis.delete(key)
                deleted_count += 1

            print(f"✅ 已删除 {deleted_count} 个旧键")
        else:
            print("\n✅ 没有需要清理的job或result键")

        print("\n" + "=" * 60)
        print("✅ ARQ队列清理完成")
        print("   建议：重启worker以确保队列完全清空")
        print("   命令：docker-compose restart worker")
        print("=" * 60)

    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(cleanup_arq_queue())
