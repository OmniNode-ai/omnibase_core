# Terminology Guide

**Purpose**: Standard terminology reference for omnibase_core documentation
**Audience**: Contributors, technical writers, AI agents
**Last Updated**: 2025-11-18

---

## Quick Reference

| Concept | ✅ Use This | ❌ Not This | Context |
|---------|-------------|-------------|---------|
| **Node Types (Code)** | `EFFECT`, `COMPUTE`, `REDUCER`, `ORCHESTRATOR` | EffectNode, ComputeNode | Class names, constants |
| **Node Types (Prose)** | "effect node", "compute node" | "Effect Node", "EFFECT" | Descriptive text |
| **DI Container** | `ModelONEXContainer` | ModelContainer, Container | Node constructors |
| **Value Wrapper** | `ModelContainer[T]` | ModelONEXContainer | Data wrapping |
| **Protocol Reference** | "protocol interface" | "service interface" | Architecture docs |
| **Protocol Parameter** | "protocol name" | "protocol interface" | API/method docs |
| **ONEX Version** | "ONEX v2.0" (first), "v2.0" (later) | "v2.0" alone, "2.0" | Version references |
| **Current Pattern** | "Pure FSM pattern (ONEX v2.0+)" | "new pattern", "latest" | Pattern references |
| **Deprecated Pattern** | "Legacy pattern (pre-v2.0)" | "old pattern" | Deprecated features |
| **Action** | `ModelAction`, "action" | "thunk" (except migration) | Orchestrator commands |
| **Intent** | `ModelIntent`, "intent" | N/A | Reducer side effects |
| **FSM** | "Pure FSM pattern", "FSM" | "state machine" alone | Reducer patterns |

---

## Detailed Guidelines

### 1. Node Type Terminology

#### In Code Contexts
```
# ✅ Correct - ALL CAPS in class names
class NodeFileBackupEffect(NodeCoreBase):
    """EFFECT node for file backup operations."""

# ✅ Correct - ALL CAPS in constants
NODE_TYPE_EFFECT = "EFFECT"
NODE_TYPE_COMPUTE = "COMPUTE"
NODE_TYPE_REDUCER = "REDUCER"
NODE_TYPE_ORCHESTRATOR = "ORCHESTRATOR"
```

#### In Documentation Prose
```markdown
✅ The effect node handles external I/O operations.
✅ Use a compute node for pure transformations.
✅ The REDUCER node maintains state through FSM transitions.

❌ The Effect Node handles I/O.  (Don't capitalize)
❌ Use a COMPUTE for transformations.  (Missing "node")
```

#### In Headers and Titles
```markdown
✅ # EFFECT Node Tutorial
✅ ## Building Your First COMPUTE Node
✅ ### REDUCER Node Patterns

✅ # Effect Node Tutorial  (Title case acceptable)
❌ # Effect node tutorial  (inconsistent capitalization)
```

---

### 2. Container Terminology

#### CRITICAL Distinction

**Two different types - NOT interchangeable!**

##### ModelONEXContainer - Dependency Injection
```
# ✅ ALWAYS use in node constructors
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
```

**Documentation Terms**:
- ✅ "dependency injection container"
- ✅ "DI container"
- ✅ "service container"
- ❌ "container" (too ambiguous)

##### ModelContainer[T] - Value Wrapper
```
# ✅ Use for wrapping values with metadata
from omnibase_core.models.core.model_container import ModelContainer

config = ModelContainer.create(
    value="production",
    container_type="environment"
)
```

**Documentation Terms**:
- ✅ "value wrapper"
- ✅ "generic value container"
- ✅ "metadata wrapper"
- ❌ "DI container" (wrong type!)

**See**: `docs/architecture/CONTAINER_TYPES.md` for complete guide.

---

### 3. Protocol Terminology

#### In Architecture Documentation
```markdown
✅ The protocol interface defines the contract.
✅ Services are resolved by protocol interface.
✅ Use protocol-based dependency injection.

❌ The service interface defines the contract.  (ambiguous)
```

#### In API/Method Documentation
```
# ✅ Method parameter documentation
def get_service(self, protocol_name: str) -> Any:
    """
    Resolve service by protocol name.

    Args:
        protocol_name: Name of the protocol interface (e.g., "ProtocolLogger")
    """
```

#### In Code Examples
```
# ✅ Use string literal for protocol names
logger = container.get_service("ProtocolLogger")
event_bus = container.get_service("ProtocolEventBus")

# ✅ Comment style
# Get service by protocol interface
# Resolve protocol by name
```

---

### 4. Version References

#### ONEX Framework Versions

**First Mention in Document**:
```markdown
✅ ONEX v2.0 introduces the Pure FSM pattern.
❌ v2.0 introduces the Pure FSM pattern.  (missing framework name)
```

**Subsequent Mentions** (same context):
```markdown
✅ The v2.0 pattern eliminates side effects...
✅ In v2.0, all Reducers must emit Intents...
```

**Version Ranges**:
```markdown
✅ ONEX v2.0+ implementations should use...
✅ Legacy pattern (pre-v2.0) for backward compatibility
✅ Introduced in ONEX v0.1.0, enhanced in v2.0
```

#### Temporal Language - AVOID

**Instead of temporal terms, use version markers:**

❌ **Don't Use**:
```markdown
❌ New implementations should use...
❌ The old pattern is deprecated...
❌ Modern ONEX uses...
❌ The latest version introduces...
```

✅ **Use Version-Specific Terms**:
```markdown
✅ ONEX v2.0+ implementations should use...
✅ The legacy pattern (pre-v2.0) is deprecated...
✅ ONEX v2.0 uses the Pure FSM pattern...
✅ ONEX v2.0 introduces Intent emission...
```

**Why?** Temporal language becomes outdated. "New" in 2025 is "old" in 2027.

---

### 5. Pattern Terminology

#### Intent Pattern
```markdown
✅ The ModelIntent class represents declarative side effects.
✅ Reducers emit intents describing what should happen.
✅ Use the Intent emission pattern for pure Reducers.

❌ Intents are thunks for side effects.  (thunk is legacy Action term)
```

#### Action Pattern
```markdown
✅ The ModelAction class represents Orchestrator-issued commands.
✅ Actions include lease_id for single-writer semantics.
✅ Use the Action emission pattern for workflow coordination.

❌ Actions are like thunks with ownership.  (avoid thunk except in migration)
```

#### FSM Pattern
```markdown
✅ The Pure FSM pattern eliminates side effects in Reducers.
✅ Use FSM (Finite State Machine) for state transitions.
✅ Pure FSM Reducers emit Intents, not direct I/O.

✅ FSM / finite state machine / state machine  (all acceptable)
❌ State machine pattern  (missing "FSM" or "Pure")
```

---

### 6. Legacy Terminology

#### When to Reference Legacy Terms

**Acceptable Contexts**:
1. **Migration Guides**: "Upgrading from thunk to Action..."
2. **Changelog**: Historical record of changes
3. **Anti-Pattern Examples**: "Don't use generic thunks"
4. **Comparison Tables**: "Action vs Thunk"

**Add Historical Notes**:
```markdown
## Action vs Thunk

> **Historical Note**: "Thunk" was the legacy term for what is now called "Action" (changed in ONEX v0.1.0). This comparison is retained for migration context.
```

#### Legacy Patterns
```markdown
✅ Legacy pattern (pre-v2.0): Stateful Reducers with direct I/O
✅ Traditional pattern (pre-v2.0, still supported): Aggregation in Reducers
✅ Deprecated: Direct side effects in Reducers (use Intent emission)

❌ Old pattern: Stateful Reducers  (use "Legacy pattern (pre-v2.0)")
❌ Outdated approach  (use version-specific reference)
```

---

### 7. Workflow Terminology

**Semantic Distinctions**:

| Term | Meaning | Usage |
|------|---------|-------|
| **Workflow** | Multi-step process definition | "Define workflow steps" |
| **Orchestration** | Coordination of execution | "Orchestrate node execution" |
| **Workflow Orchestration** | Combined concept | "Workflow orchestration system" |

**Examples**:
```markdown
✅ The workflow defines validation → processing → storage steps.
✅ The Orchestrator coordinates workflow execution.
✅ Workflow orchestration uses ModelAction for coordination.

❌ The orchestration defines steps.  (wrong - orchestration coordinates, not defines)
```

---

## Common Mistakes

### ❌ Wrong: Generic "Container"
```
❌ def __init__(self, container: Container):  # Too ambiguous
✅ def __init__(self, container: ModelONEXContainer):
```

### ❌ Wrong: Confusing Container Types
```
❌ from omnibase_core.models.core.model_container import ModelContainer
   def __init__(self, container: ModelContainer):  # WRONG TYPE!

✅ from omnibase_core.models.container.model_onex_container import ModelONEXContainer
   def __init__(self, container: ModelONEXContainer):
```

### ❌ Wrong: Temporal Language
```markdown
❌ New pattern: Pure FSM Reducers
✅ Pure FSM pattern (ONEX v2.0+)

❌ Old implementations used stateful Reducers
✅ Legacy implementations (pre-v2.0) used stateful Reducers
```

### ❌ Wrong: Mixed Node Capitalization
```markdown
❌ The Effect node processes I/O
✅ The effect node processes I/O

❌ Use the COMPUTE for calculations
✅ Use the COMPUTE node for calculations
✅ Use a compute node for calculations
```

---

## Style Guide Integration

### For Technical Writers

**Before Writing**:
1. Check this guide for preferred terminology
2. Search existing docs for usage patterns
3. Use version-specific references, not temporal language

**Terminology Checklist**:
- [ ] Node types capitalized correctly (code vs prose)
- [ ] Container types used correctly (DI vs value wrapper)
- [ ] Version references include "ONEX" prefix
- [ ] No temporal language ("new", "old", "latest")
- [ ] Protocol terminology consistent (interface vs name)

### For Code Contributors

**In Docstrings**:
```
def process_data(self, container: ModelONEXContainer) -> ModelIntent:
    """
    Process data using Pure FSM pattern (ONEX v2.0+).

    Args:
        container: Dependency injection container

    Returns:
        Intent describing side effects to execute
    """
```

**In Comments**:
```
# ✅ Resolve service by protocol interface
logger = container.get_service("ProtocolLogger")

# ✅ EFFECT node handles external I/O
class NodeDatabaseWriterEffect(NodeCoreBase):
    pass
```

### For AI Agents

**Pattern Recognition**:
- Recognize both `ModelONEXContainer` and `ModelContainer[T]` as distinct types
- Use version-specific language in generated documentation
- Follow node type capitalization rules consistently
- Reference this guide when uncertain

**Template Usage**:
```markdown
When creating EFFECT nodes:
- Use `EFFECT` in class names
- Use "effect node" in descriptions
- Include `container: ModelONEXContainer` parameter
- Emit Intents for side effects (ONEX v2.0+)
```

---

## Validation Tools

### Manual Checks

**Grep Commands**:
```
# Find temporal language in docs (should review all matches)
grep -rn "new pattern\|old pattern\|latest version" docs/

# Find ambiguous container references
grep -rn "def __init__(self, container:" docs/ | grep -v "ModelONEXContainer"

# Find version references without ONEX prefix
grep -rn "\\bv[0-9]\\.[0-9]" docs/ | grep -v "ONEX v"

# Find protocol terminology inconsistencies
grep -rn "service interface" docs/
```

### Automated Checks (Future)

**Pre-Commit Hook** (recommended):
```
#!/bin/bash
# .git/hooks/pre-commit

# Detect temporal language
if git diff --cached --name-only | grep -q '\.md$'; then
    temporal_language=$(git diff --cached | grep -E "(New pattern|Old pattern|new feature|old feature|latest version)")

    if [ -n "$temporal_language" ]; then
        echo "⚠️  Warning: Temporal language detected in documentation."
        echo "    Consider using version-specific terms instead."
        echo "    See: docs/conventions/TERMINOLOGY_GUIDE.md"
        echo ""
        echo "$temporal_language"
        exit 1
    fi
fi
```

---

## References

- **Container Types Guide**: `docs/architecture/CONTAINER_TYPES.md`
- **Terminology Audit**: `docs/quality/TERMINOLOGY_AUDIT_REPORT.md`
- **Fix Checklist**: `docs/quality/TERMINOLOGY_FIXES_CHECKLIST.md`
- **Node Building Guide**: `docs/guides/node-building/README.md`
- **Protocol Architecture**: `docs/architecture/PROTOCOL_ARCHITECTURE.md`

---

## Questions?

**Container confusion?** → See `docs/architecture/CONTAINER_TYPES.md`
**Version references?** → Use "ONEX v2.0" format
**Node capitalization?** → ALL CAPS in code, lowercase in prose
**Protocol naming?** → "protocol interface" (architecture) or "protocol name" (API docs)

**Not covered here?** → Check existing documentation for usage patterns or ask maintainers.

---

**Version**: 1.0
**Last Updated**: 2025-11-18
**Maintained By**: omnibase_core documentation team
