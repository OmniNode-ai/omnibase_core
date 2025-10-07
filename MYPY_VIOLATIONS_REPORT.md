# MyPy Violations Report - Prioritized by File

## Executive Summary

**Total MyPy Errors:** 268 errors across 134 files
**Strategy:** Recreate top violators from scratch with correct types

---

## 🔥 Top 20 Violators (Candidates for Recreation)

### Tier 1: Critical (15+ violations) - RECREATE THESE
| Rank | File | Violations | Primary Issues |
|------|------|------------|----------------|
| 1 | `model_custom_filters.py` | 21 | Missing type annotations (5), union attr access (7), type assignments (6), arg-type (3) |
| 2 | `model_security_utils.py` | 13 | Complex recursive type issues, assignment mismatches, unreachable code |
| 3 | `model_nodehealthevent.py` | 13 | ModelHealthMetrics interface mismatch (12), type annotations (1) |

### Tier 2: High Priority (10-14 violations) - RECREATE OR FIX
| Rank | File | Violations | Primary Issues |
|------|------|------------|----------------|
| 4 | `model_node_capability.py` | 12 | str→ModelSemVer conversions (10), type annotations (1), operator (1) |
| 5 | `model_dependency.py` | 11 | Missing ModelSchemaValue import (10), missing ModelErrorContext (1) |
| 6 | `model_secret_manager.py` | 10 | Type compatibility issues, indexable errors |

### Tier 3: Medium Priority (7-9 violations) - FIX PATTERNS
| Rank | File | Violations | Primary Issues |
|------|------|------------|----------------|
| 7 | `model_secure_event_envelope_class.py` | 8 | Type mismatches, missing imports |
| 8 | `model_tool_health.py` | 7 | Type annotations, unreachable code |
| 9 | `model_examples_collection.py` | 7 | Type variable issues (3), attr access (2), call-arg (2) |

### Tier 4: Moderate (5-6 violations) - BATCH FIX
| Rank | File | Violations | Primary Issues |
|------|------|------------|----------------|
| 10 | `model_genericmetadata.py` | 6 | TypedDict issues (4), name-defined (1), type annotations (1) |
| 11 | `model_introspection_response_event.py` | 6 | Type annotations (3), str→UUID conversions (3) |
| 12 | `model_namespace.py` | 6 | Type annotations (2), method override issues |
| 13 | `model_trustpolicy.py` | 5 | Type variable, arg-type issues |
| 14 | `model_operation_parameters_base.py` | 5 | Type annotations, missing imports |
| 15 | `model_computation_output_data_class.py` | 5 | Union attr access, type mismatches |
| 16 | `model_tooldiscoveryrequest.py` | 5 | Type annotations, missing imports |
| 17 | `model_nodeintrospectionevent.py` | 5 | Type annotations (1), call-arg (3), attr-defined (1) |
| 18 | `model_node_metadata_block.py` | 5 | Type annotations, call-arg issues |
| 19 | `model_log_formatting.py` | 5 | Type annotations (4), attr-defined (1) |
| 20 | `model_node_service_config.py` | 4 | Re-definition, assignment, type annotations |

---

## 📊 Detailed Error Analysis for Top 6 Files

### 1. `model_custom_filters.py` (21 errors) - **RECREATE**

**Error Breakdown:**
- 5 × Missing type annotations (`no-untyped-def`)
- 7 × Union attr access (`.to_dict()` method missing on all filter types)
- 6 × Assignment type mismatches (assigning different filter types to `ModelStringFilter`)
- 3 × Argument type incompatibility

**Root Cause:** Poorly designed union type system. All filter classes need `.to_dict()` method or use discriminated union.

**Recommendation:** **RECREATE** with:
- Protocol/ABC base class defining `.to_dict()` method
- OR discriminated union with `type` field
- Proper type annotations on all methods

---

### 2. `model_security_utils.py` (13 errors) - **RECREATE**

**Error Breakdown:**
- 10 × Recursive type assignment/argument issues
- 2 × Variance issues (dict is invariant)
- 1 × Unreachable statement

**Root Cause:** Complex recursive JSON type not properly defined. Type aliases conflict.

**Recommendation:** **RECREATE** with:
- Proper recursive type alias: `JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None`
- Use `Mapping`/`Sequence` for covariant types
- Simplify control flow

---

### 3. `model_nodehealthevent.py` (13 errors) - **RECREATE**

**Error Breakdown:**
- 6 × Unexpected keyword argument "status" for `ModelHealthMetrics`
- 4 × Unexpected keyword argument "last_health_check" for `ModelHealthMetrics`
- 2 × Argument type incompatibility (`custom_metrics`)
- 1 × Missing attribute `status` on `ModelHealthMetrics`

**Root Cause:** Code expects different `ModelHealthMetrics` interface than what exists. Calling code out of sync with model definition.

**Recommendation:** **RECREATE** by:
1. Read `ModelHealthMetrics` definition
2. Update all factory methods to use correct interface
3. OR update `ModelHealthMetrics` to match expected interface

---

### 4. `model_node_capability.py` (12 errors) - **FIX PATTERN**

**Error Breakdown:**
- 10 × `str` passed to `version_introduced: ModelSemVer` parameter
- 1 × Missing type annotation
- 1 × Operator `<=` not supported between `ModelSemVer` and `str`

**Root Cause:** Factory methods still passing string versions after field was converted to ModelSemVer.

**Recommendation:** **BATCH FIX** - replace all `version_introduced="1.0.0"` with `version_introduced=ModelSemVer(major=1, minor=0, patch=0)`

---

### 5. `model_dependency.py` (11 errors) - **QUICK FIX**

**Error Breakdown:**
- 10 × `Name "ModelSchemaValue" is not defined`
- 1 × `Name "ModelErrorContext" is not defined`

**Root Cause:** Missing imports.

**Recommendation:** **QUICK FIX** - Add imports:
```python
from omnibase_core.models.core.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_error_context import ModelErrorContext
```

---

### 6. `model_secret_manager.py` (10 errors) - **RECREATE**

**Error Breakdown:**
- Multiple indexable/attr-defined errors
- Type compatibility issues

**Root Cause:** Models being used as dicts without proper support.

**Recommendation:** **RECREATE** with proper dict-like interface or use `.model_dump()`.

---

## 📋 Complete Violation List (All 134 Files)

### Files with 4+ violations (29 files) - Priority Fixes
```
21 - model_custom_filters.py
13 - model_security_utils.py
13 - model_nodehealthevent.py
12 - model_node_capability.py
11 - model_dependency.py
10 - model_secret_manager.py
8  - model_secure_event_envelope_class.py
7  - model_tool_health.py
7  - model_examples_collection.py
6  - model_genericmetadata.py
6  - model_introspection_response_event.py
6  - model_namespace.py
5  - model_trustpolicy.py
5  - model_operation_parameters_base.py
5  - model_computation_output_data_class.py
5  - model_tooldiscoveryrequest.py
5  - model_nodeintrospectionevent.py
5  - model_node_metadata_block.py
5  - model_log_formatting.py
4  - model_node_service_config.py
4  - model_signature_chain.py
4  - model_tool_invocation_event.py
4  - model_node_shutdown_event.py
4  - model_discovery_response.py
4  - model_schema.py
4  - model_onex_event.py
```

### Files with 2-3 violations (50 files) - Batch Fixes
```
3  - model_nodesignature.py
3  - model_detection_ruleset.py
3  - model_event_data_base.py
3  - model_versionunion.py
3  - model_discovery_request.py
3  - model_route_hop.py
3  - model_node_action.py
3  - model_execution_context.py
3  - model_directory_processing_result.py
3  - model_fast_imports.py
3  - model_enhanced_logger.py
2  - model_service_registry_config.py
2  - model_custom_fields.py
2  - model_security_policy.py
2  - model_secretmanagercompat.py
2  - model_function_node_metadata_class.py
2  - model_metadata_node_info.py
2  - [40+ more with 2 violations]
```

### Files with 1 violation (55 files) - Individual Fixes
```
1  - [55 files with single errors]
```

---

## 🎯 Recommended Fix Strategy

### Phase 1: Quick Wins (30 minutes)
**Fix files with simple missing imports (15 files):**
- `model_dependency.py` - Add ModelSchemaValue, ModelErrorContext imports
- Other files with `name-defined` errors
- **Impact:** Fixes ~30 errors

### Phase 2: Recreate Top 3 (2-3 hours)
**Recreate from scratch:**
1. `model_custom_filters.py` (21 errors) - 1 hour
2. `model_security_utils.py` (13 errors) - 45 min
3. `model_nodehealthevent.py` (13 errors) - 45 min
- **Impact:** Fixes 47 errors

### Phase 3: Pattern Fixes (1 hour)
**Batch fix common patterns:**
- `model_node_capability.py` - Replace str with ModelSemVer (12 errors)
- Files with type annotation issues - Add annotations (60+ errors)
- **Impact:** Fixes 72+ errors

### Phase 4: Remaining Files (2 hours)
**Fix moderate violators (7-10 errors each):**
- 6 files with 7-10 errors each
- **Impact:** Fixes remaining ~120 errors

### Phase 5: Polish (1 hour)
**Fix all 1-2 error files**
- 105 files with 1-2 errors
- Most are simple fixes
- **Impact:** Achieves 0 errors

**Total Estimated Time:** 7-8 hours
**With Parallel Agents:** 2-3 hours

---

## 🤖 Agent Coordination Strategy

### Spawn 6 Agents in Parallel:

**Agent 1: Quick Import Fixes** (30 min)
- Fix all `name-defined` errors
- Add missing imports
- Target: 15 files

**Agent 2: Recreate model_custom_filters.py** (1 hour)
- Complete rewrite with proper types
- Add Protocol base or discriminated union

**Agent 3: Recreate model_security_utils.py** (45 min)
- Fix recursive JSON type issues
- Proper variance handling

**Agent 4: Fix model_nodehealthevent.py** (45 min)
- Align with ModelHealthMetrics interface
- Fix all 13 errors

**Agent 5: Pattern Fixes** (1 hour)
- str→ModelSemVer conversions
- Add type annotations batch

**Agent 6: Moderate Violators** (1.5 hours)
- Fix 6 files with 7-10 errors each

**Final Agent: Polish & Validation** (30 min)
- Fix remaining 1-2 error files
- Run full validation

---

## 📝 Notes

- Some files may have been incorrectly counted if mypy output changed between runs
- Priority should be on files that block others (imports)
- Recreating vs fixing: If >10 errors and complex types → recreate
- Test after each phase to ensure no regressions
