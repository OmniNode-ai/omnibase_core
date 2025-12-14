# Pydantic Best Practices for ONEX

This document covers Pydantic configuration patterns, safety considerations, and best practices for ONEX models.

---

## Table of Contents

1. [Model Configuration](#model-configuration)
2. [from_attributes Safety](#from_attributes-safety)
3. [Frozen Models](#frozen-models)
4. [Validation Patterns](#validation-patterns)
5. [Error Handling](#error-handling)

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
| Fingerprint | `True` | `"forbid"` | Optional | `True` |
| Envelope | `True` | `"forbid"` | Optional | `True` |
| Contract | `False` | `"ignore"` | No | `True` |
| Config | `False` | `"forbid"` | Optional | `True` |
| Metadata | `False` | (default) | `True` (ORM) | (default) |

**Note**: Metadata models use `from_attributes=True` for ORM compatibility. Other options
use Pydantic defaults unless specific validation behavior is required.

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

**Last Updated**: 2025-12-14
**Project**: omnibase_core v0.3.6
