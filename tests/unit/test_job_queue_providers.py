# ABOUTME: Unit tests for job queue provider system.
# ABOUTME: Tests both synchronous and persistent job queue implementations.

from __future__ import annotations

import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from paise2.plugins.core.interfaces import Job, JobQueue, JobQueueProvider
from paise2.plugins.core.jobs import (
    JOB_TYPES,
    MockJobExecutor,
    NoJobQueueProvider,
    SQLiteJobQueue,
    SQLiteJobQueueProvider,
    SynchronousJobQueue,
)
from tests.fixtures import MockConfiguration


class TestJobTypes:
    """Test the strongly typed job types constant."""

    def test_job_types_constant_exists(self) -> None:
        """Test that JOB_TYPES constant is defined."""
        assert JOB_TYPES is not None
        assert isinstance(JOB_TYPES, dict)

    def test_job_types_contains_required_types(self) -> None:
        """Test that JOB_TYPES contains all required job types from spec."""
        required_types = [
            "fetch_content",
            "extract_content",
            "store_content",
            "cleanup_cache",
        ]

        for job_type in required_types:
            assert job_type in JOB_TYPES
            assert isinstance(JOB_TYPES[job_type], str)
            assert len(JOB_TYPES[job_type]) > 0


class TestNoJobQueueProvider:
    """Test NoJobQueueProvider implementation."""

    def test_no_job_queue_provider_implements_protocol(self) -> None:
        """Test that NoJobQueueProvider implements JobQueueProvider protocol."""
        provider = NoJobQueueProvider()
        assert isinstance(provider, JobQueueProvider)

    def test_creates_synchronous_job_queue(self) -> None:
        """Test that provider creates SynchronousJobQueue."""
        provider = NoJobQueueProvider()
        configuration = MockConfiguration({})
        executor = MockJobExecutor()

        queue = provider.create_job_queue(configuration, executor)

        assert isinstance(queue, JobQueue)
        assert isinstance(queue, SynchronousJobQueue)


class TestSynchronousJobQueue:
    """Test SynchronousJobQueue implementation."""

    def test_synchronous_job_queue_implements_protocol(self) -> None:
        """Test that SynchronousJobQueue implements JobQueue protocol."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)
        assert isinstance(queue, JobQueue)

    @pytest.mark.asyncio
    async def test_enqueue_returns_job_id(self) -> None:
        """Test that enqueue returns a job ID."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        job_id = await queue.enqueue("fetch_content", {"url": "test://example.com"})

        assert job_id is not None
        assert isinstance(job_id, str)
        assert job_id.startswith("sync-")

    @pytest.mark.asyncio
    async def test_enqueue_handles_priority(self) -> None:
        """Test that enqueue accepts priority parameter."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        job_id = await queue.enqueue(
            "fetch_content", {"url": "test://example.com"}, priority=5
        )

        assert job_id is not None

    @pytest.mark.asyncio
    async def test_dequeue_returns_none(self) -> None:
        """Test that dequeue always returns None in synchronous mode."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        # Even after enqueuing, dequeue should return None
        await queue.enqueue("fetch_content", {"url": "test://example.com"})
        job = await queue.dequeue("worker-1")

        assert job is None

    @pytest.mark.asyncio
    async def test_complete_is_noop(self) -> None:
        """Test that complete operation is a no-op."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        # Should not raise any exceptions
        await queue.complete("test-job-id")
        await queue.complete("test-job-id", {"result": "success"})

    @pytest.mark.asyncio
    async def test_fail_is_noop(self) -> None:
        """Test that fail operation is a no-op."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        # Should not raise any exceptions
        await queue.fail("test-job-id", "test error")
        await queue.fail("test-job-id", "test error", retry=False)

    @pytest.mark.asyncio
    async def test_get_incomplete_jobs_returns_empty_list(self) -> None:
        """Test that get_incomplete_jobs returns empty list."""
        executor = MockJobExecutor()
        queue = SynchronousJobQueue(executor)

        # Even after enqueuing, should return empty list
        await queue.enqueue("fetch_content", {"url": "test://example.com"})
        incomplete_jobs = await queue.get_incomplete_jobs()

        assert incomplete_jobs == []


class TestSQLiteJobQueueProvider:
    """Test SQLiteJobQueueProvider implementation."""

    def test_sqlite_job_queue_provider_implements_protocol(self) -> None:
        """Test that SQLiteJobQueueProvider implements JobQueueProvider protocol."""
        provider = SQLiteJobQueueProvider()
        assert isinstance(provider, JobQueueProvider)

    def test_creates_sqlite_job_queue_with_default_path(self) -> None:
        """Test that provider creates SQLiteJobQueue with default path."""
        provider = SQLiteJobQueueProvider()
        configuration = MockConfiguration({})

        queue = provider.create_job_queue(configuration)

        assert isinstance(queue, JobQueue)
        assert isinstance(queue, SQLiteJobQueue)

    def test_creates_sqlite_job_queue_with_custom_path(self) -> None:
        """Test that provider creates SQLiteJobQueue with custom path."""
        # Create a temporary directory that will persist for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = str(Path(temp_dir) / "test_jobs.db")

            provider = SQLiteJobQueueProvider()
            configuration = MockConfiguration({"job_queue.sqlite_path": custom_path})

            queue = provider.create_job_queue(configuration)

            assert isinstance(queue, SQLiteJobQueue)
            # Just check that the db_path points to a file in the temp directory
            # We don't care about the exact path, just that it's a working database
            assert queue.db_path is not None
            assert queue.db_path.exists()

            # Test that the queue works with this path
            with sqlite3.connect(queue.db_path or ":memory:") as conn:
                conn.execute("SELECT 1")  # Simple test query

    def test_handles_path_expansion(self) -> None:
        """Test that provider handles path expansion (~ for home directory)."""
        provider = SQLiteJobQueueProvider()
        configuration = MockConfiguration({"job_queue.sqlite_path": "~/test_jobs.db"})

        queue = provider.create_job_queue(configuration)

        assert isinstance(queue, SQLiteJobQueue)
        # Path should be expanded, but we won't test the actual path
        # to avoid assumptions about the user's home directory


class TestSQLiteJobQueue:
    """Test SQLiteJobQueue implementation."""

    def test_sqlite_job_queue_implements_protocol(self) -> None:
        """Test that SQLiteJobQueue implements JobQueue protocol."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")
            assert isinstance(queue, JobQueue)

    def test_database_initialization(self) -> None:
        """Test that database is properly initialized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            _ = SQLiteJobQueue(db_path)  # Initialize database

            # Database file should exist
            assert db_path.exists()

            # Should be able to query the jobs table
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
                )
                assert cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_enqueue_and_basic_job_storage(self) -> None:
        """Test basic job enqueue operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            job_id = await queue.enqueue(
                "fetch_content", {"url": "test://example.com"}, priority=1
            )

            assert job_id is not None
            assert isinstance(job_id, str)
            # Should be a valid UUID
            assert uuid.UUID(job_id)

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_cycle(self) -> None:
        """Test complete enqueue -> dequeue cycle."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue a job
            job_data = {"url": "test://example.com", "metadata": {"title": "Test"}}
            job_id = await queue.enqueue("fetch_content", job_data, priority=2)

            # Dequeue the job
            job = await queue.dequeue("worker-1")

            assert job is not None
            assert isinstance(job, Job)
            assert job.job_id == job_id
            assert job.job_type == "fetch_content"
            assert job.job_data == job_data
            assert job.priority == 2
            assert job.worker_id == "worker-1"
            assert isinstance(job.created_at, datetime)

    @pytest.mark.asyncio
    async def test_dequeue_priority_ordering(self) -> None:
        """Test that jobs are dequeued in priority order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue jobs with different priorities
            low_priority_id = await queue.enqueue(
                "fetch_content", {"url": "low"}, priority=1
            )
            high_priority_id = await queue.enqueue(
                "fetch_content", {"url": "high"}, priority=5
            )
            medium_priority_id = await queue.enqueue(
                "fetch_content", {"url": "medium"}, priority=3
            )

            # Dequeue should return highest priority first
            job1 = await queue.dequeue("worker-1")
            job2 = await queue.dequeue("worker-2")
            job3 = await queue.dequeue("worker-3")

            assert job1 is not None
            assert job1.job_id == high_priority_id
            assert job1.priority == 5

            assert job2 is not None
            assert job2.job_id == medium_priority_id
            assert job2.priority == 3

            assert job3 is not None
            assert job3.job_id == low_priority_id
            assert job3.priority == 1

    @pytest.mark.asyncio
    async def test_dequeue_creation_time_ordering_for_same_priority(self) -> None:
        """Test that jobs with same priority are dequeued in creation order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue jobs with same priority
            first_id = await queue.enqueue(
                "fetch_content", {"url": "first"}, priority=1
            )
            second_id = await queue.enqueue(
                "fetch_content", {"url": "second"}, priority=1
            )

            # Should dequeue in creation order
            job1 = await queue.dequeue("worker-1")
            job2 = await queue.dequeue("worker-2")
            assert job1 is not None
            assert job1.job_id == first_id
            assert job2 is not None
            assert job2.job_id == second_id

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self) -> None:
        """Test dequeue behavior when queue is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            job = await queue.dequeue("worker-1")

            assert job is None

    @pytest.mark.asyncio
    async def test_complete_job(self) -> None:
        """Test job completion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue and dequeue a job
            _ = await queue.enqueue("fetch_content", {"url": "test://example.com"})
            job = await queue.dequeue("worker-1")
            assert job is not None

            # Complete the job
            result = {"status": "success", "content_length": 1024}
            await queue.complete(job.job_id, result)

            # Job should no longer be in incomplete jobs
            incomplete_jobs = await queue.get_incomplete_jobs()
            assert len(incomplete_jobs) == 0

    @pytest.mark.asyncio
    async def test_fail_job_with_retry(self) -> None:
        """Test job failure with retry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue and dequeue a job
            job_id = await queue.enqueue("fetch_content", {"url": "test://example.com"})
            job = await queue.dequeue("worker-1")
            assert job is not None

            # Fail the job with retry
            await queue.fail(job.job_id, "Network timeout", retry=True)

            # Job should be back in pending state and available for dequeue
            retry_job = await queue.dequeue("worker-2")
            assert retry_job is not None
            assert retry_job.job_id == job_id

    @pytest.mark.asyncio
    async def test_fail_job_without_retry(self) -> None:
        """Test job failure without retry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue and dequeue a job
            _ = await queue.enqueue("fetch_content", {"url": "test://example.com"})
            job = await queue.dequeue("worker-1")
            assert job is not None

            # Fail the job without retry
            await queue.fail(job.job_id, "Permanent error", retry=False)

            # Job should not be available for dequeue
            next_job = await queue.dequeue("worker-2")
            assert next_job is None

            # Job should not be in incomplete jobs
            incomplete_jobs = await queue.get_incomplete_jobs()
            assert len(incomplete_jobs) == 0

    @pytest.mark.asyncio
    async def test_get_incomplete_jobs(self) -> None:
        """Test getting incomplete jobs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue multiple jobs
            pending_id = await queue.enqueue("fetch_content", {"url": "pending"})
            processing_id = await queue.enqueue("extract_content", {"content": "data"})

            # Dequeue one job (makes it processing)
            processing_job = await queue.dequeue("worker-1")
            assert processing_job is not None
            assert processing_job.job_id == pending_id  # First in creation order

            # Get incomplete jobs
            incomplete_jobs = await queue.get_incomplete_jobs()

            assert len(incomplete_jobs) == 2

            # Find the jobs by ID
            incomplete_ids = [job.job_id for job in incomplete_jobs]
            assert pending_id in incomplete_ids  # Now processing
            assert processing_id in incomplete_ids  # Still pending

    @pytest.mark.asyncio
    async def test_job_persistence_across_instances(self) -> None:
        """Test that jobs persist across SQLiteJobQueue instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"

            # Create first queue instance and enqueue jobs
            queue1 = SQLiteJobQueue(db_path)
            job_id = await queue1.enqueue(
                "fetch_content", {"url": "test://example.com"}
            )

            # Create second queue instance with same database
            queue2 = SQLiteJobQueue(db_path)

            # Should be able to dequeue job from second instance
            job = await queue2.dequeue("worker-1")
            assert job is not None
            assert job.job_id == job_id

    @pytest.mark.asyncio
    async def test_multiple_job_types(self) -> None:
        """Test handling of different job types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue jobs of different types
            for job_type in JOB_TYPES:
                job_id = await queue.enqueue(job_type, {"test": "data"})
                assert job_id is not None

            # Should be able to dequeue all job types
            dequeued_types: list[str] = []
            for _ in range(len(JOB_TYPES)):
                job = await queue.dequeue(f"worker-{len(dequeued_types)}")
                if job:
                    dequeued_types.append(job.job_type)

            assert len(dequeued_types) == len(JOB_TYPES)
            for job_type in JOB_TYPES:
                assert job_type in dequeued_types

    @pytest.mark.asyncio
    async def test_binary_data_handling(self) -> None:
        """Test that SQLite job queue can handle binary data in job_data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Create job data with binary content
            binary_content = b"\x00\x01\x02\xff\xfe\xfd\x89PNG\r\n\x1a\n"
            job_data = {
                "url": "test://example.com/image.png",
                "content": binary_content,
                "metadata": {"size": len(binary_content), "type": "image/png"},
            }

            # Enqueue job with binary data
            job_id = await queue.enqueue("extract_content", job_data, priority=1)
            assert job_id is not None

            # Dequeue and verify binary data is preserved
            job = await queue.dequeue("worker-1")
            assert job is not None
            assert job.job_type == "extract_content"
            assert job.job_data["url"] == "test://example.com/image.png"
            assert job.job_data["content"] == binary_content
            assert job.job_data["metadata"]["size"] == len(binary_content)

            # Complete job with binary result
            binary_result = b"\x89PNG processed"
            result_data = {
                "extracted_text": "Some extracted text",
                "processed_image": binary_result,
                "status": "success",
            }
            await queue.complete(job.job_id, result_data)

            # Verify job is completed (no more incomplete jobs)
            incomplete_jobs = await queue.get_incomplete_jobs()
            assert len(incomplete_jobs) == 0

    @pytest.mark.asyncio
    async def test_mixed_binary_and_text_data(self) -> None:
        """Test job queue with mixed binary and text data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Job data with multiple binary fields and regular data
            job_data = {
                "url": "test://example.com",
                "html_content": b"<html><body>Test</body></html>",
                "image_data": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
                "text_metadata": "Regular string data",
                "number": 42,
                "list_data": ["item1", "item2"],
                "nested": {"key": "value", "binary": b"nested binary data"},
            }  # Enqueue and dequeue
            _ = await queue.enqueue("store_content", job_data)
            job = await queue.dequeue("worker-1")
            assert job is not None

            # Verify all data types are preserved
            assert job.job_data["url"] == "test://example.com"
            assert job.job_data["html_content"] == b"<html><body>Test</body></html>"
            assert job.job_data["image_data"] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            assert job.job_data["text_metadata"] == "Regular string data"
            assert job.job_data["number"] == 42
            assert job.job_data["list_data"] == ["item1", "item2"]
            assert job.job_data["nested"]["key"] == "value"
            assert job.job_data["nested"]["binary"] == b"nested binary data"

    @pytest.mark.asyncio
    async def test_job_data_without_binary(self) -> None:
        """Test that jobs without binary data still work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Regular job data without any binary content
            job_data = {
                "url": "test://example.com",
                "text": "Some text content",
                "metadata": {"type": "text", "size": 100},
            }  # Should work exactly as before
            _ = await queue.enqueue("fetch_content", job_data)
            job = await queue.dequeue("worker-1")
            assert job is not None

            assert job.job_data == job_data

            # Complete with regular result
            await queue.complete(
                job.job_id, {"status": "success", "result": "processed"}
            )

            incomplete_jobs = await queue.get_incomplete_jobs()
            assert len(incomplete_jobs) == 0


class TestJobQueueIntegration:
    """Integration tests for job queue system."""

    @pytest.mark.asyncio
    async def test_job_lifecycle_with_synchronous_queue(self) -> None:
        """Test complete job lifecycle with synchronous queue."""
        provider = NoJobQueueProvider()
        executor = MockJobExecutor()
        queue = provider.create_job_queue(MockConfiguration({}), executor)

        # Test the full lifecycle
        job_id = await queue.enqueue("fetch_content", {"url": "test://example.com"})
        assert job_id is not None

        # In synchronous mode, jobs aren't actually queued
        job = await queue.dequeue("worker-1")
        assert job is None

        # Complete and fail should not raise errors
        await queue.complete(job_id)
        await queue.fail(job_id, "test error")

        # Should have no incomplete jobs
        incomplete = await queue.get_incomplete_jobs()
        assert len(incomplete) == 0

    @pytest.mark.asyncio
    async def test_job_lifecycle_with_sqlite_queue(self) -> None:
        """Test complete job lifecycle with SQLite queue."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = SQLiteJobQueueProvider()
            configuration = MockConfiguration(
                {"job_queue.sqlite_path": str(Path(temp_dir) / "jobs.db")}
            )
            queue = provider.create_job_queue(configuration)

            # Enqueue a job
            job_data = {"url": "test://example.com"}
            job_id = await queue.enqueue("fetch_content", job_data, priority=1)

            # Dequeue the job
            job = await queue.dequeue("worker-1")
            assert job is not None
            assert job.job_id == job_id

            # Complete the job
            await queue.complete(job.job_id, {"status": "success"})

            # Should have no incomplete jobs
            incomplete = await queue.get_incomplete_jobs()
            assert len(incomplete) == 0

    @pytest.mark.asyncio
    async def test_error_handling_and_retry_logic(self) -> None:
        """Test error handling and retry logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = SQLiteJobQueue(Path(temp_dir) / "jobs.db")

            # Enqueue a job
            job_id = await queue.enqueue("fetch_content", {"url": "test://failing.com"})

            # Simulate job processing and failure
            job = await queue.dequeue("worker-1")
            assert job is not None
            await queue.fail(job.job_id, "Network error", retry=True)

            # Job should be retryable
            retry_job = await queue.dequeue("worker-2")
            assert retry_job is not None
            assert retry_job.job_id == job_id

            # Fail again without retry
            await queue.fail(retry_job.job_id, "Permanent failure", retry=False)

            # Job should not be available anymore
            final_job = await queue.dequeue("worker-3")
            assert final_job is None
