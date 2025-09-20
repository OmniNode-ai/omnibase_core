# Factory Pattern Analysis and Refactoring Guide

## Overview

This document analyzes the repetitive factory methods across the CLI, Config, Nodes, and Validation domains and demonstrates how the new `ModelGenericFactory` pattern can replace them with type-safe, consistent implementations.

## Current Factory Method Patterns

### 1. ModelCliResult Factory Methods

**Current Implementation (Lines 237-336):**

```python
@classmethod
def create_success(
    cls,
    execution: ModelCliExecution,
    output_data: ModelCliOutputData | None = None,
    output_text: str | None = None,
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a successful result."""
    # ... implementation

@classmethod
def create_failure(
    cls,
    execution: ModelCliExecution,
    error_message: str,
    exit_code: int = 1,
    error_details: str | None = None,
    validation_errors: list[ModelValidationError] | None = None,
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a failure result."""
    # ... implementation

@classmethod
def create_validation_failure(
    cls,
    execution: ModelCliExecution,
    validation_errors: list[ModelValidationError],
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a result for validation failures."""
    # ... implementation
```

**Refactored Implementation:**

```python
from ..core.model_generic_factory import ResultFactory

# Class-level factory instance
_factory = ResultFactory(ModelCliResult)

# Register CLI-specific builders
_factory.register_builder("cli_success", lambda kwargs: ModelCliResult(
    execution=kwargs["execution"],
    success=True,
    exit_code=0,
    output_data=kwargs.get("output_data") or ModelCliOutputData(
        stdout=None, stderr=None, execution_time_ms=None, memory_usage_mb=None
    ),
    output_text=kwargs.get("output_text"),
    execution_time=kwargs.get("execution_time") or ModelDuration(
        milliseconds=kwargs["execution"].get_elapsed_ms()
    ),
    **{k: v for k, v in kwargs.items() if k not in [
        "execution", "output_data", "output_text", "execution_time"
    ]}
))

_factory.register_builder("cli_failure", lambda kwargs: ModelCliResult(
    execution=kwargs["execution"],
    success=False,
    exit_code=kwargs.get("exit_code", 1),
    error_message=kwargs["error_message"],
    error_details=kwargs.get("error_details"),
    validation_errors=kwargs.get("validation_errors", []),
    execution_time=kwargs.get("execution_time") or ModelDuration(
        milliseconds=kwargs["execution"].get_elapsed_ms()
    ),
    **{k: v for k, v in kwargs.items() if k not in [
        "execution", "error_message", "error_details", "validation_errors", "execution_time"
    ]}
))

_factory.register_builder("cli_validation_failure", lambda kwargs: ModelCliResult(
    execution=kwargs["execution"],
    success=False,
    exit_code=2,
    error_message=kwargs["validation_errors"][0].message if kwargs["validation_errors"] else "Validation failed",
    validation_errors=kwargs["validation_errors"],
    execution_time=kwargs.get("execution_time") or ModelDuration(
        milliseconds=kwargs["execution"].get_elapsed_ms()
    ),
    **{k: v for k, v in kwargs.items() if k not in [
        "execution", "validation_errors", "execution_time"
    ]}
))

@classmethod
def create_success(
    cls,
    execution: ModelCliExecution,
    output_data: ModelCliOutputData | None = None,
    output_text: str | None = None,
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a successful result."""
    execution.mark_completed()
    return _factory.build("cli_success",
        execution=execution,
        output_data=output_data,
        output_text=output_text,
        execution_time=execution_time
    )

@classmethod
def create_failure(
    cls,
    execution: ModelCliExecution,
    error_message: str,
    exit_code: int = 1,
    error_details: str | None = None,
    validation_errors: list[ModelValidationError] | None = None,
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a failure result."""
    execution.mark_completed()
    return _factory.build("cli_failure",
        execution=execution,
        error_message=error_message,
        exit_code=exit_code,
        error_details=error_details,
        validation_errors=validation_errors,
        execution_time=execution_time
    )

@classmethod
def create_validation_failure(
    cls,
    execution: ModelCliExecution,
    validation_errors: list[ModelValidationError],
    execution_time: ModelDuration | None = None,
) -> "ModelCliResult":
    """Create a result for validation failures."""
    execution.mark_completed()
    return _factory.build("cli_validation_failure",
        execution=execution,
        validation_errors=validation_errors,
        execution_time=execution_time
    )
```

### 2. ModelNodeCapability Factory Methods

**Current Implementation (Lines 79-192):**

```python
@classmethod
def supports_dry_run(cls) -> "ModelNodeCapability":
    """Dry run support capability."""
    return cls(
        name="SUPPORTS_DRY_RUN",
        value="supports_dry_run",
        description="Node can simulate execution without side effects",
        version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        configuration_required=False,
        performance_impact=EnumPerformanceImpact.LOW,
    )

@classmethod
def supports_batch_processing(cls) -> "ModelNodeCapability":
    """Batch processing support capability."""
    return cls(
        name="SUPPORTS_BATCH_PROCESSING",
        value="supports_batch_processing",
        description="Node can process multiple items in a single execution",
        version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        configuration_required=True,
        performance_impact=EnumPerformanceImpact.MEDIUM,
        example_config={"batch_size": 100, "parallel_workers": 4},
    )

# ... 8 more similar methods
```

**Refactored Implementation:**

```python
from ..core.model_generic_factory import CapabilityFactory

# Class-level factory instance
_capability_factory = CapabilityFactory(ModelNodeCapability)

# Register capability factories
_capability_factory.register_factory("dry_run", lambda: ModelNodeCapability(
    name="SUPPORTS_DRY_RUN",
    value="supports_dry_run",
    description="Node can simulate execution without side effects",
    version_introduced=ModelSemVer(major=1, minor=0, patch=0),
    configuration_required=False,
    performance_impact=EnumPerformanceImpact.LOW,
))

_capability_factory.register_factory("batch_processing", lambda: ModelNodeCapability(
    name="SUPPORTS_BATCH_PROCESSING",
    value="supports_batch_processing",
    description="Node can process multiple items in a single execution",
    version_introduced=ModelSemVer(major=1, minor=0, patch=0),
    configuration_required=True,
    performance_impact=EnumPerformanceImpact.MEDIUM,
    example_config={"batch_size": 100, "parallel_workers": 4},
))

_capability_factory.register_factory("custom_handlers", lambda: ModelNodeCapability(
    name="SUPPORTS_CUSTOM_HANDLERS",
    value="supports_custom_handlers",
    description="Node accepts custom handler implementations",
    version_introduced=ModelSemVer(major=1, minor=0, patch=0),
    configuration_required=True,
    performance_impact=EnumPerformanceImpact.LOW,
    dependencies=["SUPPORTS_SCHEMA_VALIDATION"],
))

# ... register other capabilities

@classmethod
def supports_dry_run(cls) -> "ModelNodeCapability":
    """Dry run support capability."""
    return _capability_factory.create("dry_run")

@classmethod
def supports_batch_processing(cls) -> "ModelNodeCapability":
    """Batch processing support capability."""
    return _capability_factory.create("batch_processing")

@classmethod
def supports_custom_handlers(cls) -> "ModelNodeCapability":
    """Custom handlers support capability."""
    return _capability_factory.create("custom_handlers")

# ... simplified factory methods
```

### 3. ModelValidationError Factory Methods

**Current Implementation (Lines 66-109):**

```python
@classmethod
def create_error(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a standard error."""
    return cls(
        message=message,
        severity=EnumValidationSeverity.ERROR,
        field_name=field_name,
        error_code=error_code,
    )

@classmethod
def create_critical(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a critical error."""
    return cls(
        message=message,
        severity=EnumValidationSeverity.CRITICAL,
        field_name=field_name,
        error_code=error_code,
    )

@classmethod
def create_warning(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a warning."""
    return cls(
        message=message,
        severity=EnumValidationSeverity.WARNING,
        field_name=field_name,
        error_code=error_code,
    )
```

**Refactored Implementation:**

```python
from ..core.model_generic_factory import ValidationErrorFactory

# Class-level factory instance
_validation_factory = ValidationErrorFactory(ModelValidationError)

@classmethod
def create_error(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a standard error."""
    return _validation_factory.build("error",
        message=message,
        field_name=field_name,
        error_code=error_code
    )

@classmethod
def create_critical(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a critical error."""
    return _validation_factory.build("critical",
        message=message,
        field_name=field_name,
        error_code=error_code
    )

@classmethod
def create_warning(
    cls,
    message: str,
    field_name: str | None = None,
    error_code: str | None = None,
) -> "ModelValidationError":
    """Create a warning."""
    return _validation_factory.build("warning",
        message=message,
        field_name=field_name,
        error_code=error_code
    )
```

## Benefits of the Generic Factory Pattern

### 1. **Type Safety**
- Generic `TypeVar` ensures type safety at compile time
- MyPy can verify factory methods return correct types
- No runtime type errors from factory misuse

### 2. **Consistency**
- Standardized factory registration and creation patterns
- Common naming conventions across domains
- Consistent error handling and validation

### 3. **Extensibility**
- Easy to add new factory methods without code duplication
- Specialized factory classes for different model types
- Registry pattern allows runtime discovery of available factories

### 4. **Maintainability**
- Single source of truth for factory logic
- Easier to update factory behavior across the codebase
- Clear separation between factory registration and usage

### 5. **Testing**
- Factories can be easily mocked or overridden for testing
- Consistent test patterns across different model types
- Better isolation of factory logic for unit testing

## Additional Factory Patterns Found

### Duration Factory Methods (ModelDuration)
- `create_from_seconds()`, `create_from_milliseconds()`, etc.
- Could use a `TimeFactory` specialization

### Configuration Factory Methods (ModelEnvironmentProperties)
- `create_from_dict()`, `create_empty()`
- Could use a `ConfigFactory` specialization

### Metadata Factory Methods (ModelMetadataFieldInfo)
- Multiple `create_*_field()` methods
- Could use a `MetadataFactory` specialization

## Implementation Plan

1. **Phase 1**: Create the generic factory infrastructure ✅
2. **Phase 2**: Refactor CLI result factories
3. **Phase 3**: Refactor node capability factories
4. **Phase 4**: Refactor validation error factories
5. **Phase 5**: Extend pattern to other domains (Duration, Config, Metadata)
6. **Phase 6**: Add comprehensive tests for all factory patterns
7. **Phase 7**: Update documentation and examples

## Migration Strategy

### Backward Compatibility
- Keep existing factory methods as thin wrappers
- Gradually migrate callers to use factory instances directly
- Deprecate old methods after migration is complete

### Testing
- Ensure all existing tests continue to pass
- Add new tests for factory pattern functionality
- Test factory registration and creation patterns

### Documentation
- Update model documentation to reference factory patterns
- Add examples of factory usage in docstrings
- Create migration guide for developers

## Conclusion

The generic factory pattern provides significant benefits in terms of type safety, consistency, and maintainability while reducing code duplication across the codebase. The pattern scales well to handle the various factory needs across CLI, Config, Nodes, and Validation domains while maintaining backward compatibility.