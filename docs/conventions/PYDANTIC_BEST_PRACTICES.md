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
| `extra="forbid"` | **Mandatory on every model** (OMN-14515) | Everything — `ignore`/`allow` are default-deny |
| `validate_assignment=True` | Re-validate on set | Mutable models with constraints |

---

## `extra` Policy: always `forbid` (OMN-14515)

**There is no `extra` decision to make. Every Pydantic model declares `extra="forbid"`.**
`extra="ignore"` and `extra="allow"` are default-deny platform-wide (operator ruling,
2026-07-12). The earlier decision matrix in this document — which routed "contracts /
external data" to `extra="ignore"` for forward-compatibility — is **superseded**.

### Why the forward-compatibility argument lost

`extra="ignore"` does not give you forward-compatibility. It gives you *silence*. When a
producer adds a field and a consumer's model does not know about it, `ignore` drops it on
every single message, with no error, no log, and no metric. The consumer keeps working and
keeps being wrong.

Four confirmed live silent-data-loss bugs came from exactly this shape — a consumer
hand-rolled a slim copy of a producer's event model with a permissive `extra`, silently
dropping fields on every event: **OMN-14490, OMN-14506, OMN-14513, OMN-14514**.
`extra="ignore"` is what converts a *loud* schema mismatch into a *silent* one.

If a model genuinely must tolerate unknown input, that is a **typed passthrough**, not a
permissive config: declare an explicit field for it.

```python
# WRONG — unknown fields vanish silently
class ModelExternalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: str

# RIGHT — unknown input is explicit, typed, and survives the round trip
class ModelExternalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    vendor_extensions: dict[str, Any] = Field(default_factory=dict)
```

### Declaring nothing is NOT neutral

**Pydantic's default for an undeclared `extra` is `"ignore"`.** A model with no
`model_config` at all is already silently dropping fields — it just never said so. That is
why the gate asserts the *positive*: an explicit, declared-or-inherited `extra="forbid"`.
**Absence is a violation.** In the platform census, the implicit-default population (858)
was *larger* than the explicit `ignore`/`allow` population (514) — a validator that greps
for the string `extra="ignore"` would have missed the majority of the problem.

```python
# VIOLATION — declares nothing, so Pydantic silently applies extra="ignore"
class ModelThing(BaseModel):
    field: str

# COMPLIANT — explicit
class ModelThing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str

# COMPLIANT — inherited from a compliant base (do not redundantly redeclare)
class ModelThing(ModelStrictBase):
    field: str
```

### Enforcement

`omnibase_core.validators.pydantic_extra_forbid` (OMN-14515) is wired as a **CI gate**
(inside the required Quality Gate rollup) and a **pre-commit hook**. It resolves the
effective `extra` through the MRO by reading the real `cls.model_config`, so inheriting
`forbid` from a base counts as compliant. It fails a NEW model outright, and fails a
BASELINED model whose body you just edited — touching a broken model is your chance to fix
it. The frozen baseline may only shrink. The single sanctioned suppression is an
**expiring waiver** keyed to an open ticket + PR (`extra_forbid_waivers.yaml`); an expired
waiver is a hard failure, by design, so it cannot decay into an allowlist.

The one exemption is `RootModel`, which Pydantic itself refuses to let you configure with
`extra`.

The pre-existing violations are not being burned down by hand — the RSD canonical rewrite
regenerates the corpus with `extra="forbid"` emitted by construction. This gate exists so
that the *next* hand-written model cannot be born broken.

---

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

#### Reference Example (immutable value object)

```python
class ModelSemVer(BaseModel):
    """Semantic version value object.

    Thread Safety:
        from_attributes=True allows Pydantic to accept objects with matching
        attributes even when class identity differs (e.g., in pytest-xdist
        parallel execution where model classes are imported in separate workers).
    """
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    major: int
    minor: int
    patch: int
```

> The live `ModelSemVer` still carries `extra="ignore"` and is in the OMN-14515 baseline
> (708 consumers — the highest-blast-radius entry in the census; it needs a canary, not a
> drive-by edit). The example above shows the target shape, not the current source.

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
