> **Navigation**: [Home](../INDEX.md) > Conventions > Version Semantics

# Version Field Semantics in ONEX Models

**Version**: 1.0.0
**Last Updated**: 2025-11-21
**Status**: Active

---

## Table of Contents

1. [Overview](#overview)
2. [Two Types of Versions](#two-types-of-versions)
3. [INTERFACE_VERSION (Class-Level)](#interface_version-class-level)
4. [version Field (Instance-Level)](#version-field-instance-level)
5. [When to Update Each Version](#when-to-update-each-version)
6. [Complete Examples](#complete-examples)
7. [Code Generation Implications](#code-generation-implications)
8. [Migration Guidance](#migration-guidance)
9. [Common Mistakes](#common-mistakes)
10. [Validation and Compliance](#validation-and-compliance)

---

## Overview

ONEX models use **two distinct version concepts** that serve different purposes and operate at different scopes:

1. **`INTERFACE_VERSION`** (ClassVar) - Tracks the stability of the model's **schema/interface**
2. **`version`** (instance field) - Tracks the version of a **specific model instance**

**Critical Distinction**: Confusing these two concepts can lead to:
- Broken code generation
- API compatibility issues
- Incorrect version tracking
- Failed ONEX validation

This document clarifies the semantics, usage, and update guidelines for both version types.

---

## Two Types of Versions

### Quick Reference

| Aspect | INTERFACE_VERSION | version Field |
|--------|-------------------|---------------|
| **Type** | `ClassVar[ModelSemVer]` | `ModelSemVer` (Pydantic Field) |
| **Scope** | Entire model class | Individual instance |
| **Purpose** | Schema stability tracking | Instance version tracking |
| **Set By** | Developers (class definition) | Runtime (instance creation) |
| **Mutable** | No (class constant) | No (frozen model) |
| **Used By** | Code generators, API clients | ONEX validation, auditing |
| **Updated When** | Interface/schema changes | Instance data changes |
| **Visibility** | Class-level metadata | Instance data |

### Visual Representation

```text
┌─────────────────────────────────────────────────────────┐
│        ModelFSMSubcontract (Class Definition)           │
│                                                          │
│  INTERFACE_VERSION = "1.0.0" ← Class-level constant    │
│                                  (Schema version)        │
├─────────────────────────────────────────────────────────┤
│  Instance #1:                                           │
│    version: "1.0.0"  ← Instance data version           │
│    state_machine_name: "OrderProcessing"               │
│    ...                                                  │
├─────────────────────────────────────────────────────────┤
│  Instance #2:                                           │
│    version: "1.2.0"  ← Different instance version      │
│    state_machine_name: "PaymentProcessing"             │
│    ...                                                  │
└─────────────────────────────────────────────────────────┘
```

---

## INTERFACE_VERSION (Class-Level)

### Definition

```python
from typing import ClassVar
from omnibase_core.models.primitives.model_semver import ModelSemVer

class ModelMySubcontract(BaseModel):
    """Subcontract model with interface version."""

    # Class-level: Tracks schema stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(
        major=1, minor=0, patch=0
    )
```

### Purpose

**INTERFACE_VERSION** indicates the **stability of the model's structure** for:
- **Code generation**: Ensures generated code matches expected schema
- **API compatibility**: Signals breaking changes to consumers
- **Schema evolution**: Tracks when fields are added/removed/changed
- **Documentation**: Provides versioned API reference

### Characteristics

- **Immutable**: Cannot be changed at runtime
- **Class-level**: Shared by all instances
- **Developer-controlled**: Updated manually during development
- **Semantic versioning**:
  - **Major**: Breaking changes (field removal, type changes)
  - **Minor**: Backward-compatible additions (new optional fields)
  - **Patch**: Documentation or internal changes (no schema impact)

### When to Update

Update `INTERFACE_VERSION` when:

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **Breaking** | Major (1.0.0 → 2.0.0) | Remove field, change field type, rename field, make optional field required |
| **Additive** | Minor (1.0.0 → 1.1.0) | Add optional field, add new enum value, expand validation range |
| **Non-Breaking** | Patch (1.0.0 → 1.0.1) | Fix docstring, update comments, internal refactoring |

**Examples**:

```python
# Breaking change: Remove field → Major version bump
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=2, minor=0, patch=0)
    # Removed: cache_backend field (was in 1.0.0)

# Additive change: Add optional field → Minor version bump
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=1, patch=0)
    cache_compression_enabled: bool = Field(default=False)  # New optional field

# Documentation change → Patch version bump
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=1)
    # Updated docstrings only, no schema changes
```

### Code Generation Dependency

**CRITICAL**: Code generators rely on `INTERFACE_VERSION` to:

1. **Detect breaking changes**: Prevent incompatible code generation
2. **Lock interfaces**: Ensure stability guarantees are met
3. **Version API clients**: Generate version-specific clients
4. **Validate contracts**: Ensure schema compliance

**Locked Interface Example** (from subcontract headers):

```python
"""
VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
"""
```

---

## version Field (Instance-Level)

### Definition

```python
from omnibase_core.models.primitives.model_semver import ModelSemVer
from pydantic import Field

class ModelMySubcontract(BaseModel):
    """Subcontract model with instance version."""

    # Instance-level: Tracks this specific instance's version
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
    )
```

### Purpose

The **version field** tracks the **version of a specific model instance** for:
- **ONEX validation**: Compliance with ONEX validation requirements
- **Instance tracking**: Audit trail for individual instances
- **Data migration**: Track which version of data this instance represents
- **Change history**: Record when instance data was updated

### Characteristics

- **Instance-specific**: Each instance has its own version
- **Runtime-set**: Initialized when instance is created
- **Frozen**: Cannot be changed after creation (Pydantic frozen models)
- **User-controlled**: Set by application logic, not framework
- **Independent**: Not related to `INTERFACE_VERSION`

### When to Update

Update the `version` field when creating a new instance to reflect:

| Scenario | Version Bump | Example |
|----------|--------------|---------|
| **Major instance change** | Major (1.0.0 → 2.0.0) | Complete data restructure, incompatible format |
| **Significant update** | Minor (1.0.0 → 1.1.0) | New data added, feature enabled |
| **Minor fix/update** | Patch (1.0.0 → 1.0.1) | Data correction, metadata update |

**Examples**:

```python
# Create instance with default version
cache_config = ModelCachingSubcontract(
    caching_enabled=True,
    cache_strategy="lru",
    version=ModelSemVer(major=1, minor=0, patch=0),  # Initial version
)

# Create instance with updated version after migration
migrated_config = ModelCachingSubcontract(
    caching_enabled=True,
    cache_strategy="lru_with_ttl",
    version=ModelSemVer(major=1, minor=1, patch=0),  # Bumped minor version
)
```

### ONEX Validation Requirement

**All ONEX-compliant models MUST include a `version` field** for:
- Compliance tracking
- Version-aware validation
- Audit trail completeness

**Note**: The `version` field is a required component of ONEX-compliant models for validation and auditing purposes.

---

## When to Update Each Version

### Decision Tree

```text
Did you change the MODEL SCHEMA (fields, types, validators)?
├─ YES → Update INTERFACE_VERSION
│   ├─ Breaking change? → Bump major (2.0.0)
│   ├─ Added optional field? → Bump minor (1.1.0)
│   └─ Documentation only? → Bump patch (1.0.1)
└─ NO → Did you change INSTANCE DATA?
    └─ YES → Update version field when creating new instance
        ├─ Incompatible data? → Bump major (2.0.0)
        ├─ New data added? → Bump minor (1.1.0)
        └─ Data corrected? → Bump patch (1.0.1)
```

### Update Matrix

| Change | INTERFACE_VERSION | version Field | Both? |
|--------|-------------------|---------------|-------|
| Add optional field to class | ✅ Bump minor | ❌ No change | No |
| Remove field from class | ✅ Bump major | ❌ No change | No |
| Change field type | ✅ Bump major | ❌ No change | No |
| Update instance data | ❌ No change | ✅ Set on new instance | No |
| Migrate instance format | ❌ No change | ✅ Bump on new instance | No |
| Major schema redesign | ✅ Bump major | ✅ Bump on new instances | Yes (separate changes) |

---

## Complete Examples

### Example 1: FSM Subcontract

```python
from typing import ClassVar
from pydantic import BaseModel, Field
from omnibase_core.models.primitives.model_semver import ModelSemVer

class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    INTERFACE_VERSION tracks schema stability for code generation.
    version tracks individual FSM instance versions.
    """

    # ========================================
    # CLASS-LEVEL: Schema version
    # ========================================
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(
        major=1, minor=0, patch=0
    )

    # ========================================
    # INSTANCE-LEVEL: Instance data version
    # ========================================
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
    )

    # ========================================
    # Domain-Specific: State machine version
    # ========================================
    state_machine_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the state machine definition",
    )

    # Core FSM fields
    state_machine_name: str = Field(...)
    description: str = Field(...)
    # ... more fields ...


# Usage: Creating FSM instances
order_fsm = ModelFSMSubcontract(
    state_machine_name="OrderProcessing",
    description="FSM for order workflow",
    version=ModelSemVer(major=1, minor=0, patch=0),  # Instance version
    state_machine_version=ModelSemVer(major=2, minor=1, patch=0),  # FSM definition version
)

payment_fsm = ModelFSMSubcontract(
    state_machine_name="PaymentProcessing",
    description="FSM for payment workflow",
    version=ModelSemVer(major=1, minor=2, patch=0),  # Different instance version
    state_machine_version=ModelSemVer(major=1, minor=0, patch=0),  # Different FSM version
)

# Note: Both instances share the same INTERFACE_VERSION (1.0.0)
# because they use the same model schema
```

### Example 2: Caching Subcontract

```python
class ModelCachingSubcontract(BaseModel):
    """
    Caching subcontract model.

    Demonstrates version field usage in caching configuration.
    """

    # CLASS-LEVEL: Schema version for code generation
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(
        major=1, minor=0, patch=0
    )

    # INSTANCE-LEVEL: Cache configuration version
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
    )

    caching_enabled: bool = Field(default=True)
    cache_strategy: str = Field(default="lru")
    # ... more fields ...


# Usage: Different cache configurations with different versions
dev_cache = ModelCachingSubcontract(
    caching_enabled=True,
    cache_strategy="lru",
    version=ModelSemVer(major=1, minor=0, patch=0),  # Initial version
)

prod_cache = ModelCachingSubcontract(
    caching_enabled=True,
    cache_strategy="distributed",
    version=ModelSemVer(major=2, minor=0, patch=0),  # Major change in configuration
)
```

### Example 3: Version Evolution Scenario

```python
# ========================================
# Version 1.0.0 of ModelCachingSubcontract
# ========================================
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    version: ModelSemVer = Field(...)
    caching_enabled: bool = Field(default=True)
    cache_strategy: str = Field(default="lru")


# ========================================
# Version 1.1.0: Added optional field (minor bump)
# ========================================
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=1, patch=0)

    version: ModelSemVer = Field(...)
    caching_enabled: bool = Field(default=True)
    cache_strategy: str = Field(default="lru")
    cache_compression_enabled: bool = Field(default=False)  # NEW FIELD


# ========================================
# Version 2.0.0: Breaking change (major bump)
# ========================================
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=2, minor=0, patch=0)

    version: ModelSemVer = Field(...)
    caching_enabled: bool = Field(default=True)
    cache_strategy: str = Field(default="lru")
    cache_compression_enabled: bool = Field(default=False)
    # BREAKING: Renamed from cache_backend to cache_storage_backend
    cache_storage_backend: str = Field(default="memory")
```

---

## Code Generation Implications

### Interface Stability Contract

**Code generators depend on `INTERFACE_VERSION` for**:

1. **Breaking Change Detection**
   ```python
   # Code generator checks INTERFACE_VERSION before generating
   if model.INTERFACE_VERSION.major > expected_major:
       raise IncompatibleSchemaError("Breaking change detected")
   ```

2. **Versioned Client Generation**
   ```python
   # Generated client code includes version check
   class FSMSubcontractClient_v1:
       COMPATIBLE_VERSIONS = ["1.0.0", "1.1.0", "1.2.0"]  # Major version 1.x.x

       def validate_compatibility(self, instance):
           if instance.INTERFACE_VERSION.major != 1:
               raise IncompatibleVersionError()
   ```

3. **Schema Locking**
   ```python
   """
   VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

   STABILITY GUARANTEE:
   - All fields, methods, and validators are stable interfaces
   - New optional fields may be added in minor versions only
   - Existing fields cannot be removed or have types/constraints changed
   """
   ```

### Version Validation in Code Generation

**Best Practice**: Code generators should validate both versions:

```python
def validate_model_compatibility(model_class, instance):
    """Validate model compatibility for code generation."""

    # Check class-level interface version
    if model_class.INTERFACE_VERSION.major != EXPECTED_MAJOR:
        raise IncompatibleInterfaceError(
            f"Interface version {model_class.INTERFACE_VERSION} "
            f"incompatible with expected major version {EXPECTED_MAJOR}"
        )

    # Check instance-level version for data compatibility
    if instance.version.major > model_class.INTERFACE_VERSION.major:
        warn(
            f"Instance version {instance.version} is newer than "
            f"interface version {model_class.INTERFACE_VERSION}"
        )
```

---

## Migration Guidance

### Migrating Instance Data

When migrating instance data between versions:

```python
def migrate_cache_config_v1_to_v2(old_config: dict) -> ModelCachingSubcontract:
    """
    Migrate cache configuration from v1 to v2.

    Changes:
    - Renamed: cache_backend → cache_storage_backend
    - Updated instance version to reflect migration
    """
    # Transform data
    new_config = {
        **old_config,
        "cache_storage_backend": old_config.pop("cache_backend"),
        "version": ModelSemVer(major=2, minor=0, patch=0),  # ← Instance version updated
    }

    # Create new instance with updated version
    return ModelCachingSubcontract(**new_config)
```

**Note**: `INTERFACE_VERSION` is not updated in migration code—it's already updated in the class definition.

### Schema Evolution Workflow

```text
1. Developer updates model schema
   ├─ Add/remove/change fields
   └─ Update INTERFACE_VERSION in class definition

2. Code generator detects version change
   ├─ Major bump → Regenerate clients with new major version
   ├─ Minor bump → Add new fields to existing clients
   └─ Patch bump → No code generation change

3. Application creates new instances
   ├─ Use updated schema (automatically uses new INTERFACE_VERSION)
   └─ Set instance version field based on data version

4. Migration (if needed)
   ├─ Transform old instance data to new format
   └─ Update instance version field to reflect migration
```

---

## Common Mistakes

### ❌ Mistake 1: Updating version Field Instead of INTERFACE_VERSION

```python
# WRONG: Updating instance version for schema change
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)  # ← Should be updated!

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=2, minor=0, patch=0)  # ← Wrong place!
    )

    # Added new field but didn't update INTERFACE_VERSION
    cache_compression_enabled: bool = Field(default=False)
```

```python
# CORRECT: Update INTERFACE_VERSION for schema changes
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=1, patch=0)  # ✅ Correct!

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0)  # ← Unchanged
    )

    cache_compression_enabled: bool = Field(default=False)
```

### ❌ Mistake 2: Not Updating INTERFACE_VERSION for Breaking Changes

```python
# WRONG: Breaking change without major version bump
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=1, patch=0)  # ← Should be 2.0.0!

    # Removed field (breaking change!) but only bumped minor version
    # cache_backend: str = Field(...)  # ← Removed
```

```python
# CORRECT: Major version bump for breaking changes
class ModelCachingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=2, minor=0, patch=0)  # ✅ Correct!

    # Breaking change reflected in major version bump
    # cache_backend removed
```

### ❌ Mistake 3: Confusing Domain Versions with Instance Versions

```python
# Example: FSM has THREE different version concepts
class ModelFSMSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ...  # Schema version
    version: ModelSemVer = ...                      # Instance version
    state_machine_version: ModelSemVer = ...        # FSM definition version

# WRONG: Using state_machine_version for instance tracking
fsm = ModelFSMSubcontract(
    state_machine_name="OrderProcessing",
    version=ModelSemVer(major=1, minor=0, patch=0),          # ← Instance version
    state_machine_version=ModelSemVer(major=2, minor=0, patch=0),  # ← FSM definition version
)

# These are DIFFERENT:
# - version: Tracks this ModelFSMSubcontract instance
# - state_machine_version: Tracks the FSM workflow definition itself
```

### ❌ Mistake 4: Modifying version Field After Creation

```python
# WRONG: Attempting to modify frozen field
config = ModelCachingSubcontract(
    caching_enabled=True,
    version=ModelSemVer(major=1, minor=0, patch=0),
)

config.version = ModelSemVer(major=1, minor=1, patch=0)  # ❌ Raises ValidationError (frozen)
```

```python
# CORRECT: Create new instance with updated version
old_config = ModelCachingSubcontract(
    caching_enabled=True,
    version=ModelSemVer(major=1, minor=0, patch=0),
)

new_config = ModelCachingSubcontract(
    caching_enabled=old_config.caching_enabled,
    version=ModelSemVer(major=1, minor=1, patch=0),  # ✅ New instance with new version
)
```

---

## Validation and Compliance

### ONEX Validation Requirements

**All ONEX-compliant models MUST**:

1. **Define `INTERFACE_VERSION`** as `ClassVar[ModelSemVer]`
2. **Include `version` field** as `ModelSemVer` with default factory
3. **Follow semantic versioning** for both versions
4. **Document version changes** in module docstring
5. **Maintain version consistency** across schema and instance versions

### Validation Checklist

```python
# ✅ Compliant Model
class ModelMySubcontract(BaseModel):
    """
    My subcontract model.

    VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION  # ✅ Documented
    """

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)  # ✅ Class-level

    version: ModelSemVer = Field(  # ✅ Instance-level
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
    )
```

### Pre-commit Validation

**Automated checks** (proposed - not yet implemented):

```bash
# Proposed validation script examples (not yet implemented):
# Check for missing INTERFACE_VERSION
# uv run python scripts/validate_versions.py --check-interface-version

# Check for missing version field
# uv run python scripts/validate_versions.py --check-instance-version

# Validate version consistency
# uv run python scripts/validate_versions.py --check-consistency
```

**Note**: These validation scripts are proposed enhancements. Currently, version field compliance is enforced through code review and type checking (mypy strict mode).

---

## Summary

### Key Takeaways

1. **Two Distinct Versions**:
   - `INTERFACE_VERSION` → Schema stability (class-level)
   - `version` → Instance data version (instance-level)

2. **Update Triggers**:
   - Schema changes → Update `INTERFACE_VERSION`
   - Instance data changes → Update `version` field

3. **Semantic Versioning**:
   - Major → Breaking changes
   - Minor → Backward-compatible additions
   - Patch → Non-breaking fixes/documentation

4. **Code Generation**:
   - Relies on `INTERFACE_VERSION` for stability
   - Breaking changes require major version bump
   - Minor changes allow backward compatibility

5. **ONEX Compliance**:
   - Both versions are required
   - Follow semantic versioning
   - Document in module docstring

### Quick Reference Card

```text
╔══════════════════════════════════════════════════════════════════╗
║                    VERSION FIELD QUICK REFERENCE                  ║
╠══════════════════════════════════════════════════════════════════╣
║  INTERFACE_VERSION                │  version Field                ║
║  (Class-Level)                    │  (Instance-Level)             ║
╟───────────────────────────────────┼───────────────────────────────╢
║  ClassVar[ModelSemVer]            │  ModelSemVer (Pydantic Field) ║
║  Schema stability                 │  Instance data version        ║
║  Code generation                  │  ONEX validation              ║
║  Update for schema changes        │  Update for data changes      ║
║  Shared by all instances          │  Unique per instance          ║
╚══════════════════════════════════════════════════════════════════╝
```

---

**See Also**:
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Semantic Versioning Specification](https://semver.org/)
- [ModelSemVer API Reference](../../src/omnibase_core/models/primitives/model_semver.py)
- [Error Handling Best Practices](ERROR_HANDLING_BEST_PRACTICES.md)

---

**Correlation ID**: `95cac850-05a3-43e2-9e57-ccbbef683f43`
**PR Reference**: #88 (Nitpick #8 - Version field semantics documentation)
