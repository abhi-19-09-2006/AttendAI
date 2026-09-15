"""
Redis Queue (RQ) configuration and setup for background job processing.
"""
import redis
from redis import Redis
from rq import Queue, Worker
from rq.job import JobStatus
from datetime import timedelta
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rq_config")


def get_redis_connection() -> Redis:
    """Get or create Redis connection."""
    try:
        redis_conn = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )
        # Test connection
        redis_conn.ping()
        logger.info("Connected to Redis")
        return redis_conn
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise


def get_queue(name: str = "default") -> Queue:
    """Get a named queue for job processing."""
    redis_conn = get_redis_connection()
    return Queue(name, connection=redis_conn, default_timeout=3600)


def get_call_queue() -> Queue:
    """Get the call processing queue."""
    return get_queue("calls")


def get_retry_queue() -> Queue:
    """Get the retry queue."""
    return get_queue("retries")


def get_campaign_queue() -> Queue:
    """Get the campaign processing queue."""
    return get_queue("campaigns")


def get_followup_queue() -> Queue:
    """Get the follow-up queue."""
    return get_queue("followups")


class RQHealthCheck:
    """Health check utilities for RQ and Redis."""

    @staticmethod
    def check_redis() -> dict:
        """Check Redis connectivity and basic health."""
        try:
            redis_conn = get_redis_connection()
            info = redis_conn.info()
            return {
                "status": "healthy",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_workers() -> dict:
        """Check RQ worker status."""
        try:
            redis_conn = get_redis_connection()
            workers = Worker.all(connection=redis_conn)
            return {
                "status": "ok",
                "worker_count": len(workers),
                "workers": [
                    {
                        "name": w.name,
                        "state": w.get_state(),
                        "job_count": len(w.get_current_job() and [w.get_current_job()] or [])
                    }
                    for w in workers
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    @staticmethod
    def check_queues() -> dict:
        """Check queue status and job counts."""
        try:
            redis_conn = get_redis_connection()
            queues = {
                "calls": Queue("calls", connection=redis_conn),
                "retries": Queue("retries", connection=redis_conn),
                "campaigns": Queue("campaigns", connection=redis_conn),
                "followups": Queue("followups", connection=redis_conn),
            }

            stats = {}
            for queue_name, queue in queues.items():
                stats[queue_name] = {
                    "count": len(queue),
                    "failed_count": len(queue.failed_job_registry)
                }

            return {"status": "ok", "queues": stats}
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
