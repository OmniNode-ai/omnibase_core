# ONEX Type Safety Anti-Pattern Remediation Plan

## Summary

This document outlines a comprehensive plan to eliminate type safety anti-patterns throughout the omnibase_core codebase, following the **Strong Typing Only - No Fallbacks** architectural principle.

## Anti-Pattern Categories Found

### 1. **String Path Anti-Patterns** (1 file)
**Files affected:**
- `src/omnibase_core/model/ai/haystack/model_document_processing.py`

**Anti-pattern:**
```python
file_path: str | Path  # WRONG - creates ambiguity
```

**Fix:**
```python  
file_path: Path  # CORRECT - always use Path objects
```

### 2. **Dict[str, Any] Anti-Patterns** (20+ files)
**High priority files:**
- `src/omnibase_core/core/monadic/model_node_result.py`
- `src/omnibase_core/core/mixins/mixin_node_service.py`
- `src/omnibase_core/core/node_reducer.py`
- `src/omnibase_core/core/contracts/model_contract_orchestrator.py`
- `src/omnibase_core/core/contracts/model_contract_compute.py`

**Anti-pattern:**
```python
metadata: dict[str, Any]  # WRONG - Any defeats type safety
context: dict[str, Any] | None  # WRONG - loose typing
```

**Fix:**
```python
metadata: dict[str, str]  # CORRECT - specific string values
context: dict[str, str] | None  # CORRECT - or use typed model
# OR better yet:
metadata: ModelMetadata  # CORRECT - proper typed model
```

### 3. **Discriminated Union Anti-Patterns** (5 files)
**Files affected:**
- `src/omnibase_core/core/common_types.py`
- `src/omnibase_core/model/claude_code_responses/claude_code_tool_response_union.py`
- `src/omnibase_core/model/hook_events/model_tool_event_union.py`
- `src/omnibase_core/model/validation/model_fixture_data.py`

**Anti-pattern:**
```python
# WRONG - discriminated unions for basic types
class ModelStringValue(BaseModel):
    type: Literal["string"] = "string"
    value: str

ModelTypedValue = Union[ModelStringValue, ModelIntegerValue, ...]
```

**Fix:**
```python
# CORRECT - generic containers preserving native types
class ModelValueContainer(BaseModel, Generic[T]):
    value: T

StringContainer = ModelValueContainer[str]
IntContainer = ModelValueContainer[int]
```

### 4. **Kwargs Any Anti-Patterns** (10+ files)
**Files affected:**
- `src/omnibase_core/core/core_bootstrap.py`
- `src/omnibase_core/mixin/mixin_redaction.py`
- `src/omnibase_core/mixin/mixin_utils.py`

**Anti-pattern:**
```python
def method(self, **kwargs: Any) -> None:  # WRONG
```

**Fix:**
```python
def method(self, **kwargs: str) -> None:  # CORRECT - constrained type
# OR better yet - explicit parameters:
def method(self, name: str, version: str) -> None:  # BEST
```

## Remediation Strategy

### Phase 1: Critical Core Files (Week 1)
**Priority: CRITICAL**

1. **Core Infrastructure** - Fix `dict[str, Any]` in core files:
   - `core/node_reducer.py`
   - `core/contracts/model_contract_orchestrator.py`
   - `core/mixins/mixin_node_service.py`
   - `core/monadic/model_node_result.py`

2. **Path Objects** - Fix string path fallbacks:
   - `model/ai/haystack/model_document_processing.py`

### Phase 2: Model Layer Cleanup (Week 2)
**Priority: HIGH**

1. **Remove Discriminated Union Anti-patterns**:
   - Replace `core/common_types.py` with generic containers
   - Fix `model/validation/model_fixture_data.py`
   - Update `model/hook_events/model_tool_event_union.py`

2. **Claude Code Response Models**:
   - Evaluate if `claude_code_tool_response_union.py` needs discriminated unions
   - If legitimate (for external API responses), document exception
   - If not, replace with generic containers

### Phase 3: Mixin Layer Hardening (Week 3)
**Priority: MEDIUM**

1. **Mixin Anti-patterns**:
   - Fix `**kwargs: Any` in mixin files
   - Replace with explicit parameters or constrained types
   - Update `mixin_redaction.py`, `mixin_utils.py`

2. **Bootstrap and Core Utilities**:
   - Fix `core_bootstrap.py` kwargs patterns
   - Ensure all container initialization uses strong types

### Phase 4: Validation and Testing (Week 4)
**Priority: LOW**

1. **Comprehensive Validation**:
   - Run union validation script
   - Ensure count stays below 6700 limit
   - Add tests for new generic containers

2. **Documentation Updates**:
   - Update all model docstrings
   - Add examples of proper generic usage
   - Document exceptions (if any)

## Implementation Guidelines

### Replace Dict[str, Any] Patterns

**Step 1: Identify Usage Context**
```bash
# Find specific usage patterns
grep -n "dict\[str, Any\]" file.py
```

**Step 2: Classify Replacement Strategy**
- **Configuration data**: Use `dict[str, str]` if all values are strings
- **Mixed data**: Create proper typed model
- **Metadata**: Use `dict[str, str]` for simple key-value pairs
- **Complex data**: Use generic containers `ModelValueContainer[T]`

**Step 3: Apply Replacement**
```python
# BEFORE
metadata: dict[str, Any] = Field(default_factory=dict)

# AFTER - Simple case
metadata: dict[str, str] = Field(default_factory=dict)

# AFTER - Complex case  
metadata: ModelTypedMapping = Field(default_factory=ModelTypedMapping)
```

### Replace Path String Fallbacks

**Step 1: Audit Path Usage**
```bash
# Find mixed path patterns
grep -n "str.*Path\|Path.*str" file.py
```

**Step 2: Standardize on Path Objects**
```python
# BEFORE
file_path: str | Path

# AFTER
file_path: Path

# Input validation at boundaries
@field_validator("file_path", mode="before")
@classmethod
def normalize_path(cls, v):
    return Path(v) if isinstance(v, str) else v
```

### Replace Discriminated Union Anti-patterns

**Step 1: Identify Legitimate vs Anti-pattern Usage**
- **Legitimate**: External API response types, heterogeneous data structures
- **Anti-pattern**: Wrapping basic Python types (str, int, float, bool)

**Step 2: Replace with Generic Containers**
```python
# BEFORE - Anti-pattern
class ModelStringValue(BaseModel):
    type: Literal["string"] = "string"
    value: str

# AFTER - Generic container
StringContainer = ModelValueContainer[str]
```

## Verification Strategy

### Automated Checks

1. **Union Count Validation**:
   ```bash
   python scripts/validate-union-usage.py --max-unions 6700
   ```

2. **Anti-pattern Detection**:
   ```bash
   # Check for remaining Any types
   find src -name "*.py" -exec grep -l "dict\[str, Any\]" {} \;

   # Check for path string fallbacks  
   find src -name "*.py" -exec grep -l "str.*Path\|Path.*str" {} \;

   # Check for kwargs Any
   find src -name "*.py" -exec grep -l "\*\*kwargs:.*Any" {} \;
   ```

3. **Type Checking**:
   ```bash
   poetry run mypy src/omnibase_core --strict
   ```

### Manual Code Review

1. **Core Files Review**: Ensure critical infrastructure uses strong types
2. **Model Consistency**: Verify all new models follow generic container patterns  
3. **API Boundary Validation**: Check that external interfaces have proper type conversion

## Success Metrics

### Quantitative Goals
- **Union count**: Maintain ≤ 6700 (current baseline: 6687)
- **Any type usage**: Eliminate all `dict[str, Any]` patterns
- **Path consistency**: 100% Path object usage (no string paths)
- **Type coverage**: 100% mypy strict mode compliance

### Qualitative Goals
- **Predictable APIs**: No Union[T, str] fallback patterns
- **Clear semantics**: Each field has exactly one type, not multiple options
- **Platform safety**: No string path platform issues
- **Maintainability**: Type errors caught at compile time, not runtime

## Risk Assessment

### Low Risk Changes
- Replacing `dict[str, Any]` with `dict[str, str]` in metadata
- Converting string paths to Path objects with validation
- Fixing `**kwargs: Any` to `**kwargs: str`

### Medium Risk Changes  
- Removing discriminated unions for basic types
- Updating core infrastructure types
- Changing mixin signatures

### High Risk Changes
- Modifying external API response models
- Changing container initialization patterns
- Updating event bus message types

## Rollback Strategy

1. **Git Branch Protection**: All changes on feature branches
2. **Incremental Commits**: Each file change as separate commit
3. **Test Suite Coverage**: Full test run before each phase
4. **Union Count Monitoring**: Fail CI if count exceeds 6700

## Timeline

| Phase | Duration | Effort | Risk | Dependencies |
|-------|----------|---------|------|--------------|
| Phase 1: Core Files | 1 week | 40 hours | Medium | None |
| Phase 2: Model Layer | 1 week | 32 hours | Low | Phase 1 |
| Phase 3: Mixin Layer | 1 week | 24 hours | Low | Phase 2 |
| Phase 4: Validation | 1 week | 16 hours | Low | All phases |
| **Total** | **4 weeks** | **112 hours** | **Medium** | Sequential |

---

**Document Version**: 1.0  
**Created**: 2025-01-15  
**Next Review**: After Phase 1 completion
