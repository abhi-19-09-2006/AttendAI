"""
RQ Worker entry point for background job processing.

Usage:
    python -m app.worker
    python -m app.worker --queues calls,retries,campaigns,followups
    python -m app.worker --workers 4
"""
import sys
import signal
import logging
from rq import Worker
from app.core.rq_config import get_rq_redis_connection
from app.core.logging import get_logger, setup_logging

# Setup application logging
setup_logging()
logger = get_logger("worker")


def handle_shutdown(signum, frame):
    """Gracefully handle worker shutdown."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


def main():
    """Start the RQ worker."""
    # Default queues
    queues = ["calls", "retries", "campaigns", "followups"]
    worker_count = 1

    # Parse command line arguments
    if "--queues" in sys.argv:
        idx = sys.argv.index("--queues")
        queues = sys.argv[idx + 1].split(",")

    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        worker_count = int(sys.argv[idx + 1])

    logger.info(f"Starting RQ worker with queues: {queues}")

    try:
        redis_conn = get_rq_redis_connection()

        # Create worker
        worker = Worker(
            queues,
            connection=redis_conn,
            name=f"rq_worker_{worker_count}",
            default_result_ttl=500,  # Keep results for 500 seconds
            job_monitoring_interval=30,
            disable_default_exception_handler=False
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

        logger.info("Worker started, listening for jobs...")
        worker.work()

    except Exception as e:
        logger.error(f"Worker failed to start: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
