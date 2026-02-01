> **Navigation**: [Home](../INDEX.md) > Conventions > Pydantic Best Practices

# Pydantic Best Practices for ONEX

This document covers Pydantic configuration patterns, safety considerations, and best practices for ONEX models.

---

## Table of Contents

1. [Model Configuration](#model-configuration)
2. [ConfigDict Policy Decision Matrix](#configdict-policy-decision-matrix)
3. [from_attributes Safety](#from_attributes-safety)
4. [Frozen Models](#frozen-models)
5. [Field Definition Best Practices](#field-definition-best-practices)
6. [Validation Patterns](#validation-patterns)
7. [Error Handling](#error-handling)

---

## Model Configuration

### Standard ConfigDict Options

```python
from pydantic import BaseModel, ConfigDict

class ModelExample(BaseModel):
    model_config = ConfigDict(
        frozen=True,           # Immutable after creation
        extra="forbid",        # Reject unknown fields
        validate_assignment=True,  # Validate on attribute assignment
    )
```

### Common Configuration Patterns

| Option | Value | Use Case |
|--------|-------|----------|
| `frozen=True` | Immutable model | Fingerprints, envelopes, security models |
| `frozen=False` | Mutable model | Configuration, builders, state objects |
| `extra="forbid"` | Strict validation | Contracts, security models |
| `extra="ignore"` | Flexible input | YAML contracts, external data |
| `validate_assignment=True` | Re-validate on set | Mutable models with constraints |

---

## ConfigDict Policy Decision Matrix

### Quick Decision Guide

For a rapid ConfigDict selection, follow this simplified flowchart:

```text
Is the model immutable after creation?
│
├─ YES ──► frozen=True, from_attributes=True (REQUIRED combo)
│          │
│          └─ Does it accept external data (YAML, APIs)?
│             │
│             ├─ NO (internal value object) ──► extra="forbid"
│             │
│             └─ YES (contracts, configs)
│                │
│                ├─ Extension point? ──► extra="allow"
│                │
│                └─ Forward-compat? ──► extra="ignore"
│
└─ NO ──► No frozen=True
          │
          └─ Is it internal or external?
             │
             ├─ Internal domain model ──► extra="forbid"
             │
             └─ External data / Contract ──► extra="ignore"
                │
                └─ Extension point? ──► extra="allow"
```

### Detailed Decision Flowchart

Use this flowchart to determine the appropriate ConfigDict settings for your model:

```text
                          ┌─────────────────────────────────┐
                          │      New Pydantic Model         │
                          └───────────────┬─────────────────┘
                                          │
                          ┌───────────────▼─────────────────┐
                          │  Should it be immutable after   │
                          │  creation? (fingerprints,       │
                          │  envelopes, value objects)      │
                          └───────────────┬─────────────────┘
                                     Yes / \ No
                     ┌──────────────────┘   └──────────────────┐
                     │                                          │
         ┌───────────▼───────────┐              ┌───────────────▼───────────────┐
         │ frozen=True           │              │ Does it accept external data   │
         │ from_attributes=True  │              │ (YAML, JSON, APIs)?            │
         │ (REQUIRED combo)      │              └───────────────┬───────────────┘
         └───────────┬───────────┘                         Yes / \ No
                     │                          ┌──────────────┘   └──────────────┐
         ┌───────────▼───────────┐              │                                  │
         │ Should unknown fields │  ┌───────────▼───────────┐      ┌───────────────▼───────────────┐
         │ be rejected?          │  │ Is it an extension    │      │ Internal domain model         │
         └───────────┬───────────┘  │ point for plugins?    │      │ extra="forbid"                │
                Yes / \ No          └───────────┬───────────┘      │ (catches bugs)                │
        ┌──────────┘   └──────────┐        Yes / \ No              └───────────────────────────────┘
        │                          │    ┌──────┘   └──────┐
┌───────▼─────────┐      ┌─────────▼───────┐     ┌────────▼────────┐
│ Value Object    │      │ Forward-compat  │     │ Extension Point │
│ extra="forbid"  │      │ extra="ignore"  │     │ extra="allow"   │
│ (security,      │      │ (contracts,     │     │ (plugins,       │
│ results)        │      │ configs)        │     │ metadata)       │
└─────────────────┘      └─────────────────┘     └─────────────────┘

RESULT CONFIGURATIONS:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Immutable Value Object:  ConfigDict(frozen=True, extra="forbid",            │
│                                     from_attributes=True)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Forward-Compatible:      ConfigDict(extra="ignore")                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Extension Point:         ConfigDict(extra="allow")                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Internal Domain Model:   ConfigDict(extra="forbid", from_attributes=True)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### When to use `extra="forbid"` (strictest)

Use for models where unknown fields indicate a bug:

- Security-critical models (signatures, assessments)
- Immutable value objects (results, metrics)
- Internal domain models
- Any model where extra fields should fail loudly

```python
class ModelSecurityAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    risk_level: str
    confidence: float
```

### When to use `extra="ignore"` (permissive)

Use for forward-compatibility with external data:

- YAML/JSON contract parsing from external sources
- Forward-compatibility with newer schema versions
- Infrastructure configuration models
- External API response models

```python
class ModelExternalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str
    settings: dict[str, Any]
```

### When to use `extra="allow"` (extensible)

Use ONLY when arbitrary additional fields are intentional:

- Extension point models (ModelNodeExtensions)
- Metadata passthrough containers
- Plugin/vendor extensibility points

```python
class ModelNodeExtensions(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Allows arbitrary vendor-specific fields
```

### When to use `frozen=True`

Use for models that should never change after creation:

- Value objects that must be immutable
- Results, metrics, assessments, audit entries
- Nested models that may be used in parallel test contexts
- **ALWAYS pair with `from_attributes=True`** for pytest-xdist compatibility

### When NOT to use `frozen=True`

Avoid for models that need mutation:

- Models with mutating methods (`add_*`, `mark_*`, `set_*`)
- Builder-pattern models
- Models used as accumulators
- Configuration objects that get modified at runtime

---

## from_attributes Safety

### What is `from_attributes`?

The `from_attributes=True` config option allows Pydantic to create models from arbitrary objects by reading their attributes:

```python
class ModelServiceMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    version: str

# Can create from any object with .name and .version attributes
class SomeOtherClass:
    name = "service"
    version = "1.0.0"

metadata = ModelServiceMetadata.model_validate(SomeOtherClass())
```

### When `from_attributes` is Safe

**SAFE - Frozen/Immutable Source Models:**

```python
from pydantic import BaseModel, ConfigDict

class ModelContractFingerprint(BaseModel):
    """Immutable fingerprint - safe for from_attributes."""
    model_config = ConfigDict(
        frozen=True,           # IMMUTABLE
        from_attributes=True,  # Safe because frozen
    )

    version: str
    hash_prefix: str
```

**Why it's safe:**
- Source object cannot be modified after creation
- No race conditions during attribute access
- Predictable behavior in concurrent scenarios

### When `from_attributes` is Risky

**RISKY - Mutable Source Objects:**

```python
# CAUTION: Mutable object with from_attributes
class ModelMutableConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeout: int
    retries: int

# Race condition risk:
config_obj = MutableConfigObject()
# Thread 1: config_obj.timeout = 30
# Thread 2: model = ModelMutableConfig.model_validate(config_obj)
# Thread 1: config_obj.timeout = 60
# What value did Thread 2 get?
```

### Safety Guidelines

| Source Type | `from_attributes` | Safety Level |
|-------------|-------------------|--------------|
| Frozen Pydantic model | Safe | Use freely |
| Immutable dataclass (`frozen=True`) | Safe | Use freely |
| NamedTuple | Safe | Use freely |
| Regular class (mutable) | Risky | Add synchronization |
| Dict-like objects | Safe | Pydantic handles dict input |

### pytest-xdist Compatibility

#### The Problem

pytest-xdist runs tests in parallel workers. Each worker imports model classes independently, creating different class objects with the same name. Without `from_attributes=True`, Pydantic rejects valid instances due to class identity differences.

**Example failure scenario:**
```python
# Worker 1 imports ModelSemVer as class object A
# Worker 2 imports ModelSemVer as class object B
# When a test passes ModelSemVer instance from Worker 1 context to Worker 2:
# Pydantic says "Expected ModelSemVer (class B), got ModelSemVer (class A)"
```

#### The Solution

Add `from_attributes=True` to ALL frozen models:

```python
model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
```

This tells Pydantic: "Accept any object with matching attributes, not just exact class matches."

#### Reference Example (ModelSemVer)

```python
class ModelSemVer(BaseModel):
    """Semantic version value object.

    Thread Safety:
        from_attributes=True allows Pydantic to accept objects with matching
        attributes even when class identity differs (e.g., in pytest-xdist
        parallel execution where model classes are imported in separate workers).
    """
    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    major: int
    minor: int
    patch: int
```

### Recommended Pattern

**For thread-safe models that use `from_attributes`:**

```python
from pydantic import BaseModel, ConfigDict

class ModelServiceMetadata(BaseModel):
    """
    Service registration metadata.

    Thread Safety:
        This model uses `from_attributes=True` for ORM compatibility.
        It is safe to use because:
        1. Source objects should be frozen/immutable when possible
        2. If mutable, ensure single-writer access during model creation
        3. The created Pydantic model is independent of the source object
    """
    model_config = ConfigDict(from_attributes=True)

    service_id: UUID
    service_name: str
    version: ModelSemVer
```

**For models that MUST be immutable:**

```python
class ModelContractFingerprint(BaseModel):
    """
    Contract fingerprint for integrity verification.

    Immutability Guarantee:
        This model is frozen (immutable) after creation to ensure:
        1. Thread-safe access from multiple readers
        2. Safe use as dictionary keys
        3. No accidental modification of computed fingerprints
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    version: ModelContractVersion
    hash_prefix: str
    full_hash: str
```

---

## Frozen Models

### When to Use `frozen=True`

**Use frozen models for:**

1. **Fingerprints and Hashes** - Integrity verification requires immutability
2. **Envelope Metadata** - Event routing must not change mid-processing
3. **Security Context** - Authentication/authorization data
4. **Configuration Snapshots** - Point-in-time configuration capture
5. **Cache Keys** - Hashable objects for dictionary keys

### Frozen Model Benefits

```python
from pydantic import BaseModel, ConfigDict

class ModelImmutableConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: int

# Benefits:
config = ModelImmutableConfig(name="test", value=42)

# 1. Thread-safe reads (no writes possible)
# Multiple threads can read without synchronization

# 2. Hashable (usable as dict key)
cache: dict[ModelImmutableConfig, str] = {}
cache[config] = "cached_result"

# 3. Prevents accidental modification
config.name = "new"  # Raises ValidationError
```

### Frozen Model Limitations

```python
# Cannot modify after creation
config.name = "new"  # ValidationError!

# Cannot use mutable defaults
class ModelBadDefault(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[str] = []  # WARNING: shared mutable default

# Correct: use default_factory
class ModelGoodDefault(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[str] = Field(default_factory=list)
```

---

## Field Definition Best Practices

### Rule: Use `Field()` only when adding metadata

`Field()` is a wrapper that should only be used when you need to add metadata, validation constraints, or aliases. For simple optional fields, use `= None` directly.

```python
# Simple optional field - no Field() needed
name: str | None = None

# Field with description - Field() justified
name: str | None = Field(default=None, description="The user's display name")

# Field with validation - Field() justified
age: int | None = Field(default=None, ge=0, le=150)

# Field with alias - Field() justified
created_at: datetime | None = Field(default=None, alias="createdAt")

# Field with multiple metadata - Field() justified
priority: int = Field(default=0, ge=0, le=100, description="Task priority")
```

### Anti-pattern: Unnecessary Field() wrapper

```python
# WRONG - Field(default=None) with no other arguments
field: str | None = Field(default=None)

# CORRECT - Simplified
field: str | None = None
```

**Why this matters:**
- `Field(default=None)` adds no value over `= None`
- Extra code means more to read and maintain
- Implies there's metadata when there isn't

### Mutable Defaults

Always use `default_factory` for mutable types to avoid shared state bugs:

```python
# CORRECT - Each instance gets its own list/dict
items: list[str] = Field(default_factory=list)
config: dict[str, Any] = Field(default_factory=dict)
tags: set[str] = Field(default_factory=set)

# WRONG - Creates shared mutable state across all instances!
items: list[str] = []
config: dict[str, Any] = {}
tags: set[str] = set()
```

**The bug with mutable defaults:**
```python
class BadModel(BaseModel):
    items: list[str] = []  # Shared across ALL instances!

m1 = BadModel()
m2 = BadModel()
m1.items.append("hello")
print(m2.items)  # ["hello"] - SURPRISE! m2 was affected!
```

### Required vs Optional Fields

```python
class ModelExample(BaseModel):
    # Required - must be provided
    id: str

    # Required with validation
    name: str = Field(..., min_length=1)

    # Optional - defaults to None
    description: str | None = None

    # Optional with default value
    priority: int = 0

    # Optional with default_factory for mutable types
    tags: list[str] = Field(default_factory=list)
```

### Field Naming Conventions

Follow these naming patterns for consistency:

| Pattern | When to Use | Example |
|---------|-------------|---------|
| `*_id` | Identifier fields | `user_id`, `session_id` |
| `*_at` | Timestamp fields | `created_at`, `updated_at` |
| `*_count` | Counter fields | `retry_count`, `error_count` |
| `is_*` | Boolean flags | `is_active`, `is_deleted` |
| `has_*` | Boolean existence | `has_errors`, `has_children` |
| `*_config` | Configuration objects | `retry_config`, `auth_config` |

---

## Validation Patterns

### Field Validators

```python
from pydantic import BaseModel, Field, field_validator

class ModelEventConfig(BaseModel):
    topic: str = Field(..., description="Event topic name")

    @field_validator("topic")
    @classmethod
    def validate_topic_prefix(cls, v: str) -> str:
        """Ensure topic uses onex.* prefix."""
        if not v.startswith("onex."):
            raise ValueError(f"Topic must start with 'onex.', got '{v}'")
        return v
```

### Model Validators

```python
from pydantic import BaseModel, model_validator

class ModelRetryConfig(BaseModel):
    max_retries: int
    retry_delay: float

    @model_validator(mode="after")
    def validate_retry_config(self) -> "ModelRetryConfig":
        """Validate retry configuration consistency."""
        if self.max_retries > 0 and self.retry_delay <= 0:
            raise ValueError("retry_delay must be > 0 when max_retries > 0")
        return self
```

### Custom Error Messages

```python
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

@field_validator("channel_name")
@classmethod
def validate_channel_name(cls, v: str) -> str:
    """Validate channel name format."""
    if not v.replace("_", "").replace(".", "").replace("-", "").isalnum():
        raise ModelOnexError(
            message=f"Channel name must be alphanumeric with ._-, got '{v}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            field="channel_name",
            provided_value=v,
        )
    return v
```

---

## Error Handling

### ONEX Error Integration

Always use `ModelOnexError` instead of generic exceptions:

```python
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class ModelContractFingerprint(BaseModel):
    @classmethod
    def from_string(cls, fingerprint_str: str) -> "ModelContractFingerprint":
        if ":" not in fingerprint_str:
            raise ModelOnexError(
                message=f"Invalid fingerprint format: '{fingerprint_str}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                expected_format="<semver>:<hash>",
            )
        # ... parsing logic
```

### Validation Error Context

Provide rich context for debugging:

```python
@model_validator(mode="after")
def validate_configuration(self) -> "ModelConfig":
    if not self.async_support and not self.sync_fallback:
        raise ModelOnexError(
            message="At least one of async_support or sync_fallback must be enabled",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            details=ModelErrorContext.with_context({
                "async_support": ModelSchemaValue.from_value(self.async_support),
                "sync_fallback": ModelSchemaValue.from_value(self.sync_fallback),
            }),
        )
    return self
```

---

## Quick Reference

### Model Configuration Checklist

| Model Type | frozen | extra | from_attributes | validate_assignment |
|------------|--------|-------|-----------------|---------------------|
| Fingerprint | `True` | `"forbid"` | `True` (required) | `True` |
| Envelope | `True` | `"forbid"` | `True` (required) | `True` |
| Value Object | `True` | `"forbid"` | `True` (required) | `True` |
| Contract | `False` | `"ignore"` | Optional | `True` |
| Internal Model | `False` | `"forbid"` | `True` | Optional |
| Metadata | `False` | `"forbid"` | `True` (ORM) | Optional |

**Note**: All frozen models MUST have `from_attributes=True` for pytest-xdist compatibility.
Internal models use `extra="forbid"` to catch unexpected fields during development.

### Safety Decision Tree

```plaintext
Need from_attributes?
├── No → Don't enable it
└── Yes → Is source object immutable?
    ├── Yes (frozen Pydantic, NamedTuple) → Safe to use
    └── No (mutable class) → Add synchronization or copy first
```

---

## Related Documentation

- **Naming Conventions**: `docs/conventions/NAMING_CONVENTIONS.md`
- **Error Handling**: `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`
- **Threading Guide**: `docs/guides/THREADING.md`
- **Contract System**: `docs/architecture/CONTRACT_SYSTEM.md`

---

**Last Updated**: 2026-01-12
**Project**: omnibase_core v0.6.6
