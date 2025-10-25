# Type System - omnibase_core

**Status**: ✅ Complete

## Overview

Type conventions and patterns used throughout the ONEX framework.

## Type Philosophy

1. **Explicit over implicit**: Always annotate types
2. **Strict typing**: Use mypy in strict mode
3. **Pydantic for models**: Runtime validation with Pydantic
4. **Protocols for interfaces**: Protocol-based polymorphism

## Core Type Patterns

### Pydantic Models

```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    """Type-safe data model."""
    name: str
    value: int = Field(ge=0, description="Non-negative integer")
    optional_data: Optional[dict] = None
```

### Type Annotations

```python
from typing import Optional, List, Dict, Any, Protocol

# Function signatures
def process_data(
    input_data: dict,
    config: Optional[ModelConfig] = None
) -> Dict[str, Any]:
    pass

# Async functions
async def fetch_data(
    url: str,
    timeout: float = 30.0
) -> List[dict]:
    pass
```

### Protocol Definitions

```python
from typing import Protocol

class ProtocolCache(Protocol):
    """Cache interface protocol."""

    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...
    def delete(self, key: str) -> bool: ...
```

## Common Types

### Result Types

```python
from typing import Union, TypedDict

class Success(TypedDict):
    status: str
    data: Any

class Failure(TypedDict):
    status: str
    error: str

Result = Union[Success, Failure]
```

### Generic Types

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value
```

## Type Checking

### mypy Configuration

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Running Type Checks

```bash
# Check all code
poetry run mypy src/

# Check with verbose output
poetry run mypy src/ --verbose

# Check specific file
poetry run mypy src/my_module.py
```

## Best Practices

### 1. Always Annotate Return Types

```python
# ❌ Wrong: No return type
def calculate(x, y):
    return x + y

# ✅ Right: Explicit return type
def calculate(x: float, y: float) -> float:
    return x + y
```

### 2. Use Optional for Nullable Values

```python
# ❌ Wrong: Implicit None
def get_user(id: str) -> dict:
    return None  # Type error!

# ✅ Right: Explicit Optional
def get_user(id: str) -> Optional[dict]:
    return None  # OK
```

### 3. Use TypedDict for Structured Dicts

```python
from typing import TypedDict

# ❌ Wrong: Unstructured dict
def process(data: dict) -> dict:
    pass

# ✅ Right: Structured TypedDict
class InputData(TypedDict):
    name: str
    value: int

class OutputData(TypedDict):
    result: str

def process(data: InputData) -> OutputData:
    pass
```

## Advanced Patterns

### Literal Types

```python
from typing import Literal

ExecutionMode = Literal["sequential", "parallel", "batch"]

def execute(mode: ExecutionMode) -> None:
    pass
```

### Union Types

```python
from typing import Union

def process(data: Union[str, int, float]) -> str:
    return str(data)
```

### Type Guards

```python
from typing import TypeGuard

def is_string_list(val: list) -> TypeGuard[List[str]]:
    return all(isinstance(x, str) for x in val)
```

## Next Steps

- [Contract System](CONTRACT_SYSTEM.md) - Contract architecture
- [Architecture Overview](overview.md) - System design
- [Node Building Guide](../guides/node-building/README.md)

---

**Related Documentation**:
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [mypy Documentation](https://mypy.readthedocs.io/)
