> **Navigation**: [Home](../../INDEX.md) > [Reference](../README.md) > API > Models

# Models API Reference - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides comprehensive API reference for all Pydantic models in omnibase_core. These models provide type safety, validation, and serialization for the ONEX framework.

## Core Models

### Container Models

#### ModelONEXContainer

**Location**: `omnibase_core.models.container.model_onex_container`

**Purpose**: Dependency injection container for service resolution.

```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Create container
container = ModelONEXContainer()

# Register services
container.register_service("MyService", my_service_instance)

# Resolve services
service = container.get_service("MyService")
```

#### Key Methods

- `register_service(name: str, service: Any)` - Register a service
- `get_service(name: str) -> Any` - Resolve service by name
- `has_service(name: str) -> bool` - Check if service exists
- `get_all_services() -> Dict[str, Any]` - Get all registered services

### Input/Output Models

#### ModelComputeInput

**Location**: `omnibase_core.models.compute.model_compute_input`

**Purpose**: Standard input model for COMPUTE nodes.

```
from omnibase_core.models.compute.model_compute_input import ModelComputeInput

input_data = ModelComputeInput(
    computation_type="calculate",
    data={"values": [1, 2, 3, 4, 5]},
    correlation_id="12345"
)
```

#### ModelComputeOutput

**Location**: `omnibase_core.models.compute.model_compute_output`

**Purpose**: Standard output model for COMPUTE nodes.

```
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput

output_data = ModelComputeOutput(
    result={"sum": 15},
    success=True,
    processing_time_ms=2.5,
    correlation_id="12345"
)
```

### Error Models

#### ModelOnexError

**Location**: `omnibase_core.errors.model_onex_error`

**Purpose**: Standard error model for ONEX framework.

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

error = ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="Invalid input data",
    context={"field": "value", "expected": "string"}
)
```

#### Key Properties

- `error_code: EnumCoreErrorCode` - Error classification
- `message: str` - Human-readable error message
- `context: Dict[str, Any]` - Additional error context
- `timestamp: float` - Error timestamp
- `correlation_id: Optional[str]` - Request correlation ID

### Event Models

#### ModelEventEnvelope

**Location**: `omnibase_core.models.events.model_event_envelope`

**Purpose**: Event envelope for inter-node communication.

```
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

event = ModelEventEnvelope(
    event_type="computation_completed",
    payload={"result": "success"},
    source_node="compute_node_1",
    target_node="effect_node_1"
)
```

### Intent and Action Models

#### ModelIntent

**Location**: `omnibase_core.models.reducer.model_intent`

**Purpose**: Intent model for side effect declarations from pure Reducer FSM.

The Reducer is a pure function that emits Intents describing what side effects should occur. The Effect node consumes and executes these Intents.

```
from omnibase_core.models.reducer.model_intent import ModelIntent

intent = ModelIntent(
    intent_type="emit_event",
    target="user.created",
    payload={"user_id": "123", "email": "user@example.com"},
    priority=5
)
```

**Note**: `intent_type` is a string field (common values: "log", "emit_event", "write", "notify", "http_request").

#### ModelAction

**Location**: `omnibase_core.models.orchestrator.model_action`

**Purpose**: Orchestrator-issued Action with lease management for single-writer semantics.

```
from uuid import uuid4
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_workflow_execution import EnumActionType

action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    target_node_type="compute",
    lease_id=uuid4(),
    epoch=1,
    priority=5,
    payload={"field": "status", "value": "completed"}
)
```

### Cache Models

#### ModelComputeCache

**Location**: `omnibase_core.models.infrastructure.model_compute_cache`

**Purpose**: LRU cache for computation results.

```
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache

cache = ModelComputeCache(max_size=1000, default_ttl_minutes=30)

# Store result
cache.put("key", {"result": "computed"}, ttl_minutes=60)

# Retrieve result
result = cache.get("key")

# Check if exists
exists = cache.contains("key")
```

#### Key Methods

- `put(key: str, value: Any, ttl_minutes: Optional[int])` - Store value
- `get(key: str) -> Optional[Any]` - Retrieve value
- `contains(key: str) -> bool` - Check existence
- `clear()` - Clear all entries
- `get_stats() -> Dict[str, Any]` - Get cache statistics

### Circuit Breaker Models

#### ModelCircuitBreaker

**Location**: `omnibase_core.models.infrastructure.model_circuit_breaker`

**Purpose**: Circuit breaker for failure handling.

```
from omnibase_core.models.infrastructure.model_circuit_breaker import ModelCircuitBreaker

breaker = ModelCircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)

# Check if can execute
if breaker.can_execute():
    try:
        result = await risky_operation()
        breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        raise
else:
    raise Exception("Circuit breaker is open")
```

#### Key Methods

- `can_execute() -> bool` - Check if operation can proceed
- `record_success()` - Record successful operation
- `record_failure()` - Record failed operation
- `get_state() -> EnumCircuitBreakerState` - Get current state

### Transaction Models

#### ModelEffectTransaction

**Location**: `omnibase_core.models.infrastructure.model_effect_transaction`

**Purpose**: Transaction management for side effects.

```
from omnibase_core.models.infrastructure.model_effect_transaction import ModelEffectTransaction

async with ModelEffectTransaction() as transaction:
    # Add operations to transaction
    transaction.add_operation("database_write", {"table": "users"})
    transaction.add_operation("file_write", {"path": "/tmp/data.json"})

    # Execute operations
    await transaction.execute()

    # Transaction commits automatically on success
    # or rolls back on exception
```

## Validation Patterns

### Input Validation

```
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class MyInputModel(BaseModel):
    """Example input model with validation."""

    name: str = Field(description="User name", min_length=1, max_length=100)
    age: int = Field(description="User age", ge=0, le=150)
    email: str = Field(description="Email address", regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    tags: List[str] = Field(description="User tags", max_items=10)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Custom name validation."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Custom tags validation."""
        if len(set(v)) != len(v):
            raise ValueError("Tags must be unique")
        return v
```

### Output Validation

```
class MyOutputModel(BaseModel):
    """Example output model with validation."""

    success: bool = Field(description="Operation success status")
    result: Optional[Dict[str, Any]] = Field(description="Operation result")
    error_message: Optional[str] = Field(description="Error message if failed")
    processing_time_ms: float = Field(description="Processing time", ge=0)

    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v, info):
        """Validate error message consistency."""
        success = info.data.get('success', True)
        if success and v is not None:
            raise ValueError("Error message should be None when success is True")
        if not success and v is None:
            raise ValueError("Error message required when success is False")
        return v
```

## Serialization Patterns

### JSON Serialization (Pydantic v2)

```
# Convert to JSON string
json_data = model.model_dump_json()

# Convert from JSON string
model = MyModel.model_validate_json(json_data)

# Convert to dict
dict_data = model.model_dump()

# Convert from dict
model = MyModel.model_validate(dict_data)
# Or use keyword arguments
model = MyModel(**dict_data)
```

### Custom Serialization

```
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from datetime import datetime
from typing import Any, Dict

class CustomModel(BaseModel):
    """Model with custom serialization."""

    model_config = ConfigDict(
        ser_json_timedelta="iso8601"
    )

    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Custom timestamp serialization."""
        return value.isoformat()

    def to_api_dict(self) -> Dict[str, Any]:
        """Custom serialization for API responses."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "version": "1.0"
        }
```

## Error Handling Patterns

### Validation Error Handling

```
from pydantic import ValidationError

try:
    model = MyModel(**input_data)
except ValidationError as e:
    # Handle validation errors
    error_details = []
    for error in e.errors():
        error_details.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message="Input validation failed",
        context={"errors": error_details}
    )
```

### Model Error Conversion

```
def convert_to_onex_error(error: Exception, context: Dict[str, Any]) -> ModelOnexError:
    """Convert any exception to ModelOnexError."""

    if isinstance(error, ValidationError):
        return ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Validation failed: {str(error)}",
            context=context
        )
    elif isinstance(error, TimeoutError):
        return ModelOnexError(
            error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
            message=f"Operation timed out: {str(error)}",
            context=context
        )
    else:
        return ModelOnexError(
            error_code=EnumCoreErrorCode.PROCESSING_ERROR,
            message=f"Processing failed: {str(error)}",
            context=context
        )
```

## Performance Considerations

### Model Caching

```
from functools import lru_cache

@lru_cache(maxsize=128)
def create_model_from_dict(model_class: type, data: Dict[str, Any]) -> BaseModel:
    """Cache model creation for performance."""
    return model_class(**data)
```

### Lazy Loading

```
from typing import Optional

class LazyModel(BaseModel):
    """Model with lazy-loaded fields."""

    _cached_data: Optional[Dict[str, Any]] = None

    @property
    def expensive_data(self) -> Dict[str, Any]:
        """Lazy-loaded expensive data."""
        if self._cached_data is None:
            self._cached_data = self._load_expensive_data()
        return self._cached_data

    def _load_expensive_data(self) -> Dict[str, Any]:
        """Load expensive data."""
        # Expensive operation here
        return {"loaded": "data"}
```

## Related Documentation

- [Nodes API](nodes.md) - Node class reference
- [Enums API](enums.md) - Enumeration reference
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Node Building Guide](../../guides/node-building/README.md) - Usage examples
