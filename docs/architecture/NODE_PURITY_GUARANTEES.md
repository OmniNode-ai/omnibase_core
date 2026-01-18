> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Node Purity Guarantees
>
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Node Purity Guarantees

> **Version**: 1.0.0
> **Ticket**: OMN-156
> **Status**: Enforced via AST checks in CI

## Overview

ONEX enforces **purity guarantees** for declarative nodes (COMPUTE and REDUCER) to maintain architectural integrity. Pure nodes must not contain I/O operations, network calls, or other side effects.

This document describes what purity means in the ONEX context, what patterns are forbidden, and how purity is enforced.

## Purity Definition

A **pure node** is one that:
1. Has no observable side effects (no I/O, no state modification outside its container)
2. Is deterministic (same input always produces same output)
3. Relies solely on its input data and container-provided services

### Pure Node Types
- **COMPUTE nodes**: Pure transformations only (input -> transform -> output)
- **REDUCER nodes**: Pure state management via FSM (state transitions, no direct I/O)

### Impure Node Types (Side Effects Allowed)
- **EFFECT nodes**: Explicitly designed for side effects (file I/O, API calls, database operations)
- **ORCHESTRATOR nodes**: Workflow coordination (can emit actions that Effect nodes execute)

## Forbidden Patterns

The following patterns are **FORBIDDEN** in COMPUTE and REDUCER nodes:

### 1. Networking Libraries

```python
# FORBIDDEN - Direct network access
import requests
import httpx
import aiohttp
import urllib
import socket
from http.client import HTTPConnection
import boto3  # AWS SDK
import redis
import kafka
```

**Why**: Network calls are side effects that can fail, timeout, or return different results.

**Alternative**: Use EFFECT nodes for network operations, or inject network clients via container.

### 2. Filesystem Operations

```python
# FORBIDDEN - File writes
with open("file.txt", "w") as f:
    f.write("data")

Path("file.txt").write_text("data")
Path("dir").mkdir()
os.remove("file.txt")
shutil.copy(src, dst)
```

**Why**: Filesystem operations are side effects that modify external state.

**Alternative**: Use EFFECT nodes for file operations. Reading files for configuration may be acceptable during initialization but not in `process()`.

### 3. Subprocess Calls

```python
# FORBIDDEN - External process execution
import subprocess
subprocess.run(["ls", "-la"])
os.system("echo hello")
os.popen("command")
```

**Why**: Subprocess calls are side effects with unpredictable behavior.

**Alternative**: Use EFFECT nodes for subprocess operations.

### 4. Threading/Multiprocessing

```python
# FORBIDDEN in subclasses
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor  # Allowed only in base class
```

**Why**: Threading introduces non-determinism and race conditions.

**Exception**: `NodeCompute` base class is allowed to use `ThreadPoolExecutor` for internal parallel processing.

### 5. Module-Level Logging Import

```python
# FORBIDDEN
import logging
logger = logging.getLogger(__name__)
```

**Why**: Module-level logging bypasses the container's structured logging.

**Alternative**: Use structured logging via container:
```python
from omnibase_core.logging.logging_structured import emit_log_event_sync as emit_log_event
emit_log_event(LogLevel.INFO, "message", {"context": "data"})
```

### 6. Class-Level Mutable Data

```python
# FORBIDDEN - Mutable class attributes
class NodeMyCompute(NodeCoreBase):
    cache = {}  # Mutable!
    items = []  # Mutable!
    seen = set()  # Mutable!
```

**Why**: Class-level mutable data is shared across instances, violating isolation.

**Alternative**: Use instance attributes in `__init__` or container-provided caching.

### 7. Caching Decorators

```python
# FORBIDDEN
from functools import lru_cache, cache, cached_property

class NodeMyCompute(NodeCoreBase):
    @lru_cache  # State leakage!
    def compute(self, x):
        return x * 2
```

**Why**: Caching decorators introduce hidden mutable state.

**Alternative**: Use `ModelComputeCache` from container:
```python
self.computation_cache = container.compute_cache_config
```

## Allowed Patterns

### Standard Library (Pure Modules)
- `typing`, `typing_extensions`, `types`
- `abc`, `dataclasses`, `enum`
- `collections`, `collections.abc`
- `functools` (but NOT caching decorators)
- `itertools`, `operator`, `copy`
- `re`, `string`, `textwrap`
- `math`, `decimal`, `statistics`
- `json`, `base64`, `struct`
- `datetime`, `time` (for `perf_counter`)
- `hashlib`, `hmac`, `secrets`
- `uuid`, `pathlib` (reading only)
- `asyncio` (async/await control flow)

### Framework Modules
- `omnibase_core.*` - All core framework modules
- `omnibase_spi.*` - All SPI modules
- `pydantic`, `pydantic_settings` - Model validation

### Container Services
Nodes should access external capabilities through the container:
```python
# CORRECT - Use container services
class NodeMyCompute(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
        self.cache = container.compute_cache_config
```

## Valid Inheritance

Nodes must inherit from approved base classes only:

```python
# ALLOWED base classes
NodeCoreBase
Generic[T]
ABC

# ALLOWED mixins (must start with "Mixin")
MixinFSMExecution
MixinWorkflowExecution
MixinDiscoveryResponder
MixinEventHandler
MixinEventListener
MixinNodeExecutor
MixinNodeLifecycle
MixinRequestResponseIntrospection
MixinWorkflowSupport
MixinContractMetadata
```

## Enforcement

### AST-Based Purity Checker

Purity is enforced by `scripts/check_node_purity.py`:

```bash
# Run purity checks
poetry run python scripts/check_node_purity.py

# Verbose output
poetry run python scripts/check_node_purity.py --verbose

# Strict mode (warnings as errors)
poetry run python scripts/check_node_purity.py --strict

# JSON output for CI
poetry run python scripts/check_node_purity.py --json

# Check specific file
poetry run python scripts/check_node_purity.py --file src/omnibase_core/nodes/node_compute.py
```

### Exit Codes
- `0` - All pure nodes pass purity checks
- `1` - Purity violations detected (blocks PR)
- `2` - Script error (invalid arguments, file not found)

### CI Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Check Node Purity
  run: poetry run python scripts/check_node_purity.py
```

### Test Suite

Comprehensive tests in `tests/unit/nodes/test_node_purity.py`:

```bash
poetry run pytest tests/unit/nodes/test_node_purity.py -v
```

## Violation Types

| Type | Severity | Description |
|------|----------|-------------|
| `networking_import` | ERROR | Import of networking library |
| `filesystem_operation` | ERROR | Direct filesystem operation |
| `subprocess_import` | ERROR | Import of subprocess module |
| `threading_import` | ERROR | Import of threading module |
| `logging_import` | ERROR | Module-level logging import |
| `class_mutable_data` | ERROR | Class-level mutable attribute |
| `caching_decorator` | ERROR | Use of caching decorator |
| `forbidden_import` | WARNING | Potentially unsafe import |
| `invalid_inheritance` | ERROR | Invalid base class |
| `open_call` | ERROR | open() with write mode |
| `pathlib_write` | ERROR | Path.write_*() method |

## Migration Guide

If your node has purity violations:

1. **Move I/O to Effect nodes**: Create dedicated Effect nodes for file, network, and database operations
2. **Use container services**: Replace direct library usage with container-provided services
3. **Remove class-level state**: Move mutable data to instance attributes
4. **Replace caching decorators**: Use `ModelComputeCache` from container
5. **Use structured logging**: Replace `import logging` with `emit_log_event`

## Examples

### Before (Impure)

```python
import requests
import logging

class NodeDataCompute(NodeCoreBase):
    cache = {}  # Mutable class attribute

    @lru_cache
    def fetch_and_process(self, url):
        response = requests.get(url)  # Network I/O!
        logging.info(f"Fetched {url}")  # Module logging!
        return response.json()
```

### After (Pure)

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.logging_structured import emit_log_event_sync as emit_log_event

class NodeDataCompute(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.cache = container.compute_cache_config  # Container-provided

    async def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        # Pure transformation - no I/O in this node
        # Network fetching would be done by an Effect node before this
        data = input_data.data  # Already fetched by Effect node
        result = self._transform(data)

        emit_log_event(
            LogLevel.INFO,
            "Data processed",
            {"node_id": str(self.node_id)}
        )

        return ModelComputeOutput(result=result, ...)
```

## Related Documentation

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md)
- [Node Building Guide](../guides/node-building/README.md)
- [Container Types](CONTAINER_TYPES.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

**Last Updated**: 2025-12-09
**Author**: ONEX Framework Team
