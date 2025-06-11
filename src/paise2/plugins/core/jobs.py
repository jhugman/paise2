# ABOUTME: Job queue provider implementations for asynchronous job processing.
# ABOUTME: Provides both synchronous and persistent job queue implementations.

from __future__ import annotations

import pickle
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from paise2.config.models import Configuration
    from paise2.plugins.core.interfaces import Job, JobExecutor, JobQueue

# Pickle protocol version for serialization compatibility
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


class DefaultJobExecutor:
    """
    Default implementation of JobExecutor protocol.

    Provides job execution by routing jobs to registered handlers.
    This implementation will be progressively enhanced in later prompts
    to integrate with the full content processing pipeline.
    """

    def __init__(self) -> None:
        """Initialize the job executor with an empty handler registry."""
        self._handlers: dict[
            str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
        ] = {}

    async def execute_job(self, job: Job) -> dict[str, Any]:
        """
        Execute a job by routing it to the appropriate handler.

        Args:
            job: Job to execute

        Returns:
            Job execution result data

        Raises:
            ValueError: If no handler is registered for the job type
        """
        handler = self._handlers.get(job.job_type)
        if handler is None:
            msg = f"No handler registered for job type: {job.job_type}"
            raise ValueError(msg)

        return await handler(job.job_data)

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """
        Register a handler function for a specific job type.

        Args:
            job_type: Type of job this handler can process
            handler: Async function that takes job_data and returns result
        """
        self._handlers[job_type] = handler

    def get_registered_types(self) -> list[str]:
        """
        Get list of job types that have registered handlers.

        Returns:
            List of job types with handlers
        """
        return list(self._handlers.keys())


class MockJobExecutor:
    """
    Mock implementation of JobExecutor for testing.

    Provides a simple implementation that records execution calls
    and can be configured to simulate success or failure scenarios.
    """

    def __init__(self) -> None:
        """Initialize mock executor with tracking and default behavior."""
        self.executed_jobs: list[Job] = []
        self.execution_results: dict[str, dict[str, Any]] = {}
        self.execution_errors: dict[str, Exception] = {}
        self._handlers: dict[str, str] = {}  # Just track handler names for testing

    async def execute_job(self, job: Job) -> dict[str, Any]:
        """
        Mock execute job - records the call and returns configured result.

        Args:
            job: Job to execute

        Returns:
            Mock execution result

        Raises:
            Exception: If configured to fail for this job type
        """
        self.executed_jobs.append(job)

        # Check if we should simulate an error
        if job.job_type in self.execution_errors:
            raise self.execution_errors[job.job_type]

        # Return configured result or default
        return self.execution_results.get(
            job.job_type, {"status": "success", "mock": True}
        )

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """
        Mock register handler - just records that a handler was registered.

        Args:
            job_type: Type of job
            handler: Handler function (ignored in mock)
        """
        _ = handler  # Explicitly ignore handler in mock
        self._handlers[job_type] = f"mock_handler_{job_type}"

    def get_registered_types(self) -> list[str]:
        """
        Get list of job types that have mock handlers.

        Returns:
            List of job types with mock handlers
        """
        return list(self._handlers.keys())

    def configure_result(self, job_type: str, result: dict[str, Any]) -> None:
        """Configure mock result for a job type."""
        self.execution_results[job_type] = result

    def configure_error(self, job_type: str, error: Exception) -> None:
        """Configure mock error for a job type."""
        self.execution_errors[job_type] = error

    def reset(self) -> None:
        """Reset all mock state."""
        self.executed_jobs.clear()
        self.execution_results.clear()
        self.execution_errors.clear()
        self._handlers.clear()


# Strongly typed job types as specified in the spec
JOB_TYPES = {
    "fetch_content": "Fetch content from URL",
    "extract_content": "Extract content using appropriate extractor",
    "store_content": "Store extracted content",
    "cleanup_cache": "Clean up cache entries",
}


class NoJobQueueProvider:
    """
    No-op job queue provider for development.

    Executes jobs immediately without queuing for easier debugging
    and development workflows.
    """

    def create_job_queue(
        self, configuration: Configuration, job_executor: JobExecutor | None = None
    ) -> JobQueue:
        """Create a synchronous job queue that executes immediately."""
        _ = configuration  # Configuration not needed for synchronous queue
        if job_executor is None:
            msg = "SynchronousJobQueue requires a JobExecutor for immediate execution"
            raise ValueError(msg)
        return SynchronousJobQueue(job_executor)


class SynchronousJobQueue:
    """
    Synchronous job queue implementation.

    Executes jobs immediately instead of queuing them.
    Useful for development and testing where immediate execution
    is preferred over asynchronous processing.
    """

    def __init__(self, job_executor: JobExecutor) -> None:
        """Initialize synchronous job queue with job executor."""
        self.job_executor = job_executor

    async def enqueue(
        self, job_type: str, job_data: dict[str, Any], priority: int = 0
    ) -> str:
        """
        Execute job immediately instead of queuing.

        Args:
            job_type: Type of job to execute
            job_data: Job data
            priority: Job priority (ignored in synchronous mode)

        Returns:
            Job ID for the immediately executed job
        """
        from paise2.plugins.core.interfaces import Job

        job_id = f"sync-{uuid.uuid4()}"

        # Create temporary job object for execution
        job = Job(
            job_id=job_id,
            job_type=job_type,
            job_data=job_data,
            priority=priority,
            created_at=datetime.now(),
            worker_id="sync",
        )

        # Execute immediately
        try:
            await self.job_executor.execute_job(job)
        except Exception as e:
            # In sync mode, we can't retry, so we just continue
            # Proper logging will be added when logger integration is available
            _ = e  # Suppress exception but acknowledge it exists

        return job_id

    async def dequeue(self, worker_id: str) -> Job | None:
        """
        Return None since jobs are executed immediately.

        Args:
            worker_id: Worker identifier (ignored)

        Returns:
            None - no jobs to dequeue in synchronous mode
        """
        _ = worker_id  # Explicitly mark as used
        return None

    async def complete(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        """
        No-op since jobs aren't persisted in synchronous mode.

        Args:
            job_id: Job identifier
            result: Job result (ignored)
        """

    async def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """
        No-op since jobs aren't persisted in synchronous mode.

        Args:
            job_id: Job identifier
            error: Error message
            retry: Whether to retry (ignored)
        """

    async def get_incomplete_jobs(self) -> list[Job]:
        """
        Return empty list since no jobs are persisted in synchronous mode.

        Returns:
            Empty list - no incomplete jobs in synchronous mode
        """
        return []


class SQLiteJobQueueProvider:
    """
    SQLite-based job queue provider for production.

    Provides persistent job queue with full job lifecycle management,
    retry logic, and resumability across system restarts.
    """

    def create_job_queue(
        self, configuration: Configuration, job_executor: JobExecutor | None = None
    ) -> JobQueue:
        """Create a SQLite-based job queue."""
        _ = job_executor  # SQLite queues use external workers, executor ignored
        db_path = configuration.get(
            "job_queue.sqlite_path", "~/.local/share/paise2/jobs.db"
        )
        # Expand user path
        db_path = Path(db_path).expanduser()
        return SQLiteJobQueue(db_path)


class SQLiteJobQueue:
    """
    SQLite-based job queue implementation.

    Provides persistent job storage with full lifecycle management,
    priority handling, retry logic, and resumability.
    """

    def __init__(self, db_path: Path) -> None:
        """
        Initialize SQLite job queue.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    job_data BLOB NOT NULL,
                    pickle_version INTEGER NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    worker_id TEXT,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    result BLOB
                )
            """)

            # Create indices for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status_priority
                ON jobs (status, priority DESC, created_at ASC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_type
                ON jobs (job_type)
            """)

            conn.commit()

    async def enqueue(
        self, job_type: str, job_data: dict[str, Any], priority: int = 0
    ) -> str:
        """
        Add a job to the queue.

        Args:
            job_type: Type of job
            job_data: Job data as dictionary (may contain bytes values)
            priority: Job priority (higher = more important)

        Returns:
            Unique job identifier
        """
        job_id = str(uuid.uuid4())
        # SECURITY: Using pickle to serialize job data. Only trusted job data should be
        # processed by this queue. Do not use in environments where untrusted data
        # could be injected into the job queue.
        job_data_blob = pickle.dumps(job_data, protocol=PICKLE_PROTOCOL)
        created_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, job_type, job_data, pickle_version, priority, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    job_id,
                    job_type,
                    job_data_blob,
                    PICKLE_PROTOCOL,
                    priority,
                    created_at,
                ),
            )
            conn.commit()

        return job_id

    async def dequeue(self, worker_id: str) -> Job | None:
        """
        Get the next job from the queue for processing.

        Jobs are returned in priority order (highest first), then by creation time.

        Args:
            worker_id: Identifier of the worker requesting the job

        Returns:
            Next job to process, or None if queue is empty
        """
        from paise2.plugins.core.interfaces import Job

        with sqlite3.connect(self.db_path) as conn:
            # Get the highest priority pending job
            cursor = conn.execute("""
                SELECT job_id, job_type, job_data, pickle_version, priority, created_at
                FROM jobs
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if not row:
                return None

            (
                job_id,
                job_type,
                job_data_blob,
                _pickle_version,  # Version info for future compatibility
                priority,
                created_at_str,
            ) = row

            # Mark job as processing and assign to worker
            conn.execute(
                """
                UPDATE jobs
                SET status = 'processing', worker_id = ?
                WHERE job_id = ?
            """,
                (worker_id, job_id),
            )
            conn.commit()

            # SECURITY: Deserializing pickled job data. This assumes job data was
            # created by trusted sources within this application.
            job_data = pickle.loads(job_data_blob)  # noqa: S301
            created_at = datetime.fromisoformat(created_at_str)

            return Job(
                job_id=job_id,
                job_type=job_type,
                job_data=job_data,
                priority=priority,
                created_at=created_at,
                worker_id=worker_id,
            )

    async def complete(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        """
        Mark a job as completed.

        Args:
            job_id: Job identifier
            result: Optional job result data (may contain bytes values)
        """
        if result is None:
            result_blob = None
        else:
            # SECURITY: Using pickle to serialize result data. Only trusted result data
            # should be stored in the job queue.
            result_blob = pickle.dumps(result, protocol=PICKLE_PROTOCOL)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'completed', result = ?
                WHERE job_id = ?
            """,
                (result_blob, job_id),
            )
            conn.commit()

    async def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """
        Mark a job as failed.

        Args:
            job_id: Job identifier
            error: Error message
            retry: Whether to retry the job (resets to pending) or mark as failed
        """
        new_status = "pending" if retry else "failed"

        with sqlite3.connect(self.db_path) as conn:
            # Increment retry count and update status
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, retry_count = retry_count + 1,
                    worker_id = NULL
                WHERE job_id = ?
            """,
                (new_status, error, job_id),
            )
            conn.commit()

    async def get_incomplete_jobs(self) -> list[Job]:
        """
        Get all jobs that are not completed.

        Returns:
            List of incomplete jobs (pending or processing)
        """
        from paise2.plugins.core.interfaces import Job

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    job_id, job_type, job_data, pickle_version,
                    priority, created_at, worker_id
                FROM jobs
                WHERE status IN ('pending', 'processing')
                ORDER BY priority DESC, created_at ASC
            """)

            jobs = []
            for row in cursor.fetchall():
                (
                    job_id,
                    job_type,
                    job_data_blob,
                    _pickle_version,  # Version info for future compatibility
                    priority,
                    created_at_str,
                    worker_id,
                ) = row

                # SECURITY: Deserializing pickled job data. This assumes job data was
                # created by trusted sources within this application.
                job_data = pickle.loads(job_data_blob)  # noqa: S301
                created_at = datetime.fromisoformat(created_at_str)

                jobs.append(
                    Job(
                        job_id=job_id,
                        job_type=job_type,
                        job_data=job_data,
                        priority=priority,
                        created_at=created_at,
                        worker_id=worker_id,
                    )
                )

            return jobs
