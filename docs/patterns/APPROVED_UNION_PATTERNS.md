# Approved Union Patterns for ONEX Development

## Overview

This document defines the approved union patterns for ONEX projects. Our codebase currently uses **15 unions across 292 files**, all following these approved patterns.

## ✅ Approved Patterns

### Pattern 1: Modern Optional Fields
**Use:** Optional fields that may be None
**Syntax:** `T | None` (Python 3.10+ modern syntax)

```python
# ✅ GOOD: Modern optional syntax
user_id: UUID | None = Field(default=None, description="Optional user reference")
error_message: str | None = Field(default=None)
metadata: dict[str, str] | None = None

# ✅ GOOD: Function parameters
def process_data(data: str, config: dict[str, Any] | None = None) -> None:
    pass

# ✅ GOOD: Return types
def find_user(user_id: UUID) -> User | None:
    pass
```python

### Pattern 2: Discriminated Unions with Type Safety
**Use:** When you need to represent multiple possible data structures
**Requirement:** Must have a discriminator field (usually with Literal types)

```python
# ✅ GOOD: Discriminated union with value_type discriminator
class ModelSchemaValue(BaseModel):
    value_type: Literal["string", "number", "boolean", "null", "array", "object"]
    string_value: str | None = None
    number_value: ModelNumericValue | None = None
    boolean_value: bool | None = None
    null_value: bool | None = None
    array_value: list["ModelSchemaValue"] | None = None
    object_value: dict[str, "ModelSchemaValue"] | None = None

# ✅ GOOD: Migration conflict union with discriminator
class ModelMigrationConflictUnion(BaseModel):
    conflict_type: Literal["name_conflict", "exact_duplicate"]
    source_signature: str | None = None
    spi_signature: str | None = None
    # ... other discriminated fields
```python

### Pattern 3: Generic Result/Error Patterns
**Use:** For error handling and result types
**Requirement:** Use with generic type parameters

```python
# ✅ GOOD: Generic result patterns
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E')

class Result(Generic[T, E]):
    # Implementation for Result[Success, Error] patterns
    pass

# ✅ GOOD: Function signatures using Result patterns
def safe_operation() -> Result[User, ValidationError]:
    pass
```python

## ❌ Anti-Patterns (Blocked by Validation)

### Anti-Pattern 1: Primitive Overload
```python
# ❌ BAD: Too many primitive types
Union[str, int, bool, float]  # Replace with discriminated union

# ✅ GOOD: Replace with discriminated union
class ModelPrimitiveValue(BaseModel):
    value_type: Literal["string", "integer", "boolean", "float"]
    string_value: str | None = None
    integer_value: int | None = None
    boolean_value: bool | None = None
    float_value: float | None = None
```python

### Anti-Pattern 2: Mixed Primitive/Complex
```python
# ❌ BAD: Mixed primitive and complex types
Union[str, int, dict, list]  # Replace with flexible value model

# ✅ GOOD: Replace with structured model
class ModelFlexibleValue(BaseModel):
    value_type: Literal["primitive", "collection", "mapping"]
    primitive_value: str | int | None = None
    collection_value: list[Any] | None = None
    mapping_value: dict[str, Any] | None = None
```python

### Anti-Pattern 3: Lazy Union Usage
```python
# ❌ BAD: Lazy union without structure
Union[str, dict, list, Any]  # Too generic, no type safety

# ✅ GOOD: Use specific types or discriminated unions
class ModelDataValue(BaseModel):
    data_type: Literal["text", "structured", "collection"]
    text_data: str | None = None
    structured_data: dict[str, str] | None = None
    collection_data: list[str] | None = None
```text

### Anti-Pattern 4: Old Optional Syntax
```python
# ❌ BAD: Old Union syntax for optional
Union[str, None]  # Use modern syntax

# ✅ GOOD: Modern optional syntax
str | None
```python

## Validation Rules

Our pre-commit hook enforces these patterns with:
- **Max unions allowed:** 20 (current usage: 15)
- **Complexity threshold:** 3+ types triggers review
- **Pattern detection:** Automatically suggests discriminated union replacements

## How to Handle Union Violations

### Step 1: Identify the Union Purpose
- **Optional field?** → Use `T | None`
- **Multiple data types?** → Create discriminated union
- **Error handling?** → Use Result[T, E] pattern

### Step 2: Create Discriminated Union Model
```python
# Template for discriminated union
class ModelYourDataUnion(BaseModel):
    data_type: Literal["type1", "type2", "type3"]  # Discriminator
    type1_field: Type1 | None = None
    type2_field: Type2 | None = None
    type3_field: Type3 | None = None

    @field_validator('data_type')
    @classmethod
    def validate_discriminator_consistency(cls, v, info):
        # Add validation logic to ensure only appropriate field is set
        return v
```python

### Step 3: Migrate Existing Usage
1. Replace union type annotations with new model
2. Update code to use discriminated access
3. Add proper validation
4. Test thoroughly

## Examples from Codebase

### ModelSchemaValue (Schema Value Handling)
```python
# Replaces: Union[str, int, float, bool, dict, list, None]
class ModelSchemaValue(BaseModel):
    value_type: str  # Discriminator
    string_value: str | None = None
    number_value: ModelNumericValue | None = None
    # ... other typed fields
```python

### ModelMigrationConflictUnion (Conflict Resolution)
```python
# Replaces: Union[TypedDictMigrationDuplicateConflictDict, TypedDictMigrationNameConflictDict]
class ModelMigrationConflictUnion(BaseModel):
    conflict_type: Literal["name_conflict", "exact_duplicate"]  # Discriminator
    # ... discriminated fields based on conflict_type
```yaml

## Best Practices

1. **Always prefer discriminated unions** over raw Union types
2. **Use Literal types** for discriminator fields when possible
3. **Validate discriminator consistency** with field validators
4. **Document the purpose** of each discriminated union clearly
5. **Test all discriminator branches** thoroughly
6. **Use modern `T | None` syntax** instead of `Optional[T]` or `Union[T, None]`

## Current Statistics

- **Total unions:** 15 across 292 files
- **Pattern distribution:**
  - Modern optional (`T | None`): ~12 unions
  - Discriminated unions: ~3 unions
  - Problematic patterns: 0 unions
- **Validation limit:** 20 unions maximum
- **Compliance rate:** 100%

This demonstrates excellent union hygiene across the codebase!
