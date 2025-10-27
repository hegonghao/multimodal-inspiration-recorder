"""
Metrics Collection
指标收集和监控
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta

import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Info

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        # Prometheus 指标
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code']
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        self.llm_requests = Counter(
            'llm_requests_total',
            'Total LLM requests',
            ['provider', 'model', 'status']
        )

        self.llm_tokens = Counter(
            'llm_tokens_total',
            'Total LLM tokens',
            ['provider', 'model', 'type']  # type: prompt, completion
        )

        self.llm_response_time = Histogram(
            'llm_response_time_seconds',
            'LLM response time',
            ['provider', 'model'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
        )

        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['backend', 'operation']
        )

        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['backend', 'operation']
        )

        self.active_connections = Gauge(
            'active_connections',
            'Active connections',
            ['type']
        )

        self.error_rate = Gauge(
            'error_rate',
            'Error rate',
            ['endpoint']
        )

        self.app_info = Info(
            'app_info',
            'Application information'
        )

        # 内存指标（简单实现��
        self._memory_metrics = defaultdict(lambda: deque(maxlen=1000))
        self._error_counts = defaultdict(lambda: deque(maxlen=100))

        # 设置应用信息
        self.app_info.info({
            'version': settings.VERSION,
            'environment': settings.ENVIRONMENT,
            'app_name': settings.APP_NAME
        })

        # 启动指标清理任务
        if settings.METRICS_ENABLED:
            asyncio.create_task(self._cleanup_metrics())

    def increment_request_count(
        self,
        method: str,
        endpoint: str,
        status_code: int
    ):
        """增加请求计数"""
        if settings.METRICS_ENABLED:
            self.request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()

    def record_request_duration(
        self,
        method: str,
        endpoint: str,
        duration: float
    ):
        """记录请求持续时间"""
        if settings.METRICS_ENABLED:
            self.request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

    def increment_llm_requests(
        self,
        provider: str,
        model: str,
        status: str
    ):
        """增加 LLM 请求计数"""
        if settings.METRICS_ENABLED:
            self.llm_requests.labels(
                provider=provider,
                model=model,
                status=status
            ).inc()

    def record_llm_tokens(
        self,
        provider: str,
        model: str,
        token_type: str,
        count: int
    ):
        """记录 LLM token 使用量"""
        if settings.METRICS_ENABLED:
            self.llm_tokens.labels(
                provider=provider,
                model=model,
                type=token_type
            ).inc(count)

    def record_llm_response_time(
        self,
        provider: str,
        model: str,
        response_time: float
    ):
        """记录 LLM 响应时间"""
        if settings.METRICS_ENABLED:
            self.llm_response_time.labels(
                provider=provider,
                model=model
            ).observe(response_time)

    def increment_cache_hits(
        self,
        backend: str,
        operation: str
    ):
        """增加缓存命中计数"""
        if settings.METRICS_ENABLED:
            self.cache_hits.labels(
                backend=backend,
                operation=operation
            ).inc()

    def increment_cache_misses(
        self,
        backend: str,
        operation: str
    ):
        """增加缓存未命中计数"""
        if settings.METRICS_ENABLED:
            self.cache_misses.labels(
                backend=backend,
                operation=operation
            ).inc()

    def set_active_connections(
        self,
        connection_type: str,
        count: int
    ):
        """设置活跃连接数"""
        if settings.METRICS_ENABLED:
            self.active_connections.labels(type=connection_type).set(count)

    def update_error_rate(self, endpoint: str, rate: float):
        """更新错误率"""
        if settings.METRICS_ENABLED:
            self.error_rate.labels(endpoint=endpoint).set(rate)

    def record_custom_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """记录自定义指标"""
        if settings.METRICS_ENABLED:
            logger.debug(f"Recording custom metric: {name} = {value}", extra={
                "metric_name": name,
                "metric_value": value,
                "metric_labels": labels
            })

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics_enabled": settings.METRICS_ENABLED,
            "prometheus_metrics": {
                "http_requests_total": self.request_count._value.get(),
                "llm_requests_total": self.llm_requests._value.get(),
                "llm_tokens_total": self.llm_tokens._value.get(),
                "cache_hits_total": self.cache_hits._value.get(),
                "cache_misses_total": self.cache_misses._value.get(),
            }
        }

    async def _cleanup_metrics(self):
        """定期清理指标"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                # 这里可以添加清理逻辑
                logger.debug("Metrics cleanup completed")
            except Exception as e:
                logger.error(f"Metrics cleanup error: {e}")


# 全局指标收集器实例
metrics = MetricsCollector()


# 指标装饰器
def track_request(operation_name: str):
    """请求跟踪装饰器"""
    def decorator(func: Callable):
        if isinstance(func, type) and hasattr(func, '__call__'):
            # 类方法装饰器
            original_method = func.__call__

            @wraps(original_method)
            async def async_wrapper(self, *args, **kwargs):
                start_time = time.time()
                try:
                    result = await original_method(self, *args, **kwargs)
                    metrics.increment_request_count(
                        method="POST",  # 默认方法，可以根据实际情况调整
                        endpoint=operation_name,
                        status_code=200
                    )
                    return result
                except Exception as e:
                    metrics.increment_request_count(
                        method="POST",
                        endpoint=operation_name,
                        status_code=500
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics.record_request_duration(
                        method="POST",
                        endpoint=operation_name,
                        duration=duration
                    )

            func.__call__ = async_wrapper
            return func

        elif asyncio.iscoroutinefunction(func):
            # 异步函数装饰器
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    metrics.increment_request_count(
                        method="POST",
                        endpoint=operation_name,
                        status_code=200
                    )
                    return result
                except Exception as e:
                    metrics.increment_request_count(
                        method="POST",
                        endpoint=operation_name,
                        status_code=500
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics.record_request_duration(
                        method="POST",
                        endpoint=operation_name,
                        duration=duration
                    )

            return async_wrapper

        else:
            # 同步函数装饰器
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    metrics.increment_request_count(
                        method="POST",
                        endpoint=operation_name,
                        status_code=200
                    )
                    return result
                except Exception as e:
                    metrics.increment_request_count(
                        method="POST",
                        endpoint=operation_name,
                        status_code=500
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    metrics.record_request_duration(
                        method="POST",
                        endpoint=operation_name,
                        duration=duration
                    )

            return sync_wrapper

    return decorator


def track_latency(operation_name: str):
    """延迟跟踪装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.record_custom_metric(
                    f"{operation_name}_duration",
                    duration
                )

        return async_wrapper

    return decorator


def track_error(operation_name: str, labels: Optional[Dict[str, Any]] = None):
    """错误跟踪装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                metrics.record_custom_metric(
                    f"{operation_name}_error",
                    1,
                    labels or {"error_type": type(e).__name__}
                )
                raise

        return async_wrapper

    return decorator


@contextmanager
def track_operation(operation_name: str):
    """操作跟踪上下文管理器"""
    start_time = time.time()
    try:
        yield
    except Exception as e:
        metrics.record_custom_metric(
            f"{operation_name}_error",
            1,
            {"error_type": type(e).__name__}
        )
        raise
    finally:
        duration = time.time() - start_time
        metrics.record_custom_metric(
            f"{operation_name}_duration",
            duration
        )


@asynccontextmanager
async def track_async_operation(operation_name: str):
    """异步操作跟踪上下文管理器"""
    start_time = time.time()
    try:
        yield
    except Exception as e:
        metrics.record_custom_metric(
            f"{operation_name}_error",
            1,
            {"error_type": type(e).__name__}
        )
        raise
    finally:
        duration = time.time() - start_time
        metrics.record_custom_metric(
            f"{operation_name}_duration",
            duration
        )


class HealthMetrics:
    """健康检查指标"""

    def __init__(self):
        self.checks = {}
        self.last_check_time = {}

    def record_health_check(
        self,
        service: str,
        status: str,
        response_time: float,
        error: Optional[str] = None
    ):
        """记录健康检查结果"""
        self.checks[service] = {
            "status": status,
            "response_time": response_time,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.last_check_time[service] = time.time()

        # 记录到 Prometheus
        gauge_value = 1 if status == "healthy" else 0
        metrics.record_custom_metric(
            f"health_check_status",
            gauge_value,
            {"service": service}
        )

        metrics.record_custom_metric(
            f"health_check_response_time",
            response_time,
            {"service": service}
        )

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        healthy_count = sum(
            1 for check in self.checks.values()
            if check["status"] == "healthy"
        )
        total_count = len(self.checks)

        return {
            "overall_status": "healthy" if healthy_count == total_count else "unhealthy",
            "healthy_services": healthy_count,
            "total_services": total_count,
            "checks": self.checks,
            "last_updated": datetime.now().isoformat()
        }


# 全局健康指标实例
health_metrics = HealthMetrics()