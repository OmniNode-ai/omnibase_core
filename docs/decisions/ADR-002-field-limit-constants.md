# ADR-002: Centralized Field Limit Constants

**Status**: Accepted

**Date**: 2025-01-15

**Decision Makers**: ONEX Core Team

---

## Context

### Problem Statement

The omnibase_core codebase contains numerous Pydantic models that enforce field length constraints using `max_length` validators. Prior to this decision, these limits were hardcoded directly in model definitions, leading to several issues:

1. **Inconsistency**: The same semantic field type (e.g., identifiers, paths, descriptions) used different limit values across different models.

2. **Maintenance Burden**: Updating a limit required finding and modifying every occurrence throughout the codebase.

3. **Lack of Documentation**: There was no central reference explaining why specific limits were chosen or what semantic category a limit belonged to.

4. **Risk of Errors**: Copy-paste errors led to inappropriate limits (e.g., using a description limit for an identifier field).

### Driving Forces

- Need for consistent field validation across 1800+ source files
- Desire to align with industry standards (e.g., RFC 2616 for URLs)
- Requirement for easy global updates when limits need adjustment
- Goal of self-documenting code through meaningful constant names

---

## Decision

We will create a centralized constants module (`constants_field_limits.py`) containing all field length and collection size limits used throughout the codebase. Constants are organized by semantic category, with clear documentation explaining the rationale for each value.

### Implementation Location

```text
src/omnibase_core/constants/constants_field_limits.py
```

### Constant Categories and Values

#### Identifier Limits

| Constant | Value | Rationale |
|----------|-------|-----------|
| `MAX_IDENTIFIER_LENGTH` | 100 | Suitable for UUIDs (36 chars), short codes, and machine-readable keys. Balances uniqueness with storage efficiency. |
| `MAX_NAME_LENGTH` | 255 | Industry standard for display names and titles. Matches common database VARCHAR defaults. |
| `MAX_KEY_LENGTH` | 100 | Dictionary and map keys. Aligned with identifier length for consistency. |

#### Path Limits

| Constant | Value | Rationale |
|----------|-------|-----------|
| `MAX_PATH_LENGTH` | 255 | Matches Windows MAX_PATH (260 - null terminator - drive letter). Cross-platform compatible. |
| `MAX_URL_LENGTH` | 2048 | Per RFC 2616 practical limit. IE historically limited to 2083; 2048 provides safe margin. |

#### Content Limits

| Constant | Value | Rationale |
|----------|-------|-----------|
| `MAX_DESCRIPTION_LENGTH` | 1000 | Sufficient for detailed descriptions without allowing unbounded content. Fits comfortably in UI components. |
| `MAX_REASON_LENGTH` | 500 | Rationale and explanation fields. Shorter than descriptions as these should be concise. |
| `MAX_MESSAGE_LENGTH` | 1500 | General-purpose messages. Accommodates detailed information while preventing abuse. |
| `MAX_ERROR_MESSAGE_LENGTH` | 2000 | Error messages may include context, stack traces, and debugging information. |
| `MAX_LOG_MESSAGE_LENGTH` | 4000 | Log entries can be verbose. Aligns with common logging infrastructure limits. |

#### Collection Limits

| Constant | Value | Rationale |
|----------|-------|-----------|
| `MAX_TAGS_COUNT` | 50 | Tags per entity. Prevents tag abuse while allowing meaningful categorization. |
| `MAX_LABELS_COUNT` | 100 | Labels per entity. Higher than tags as labels may include system-generated entries. |
| `MAX_LABEL_LENGTH` | 100 | Individual label text. Aligned with identifier length for consistency. |

---

## Usage Examples

### In Pydantic Models

```python
from omnibase_core.constants.constants_field_limits import (
    MAX_IDENTIFIER_LENGTH,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
)

class ModelWorkflow(BaseModel):
    """Workflow model using centralized constants."""

    id: str = Field(..., max_length=MAX_IDENTIFIER_LENGTH)
    name: str = Field(..., max_length=MAX_NAME_LENGTH)
    description: str | None = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
```

### In Validators

```python
from pydantic import field_validator
from omnibase_core.constants.constants_field_limits import MAX_PATH_LENGTH

class ModelFileReference(BaseModel):
    path: str

    @field_validator("path")
    @classmethod
    def validate_path_length(cls, v: str) -> str:
        if len(v) > MAX_PATH_LENGTH:
            raise ValueError(f"Path exceeds maximum length of {MAX_PATH_LENGTH}")
        return v
```

---

## Consequences

### Positive

1. **Consistency**: All models use the same limits for semantically equivalent fields.

2. **Maintainability**: A single change to a constant propagates throughout the codebase.

3. **Self-Documentation**: Constant names convey intent (e.g., `MAX_ERROR_MESSAGE_LENGTH` vs magic number `2000`).

4. **Discoverability**: Developers can browse the constants module to understand available limits.

5. **Validation**: Easier to audit and verify that appropriate limits are used.

### Negative

1. **Migration Effort**: Existing models with hardcoded values must be updated.

2. **Import Overhead**: Models now require additional imports.

3. **Learning Curve**: New contributors must learn which constant applies to which field type.

### Neutral

1. **No Runtime Impact**: Constants are resolved at import time; no performance difference.

---

## Migration Strategy

### Phase 1: Foundation (Completed)

- Create `constants_field_limits.py` module
- Document all constants with rationale
- Add constants to package exports

### Phase 2: High-Priority Models

Migrate models that are:
- Frequently used across the codebase
- Part of public APIs
- Involved in serialization/deserialization

Priority targets:
- `ModelWorkflow`
- `ModelEventEnvelope`
- `ModelOnexError`
- `ModelHandlerOutput`

### Phase 3: Comprehensive Migration

Migrate all remaining models using hardcoded limits.

### Validation

To find remaining hardcoded values, run:

```bash
# Find hardcoded max_length values
grep -r "max_length\s*=" src/omnibase_core/models/ | grep -v "import" | grep -v "MAX_"

# Find specific magic numbers
grep -rE "max_length\s*=\s*[0-9]+" src/omnibase_core/models/
```

---

## Guidelines for New Constants

### When to Add a New Constant

Add a new constant when:

1. **Three or more models** use the same limit for semantically similar fields
2. **The limit has semantic meaning** (not just an arbitrary value)
3. **The limit aligns with external standards** (RFC, platform limits, etc.)
4. **The field type is likely to appear in future models**

### When NOT to Add a New Constant

Do not add a constant when:

1. The limit is truly unique to one model
2. The limit is derived from external constraints (e.g., a third-party API limit)
3. The limit is temporary or experimental

### Naming Convention

```text
MAX_{SEMANTIC_TYPE}_{UNIT}

Examples:
- MAX_IDENTIFIER_LENGTH (characters)
- MAX_TAGS_COUNT (items)
- MAX_RETRY_ATTEMPTS (attempts)
```

---

## Related Decisions

- **ADR-001**: (Reserved for future use)
- **ONEX Node Architecture**: Field limits align with node contract validation requirements

---

## References

- [RFC 2616 - HTTP/1.1](https://www.rfc-editor.org/rfc/rfc2616) - URL length recommendations
- [Windows MAX_PATH](https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation) - Path length constraints
- [Pydantic Field Constraints](https://docs.pydantic.dev/latest/concepts/fields/) - Validation documentation

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2025-01-15 | ONEX Core Team | Initial decision |
