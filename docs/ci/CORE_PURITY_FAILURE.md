# Node Purity Check Failure Guide

**Status**: Active
**Related**: OMN-203 (Declarative Node Purity Linter)
**CI Job**: `node-purity-check`

## Overview

The Node Purity Check validates that declarative nodes (COMPUTE, REDUCER) maintain **purity guarantees** - meaning they contain no I/O operations, network calls, or other side effects.

This check protects the ONEX architecture by preventing contributors from adding "convenience shortcuts" that would violate the architectural invariants.

## Which Nodes Are Checked?

| Node Type | Checked? | Rationale |
|-----------|----------|-----------|
| **COMPUTE** | Yes | Pure transformations only |
| **REDUCER** | Yes | Pure state management via FSM |
| **EFFECT** | No | Explicitly allowed to have side effects |
| **ORCHESTRATOR** | No | Coordination logic only |

## Common Violations and Fixes

### 1. Networking Import (`networking_import`)

**Error**: Importing networking libraries is forbidden in pure nodes.

```python
# WRONG
from omnibase_core.nodes import NodeCompute
import requests  # FORBIDDEN

class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        response = requests.get("https://api.example.com")  # SIDE EFFECT
```

**Fix**: Move network operations to EFFECT nodes.

```python
# CORRECT - Use Effect node for network calls
from omnibase_core.nodes import NodeEffect

class NodeApiClientEffect(NodeEffect):
    async def execute(self, input_data):
        # Network calls are allowed in EFFECT nodes
        response = await self.http_client.get("https://api.example.com")
```

**Forbidden modules**: `requests`, `httpx`, `aiohttp`, `urllib`, `socket`, `http.client`, `redis`, `kafka`, `boto3`, `sqlalchemy`, etc.

---

### 2. Filesystem Operation (`filesystem_operation`, `open_call`, `pathlib_write`)

**Error**: Writing to filesystem is forbidden in pure nodes.

```python
# WRONG
class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        with open("output.json", "w") as f:  # FORBIDDEN (write mode)
            f.write(json.dumps(result))
```

**Fix**: Move file writes to EFFECT nodes or use container services.

```python
# CORRECT - Pure computation only
class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        # Transform data (pure)
        return {"result": input_data.value * 2}

# File writing happens in Effect node or orchestrator
```

**Note**: Read-only `open()` is allowed but discouraged. Prefer injecting configuration via input parameters.

---

### 3. Subprocess Import (`subprocess_import`)

**Error**: Subprocess execution is forbidden in pure nodes.

```python
# WRONG
import subprocess

class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        result = subprocess.run(["ls", "-la"])  # FORBIDDEN
```

**Fix**: Move subprocess operations to EFFECT nodes.

---

### 4. Threading Import (`threading_import`)

**Error**: Threading/multiprocessing imports are forbidden in pure nodes.

```python
# WRONG
import threading

class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        thread = threading.Thread(target=self.work)  # FORBIDDEN
```

**Fix**: Pure nodes should not manage threads directly. Use container-provided concurrency services or ORCHESTRATOR nodes for parallel execution.

---

### 5. Module-Level Logging (`logging_import`)

**Error**: Module-level `import logging` is forbidden.

```python
# WRONG
import logging

logger = logging.getLogger(__name__)

class NodeMyCompute(NodeCompute):
    def compute(self, input_data):
        logger.info("Processing")  # Uses module-level logger
```

**Fix**: Use structured logging via the container.

```python
# CORRECT
from omnibase_core.nodes import NodeCompute

class NodeMyCompute(NodeCompute):
    def __init__(self, container):
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")

    def compute(self, input_data):
        self.logger.info("Processing")  # Container-provided logger
```

---

### 6. Class-Level Mutable Data (`class_mutable_data`)

**Error**: Mutable class attributes introduce shared state.

```python
# WRONG
class NodeMyCompute(NodeCompute):
    cache = {}  # FORBIDDEN - mutable class attribute
    results = []  # FORBIDDEN

    def compute(self, input_data):
        self.cache[input_data.key] = result  # Shared state!
```

**Fix**: Use instance attributes or immutable structures.

```python
# CORRECT
class NodeMyCompute(NodeCompute):
    CONSTANTS = frozenset({"a", "b", "c"})  # OK - immutable

    def __init__(self, container):
        super().__init__(container)
        self._cache = {}  # Instance attribute - per-instance state
```

---

### 7. Caching Decorator (`caching_decorator`)

**Error**: Caching decorators like `@lru_cache` introduce mutable state.

```python
# WRONG
from functools import lru_cache

class NodeMyCompute(NodeCompute):
    @lru_cache(maxsize=100)  # FORBIDDEN
    def expensive_calculation(self, value):
        return value ** 2
```

**Fix**: Use `ModelComputeCache` from the container.

```python
# CORRECT
class NodeMyCompute(NodeCompute):
    def __init__(self, container):
        super().__init__(container)
        self.cache = container.get_service("ModelComputeCache")

    def expensive_calculation(self, value):
        cached = self.cache.get(value)
        if cached:
            return cached
        result = value ** 2
        self.cache.set(value, result)
        return result
```

---

### 8. Any Type Hint (`any_import`, `any_type_hint`, `dict_any_type_hint`)

**Error**: `Any` and `Dict[str, Any]` type hints are forbidden in declarative nodes.

```python
# WRONG
from typing import Any, Dict

class NodeMyCompute(NodeCompute):
    def compute(self, data: Dict[str, Any]) -> Any:  # FORBIDDEN
        return data
```

**Fix**: Use specific types, TypedDict, or Pydantic models.

```python
# CORRECT
from typing import TypedDict
from pydantic import BaseModel

class InputData(TypedDict):
    name: str
    value: int

class OutputModel(BaseModel):
    result: int

class NodeMyCompute(NodeCompute):
    def compute(self, data: InputData) -> OutputModel:
        return OutputModel(result=data["value"] * 2)
```

---

### 9. Legacy Mixin Import (`legacy_mixin_import`)

**Error**: Legacy event-driven mixins are forbidden in declarative nodes.

```python
# WRONG
from omnibase_core.mixins import MixinEventBus

class NodeMyCompute(NodeCompute, MixinEventBus):  # FORBIDDEN
    pass
```

**Fix**: Use EFFECT nodes for event-driven functionality or emit intents.

**Forbidden mixins**: `MixinEventBus`, `MixinEventDrivenNode`, `MixinEventHandler`, `MixinEventListener`, `MixinServiceRegistry`

---

### 10. Event Bus Import (`event_bus_import`)

**Error**: Event bus components are forbidden in declarative nodes.

```python
# WRONG
from omnibase_core.events import ProtocolEventBus

class NodeMyCompute(NodeCompute):
    def __init__(self, container):
        super().__init__(container)
        self.event_bus = container.get_service(ProtocolEventBus)  # FORBIDDEN
```

**Fix**: Use EFFECT nodes for event bus operations or emit intents instead.

---

## Exemption Mechanisms

### 1. ONEX_EXCLUDE Comment

For legitimate cases where `Any` is required (e.g., external API contracts):

```python
# ONEX_EXCLUDE: external_api_response requires Any due to dynamic schema
def process_external_response(self, response: Any) -> ProcessedData:
    pass
```

### 2. @allow_dict_any Decorator

For functions or classes that legitimately need `Dict[str, Any]`:

```python
from omnibase_core.decorators import allow_dict_any

@allow_dict_any
def legacy_adapter(self, data: Dict[str, Any]) -> Result:
    # Adapting legacy API that returns untyped dict
    pass
```

### 3. Base Node File Exemptions

The base node files (`node_compute.py`, `node_reducer.py`) are automatically exempt because they use `Any` for generic type parameters. User subclasses must use concrete types.

---

## Running the Check Locally

```bash
# Check all node files
poetry run python scripts/check_node_purity.py

# Verbose output with code snippets
poetry run python scripts/check_node_purity.py --verbose

# Check specific file
poetry run python scripts/check_node_purity.py --file src/omnibase_core/nodes/node_compute.py

# Strict mode (warnings become errors)
poetry run python scripts/check_node_purity.py --strict

# JSON output (for tooling)
poetry run python scripts/check_node_purity.py --json
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All nodes pass purity checks |
| 1 | Purity violations detected |
| 2 | Script error (invalid arguments, file not found) |

## CI Configuration

The purity check runs as part of CI in `.github/workflows/test.yml`:

```yaml
node-purity-check:
  name: Node Purity Check
  runs-on: ubuntu-latest
  steps:
    - name: Run Node Purity Check
      run: poetry run python scripts/check_node_purity.py --verbose
      continue-on-error: true  # Non-blocking until tech debt resolved
```

**Note**: Currently non-blocking (`continue-on-error: true`) due to existing tech debt in base node files. Once resolved, this will become a blocking check.

## Allowed Patterns

The purity check allows:

- **Standard library pure modules**: `typing`, `dataclasses`, `enum`, `abc`, `collections`, `itertools`, `functools` (except caching), `json`, `datetime`, `hashlib`, `uuid`
- **Framework imports**: `omnibase_core.*`, `omnibase_spi.*`, `pydantic`
- **Time measurement**: `time.perf_counter` for metrics
- **Path parsing**: `pathlib` (reading only, no writes)
- **Container-based DI**: Getting services via `container.get_service()`

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Node Building Guide](../guides/node-building/README.md)
- [Node Class Hierarchy](../architecture/NODE_CLASS_HIERARCHY.md)

---

**Last Updated**: 2025-12-13
