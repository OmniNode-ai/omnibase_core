# TypedDict Consolidation Documentation

## Overview

As part of the ONEX compliance migration in PR #36, all TypedDict classes have been consolidated and moved from the `models/` directory to the dedicated `types/` directory. This consolidation provides improved type safety, better IDE support, and clearer separation between data structures and business logic models.

## Benefits of TypedDict Consolidation

### 1. Type Safety Enhancement
- **Static Type Checking**: Full mypy and pyright compatibility
- **Runtime Type Validation**: Optional runtime validation with typeguard
- **IDE Integration**: Enhanced autocomplete and type inference

### 2. Code Organization
- **Clear Separation**: Types separated from business logic models
- **Centralized Location**: All type definitions in one discoverable location
- **Reduced Import Complexity**: Simplified import statements

### 3. Performance Benefits
- **Memory Efficiency**: TypedDict has lower memory overhead than dataclasses
- **Serialization Speed**: Faster JSON serialization/deserialization
- **Runtime Performance**: No instance method overhead

## Migration Patterns

### Before: Models Directory Structure
```
models/
├── __init__.py
├── base_model.py
├── contract_model.py
├── event_model.py
├── request_types.py  # Mixed TypedDict and Pydantic
├── response_types.py # Mixed TypedDict and Pydantic
└── ...
```

### After: Consolidated Types Structure
```
types/
├── __init__.py
├── base_types.py
├── contract_types.py
├── event_types.py
├── request_types.py
├── response_types.py
├── validation_types.py
└── ...
```

## Core TypedDict Classes

### Contract-Related Types

#### ContractRequest
```python
from typing_extensions import TypedDict, NotRequired
from uuid import UUID
from datetime import datetime

class ContractRequest(TypedDict):
    """
    Represents a contract request with all required and optional fields.

    Attributes:
        contract_id: Unique identifier for the contract
        correlation_id: UUID for tracking across services
        contract_type: Type classification of the contract
        priority: Execution priority level
        payload: Contract-specific data payload
        metadata: Optional metadata for additional context
        created_at: Request creation timestamp
        expires_at: Optional expiration timestamp

    Example:
        >>> contract_request: ContractRequest = {
        ...     "contract_id": "contract-123",
        ...     "correlation_id": UUID("12345678-1234-1234-1234-123456789abc"),
        ...     "contract_type": "processing",
        ...     "priority": "high",
        ...     "payload": {"data": "example"},
        ...     "created_at": datetime.utcnow()
        ... }
    """
    contract_id: str
    correlation_id: UUID
    contract_type: str
    priority: str
    payload: dict[str, any]
    metadata: NotRequired[dict[str, any]]
    created_at: datetime
    expires_at: NotRequired[datetime]
```

#### ContractResponse
```python
class ContractResponse(TypedDict):
    """
    Standard response format for all contract operations.

    Attributes:
        success: Operation success indicator
        correlation_id: UUID for tracking across services
        contract_id: Associated contract identifier
        result: Operation result data
        error_code: Optional error code for failures
        error_message: Optional human-readable error description
        execution_time_ms: Processing time in milliseconds
        metadata: Optional response metadata

    Example:
        >>> response: ContractResponse = {
        ...     "success": True,
        ...     "correlation_id": UUID("12345678-1234-1234-1234-123456789abc"),
        ...     "contract_id": "contract-123",
        ...     "result": {"processed_data": "value"},
        ...     "execution_time_ms": 150
        ... }
    """
    success: bool
    correlation_id: UUID
    contract_id: str
    result: dict[str, any]
    error_code: NotRequired[str]
    error_message: NotRequired[str]
    execution_time_ms: int
    metadata: NotRequired[dict[str, any]]
```

### Event System Types

#### EventEnvelope
```python
class EventEnvelope(TypedDict):
    """
    Standard envelope for all events in the ONEX system.

    Attributes:
        event_id: Unique event identifier
        correlation_id: UUID for tracking across services
        event_type: Classification of the event
        source_node: ONEX node that generated the event
        timestamp: Event creation timestamp
        payload: Event-specific data
        metadata: Optional metadata for routing/processing
        priority: Event processing priority

    Example:
        >>> event: EventEnvelope = {
        ...     "event_id": "evt-123",
        ...     "correlation_id": UUID("12345678-1234-1234-1234-123456789abc"),
        ...     "event_type": "contract.completed",
        ...     "source_node": "COMPUTE",
        ...     "timestamp": datetime.utcnow(),
        ...     "payload": {"contract_result": "success"},
        ...     "priority": "normal"
        ... }
    """
    event_id: str
    correlation_id: UUID
    event_type: str
    source_node: str  # EFFECT | COMPUTE | REDUCER | ORCHESTRATOR
    timestamp: datetime
    payload: dict[str, any]
    metadata: NotRequired[dict[str, any]]
    priority: NotRequired[str]
```

### Validation and Error Types

#### ValidationResult
```python
class ValidationResult(TypedDict):
    """
    Result of data validation operations.

    Attributes:
        is_valid: Overall validation status
        errors: List of validation error messages
        warnings: Optional validation warnings
        field_errors: Field-specific error mapping
        validation_time_ms: Time taken for validation

    Example:
        >>> result: ValidationResult = {
        ...     "is_valid": False,
        ...     "errors": ["Required field 'contract_id' is missing"],
        ...     "field_errors": {"contract_id": "Field is required"},
        ...     "validation_time_ms": 25
        ... }
    """
    is_valid: bool
    errors: list[str]
    warnings: NotRequired[list[str]]
    field_errors: NotRequired[dict[str, str]]
    validation_time_ms: int
```

#### ErrorContext
```python
class ErrorContext(TypedDict):
    """
    Contextual information for error reporting and debugging.

    Attributes:
        error_id: Unique error identifier
        correlation_id: UUID for tracking across services
        error_type: Classification of the error
        error_code: Machine-readable error code
        message: Human-readable error description
        source_node: ONEX node where error occurred
        timestamp: Error occurrence timestamp
        stack_trace: Optional stack trace information
        additional_data: Optional additional context data

    Example:
        >>> error_ctx: ErrorContext = {
        ...     "error_id": "err-456",
        ...     "correlation_id": UUID("12345678-1234-1234-1234-123456789abc"),
        ...     "error_type": "ValidationError",
        ...     "error_code": "CONTRACT_INVALID",
        ...     "message": "Invalid contract format",
        ...     "source_node": "EFFECT",
        ...     "timestamp": datetime.utcnow()
        ... }
    """
    error_id: str
    correlation_id: UUID
    error_type: str
    error_code: str
    message: str
    source_node: str
    timestamp: datetime
    stack_trace: NotRequired[str]
    additional_data: NotRequired[dict[str, any]]
```

## Usage Patterns

### 1. Type-Safe Function Signatures

#### Before (Less Type Safety)
```python
def process_contract(data: dict) -> dict:
    # Unclear what fields are expected or returned
    contract_id = data.get("contract_id")  # Could be None
    # ... processing logic
    return {"status": "completed"}
```

#### After (Full Type Safety)
```python
def process_contract(request: ContractRequest) -> ContractResponse:
    # Clear contract - all required fields guaranteed present
    contract_id = request["contract_id"]  # Always present
    correlation_id = request["correlation_id"]  # Always UUID

    # Type-safe response construction
    response: ContractResponse = {
        "success": True,
        "correlation_id": correlation_id,
        "contract_id": contract_id,
        "result": {"status": "completed"},
        "execution_time_ms": 150
    }
    return response
```

### 2. Validation Integration

```python
from typeguard import check_type
from types.contract_types import ContractRequest, ContractResponse

def validate_contract_request(data: dict) -> ValidationResult:
    """Validate contract request data against TypedDict schema."""
    try:
        # Runtime type validation
        check_type(data, ContractRequest)

        return ValidationResult({
            "is_valid": True,
            "errors": [],
            "validation_time_ms": 10
        })

    except TypeError as e:
        return ValidationResult({
            "is_valid": False,
            "errors": [str(e)],
            "validation_time_ms": 15
        })
```

### 3. ONEX Node Integration

```python
from types.event_types import EventEnvelope
from types.contract_types import ContractRequest, ContractResponse

class EffectNode:
    def process_event(self, envelope: EventEnvelope) -> ContractResponse:
        """Process incoming event with full type safety."""

        # Extract typed payload
        contract_request = envelope["payload"]

        # Type-safe processing
        result = self._execute_effect(contract_request)

        # Type-safe response
        response: ContractResponse = {
            "success": True,
            "correlation_id": envelope["correlation_id"],
            "contract_id": contract_request["contract_id"],
            "result": result,
            "execution_time_ms": 200
        }

        return response
```

## Import Guidelines

### Centralized Imports
```python
# Preferred: Import from types module
from types.contract_types import ContractRequest, ContractResponse
from types.event_types import EventEnvelope
from types.validation_types import ValidationResult

# Avoid: Importing from models (legacy)
# from models.request_types import ContractRequest  # Don't do this
```

### Module Organization
```python
# types/__init__.py - Central export point
from .contract_types import ContractRequest, ContractResponse
from .event_types import EventEnvelope, EventPayload
from .validation_types import ValidationResult, ErrorContext
from .base_types import BaseMetadata, Timestamps

__all__ = [
    "ContractRequest",
    "ContractResponse",
    "EventEnvelope",
    "EventPayload",
    "ValidationResult",
    "ErrorContext",
    "BaseMetadata",
    "Timestamps"
]
```

## Best Practices

### 1. Always Use NotRequired for Optional Fields
```python
class ExampleType(TypedDict):
    required_field: str
    optional_field: NotRequired[str]  # Correct
    # optional_field: str | None      # Incorrect - field is still required
```

### 2. Provide Comprehensive Docstrings
```python
class WellDocumentedType(TypedDict):
    """
    Brief description of the type's purpose.

    Attributes:
        field_name: Clear description with type and constraints
        other_field: Another clear description

    Example:
        >>> instance: WellDocumentedType = {
        ...     "field_name": "example_value",
        ...     "other_field": 42
        ... }
    """
    field_name: str
    other_field: int
```

### 3. Use Generic Types for Better Reusability
```python
from typing import Generic, TypeVar

T = TypeVar('T')

class GenericResponse(TypedDict, Generic[T]):
    """Generic response type for reusability."""
    success: bool
    data: T
    errors: NotRequired[list[str]]

# Usage
StringResponse = GenericResponse[str]
IntResponse = GenericResponse[int]
```

## Testing Integration

### Type-Safe Test Data
```python
import pytest
from types.contract_types import ContractRequest
from uuid import uuid4
from datetime import datetime

@pytest.fixture
def valid_contract_request() -> ContractRequest:
    """Type-safe test fixture."""
    return ContractRequest({
        "contract_id": "test-contract-123",
        "correlation_id": uuid4(),
        "contract_type": "testing",
        "priority": "low",
        "payload": {"test": "data"},
        "created_at": datetime.utcnow()
    })

def test_contract_processing(valid_contract_request: ContractRequest):
    """Type-safe test with clear parameter types."""
    result = process_contract(valid_contract_request)

    assert result["success"] is True
    assert result["contract_id"] == valid_contract_request["contract_id"]
```

## Migration Checklist

### For Developers
- [ ] Update all imports from `models.*` to `types.*`
- [ ] Add type annotations to function signatures
- [ ] Update test fixtures to use TypedDict classes
- [ ] Run mypy to verify type safety
- [ ] Update documentation with type information

### For Code Review
- [ ] Verify all TypedDict classes have comprehensive docstrings
- [ ] Check that optional fields use `NotRequired`
- [ ] Ensure examples are provided in docstrings
- [ ] Validate that imports come from `types/` module
- [ ] Confirm type safety with static analysis tools

## Integration with ONEX Architecture

TypedDict classes integrate seamlessly with the ONEX Four-Node Architecture:

- **EFFECT Node**: Uses `EventEnvelope` and `ContractRequest` types
- **COMPUTE Node**: Processes `ContractRequest`, returns `ContractResponse`
- **REDUCER Node**: Aggregates multiple `ContractResponse` objects
- **ORCHESTRATOR Node**: Coordinates using all type definitions

This consolidation ensures type safety across the entire ONEX ecosystem while maintaining high performance and clear code organization.
