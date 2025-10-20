# Utils API Reference - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

Complete reference for utility functions and decorators in omnibase_core.

## Decorators

### @standard_error_handling

Automatic error handling decorator that eliminates boilerplate try/catch blocks.

```python
from omnibase_core.decorators.error_handling import standard_error_handling

@standard_error_handling
async def my_operation(self, data: dict) -> dict:
    """Operation with automatic error handling."""
    # Business logic here
    return result
```

**Benefits**:
- Catches all exceptions
- Converts to OnexError
- Preserves exception chains
- Adds contextual information
- Reduces 6+ lines of boilerplate per method

## Error Handling

### OnexError

Structured exception class for all ONEX errors.

```python
from omnibase_core.exceptions.base_onex_error import OnexError

raise OnexError(
    message="Operation failed",
    error_code=EnumErrorCode.OPERATION_FAILED,
    context={"operation": "process_data", "input": data}
)
```

**Features**:
- Structured error information
- Type-safe error codes
- Contextual data
- Exception chaining
- Pydantic model integration

### Error Context

```python
try:
    await risky_operation()
except Exception as e:
    raise OnexError(
        message="Failed to process",
        error_code=EnumErrorCode.OPERATION_FAILED,
        context={
            "original_error": str(e),
            "input_data": data,
            "timestamp": datetime.now()
        }
    ) from e  # Preserve exception chain
```

## Logging Utilities

### Structured Logging

```python
self.logger.info(
    "Processing data",
    extra={
        "node_type": "COMPUTE",
        "operation": "calculate",
        "input_size": len(data)
    }
)
```

## Validation Utilities

### Contract Validation

```python
def validate_contract(contract: ModelContractBase) -> bool:
    """Validate contract structure."""
    # Validation logic
    pass
```

## Type Utilities

### Type Guards

```python
from typing import TypeGuard

def is_compute_contract(
    contract: ModelContractBase
) -> TypeGuard[ModelContractCompute]:
    """Type guard for COMPUTE contracts."""
    return contract.node_type == EnumNodeType.COMPUTE
```

## Next Steps

- [Nodes API](nodes.md) - Node reference
- [Models API](models.md) - Model reference
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

**Related Documentation**:
- [Development Workflow](../../guides/development-workflow.md)
- [Testing Guide](../../guides/testing-guide.md)
