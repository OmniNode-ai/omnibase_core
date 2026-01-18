> **Navigation**: [Home](../index.md) > Quality > Tech Debt Metrics

# Tech Debt Metrics

> **Last Updated**: 2025-12-26
> **Source Files**: 2,314 Python files in `src/omnibase_core/`
> **mypy Status**: Strict mode, 0 errors

This document tracks type safety exemptions and tech debt reduction progress for the omnibase_core project.

---

## Type Safety Exemptions Summary

| Metric | Count | Files | Trend |
|--------|-------|-------|-------|
| `# type: ignore` comments | 262 | 133 | - |
| `# ONEX_EXCLUDE:` comments | 28 | 10 | - |
| `dict[str, Any]` exemptions | 26 | 10 | - |

**Exemption Ratio**: 0.113 exemptions per source file (262 / 2,314)

---

## Type Ignore Categories

Breakdown of `# type: ignore[...]` comments by error type:

| Error Type | Count | Percentage | Description |
|------------|-------|------------|-------------|
| `return-value` | 88 | 33.6% | Return type mismatches |
| `arg-type` | 44 | 16.8% | Argument type mismatches |
| `dict-item` | 30 | 11.5% | Dict value type issues (container resolver) |
| `unreachable` | 23 | 8.8% | Unreachable code blocks |
| `union-attr` | 14 | 5.3% | Union attribute access |
| `assignment` | 12 | 4.6% | Assignment type issues |
| `operator` | 9 | 3.4% | Operator type issues |
| `attr-defined` | 8 | 3.1% | Dynamic attribute definition |
| `literal-required` | 6 | 2.3% | Literal type requirements |
| `prop-decorator` | 5 | 1.9% | Property decorator issues |
| Other | 23 | 8.8% | Misc (method-assign, misc, etc.) |

### High-Concentration Files

Files with significant type: ignore concentrations:

| File | Count | Reason |
|------|-------|--------|
| `container/container_service_resolver.py` | 31 | DI registry dict construction |
| `infrastructure/node_base.py` | 13 | Base class with optional attributes |
| `models/common/model_numeric_string_value.py` | 10 | Numeric coercion utilities |
| `models/core/model_argument_map.py` | 10 | Dynamic argument handling |
| `models/contracts/model_workflow_condition.py` | 8 | Workflow condition parsing |
| `models/common/model_dict_value_union.py` | 8 | Dynamic value union handling |

---

## ONEX_EXCLUDE Categories

`# ONEX_EXCLUDE:` comments document intentional pattern deviations:

| Category | Count | Justification |
|----------|-------|---------------|
| `dict_str_any` - serialization | 6 | JSON/YAML serialization output |
| `dict_str_any` - external APIs | 4 | External library compatibility |
| `dict_str_any` - heterogeneous | 4 | Truly heterogeneous collections |
| `dict_str_any` - TypeIs narrowing | 3 | Type narrowing contexts |
| `dict_str_any` - schema conversion | 3 | Pydantic schema utilities |
| `dict_str_any` - factory input | 3 | Factory method input validation |
| `dict_str_type` | 1 | Intentional type mapping |
| `any_type` | 2 | Infrastructure utilities |

---

## Recent Improvements

### v0.4.0 - Payload Architecture (OMN-1008)

**Major Type Safety Improvements**:

1. **ModelEventPublishIntent** - Replaced `dict[str, Any]` with typed `ModelEventPayloadUnion`
   - Before: `target_event_payload: dict[str, Any]`
   - After: `target_event_payload: ModelEventPayloadUnion`
   - Impact: Enforces compile-time type checking for all event payloads

2. **Added `util_forward_reference_resolver.py`**
   - New utility for handling Pydantic forward references
   - Contains 2 type: ignore comments (unavoidable for dynamic import handling)
   - Enables proper type resolution in circular dependency scenarios

3. **Removed Backwards Compatibility Code**
   - Eliminated deprecated `payload` field aliases
   - Removed dual-support for dict and typed payloads
   - Simplified validation logic

**Commits**:
- `5d2f98ae` - Remove dict payloads, extract utils
- `9657c4d7` - Remove all deprecations, backwards compatibility

### v0.3.6 - Metadata Architecture (OMN-1009)

**Improvements**:
- Replaced `dict[str, Any]` metadata fields with typed `ModelMetadata*` models
- See PR #244 for details

---

## Targets and Goals

### Short-Term (v0.5.0)

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| `# type: ignore` | 262 | <250 | Address `return-value` errors in mixins |
| `dict-item` ignores | 30 | <20 | Refactor container_service_resolver.py |
| Overall ratio | 0.113 | <0.10 | Focus on high-concentration files |

### Long-Term (v1.0.0)

| Metric | Target | Notes |
|--------|--------|-------|
| `# type: ignore` | <100 | Essential exceptions only |
| `# ONEX_EXCLUDE:` | <20 | External API boundaries |
| Exemption ratio | <0.05 | Industry best practice |

---

## How to Update This Document

Run the following commands to gather current metrics:

```bash
# Count type: ignore comments
grep -r "# type: ignore" src/omnibase_core/ | wc -l

# Count ONEX_EXCLUDE comments
grep -r "# ONEX_EXCLUDE:" src/omnibase_core/ | wc -l

# Count dict[str, Any] exclusions specifically
grep -r "ONEX_EXCLUDE.*dict" src/omnibase_core/ | wc -l

# Categorize type: ignore by error type
grep -r "# type: ignore\[" src/omnibase_core/ | \
  sed 's/.*# type: ignore\[\([^]]*\)\].*/\1/' | \
  sort | uniq -c | sort -rn

# Count source files
find src/omnibase_core -name "*.py" -type f | wc -l
```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project conventions and type checking requirements
- [docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node architecture patterns
