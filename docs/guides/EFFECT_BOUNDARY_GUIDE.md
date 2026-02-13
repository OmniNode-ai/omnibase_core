> **Navigation**: [Home](../INDEX.md) > Guides > Effect Boundary Guide

# Effect Boundary Guide

**Version**: 1.0.0
**Last Updated**: 2026-01-14
**Ticket**: OMN-1147 (Non-Deterministic Effect Classification)

> **New in v0.6.4**: The effect boundary system provides a declarative way to annotate, classify, and enforce policies on non-deterministic effects. This enables replay-safe pipelines where external interactions (network, time, random, filesystem, database) are controlled during testing and replay execution.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Effect Categories](#effect-categories)
4. [Policy Levels](#policy-levels)
5. [Using the Mock Registry](#using-the-mock-registry)
6. [Complete Workflow](#complete-workflow)
7. [Best Practices](#best-practices)
8. [Thread Safety](#thread-safety)
9. [API Reference](#api-reference)
10. [Related Documentation](#related-documentation)

---

## Overview

The effect boundary system addresses a fundamental challenge in deterministic testing and execution replay: **non-deterministic effects** like time, randomness, and external I/O produce different results on each execution. Without control over these effects, tests become flaky and replay-based debugging becomes impossible.

### What is an Effect Boundary?

An effect boundary is a **marked scope** where non-deterministic operations are:
- **Classified** by category (network, time, random, etc.)
- **Tracked** for audit and compliance
- **Enforced** according to policy (block, warn, mock)

### System Components

```
                     @effect_boundary decorator
                              |
                              v
                    ModelEffectBoundary
                    (attached to function)
                              |
                              v
                    ModelEffectClassification
                    (category + metadata)
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
      EnumEffectCategory  EnumEffectPolicyLevel  ServiceEffectMockRegistry
      (NETWORK, TIME,     (STRICT, WARN,         (deterministic mocks
       RANDOM, etc.)       PERMISSIVE, MOCKED)    for MOCKED policy)
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Replay Safety** | Ensure pipelines produce identical results during replay |
| **Deterministic Testing** | Mock non-deterministic effects for reliable tests |
| **Audit Trail** | Track all effect executions for compliance |
| **Gradual Migration** | Use WARN mode to identify issues before enforcing |
| **Thread-Safe Models** | Immutable Pydantic models enable safe sharing |

---

## Quick Start

### Minimal Example

```python
from omnibase_core.decorators.decorator_effect_boundary import (
    effect_boundary,
    get_effect_boundary,
    has_effect_boundary,
)
from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel


# Mark a function as an effect boundary
@effect_boundary(
    boundary_id="my_service.fetch_data",
    categories=[EnumEffectCategory.NETWORK],
    policy=EnumEffectPolicyLevel.MOCKED,
    description="Fetches data from external API",
)
async def fetch_data(url: str) -> dict:
    """Fetch data from external API."""
    # Implementation...
    pass


# Later, retrieve the boundary metadata
boundary = get_effect_boundary(fetch_data)
if boundary:
    print(f"Boundary ID: {boundary.boundary_id}")
    print(f"Policy: {boundary.default_policy}")
    print(f"Categories: {[c.category for c in boundary.classifications]}")

# Check if function has boundary
if has_effect_boundary(fetch_data):
    print("Function is marked as an effect boundary")
```

### What the Decorator Does

1. **Creates classifications** for each category in the `categories` list
2. **Builds a `ModelEffectBoundary`** with the specified policy and metadata
3. **Attaches the boundary** to the function as `_effect_boundary` attribute
4. **Preserves function behavior** - the wrapper just passes through to the original function

---

## Effect Categories

The `EnumEffectCategory` enum defines six categories of non-deterministic effects:

| Category | Value | Description | Examples |
|----------|-------|-------------|----------|
| **NETWORK** | `"network"` | External network operations | HTTP calls, socket operations, DNS lookups |
| **TIME** | `"time"` | Time-dependent operations | `datetime.now()`, timestamps, durations |
| **RANDOM** | `"random"` | Randomness sources | `random.random()`, `uuid.uuid4()`, crypto RNG |
| **EXTERNAL_STATE** | `"external_state"` | External configuration | Environment variables, config files, system properties |
| **FILESYSTEM** | `"filesystem"` | File system operations | File reads/writes, directory operations |
| **DATABASE** | `"database"` | Database operations | Queries, transactions, connection state |

### Category Classification Methods

```python
from omnibase_core.enums.enum_effect_category import EnumEffectCategory

# Check if category involves external I/O
EnumEffectCategory.is_io_category(EnumEffectCategory.NETWORK)     # True
EnumEffectCategory.is_io_category(EnumEffectCategory.DATABASE)    # True
EnumEffectCategory.is_io_category(EnumEffectCategory.TIME)        # False

# Check if category depends on time or randomness
EnumEffectCategory.is_temporal_category(EnumEffectCategory.TIME)   # True
EnumEffectCategory.is_temporal_category(EnumEffectCategory.RANDOM) # True
EnumEffectCategory.is_temporal_category(EnumEffectCategory.NETWORK) # False
```

### Choosing Categories

| If your function... | Use Category |
|---------------------|--------------|
| Makes HTTP/gRPC calls | `NETWORK` |
| Connects to databases | `DATABASE` |
| Reads/writes files | `FILESYSTEM` |
| Uses `datetime.now()` or similar | `TIME` |
| Generates random values or UUIDs | `RANDOM` |
| Reads environment variables | `EXTERNAL_STATE` |
| Does multiple of the above | List all applicable categories |

**Example with Multiple Categories**:

```python
@effect_boundary(
    boundary_id="payment_service.process_payment",
    categories=[
        EnumEffectCategory.NETWORK,   # Calls payment API
        EnumEffectCategory.DATABASE,  # Updates transaction table
        EnumEffectCategory.TIME,      # Records timestamp
    ],
    policy=EnumEffectPolicyLevel.STRICT,
    description="Processes payment via external gateway and records transaction",
)
async def process_payment(order_id: str, amount: float) -> dict:
    ...
```

---

## Policy Levels

The `EnumEffectPolicyLevel` enum defines four enforcement levels:

| Level | Value | Behavior | Use Case |
|-------|-------|----------|----------|
| **STRICT** | `"strict"` | Block all non-deterministic effects | CI/CD, deterministic replay |
| **WARN** | `"warn"` | Log warning, allow execution | Migration, identifying issues |
| **PERMISSIVE** | `"permissive"` | Allow with audit trail | Production with monitoring |
| **MOCKED** | `"mocked"` | Replace with deterministic mocks | Testing, isolated replay |

### Policy Decision Methods

```python
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel

# Check if policy blocks execution
EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.STRICT)     # True
EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.WARN)       # False
EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.PERMISSIVE) # False
EnumEffectPolicyLevel.blocks_execution(EnumEffectPolicyLevel.MOCKED)     # False

# Check if policy requires mocking
EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.MOCKED)     # True
EnumEffectPolicyLevel.requires_mock(EnumEffectPolicyLevel.STRICT)     # False
```

### Choosing Policy Levels

```
                    Development                   Production
                         |                            |
                         v                            v
              +----------+----------+      +----------+----------+
              | MOCKED (tests) or   |      | PERMISSIVE (audit)  |
              | WARN (migration)    |      | or STRICT (replay)  |
              +---------------------+      +---------------------+
                         |
                         v
              +---------------------+
              | CI/CD: STRICT       |
              | (fail on non-det)   |
              +---------------------+
```

| Environment | Recommended Policy | Reason |
|-------------|-------------------|--------|
| **Unit Tests** | `MOCKED` | Inject deterministic mocks |
| **Integration Tests** | `MOCKED` or `STRICT` | Control external dependencies |
| **CI/CD** | `STRICT` | Fail fast on non-determinism |
| **Staging** | `WARN` | Identify issues without blocking |
| **Production** | `PERMISSIVE` | Allow with audit trail |
| **Replay/Debug** | `STRICT` or `MOCKED` | Ensure reproducibility |

### Using ModelEffectPolicySpec for Fine-Grained Control

For more granular policy control, use `ModelEffectPolicySpec`:

```python
from omnibase_core.models.effects.model_effect_policy import ModelEffectPolicySpec
from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel


# Create a policy that allows TIME but blocks NETWORK
policy = ModelEffectPolicySpec(
    policy_level=EnumEffectPolicyLevel.STRICT,
    allowed_categories=(EnumEffectCategory.TIME,),
    blocked_categories=(EnumEffectCategory.NETWORK,),
    require_mocks_for_categories=(EnumEffectCategory.DATABASE,),
)

# Check if a category is allowed
policy.is_category_allowed(EnumEffectCategory.TIME)      # True (explicitly allowed)
policy.is_category_allowed(EnumEffectCategory.NETWORK)   # False (explicitly blocked)
policy.is_category_allowed(EnumEffectCategory.RANDOM)    # False (STRICT blocks unlisted)

# Check if mocking is required
policy.requires_mock(EnumEffectCategory.DATABASE)  # True (in require_mocks_for_categories)
policy.requires_mock(EnumEffectCategory.TIME)      # False

# Check specific effect IDs
policy_with_allowlist = ModelEffectPolicySpec(
    policy_level=EnumEffectPolicyLevel.STRICT,
    allowlist_effect_ids=("safe_api.get_status",),
    denylist_effect_ids=("dangerous_api.delete_all",),
)

policy_with_allowlist.is_effect_allowed("safe_api.get_status", EnumEffectCategory.NETWORK)     # True
policy_with_allowlist.is_effect_allowed("dangerous_api.delete_all", EnumEffectCategory.NETWORK) # False
```

---

## Using the Mock Registry

When using `MOCKED` policy, the `ServiceEffectMockRegistry` provides deterministic mock implementations for non-deterministic effects.

### Basic Usage

```python
from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)
from datetime import datetime, timezone


# Create registry
registry = ServiceEffectMockRegistry()

# Register mocks for specific effects
registry.register_mock(
    "time.now",
    lambda: datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
)

registry.register_mock(
    "network.http_get",
    lambda url, **kwargs: {"status": 200, "body": {"mocked": True}},
)

registry.register_mock(
    "random.randint",
    lambda a, b: 42,  # Always return 42 for determinism
)

# Check if mock exists
if registry.has_mock("time.now"):
    mock_fn = registry.get_mock("time.now")
    result = mock_fn()
    print(f"Mocked time: {result}")  # 2025-06-15 12:00:00+00:00

# List all registered effects
print(registry.list_registered_effects())
# ['network.http_get', 'random.randint', 'time.now']
```

### Mock Registry API

| Method | Description |
|--------|-------------|
| `register_mock(effect_key, callable)` | Register a mock for an effect |
| `get_mock(effect_key)` | Get the mock callable (or None) |
| `has_mock(effect_key)` | Check if a mock is registered |
| `unregister_mock(effect_key)` | Remove a registered mock |
| `clear()` | Remove all registered mocks |
| `list_registered_effects()` | Get sorted list of effect keys |
| `mock_count` | Property: number of registered mocks |

### Effect Key Conventions

Use dot-separated namespaces for effect keys:

```python
# Category.operation pattern
"time.now"
"time.timestamp"
"random.randint"
"random.choice"
"network.http_get"
"network.http_post"
"database.query"
"database.execute"
"filesystem.read"
"filesystem.write"
```

### Test Fixture Example

```python
import pytest
from datetime import datetime, timezone
from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)


@pytest.fixture
def mock_registry():
    """Fixture providing a configured mock registry."""
    registry = ServiceEffectMockRegistry()

    # Register standard mocks
    registry.register_mock(
        "time.now",
        lambda: datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    registry.register_mock("random.random", lambda: 0.5)
    registry.register_mock("random.randint", lambda a, b: (a + b) // 2)

    yield registry

    # Cleanup
    registry.clear()


def test_deterministic_processing(mock_registry):
    """Test with mocked effects for determinism."""
    time_fn = mock_registry.get_mock("time.now")
    assert time_fn() == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    random_fn = mock_registry.get_mock("random.random")
    assert random_fn() == 0.5
```

---

## Complete Workflow

This section demonstrates the complete workflow from decorator annotation through policy enforcement.

### Step 1: Annotate Effect Boundaries

```python
# my_service/effects.py
from omnibase_core.decorators.decorator_effect_boundary import effect_boundary
from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel


@effect_boundary(
    boundary_id="user_service.fetch_user",
    categories=[EnumEffectCategory.NETWORK, EnumEffectCategory.DATABASE],
    policy=EnumEffectPolicyLevel.MOCKED,
    description="Fetches user from external service and caches in database",
    isolation_mechanisms=["MOCK_NETWORK", "DATABASE_READONLY_SNAPSHOT"],
)
async def fetch_user(user_id: str) -> dict:
    """Fetch user data from external service."""
    # In production: make real HTTP call
    # During replay: use mocked response
    response = await http_client.get(f"https://api.example.com/users/{user_id}")
    return response.json()


@effect_boundary(
    boundary_id="timestamp_service.get_timestamp",
    categories=[EnumEffectCategory.TIME],
    policy=EnumEffectPolicyLevel.MOCKED,
    description="Gets current timestamp",
)
def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

### Step 2: Configure Mock Registry

```python
# my_service/testing/mocks.py
from datetime import datetime, timezone
from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)


def create_test_registry() -> ServiceEffectMockRegistry:
    """Create a mock registry for deterministic testing."""
    registry = ServiceEffectMockRegistry()

    # Mock user API responses
    registry.register_mock(
        "user_service.fetch_user",
        lambda user_id: {
            "id": user_id,
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2025-01-01T00:00:00Z",
        },
    )

    # Mock timestamp
    registry.register_mock(
        "timestamp_service.get_timestamp",
        lambda: "2025-06-15T12:00:00+00:00",
    )

    return registry
```

### Step 3: Implement Policy Enforcement

```python
# my_service/runtime/enforcer.py
from omnibase_core.decorators.decorator_effect_boundary import get_effect_boundary
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)
from collections.abc import Callable
from typing import Any


class EffectEnforcer:
    """Enforces effect boundary policies at runtime."""

    def __init__(
        self,
        mock_registry: ServiceEffectMockRegistry | None = None,
    ):
        self.mock_registry = mock_registry or ServiceEffectMockRegistry()

    def execute_with_enforcement(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with effect policy enforcement."""
        boundary = get_effect_boundary(func)

        if boundary is None:
            # No boundary - execute normally
            return func(*args, **kwargs)

        policy = boundary.default_policy

        # STRICT: Block non-deterministic effects
        if policy == EnumEffectPolicyLevel.STRICT:
            if boundary.classifications:  # Has non-deterministic effects
                raise RuntimeError(
                    f"Effect '{boundary.boundary_id}' blocked in STRICT mode. "
                    f"Categories: {[c.category.value for c in boundary.classifications]}"
                )

        # WARN: Log warning but continue
        elif policy == EnumEffectPolicyLevel.WARN:
            if boundary.classifications:
                import logging
                logging.warning(
                    f"Non-deterministic effect detected: {boundary.boundary_id}"
                )

        # MOCKED: Use mock if available
        elif policy == EnumEffectPolicyLevel.MOCKED:
            if self.mock_registry.has_mock(boundary.boundary_id):
                mock_fn = self.mock_registry.get_mock(boundary.boundary_id)
                return mock_fn(*args, **kwargs)

        # PERMISSIVE or no mock available: Execute normally
        return func(*args, **kwargs)
```

### Step 4: Use in Tests

```python
# tests/test_user_service.py
import pytest
from my_service.effects import fetch_user, get_current_timestamp
from my_service.testing.mocks import create_test_registry
from my_service.runtime.enforcer import EffectEnforcer


@pytest.fixture
def enforcer():
    """Create enforcer with test mocks."""
    registry = create_test_registry()
    return EffectEnforcer(mock_registry=registry)


def test_fetch_user_mocked(enforcer):
    """Test fetch_user with mocked response."""
    result = enforcer.execute_with_enforcement(fetch_user, "user-123")

    assert result["id"] == "user-123"
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"


def test_get_timestamp_mocked(enforcer):
    """Test timestamp with mocked value."""
    result = enforcer.execute_with_enforcement(get_current_timestamp)

    assert result == "2025-06-15T12:00:00+00:00"


def test_multiple_calls_deterministic(enforcer):
    """Verify multiple calls produce identical results."""
    result1 = enforcer.execute_with_enforcement(fetch_user, "user-456")
    result2 = enforcer.execute_with_enforcement(fetch_user, "user-456")

    assert result1 == result2  # Deterministic!
```

### Step 5: Use in CI/CD with STRICT Mode

```python
# my_service/runtime/ci_enforcer.py
from omnibase_core.decorators.decorator_effect_boundary import (
    get_effect_boundary,
    has_effect_boundary,
)
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from collections.abc import Callable
from typing import Any
import os


def execute_with_strict_enforcement(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute with STRICT enforcement for CI/CD.

    Raises RuntimeError if function has non-deterministic effects
    and is not properly mocked.
    """
    if not has_effect_boundary(func):
        return func(*args, **kwargs)

    boundary = get_effect_boundary(func)

    # In CI, override to STRICT regardless of decorator policy
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        if boundary.classifications:
            raise RuntimeError(
                f"CI ENFORCEMENT: Non-deterministic effect '{boundary.boundary_id}' "
                f"must be mocked. Categories: "
                f"{[c.category.value for c in boundary.classifications]}"
            )

    return func(*args, **kwargs)
```

---

## Best Practices

### 1. Annotate at the Boundary

Mark the function that **directly** interacts with non-deterministic sources, not callers:

```python
# GOOD: Mark the actual effect
@effect_boundary(
    boundary_id="http.fetch",
    categories=[EnumEffectCategory.NETWORK],
    policy=EnumEffectPolicyLevel.MOCKED,
)
async def fetch(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()


# BAD: Don't mark high-level orchestrators unless they add effects
def process_order(order_id: str) -> dict:
    # This just calls fetch() - no new effects here
    return fetch(f"/orders/{order_id}")
```

### 2. Use Descriptive Boundary IDs

Use hierarchical, descriptive IDs:

```python
# GOOD: Clear, hierarchical, unique
boundary_id="payment_gateway.charge_card"
boundary_id="user_service.v2.get_profile"
boundary_id="cache.redis.get"

# BAD: Vague, non-unique
boundary_id="do_thing"
boundary_id="api_call"
boundary_id="fetch"
```

### 3. Include All Applicable Categories

Don't under-specify categories:

```python
# GOOD: Lists all effects
@effect_boundary(
    boundary_id="order_processor.submit",
    categories=[
        EnumEffectCategory.NETWORK,    # Calls payment API
        EnumEffectCategory.DATABASE,   # Inserts order record
        EnumEffectCategory.TIME,       # Records timestamp
    ],
    ...
)

# BAD: Missing categories
@effect_boundary(
    boundary_id="order_processor.submit",
    categories=[EnumEffectCategory.NETWORK],  # Missing DATABASE and TIME!
    ...
)
```

### 4. Choose Policy Based on Context

```python
# For production services - use PERMISSIVE with monitoring
@effect_boundary(
    boundary_id="metrics.publish",
    categories=[EnumEffectCategory.NETWORK],
    policy=EnumEffectPolicyLevel.PERMISSIVE,  # Allow but audit
)

# For test fixtures - use MOCKED
@effect_boundary(
    boundary_id="test.random_id",
    categories=[EnumEffectCategory.RANDOM],
    policy=EnumEffectPolicyLevel.MOCKED,  # Always mock in tests
)

# For replay-critical paths - use STRICT
@effect_boundary(
    boundary_id="replay.state_load",
    categories=[EnumEffectCategory.FILESYSTEM],
    policy=EnumEffectPolicyLevel.STRICT,  # Must be deterministic
)
```

### 5. Document Isolation Mechanisms

Specify available isolation mechanisms:

```python
@effect_boundary(
    boundary_id="db.query_orders",
    categories=[EnumEffectCategory.DATABASE],
    policy=EnumEffectPolicyLevel.MOCKED,
    isolation_mechanisms=[
        "DATABASE_READONLY_SNAPSHOT",  # Use read replica snapshot
        "DATABASE_TRANSACTION_ROLLBACK",  # Wrap in rollback transaction
    ],
    description="Query orders table with optional date filter",
)
```

### 6. Write Deterministic Mocks

Mocks should be stateless and deterministic:

```python
# GOOD: Stateless, deterministic
registry.register_mock(
    "time.now",
    lambda: datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
)

# BAD: Stateful, non-deterministic
counter = [0]
registry.register_mock(
    "id.next",
    lambda: (counter[0] := counter[0] + 1),  # Depends on call order!
)
```

---

## Thread Safety

### Thread-Safe Components

| Component | Thread-Safe? | Notes |
|-----------|--------------|-------|
| `ModelEffectBoundary` | Yes | Frozen Pydantic model |
| `ModelEffectClassification` | Yes | Frozen Pydantic model |
| `ModelEffectPolicySpec` | Yes | Frozen Pydantic model |
| `@effect_boundary` decorator | Yes | Attaches immutable metadata |
| `get_effect_boundary()` | Yes | Read-only attribute access |
| `has_effect_boundary()` | Yes | Read-only attribute check |

### NOT Thread-Safe Components

| Component | Thread-Safe? | Mitigation |
|-----------|--------------|------------|
| `ServiceEffectMockRegistry` | No | Use thread-local instances |

### Using Thread-Local Mock Registry

```python
import threading
from omnibase_core.services.replay.service_effect_mock_registry import (
    ServiceEffectMockRegistry,
)

# Thread-local storage
_thread_local = threading.local()


def get_mock_registry() -> ServiceEffectMockRegistry:
    """Get thread-local mock registry instance."""
    if not hasattr(_thread_local, "registry"):
        _thread_local.registry = ServiceEffectMockRegistry()
        # Configure default mocks...
        _thread_local.registry.register_mock("time.now", lambda: "2025-01-01T00:00:00Z")
    return _thread_local.registry


# Usage in multi-threaded context
def worker():
    registry = get_mock_registry()  # Each thread gets its own
    mock = registry.get_mock("time.now")
    result = mock()
    print(f"Thread {threading.current_thread().name}: {result}")
```

### Sharing Models Across Threads

The decorator-attached metadata is safe to share:

```python
from omnibase_core.decorators.decorator_effect_boundary import (
    effect_boundary,
    get_effect_boundary,
)
from omnibase_core.enums.enum_effect_category import EnumEffectCategory
import threading


@effect_boundary(
    boundary_id="shared.effect",
    categories=[EnumEffectCategory.TIME],
)
def my_effect():
    pass


def worker():
    # Safe: ModelEffectBoundary is frozen/immutable
    boundary = get_effect_boundary(my_effect)
    print(f"Thread {threading.current_thread().name}: {boundary.boundary_id}")


# Multiple threads can safely read the same boundary metadata
threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

---

## API Reference

### Decorator Functions

| Function | Purpose | Import |
|----------|---------|--------|
| `effect_boundary()` | Decorator to mark functions as effect boundaries | `from omnibase_core.decorators.decorator_effect_boundary import effect_boundary` |
| `get_effect_boundary()` | Retrieve boundary metadata from decorated function | `from omnibase_core.decorators.decorator_effect_boundary import get_effect_boundary` |
| `has_effect_boundary()` | Check if function has boundary metadata | `from omnibase_core.decorators.decorator_effect_boundary import has_effect_boundary` |

### Models

| Model | Purpose | Import |
|-------|---------|--------|
| `ModelEffectBoundary` | Defines effect boundary with classifications and policy | `from omnibase_core.models.effects.model_effect_boundary import ModelEffectBoundary` |
| `ModelEffectClassification` | Classification of a single effect type | `from omnibase_core.models.effects.model_effect_classification import ModelEffectClassification` |
| `ModelEffectPolicySpec` | Fine-grained policy specification | `from omnibase_core.models.effects.model_effect_policy import ModelEffectPolicySpec` |

### Enums

| Enum | Purpose | Import |
|------|---------|--------|
| `EnumEffectCategory` | Categories of non-deterministic effects | `from omnibase_core.enums.enum_effect_category import EnumEffectCategory` |
| `EnumEffectPolicyLevel` | Policy enforcement levels | `from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel` |

### Services

| Service | Purpose | Import |
|---------|---------|--------|
| `ServiceEffectMockRegistry` | Registry for deterministic mock implementations | `from omnibase_core.services.replay.service_effect_mock_registry import ServiceEffectMockRegistry` |

---

## Related Documentation

- [Replay Safety Integration Guide](replay/REPLAY_SAFETY_INTEGRATION.md) - Comprehensive replay safety system
- [Effect Subcontract Guide](EFFECT_SUBCONTRACT_GUIDE.md) - Declarative effect operations
- [Threading Guide](THREADING.md) - Thread safety patterns
- [Effect Node Tutorial](node-building/04_EFFECT_NODE_TUTORIAL.md) - Building EFFECT nodes

---

**Version History**:
- **v0.6.4**: Initial effect boundary system (OMN-1147)
