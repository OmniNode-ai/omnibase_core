> **Navigation**: [Home](../../INDEX.md) > [Reference](../README.md) > API > Utils

# Utils API Reference - omnibase_core

**Status**: ✅ Complete
**Last Updated**: 2026-02-14

## Overview

This document provides comprehensive API reference for utility functions and helpers in omnibase_core. These utilities provide common functionality for error handling, UUID generation, YAML loading, field conversion, and logging.

---

## Error Handling Decorators

### standard_error_handling

**Location**: `omnibase_core.decorators.decorator_error_handling`

**Purpose**: Decorator that provides standard error handling pattern for ONEX operations.

This decorator eliminates 6+ lines of boilerplate error handling code and ensures consistent error patterns across all nodes.

```
from omnibase_core.decorators.decorator_error_handling import standard_error_handling

@standard_error_handling(operation_name="data processing")
async def process_data(self, input_data):
    # Just business logic - no try/catch needed
    result = await self.transform_data(input_data)
    return result
```

**Parameters**:
- `operation_name: str` - Human-readable name for the operation (used in error messages)

**Error Handling Pattern Applied**:
```
try:
    return original_function(*args, **kwargs)
except ModelOnexError:
    raise  # Always re-raise ModelOnexError as-is
except Exception as e:
    raise ModelOnexError(
        f"{operation_name} failed: {str(e)}",
        EnumCoreErrorCode.OPERATION_FAILED
    ) from e
```

### validation_error_handling

**Location**: `omnibase_core.decorators.decorator_error_handling`

**Purpose**: Decorator for validation operations that may throw ValidationError.

Similar to `standard_error_handling` but specifically designed for validation operations.

```
from omnibase_core.decorators.decorator_error_handling import validation_error_handling

@validation_error_handling(operation_name="input validation")
def validate_user_input(self, user_data):
    # Validation logic
    return validated_data
```

---

## UUID Utilities

### UtilUUID

**Location**: `omnibase_core.utils.util_uuid_service`

**Purpose**: Centralized UUID generation and validation service.

```
from omnibase_core.utils.util_uuid_service import UtilUUID

# Generate UUID4
correlation_id = UtilUUID.generate()
correlation_id_str = UtilUUID.generate_str()

# Validate UUID
is_valid = UtilUUID.is_valid("550e8400-e29b-41d4-a716-446655440000")

# Parse UUID safely
uuid_obj = UtilUUID.parse("550e8400-e29b-41d4-a716-446655440000")  # Returns UUID or None

# Ensure UUID (generate if None or invalid)
uuid = UtilUUID.ensure_uuid(some_value)

# Parse UUID from string (raises exception if invalid)
uuid = UtilUUID.from_string("550e8400-e29b-41d4-a716-446655440000")

# Generate specific ID types
correlation_id = UtilUUID.generate_correlation_id()
event_id = UtilUUID.generate_event_id()
session_id = UtilUUID.generate_session_id()
```

**Methods**:
- `generate() -> UUID` - Generate a new UUID4
- `generate_str() -> str` - Generate a new UUID4 as string
- `is_valid(uuid_string: str) -> bool` - Check if string is valid UUID
- `parse(uuid_string: str) -> UUID | None` - Parse UUID string, return None if invalid
- `ensure_uuid(value: UUID | str | None) -> UUID` - Ensure value is UUID, generate if None
- `from_string(uuid_string: str) -> UUID` - Parse UUID from string (raises on invalid)
- `generate_correlation_id() -> UUID` - Generate correlation ID
- `generate_event_id() -> UUID` - Generate event ID
- `generate_session_id() -> UUID` - Generate session ID

---

## YAML Loading Utilities

### load_and_validate_yaml_model

**Location**: `omnibase_core.utils.util_safe_yaml_loader`

**Purpose**: Load YAML file and validate against Pydantic model class using `yaml.safe_load`.

This function provides type-safe YAML loading with Pydantic model validation for security and structure verification.

```
from pathlib import Path
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model
from pydantic import BaseModel

class MyConfig(BaseModel):
    database_host: str
    database_port: int
    api_key: str

# Load and validate YAML file
config_path = Path("config.yaml")
config = load_and_validate_yaml_model(config_path, MyConfig)

# Access validated data
print(f"Database: {config.database_host}:{config.database_port}")
```

**Parameters**:
- `path: Path` - Path to the YAML file
- `model_cls: type[T]` - Pydantic model class to validate against

**Returns**:
- `T` - Validated model instance

**Raises**:
- `ModelOnexError` - If loading or validation fails

---

## Field Conversion Utilities

### FieldConverter

**Location**: `omnibase_core.utils.util_field_converter`

**Purpose**: Represents a field conversion strategy.

This replaces hardcoded if/elif chains with a declarative, extensible converter registry pattern.

```
from omnibase_core.utils.util_field_converter import FieldConverter

# Define a field converter
converter = FieldConverter(
    field_name="user_id",
    converter_func=lambda x: str(x),
    target_type=str
)

# Use in field conversion registry
# (See model_field_converter_registry for usage)
```

**Attributes**:
- `field_name: str` - Name of the field to convert
- `converter_func: Callable` - Function to perform conversion
- `target_type: type` - Target type after conversion

### ModelFieldConverterRegistry

**Location**: `omnibase_core.utils.util_field_converter`

**Purpose**: Registry for field converters.

Provides centralized management of field conversion strategies.

---

## Logging Utilities

### ServiceLogging

**Location**: `omnibase_core.logging.logging_structured`

**Purpose**: Registry-based logging service implementation.

Provides a protocol-based logging interface for consistent logging across ONEX services.

```
from omnibase_core.utils.util_service_logging import ServiceLogging

# Initialize with logger protocol
logger = ServiceLogging(protocol=my_logger_protocol)

# Emit log events
logger.emit_log_event(message="Operation started", level="INFO")
logger.emit_log_event_sync(message="Synchronous log")
await logger.emit_log_event_async(message="Asynchronous log")

# Trace function lifecycle
@logger.trace_function_lifecycle
def my_function():
    # Function logic
    pass

# Get performance metrics
metrics = logger.tool_logger_performance_metrics(operation_name="data_processing")
```

**Methods**:
- `emit_log_event(*args, **kwargs)` - Emit log event via protocol
- `emit_log_event_sync(*args, **kwargs)` - Emit log event synchronously
- `emit_log_event_async(*args, **kwargs)` - Emit log event asynchronously
- `trace_function_lifecycle(func)` - Decorator to trace function lifecycle
- `tool_logger_performance_metrics(*args, **kwargs)` - Get performance metrics

### ToolLoggerCodeBlock

**Location**: `omnibase_core.utils.util_tool_logger_code_block`

**Purpose**: Logging tool for code blocks.

Specialized logging utility for tracking code block execution.

---

## Bootstrap Utilities

### util_bootstrap

**Location**: `omnibase_core.utils.util_bootstrap`

**Purpose**: Bootstrap utilities for initialization.

Provides utilities for bootstrapping ONEX services and components during initialization.

---

## Contract Loading Utilities

### util_contract_loader

**Location**: `omnibase_core.utils.util_contract_loader`

**Purpose**: Utility for loading and managing ONEX contracts.

Provides functions for loading contract definitions from YAML files and validating them against contract schemas.

---

## Singleton Pattern Utilities

### singleton_holders

**Location**: `omnibase_core.utils.util_singleton_holders`

**Purpose**: Singleton pattern helpers.

Provides utilities for implementing singleton pattern in ONEX services.

---

## Decorator Utilities

### decorators.py

**Location**: `omnibase_core.utils.util_decorators`

**Purpose**: Various utility decorators.

Provides additional decorators for common patterns in ONEX development.

---

## Common Usage Patterns

### Error Handling Pattern

```
from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class MyNode(NodeCoreBase):
    @standard_error_handling(operation_name="user data processing")
    async def process(self, input_data):
        # Just business logic - error handling is automatic
        result = await self.transform_data(input_data)
        return result
```

### UUID Generation Pattern

```
from omnibase_core.utils.util_uuid_service import UtilUUID

class MyNode(NodeCoreBase):
    async def process(self, input_data):
        # Generate correlation ID for tracking
        correlation_id = UtilUUID.generate_correlation_id()

        # Ensure UUID (handles None or invalid values)
        user_id = UtilUUID.ensure_uuid(input_data.get("user_id"))

        return {"correlation_id": correlation_id, "user_id": user_id}
```

### YAML Configuration Loading Pattern

```
from pathlib import Path
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str
    port: int
    database: str

class MyNode(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)

        # Load and validate configuration
        config_path = Path("config/database.yaml")
        self.db_config = load_and_validate_yaml_model(config_path, DatabaseConfig)
```

---

## Related Documentation

- [Nodes API](nodes.md) - Node class reference
- [Models API](models.md) - Model class reference
- [Enums API](enums.md) - Enumeration reference
- [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Node Building Guide](../../guides/node-building/README.md) - Usage examples

---

**Important Notes**:

1. **Error Handling**: Always use `standard_error_handling` decorator instead of manual try/catch blocks
2. **UUID Generation**: Use `UtilUUID` for all UUID generation to ensure consistency
3. **YAML Loading**: Use `load_and_validate_yaml_model` for type-safe YAML loading with validation
4. **Import Paths**: The correct import path for `standard_error_handling` is:
   ```python
   from omnibase_core.decorators.decorator_error_handling import standard_error_handling
   ```
   NOT `from omnibase_core.utils.standard_error_handling`

---

**Last Updated**: 2026-02-14
**Framework Version**: omnibase_core 0.17.0
