# Union Remediation Quick Reference Card

**Last Updated**: 2025-10-28
**Full Plan**: `docs/research/UNION_REMEDIATION_PLAN.md`

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total Invalid Unions** | 232 |
| **Primitive Soup** | 186 (80.2%) |
| **Complex Union** | 42 (18.1%) |
| **Any Contaminated** | 4 (1.7%) |
| **Estimated Effort** | ~68 hours (~2 weeks) |
| **Target** | 0 invalid unions |

---

## Primary Solution: ModelSchemaValue

**Use For**: 80% of all invalid unions (186 instances)

### Import
```python
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
```text

### Quick Replace Pattern

❌ **Before (Invalid)**:
```python
field_value: Union[str, int, float, bool, list, dict, None]
```text

✅ **After (Valid)**:
```python
field_value: ModelSchemaValue
```text

### Creation
```python
# From any value
value = ModelSchemaValue.from_value(raw_value)

# Explicit factories
value = ModelSchemaValue.create_string("text")
value = ModelSchemaValue.create_number(42)
value = ModelSchemaValue.create_boolean(True)
value = ModelSchemaValue.create_array([1, 2, 3])
value = ModelSchemaValue.create_object({"key": "value"})
value = ModelSchemaValue.create_null()
```text

### Type-Safe Access
```python
if value.is_string():
    text = value.get_string()
elif value.is_number():
    num = value.get_number()
elif value.is_boolean():
    flag = value.get_boolean()
elif value.is_array():
    items = value.get_array()
elif value.is_object():
    obj = value.get_object()
```python

### Conversion
```python
# To Python value
python_value = value.to_value()

# Serialization (automatic in Pydantic)
data = model.model_dump()
```python

---

## Alternative: ModelFlexibleValue

**Use For**: Values needing source tracking or validation state

### Import
```python
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
```text

### Creation
```python
# Auto-detect type
value = ModelFlexibleValue.from_any(raw_value, source="user_input")

# Explicit factories
value = ModelFlexibleValue.from_string("text", source="config")
value = ModelFlexibleValue.from_integer(42)
value = ModelFlexibleValue.from_dict({"key": "value"})
```python

### Features
- Enum-based type discriminator
- Source tracking
- Validation state (`is_validated`)
- Type checking: `is_primitive()`, `is_collection()`

---

## Discriminated Unions

**Use For**: Fixed set of known types with discriminator field

### Pattern
```python
from typing import Annotated, Literal
from pydantic import Field

class ModelOptionA(BaseModel):
    option_type: Literal["a"] = "a"
    value_a: str

class ModelOptionB(BaseModel):
    option_type: Literal["b"] = "b"
    value_b: int

OptionUnion = Annotated[
    ModelOptionA | ModelOptionB,
    Field(discriminator="option_type")
]
```bash

---

## Top Priority Fixes

### 1. Security Models (94 unions) - CRITICAL
**Files**: `model_masked_data*.py`, `model_security_policy_data.py`
**Pattern**: `Union[None, bool, dict, float, int, list, str]`
**Solution**: Replace with `ModelSchemaValue`
**Effort**: 8 hours

### 2. Core Models (59 unions) - HIGH
**Files**: `model_custom_fields.py`, `model_argument_value.py`, `model_extension_data.py`
**Pattern**: Various primitive soups
**Solution**: Replace with `ModelSchemaValue`
**Effort**: 4 hours

### 3. Discovery Models (32 unions) - MEDIUM
**Files**: `model_tool_parameters.py`, `model_toolparameters.py`
**Pattern**: Parameter value unions
**Solution**: Replace with `ModelSchemaValue`
**Effort**: 3 hours

---

## Validation Commands

### Check Invalid Unions
```bash
poetry run python scripts/validation/validate-union-usage.py --allow-invalid 0
```python

### Run Tests
```bash
poetry run pytest tests/ -xvs
```bash

### Type Check
```bash
poetry run mypy src/omnibase_core/
```text

### Full Quality Check
```bash
pre-commit run --all-files
```python

---

## Implementation Phases

### Phase 1: Primitive Soup (Week 1)
- Replace 186 primitive soup unions with `ModelSchemaValue`
- Focus: Security, Discovery, Core models
- Effort: ~17 hours

### Phase 2: Complex Unions (Week 2)
- Refine discriminated unions
- Add explicit discriminators
- Effort: ~17 hours

### Phase 3: Any Contamination (Week 3)
- Eliminate 4 any-contaminated unions
- Critical cleanup
- Effort: ~6 hours

### Phase 4: Validation (Week 3-4)
- Testing, documentation, validation
- Effort: ~17 hours

---

## Migration Example

**Before**:
```python
class ModelMaskedData(BaseModel):
    original_value: Union[None, bool, dict, float, int, list, str]
    masked_value: Union[None, bool, dict, float, int, list, str]
```python

**After**:
```python
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

class ModelMaskedData(BaseModel):
    original_value: ModelSchemaValue
    masked_value: ModelSchemaValue

    def get_original_as_string(self) -> str:
        if self.original_value.is_string():
            return self.original_value.get_string()
        return str(self.original_value.to_value())
```python

**Migration Helper**:
```python
def migrate_to_schema_value(old_value: Any) -> ModelSchemaValue:
    """Migrate old union values to ModelSchemaValue."""
    return ModelSchemaValue.from_value(old_value)
```yaml

---

## Common Pitfalls

❌ **Don't**: Create new primitive soup unions
```python
# WRONG
new_field: Union[str, int, bool, float]
```text

❌ **Don't**: Use Any in unions
```python
# WRONG
field: Union[str, Any, dict]
```text

❌ **Don't**: Skip discriminator in multi-type unions
```python
# WRONG (if >5 types or semantically different)
field: Union[TypeA, TypeB, TypeC, TypeD, TypeE]
```text

✅ **Do**: Use ModelSchemaValue for mixed primitives
```python
# CORRECT
field: ModelSchemaValue
```text

✅ **Do**: Use discriminated unions for fixed types
```python
# CORRECT
field: Annotated[TypeA | TypeB, Field(discriminator="type")]
```text

✅ **Do**: Use Optional for nullable single types
```python
# CORRECT
field: str | None  # or Optional[str]
```python

---

## Success Criteria

- [ ] Zero invalid unions: `validate-union-usage.py --allow-invalid 0` passes
- [ ] All tests passing: `pytest tests/` passes
- [ ] Zero mypy errors: `mypy src/omnibase_core/` passes
- [ ] Coverage ≥60%: `pytest --cov` meets threshold
- [ ] Pre-commit hooks pass: `pre-commit run --all-files` passes

---

## Resources

- **Full Plan**: `docs/research/UNION_REMEDIATION_PLAN.md` (35 pages)
- **ModelSchemaValue**: `src/omnibase_core/models/common/model_schema_value.py`
- **ModelFlexibleValue**: `src/omnibase_core/models/common/model_flexible_value.py`
- **Validation Script**: `scripts/validation/validate-union-usage.py`
- **ONEX Guide**: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md`

---

## Quick Decision Tree

```text
Union type needed?
│
├─ Single type + None? → Use Optional[T] or T | None
│
├─ Multiple primitives (str, int, float, bool, list, dict)?
│  └─ → Use ModelSchemaValue
│
├─ Fixed set of known models with discriminator?
│  └─ → Use Annotated[Model1 | Model2, Field(discriminator="field")]
│
├─ Need source tracking or validation state?
│  └─ → Use ModelFlexibleValue
│
└─ Complex custom pattern?
   └─ → Design new discriminated union model
```bash

---

**Ready to Start?** Begin with Phase 1: Security models (94 unions, highest impact)

**Questions?** See full plan: `docs/research/UNION_REMEDIATION_PLAN.md`
