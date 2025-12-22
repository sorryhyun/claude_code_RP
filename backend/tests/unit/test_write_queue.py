"""Tests for the write queue module."""

import asyncio

import pytest


class TestWriteQueue:
    """Tests for write queue functionality."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup and teardown for each test."""
        from infrastructure.database.write_queue import start_writer, stop_writer

        await start_writer()
        yield
        await stop_writer()

    async def test_enqueue_write_basic(self):
        """Test basic write enqueueing."""
        from infrastructure.database.write_queue import enqueue_write

        result = []

        async def write_op():
            result.append(1)
            return "done"

        ret = await enqueue_write(write_op())
        assert ret == "done"
        assert result == [1]

    async def test_enqueue_write_serializes_concurrent_calls(self):
        """Test that concurrent writes are serialized."""
        from infrastructure.database.write_queue import enqueue_write

        execution_order = []

        async def write_op(n: int):
            execution_order.append(f"start_{n}")
            await asyncio.sleep(0.01)  # Small delay
            execution_order.append(f"end_{n}")
            return n

        # Launch multiple writes concurrently
        tasks = [asyncio.create_task(enqueue_write(write_op(i))) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # Results should all be present
        assert set(results) == {0, 1, 2}

        # Verify writes were serialized (each start followed by its end before next start)
        # The pattern should be: start_x, end_x, start_y, end_y, start_z, end_z
        for i in range(0, len(execution_order), 2):
            start_idx = execution_order[i]
            end_idx = execution_order[i + 1]
            # Both should have same number
            assert start_idx.split("_")[1] == end_idx.split("_")[1]

    async def test_enqueue_write_propagates_exceptions(self):
        """Test that exceptions from write operations are propagated."""
        from infrastructure.database.write_queue import enqueue_write

        async def failing_write():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await enqueue_write(failing_write())

    async def test_is_writer_running(self):
        """Test writer status check."""
        from infrastructure.database.write_queue import is_writer_running

        assert is_writer_running() is True

    async def test_get_queue_size(self):
        """Test queue size reporting."""
        from infrastructure.database.write_queue import get_queue_size

        # Queue should be empty when no pending writes
        assert get_queue_size() == 0


class TestWriteQueueNotStarted:
    """Tests for write queue when not started."""

    async def test_enqueue_without_queue_executes_directly(self):
        """Test that enqueue falls back to direct execution when queue not started."""
        from infrastructure.database.write_queue import enqueue_write

        result = []

        async def write_op():
            result.append(1)
            return "done"

        # This should execute directly (with warning) since queue not started
        ret = await enqueue_write(write_op())
        assert ret == "done"
        assert result == [1]

    async def test_is_writer_running_when_stopped(self):
        """Test writer status when not running."""
        from infrastructure.database.write_queue import is_writer_running

        assert is_writer_running() is False

    async def test_get_queue_size_when_stopped(self):
        """Test queue size when not running."""
        from infrastructure.database.write_queue import get_queue_size

        assert get_queue_size() == 0
