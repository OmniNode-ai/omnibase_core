# String ID Anti-Pattern Violations Report

Generated: 2025-10-02

## Summary
Found **13 violations** across **7 files** where ID fields use `str` instead of proper `UUID` types.

## Violations by Category

### Infrastructure Files (3 violations)

#### 1. `/src/omnibase_core/infrastructure/node_compute.py`
- **Line 57**: `operation_id: str | None = Field(default_factory=lambda: str(uuid4()))`
  - **Issue**: Uses `str` wrapping `uuid4()` instead of native UUID
  - **Fix**: Change to `operation_id: UUID = Field(default_factory=uuid4)`

- **Line 79**: `operation_id: str`
  - **Issue**: Output model uses string for operation ID
  - **Fix**: Change to `operation_id: UUID`

#### 2. `/src/omnibase_core/infrastructure/node_core_base.py`
- **Line 71**: `self.node_id: str = str(uuid4())`
  - **Issue**: Converts UUID to string immediately
  - **Fix**: Change to `self.node_id: UUID = uuid4()`

### Model Files (3 violations)

#### 3. `/src/omnibase_core/models/operations/model_computation_input_data.py`
- **Line 180**: `execution_id: str = Field(default="", description="Execution identifier")`
  - **Issue**: Uses empty string default instead of UUID
  - **Fix**: Change to `execution_id: UUID = Field(default_factory=uuid4, description="Execution identifier")`

#### 4. `/src/omnibase_core/models/operations/model_workflow_payload.py`
- **Line 27**: `execution_id: str = Field(default="", description="Unique workflow execution identifier")`
  - **Issue**: Uses empty string default instead of UUID
  - **Fix**: Change to `execution_id: UUID = Field(default_factory=uuid4, description="Unique workflow execution identifier")`

#### 5. `/src/omnibase_core/models/results/model_orchestrator_info.py`
- **Line 47**: `execution_id: str | None = Field(None, description="Execution identifier")`
  - **Issue**: Uses string for optional execution ID
  - **Fix**: Change to `execution_id: UUID | None = Field(None, description="Execution identifier")`

### Logging Files (6 violations)

#### 6. `/src/omnibase_core/logging/emit.py`
Multiple function signatures with `node_id: str`:
- **Line 26**: `emit_log_event()` - `node_id: str | None = None`
- **Line 77**: `emit_log_event_with_new_correlation()` - `node_id: str | None = None`
- **Line 116**: `emit_log_event_sync()` - `node_id: str | None = None`
- **Line 148**: `emit_log_event_async()` - `node_id: str | None = None`
- **Line 585**: `_route_to_logger_node()` - `node_id: str`

**Note**: These are complex as they involve auto-detection from context. The internal `_detect_node_id_from_context()` function returns string. Two options:
1. Keep as `str` since detection might return class names or module names (not always UUIDs)
2. Create a union type `node_id: UUID | str | None` to be explicit about accepting both

**Recommended Fix**: Change to `node_id: UUID | str | None` to be explicit about accepting both UUID objects and string fallbacks.

### Error Handling Files (1 violation)

#### 7. `/src/omnibase_core/errors/core_errors.py`
- **Line 472**: `correlation_id: str | UUID | None = None`
  - **Issue**: Accepts both str and UUID, but this is actually acceptable for boundary layer
  - **Status**: ✅ **ACCEPTABLE** - This is a proper boundary layer pattern that accepts both types and normalizes internally
  - **No Fix Needed**

## Fix Priority

### High Priority (Breaking Changes)
1. ✅ `node_compute.py` - Direct node implementation
2. ✅ `node_core_base.py` - Base class affects all nodes
3. ✅ `model_computation_input_data.py` - Core computation model
4. ✅ `model_workflow_payload.py` - Core workflow model

### Medium Priority (API Surface)
5. ✅ `model_orchestrator_info.py` - Result model

### Low Priority (Internal/Logging)
6. ⚠️ `emit.py` - Logging functions (consider keeping flexible for context detection)

## Total Violations to Fix: 12
- High Priority: 6 violations
- Medium Priority: 1 violation
- Low Priority: 6 violations (questionable - may want to keep flexible)
- Acceptable (No Fix): 1

## Impact Analysis

### Breaking Changes Expected
- Any code using `operation_id` as string will need updating
- Any code using `node_id` as string will need updating
- Any code using `execution_id` as string will need updating
- Serialization/deserialization code may need UUID handling

### Benefits
- Type safety improvements
- Consistent UUID usage across codebase
- Eliminates string conversion overhead
- Better validation at boundaries
- Clearer intent in type signatures

## Next Steps
1. Fix high-priority violations first
2. Update tests to use UUID types
3. Update any serialization code
4. Consider logging functions separately (may want to keep flexible)
5. Run full test suite to catch any missed conversions
