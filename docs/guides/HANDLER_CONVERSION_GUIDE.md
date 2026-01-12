# Handler Conversion Guide

**Status**: Active
**Version**: 1.0.0
**Last Updated**: 2026-01-03
**Related Tickets**: OMN-1112, OMN-1113, OMN-1114, OMN-1162

---

## Table of Contents

1. [Overview](#overview)
2. [Why Move from Mixins to Handlers?](#why-move-from-mixins-to-handlers)
3. [Before/After Comparison](#beforeafter-comparison)
4. [Handler Design Principles](#handler-design-principles)
5. [Step-by-Step Conversion Process](#step-by-step-conversion-process)
6. [Example Conversions](#example-conversions)
7. [Naming Conventions](#naming-conventions)
8. [Testing Requirements](#testing-requirements)
9. [Related Documents](#related-documents)

---

## Quick Start

For developers who want to get started quickly:

### 1. Create Your Handler

```python
# src/omnibase_core/pipeline/handlers/handler_capability_example.py
from pydantic import BaseModel, ConfigDict, PrivateAttr


class HandlerCapabilityExample(BaseModel):
    """Example capability handler."""

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    enabled: bool = True
    _internal_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def do_something(self, value: str) -> str:
        """Perform the capability action."""
        if self.enabled:
            self._internal_data[value] = True
        return value
```

### 2. Export in __init__.py

```python
# src/omnibase_core/pipeline/handlers/__init__.py
from omnibase_core.pipeline.handlers.handler_capability_example import (
    HandlerCapabilityExample,
)

__all__ = [
    "HandlerCapabilityExample",
    # ... other handlers
]
```

### 3. Write Tests First (TDD)

```python
# tests/unit/pipeline/handlers/test_capability_example.py
import pytest
from omnibase_core.pipeline.handlers.handler_capability_example import (
    HandlerCapabilityExample,
)


@pytest.mark.unit
class TestHandlerCapabilityExample:
    def test_handler_works_standalone(self) -> None:
        handler = HandlerCapabilityExample()
        result = handler.do_something("test")
        assert result == "test"
```

### 4. Run Validation

```bash
poetry run pytest tests/unit/pipeline/handlers/test_capability_example.py -v
poetry run mypy src/omnibase_core/pipeline/handlers/handler_capability_example.py
```

---

## Overview

This guide provides step-by-step instructions for converting existing mixin-based capabilities to the new handler-based architecture. The handler pattern replaces inheritance-based mixins with composition-based, standalone Pydantic models that can be orchestrated by the Pipeline Runner.

For the complete architectural vision and rationale, see [MIXINS_TO_HANDLERS_REFACTOR.md](../architecture/MIXINS_TO_HANDLERS_REFACTOR.md).

### Key Benefits of Handler Architecture

| Benefit | Description |
|---------|-------------|
| **Loose Coupling** | Handlers are independent, composable units with no inheritance hierarchy |
| **Testability** | Each handler can be tested in complete isolation |
| **Explicit Ordering** | Configuration determines execution order, not Python MRO |
| **Runtime Visibility** | The execution manifest records exactly what ran and why |
| **Determinism** | Same inputs produce same outputs, enabling replay |
| **Type Safety** | Pydantic models provide validation and serialization |

---

## Why Move from Mixins to Handlers?

### Pain Points with Mixins

The current mixin architecture has several limitations:

1. **Tight Coupling**: Mixins inherit from node classes, creating complex inheritance hierarchies
2. **Testing Challenges**: Hard to test mixins in isolation without instantiating the full node
3. **Ordering Ambiguity**: Python's MRO (Method Resolution Order) determines behavior, not explicit configuration
4. **Composition Complexity**: Diamond inheritance problems when using multiple mixins
5. **Runtime Introspection**: Difficult to understand what capabilities are active at runtime
6. **State Management**: Mixins use `object.__setattr__` patterns to bypass Pydantic validation

### Handler Architecture Advantages

The handler pattern solves these problems by:

1. **Composition over Inheritance**: Handlers are composed at runtime, not through class hierarchy
2. **Explicit Dependencies**: Handlers declare dependencies explicitly, resolved via topological sort
3. **Configuration-Driven**: Execution order and behavior determined by declarative configuration
4. **Observable Execution**: The manifest provides complete visibility into what ran and why
5. **Pydantic-Native**: Full Pydantic model support for configuration, validation, and serialization

---

## Before/After Comparison

### Mixin-Based Approach (Legacy)

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class MyComputeNode(NodeCompute, MixinMetrics, MixinCaching):
    """Node with metrics and caching via multiple inheritance."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Mixin state initialized via super().__init__ chain
        # Order depends on MRO, not explicit configuration

    async def execute_compute(self, contract):
        # Record metric (from MixinMetrics)
        self.record_metric("compute_started", 1.0)

        # Check cache (from MixinCaching)
        cache_key = self.generate_cache_key(contract.input_data)
        cached = await self.get_cached(cache_key)
        if cached:
            return cached

        # Do computation
        result = await self._expensive_computation(contract)

        # Store in cache
        await self.set_cached(cache_key, result, ttl_seconds=600)

        return result
```

**Problems**:
- Multiple inheritance creates complex MRO
- Mixin methods are implicitly available
- Hard to test compute logic without mixin behavior
- No visibility into execution order

### Handler-Based Approach (New)

```python
from omnibase_core.pipeline import (
    RunnerPipeline,
    BuilderExecutionPlan,
    RegistryHook,
    ModelPipelineHook,
    ModelPipelineContext,
)
from omnibase_core.pipeline.handlers.handler_capability_metrics import (
    HandlerCapabilityMetrics,
)
from omnibase_core.pipeline.handlers.handler_capability_caching import (
    HandlerCapabilityCaching,
)


# Handlers are standalone, configured independently
metrics_handler = HandlerCapabilityMetrics(
    namespace="my_node",
    enabled=True,
)

caching_handler = HandlerCapabilityCaching(
    enabled=True,
    default_ttl_seconds=600,
)

# Register hooks with explicit ordering
registry = RegistryHook()

registry.register(ModelPipelineHook(
    hook_name="metrics-before",
    phase="before",
    priority=10,
    callable_ref="hooks.metrics.before",
))

registry.register(ModelPipelineHook(
    hook_name="cache-check",
    phase="before",
    priority=20,
    dependencies=["metrics-before"],
    callable_ref="hooks.caching.check",
))

registry.register(ModelPipelineHook(
    hook_name="compute",
    phase="execute",
    callable_ref="hooks.compute.execute",
))

registry.register(ModelPipelineHook(
    hook_name="cache-store",
    phase="after",
    callable_ref="hooks.caching.store",
))

registry.register(ModelPipelineHook(
    hook_name="metrics-after",
    phase="after",
    dependencies=["cache-store"],
    callable_ref="hooks.metrics.after",
))

registry.freeze()

# Build and execute
builder = BuilderExecutionPlan(registry=registry)
plan, warnings = builder.build()

runner = RunnerPipeline(plan=plan, callable_registry=callables)
result = await runner.run()
```

**Benefits**:
- Clear, explicit execution order
- Each handler tested independently
- Full visibility via execution manifest
- Configuration determines behavior

---

## Handler Design Principles

### 1. Standalone Classes (No Node Inheritance)

Handlers must NOT inherit from node classes. They are standalone units:

```python
# CORRECT: Standalone Pydantic model
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class HandlerCapabilityMetrics(BaseModel):
    """Metrics capability handler - standalone, no inheritance from nodes."""

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    # Configuration fields (public)
    namespace: str = "onex"
    enabled: bool = True

    # Internal state (private) - not serialized
    _metrics_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value."""
        if self.enabled:
            self._metrics_data[name] = {"value": value, "tags": {}}


# WRONG: Inherits from node or mixin
class BadHandler(NodeCompute, MixinMetrics):  # DO NOT DO THIS
    pass
```

### 2. Pydantic BaseModel for Configuration

All handlers must be Pydantic BaseModel subclasses:

```python
from pydantic import BaseModel, ConfigDict, Field


class HandlerCapabilityCaching(BaseModel):
    """Caching capability handler."""

    model_config = ConfigDict(
        frozen=False,  # Allow mutation of internal state
        extra="forbid",  # Strict configuration validation
        from_attributes=True,  # Required for pytest-xdist compatibility
    )

    # Configuration (validated by Pydantic)
    enabled: bool = True
    default_ttl_seconds: int = Field(
        default=3600, ge=0, description="Default TTL in seconds"
    )
```

### 3. PrivateAttr for Internal State

Use `PrivateAttr` for internal state that should not be serialized:

```python
from pydantic import BaseModel, PrivateAttr


class HandlerCapabilityCaching(BaseModel):
    """Caching handler with internal state."""

    # Public configuration
    enabled: bool = True
    default_ttl_seconds: int = 3600

    # Private internal state (not serialized)
    _cache_data: dict[str, object] = PrivateAttr(default_factory=dict)
```

### 4. "Handler" Prefix for All Capability Classes

All handler capability classes MUST follow the `Handler<Type><Name>` naming pattern:

```python
# CORRECT
class HandlerCapabilityMetrics(BaseModel): ...
class HandlerCapabilityCaching(BaseModel): ...
class HandlerCapabilityRetry(BaseModel): ...

# WRONG
class MetricsHandler(BaseModel): ...    # Missing "Handler" prefix and wrong order
class CachingCapability(BaseModel): ... # Missing "Handler" prefix pattern
```

### 5. File Naming Convention

Handler files follow the pattern `handler_capability_<name>.py`:

```text
src/omnibase_core/pipeline/handlers/
    handler_capability_metrics.py      # HandlerCapabilityMetrics
    handler_capability_caching.py      # HandlerCapabilityCaching
    # Future:
    # handler_capability_retry.py        # HandlerCapabilityRetry
    # handler_capability_circuit_breaker.py  # HandlerCapabilityCircuitBreaker
```

---

## Step-by-Step Conversion Process

### Step 1: Identify Mixin Functionality

Analyze the existing mixin to understand:
- What configuration options does it have?
- What internal state does it maintain?
- What methods does it expose?
- How does it interact with node lifecycle?

**Example Analysis - MixinMetrics**:

```python
# From mixin_metrics.py
class MixinMetrics:
    # Configuration
    _metrics_enabled: bool  # Whether metrics are enabled

    # Internal state
    _metrics_data: dict[str, dict]  # Metric storage

    # Methods
    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None
    def increment_counter(self, counter_name: str, value: int = 1) -> None
    def get_metrics(self) -> dict[str, TypedDictMetricEntry]
    def reset_metrics(self) -> None
```

### Step 2: Design Handler Interface (Pydantic Model)

Convert the mixin to a Pydantic model:

1. Configuration options become public fields
2. Internal state becomes `PrivateAttr`
3. Methods remain as instance methods

```python
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from typing import Any


class HandlerCapabilityMetrics(BaseModel):
    """Metrics capability handler.

    Provides performance metrics collection capabilities.
    """

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    # Configuration (was implicit in mixin)
    namespace: str = "onex"
    enabled: bool = True

    # Internal state (converted from object.__setattr__ pattern)
    _metrics_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def record_metric(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a metric value."""
        if not self.enabled:
            return
        self._metrics_data[metric_name] = {
            "value": value,
            "tags": tags or {},
        }

    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        if not self.enabled:
            return
        current = self._metrics_data.get(counter_name, {"value": 0})["value"]
        self._metrics_data[counter_name] = {"value": current + value}

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """Get current metrics data."""
        return self._metrics_data.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics data."""
        self._metrics_data.clear()
```

### Step 3: Write TDD Tests Based on Existing Mixin Tests

Before implementing, write tests based on existing mixin tests:

```python
# tests/unit/pipeline/handlers/test_capability_metrics.py
import pytest
from omnibase_core.pipeline.handlers.handler_capability_metrics import (
    HandlerCapabilityMetrics,
)


class TestHandlerCapabilityMetrics:
    """Tests for HandlerCapabilityMetrics handler."""

    def test_record_metric_stores_value(self) -> None:
        """Test that record_metric stores the metric value."""
        handler = HandlerCapabilityMetrics(enabled=True, namespace="test")

        handler.record_metric("test_metric", 42.0)

        metrics = handler.get_metrics()
        assert "test_metric" in metrics
        assert metrics["test_metric"]["value"] == 42.0

    def test_record_metric_with_tags(self) -> None:
        """Test that record_metric stores tags."""
        handler = HandlerCapabilityMetrics()

        handler.record_metric("tagged_metric", 1.0, tags={"env": "test"})

        metrics = handler.get_metrics()
        assert metrics["tagged_metric"]["tags"] == {"env": "test"}

    def test_record_metric_disabled(self) -> None:
        """Test that metrics are not recorded when disabled."""
        handler = HandlerCapabilityMetrics(enabled=False)

        handler.record_metric("ignored_metric", 100.0)

        assert handler.get_metrics() == {}

    def test_increment_counter_increases_value(self) -> None:
        """Test that increment_counter increases the counter."""
        handler = HandlerCapabilityMetrics()

        handler.increment_counter("requests")
        handler.increment_counter("requests")
        handler.increment_counter("requests", value=5)

        metrics = handler.get_metrics()
        assert metrics["requests"]["value"] == 7

    def test_reset_metrics_clears_all(self) -> None:
        """Test that reset_metrics clears all stored metrics."""
        handler = HandlerCapabilityMetrics()
        handler.record_metric("metric1", 1.0)
        handler.record_metric("metric2", 2.0)

        handler.reset_metrics()

        assert handler.get_metrics() == {}

    def test_get_metrics_returns_copy(self) -> None:
        """Test that get_metrics returns a copy, not the original."""
        handler = HandlerCapabilityMetrics()
        handler.record_metric("test", 1.0)

        metrics = handler.get_metrics()
        metrics["test"]["value"] = 999.0

        # Original should be unchanged
        assert handler.get_metrics()["test"]["value"] == 1.0

    def test_handler_is_standalone(self) -> None:
        """Test that handler works without any node context."""
        # This is the key difference from mixins - no node required
        handler = HandlerCapabilityMetrics(namespace="standalone")

        handler.record_metric("standalone_metric", 123.0)

        assert handler.get_metrics()["standalone_metric"]["value"] == 123.0
```

### Step 4: Implement Handler

Implement the handler to make all tests pass. Follow the design from Step 2.

### Step 5: Verify All Original Tests Pass

Ensure the handler provides the same functionality as the original mixin:

```bash
# Run handler tests
poetry run pytest tests/unit/pipeline/handlers/test_capability_metrics.py -v

# Run original mixin tests (should still pass)
poetry run pytest tests/unit/mixins/test_mixin_metrics.py -v
```

### Step 6: Document in Conversion Checklist

Update the conversion checklist (see [HANDLER_CONVERSION_CHECKLIST.md](HANDLER_CONVERSION_CHECKLIST.md)):

```markdown
| Mixin | Handler | Status | Tests | Notes |
|-------|---------|--------|-------|-------|
| MixinMetrics | HandlerCapabilityMetrics | Complete | 7/7 | Added namespace config |
```

---

## Example Conversions

### Example 1: MixinMetrics to HandlerCapabilityMetrics

**Original Mixin** (`mixin_metrics.py`):

```python
class MixinMetrics:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_metrics_enabled", True)
        object.__setattr__(self, "_metrics_data", {})

    def record_metric(self, metric_name: str, value: float, tags: dict | None = None):
        metrics_enabled = object.__getattribute__(self, "_metrics_enabled")
        if metrics_enabled:
            metrics_data = object.__getattribute__(self, "_metrics_data")
            metrics_data[metric_name] = {"value": value, "tags": tags or {}}
```

**Converted Handler** (`handler_capability_metrics.py`):

```python
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class HandlerCapabilityMetrics(BaseModel):
    """Standalone metrics capability handler."""

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    namespace: str = "onex"
    enabled: bool = True

    _metrics_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def record_metric(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        if self.enabled:
            self._metrics_data[metric_name] = {"value": value, "tags": tags or {}}

    def get_metrics(self) -> dict[str, object]:
        return self._metrics_data.copy()
```

**Key Differences**:
- No `object.__setattr__` hacks
- Configuration via Pydantic fields
- Internal state via `PrivateAttr`
- Works standalone without node context

### Example 2: MixinCaching to HandlerCapabilityCaching

**Original Mixin** (`mixin_caching.py`):

```python
class MixinCaching:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_enabled = True
        self._cache_data: dict[str, object] = {}

    async def get_cached(self, cache_key: str) -> Any | None:
        if not self._cache_enabled:
            return None
        return self._cache_data.get(cache_key)

    async def set_cached(self, cache_key: str, value: Any, ttl_seconds: int = 3600):
        if self._cache_enabled:
            self._cache_data[cache_key] = value
```

**Converted Handler** (`handler_capability_caching.py`):

```python
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from typing import Any
import hashlib
import json


class HandlerCapabilityCaching(BaseModel):
    """Standalone caching capability handler."""

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    enabled: bool = True
    default_ttl_seconds: int = Field(
        default=3600, ge=0, description="Default TTL in seconds"
    )

    # Private attribute for internal cache storage (not serialized)
    _cache_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def generate_cache_key(self, data: Any) -> str:
        """Generate a cache key from data using SHA256 hash."""
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return hashlib.sha256(str(data).encode()).hexdigest()

    async def get_cached(self, cache_key: str) -> Any | None:
        """Retrieve cached value."""
        if not self.enabled:
            return None
        return self._cache_data.get(cache_key)

    async def set_cached(
        self, cache_key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """Store value in cache."""
        if self.enabled:
            self._cache_data[cache_key] = value

    async def invalidate_cache(self, cache_key: str) -> None:
        """Invalidate a cache entry."""
        self._cache_data.pop(cache_key, None)

    async def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache_data.clear()

    def get_cache_stats(self) -> dict[str, object]:
        """Get cache statistics."""
        return {
            "enabled": self.enabled,
            "entries": len(self._cache_data),
            "keys": list(self._cache_data.keys()),
        }
```

---

## Naming Conventions

### Class Names

All handler classes MUST follow the pattern `Handler<Capability>`:

| Pattern | Example | Description |
|---------|---------|-------------|
| `HandlerCapability<Name>` | `HandlerCapabilityMetrics` | Capability handlers |
| `HandlerIntegration<Name>` | `HandlerIntegrationKafka` | Integration handlers |

### File Names

Files follow the pattern `handler_<type>_<name>.py`:

| Type | File Pattern | Example |
|------|--------------|---------|
| Capability | `handler_capability_<name>.py` | `handler_capability_metrics.py` |
| Integration | `handler_integration_<name>.py` | `handler_integration_kafka.py` |

### Directory Structure

```text
src/omnibase_core/pipeline/
    handlers/
        __init__.py
        handler_capability_caching.py
        handler_capability_metrics.py
        # Future handlers:
        # handler_capability_retry.py
        # handler_capability_circuit_breaker.py
```

### Test File Names

Test files follow the pattern `test_<capability_name>.py`:

```text
tests/unit/pipeline/handlers/
    __init__.py
    test_capability_caching.py
    test_capability_metrics.py
    # Future tests:
    # test_capability_retry.py
```

---

## Testing Requirements

### TDD Approach: Write Tests FIRST

The conversion process follows Test-Driven Development:

1. **Copy tests from existing mixin tests** - Start with the same test cases
2. **Adapt to handler interface** - Update to use standalone handler
3. **Add standalone tests** - Verify handler works without node context
4. **Run tests before implementation** - Confirm tests fail appropriately
5. **Implement to make tests pass** - Write minimal code to pass tests

### Test Categories

#### 1. Unit Tests (Required)

Test handler in isolation:

```python
def test_handler_configuration():
    """Test that handler accepts configuration."""
    handler = HandlerCapabilityMetrics(enabled=True, namespace="test")
    assert handler.enabled is True
    assert handler.namespace == "test"


def test_handler_default_configuration():
    """Test that handler has sensible defaults."""
    handler = HandlerCapabilityMetrics()
    assert handler.enabled is True  # Default enabled
```

#### 2. Standalone Tests (Required)

Verify handler works without any node context:

```python
def test_handler_works_standalone():
    """Test that handler functions without node context."""
    # No container, no node, no mixin inheritance
    handler = HandlerCapabilityMetrics()

    handler.record_metric("standalone_test", 42.0)

    assert handler.get_metrics()["standalone_test"]["value"] == 42.0
```

#### 3. Serialization Tests (Required)

Test Pydantic serialization/deserialization:

```python
def test_handler_serialization():
    """Test that handler configuration serializes correctly."""
    handler = HandlerCapabilityMetrics(enabled=True, namespace="prod")

    # Serialize to dict
    data = handler.model_dump()
    assert data["enabled"] is True
    assert data["namespace"] == "prod"

    # Private attrs should NOT be in serialized output
    assert "_metrics_data" not in data


def test_handler_deserialization():
    """Test that handler can be created from dict."""
    data = {"enabled": False, "namespace": "test"}

    handler = HandlerCapabilityMetrics.model_validate(data)

    assert handler.enabled is False
    assert handler.namespace == "test"
```

#### 4. Integration with Pipeline (Optional but Recommended)

Test handler with Pipeline Runner:

```python
@pytest.mark.asyncio
async def test_handler_in_pipeline():
    """Test handler integration with pipeline runner."""
    from omnibase_core.pipeline import (
        RunnerPipeline,
        BuilderExecutionPlan,
        RegistryHook,
        ModelPipelineHook,
        ModelPipelineContext,
    )

    # Setup handler
    metrics = HandlerCapabilityMetrics(namespace="pipeline_test")

    # Create hook that uses handler
    def metrics_hook(ctx: ModelPipelineContext) -> None:
        metrics.record_metric("pipeline_executed", 1.0)
        ctx.data["metrics_recorded"] = True

    # Setup pipeline
    registry = RegistryHook()
    registry.register(ModelPipelineHook(
        hook_name="metrics",
        phase="after",
        callable_ref="test.metrics",
    ))
    registry.freeze()

    builder = BuilderExecutionPlan(registry=registry)
    plan, _ = builder.build()

    runner = RunnerPipeline(
        plan=plan,
        callable_registry={"test.metrics": metrics_hook}
    )

    result = await runner.run()

    assert result.success
    assert result.context.data["metrics_recorded"] is True
    assert metrics.get_metrics()["pipeline_executed"]["value"] == 1.0
```

### Running Tests

```bash
# Run all capability handler tests
poetry run pytest tests/unit/pipeline/handlers/ -v

# Run specific handler tests
poetry run pytest tests/unit/pipeline/handlers/test_capability_metrics.py -v

# Run with coverage
poetry run pytest tests/unit/pipeline/handlers/ --cov=src/omnibase_core/pipeline/handlers

# Run both mixin and handler tests (verify compatibility)
poetry run pytest tests/unit/mixins/ tests/unit/pipeline/handlers/ -v
```

---

## Related Documents

- [MIXINS_TO_HANDLERS_REFACTOR.md](../architecture/MIXINS_TO_HANDLERS_REFACTOR.md) - Complete architectural vision
- [PIPELINE_HOOK_REGISTRY.md](PIPELINE_HOOK_REGISTRY.md) - Pipeline Runner and Hook Registry guide
- [ONEX_FOUR_NODE_ARCHITECTURE.md](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node type overview
- [THREADING.md](THREADING.md) - Thread safety considerations

### Related Tickets

- **OMN-1112**: First Pure Handler Conversions
- **OMN-1113**: Manifest Generation & Observability
- **OMN-1114**: Pipeline Runner & Hook Registry
- **OMN-1162**: Mixins to Handlers Refactor Documentation

---

**Last Updated**: 2026-01-03
**Version**: 1.0.0
