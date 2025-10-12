# Testing Quick Start Guide

## Current Status

✅ **Coverage: 62.72%** (Already above 60% target!)
🎯 **Next Goal: 70% coverage**

## Get Started in 5 Minutes

### 1. Check Current Coverage

```bash
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing --cov-report=html
open htmlcov/index.html
```

### 2. Run Existing Tests

```bash
# Run all tests
poetry run pytest tests/

# Run specific module
poetry run pytest tests/unit/decorators/ -v

# Run with verbose output
poetry run pytest tests/unit/decorators/test_error_handling.py -xvs
```

---

## Priority 1: Error Handling Decorator (CRITICAL)

**File:** `src/omnibase_core/decorators/error_handling.py`
**Current Coverage:** 18.5%
**Impact:** +1.28% coverage

### Create Test File

```bash
# Create test file
mkdir -p tests/unit/decorators
touch tests/unit/decorators/test_error_handling_extended.py
```

### Basic Test Template

```python
"""Extended tests for error handling decorator."""
import pytest
from omnibase_core.decorators.error_handling import error_handler
from omnibase_core.errors.model_onex_error import ModelOnexError

class TestErrorHandlingBasics:
    """Basic error handling functionality"""

    def test_propagates_exceptions(self):
        """Test that exceptions are properly propagated"""
        @error_handler
        def raises_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            raises_error()

    def test_preserves_context(self):
        """Test that error context is preserved"""
        @error_handler
        def raises_with_context():
            raise ModelOnexError(
                error_code="TEST_001",
                message="Context test",
                context={"key": "value"}
            )

        with pytest.raises(ModelOnexError) as exc_info:
            raises_with_context()

        assert exc_info.value.context["key"] == "value"

class TestErrorHandlingEdgeCases:
    """Edge cases and error scenarios"""

    def test_nested_exceptions(self):
        """Test handling of nested exception chains"""
        # TODO: Implement
        pass

    def test_async_functions(self):
        """Test decorator with async functions"""
        # TODO: Implement
        pass
```

### Run Tests

```bash
poetry run pytest tests/unit/decorators/test_error_handling_extended.py -v
```

---

## Priority 2: Pattern Exclusions (HIGH)

**File:** `src/omnibase_core/decorators/pattern_exclusions.py`
**Current Coverage:** 49.2%
**Impact:** +0.67% coverage

### Create Test File

```bash
touch tests/unit/decorators/test_pattern_exclusions.py
```

### Basic Test Template

```python
"""Tests for pattern exclusions decorator."""
import pytest
from omnibase_core.decorators.pattern_exclusions import pattern_exclusions

class TestPatternExclusionsBasics:
    """Basic pattern exclusion functionality"""

    def test_exact_match(self):
        """Test exact pattern matching"""
        # TODO: Implement
        pass

    def test_wildcard_match(self):
        """Test wildcard pattern matching"""
        # TODO: Implement
        pass

class TestPatternExclusionsEdgeCases:
    """Edge cases for pattern exclusions"""

    def test_empty_patterns(self):
        """Test behavior with empty pattern list"""
        # TODO: Implement
        pass

    def test_invalid_regex(self):
        """Test handling of invalid regex patterns"""
        # TODO: Implement
        pass
```

---

## Priority 3: Configuration Base (MEDIUM)

**File:** `src/omnibase_core/models/core/model_configuration_base.py`
**Current Coverage:** 62.0%
**Impact:** +0.91% coverage

### Create Test File

```bash
mkdir -p tests/unit/models/core
touch tests/unit/models/core/test_model_configuration_base.py
```

### Basic Test Template

```python
"""Tests for ModelConfigurationBase."""
import pytest
from datetime import datetime, UTC
from omnibase_core.models.core.model_configuration_base import ModelConfigurationBase

class TestConfigurationBaseLifecycle:
    """Test configuration lifecycle methods"""

    def test_creation(self):
        """Test configuration creation"""
        config = ModelConfigurationBase(name="test_config")
        assert config.name == "test_config"
        assert config.enabled is True

    def test_update_timestamp(self):
        """Test timestamp update"""
        config = ModelConfigurationBase(name="test")
        original_time = config.updated_at
        config.update_timestamp()
        assert config.updated_at > original_time

class TestConfigurationBaseValidation:
    """Test validation logic"""

    def test_validate_instance(self):
        """Test instance validation"""
        # TODO: Implement
        pass

    def test_serialize_exception(self):
        """Test serialization of Exception in config_data"""
        # TODO: Implement
        pass
```

---

## Quick Wins (1 Hour Total)

### 1. Decorator Allow Any Type (30 min)

```bash
touch tests/unit/decorators/test_decorator_allow_any_type.py
```

```python
"""Tests for decorator_allow_any_type."""
import pytest
from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

class TestAllowAnyType:
    def test_bypasses_validation(self):
        """Test that type validation is bypassed"""
        # TODO: Implement
        pass
```

### 2. Event Types Constants (30 min)

```bash
mkdir -p tests/unit/constants
touch tests/unit/constants/test_event_types.py
```

```python
"""Tests for event_types constants."""
import pytest
from omnibase_core.constants.event_types import EVENT_TYPES

class TestEventTypes:
    def test_all_defined(self):
        """Test that all event types are defined"""
        # TODO: Implement
        pass

    def test_unique_values(self):
        """Test that event type values are unique"""
        # TODO: Implement
        pass
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
poetry run pytest tests/

# Run with coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Run specific test file
poetry run pytest tests/unit/decorators/test_error_handling.py -v

# Run specific test class
poetry run pytest tests/unit/decorators/test_error_handling.py::TestErrorHandlingBasics -xvs

# Run specific test method
poetry run pytest tests/unit/decorators/test_error_handling.py::TestErrorHandlingBasics::test_propagates_exceptions -xvs
```

### Coverage Reports

```bash
# Generate HTML coverage report
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=html

# View HTML report
open htmlcov/index.html

# Generate JSON coverage report
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=json

# Terminal coverage with missing lines
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing
```

---

## Test Writing Best Practices

### 1. Test Structure (AAA Pattern)

```python
def test_something():
    """Test description"""
    # Arrange - Set up test data
    config = ModelConfigurationBase(name="test")

    # Act - Execute the code under test
    result = config.validate_instance()

    # Assert - Verify the result
    assert result is True
```

### 2. Use Fixtures for Common Setup

```python
import pytest

@pytest.fixture
def sample_config():
    """Create a sample configuration for testing"""
    return ModelConfigurationBase(
        name="test_config",
        description="Test configuration",
        enabled=True
    )

def test_with_fixture(sample_config):
    """Test using the fixture"""
    assert sample_config.name == "test_config"
```

### 3. Test Edge Cases

```python
def test_edge_case_empty_name():
    """Test behavior with empty name"""
    config = ModelConfigurationBase(name="")
    assert config.validate_instance() is False

def test_edge_case_none_config_data():
    """Test behavior with None config_data"""
    config = ModelConfigurationBase(name="test", config_data=None)
    assert config.validate_instance() is True
```

### 4. Use Parametrize for Multiple Test Cases

```python
@pytest.mark.parametrize("name,expected", [
    ("test", True),
    ("", False),
    (None, False),
])
def test_name_validation(name, expected):
    """Test name validation with multiple inputs"""
    config = ModelConfigurationBase(name=name)
    assert config.validate_instance() == expected
```

---

## Monitoring Progress

### Track Coverage Over Time

```bash
# Before starting
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term | grep TOTAL

# After adding tests
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term | grep TOTAL

# Compare results
```

### Coverage Checkpoints

| Checkpoint | Target Coverage | Modules Complete |
|------------|----------------|------------------|
| Start | 62.72% | Baseline |
| After Priority 1 | 64.0% | error_handling.py |
| After Priority 2 | 64.7% | + pattern_exclusions.py |
| After Priority 3 | 65.6% | + model_configuration_base.py |
| After Quick Wins | 66.6% | + allow_any_type.py, event_types.py |
| **Phase 1 Complete** | **66.6%** | **All Critical Modules** |
| After Validation | 69.0% | + validation modules |
| **Phase 2 Complete** | **70%** | **All High Priority** |

---

## Common Issues & Solutions

### Issue: Tests Not Found

```bash
# Make sure __init__.py exists in test directories
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/decorators/__init__.py
```

### Issue: Import Errors

```bash
# Make sure you're using Poetry
poetry run pytest tests/

# NOT: pytest tests/  (this won't use the Poetry virtualenv)
```

### Issue: Coverage Not Updating

```bash
# Remove old coverage data
rm .coverage
rm -rf htmlcov/

# Re-run tests
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=html
```

---

## Next Steps

1. ✅ **Week 1:** Complete Priority 1-3 modules (7-9 hours)
   - Error handling decorator
   - Pattern exclusions
   - Configuration base

2. 🎯 **Week 2:** Validation & infrastructure (8-10 hours)
   - Validation modules
   - Infrastructure models

3. 🚀 **Week 3+:** Primitives & polish
   - Primitives coverage
   - Integration tests for enums

---

## Resources

- **Full Report:** `COVERAGE_ANALYSIS_REPORT.md`
- **Priority JSON:** `coverage_priorities.json`
- **HTML Coverage:** `htmlcov/index.html`

---

**Remember:** Use `poetry run` for ALL Python commands!

✅ Good: `poetry run pytest tests/`
❌ Bad: `pytest tests/`
