> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Type System
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Type System

**Status**: Current
**Last Updated**: 2026-02-14

---

## Table of Contents

1. [Overview](#overview)
2. [PEP 604 Union Syntax](#pep-604-union-syntax)
3. [Built-In Generics](#built-in-generics)
4. [Pydantic Model Patterns](#pydantic-model-patterns)
5. [Protocol-Based Typing](#protocol-based-typing)
6. [Enum Standards](#enum-standards)
7. [Type Narrowing and Type Guards](#type-narrowing-and-type-guards)
8. [TypedDict for Structured Data](#typeddict-for-structured-data)
9. [Generic Types](#generic-types)
10. [Literal Types](#literal-types)
11. [mypy Configuration](#mypy-configuration)
12. [Banned Patterns](#banned-patterns)

---

## Overview

All code in omnibase_core targets **Python 3.12+** and uses modern type syntax throughout. The following principles apply universally:

1. **PEP 604 union syntax**: `X | Y` instead of `Union[X, Y]`, `X | None` instead of `Optional[X]`
2. **Built-in generics**: `list[str]` instead of `List[str]`, `dict[str, int]` instead of `Dict[str, int]`
3. **Explicit annotations**: Every function has parameter and return type annotations
4. **Strict mypy**: All code must pass `mypy --strict` with zero errors
5. **Pydantic for models**: Runtime validation with `ConfigDict` for model configuration
6. **Protocols for interfaces**: Protocol-based polymorphism for DI

---

## PEP 604 Union Syntax

Python 3.10+ introduced the `X | Y` syntax for union types. This is the **only** accepted syntax in omnibase_core.

### Nullable Types

```python
# CORRECT -- PEP 604
def get_user(user_id: str) -> UserModel | None:
    ...

name: str | None = None
config: ModelConfig | None = Field(default=None)
```

```python
# BANNED -- do not use
from typing import Optional
def get_user(user_id: str) -> Optional[UserModel]:  # Forbidden
    ...
```

### Multi-Type Unions

```python
# CORRECT -- PEP 604
def process(data: str | int | float) -> str:
    return str(data)

InputType = str | bytes | Path
```

```python
# BANNED -- do not use
from typing import Union
def process(data: Union[str, int, float]) -> str:  # Forbidden
    ...
```

### Union in Pydantic Models

```python
from pydantic import BaseModel, Field


class ModelEventPayload(BaseModel):
    source: str
    data: dict[str, str] | list[str] | None = None
    error_code: int | None = Field(default=None, description="Error code if failed")
```

---

## Built-In Generics

Python 3.9+ supports built-in collection types as generics. Always use lowercase built-in names.

### Collections

```python
# CORRECT -- built-in generics
names: list[str] = []
config: dict[str, int] = {}
unique_ids: set[str] = set()
items: tuple[str, int, float] = ("a", 1, 0.5)
frozen: frozenset[int] = frozenset({1, 2, 3})
```

```python
# BANNED -- do not use
from typing import List, Dict, Set, Tuple, FrozenSet
names: List[str] = []         # Forbidden
config: Dict[str, int] = {}   # Forbidden
unique_ids: Set[str] = set()  # Forbidden
```

### Nested Generics

```python
# CORRECT
registrations: dict[str, list[ModelServiceRegistration]] = {}
callbacks: list[tuple[str, int]] = []
nested_config: dict[str, dict[str, str | int]] = {}
```

### Callable Types

```python
from collections.abc import Callable, Awaitable

# CORRECT -- use collections.abc
handler: Callable[[str, int], bool]
factory: Callable[[], ModelService]
async_handler: Callable[[str], Awaitable[ModelResult]]
```

```python
# BANNED -- do not use
from typing import Callable  # Forbidden (use collections.abc.Callable)
```

### Iterator and Sequence Types

```python
from collections.abc import Iterator, Sequence, Mapping, Iterable

def process_items(items: Sequence[str]) -> Iterator[str]:
    for item in items:
        yield item.upper()

def read_config(config: Mapping[str, str]) -> str:
    return config.get("key", "default")
```

---

## Pydantic Model Patterns

All Pydantic models in omnibase_core use `ConfigDict` for configuration. The required settings depend on the model's purpose.

### Immutable Value Models

For models that represent read-only data (contracts, events, configuration snapshots):

```python
from pydantic import BaseModel, ConfigDict, Field


class ModelEventEnvelope(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    event_id: str
    event_type: str
    timestamp: float
    payload: dict[str, str | int | float | bool | None]
```

- `frozen=True`: Instances are immutable after creation.
- `extra="forbid"`: Unknown fields raise `ValidationError`.
- `from_attributes=True`: Required on frozen models for pytest-xdist compatibility.

### Mutable Internal Models

For models that track state or accumulate data during processing:

```python
class ModelPerformanceMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    total_operations: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    timestamps: list[float] = Field(default_factory=list)
```

### Contract/External Models

For models that parse external data (YAML contracts, API responses) where extra fields should be tolerated:

```python
class ModelContractCompute(ModelContractBase):
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )

    algorithm: ModelAlgorithmConfig
    parallel_processing: ModelParallelConfig = Field(default_factory=ModelParallelConfig)
```

### Mutable Default Fields

Always use `default_factory` for mutable defaults. Never use bare `[]`, `{}`, or `set()` as defaults:

```python
# CORRECT
tags: list[str] = Field(default_factory=list)
metadata: dict[str, str] = Field(default_factory=dict)
items: set[int] = Field(default_factory=set)

# WRONG -- mutable default shared across instances
tags: list[str] = []           # Forbidden
metadata: dict[str, str] = {}  # Forbidden
```

---

## Protocol-Based Typing

Protocols define interfaces for the DI system. They enable structural subtyping -- any class that implements the required methods satisfies the protocol without explicit inheritance.

### Defining Protocols

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLogger(Protocol):
    """Logging interface for DI resolution."""

    def info(self, message: str) -> None: ...
    def error(self, message: str, exc_info: bool = False) -> None: ...
    def warning(self, message: str) -> None: ...


class ProtocolCache(Protocol):
    """Cache interface for DI resolution."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None: ...
    def delete(self, key: str) -> bool: ...
```

### Using Protocols as Type Hints

```python
def create_service(logger: ProtocolLogger, cache: ProtocolCache) -> MyService:
    """Both parameters are protocol-typed -- any conforming object works."""
    return MyService(logger=logger, cache=cache)
```

### Protocols in DI Container Resolution

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# The container resolves protocols to concrete implementations
logger = container.get_service(ProtocolLogger)      # Returns concrete impl
cache = container.get_service_optional(ProtocolCache)  # Returns impl or None
```

### Protocol with Properties

```python
class ProtocolServiceMetadata(Protocol):
    @property
    def service_name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def is_healthy(self) -> bool: ...
```

### Async Protocols

```python
class ProtocolAsyncEventBus(Protocol):
    async def publish(self, topic: str, payload: dict[str, str]) -> None: ...
    async def subscribe(self, topic: str, handler: Callable[[dict[str, str]], Awaitable[None]]) -> None: ...
```

---

## Enum Standards

### String-Valued Enums for Serialization

All enums that cross process boundaries or appear in contracts use `str` as base class for stable serialization:

```python
from enum import Enum


class EnumNodeType(str, Enum):
    """Node type classification for 4-node architecture."""

    COMPUTE_GENERIC = "compute"
    EFFECT_GENERIC = "effect"
    REDUCER_GENERIC = "reducer"
    ORCHESTRATOR_GENERIC = "orchestrator"


class EnumHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
```

### When to Use Enum vs Literal

| Context | Use |
|---------|-----|
| **External contract surface** (YAML, API) | Enums |
| **Cross-process boundaries** (events, serialized data) | Enums |
| **Internal parsing glue** (local function parameters) | Literals allowed |
| **Fixed string sets in function signatures** | Literals allowed |

```python
from typing import Literal

# Literal -- acceptable for internal use only
ExecutionMode = Literal["sequential", "parallel", "batch"]

def execute(mode: ExecutionMode) -> None:
    ...

# Enum -- required for contract fields and cross-process data
class EnumExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
```

### Enum in Pydantic Models

```python
class ModelWorkflowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: EnumExecutionMode = EnumExecutionMode.SEQUENTIAL
    max_retries: int = 3
```

---

## Type Narrowing and Type Guards

### isinstance Narrowing

```python
def process_input(data: str | int | list[str]) -> str:
    if isinstance(data, str):
        return data.upper()  # mypy knows data is str here
    if isinstance(data, int):
        return str(data)     # mypy knows data is int here
    return ", ".join(data)   # mypy knows data is list[str] here
```

### Custom Type Guards

```python
from typing import TypeGuard


def is_string_list(val: list[str | int]) -> TypeGuard[list[str]]:
    """Narrow list[str | int] to list[str]."""
    return all(isinstance(x, str) for x in val)


def process(items: list[str | int]) -> str:
    if is_string_list(items):
        return ", ".join(items)  # mypy knows items is list[str]
    return str(items)
```

### TypeGuard for Protocol Checking

```python
from typing import TypeGuard


def is_logger(obj: object) -> TypeGuard[ProtocolLogger]:
    return hasattr(obj, "info") and hasattr(obj, "error") and hasattr(obj, "warning")


def maybe_log(obj: object, message: str) -> None:
    if is_logger(obj):
        obj.info(message)  # mypy knows obj is ProtocolLogger
```

### assert_never for Exhaustive Matching

```python
from typing import assert_never


def handle_status(status: EnumHealthStatus) -> str:
    match status:
        case EnumHealthStatus.HEALTHY:
            return "All systems operational"
        case EnumHealthStatus.DEGRADED:
            return "Performance degraded"
        case EnumHealthStatus.UNHEALTHY:
            return "System unhealthy"
        case _ as unreachable:
            assert_never(unreachable)  # Compile-time exhaustiveness check
```

---

## TypedDict for Structured Data

Use `TypedDict` when you need a typed dictionary shape without Pydantic validation overhead. Common for function return types and internal data passing.

```python
from typing import TypedDict


class TypedDictResolutionContext(TypedDict, total=False):
    correlation_id: str
    scope: str
    timeout_ms: int


class TypedDictPerformanceCheckpointResult(TypedDict, total=False):
    phase_name: str
    duration_ms: float
    cache_hit_rate: float
    error: str
```

### TypedDict vs Pydantic Model

| Scenario | Use |
|----------|-----|
| Internal function return types | TypedDict |
| Configuration or contract data | Pydantic model |
| Cross-module interfaces | Pydantic model |
| Performance-sensitive hot paths | TypedDict |
| Data requiring validation | Pydantic model |

---

## Generic Types

### TypeVar

```python
from typing import TypeVar

T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


def first_or_none(items: list[T]) -> T | None:
    return items[0] if items else None
```

### Generic Classes

```python
from typing import Generic, TypeVar

T = TypeVar("T")


class ModelContainer(Generic[T]):
    """Generic value wrapper with metadata."""

    def __init__(self, value: T, source: str) -> None:
        self._value = value
        self._source = source

    def get_value(self) -> T:
        return self._value

    def map_value(self, fn: Callable[[T], T]) -> "ModelContainer[T]":
        return ModelContainer(fn(self._value), self._source)
```

### Constrained TypeVar

```python
from typing import TypeVar

TNumber = TypeVar("TNumber", int, float)


def add(a: TNumber, b: TNumber) -> TNumber:
    return a + b
```

---

## Literal Types

Use `Literal` for fixed string sets in function parameters and internal types:

```python
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
Purity = Literal["pure", "side_effecting"]
ConcurrencyPolicy = Literal["parallel_ok", "serialized", "singleflight"]


def configure_handler(
    purity: Purity,
    concurrency: ConcurrencyPolicy,
    log_level: LogLevel = "INFO",
) -> None:
    ...
```

---

## mypy Configuration

The project uses strict mypy configuration in `pyproject.toml`:

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
# Check all source code
poetry run mypy src/omnibase_core/

# Check specific module
poetry run mypy src/omnibase_core/models/container/

# With verbose output
poetry run mypy src/omnibase_core/ --verbose
```

### type: ignore Policy

When a `type: ignore` comment is necessary, always use a specific error code and include an explanation with a ticket reference:

```python
# CORRECT -- specific code + explanation
# NOTE(OMN-1234): mypy false-positive due to Protocol-based DI resolution.
value = container.get_service("ProtocolLogger")  # type: ignore[arg-type]

# WRONG -- generic ignore
value = some_call()  # type: ignore
```

---

## Banned Patterns

The following patterns are **forbidden** in omnibase_core. Pre-commit hooks and CI enforce these rules.

| Banned Pattern | Replacement |
|---|---|
| `Optional[X]` | `X \| None` |
| `Union[X, Y]` | `X \| Y` |
| `List[X]` | `list[X]` |
| `Dict[K, V]` | `dict[K, V]` |
| `Set[X]` | `set[X]` |
| `Tuple[X, Y]` | `tuple[X, Y]` |
| `FrozenSet[X]` | `frozenset[X]` |
| `Type[X]` | `type[X]` |
| `typing.Callable` | `collections.abc.Callable` |
| `typing.Iterator` | `collections.abc.Iterator` |
| `typing.Sequence` | `collections.abc.Sequence` |
| Bare `dict` without type params | `dict[str, ...]` with specific types |
| `# type: ignore` without error code | `# type: ignore[specific-code]` |

### Imports to Avoid

```python
# BANNED imports
from typing import Optional      # Use X | None
from typing import Union         # Use X | Y
from typing import List          # Use list[X]
from typing import Dict          # Use dict[K, V]
from typing import Set           # Use set[X]
from typing import Tuple         # Use tuple[X, Y]
from typing import FrozenSet     # Use frozenset[X]
from typing import Callable      # Use collections.abc.Callable
```

### Acceptable typing Imports

```python
# These are still needed from typing
from typing import (
    Any,              # Sometimes unavoidable at API boundaries
    ClassVar,         # Class-level type annotations
    Generic,          # Generic base class
    Literal,          # Fixed string sets
    Protocol,         # Interface definitions
    TypeVar,          # Type variables
    TypeGuard,        # Type narrowing
    TYPE_CHECKING,    # Import-time only
    Self,             # Self-referencing return types
    runtime_checkable,  # Protocol runtime checking
    cast,             # Type casting
    assert_never,     # Exhaustive matching
    overload,         # Function overloads
)
```

---

## Related Documentation

- [Pydantic Best Practices](../conventions/PYDANTIC_BEST_PRACTICES.md) -- ConfigDict patterns and model standards
- [Contract System](CONTRACT_SYSTEM.md) -- Contract architecture using these types
- [Dependency Injection](DEPENDENCY_INJECTION.md) -- Protocol-based DI
- [Container Types](CONTAINER_TYPES.md) -- ModelContainer[T] vs ModelONEXContainer
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Python Type Hints (stdlib)](https://docs.python.org/3/library/typing.html)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- [mypy Documentation](https://mypy.readthedocs.io/)
