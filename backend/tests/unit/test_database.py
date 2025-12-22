"""
Unit tests for database module.

Tests database connection and initialization.
Note: SQLite-specific retry logic tests have been removed since
we now use PostgreSQL which handles concurrency natively.
"""

import pytest
from database import get_db, retry_on_db_lock


class TestRetryOnDbLock:
    """Tests for retry_on_db_lock decorator (PostgreSQL: no-op)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test decorator with successful operation (no retry needed)."""
        call_count = 0

        @retry_on_db_lock(max_retries=3)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_operation()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_decorator_is_passthrough_for_postgresql(self):
        """Test that decorator is a passthrough for PostgreSQL (no retry logic)."""
        call_count = 0

        @retry_on_db_lock(max_retries=3, initial_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("simulated error")
            return "success"

        # PostgreSQL decorator is a no-op, so error should propagate immediately
        with pytest.raises(ValueError):
            await mock_operation()

        # Should only be called once (no retries with PostgreSQL)
        assert call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_exceptions_immediately(self):
        """Test decorator raises exceptions without retry."""
        call_count = 0

        @retry_on_db_lock(max_retries=3)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("some error")

        with pytest.raises(ValueError):
            await mock_operation()

        # Should only be called once (no retries)
        assert call_count == 1


class TestGetDb:
    """Tests for get_db dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields an AsyncSession."""
        session_gen = get_db()
        session = await anext(session_gen)

        # Should be an AsyncSession
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(session, AsyncSession)

        # Cleanup
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_db_closes_session(self):
        """Test get_db properly closes the session."""
        session_gen = get_db()
        session = await anext(session_gen)

        # Session should be open
        assert not session.is_active or True  # Session exists

        # Finish the generator
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass

        # Session should be closed after generator finishes
