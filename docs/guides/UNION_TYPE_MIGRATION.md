# Union Type Migration Guide

## Overview

This guide documents the centralized JSON type aliases introduced in PR #163 to reduce union type tech debt throughout the omnibase_core codebase.

**Key Takeaway**: Use centralized type aliases from `omnibase_core.types.json_types` instead of inline union types to improve code maintainability, consistency, and type safety.

## The Problem: "Primitive Soup" Anti-Pattern

### What Is Primitive Soup?

The "primitive soup" anti-pattern occurs when inline union types like `str | int | float | bool | None` are scattered throughout a codebase. This creates several problems:

1. **Inconsistency**: Different files may define slightly different unions for the same concept
2. **Maintenance Burden**: Changes require updating every occurrence
3. **Unclear Intent**: `str | int | float | bool` doesn't communicate *why* these types are grouped
4. **Type Checker Confusion**: Minor variations cause false positives in type checking
5. **Documentation Drift**: Inline types lack documentation about their purpose

### Example of the Problem

```python
# File A: model_config.py
def get_setting(key: str) -> str | int | float | bool | None:
    ...

# File B: model_metadata.py
def get_metadata(key: str) -> str | int | bool | float | None:  # Same types, different order
    ...

# File C: model_params.py
def get_param(key: str) -> str | int | float | bool:  # Missing None - intentional or bug?
    ...

# File D: model_data.py
def process(data: str | int | float | bool | list[Any] | dict[str, Any] | None):  # Full JSON
    ...
```

Each file reinvents the same concept with subtle variations, making the codebase harder to understand and maintain.

## The Solution: Centralized Type Aliases

PR #163 introduces centralized type aliases in `omnibase_core.types.json_types` that provide:

- **Semantic naming**: `JsonPrimitive` is clearer than `str | int | float | bool | None`
- **Single source of truth**: One location to update when requirements change
- **Documentation**: Each alias has docstrings explaining its purpose and usage
- **Consistency**: All code uses the same definition

## Available Type Aliases

### Import Statement

```python
from omnibase_core.types.json_types import (
    JsonPrimitive,
    PrimitiveValue,
    JsonValue,
    JsonType,
    PrimitiveContainer,
    ToolParameterValue,
)
```

### Type Alias Reference

| Alias | Definition | Nullable | Containers | Use Case |
|-------|------------|----------|------------|----------|
| `JsonPrimitive` | `str \| int \| float \| bool \| None` | Yes | No | JSON scalar values |
| `PrimitiveValue` | `str \| int \| float \| bool` | No | No | Non-nullable scalars |
| `JsonValue` | `str \| int \| float \| bool \| list[Any] \| dict[str, Any] \| None` | Yes | Yes (Any) | General JSON data |
| `JsonType` | Recursive `dict[str, "JsonType"] \| list["JsonType"] \| ...` | Yes | Yes (typed) | Full JSON with type checking |
| `PrimitiveContainer` | `PrimitiveValue \| list[PrimitiveValue] \| dict[str, PrimitiveValue]` | No | Yes (flat) | Simple configs |
| `ToolParameterValue` | `str \| int \| float \| bool \| list[str] \| dict[str, str]` | No | Yes (strings) | API/CLI parameters |

### Detailed Type Alias Documentation

#### JsonPrimitive

Basic JSON scalar values including null.

```python
# Definition
JsonPrimitive = str | int | float | bool | None

# Use cases
- JSON property values
- Configuration settings that may be null
- Optional metadata fields
- Default/fallback values

# Examples
value: JsonPrimitive = "hello"
value: JsonPrimitive = 42
value: JsonPrimitive = 3.14
value: JsonPrimitive = True
value: JsonPrimitive = None
```

#### PrimitiveValue

Non-nullable primitive values. Use when `None` is not a valid value.

```python
# Definition
PrimitiveValue = str | int | float | bool

# Use cases
- Required configuration fields
- Non-optional function parameters
- Values that must have meaningful content
- Dictionary values where None would be invalid

# Examples
setting: PrimitiveValue = "production"  # Valid
setting: PrimitiveValue = None          # Type error!

def require_value(val: PrimitiveValue) -> str:
    return str(val)  # Always has a value
```

#### JsonValue

Any JSON-compatible value including containers. Uses `Any` for container contents.

```python
# Definition
JsonValue = str | int | float | bool | list[Any] | dict[str, Any] | None

# Use cases
- General JSON data handling
- API request/response bodies
- Configuration file parsing
- Data transformation pipelines

# Examples
data: JsonValue = {"users": [{"name": "Alice", "age": 30}]}
data: JsonValue = [1, 2, 3, "mixed", True]
data: JsonValue = "simple string"
data: JsonValue = None

# Note: Container contents are not type-checked
# Use JsonType for full recursive type checking
```

#### JsonType

Full recursive JSON structure with proper nested type definitions.

```python
# Definition
JsonType = dict[str, "JsonType"] | list["JsonType"] | str | int | float | bool | None

# Use cases
- JSON schema validation contexts
- Deep nested configuration parsing
- Full type coverage for JSON documents
- When type checker must validate nested structure

# Examples
config: JsonType = {
    "database": {
        "hosts": ["host1", "host2"],
        "settings": {
            "timeout": 30,
            "retry": True,
            "options": {
                "ssl": True,
                "verify": False
            }
        }
    }
}

# Type checker validates nested structure
```

#### PrimitiveContainer

Primitives or flat collections of primitives. No deep nesting, no `None` values.

```python
# Definition
PrimitiveContainer = PrimitiveValue | list[PrimitiveValue] | dict[str, PrimitiveValue]

# Use cases
- Simple configuration values
- Flat metadata structures
- Parameters that don't need deep nesting
- Environment variable representations

# Examples
settings: PrimitiveContainer = {"timeout": 30, "enabled": True}
tags: PrimitiveContainer = ["prod", "critical", "v2"]
count: PrimitiveContainer = 42

# Note: None is EXCLUDED (uses PrimitiveValue, not JsonPrimitive)
# This is intentional - use JsonValue if you need nullable containers
```

#### ToolParameterValue

Constrained types for tool/API parameters with string-only containers.

```python
# Definition
ToolParameterValue = str | int | float | bool | list[str] | dict[str, str]

# Use cases
- MCP tool parameters
- CLI argument values
- API request parameters
- HTTP headers and query parameters

# Examples
params: dict[str, ToolParameterValue] = {
    "url": "https://example.com",
    "timeout": 30,
    "retries": 3,
    "verbose": True,
    "headers": {"Authorization": "Bearer token", "Accept": "application/json"},
    "tags": ["api", "external", "v2"]
}

# Note: More constrained than JsonValue
# - No None (parameters should be explicit)
# - No arbitrary nested structures
# - List/dict values are strings only
```

## Decision Tree: Choosing the Right Type Alias

Use this decision tree to select the appropriate type alias:

```text
Is the value JSON-compatible?
|
+-- NO --> Keep specific union or use Any with suppression comment
|
+-- YES --> Is it a scalar only (no containers)?
    |
    +-- YES --> Can it be None?
    |   |
    |   +-- YES --> Use JsonPrimitive
    |   |
    |   +-- NO --> Use PrimitiveValue
    |
    +-- NO --> Is it for tool/API parameters?
        |
        +-- YES --> Use ToolParameterValue
        |
        +-- NO --> Is it flat (no nested containers)?
            |
            +-- YES --> Does it allow None?
            |   |
            |   +-- YES --> Use JsonValue
            |   |
            |   +-- NO --> Use PrimitiveContainer
            |
            +-- NO --> Need recursive type checking?
                |
                +-- YES --> Use JsonType
                |
                +-- NO --> Use JsonValue
```

### Quick Reference Table

| Scenario | Recommended Type |
|----------|------------------|
| JSON scalar, may be null | `JsonPrimitive` |
| JSON scalar, must have value | `PrimitiveValue` |
| Any JSON data, simple handling | `JsonValue` |
| Deeply nested JSON, need type safety | `JsonType` |
| Flat config with primitives | `PrimitiveContainer` |
| CLI args, API params, HTTP headers | `ToolParameterValue` |

## Migration Steps

### Step 1: Identify Inline Unions

Search for patterns that match the type aliases:

```bash
# Find potential JsonPrimitive candidates
poetry run grep -rn "str | int | float | bool | None" src/

# Find potential JsonValue candidates
poetry run grep -rn "list\[Any\] | dict\[str, Any\]" src/

# Find primitive unions without None
poetry run grep -rn "str | int | float | bool[^|]" src/
```

Or use the validation script:

```bash
poetry run python scripts/validation/validate-union-usage.py --report
```

### Step 2: Analyze Each Occurrence

For each inline union found, determine:

1. **Is it JSON-compatible?** If not, it may need a domain-specific type
2. **Does it allow None?** Determines `JsonPrimitive` vs `PrimitiveValue`
3. **Does it include containers?** Determines scalar vs container types
4. **What is the semantic meaning?** May warrant a new domain-specific alias

### Step 3: Replace with Type Alias

```python
# Before
def get_config(key: str) -> str | int | float | bool | None:
    ...

# After
from omnibase_core.types.json_types import JsonPrimitive

def get_config(key: str) -> JsonPrimitive:
    ...
```

### Step 4: Validate Changes

```bash
# Run type checker
poetry run mypy src/omnibase_core/

# Run tests
poetry run pytest tests/unit/

# Run union validation
poetry run python scripts/validation/validate-union-usage.py
```

## Suppression Comments: When and How

### When to Use Suppression Comments

Use `# union-ok:` comments when an inline union is intentional and should not be replaced:

1. **Domain-specific unions** that don't match the JSON aliases
2. **Discriminated unions** with Pydantic's `Discriminator` pattern
3. **Factory patterns** returning multiple model types
4. **Intentional type restrictions** that exclude certain types

### Suppression Comment Format

```python
# union-ok: <reason_code> - <explanation>
```

### Recognized Reason Codes

| Code | Meaning | Example |
|------|---------|---------|
| `json_value` | Standard JSON types for serialization | Protocol return types |
| `discriminated_union` | Has companion discriminator field | `Annotated[..., Discriminator]` |
| `domain_specific` | Domain excludes certain types | Security types without float |
| `nested_schema` | Complex JSON Schema representation | OpenAPI schemas |
| `service_metadata` | Service discovery metadata | Node action metadata |
| `condition_value` | Domain-specific condition types | Permission conditions |
| `mask_value` | Domain-specific masking types | Secret masking |
| `permission_primitive` | Permission attribute types | RBAC attributes |

### Examples of Valid Suppression

```python
# Domain-specific type that excludes float
class ModelPermissionContext(BaseModel):
    # union-ok: permission_primitive - domain excludes float for permission attribute types
    attributes: dict[str, str | int | bool]

# Discriminated union with type safety
class ModelFilterUnion(BaseModel):
    # union-ok: discriminated_union - companion filter_type field provides type safety
    filter: Annotated[
        ModelEqualsFilter | ModelRangeFilter | ModelContainsFilter,
        Field(discriminator="filter_type")
    ]

# Factory pattern returning multiple types
# union-ok: Factory pattern legitimately needs union of all action payload types
ActionPayloadType = (
    ModelCreatePayload |
    ModelUpdatePayload |
    ModelDeletePayload
)
```

### Invalid Uses of Suppression

Do NOT use suppression comments for:

```python
# BAD: This is just JsonPrimitive
# union-ok: legacy_code - we've always done it this way  # WRONG!
def get_value() -> str | int | float | bool | None:
    ...

# BAD: This is exactly JsonValue
# union-ok: too_hard_to_change - lots of callers  # WRONG!
ConfigValue = str | int | float | bool | list[Any] | dict[str, Any] | None
```

## Best Practices

### Do

1. **Use the most specific type alias** that fits your use case
2. **Document why** if you choose a different alias than the decision tree suggests
3. **Add suppression comments** with clear explanations for legitimate inline unions
4. **Run validation** after migrations to ensure consistency
5. **Update tests** if changing function signatures

### Don't

1. **Don't create new aliases** unless existing ones truly don't fit
2. **Don't suppress** just to avoid migration work
3. **Don't mix inline unions** with aliases in the same module
4. **Don't ignore type checker errors** - they often reveal real issues

## Validation Script

The union usage validation script helps maintain consistency:

```bash
# Check for unaddressed inline unions
poetry run python scripts/validation/validate-union-usage.py

# Generate detailed report
poetry run python scripts/validation/validate-union-usage.py --report

# Check specific file
poetry run python scripts/validation/validate-union-usage.py --file src/omnibase_core/models/config.py
```

The script:
- Detects inline unions that could use type aliases
- Recognizes valid `# union-ok:` suppression comments
- Reports statistics on alias usage vs inline unions
- Integrates with CI/CD for automated checking

## Migration Examples

### Example 1: Simple Scalar Migration

```python
# Before
class ModelConfig(BaseModel):
    timeout: int | float
    name: str | None
    enabled: bool
    value: str | int | float | bool | None

# After
from omnibase_core.types.json_types import JsonPrimitive

class ModelConfig(BaseModel):
    timeout: int | float  # Keep specific - we want numeric only
    name: str | None      # Keep specific - we want string only
    enabled: bool         # Keep specific - boolean only
    value: JsonPrimitive  # Use alias - any JSON scalar
```

### Example 2: Container Migration

```python
# Before
def process_data(
    data: str | int | float | bool | list[Any] | dict[str, Any] | None
) -> dict[str, str | int | float | bool | list[Any] | dict[str, Any] | None]:
    ...

# After
from omnibase_core.types.json_types import JsonValue

def process_data(data: JsonValue) -> dict[str, JsonValue]:
    ...
```

### Example 3: Tool Parameters Migration

```python
# Before
def execute_tool(
    params: dict[str, str | int | float | bool | list[str] | dict[str, str]]
) -> None:
    ...

# After
from omnibase_core.types.json_types import ToolParameterValue

def execute_tool(params: dict[str, ToolParameterValue]) -> None:
    ...
```

### Example 4: Keeping Domain-Specific Union

```python
# Before (with implicit domain knowledge)
class ModelPermission(BaseModel):
    value: str | int | bool  # No float - permission values are discrete

# After (with explicit documentation)
class ModelPermission(BaseModel):
    # union-ok: permission_primitive - domain excludes float for discrete permission values
    value: str | int | bool
```

## Related Documentation

- [json_types.py](../../src/omnibase_core/types/json_types.py) - Type alias definitions
- [validate-union-usage.py](../../scripts/validation/validate-union-usage.py) - Validation script
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node patterns

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Initial guide for PR #163 |

---

**Last Updated**: 2025-12-11
**Related PR**: #163 - Reduce union type tech debt with centralized JSON type aliases
