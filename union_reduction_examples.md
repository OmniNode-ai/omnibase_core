# Union Type Reduction Examples and Strategy

## Analysis Summary

Based on comprehensive codebase analysis, we have identified **291 total Union/Optional usages** (58 Union + 233 Optional) across 249 files, not the 6,692 initially mentioned. This is a much more manageable number.

## Pattern Distribution

1. **Simple Optional**: 233 usages (80% of total)
2. **Typing Imports**: 111 usages
3. **Complex Union**: 35 usages (4+ types)
4. **Dict[str, Union[...]]**: 26 usages
5. **Primitive Union**: 22 usages (str|int|float|bool)
6. **Model Union**: 12 usages

## Top Files Requiring Attention

1. `node_gateway.py` - 26 unions (highest)
2. `node_effect.py` - 15 unions
3. `model_quality_standards.py` - 13 unions
4. `model_introspection_subcontract.py` - 12 unions
5. `protocol_service_discovery.py` - 11 unions

## Refactoring Examples

### 1. Dict[str, Union[str, int, float, bool]] → Pydantic Model

**Before:**
```python
# In node_gateway.py
metadata: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
    default_factory=dict
)
```

**After:**
```python
from pydantic import BaseModel

class MetadataModel(BaseModel):
    """Strongly typed metadata model."""
    service_name: Optional[str] = None
    timeout_ms: Optional[int] = None
    retry_count: Optional[int] = None
    priority_score: Optional[float] = None
    enabled: Optional[bool] = None
    # Add other known metadata fields based on usage analysis

# Usage in main model
metadata: Optional[MetadataModel] = Field(default=None)
```

### 2. Primitive Unions → Discriminated Union

**Before:**
```python
# In node_effect.py  
result: Union[str, int, float, bool, Dict, list]
```

**After:**
```python
from typing import Literal
from pydantic import BaseModel, Field

class StringResult(BaseModel):
    type: Literal["string"] = "string"
    value: str

class NumericResult(BaseModel):
    type: Literal["numeric"] = "numeric"
    value: Union[int, float]

class BooleanResult(BaseModel):
    type: Literal["boolean"] = "boolean"
    value: bool

class ObjectResult(BaseModel):
    type: Literal["object"] = "object"
    value: Dict[str, Any]

class ListResult(BaseModel):
    type: Literal["list"] = "list"
    value: List[Any]

ResultType = Union[
    StringResult,
    NumericResult,
    BooleanResult,
    ObjectResult,
    ListResult
]

# Usage
result: ResultType
```

### 3. Optional Fields → Required with Defaults

**Before:**
```python
# In model_quality_standards.py
code_coverage_minimum: Optional[float] = Field(default=None)
max_complexity_score: Optional[int] = Field(default=None)
documentation_required: Optional[bool] = Field(default=None)
```

**After:**
```python
# Use specific defaults instead of None
code_coverage_minimum: float = Field(default=80.0, ge=0, le=100)
max_complexity_score: int = Field(default=10, ge=1, le=50)  
documentation_required: bool = Field(default=True)
```

### 4. Protocol Method Returns → Strongly Typed Models

**Before:**
```python
# In protocol_service_discovery.py
async def discover_services(
    self, service_name: str, healthy_only: bool = True
) -> List[Dict[str, Union[str, int, float, bool]]]:
```

**After:**
```python
class ServiceInstance(BaseModel):
    """Strongly typed service instance model."""
    service_id: str
    host: str
    port: int
    health_status: bool
    last_check: float  # timestamp
    tags: List[str] = Field(default_factory=list)
    weight: float = Field(default=1.0)

async def discover_services(
    self, service_name: str, healthy_only: bool = True
) -> List[ServiceInstance]:
```

## Reduction Strategy

### Phase 1: Low-Risk Refactoring (Target: 80% reduction)

1. **Replace Dict[str, Union[...]] patterns** (26 instances)
   - Create specific Pydantic models for metadata, configuration, results
   - Estimated reduction: 26 unions → 0 unions

2. **Convert Optional fields with meaningful defaults** (150+ instances)
   - Use domain-specific defaults instead of None
   - Estimated reduction: 150 optionals → 75 optionals

3. **Replace primitive unions with discriminated unions** (22 instances)
   - Use Literal types for type discrimination
   - Estimated reduction: 22 unions → 22 discriminated models (better type safety)

### Phase 2: Protocol and Interface Refactoring (Target: 15% additional reduction)

1. **Strengthen protocol return types** (12 instances)
   - Replace generic Dict returns with specific models
   - Estimated reduction: 12 unions → 0 unions

2. **Model unions → Discriminated unions** (12 instances)
   - Use Pydantic discriminated unions for related models
   - Estimated reduction: 12 unions → 12 discriminated models

### Phase 3: Complex Union Simplification (Target: 5% additional reduction)

1. **Simplify complex unions** (35 instances)
   - Break down into smaller, more focused types
   - Use composition over complex unions
   - Estimated reduction: 35 unions → 10 unions

## Expected Outcomes

- **Current State**: 291 Union/Optional usages
- **After Phase 1**: ~58 remaining (80% reduction)
- **After Phase 2**: ~44 remaining (85% reduction)
- **After Phase 3**: ~41 remaining (86% reduction)

## Benefits of This Approach

1. **Better Type Safety**: Compile-time validation instead of runtime Union checking
2. **Enhanced IDE Support**: Better autocomplete and error detection
3. **Clearer Intent**: Explicit models communicate purpose better than generic unions
4. **Easier Testing**: Specific models are easier to mock and validate
5. **Better Documentation**: Pydantic models serve as living documentation

## Implementation Priority

1. **Start with `node_gateway.py` and `node_effect.py`** (high impact files)
2. **Focus on Dict[str, Union[...]] patterns first** (immediate type safety gain)
3. **Gradual migration of Optional fields** (low risk, high impact)
4. **Protocol refactoring last** (requires interface coordination)

## Validation Strategy

1. **Run existing tests** after each refactoring
2. **Add new tests** for Pydantic model validation
3. **Use mypy** for static type checking validation
4. **Performance testing** to ensure no degradation
