# ChitChats Backend Tests

Comprehensive test suite for the ChitChats backend application.

## Overview

This test suite provides comprehensive coverage for:
- **Unit Tests**: Individual components (utilities, models, CRUD operations, authentication)
- **Integration Tests**: API endpoints and full request/response cycles

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, isolated)
│   ├── test_auth.py               # Authentication functions
│   ├── test_crud.py               # CRUD operations
│   ├── test_korean_particles.py   # Korean particle utilities
│   ├── test_models.py             # SQLAlchemy models
│   ├── test_schemas.py            # Pydantic schemas
│   └── test_utils.py              # Utility functions
├── integration/                    # Integration tests (API endpoints)
│   ├── test_api_agents.py         # Agent endpoints
│   ├── test_api_auth.py           # Auth endpoints
│   └── test_api_rooms.py          # Room and message endpoints
├── conftest.py                     # Shared fixtures
└── README.md                       # This file
```

## Running Tests

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Authentication tests
pytest -m auth

# CRUD tests
pytest -m crud

# API tests
pytest -m api
```

### Run Specific Test Files

```bash
# Test Korean particles
pytest tests/unit/test_korean_particles.py

# Test API authentication
pytest tests/integration/test_api_auth.py

# Test CRUD operations
pytest tests/unit/test_crud.py
```

### Run with Coverage

```bash
# Run tests with coverage report
pytest --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run with Verbose Output

```bash
pytest -v
```

### Run Failed Tests Only

```bash
# Run only tests that failed in the last run
pytest --lf

# Run all tests, but run failed tests first
pytest --ff
```

## Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower)
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.crud` - Database CRUD tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.utils` - Utility function tests
- `@pytest.mark.slow` - Slow-running tests

## Test Fixtures

Key fixtures provided in `conftest.py`:

### Database Fixtures
- `test_db` - Fresh in-memory SQLite database for each test
- `sample_agent` - Pre-created test agent
- `sample_room` - Pre-created test room
- `sample_room_with_agents` - Room with agents already added
- `sample_message` - Pre-created test message

### Client Fixtures
- `client` - Test client with auth bypassed (for unauthenticated tests)
- `authenticated_client` - Test client with valid admin JWT token
- `guest_client` - Test client with valid guest JWT token

### Configuration Fixtures
- `mock_env_vars` - Mock environment variables (API key hash, JWT secret)
- `temp_agent_config` - Temporary agent configuration directory

## Test Coverage

Current test coverage includes:

### Unit Tests
- ✅ Korean particle selection (`has_final_consonant`, `format_with_particles`)
- ✅ Utility functions (serializers, helpers, timezone)
- ✅ Authentication (password validation, JWT tokens, role-based auth)
- ✅ Database models (Room, Agent, Message, RoomAgentSession)
- ✅ Pydantic schemas (validation, serialization)
- ✅ CRUD operations (create, read, update, delete for all models)

### Integration Tests
- ✅ Authentication endpoints (login, token validation)
- ✅ Role-based access control (admin vs guest)
- ✅ Room endpoints (create, list, get, update, delete)
- ✅ Agent endpoints (list, get, update, delete)
- ✅ Room-agent relationships (add/remove agents)
- ✅ Message endpoints (create, list, poll, delete)
- ✅ Agent memory operations

## Writing New Tests

### Unit Test Example

```python
import pytest

class TestMyFeature:
    @pytest.mark.unit
    def test_something(self):
        """Test description."""
        result = my_function()
        assert result == expected_value
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

class TestMyEndpoint:
    @pytest.mark.integration
    @pytest.mark.api
    async def test_endpoint(self, authenticated_client):
        """Test endpoint description."""
        client, token = authenticated_client

        response = await client.get("/my-endpoint")

        assert response.status_code == 200
        assert response.json()["key"] == "value"
```

### Async Test Example

```python
import pytest

class TestAsyncOperation:
    @pytest.mark.unit
    async def test_async_function(self, test_db):
        """Test async operation."""
        result = await my_async_function(test_db)
        assert result is not None
```

## CI/CD Integration

To run tests in CI/CD pipelines:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=. --cov-report=xml --cov-report=term

# Upload coverage to codecov (if configured)
codecov
```

## Troubleshooting

### Tests fail with import errors
- Make sure you're in the `backend` directory
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Database errors
- Tests use in-memory SQLite, no setup needed
- If issues persist, check `conftest.py` for database fixture configuration

### Authentication errors in tests
- Check `mock_env_vars` fixture in `conftest.py`
- Ensure `API_KEY_HASH` and `JWT_SECRET` are properly mocked

### Async test errors
- Make sure to use `async def` for async tests
- Use `await` for async operations
- Check `pytest-asyncio` is installed

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Fixtures**: Use fixtures for common test data and setup
3. **Markers**: Tag tests with appropriate markers for easy filtering
4. **Documentation**: Add docstrings to describe what each test does
5. **Coverage**: Aim for high coverage but focus on critical paths
6. **Fast Tests**: Keep unit tests fast by avoiding external dependencies
7. **Clear Assertions**: Use descriptive assertion messages when helpful

## Contributing

When adding new features:
1. Write tests for new functionality
2. Ensure all existing tests still pass
3. Maintain test coverage above 80%
4. Follow existing test structure and naming conventions
