# Protocol Audit & Deduplication Report
**Date:** 2025-10-07
**Repository:** omnibase_core
**Objective:** Identify protocol duplicates with omnibase_spi and create migration plan

---

## Executive Summary

**Critical Finding:** NO true duplicates found, but **4 NAMING CONFLICTS** discovered where the same protocol name is used for different purposes in each repository. Additionally, **2 DEAD CODE** files identified that are shadowed by omnibase_spi re-exports.

**Impact:**
- **High Risk:** `ProtocolEventBus` - Mixed usage across codebase (some files use omnibase_core version, others use omnibase_spi version)
- **Medium Risk:** 2 protocol files are dead code consuming maintenance overhead
- **Low Risk:** Naming conflicts may cause confusion but are currently isolated

---

## Phase 1: Protocol Inventory (omnibase_core)

### Complete Protocol List

| Protocol Name | Location | Runtime Checkable | Purpose |
|--------------|----------|-------------------|---------|
| ProtocolErrorContext | `types/protocol_error_context.py` | ✅ Yes | Simple dict conversion for error context |
| ProtocolMetadataProvider | `types/protocol_metadata_provider.py` | ❌ No | Simple metadata property |
| ProtocolSchemaValue | `types/protocol_schema_value.py` | ✅ Yes | Schema value conversion |
| ProtocolValidatable | `types/protocol_validatable.py` | ❌ No | Instance validation (bool return) |
| ProtocolLogContextFallback | `logging/protocol_log_context_fallback.py` | ❌ No | Fallback for log context |
| ProtocolRegistryAware | `mixins/protocol_registry_aware.py` | ❌ No | Registry acceptance |
| ProtocolEventBus | `mixins/protocol_event_bus.py` | ✅ Yes | Synchronous event bus |
| SerializableMixin | `mixins/mixin_serializable.py` | ❌ No | Recursive serialization |
| EnumStatusProtocol | `models/core/model_status_protocol.py` | ❌ No | Status enum migration |

**Total:** 9 protocols

---

## Phase 2: Duplicate Analysis

### Category 1: DEAD CODE (Shadowed by omnibase_spi)

#### ProtocolMetadataProvider
**Status:** ⚠️ DEAD CODE - Remove immediately

**Evidence:**
- Local file: `src/omnibase_core/types/protocol_metadata_provider.py`
- **ZERO direct imports** of local version
- `constraints.py` line 55: `from omnibase_spi.protocols.types import ProtocolMetadataProvider`
- Re-exported via `types/__init__.py` line 35, 146
- **All consumers are using omnibase_spi version via re-export**

**Signature Comparison:**
```python
# omnibase_core (UNUSED)
class ProtocolMetadataProvider(Protocol):
    @property
    def metadata(self) -> dict[str, Any]: ...

# omnibase_spi (ACTIVE)
@runtime_checkable
class ProtocolMetadataProvider(Protocol):
    __omnibase_metadata_provider_marker__: Literal[True]
    async def get_metadata(self) -> dict[str, str | int | bool | float]: ...
```

**Usage:** 1 consumer (`types/constraints.py` - imports from omnibase_spi)

**Recommendation:** ✅ DELETE local file immediately

---

#### ProtocolValidatable
**Status:** ⚠️ DEAD CODE - Remove immediately

**Evidence:**
- Local file: `src/omnibase_core/types/protocol_validatable.py`
- **ZERO direct imports** of local version
- `constraints.py` line 58: `from omnibase_spi.protocols.types import ProtocolValidatable`
- Re-exported via `types/__init__.py` line 36, 147
- **All consumers are using omnibase_spi version via re-export**

**Signature Comparison:**
```python
# omnibase_core (UNUSED)
class ProtocolValidatable(Protocol):
    def validate_instance(self) -> bool: ...

# omnibase_spi (ACTIVE)
@runtime_checkable
class ProtocolValidatable(Protocol):
    async def get_validation_context(self) -> dict[str, ContextValue]: ...
```

**Usage:** 1 consumer (`types/constraints.py` - imports from omnibase_spi)

**Recommendation:** ✅ DELETE local file immediately

---

### Category 2: NAMING CONFLICTS (Different Signatures)

#### ProtocolErrorContext
**Status:** ⚠️ NAMING CONFLICT - Different purposes

**Signature Comparison:**
```python
# omnibase_core
@runtime_checkable
class ProtocolErrorContext(Protocol):
    def to_dict(self) -> dict[str, Any]: ...

# omnibase_spi (DIFFERENT - comprehensive error tracking)
@runtime_checkable
class ProtocolErrorContext(Protocol):
    correlation_id: UUID
    operation_name: str
    timestamp: ProtocolDateTime
    context_data: dict[str, ContextValue]
    stack_trace: str | None
    async def validate_error_context(self) -> bool: ...
    def has_trace(self) -> bool: ...
```

**Usage in omnibase_core:**
- Imported via `types/core_types.py`
- Exported via `types/__init__.py`
- **2 consumers total**

**Recommendation:** 🔍 INVESTIGATE - Rename local protocol to avoid confusion (e.g., `ProtocolSimpleErrorContext`)

---

#### ProtocolEventBus
**Status:** 🚨 CRITICAL - MIXED USAGE ACROSS CODEBASE

**Signature Comparison:**
```python
# omnibase_core (sync event-based)
@runtime_checkable
class ProtocolEventBus(Protocol):
    def publish(self, event: ModelOnexEvent) -> None: ...
    def publish_async(self, envelope: ModelEventEnvelope[Any]) -> None: ...
    def subscribe(self, handler: Callable, event_type: str | None = None) -> Any: ...
    def unsubscribe(self, subscription: Any) -> None: ...

# omnibase_spi (async Kafka-based)
@runtime_checkable
class ProtocolEventBus(Protocol):
    @property
    def adapter(self) -> ProtocolKafkaEventBusAdapter: ...
    @property
    def environment(self) -> str: ...
    @property
    def group(self) -> str: ...
    async def publish(self, topic: str, key: bytes | None, value: bytes, headers: ...) -> None: ...
    async def subscribe(self, topic: str, group_id: str, on_message: Callable) -> ...: ...
```

**Mixed Usage:**

**Using omnibase_core version:**
- `mixins/__init__.py` line 62
- `mixins/mixin_workflow_support.py` line 15
- `mixins/mixin_event_listener.py` line 31

**Using omnibase_spi version:**
- `mixins/mixin_event_driven_node.py` line 40
- `mixins/mixin_discovery_responder.py` line 12

**Total consumers:** 15 files (via direct and indirect imports)

**Recommendation:** 🚨 CRITICAL ISSUE - Requires architectural decision:
1. **Option A:** Rename omnibase_core protocol to `ProtocolSyncEventBus`
2. **Option B:** Migrate all omnibase_core usage to omnibase_spi async version
3. **Option C:** Create adapter layer to unify interfaces

---

### Category 3: UNIQUE PROTOCOLS (Only in omnibase_core)

#### ProtocolSchemaValue
**Status:** ✅ KEEP - No conflict, actively used

**Location:** `types/protocol_schema_value.py`

**Signature:**
```python
@runtime_checkable
class ProtocolSchemaValue(Protocol):
    def to_value(self) -> object: ...
    @classmethod
    def from_value(cls, value: object) -> ProtocolSchemaValue: ...
```

**Usage:** 2 consumers (`types/__init__.py`, `types/core_types.py`)

**Recommendation:** ✅ KEEP - Evaluate for future migration to omnibase_spi

---

#### ProtocolLogContextFallback
**Status:** ✅ KEEP - Fallback pattern by design

**Location:** `logging/protocol_log_context_fallback.py`

**Purpose:** Fallback when omnibase_spi is not available (by design)

**Signature:**
```python
class ProtocolLogContextFallback(Protocol):
    def to_dict(self) -> dict[str, Any]: ...
```

**Usage:** 2 consumers (`logging/structured.py`, self)

**Recommendation:** ✅ KEEP - Intentional fallback pattern

---

#### ProtocolRegistryAware
**Status:** ⚠️ INVESTIGATE - Already imports from omnibase_spi

**Location:** `mixins/protocol_registry_aware.py`

**Signature:**
```python
class ProtocolRegistryAware(Protocol):
    registry: ProtocolServiceRegistry | None
```

**Note:** Already imports `ProtocolServiceRegistry` from omnibase_spi

**Usage:** 2 consumers (`mixin_registry_injection.py`, self)

**Recommendation:** 🔍 EVALUATE - Consider moving to omnibase_spi for consistency

---

#### SerializableMixin
**Status:** ✅ KEEP - Actively used

**Location:** `mixins/mixin_serializable.py`

**Signature:**
```python
class SerializableMixin(Protocol):
    def to_serializable_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_serializable_dict(cls, data: dict[str, Any]) -> T: ...
```

**Usage:** 2 consumers (`mixins/__init__.py`, self)

**Recommendation:** ✅ KEEP - Evaluate for future migration to omnibase_spi

---

#### EnumStatusProtocol
**Status:** ✅ KEEP - Domain-specific

**Location:** `models/core/model_status_protocol.py`

**Signature:**
```python
class EnumStatusProtocol(Protocol):
    value: str
    def to_base_status(self) -> EnumBaseStatus: ...
```

**Usage:** 2 consumers (`enum_status_migration.py`, self)

**Recommendation:** ✅ KEEP - Domain-specific to omnibase_core status system

---

## Phase 3: Import Analysis Summary

| Protocol | Direct Imports | Via Re-exports | Total Usage |
|----------|---------------|----------------|-------------|
| ProtocolErrorContext | 0 | 2 | 2 |
| ProtocolMetadataProvider | 0 (spi) | 1 (spi) | 1 |
| ProtocolSchemaValue | 0 | 2 | 2 |
| ProtocolValidatable | 0 (spi) | 1 (spi) | 1 |
| ProtocolLogContextFallback | 1 | 1 | 2 |
| ProtocolRegistryAware | 1 | 1 | 2 |
| ProtocolEventBus | 3 (core) + 2 (spi) | ~10 | 15 |
| SerializableMixin | 1 | 1 | 2 |
| EnumStatusProtocol | 1 | 1 | 2 |

---

## Phase 4: Migration Plan

### IMMEDIATE ACTIONS (Dead Code Removal)

#### Action 1: Remove ProtocolMetadataProvider
**Risk:** ✅ LOW - File is completely unused

**Steps:**
1. ✅ Verify no direct imports exist
2. Delete file: `src/omnibase_core/types/protocol_metadata_provider.py`
3. Verify re-export still works via `constraints.py` → `types/__init__.py`
4. Run `poetry run mypy src/omnibase_core/`
5. Run formatters

**Import Changes:** NONE (file is unused)

**Expected Result:** No impact, dead code removed

---

#### Action 2: Remove ProtocolValidatable
**Risk:** ✅ LOW - File is completely unused

**Steps:**
1. ✅ Verified no direct imports exist
2. Delete file: `src/omnibase_core/types/protocol_validatable.py`
3. Verify re-export still works via `constraints.py` → `types/__init__.py`
4. Run `poetry run mypy src/omnibase_core/`
5. Run formatters

**Import Changes:** NONE (file is unused)

**Expected Result:** No impact, dead code removed

---

### DEFERRED ACTIONS (Requires Architectural Decisions)

#### Decision Required 1: ProtocolErrorContext Naming Conflict

**Current State:**
- omnibase_core version: Simple dict conversion
- omnibase_spi version: Comprehensive error context with async validation

**Options:**
1. **Rename local protocol** to `ProtocolSimpleErrorContext` for clarity
2. **Migrate to omnibase_spi version** if comprehensive error tracking needed
3. **Keep both** if they serve genuinely different purposes

**Recommendation:** Rename local protocol to avoid confusion

---

#### Decision Required 2: ProtocolEventBus Mixed Usage (CRITICAL)

**Current State:**
- 3 files use omnibase_core sync version
- 2 files use omnibase_spi async Kafka version
- **This creates inconsistent behavior across the codebase**

**Options:**
1. **Unified Migration:** Migrate all usage to omnibase_spi async version
   - Requires updating mixin_event_listener.py, mixin_workflow_support.py
   - Breaking change for consumers expecting sync behavior

2. **Rename & Coexist:** Rename omnibase_core version to `ProtocolSyncEventBus`
   - Explicit naming makes intent clear
   - Allows both patterns to coexist
   - No breaking changes

3. **Adapter Pattern:** Create adapter from sync → async
   - Bridge between sync and async patterns
   - More complex but preserves both interfaces

**Recommendation:** Option 2 (Rename to `ProtocolSyncEventBus`) for immediate clarity

---

### EVALUATION ACTIONS (Future Consideration)

#### Evaluate 1: Move ProtocolSchemaValue to omnibase_spi

**Rationale:** Generic schema value protocol could benefit other packages

**Prerequisites:**
- Ensure no omnibase_core-specific dependencies
- Verify signature is sufficiently general

**Effort:** Medium

---

#### Evaluate 2: Move SerializableMixin to omnibase_spi

**Rationale:** Serialization is a cross-cutting concern

**Prerequisites:**
- Verify no circular dependencies
- Ensure compatibility with other packages

**Effort:** Medium

---

#### Evaluate 3: Move ProtocolRegistryAware to omnibase_spi

**Rationale:** Already imports from omnibase_spi, would be more consistent there

**Prerequisites:**
- None (already depends on omnibase_spi)

**Effort:** Low

---

## Phase 5: Execution Plan (Dead Code Only)

### Step 1: Delete Dead Protocol Files

```bash
# Verify current state
poetry run mypy src/omnibase_core/
poetry run pytest tests/ -v

# Remove dead code
rm src/omnibase_core/types/protocol_metadata_provider.py
rm src/omnibase_core/types/protocol_validatable.py

# Verify everything still works
poetry run mypy src/omnibase_core/
poetry run pytest tests/ -v

# Format code
poetry run black src/
poetry run isort src/
```

**Expected Result:**
- MyPy: ✅ No new errors (protocols re-exported from omnibase_spi)
- Tests: ✅ All passing
- Files removed: 2
- Lines removed: ~90

---

## Phase 6: Validation Checklist

### Pre-Removal Validation
- ✅ Verified ProtocolMetadataProvider has ZERO direct imports
- ✅ Verified ProtocolValidatable has ZERO direct imports
- ✅ Confirmed both protocols are re-exported from omnibase_spi via constraints.py
- ✅ Identified ProtocolEventBus mixed usage as critical issue

### Post-Removal Validation
- ⏳ MyPy type checking passes
- ⏳ All unit tests pass
- ⏳ Integration tests pass (if any)
- ⏳ Code formatters applied successfully

---

## Summary Statistics

### Protocols by Status

| Status | Count | Action |
|--------|-------|--------|
| Dead Code (Remove) | 2 | DELETE |
| Naming Conflicts | 2 | INVESTIGATE |
| Mixed Usage (Critical) | 1 | DECIDE |
| Unique (Keep) | 5 | EVALUATE |
| **Total** | **9** | - |

### Impact Assessment

| Impact Level | Count | Details |
|--------------|-------|---------|
| 🚨 Critical | 1 | ProtocolEventBus mixed usage |
| ⚠️ Medium | 2 | Dead code files |
| 🔍 Low | 4 | Naming conflicts, evaluation candidates |
| ✅ None | 2 | Intentional fallbacks |

### Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| Remove Dead Code | 15 min | LOW |
| Resolve ProtocolEventBus | 2-4 hours | HIGH |
| Rename Conflicts | 30 min | LOW |
| Evaluate Migrations | 4-8 hours | MEDIUM |

---

## Recommendations Priority

1. **IMMEDIATE:** Remove 2 dead code files (ProtocolMetadataProvider, ProtocolValidatable)
2. **URGENT:** Decide on ProtocolEventBus strategy (mixed usage is critical issue)
3. **SHORT-TERM:** Rename ProtocolErrorContext to avoid confusion
4. **LONG-TERM:** Evaluate moving generic protocols to omnibase_spi

---

## Appendix: File Locations

### Dead Code Files (Safe to Delete)
```
src/omnibase_core/types/protocol_metadata_provider.py
src/omnibase_core/types/protocol_validatable.py
```

### Files Importing from omnibase_spi (Already Migrated)
```
src/omnibase_core/types/constraints.py (lines 55, 58)
src/omnibase_core/mixins/mixin_event_driven_node.py (line 40)
src/omnibase_core/mixins/mixin_discovery_responder.py (line 12)
```

### Files Using Local Protocols (Require Review)
```
src/omnibase_core/mixins/mixin_event_listener.py (line 31)
src/omnibase_core/mixins/mixin_workflow_support.py (line 15)
src/omnibase_core/types/__init__.py (re-exports)
src/omnibase_core/types/core_types.py (imports local protocols)
```

---

**End of Report**
