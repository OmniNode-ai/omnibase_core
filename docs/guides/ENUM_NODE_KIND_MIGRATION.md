# EnumNodeKind Migration Guide

> **Version**: 0.4.0
> **Last Updated**: 2025-12-13
> **Related**: [CLAUDE.md](../../CLAUDE.md), [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

---

## Overview

This guide explains the introduction of `EnumNodeKind` and how to migrate existing code that uses `EnumNodeType` for architectural classification.

---

## Why the Change?

### The Problem: Naming Collision

Before v0.2.0, `EnumNodeType` served two purposes:
1. **Architectural classification** - What role does this node play? (COMPUTE, EFFECT, etc.)
2. **Implementation type** - What specific kind of node is this? (TRANSFORMER, AGGREGATOR, etc.)

This caused confusion:
- Developers weren't sure which values to use for routing vs. discovery
- Values like `COMPUTE` could mean either "any compute role" or "a specific compute implementation"
- Adding new implementation types created ambiguity with architectural roles

### The Solution: Clear Separation

v0.2.0 introduces `EnumNodeKind` for architectural classification:

| Enum | Purpose | Example Values |
|------|---------|----------------|
| **EnumNodeKind** | Architectural role | `COMPUTE`, `EFFECT`, `REDUCER`, `ORCHESTRATOR`, `RUNTIME_HOST` |
| **EnumNodeType** | Implementation type | `COMPUTE_GENERIC`, `TRANSFORMER`, `AGGREGATOR`, `GATEWAY`, etc. |

---

## Before/After Code Examples

### Example 1: Routing Based on Node Role

**Before** (ambiguous):
```python
from omnibase_core.enums import EnumNodeType

# What does COMPUTE mean here? Role or specific type?
if node_type == EnumNodeType.COMPUTE:
    route_to_compute_pipeline(node)
```

**After** (clear):
```python
from omnibase_core.enums import EnumNodeKind

# Clearly indicates architectural role
if node_kind == EnumNodeKind.COMPUTE:
    route_to_compute_pipeline(node)
```

### Example 2: Getting Architectural Role from Implementation Type

**Before** (not possible):
```python
# No way to get architectural role from TRANSFORMER
node_type = EnumNodeType.TRANSFORMER
# What role is this? Manual mapping required
```

**After** (built-in mapping):
```python
from omnibase_core.enums import EnumNodeType, EnumNodeKind

node_type = EnumNodeType.TRANSFORMER
node_kind = EnumNodeType.get_node_kind(node_type)  # Returns EnumNodeKind.COMPUTE
```

### Example 3: Node Discovery with Implementation Type

**Before** (unchanged):
```python
from omnibase_core.enums import EnumNodeType

# Finding specific implementation types
if node_type == EnumNodeType.TRANSFORMER:
    apply_transformer_capabilities(node)
```

**After** (unchanged - still valid):
```python
from omnibase_core.enums import EnumNodeType

# EnumNodeType still used for specific implementations
if node_type == EnumNodeType.TRANSFORMER:
    apply_transformer_capabilities(node)
```

### Example 4: YAML Contract Migration

**Before** (legacy - triggers deprecation warning):
```yaml
# contracts/my_node.yaml
contract_version: "1.0.0"
node_type: compute  # Legacy lowercase value
```

**After** (recommended):
```yaml
# contracts/my_node.yaml
contract_version: "1.0.0"
node_type: COMPUTE_GENERIC  # Explicit implementation type
```

---

## Migration Checklist

### For External Projects Consuming omnibase_core

- [ ] **Update imports**: Add `EnumNodeKind` where needed
  ```python
  from omnibase_core.enums import EnumNodeKind, EnumNodeType
  ```

- [ ] **Review routing logic**: Replace `EnumNodeType` with `EnumNodeKind` for architectural routing
  ```python
  # Before: if node_type == EnumNodeType.COMPUTE
  # After:  if node_kind == EnumNodeKind.COMPUTE
  ```

- [ ] **Update YAML contracts**: Replace legacy lowercase values
  ```yaml
  # Before: node_type: compute
  # After:  node_type: COMPUTE_GENERIC
  ```

- [ ] **Add kind resolution**: Use `get_node_kind()` when you have a type and need the kind
  ```python
  kind = EnumNodeType.get_node_kind(node_type)
  ```

- [ ] **Review helper methods**: Use `EnumNodeKind.is_core_node_type()` for architectural checks
  ```python
  if EnumNodeKind.is_core_node_type(node_kind):
      # This is a core 4-node architecture type
      pass
  ```

- [ ] **Run tests**: Ensure all tests pass with updated code
  ```bash
  poetry run pytest tests/ -x
  ```

- [ ] **Check deprecation warnings**: Run with `-W default` to see deprecation warnings
  ```bash
  poetry run pytest tests/ -W default 2>&1 | grep -i deprecat
  ```

---

## Key Mappings

### EnumNodeType → EnumNodeKind

| EnumNodeType | EnumNodeKind |
|--------------|--------------|
| `COMPUTE_GENERIC` | `COMPUTE` |
| `TRANSFORMER` | `COMPUTE` |
| `AGGREGATOR` | `COMPUTE` |
| `FUNCTION` | `COMPUTE` |
| `MODEL` | `COMPUTE` |
| `EFFECT_GENERIC` | `EFFECT` |
| `TOOL` | `EFFECT` |
| `AGENT` | `EFFECT` |
| `REDUCER_GENERIC` | `REDUCER` |
| `ORCHESTRATOR_GENERIC` | `ORCHESTRATOR` |
| `GATEWAY` | `ORCHESTRATOR` |
| `VALIDATOR` | `ORCHESTRATOR` |
| `WORKFLOW` | `ORCHESTRATOR` |
| `RUNTIME_HOST_GENERIC` | `RUNTIME_HOST` |

### Legacy Value Mappings (Deprecated)

These lowercase values trigger deprecation warnings:

| Legacy Value | Maps To |
|--------------|---------|
| `"compute"` | `COMPUTE_GENERIC` |
| `"effect"` | `EFFECT_GENERIC` |
| `"reducer"` | `REDUCER_GENERIC` |
| `"orchestrator"` | `ORCHESTRATOR_GENERIC` |

---

## Common Pitfalls

### ❌ Don't Use EnumNodeKind for Discovery

```python
# WRONG - EnumNodeKind is for architectural role, not discovery
node_registry.find_by_kind(EnumNodeKind.COMPUTE)

# RIGHT - Use EnumNodeType for specific implementations
node_registry.find_by_type(EnumNodeType.TRANSFORMER)
```

### ❌ Don't Confuse Value Casing

```python
# EnumNodeKind uses lowercase values
EnumNodeKind.COMPUTE.value  # "compute"

# EnumNodeType uses uppercase values
EnumNodeType.COMPUTE_GENERIC.value  # "COMPUTE_GENERIC"
```

### ✅ Do Use get_node_kind() for Mapping

```python
# Get architectural role from implementation type
from omnibase_core.enums import EnumNodeType

node_type = EnumNodeType.TRANSFORMER
node_kind = EnumNodeType.get_node_kind(node_type)
print(node_kind)  # EnumNodeKind.COMPUTE
```

---

## API Reference

### EnumNodeKind

```python
class EnumNodeKind(str, Enum):
    EFFECT = "effect"           # External interactions (I/O)
    COMPUTE = "compute"         # Data processing
    REDUCER = "reducer"         # State management
    ORCHESTRATOR = "orchestrator"  # Workflow coordination
    RUNTIME_HOST = "runtime_host"  # Runtime infrastructure

    @classmethod
    def is_core_node_type(cls, node_kind: EnumNodeKind) -> bool:
        """Check if it's a core 4-node architecture type."""

    @classmethod
    def is_infrastructure_type(cls, node_kind: EnumNodeKind) -> bool:
        """Check if it's an infrastructure type (RUNTIME_HOST)."""
```

### EnumNodeType.get_node_kind()

```python
@classmethod
def get_node_kind(cls, node_type: EnumNodeType) -> EnumNodeKind:
    """Get the architectural kind for this node type."""
```

---

## Related Handler Enums (v0.4.0+)

The handler system uses a parallel classification that aligns with `EnumNodeKind`:

| Handler Enum | Purpose | Relationship to EnumNodeKind |
|--------------|---------|------------------------------|
| `EnumHandlerTypeCategory` | Behavioral classification | COMPUTE/EFFECT categories align with EnumNodeKind.COMPUTE/EFFECT |
| `EnumHandlerCapability` | Handler feature flags | Cross-cutting capabilities for all node kinds |
| `EnumHandlerCommandType` | Typed command dispatch | ROLLBACK only applies to EFFECT handlers |

**See**: [Enums API Reference](../reference/api/enums.md#handler-enums)

---

## Support

- **Questions**: See [CLAUDE.md](../../CLAUDE.md) for quick reference
- **Architecture**: See [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Node Building**: See [Node Building Guide](node-building/README.md)
- **Enums Reference**: See [Enums API Reference](../reference/api/enums.md)

---

**Last Updated**: 2025-12-13
**Version**: 0.4.0
