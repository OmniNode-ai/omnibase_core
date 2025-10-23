# Type Safety Overhaul - Next Steps

**Current Status**: Phase 2 In Progress - 64 errors remaining (down from 92)

---

## Quick Start

To continue the type safety overhaul, follow these steps:

### 1. Verify Current State
```bash
# Check error count
poetry run mypy src/omnibase_core/ --strict 2>&1 | grep "no-any-return" | wc -l
# Should show: 64

# Ensure tests pass
poetry run pytest tests/ -x -v
# Should show: 10,848 passing
```

### 2. Priority Order

**PHASE 2A: Models & Services (17 errors, 3-4 hours)**
1. Models/Core Registry (10 errors)
2. Container Generics (5 errors)
3. Discovery Events (2 errors)

**PHASE 2B: Infrastructure (2 errors, 30 minutes)**
4. node_base.py (1 error)
5. node_core_base.py (1 error)

**PHASE 2C: Mixins (45 errors, 6-8 hours)**
6. High-impact mixins (7 files with 20+ errors)
7. Remaining mixins (6 files with remaining errors)

---

## Detailed Fix Guide

### Pattern 1: Container Service Resolution

**Problem**: Container methods return Any
```python
# Error: Returning Any from function declared to return "ModelActionRegistry"
return container.action_registry()
```

**Solution**: Add explicit type annotation
```python
registry: ModelActionRegistry = container.action_registry()
return registry
```

**Files Needing This**:
- `model_event_type_registry.py:221, 231`
- `model_cli_command_registry.py:274, 283`
- `service_registry.py:428, 470`

---

### Pattern 2: Generic Type Returns

**Problem**: Generic T returns from container
```python
# Error: Returning Any from function declared to return "T"
return self._resolve_instance(interface)
```

**Solution**: Use cast() for generic types
```python
from typing import cast
instance = self._resolve_instance(interface)
return cast(T, instance)
```

**Files Needing This**:
- `model_onex_container.py:264, 288, 363` (Generic T)
- `service_registry.py:428, 470` (Generic TInterface)

---

### Pattern 3: UUID Attribute Access

**Problem**: UUID from dynamic attribute access
```python
# Error: Returning Any from function declared to return "UUID"
return event.node_id
```

**Solution**: Type annotation or cast
```python
node_id: UUID = event.node_id
return node_id
# OR
return cast(UUID, event.node_id)
```

**Files Needing This**:
- `model_nodehealthevent.py:48`
- `model_node_shutdown_event.py:72`
- `model_nodeintrospectionevent.py:65`
- `model_introspection_response_event.py:82`

---

### Pattern 4: Pydantic model_dump()

**Problem**: model_dump() returns dict[str, Any]
```python
# Error: Returning Any from function declared to return "dict[str, Any]"
return self.model_dump()
```

**Solution**: Explicit type annotation
```python
result: dict[str, Any] = self.model_dump()
return result
```

**Files Needing This**:
- `model_onex_container.py:625`
- `model_custom_connection_properties.py:75`

---

### Pattern 5: Generic State Types (Mixins)

**Problem**: InputStateT/OutputStateT returns
```python
# Error: Returning Any from function declared to return "InputStateT"
return self._transform_state(input_state)
```

**Solution**: Cast to generic type
```python
from typing import cast
transformed = self._transform_state(input_state)
return cast(InputStateT, transformed)
```

**Files Needing This**:
- `mixin_event_listener.py:714, 724, 733, 740`
- `mixin_cli_handler.py:339`
- `mixin_event_bus.py:639, 641`
- `mixin_hybrid_execution.py:245`
- `node_base.py:519`

---

### Pattern 6: Type | None Returns

**Problem**: getattr or dict.get() returns Any
```python
# Error: Returning Any from function declared to return "str | None"
return self.config.get("key")
```

**Solution**: Type guard or conversion
```python
value = self.config.get("key")
return str(value) if value is not None else None
# OR with type guard
if isinstance(value, str):
    return value
return None
```

**Files Needing This**:
- `mixin_discovery_responder.py:458, 460`
- `model_external_service_config.py:92, 136`
- Various mixin dict operations

---

## Automation Script

For bulk fixes of similar patterns, use this script:

```python
#!/usr/bin/env python3
"""Automated type safety fixes for common patterns."""
import re
from pathlib import Path

def fix_container_returns(file_path: Path, class_name: str) -> None:
    """Fix container.service() returns."""
    content = file_path.read_text()

    # Pattern: return container.service_name()
    pattern = rf'(return\s+)container\.(\w+)\(\)'

    def replacement(match: re.Match) -> str:
        method = match.group(2)
        return f'result: {class_name} = container.{method}()\n        return result'

    content = re.sub(pattern, replacement, content)
    file_path.write_text(content)

# Usage
fix_container_returns(
    Path("src/omnibase_core/models/core/model_event_type_registry.py"),
    "ModelEventTypeRegistry"
)
```

---

## Testing Strategy

After each batch of fixes:

```bash
# 1. Check mypy on specific files
poetry run mypy src/omnibase_core/models/core/model_action_registry.py --strict

# 2. Run related tests
poetry run pytest tests/unit/models/core/test_action_registry.py -xvs

# 3. Full test suite (every 5-10 files)
poetry run pytest tests/ -x

# 4. Count remaining errors
poetry run mypy src/omnibase_core/ --strict 2>&1 | grep "no-any-return" | wc -l
```

---

## Commit Strategy

Commit after each logical group:

```bash
# After fixing models/core (10 files)
git add src/omnibase_core/models/core/
git commit -m "fix: resolve no-any-return errors in models/core registry classes"

# After fixing container (2 files)
git add src/omnibase_core/models/container/ src/omnibase_core/container/
git commit -m "fix: resolve generic type returns in container classes"

# After fixing mixins (13 files)
git add src/omnibase_core/mixins/
git commit -m "fix: resolve no-any-return errors in mixin layer"
```

---

## Progress Tracking

Update error count regularly:

```bash
# Create a tracking file
echo "$(date): $(poetry run mypy src/omnibase_core/ --strict 2>&1 | grep 'no-any-return' | wc -l) errors" >> TYPE_SAFETY_LOG.txt

# View progress
cat TYPE_SAFETY_LOG.txt
```

---

## Common Pitfalls

### ❌ Avoid
1. Using `# type: ignore` - Always fix the root cause
2. Returning `Any` - Always narrow to specific type
3. Skipping tests - Always verify no regressions
4. Large commits - Keep commits focused and reviewable

### ✅ Do
1. Add explicit type annotations
2. Use isinstance() checks for type narrowing
3. Use cast() for generic types only when necessary
4. Test after each file or small batch
5. Commit frequently with clear messages

---

## Estimated Timeline

| Phase | Errors | Time | Cumulative |
|-------|--------|------|------------|
| 2A: Models/Services | 17 | 3-4h | 3-4h |
| 2B: Infrastructure | 2 | 0.5h | 4-5h |
| 2C: Mixins | 45 | 6-8h | 10-13h |
| **Total Remaining** | **64** | **10-13h** | - |

**Already Complete**: 28 errors (3-4 hours invested)
**Total Project**: 92 errors (13-17 hours total)

---

## Success Criteria

- [ ] 0 `no-any-return` errors
- [ ] All 10,848 tests passing
- [ ] No new type errors introduced
- [ ] Code review approved
- [ ] Documentation updated

---

## Support Resources

- **Type Analysis**: `TYPE_ANALYSIS_REPORT.md`
- **Protocol Guide**: `PROTOCOL_ARCHITECTURE.md`
- **Progress Tracker**: `TYPE_SAFETY_PROGRESS.md`
- **Fix Patterns**: This file

---

## Questions?

If stuck, refer to:
1. Existing fixes in completed files (utils/, logging/, models/security/)
2. Python typing documentation: https://docs.python.org/3/library/typing.html
3. Pydantic v2 typing: https://docs.pydantic.dev/latest/concepts/types/
4. Mypy strict mode: https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict

---

**Last Updated**: 2025-10-22
**Status**: Ready to continue Phase 2
**Next**: Fix Models/Core registry errors (10 errors, ~2-3 hours)
