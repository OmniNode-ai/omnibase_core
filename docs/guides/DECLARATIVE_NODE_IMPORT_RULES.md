# Declarative Node Import Rules

**Version**: 1.0.0
**Last Updated**: 2025-12-12
**Related Issue**: OMN-203 (AST-based purity linter for declarative nodes)

## Overview

Declarative nodes (`NodeCompute`, `NodeReducer`) must remain **pure** to guarantee determinism, testability, and architectural consistency. This document defines which imports are allowed and which are disallowed, along with the rationale for each restriction.

Purity in this context means:
- **No side effects** - Functions should not modify external state
- **Deterministic output** - Same inputs always produce same outputs
- **No hidden dependencies** - All dependencies explicit in function signatures
- **Strong typing** - Types fully specified, no `Any` escape hatches

---

## Table of Contents

1. [Node Types and Purity Requirements](#node-types-and-purity-requirements)
2. [Disallowed Imports](#disallowed-imports)
3. [Allowed Imports](#allowed-imports)
4. [Exemptions](#exemptions)
5. [CI Enforcement](#ci-enforcement)
6. [Migration Guide](#migration-guide)
7. [Related Documentation](#related-documentation)

---

## Node Types and Purity Requirements

| Node Type | Purity Required | Import Restrictions | Rationale |
|-----------|-----------------|---------------------|-----------|
| `NodeCompute` | **YES** | Full restrictions | Pure computation - no side effects, deterministic |
| `NodeReducer` | **YES** | Full restrictions | FSM-driven state management - pure transitions |
| `NodeEffect` | **NO** | No restrictions | Explicitly designed for external I/O and side effects |
| `NodeOrchestrator` | **NO** | No restrictions | Workflow coordination requires external interactions |

### Import Paths

```python
# All nodes imported from single location (v0.4.0+)
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
```

---

## Disallowed Imports

### 1. `typing.Any` and `Dict[str, Any]`

**Status**: BLOCKED in pure nodes

**Why Disallowed**:
- Defeats strong typing guarantees
- Hides bugs that would be caught at type-check time
- Makes refactoring dangerous - no IDE/mypy support
- Violates ONEX principle: "Types should be explicit, never vague"
- Creates implicit dependencies that break determinism

**Blocked Patterns**:
```python
# BLOCKED - typing.Any
from typing import Any
def process(self, data: Any) -> Any:  # type: ignore[arg-type]
    ...

# BLOCKED - Dict[str, Any]
from typing import Dict
metadata: Dict[str, Any] = {}

# BLOCKED - dict[str, Any] (Python 3.9+)
metadata: dict[str, Any] = {}
```

**Correct Alternatives**:
```python
# Use specific types
from typing import TypedDict
from pydantic import BaseModel

class ProcessMetadata(TypedDict):
    timestamp: str
    source: str
    version: int

# Or Pydantic models
class ModelProcessMetadata(BaseModel):
    timestamp: str
    source: str
    version: int

def process(self, data: ModelComputeInput) -> ModelComputeOutput:
    metadata: ProcessMetadata = {"timestamp": "...", "source": "...", "version": 1}
    ...
```

### 2. Legacy Mixins (Event-Driven)

**Status**: BLOCKED in pure nodes

**Why Disallowed**:
- Introduce non-deterministic event bus dependencies
- Create hidden side effects (event publishing)
- Break the pure computation model
- Make testing difficult (requires mocking event bus)

**Blocked Mixins**:
| Mixin | Reason |
|-------|--------|
| `MixinEventBus` | Publishes events - side effect |
| `MixinEventDrivenNode` | Subscribes/publishes events - hidden I/O |
| `MixinEventHandler` | Handles external events - non-deterministic |
| `MixinEventListener` | Listens for events - non-deterministic |
| `MixinServiceRegistry` | Service registry access - external I/O |

**Blocked Import Patterns**:
```python
# BLOCKED in NodeCompute/NodeReducer
from omnibase_core.mixins import MixinEventBus
from omnibase_core.mixins import MixinEventDrivenNode
from omnibase_core.mixins.mixin_event_bus import MixinEventBus
```

### 3. Event Bus Components

**Status**: BLOCKED in pure nodes

**Why Disallowed**:
- Event bus operations are inherently side-effectful
- Publishing/subscribing breaks determinism
- Creates hidden dependencies on external systems
- Violates 4-node architecture - effects belong in `NodeEffect`

**Blocked Imports**:
```python
# BLOCKED - Event bus protocols
from omnibase_core.protocols import ProtocolEventBus
from omnibase_core.protocols import ProtocolEventBusRegistry

# BLOCKED - Event models (for publishing)
from omnibase_core.models.events import ModelEventEnvelope
from omnibase_core.events import EventPublisher

# BLOCKED - Direct event operations
from omnibase_core.events import publish_event, subscribe_to_topic
```

### 4. Direct I/O Operations

**Status**: PARTIALLY BLOCKED in pure nodes

**Why Disallowed**:
- File, network, database operations are side effects
- Non-deterministic (external state can change)
- Violates ONEX 4-node architecture principle

**Note on `open()` behavior**: The linter allows `open()` in **read mode** (default mode, or explicit `'r'`). Only write modes (`'w'`, `'a'`, `'x'`, `'+'`) are blocked.

**Blocked Patterns**:
```python
# BLOCKED - File I/O (write modes)
with open("file.txt", "w") as f:  # Write mode - BLOCKED
    f.write("data")

with open("file.txt", "a") as f:  # Append mode - BLOCKED
    f.write("more data")

# ALLOWED - Read mode (for configuration, schemas, etc.)
with open("config.json", "r") as f:  # Read mode - ALLOWED
    config = json.load(f)

with open("schema.yaml") as f:  # Default read mode - ALLOWED
    schema = yaml.safe_load(f)

# BLOCKED - Network
import requests
import httpx
import aiohttp

# BLOCKED - Database
import psycopg2
import sqlalchemy
```

### 5. Non-Deterministic Operations

**Status**: ALLOWED (guidance provided for best practices)

**Note on Linter Behavior**: The purity linter **allows** `random`, `time`, and `uuid` imports because they are in the `ALLOWED_STDLIB_MODULES` allowlist. These are permitted for legitimate use cases:
- `time.perf_counter()` for performance metrics
- `random` with seeded values for deterministic pseudo-random algorithms
- `uuid` for identifier generation

**Best Practice Guidance**:
While these imports are allowed by the linter, consider injecting values for maximum testability:

```python
# ALLOWED - time module for metrics
import time
elapsed = time.perf_counter() - start_time  # Performance measurement

# ALLOWED - random with seeds is deterministic
import random
random.seed(42)  # Seeded random is deterministic
value = random.randint(0, 100)

# ALLOWED - UUID generation
from uuid import uuid4
new_id = uuid4()  # Consider using container.correlation_id for traceability
```

**Recommendation**: For maximum testability in pure nodes, consider:
- Injecting timestamps through function parameters
- Using seeded random generators
- Passing UUIDs as input rather than generating internally

---

## Allowed Imports

### Standard Library (Pure)

These standard library modules are safe for pure nodes:

```python
# Typing support (except Any)
from typing import (
    TypeVar, Generic, Protocol, TypedDict,
    Optional, Union, Literal,
    Callable, Sequence, Mapping,
    cast, overload, TYPE_CHECKING
)
from collections.abc import Callable, Sequence, Mapping, Iterator

# Data structures
from dataclasses import dataclass, field
from enum import Enum, auto, IntEnum, StrEnum
from collections import defaultdict, Counter, deque

# Functional programming (NOTE: lru_cache is FORBIDDEN - introduces state)
from functools import reduce, partial
from itertools import chain, groupby, islice
from operator import itemgetter, attrgetter

# Math and algorithms
import math
import decimal
from decimal import Decimal
import statistics
import hashlib  # For deterministic hashing

# String/data processing
import re
import json  # For parsing, not file I/O
import base64

# Abstract base classes
from abc import ABC, abstractmethod
```

### Framework Imports (ONEX)

These omnibase_core imports are allowed in pure nodes:

```python
# Models - all Pydantic models are pure
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.core import ModelTypedMapping
from omnibase_core.models.common import ModelMetadata

# Enums - pure value types
from omnibase_core.enums import EnumNodeKind, EnumNodeType
from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Errors - structured error handling
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Container - for dependency injection (read-only access)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Infrastructure base class
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

# Pure utility functions
from omnibase_core.utils.validation import validate_input
from omnibase_core.utils.hashing import compute_deterministic_hash
```

### Allowed Mixins (Pure)

These mixins maintain purity and are allowed:

| Mixin | Purpose | Why Allowed |
|-------|---------|-------------|
| `MixinFSMExecution` | FSM state machine execution | Pure state transitions |
| `MixinWorkflowExecution` | Workflow step coordination | Pure workflow logic |
| `MixinComputeExecution` | Computation execution | Pure computation patterns |
| `MixinContractMetadata` | Contract access | Read-only metadata |
| `MixinDiscoveryResponder` | Service discovery responses | Read-only discovery metadata |
| `MixinIntrospection` | Node introspection | Read-only reflection |
| `MixinHashComputation` | Deterministic hashing | Pure computation |
| `MixinNodeLifecycle` | Node lifecycle management | Lifecycle coordination |
| `MixinNodeExecutor` | Node execution patterns | Execution coordination |
| `MixinRequestResponseIntrospection` | Request/response inspection | Read-only introspection |
| `MixinSerializable` | Serialization | Pure transformation |
| `MixinWorkflowSupport` | Workflow support utilities | Pure workflow logic |
| `MixinYAMLSerialization` | YAML serialization | Pure transformation |

```python
# ALLOWED in pure nodes
from omnibase_core.mixins import MixinFSMExecution
from omnibase_core.mixins import MixinComputeExecution
from omnibase_core.mixins import MixinHashComputation
from omnibase_core.mixins import MixinSerializable
```

### Third-Party Libraries (Pure)

```python
# Pydantic - data validation
from pydantic import BaseModel, Field, field_validator

# NumPy/Pandas - numerical computation (if installed)
import numpy as np
import pandas as pd

# Other pure libraries
import orjson  # Fast JSON parsing
```

---

## Exemptions

### `@allow_dict_any` Decorator

Use sparingly for legacy code or genuinely dynamic data with documented justification:

```python
from omnibase_core.decorators import allow_dict_any

class NodeLegacyProcessor(NodeCompute):
    @allow_dict_any(
        reason="External API returns untyped JSON",
        ticket="OMN-XXX",
        migration_plan="Convert to typed model in v0.5.0"
    )
    def parse_external_response(self, response: dict[str, Any]) -> ModelParsedResponse:
        """
        Parse response from legacy external API.

        This exemption is required because:
        1. External API does not provide OpenAPI schema
        2. Response structure varies by endpoint version
        3. Typed wrapper being developed under OMN-XXX
        """
        # Implementation
        ...
```

**Requirements for `@allow_dict_any`**:
- `reason`: Clear explanation why typing is impossible
- `ticket`: Linear ticket tracking the technical debt
- `migration_plan`: How and when this will be resolved

### `# ONEX_EXCLUDE` Comment

For legacy code during migration:

```python
# ONEX_EXCLUDE: Legacy bridge code, migration tracked in OMN-XXX
from typing import Any  # noqa: ONEX001

def legacy_bridge(data: Any) -> Any:  # noqa: ONEX001
    """Bridge to legacy system - will be removed in v0.5.0."""
    ...
```

**Requirements for `# ONEX_EXCLUDE`**:
- Must include ticket reference
- Must be temporary (tracked for removal)
- Should include expected removal version/date

---

## CI Enforcement

### Pre-push Hook

The purity linter runs automatically on pre-push when node files are modified:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-node-purity
        name: ONEX Node Purity Validation
        entry: poetry run python scripts/check_node_purity.py
        language: system
        pass_filenames: false
        files: ^src/omnibase_core/nodes/
        stages: [pre-push]
```

### CI Pipeline

The linter runs in CI via GitHub Actions:

```yaml
# .github/workflows/test.yml
- name: Run purity linter
  run: poetry run python scripts/check_node_purity.py src/
```

### Error Codes

| Code | Description | Severity |
|------|-------------|----------|
| `ONEX001` | `typing.Any` usage detected | ERROR |
| `ONEX002` | `Dict[str, Any]` usage detected | ERROR |
| `ONEX003` | Blocked mixin import | ERROR |
| `ONEX004` | Event bus import in pure node | ERROR |
| `ONEX005` | Direct I/O operation detected | ERROR |
| `ONEX006` | Non-deterministic operation | WARNING |

### Example Linter Output

```
src/nodes/node_my_processor_compute.py:15:1: ONEX001 Disallowed import: 'typing.Any' in pure node
src/nodes/node_my_processor_compute.py:23:5: ONEX002 Disallowed type: 'Dict[str, Any]' - use typed alternative
src/nodes/node_my_processor_compute.py:45:1: ONEX003 Blocked mixin 'MixinEventBus' in pure node - use NodeEffect for event operations

Found 3 purity violations in 1 file.
```

---

## Migration Guide

### Step 1: Identify Violations

Run the linter to find all violations:

```bash
# Check specific file
poetry run python scripts/check_node_purity.py src/omnibase_core/nodes/node_my_compute.py

# Check all nodes
poetry run python scripts/check_node_purity.py src/omnibase_core/nodes/

# Generate report
poetry run python scripts/check_node_purity.py src/ --output report.json
```

### Step 2: Replace `Any` with Typed Alternatives

**Before** (violation):
```python
from typing import Any, Dict

class NodeDataProcessor(NodeCompute):
    def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        metadata: Dict[str, Any] = input_data.metadata
        config: Any = metadata.get("config")
        ...
```

**After** (compliant):
```python
from typing import TypedDict
from pydantic import BaseModel

class ProcessorConfig(BaseModel):
    batch_size: int
    timeout_ms: int
    enabled: bool

class ProcessorMetadata(TypedDict):
    config: ProcessorConfig
    source: str
    version: int

class NodeDataProcessor(NodeCompute):
    def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        metadata: ProcessorMetadata = input_data.metadata  # type: ignore[assignment]
        config: ProcessorConfig = ProcessorConfig(**metadata["config"])
        ...
```

### Step 3: Move Side Effects to NodeEffect

**Before** (violation in NodeCompute):
```python
class NodeDataProcessor(NodeCompute, MixinEventBus):
    def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        result = self._compute(input_data)

        # VIOLATION: Side effect in pure node
        self.publish_event("data.processed", {"result_id": result.id})

        return result
```

**After** (compliant - separate effect node):
```python
# Pure compute node
class NodeDataProcessor(NodeCompute):
    def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        return self._compute(input_data)  # Pure computation only

# Effect node for events
class NodeDataProcessorEvents(NodeEffect):
    def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        # Side effect is explicit and expected here
        self.publish_event("data.processed", input_data.operation_data)
        return ModelEffectOutput(success=True)
```

### Step 4: Replace Event Mixins with Intents

For reducers that need to trigger side effects, use the Intent pattern:

**Before** (violation):
```python
class NodeMetricsReducer(NodeReducer, MixinEventBus):
    def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        aggregated = self._aggregate(input_data.data)

        # VIOLATION: Event publishing in reducer
        self.publish_event("metrics.aggregated", aggregated)

        return ModelReducerOutput(result=aggregated)
```

**After** (compliant - Intent pattern):
```python
from omnibase_core.mixins import MixinIntentPublisher

class NodeMetricsReducer(NodeReducer, MixinIntentPublisher):
    def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        aggregated = self._aggregate(input_data.data)

        # Emit intent - actual event publishing happens externally
        intent = self.create_intent(
            intent_type="publish_metrics",
            payload={"metrics": aggregated}
        )

        return ModelReducerOutput(
            result=aggregated,
            intents=[intent]  # Intents processed by orchestrator
        )
```

### Step 5: Validate Migration

After migration, verify:

```bash
# Run linter - should pass
poetry run python scripts/check_node_purity.py src/omnibase_core/nodes/

# Run tests - should pass
poetry run pytest tests/unit/nodes/ -v

# Run type checker - should pass
poetry run mypy src/omnibase_core/nodes/
```

---

## Related Documentation

- [Node Building Guide](node-building/README.md) - How to build nodes
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Architecture overview
- [Migrating to Declarative Nodes](MIGRATING_TO_DECLARATIVE_NODES.md) - v0.4.0 migration
- [Threading Guide](THREADING.md) - Thread safety considerations
- [Mixin Subcontract Mapping](MIXIN_SUBCONTRACT_MAPPING.md) - Which mixins to use where

---

## Quick Reference

### Summary Table

| Category | Allowed in `NodeCompute`/`NodeReducer` | Allowed in `NodeEffect`/`NodeOrchestrator` |
|----------|----------------------------------------|-------------------------------------------|
| `typing.Any` | NO | YES |
| `Dict[str, Any]` | NO | YES |
| `MixinEventBus` | NO | YES |
| `MixinEventDrivenNode` | NO | YES |
| Event publishing | NO | YES |
| File I/O (write modes) | NO | YES |
| File I/O (read mode) | YES* | YES |
| Network calls | NO | YES |
| Database operations | NO | YES |
| `random`, `time`, `uuid` | YES* (inject for testability) | YES |
| Pydantic models | YES | YES |
| Typed containers | YES | YES |
| Pure mixins | YES | YES |
| `@lru_cache`, `@cache` | NO | YES |

*Allowed by linter but consider best practices for testability

### Decision Tree

```
Is your node doing pure computation or FSM state management?
  |
  +-- YES --> Use NodeCompute or NodeReducer
  |             |
  |             +-- Follow FULL import restrictions
  |             +-- Use Intent pattern for side effects
  |
  +-- NO --> Does it do external I/O or workflow coordination?
              |
              +-- YES --> Use NodeEffect or NodeOrchestrator
                            |
                            +-- No import restrictions
                            +-- Side effects allowed
```

---

**Maintainer**: ONEX Framework Team
**Correlation ID**: `omn-203-import-rules-doc`
