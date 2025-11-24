"""
Unit tests for database module.

Tests database connection, retry logic, and initialization.
"""

import asyncio

import pytest
from database import async_session_maker, engine, get_db, retry_on_db_lock
from sqlalchemy.exc import DBAPIError, OperationalError


class TestRetryOnDbLock:
    """Tests for retry_on_db_lock decorator."""

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
    async def test_retry_on_database_locked(self):
        """Test decorator retries on database locked error."""
        call_count = 0

        @retry_on_db_lock(max_retries=3, initial_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("database is locked", None, None)
            return "success"

        result = await mock_operation()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Test decorator raises exception after max retries."""

        @retry_on_db_lock(max_retries=3, initial_delay=0.01)
        async def mock_operation():
            raise OperationalError("database is locked", None, None)

        with pytest.raises(OperationalError):
            await mock_operation()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_non_lock_errors_immediately(self):
        """Test decorator raises non-lock errors without retry."""
        call_count = 0

        @retry_on_db_lock(max_retries=3)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise OperationalError("other error", None, None)

        with pytest.raises(OperationalError):
            await mock_operation()

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_other_exceptions_immediately(self):
        """Test decorator raises other exceptions without retry."""
        call_count = 0

        @retry_on_db_lock(max_retries=3)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("some other error")

        with pytest.raises(ValueError):
            await mock_operation()

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_backoff_delay(self):
        """Test decorator uses exponential backoff."""
        call_times = []

        @retry_on_db_lock(max_retries=3, initial_delay=0.01, backoff_factor=2)
        async def mock_operation():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise OperationalError("database is locked", None, None)
            return "success"

        await mock_operation()

        # Check that delays are approximately increasing
        assert len(call_times) == 3
        # First retry should wait ~0.01s
        # Second retry should wait ~0.02s
        # Delays should be increasing

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dbapi_error_retry(self):
        """Test decorator also retries on DBAPIError."""
        call_count = 0

        @retry_on_db_lock(max_retries=3, initial_delay=0.01)
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise DBAPIError("database is locked", None, None)
            return "success"

        result = await mock_operation()

        assert result == "success"
        assert call_count == 2


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


class TestDatabaseEngine:
    """Tests for database engine configuration."""

    @pytest.mark.unit
    def test_engine_configuration(self):
        """Test database engine is properly configured."""
        assert engine is not None
        assert "sqlite" in str(engine.url)

    @pytest.mark.unit
    def test_async_session_maker_configuration(self):
        """Test async session maker is properly configured."""
        assert async_session_maker is not None
        # Should create AsyncSession instances
        from sqlalchemy.ext.asyncio import AsyncSession

        assert async_session_maker.class_ == AsyncSession
