# Contract System - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

The ONEX contract system defines typed interfaces for all node operations using Pydantic models.

## Contract Architecture

### Base Contract

All contracts inherit from `ModelContractBase`:

```python
class ModelContractBase(BaseModel):
    """Base contract for all ONEX operations."""
    name: str
    version: str
    description: Optional[str]
    node_type: EnumNodeType
```

### Specialized Contracts

Each node type has specific contracts:

```python
# EFFECT contract
class ModelContractEffect(ModelContractBase):
    operation_type: str
    target: str
    parameters: dict

# COMPUTE contract
class ModelContractCompute(ModelContractBase):
    input_data: dict
    cache_config: Optional[ModelCacheConfig]

# REDUCER contract
class ModelContractReducer(ModelContractBase):
    state_key: str
    aggregation_config: dict

# ORCHESTRATOR contract
class ModelContractOrchestrator(ModelContractBase):
    workflow_definition: dict
    execution_mode: str
```

## Subcontracts

Complex operations use subcontracts for specialized behaviors:

### Subcontract Types

1. **FSM Subcontract** - Finite state machines
2. **Event Type Subcontract** - Event definitions
3. **Aggregation Subcontract** - Data aggregation rules
4. **State Management Subcontract** - State handling
5. **Routing Subcontract** - Message routing
6. **Caching Subcontract** - Cache strategies

**See**: [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md) for complete details.

## Contract Validation

Pydantic provides automatic validation:

```python
# Valid contract
contract = ModelContractCompute(
    name="price_calculator",
    version="1.0.0",
    node_type=EnumNodeType.COMPUTE,
    input_data={"price": 100}
)

# Invalid contract raises ValidationError
contract = ModelContractCompute(
    name="calculator",
    version="1.0.0",
    # Missing required node_type
)  # Raises ValidationError
```

## Benefits

1. **Type Safety**: Compile-time validation with mypy
2. **Runtime Validation**: Automatic Pydantic validation
3. **Documentation**: Contracts serve as API documentation
4. **Versioning**: Built-in version tracking
5. **Testability**: Easy to create test contracts

## Design Patterns

### Contract Composition

```python
class MyComplexContract(ModelContractBase):
    compute_config: ModelContractCompute
    effect_config: ModelContractEffect
```

### Contract Extension

```python
class MyCustomContract(ModelContractCompute):
    custom_field: str
    advanced_options: dict
```

## Next Steps

- [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md) - Detailed subcontract design
- [Type System](type-system.md) - Type conventions
- [Node Building Guide](../guides/node-building/README.md)

---

**Related Documentation**:
- [Architecture Overview](overview.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
