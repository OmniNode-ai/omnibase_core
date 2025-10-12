# Quick Start Guide for Agents 7 & 8

## Agent 7: Quick Wins (Target: 46-50% coverage)

### Priority Order:
1. `models/core/model_uri` (0%, 8 lines) - **START HERE**
2. `models/contracts/model_performance_monitor` (0%, 9 lines)
3. `models/core/model_environment` (0%, 143 lines)
4. Then expand existing tests for remaining 11 modules

### Example Test Pattern (Small Model):
```python
# tests/unit/models/core/test_model_uri.py
import pytest
from omnibase_core.models.core.model_uri import ModelUri

class TestModelUri:
    """Test suite for ModelUri."""

    def test_initialization_with_valid_uri(self):
        """Test initialization with valid URI."""
        uri = ModelUri(value="http://example.com")
        assert uri.value == "http://example.com"

    def test_validation_with_invalid_uri(self):
        """Test validation rejects invalid URI."""
        with pytest.raises(ValidationError):
            ModelUri(value="invalid")

    def test_serialization(self):
        """Test model serialization."""
        uri = ModelUri(value="http://example.com")
        data = uri.model_dump()
        assert data["value"] == "http://example.com"
```

### Run Tests:
```bash
poetry run pytest tests/unit/models/core/test_model_uri.py -v
poetry run pytest tests/unit/models/core/ --cov=src/omnibase_core/models/core/model_uri --cov-report=term-missing
```

---

## Agent 8: Infrastructure (Target: 60-65% coverage)

### Priority Order:
1. `infrastructure/node_base` (0%, 162 lines) - **FOUNDATION - START HERE**
2. `infrastructure/node_effect` (0%, 394 lines)
3. `infrastructure/node_compute` (0%, 261 lines)
4. `infrastructure/node_reducer` (0%, 488 lines)
5. `infrastructure/node_orchestrator` (0%, 437 lines)

### Example Test Pattern (Infrastructure):
```python
# tests/unit/infrastructure/test_node_base.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from omnibase_core.infrastructure.node_base import NodeBase

class TestNodeBase:
    """Test suite for NodeBase infrastructure."""

    @pytest.fixture
    def mock_contract(self):
        """Create mock contract for testing."""
        contract = Mock()
        contract.name = "test_contract"
        contract.version = "1.0.0"
        return contract

    @pytest.fixture
    def node(self, mock_contract):
        """Create NodeBase instance."""
        return NodeBase(contract=mock_contract)

    def test_initialization(self, node, mock_contract):
        """Test node initialization."""
        assert node.contract == mock_contract
        assert node.contract.name == "test_contract"

    async def test_execute_lifecycle(self, node):
        """Test full execution lifecycle."""
        # Test pre-execution
        # Test execution
        # Test post-execution
        pass

    async def test_error_handling(self, node):
        """Test error handling and recovery."""
        with pytest.raises(ExpectedError):
            await node.execute_with_error()
```

### Run Tests:
```bash
poetry run pytest tests/unit/infrastructure/test_node_base.py -v
poetry run pytest tests/unit/infrastructure/ --cov=src/omnibase_core/infrastructure/node_base --cov-report=term-missing
```

---

## CRITICAL: Poetry Commands Only

### ✅ CORRECT:
```bash
poetry run pytest tests/
poetry run pytest tests/unit/models/core/test_model_uri.py -v
poetry run pytest --cov=src/omnibase_core --cov-report=term-missing
```

### ❌ WRONG:
```bash
pytest tests/  # NEVER - no poetry
pip install -e .  # NEVER - use poetry
python -m pytest  # NEVER - use poetry run
```

---

## Quick Coverage Check

After creating tests, check coverage:
```bash
# Full coverage report
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing --cov-report=json -q

# Specific module coverage
poetry run pytest tests/unit/models/core/ --cov=src/omnibase_core/models/core --cov-report=term-missing
```

---

## Success Criteria

### Agent 7:
- ✅ 14 test files created/updated
- ✅ Coverage: 46-50%
- ✅ All tests passing
- ✅ ~800 lines covered

### Agent 8:
- ✅ 10 test files created
- ✅ Coverage: 60-65%
- ✅ All tests passing
- ✅ ~2,886 lines covered

### Combined:
- ✅ **Overall coverage: 60%+ (MANDATORY)**
- ✅ Zero test collection errors
- ✅ All tests passing

---

## File Locations

- **Full Analysis**: `COVERAGE_PRIORITY_ANALYSIS_AGENT6.md`
- **JSON Data**: `coverage_agent_assignments.json`
- **This Guide**: `AGENT_7_8_QUICK_START.md`

---

## Test Organization

Tests follow this structure:
```
tests/
├── unit/
│   ├── models/
│   │   ├── core/
│   │   │   ├── test_model_uri.py          # Agent 7
│   │   │   └── test_model_environment.py  # Agent 7
│   │   ├── contracts/
│   │   │   └── test_model_fast_imports.py # Agent 7 (expand)
│   │   └── infrastructure/
│   │       └── test_node_base.py          # Agent 8
│   └── infrastructure/
│       ├── test_node_base.py              # Agent 8
│       ├── test_node_effect.py            # Agent 8
│       ├── test_node_compute.py           # Agent 8
│       ├── test_node_reducer.py           # Agent 8
│       └── test_node_orchestrator.py      # Agent 8
```

---

## Common Patterns

### Test Class Naming:
```python
class TestModelUri:  # For models
class TestNodeBase:  # For infrastructure
class TestValidationType:  # For validation
```

### Test Method Naming:
```python
def test_initialization_with_valid_data(self):
def test_validation_rejects_invalid_input(self):
def test_serialization_produces_correct_output(self):
async def test_async_execution_completes(self):
```

### Fixtures:
```python
@pytest.fixture
def sample_data(self):
    """Provide sample test data."""
    return {"key": "value"}

@pytest.fixture
def mock_dependency(self):
    """Mock external dependency."""
    return Mock()
```

---

## Pro Tips

1. **Look at existing tests** for similar modules
2. **Copy patterns** from high-coverage files
3. **Test edge cases**: None, empty, invalid, boundary values
4. **Use parametrize** for multiple test cases:
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("valid", True),
       ("invalid", False),
   ])
   def test_validation(self, input, expected):
       assert validate(input) == expected
   ```

---

**GO TIME!** 🚀
