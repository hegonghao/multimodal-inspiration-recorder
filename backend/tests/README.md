# Test Suite Documentation

## Overview

This directory contains comprehensive tests for the multimodal inspiration recorder backend.

### Test Structure

```
tests/
├── contract/              # API contract tests
│   ├── test_records_api.py      # POST /records endpoint tests
│   ├── test_image_ocr.py        # Image OCR contract tests
│   └── test_ai_processing.py    # AI processor service tests
├── integration/           # End-to-end integration tests
│   └── test_voice_workflow.py   # Voice recording workflow tests
├── unit/                  # Unit tests (to be added)
└── README.md             # This file
```

### Test Categories

#### Contract Tests (`@pytest.mark.contract`)
- Validate API request/response schemas
- Test HTTP status codes
- Verify error response structures
- Ensure API contract compliance

#### Integration Tests (`@pytest.mark.integration`)
- Test complete workflows end-to-end
- Validate database operations
- Test service interactions
- Verify data flow through entire system

#### Unit Tests (`@pytest.mark.unit`)
- Test individual functions/methods
- Mock external dependencies
- Fast, isolated tests

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run and show coverage report
pytest --cov=backend.src --cov-report=term-missing
```

### Run Specific Test Categories

```bash
# Contract tests only
pytest -m contract

# Integration tests only
pytest -m integration

# Fast unit tests only
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Records API tests
pytest tests/contract/test_records_api.py

# Voice workflow tests
pytest tests/integration/test_voice_workflow.py

# Specific test class
pytest tests/contract/test_records_api.py::TestRecordsAPIContract

# Specific test function
pytest tests/contract/test_records_api.py::TestRecordsAPIContract::test_create_text_record_success
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=backend.src --cov-report=html

# Open coverage report (after running above)
# Windows
start coverage_html/index.html

# Linux/Mac
open coverage_html/index.html
```

## Test Scenarios Covered

### User Story 1: Voice Recording (T021-T024)

#### Contract Tests (T021, T022)
- ✅ Text input validation
- ✅ Voice file upload
- ✅ Missing file error handling
- ✅ Invalid input type rejection
- ✅ Response schema validation
- ✅ AI processing contract
- ✅ Confidence score calculation
- ✅ Error response structure

#### Integration Tests (T023)
- ✅ Complete voice workflow (upload → transcribe → AI → DB → sync)
- ✅ Low confidence handling
- ✅ Transaction rollback on error
- ✅ AI processing integration
- ✅ Metadata propagation
- ✅ Sync queue creation
- ✅ Performance validation (<10s)
- ✅ Concurrent uploads

### User Story 2: Image OCR (T037-T039)

#### Contract Tests (T037)
- ✅ Image upload validation
- ✅ Multiple format support (PNG, JPG)
- ✅ OCR confidence validation (T046)
- ✅ Low confidence error structure
- ✅ Fallback suggestions (T047)
- ✅ Content extraction
- ✅ Language detection
- ✅ Large image handling
- ✅ OCR metadata completeness
- ✅ AI integration (T048)

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| API Endpoints | 90% | TBD |
| Services | 85% | TBD |
| Models | 80% | TBD |
| Overall | 75% | TBD |

## Mocking Strategy

### External Services

Tests use mocks for external services to ensure:
- Fast execution
- Reliable results
- No dependency on external APIs

```python
# Example: Mocking AI processor
with patch('backend.src.services.ai_processor.AsyncOpenAI') as mock_client:
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    # Test code here
```

### Database

Integration tests use a real database (test instance) to validate:
- SQL queries
- Transactions
- Data integrity

## Continuous Integration

### GitHub Actions (Recommended)

```yaml
- name: Run tests
  run: |
    pytest --cov=backend.src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'backend'`
**Solution**: Ensure `PYTHONPATH` is set correctly or install in editable mode:
```bash
pip install -e .
```

**Issue**: Tests timeout
**Solution**: Increase pytest timeout or skip slow tests:
```bash
pytest -m "not slow"
```

**Issue**: Database connection errors
**Solution**: Ensure test database is configured in `.env.test`

## Writing New Tests

### Test Template

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.contract
class TestNewFeature:
    """Contract tests for new feature"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    async def test_feature_success(self, client):
        """Test successful feature operation"""
        response = await client.post("/api/endpoint", json={...})

        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Best Practices

1. **Naming**: Use descriptive test names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Isolation**: Each test should be independent
4. **Mocking**: Mock external dependencies
5. **Coverage**: Aim for high coverage but focus on meaningful tests
6. **Documentation**: Add docstrings explaining test purpose

## Next Steps

- [ ] Add unit tests for individual services
- [ ] Add performance benchmarks
- [ ] Add stress tests for concurrent operations
- [ ] Implement Flutter widget tests (T024, T039)
- [ ] Setup CI/CD pipeline
- [ ] Add mutation testing

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [httpx testing](https://www.python-httpx.org/advanced/#testing)
