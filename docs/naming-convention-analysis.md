# Naming Convention Analysis - Model* Classes in nodes/ Directory

## Executive Summary

**Root Cause**: Validator false positives caused by helper models being located in `/nodes/` directory instead of `/models/infrastructure/`. The validator expects ALL classes in `/nodes/` to have `Node*` prefix unless they inherit from BaseModel.

**Status**: 3 of 4 classes are duplicates; 1 class needs to be created in proper location.

**Recommendation**: Remove duplicates from `nodes/` directory, create missing class in `models/infrastructure/`, and update imports.

---

## Detailed Analysis

### 1. Validator Logic

File: `scripts/validation/validate_naming.py`

**How it works**:
- Line 58-63: Defines "nodes" category with `Node*` prefix requirement
- Line 293-297: Exempts BaseModel subclasses from Node* requirement
- Line 326-340: Flags classes in `/nodes/` directory without Node* prefix
- Line 354-372: Uses heuristics to detect node-like classes (checks for keywords: "node", "effect", "compute", "reducer", "orchestrator")

**Why our classes are flagged**:
1. They are located in `/nodes/` directory
2. They are NOT BaseModel subclasses (just regular Python classes)
3. Therefore validator expects `Node*` prefix
4. User clarification: "only nodes need node prefixes, otherwise they are models"

### 2. Current State

| Class | Location in nodes/ | Location in models/infrastructure/ | Status |
|-------|-------------------|-----------------------------------|--------|
| `ModelCircuitBreaker` | ✅ `/nodes/model_circuit_breaker.py:32` | ✅ `/models/infrastructure/model_circuit_breaker.py:8` | **DUPLICATE** |
| `ModelComputeCache` | ✅ `/nodes/model_compute_cache.py:31` | ❌ Does not exist | **MISSING** |
| `ModelStreamingWindow` | ✅ `/nodes/model_streaming_window.py:14` | ✅ `/models/infrastructure/model_streaming_window.py:8` | **DUPLICATE** |
| `ModelConflictResolver` | ✅ `/nodes/model_conflict_resolver.py:17` | ✅ `/models/infrastructure/model_conflict_resolver.py:14` | **DUPLICATE** |

### 3. Import Analysis

**Current imports** (all from nodes/):

```python
# src/omnibase_core/nodes/node_effect.py:47
from omnibase_core.models.infrastructure import ModelCircuitBreaker

# src/omnibase_core/nodes/node_compute.py:40
from omnibase_core.models.infrastructure import ModelComputeCache

# src/omnibase_core/nodes/node_reducer.py:43
from omnibase_core.models.infrastructure import ModelConflictResolver

# src/omnibase_core/nodes/node_reducer.py:46
from omnibase_core.models.infrastructure import ModelStreamingWindow
```

**Required changes** (import from models/infrastructure/):

```python
# src/omnibase_core/nodes/node_effect.py:47
from omnibase_core.models.infrastructure import ModelCircuitBreaker

# src/omnibase_core/nodes/node_compute.py:40
from omnibase_core.models.infrastructure import ModelComputeCache

# src/omnibase_core/nodes/node_reducer.py:43
from omnibase_core.models.infrastructure import ModelConflictResolver

# src/omnibase_core/nodes/node_reducer.py:46
from omnibase_core.models.infrastructure import ModelStreamingWindow
```

### 4. Export Status in models/infrastructure/__init__.py

| Class | Exported? | Action Required |
|-------|-----------|----------------|
| `ModelCircuitBreaker` | ✅ Yes (line 11, 34) | None |
| `ModelComputeCache` | ❌ No | Add to imports and __all__ |
| `ModelStreamingWindow` | ✅ Yes (line 23, 52) | None |
| `ModelConflictResolver` | ✅ Yes (line 13, 35) | None |

### 5. Semantic Analysis

**ModelCircuitBreaker** (`nodes/model_circuit_breaker.py`):
- **Purpose**: Circuit breaker pattern for external service failures
- **Used by**: NodeEffect (resilient service interactions)
- **Is it a node?**: ❌ No - it's a helper utility
- **Correct location**: ✅ `models/infrastructure/`
- **Verdict**: Delete from nodes/, already exists in proper location

**ModelComputeCache** (`nodes/model_compute_cache.py`):
- **Purpose**: TTL-based caching with LRU eviction
- **Used by**: NodeCompute (optimize performance)
- **Is it a node?**: ❌ No - it's a helper utility
- **Correct location**: ✅ `models/infrastructure/`
- **Verdict**: Move to models/infrastructure/, does not exist there yet

**ModelStreamingWindow** (`nodes/model_streaming_window.py`):
- **Purpose**: Time-based windowing for streaming data
- **Used by**: Reduction operations
- **Is it a node?**: ❌ No - it's a helper utility
- **Correct location**: ✅ `models/infrastructure/`
- **Verdict**: Delete from nodes/, already exists in proper location

**ModelConflictResolver** (`nodes/model_conflict_resolver.py`):
- **Purpose**: Conflict resolution during data reduction
- **Used by**: Data reduction operations
- **Is it a node?**: ❌ No - it's a helper utility
- **Correct location**: ✅ `models/infrastructure/`
- **Verdict**: Delete from nodes/, already exists in proper location

### 6. nodes/__init__.py Export Status

File: `src/omnibase_core/nodes/__init__.py`

Line 33-35 explicitly states:
```python
# NOTE: Internal models like ModelConflictResolver, ModelDependencyGraph, ModelLoadBalancer,
# ModelStreamingWindow, ModelThunk, ModelWorkflowStep are NOT exported - they are internal
# implementation details used by the nodes themselves.
```

**Verdict**: These classes are correctly NOT exported from nodes/__init__.py, confirming they are internal implementation details, not public node types.

---

## Recommended Solution

### Phase 1: Create Missing Model (ModelComputeCache)

1. **Move** `/nodes/model_compute_cache.py` to `/models/infrastructure/model_compute_cache.py`
2. **Update** import in `/models/infrastructure/__init__.py`:
   ```python
   from .model_compute_cache import ModelComputeCache
   ```
3. **Add** to `__all__` list:
   ```python
   "ModelComputeCache",
   ```

### Phase 2: Update Imports in Node Files

Update 4 import statements:

1. **node_effect.py:47**: ✅ FIXED
   ```python
   from omnibase_core.models.infrastructure import ModelCircuitBreaker
   ```

2. **node_compute.py:40**: ✅ FIXED
   ```python
   from omnibase_core.models.infrastructure import ModelComputeCache
   ```

3. **node_reducer.py:43**: ✅ FIXED
   ```python
   from omnibase_core.models.infrastructure import ModelConflictResolver
   ```

4. **node_reducer.py:46**: ✅ FIXED
   ```python
   from omnibase_core.models.infrastructure import ModelStreamingWindow
   ```

### Phase 3: Delete Duplicate Files

Remove 4 files from `nodes/`:
```bash
rm src/omnibase_core/nodes/model_circuit_breaker.py
rm src/omnibase_core/nodes/model_compute_cache.py
rm src/omnibase_core/nodes/model_streaming_window.py
rm src/omnibase_core/nodes/model_conflict_resolver.py
```

### Phase 4: Verification

1. **Run validator**:
   ```bash
   poetry run python scripts/validation/validate_naming.py src/
   ```

2. **Run type checking**:
   ```bash
   poetry run mypy src/omnibase_core/nodes/
   ```

3. **Run tests**:
   ```bash
   poetry run pytest tests/unit/nodes/ -v
   ```

---

## Alternative Solutions (Not Recommended)

### Option A: Update Validator to Exempt These Classes

**Pros**: No file movement required
**Cons**:
- Doesn't fix the semantic issue (helper models in wrong location)
- Adds complexity to validator
- Violates ONEX architectural patterns (models should be in models/)

### Option B: Add Special Comment Markers

**Pros**: Minimal code changes
**Cons**:
- Band-aid solution
- Doesn't address root cause
- Creates technical debt

---

## Impact Analysis

### Files Changed: 9 total

**Created (1)**:
- `/models/infrastructure/model_compute_cache.py` (move from nodes/)

**Modified (4)**:
- `/nodes/node_effect.py` (1 import)
- `/nodes/node_compute.py` (1 import)
- `/nodes/node_reducer.py` (2 imports)
- `/models/infrastructure/__init__.py` (add ModelComputeCache export)

**Deleted (4)**:
- `/nodes/model_circuit_breaker.py` (duplicate)
- `/nodes/model_compute_cache.py` (moved)
- `/nodes/model_streaming_window.py` (duplicate)
- `/nodes/model_conflict_resolver.py` (duplicate)

### Test Impact

**Tests to verify**:
- `tests/unit/nodes/test_node_effect.py` (uses ModelCircuitBreaker)
- `tests/unit/nodes/test_node_compute.py` (uses ModelComputeCache)
- `tests/unit/nodes/test_node_reducer.py` (uses ModelConflictResolver, ModelStreamingWindow)

**Expected**: No test failures (imports change, functionality identical)

---

## Conclusion

**These are NOT validator false positives** - they are legitimate violations caused by helper models being in the wrong location.

**User clarification is correct**: "only nodes need node prefixes, otherwise they are models"

**Solution**: Move/delete files to match ONEX architectural patterns where helper models live in `models/infrastructure/`, not `nodes/`.

**Estimated effort**: ~15 minutes (low risk, straightforward refactor)

**Risk level**: Low (all changes are import path updates, no logic changes)
