> **Navigation**: [Home](../INDEX.md) > Conventions > Error Handling Best Practices

# ONEX Error Handling Best Practices

## Overview

This document establishes comprehensive error handling standards for the ONEX Four-Node Architecture introduced in PR #36. It provides patterns, practices, and implementation guidelines for robust error handling across all contract models, subcontracts, and node implementations with complete correlation tracking and recovery mechanisms.

## Error Handling Philosophy

### Core Principles

1. **Fail Fast, Fail Explicitly**: Detect and report errors immediately with clear context
2. **Correlation Preservation**: Maintain correlation IDs throughout error propagation
3. **Structured Error Context**: Provide actionable error information with debugging context
4. **Graceful Degradation**: Continue operation where possible with reduced functionality
5. **Comprehensive Recovery**: Implement robust recovery mechanisms for transient failures
6. **Audit Trail**: Maintain complete error audit trails for compliance and debugging

### Error Categories

- **Validation Errors**: Input data or configuration validation failures
- **Business Logic Errors**: Domain-specific rule violations
- **System Errors**: Infrastructure, network, or resource failures
- **Integration Errors**: External service or dependency failures
- **Timeout Errors**: Operation timeouts and deadline violations
- **Concurrency Errors**: Race conditions and synchronization failures

## ONEX Error Framework

### Centralized Error Code Pattern

ONEX uses a centralized error code pattern to ensure consistency across all error handling code. The pattern is defined once and imported wherever validation is needed.

**Single Source of Truth**: `src/omnibase_core/constants/constants_error.py`

```python
from omnibase_core.constants import ERROR_CODE_PATTERN, ERROR_CODE_PATTERN_STRING

# Validate error codes
if ERROR_CODE_PATTERN.match("AUTH_001"):
    print("Valid error code")

# Use raw pattern string for JSON schemas
schema = {"pattern": ERROR_CODE_PATTERN_STRING}
```

**Pattern Format**: `CATEGORY_NNN` (e.g., `AUTH_001`, `VALIDATION_123`, `SYSTEM_01`)

**Benefits of Centralization**:
- **No Pattern Drift**: All modules use the same pattern definition
- **Single Maintenance Point**: Pattern changes propagate automatically
- **Thread-Safe**: Compiled regex patterns are immutable
- **Consistent Validation**: Same behavior across Pydantic models, validators, and utilities

**Modules Using This Pattern**:
- `omnibase_core.models.context.model_error_metadata` - Error metadata model
- `omnibase_core.models.context.model_retry_error_context` - Retry context model
- `omnibase_core.validation.validators.common_validators` - Standalone validators

For complete error code standards including valid/invalid examples and best practices, see [Error Code Standards](ERROR_CODE_STANDARDS.md).

### ModelOnexError Base Class

All ONEX errors inherit from the `ModelOnexError` base class which provides structured error context and correlation tracking:

```
# ModelOnexError class definition (from omnibase_core.models.errors.model_onex_error)
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import UTC, datetime

class ModelOnexError(Exception):
    """
    Base exception class for all ONEX-related errors.

    Provides structured error information, correlation tracking,
    and comprehensive context for debugging and monitoring.

    Attributes:
        message (str): Human-readable error description
        correlation_id (Optional[UUID]): Request correlation identifier
        error_code (str): Machine-readable error classification
        error_context (Dict[str, Any]): Additional error context and metadata
        timestamp (datetime): When the error occurred
        component (str): Component where the error originated
        operation (str): Operation that was being performed
        recoverable (bool): Whether the error might be recoverable
    """

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        error_code: str = "ONEX_ERROR",
        error_context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        operation: Optional[str] = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id
        self.error_code = error_code
        self.error_context = error_context or {}
        self.timestamp = datetime.now(UTC)
        self.component = component
        self.operation = operation
        self.recoverable = recoverable

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "message": self.message,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "error_code": self.error_code,
            "error_context": self.error_context,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "operation": self.operation,
            "recoverable": self.recoverable
        }

    def __str__(self) -> str:
        """Human-readable error representation."""
        context = f" (correlation_id: {self.correlation_id})" if self.correlation_id else ""
        return f"{self.error_code}: {self.message}{context}"
```

### Specialized Error Classes

#### Contract Validation Errors

```
class ContractValidationError(ModelOnexError):
    """
    Error raised when contract validation fails.

    Used for Pydantic validation errors, missing required fields,
    invalid field values, or contract constraint violations.
    """

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        contract_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code="CONTRACT_VALIDATION_FAILED",
            error_context={
                "validation_errors": validation_errors or [],
                "contract_type": contract_type,
                **kwargs.get("error_context", {})
            },
            component="contract_validator",
            recoverable=True,  # Usually recoverable by fixing input
            **kwargs
        )

# Usage Example
def validate_contract(contract: ModelContractBase) -> None:
    """Validate contract with comprehensive error handling."""
    try:
        # Pydantic validation happens automatically
        contract.model_validate(contract.model_dump())
    except ValidationError as e:
        raise ContractValidationError(
            message=f"Contract validation failed for {type(contract).__name__}",
            correlation_id=contract.correlation_id,
            validation_errors=[
                {
                    "field": error["loc"][-1] if error["loc"] else "unknown",
                    "message": error["msg"],
                    "input": error.get("input"),
                    "type": error["type"]
                }
                for error in e.errors()
            ],
            contract_type=type(contract).__name__
        ) from e
```

#### Node Operation Errors

```
class NodeOperationError(ModelOnexError):
    """
    Error raised during ONEX node operations.

    Covers errors in EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR
    node operations with node-specific context.
    """

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        node_type: Optional[str] = None,
        operation_type: Optional[str] = None,
        node_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code=f"{node_type.upper()}_NODE_ERROR" if node_type else "NODE_ERROR",
            error_context={
                "node_type": node_type,
                "operation_type": operation_type,
                "node_metadata": node_metadata or {},
                **kwargs.get("error_context", {})
            },
            component=f"{node_type}_node" if node_type else "unknown_node",
            operation=operation_type,
            **kwargs
        )

# Node-specific error classes
class EffectNodeError(NodeOperationError):
    """Error in EFFECT node operations."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            node_type="effect",
            **kwargs
        )

class ComputeNodeError(NodeOperationError):
    """Error in COMPUTE node operations."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            node_type="compute",
            **kwargs
        )

class ReducerNodeError(NodeOperationError):
    """Error in REDUCER node operations."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            node_type="reducer",
            **kwargs
        )

class OrchestratorNodeError(NodeOperationError):
    """Error in ORCHESTRATOR node operations."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            node_type="orchestrator",
            **kwargs
        )
```

#### Subcontract Execution Errors

```
class SubcontractExecutionError(ModelOnexError):
    """
    Error raised during subcontract execution.

    Handles errors in aggregation, FSM, routing, caching,
    and other specialized subcontract operations.
    """

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        subcontract_type: Optional[str] = None,
        execution_phase: Optional[str] = None,
        subcontract_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code=f"SUBCONTRACT_{subcontract_type.upper()}_ERROR" if subcontract_type else "SUBCONTRACT_ERROR",
            error_context={
                "subcontract_type": subcontract_type,
                "execution_phase": execution_phase,
                "subcontract_config": subcontract_config or {},
                **kwargs.get("error_context", {})
            },
            component=f"{subcontract_type}_subcontract" if subcontract_type else "unknown_subcontract",
            operation=execution_phase,
            **kwargs
        )

# Specific subcontract errors
class AggregationError(SubcontractExecutionError):
    """Error in aggregation subcontract execution."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            subcontract_type="aggregation",
            **kwargs
        )

class FSMExecutionError(SubcontractExecutionError):
    """Error in FSM subcontract execution."""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
        **kwargs
    ):
        error_context = kwargs.get("error_context", {})
        error_context.update({
            "current_state": current_state,
            "target_state": target_state
        })
        kwargs["error_context"] = error_context

        super().__init__(
            message=message,
            correlation_id=correlation_id,
            subcontract_type="fsm",
            **kwargs
        )

class RoutingError(SubcontractExecutionError):
    """Error in routing subcontract execution."""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[UUID] = None,
        route_id: Optional[str] = None,
        target_service: Optional[str] = None,
        **kwargs
    ):
        error_context = kwargs.get("error_context", {})
        error_context.update({
            "route_id": route_id,
            "target_service": target_service
        })
        kwargs["error_context"] = error_context

        super().__init__(
            message=message,
            correlation_id=correlation_id,
            subcontract_type="routing",
            **kwargs
        )
```

#### Declarative Node Errors

These error classes support the declarative node validation system introduced in PR #150 (OMN-177). They provide structured error handling for YAML contract binding, purity constraints, runtime execution, and capability validation.

```python
from omnibase_core.errors import (
    AdapterBindingError,
    PurityViolationError,
    NodeExecutionError,
    UnsupportedCapabilityError,
)

# AdapterBindingError - Raised when an adapter cannot bind to a contract
# Use when: YAML/JSON contract parsing fails or adapter-contract mismatch occurs
raise AdapterBindingError(
    "Cannot bind YAML adapter to contract",
    adapter_type="YamlContractAdapter",
    contract_path="nodes/compute/contract.yaml",
)

# With additional context for debugging
raise AdapterBindingError(
    "Contract schema version mismatch",
    adapter_type="YamlContractAdapter",
    contract_path="nodes/effect/contract.yaml",
    operation="load_contract",
    expected_version="2.0",
    actual_version="1.5",
)


# PurityViolationError - Raised when a node violates purity constraints
# Use when: COMPUTE nodes access external state or perform I/O operations
raise PurityViolationError(
    "COMPUTE node accessed external state",
    node_id="node-compute-123",
    violation_type="external_state_access",
)

# Common violation types: "external_state_access", "io_operation", "network_call"
raise PurityViolationError(
    "COMPUTE node performed network I/O during computation",
    node_id="node-compute-data-transformer",
    violation_type="network_call",
    operation="transform_data",
    detected_at="execution_phase",
)


# NodeExecutionError - Raised when runtime execution fails
# Use when: Node processing fails due to runtime conditions
raise NodeExecutionError(
    "Execution failed during compute phase",
    node_id="node-compute-abc",
    execution_phase="compute",
)

# With retry context for transient failures
raise NodeExecutionError(
    "Reducer aggregation timed out",
    node_id="node-reducer-aggregator",
    execution_phase="reduce",
    operation="aggregate_results",
    retry_count=3,
    timeout_ms=5000,
)


# UnsupportedCapabilityError - Raised when contract demands unavailable capability
# Use when: Contract requires features the node cannot provide
raise UnsupportedCapabilityError(
    "Node does not support streaming",
    capability="streaming",
    node_type="COMPUTE",
)

# With available capabilities for debugging
raise UnsupportedCapabilityError(
    "Required capability 'real_time_processing' not available",
    capability="real_time_processing",
    node_type="EFFECT",
    operation="validate_capabilities",
    available_capabilities=["batch_processing", "async_io"],
)
```

**Key Design Principles**:
- All errors inherit from `RuntimeHostError` for consistency
- Include domain-specific attributes (`adapter_type`, `node_id`, `capability`, etc.)
- Support arbitrary `**context` kwargs for additional debugging information
- Serializable for event bus and logging integration
- Default error codes from `EnumCoreErrorCode` (e.g., `ADAPTER_BINDING_ERROR`)

### Centralized Exception Groups

ONEX provides centralized exception type tuples for consistent error handling across the codebase. These groups are defined in `omnibase_core.errors.exception_groups` and should be used instead of ad-hoc exception tuples.

**Import and Usage**:

```python
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS, PYDANTIC_MODEL_ERRORS

try:
    result = model.model_validate(data)
except PYDANTIC_MODEL_ERRORS as e:
    # Handle validation errors consistently
    logger.warning(f"Validation failed: {e}")
```

**Available Exception Groups**:

| Group | Exceptions | Use Case |
|-------|-----------|----------|
| `VALIDATION_ERRORS` | `TypeError`, `ValidationError`, `ValueError` | Type checking, value validation |
| `PYDANTIC_MODEL_ERRORS` | `AttributeError`, `TypeError`, `ValidationError`, `ValueError` | `model_validate()`, `model_dump()`, field access |
| `ATTRIBUTE_ACCESS_ERRORS` | `AttributeError`, `IndexError`, `KeyError`, `TypeError` | Dict keys, object attributes, list indices |
| `YAML_PARSING_ERRORS` | `ValidationError`, `ValueError`, `yaml.YAMLError` | YAML config/contract parsing |
| `JSON_PARSING_ERRORS` | `json.JSONDecodeError`, `TypeError`, `ValidationError`, `ValueError` | JSON data/API response parsing |
| `FILE_IO_ERRORS` | `FileNotFoundError`, `IOError`, `OSError`, `PermissionError` | File read/write operations |
| `NETWORK_ERRORS` | `ConnectionError`, `OSError`, `TimeoutError` | HTTP requests, socket connections |
| `ASYNC_ERRORS` | `asyncio.TimeoutError`, `RuntimeError` | Async task failures |

**Exception Tuple Ordering**: All tuples are alphabetically ordered by exception class name for consistency and readability.

```python
# Correct - alphabetical order
except (AttributeError, TypeError, ValidationError, ValueError) as e:

# Wrong - not alphabetical
except (ValueError, TypeError, AttributeError) as e:
```

#### Async Cancellation Handling

**CRITICAL**: `asyncio.CancelledError` is intentionally NOT included in any exception group. It must be caught separately and **always re-raised** to honor task cancellation semantics:

```python
try:
    await async_operation()
except asyncio.CancelledError:
    # Perform cleanup if needed
    await cleanup_resources()
    raise  # ALWAYS re-raise - never suppress!
except ASYNC_ERRORS as e:
    # Handle other async errors
    logger.error(f"Async operation failed: {e}")
```

**Why**: Suppressing `CancelledError` breaks Python's cooperative cancellation model and can cause tasks to hang indefinitely during shutdown.

#### Exception Handler Comment Markers

When using catch-all or broad exception handlers, document the intent with standardized markers:

| Marker | When to Use | Example Context |
|--------|-------------|-----------------|
| `# fallback-ok:` | Graceful degradation to default values | Config loading, optional features |
| `# catch-all-ok:` | Boundary handlers that must not crash | API endpoints, CLI entry points |
| `# cleanup-resilience-ok:` | Cleanup that must complete | Resource release, rollback |
| `# boundary-ok:` | System/API boundaries | Event handlers, webhooks |
| `# init-errors-ok:` | Initialization with safe defaults | Service startup, lazy loading |
| `# tool-resilience-ok:` | Tool/plugin isolation | mypy plugins, linters |

**Usage Examples**:

```python
# Graceful degradation with explicit marker
try:
    config = load_config(path)
except FILE_IO_ERRORS as e:
    # fallback-ok: use defaults if config unavailable
    logger.warning(f"Config not found, using defaults: {e}")
    config = DEFAULT_CONFIG

# API boundary protection
@app.post("/api/process")
async def process_request(data: dict) -> dict:
    try:
        return await processor.handle(data)
    except Exception as e:
        # boundary-ok: API must return valid JSON response
        logger.error(f"Processing failed: {e}")
        return {"error": str(e), "status": "failed"}

# Cleanup resilience
finally:
    try:
        await connection.close()
    except Exception as e:
        # cleanup-resilience-ok: must not fail during cleanup
        logger.warning(f"Connection close failed: {e}")
```

**Benefits**:
- **Code Review**: Markers explain intentional catch patterns
- **Static Analysis**: Tools can verify markers are present
- **Documentation**: Self-documenting exception handling intent

## Error Handling Patterns

### Pattern 1: Standard Error Handling Decorator

```
from functools import wraps
from typing import Callable, Any
import logging
import traceback

def standard_error_handling(
    error_class: type = ModelOnexError,
    component: str = None,
    operation: str = None,
    recoverable: bool = False,
    log_level: str = "ERROR"
):
    """
    Decorator for standardized error handling across ONEX components.

    Provides consistent error handling with correlation tracking,
    logging, and structured error context.

    Args:
        error_class: Exception class to raise on errors
        component: Component name for error context
        operation: Operation name for error context
        recoverable: Whether errors are generally recoverable
        log_level: Logging level for caught exceptions

    Example:
        @standard_error_handling(
            error_class=EffectNodeError,
            component="database_effect",
            operation="execute_query",
            recoverable=True
        )
        async def execute_database_query(self, query: str, correlation_id: UUID):
            # Implementation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            correlation_id = None

            # Extract correlation_id from arguments
            try:
                # Try to find correlation_id in function arguments
                if 'correlation_id' in kwargs:
                    correlation_id = kwargs['correlation_id']
                elif hasattr(args[0], 'correlation_id') and args[0].correlation_id:
                    correlation_id = args[0].correlation_id
                elif len(args) > 1 and hasattr(args[1], 'correlation_id'):
                    correlation_id = args[1].correlation_id
            except (IndexError, AttributeError):
                pass

            try:
                return await func(*args, **kwargs)
            except ModelOnexError:
                # Re-raise ModelOnexError without modification
                raise
            except Exception as e:
                # Log the original exception
                logger = logging.getLogger(component or func.__module__)
                logger.log(
                    getattr(logging, log_level),
                    f"Error in {operation or func.__name__}: {e}",
                    extra={
                        "correlation_id": str(correlation_id) if correlation_id else None,
                        "component": component,
                        "operation": operation or func.__name__,
                        "traceback": traceback.format_exc()
                    }
                )

                # Create structured ModelOnexError
                raise error_class(
                    message=f"Error in {operation or func.__name__}: {str(e)}",
                    correlation_id=correlation_id,
                    component=component,
                    operation=operation or func.__name__,
                    recoverable=recoverable,
                    error_context={
                        "original_error": str(e),
                        "original_error_type": type(e).__name__,
                        "function": func.__name__,
                        "module": func.__module__
                    }
                ) from e

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Similar implementation for synchronous functions
            correlation_id = None

            try:
                # Extract correlation_id from arguments
                if 'correlation_id' in kwargs:
                    correlation_id = kwargs['correlation_id']
                elif hasattr(args[0], 'correlation_id') and args[0].correlation_id:
                    correlation_id = args[0].correlation_id
                elif len(args) > 1 and hasattr(args[1], 'correlation_id'):
                    correlation_id = args[1].correlation_id
            except (IndexError, AttributeError):
                pass

            try:
                return func(*args, **kwargs)
            except ModelOnexError:
                raise
            except Exception as e:
                logger = logging.getLogger(component or func.__module__)
                logger.log(
                    getattr(logging, log_level),
                    f"Error in {operation or func.__name__}: {e}",
                    extra={
                        "correlation_id": str(correlation_id) if correlation_id else None,
                        "component": component,
                        "operation": operation or func.__name__,
                        "traceback": traceback.format_exc()
                    }
                )

                raise error_class(
                    message=f"Error in {operation or func.__name__}: {str(e)}",
                    correlation_id=correlation_id,
                    component=component,
                    operation=operation or func.__name__,
                    recoverable=recoverable,
                    error_context={
                        "original_error": str(e),
                        "original_error_type": type(e).__name__,
                        "function": func.__name__,
                        "module": func.__module__
                    }
                ) from e

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

# Usage Examples
class DatabaseEffectService(ModelServiceEffect):
    """EFFECT node with standardized error handling."""

    @standard_error_handling(
        error_class=EffectNodeError,
        component="database_effect",
        operation="execute_query",
        recoverable=True
    )
    async def execute_database_query(
        self,
        query: str,
        parameters: Dict[str, Any],
        correlation_id: UUID
    ) -> Dict[str, Any]:
        """Execute database query with error handling."""
        async with self.connection_pool.acquire() as conn:
            cursor = await conn.execute(query, parameters)
            return await cursor.fetchall()

    @standard_error_handling(
        error_class=EffectNodeError,
        component="database_effect",
        operation="execute_transaction",
        recoverable=False
    )
    async def execute_transaction(
        self,
        operations: List[Dict[str, Any]],
        correlation_id: UUID
    ) -> bool:
        """Execute database transaction with error handling."""
        async with self.connection_pool.acquire() as conn:
            async with conn.begin():
                for operation in operations:
                    await conn.execute(operation["query"], operation["parameters"])
                return True
```

### Pattern 2: Circuit Breaker Pattern

```
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from typing import Callable, Any, Optional

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: int = 60           # Seconds before half-open
    success_threshold: int = 3           # Successes to close from half-open
    timeout: int = 30                    # Operation timeout seconds
    monitor_window: int = 300            # Monitoring window seconds

class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern with proper correlation
    tracking and ONEX error integration.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        correlation_id: Optional[UUID] = None
    ):
        self.name = name
        self.config = config
        self.correlation_id = correlation_id
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            ModelOnexError: If function execution fails
        """
        # Check circuit breaker state
        await self._update_state()

        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                message=f"Circuit breaker '{self.name}' is open",
                correlation_id=self.correlation_id,
                error_context={
                    "circuit_breaker_name": self.name,
                    "failure_count": self.failure_count,
                    "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
                },
                component="circuit_breaker",
                operation="circuit_check"
            )

        try:
            # Execute function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            # Record success
            await self._record_success()
            return result

        except asyncio.TimeoutError as e:
            await self._record_failure()
            raise CircuitBreakerTimeoutError(
                message=f"Operation timed out in circuit breaker '{self.name}'",
                correlation_id=self.correlation_id,
                error_context={
                    "circuit_breaker_name": self.name,
                    "timeout_seconds": self.config.timeout
                },
                component="circuit_breaker",
                operation="timeout_check"
            ) from e

        except Exception as e:
            await self._record_failure()

            # Wrap in ModelOnexError if not already
            if not isinstance(e, ModelOnexError):
                raise ModelOnexError(
                    message=f"Circuit breaker '{self.name}' operation failed: {str(e)}",
                    correlation_id=self.correlation_id,
                    error_context={
                        "circuit_breaker_name": self.name,
                        "original_error": str(e),
                        "original_error_type": type(e).__name__
                    },
                    component="circuit_breaker",
                    operation="function_execution"
                ) from e
            else:
                raise

    async def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        now = datetime.now(UTC)

        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and
                now - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0

        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Check if enough successes to close
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0

    async def _record_success(self):
        """Record successful operation."""
        self.last_success_time = datetime.now(UTC)

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    async def _record_failure(self):
        """Record failed operation."""
        self.last_failure_time = datetime.now(UTC)
        self.failure_count += 1

        if (self.state == CircuitBreakerState.CLOSED and
            self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN

        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Go back to open on any failure in half-open state
            self.state = CircuitBreakerState.OPEN

# Circuit breaker error classes
class CircuitBreakerError(ModelOnexError):
    """Base class for circuit breaker errors."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code="CIRCUIT_BREAKER_ERROR",
            **kwargs
        )

class CircuitBreakerOpenError(CircuitBreakerError):
    """Error when circuit breaker is open."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code="CIRCUIT_BREAKER_OPEN",
            recoverable=True,  # Recoverable after timeout
            **kwargs
        )

class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Error when operation times out in circuit breaker."""

    def __init__(self, message: str, correlation_id: Optional[UUID] = None, **kwargs):
        super().__init__(
            message=message,
            correlation_id=correlation_id,
            error_code="CIRCUIT_BREAKER_TIMEOUT",
            recoverable=True,
            **kwargs
        )

# Usage Example
class ExternalServiceEffectNode(ModelServiceEffect):
    """EFFECT node with circuit breaker protection."""

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.circuit_breaker = CircuitBreaker(
            name="external_api_service",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                timeout=30
            )
        )

    async def call_external_api(
        self,
        endpoint: str,
        data: Dict[str, Any],
        correlation_id: UUID
    ) -> Dict[str, Any]:
        """Call external API with circuit breaker protection."""
        self.circuit_breaker.correlation_id = correlation_id

        return await self.circuit_breaker.call(
            self._make_api_call,
            endpoint,
            data,
            correlation_id
        )

    async def _make_api_call(
        self,
        endpoint: str,
        data: Dict[str, Any],
        correlation_id: UUID
    ) -> Dict[str, Any]:
        """Make the actual API call."""
        # Implementation of API call
        pass
```

### Pattern 3: Retry Logic with Exponential Backoff

```python
import asyncio
import logging
import random
from typing import List, Optional, Type, Union

class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]

async def retry_with_backoff(
    func: Callable,
    config: RetryConfig,
    correlation_id: Optional[UUID] = None,
    *args,
    **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff.

    Args:
        func: Function to execute
        config: Retry configuration
        correlation_id: Request correlation ID
        *args: Function positional arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        ModelOnexError: If all retry attempts fail
    """
    last_exception = None
    delay = config.initial_delay

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if exception is retryable
            if not any(isinstance(e, exc_type) for exc_type in config.retryable_exceptions):
                # Not retryable, raise immediately
                if not isinstance(e, ModelOnexError):
                    raise ModelOnexError(
                        message=f"Non-retryable error: {str(e)}",
                        correlation_id=correlation_id,
                        error_context={
                            "original_error": str(e),
                            "original_error_type": type(e).__name__,
                            "attempt": attempt + 1,
                            "retryable": False
                        },
                        component="retry_handler",
                        operation="non_retryable_check"
                    ) from e
                else:
                    raise

            # If this is the last attempt, don't wait
            if attempt == config.max_attempts - 1:
                break

            # Add jitter to prevent thundering herd
            actual_delay = delay
            if config.jitter:
                actual_delay = delay + random.uniform(0, delay * 0.1)

            # Log retry attempt
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {actual_delay:.2f}s: {str(e)}",
                extra={
                    "correlation_id": str(correlation_id) if correlation_id else None,
                    "attempt": attempt + 1,
                    "max_attempts": config.max_attempts,
                    "delay": actual_delay,
                    "error": str(e)
                }
            )

            await asyncio.sleep(actual_delay)

            # Calculate next delay
            delay = min(delay * config.backoff_multiplier, config.max_delay)

    # All attempts failed
    if not isinstance(last_exception, ModelOnexError):
        raise ModelOnexError(
            message=f"All {config.max_attempts} retry attempts failed: {str(last_exception)}",
            correlation_id=correlation_id,
            error_context={
                "max_attempts": config.max_attempts,
                "last_error": str(last_exception),
                "last_error_type": type(last_exception).__name__,
                "total_attempts": config.max_attempts
            },
            component="retry_handler",
            operation="max_attempts_exceeded",
            recoverable=False
        ) from last_exception
    else:
        # Update the ModelOnexError with retry context
        last_exception.error_context.update({
            "retry_attempts": config.max_attempts,
            "all_attempts_failed": True
        })
        raise last_exception

# Retry decorator
def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for delay between attempts
        jitter: Whether to add random jitter to delays
        retryable_exceptions: List of exception types that should trigger retries

    Example:
        @with_retry(
            max_attempts=3,
            initial_delay=1.0,
            retryable_exceptions=[ConnectionError, TimeoutError]
        )
        async def call_external_service(self, correlation_id: UUID):
            # Implementation here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract correlation_id
            correlation_id = None
            if 'correlation_id' in kwargs:
                correlation_id = kwargs['correlation_id']
            elif hasattr(args[0], 'correlation_id'):
                correlation_id = args[0].correlation_id

            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_multiplier=backoff_multiplier,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions
            )

            return await retry_with_backoff(
                func,
                config,
                correlation_id,
                *args,
                **kwargs
            )

        return wrapper
    return decorator

# Usage Example
class ReliableEffectService(ModelServiceEffect):
    """EFFECT node with retry logic."""

    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        retryable_exceptions=[ConnectionError, TimeoutError, HTTPError]
    )
    async def call_external_api(
        self,
        url: str,
        data: Dict[str, Any],
        correlation_id: UUID
    ) -> Dict[str, Any]:
        """Call external API with automatic retry."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers={"X-Correlation-ID": str(correlation_id)},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
```

## Error Recovery Strategies

### Recovery Strategy 1: Graceful Degradation

```
class GracefulDegradationMixin:
    """
    Mixin for implementing graceful degradation patterns.

    Allows services to continue operating with reduced functionality
    when non-critical components fail.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.degraded_services: Set[str] = set()
        self.degradation_reasons: Dict[str, str] = {}

    async def with_graceful_degradation(
        self,
        service_name: str,
        func: Callable,
        fallback_func: Optional[Callable] = None,
        critical: bool = False,
        correlation_id: Optional[UUID] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with graceful degradation support.

        Args:
            service_name: Name of the service being called
            func: Primary function to execute
            fallback_func: Optional fallback function
            critical: Whether service is critical (no degradation allowed)
            correlation_id: Request correlation ID
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result

        Raises:
            ModelOnexError: If critical service fails or no fallback available
        """
        try:
            # If service is already degraded and critical, fail fast
            if service_name in self.degraded_services and critical:
                raise ServiceDegradedError(
                    message=f"Critical service '{service_name}' is degraded",
                    correlation_id=correlation_id,
                    error_context={
                        "service_name": service_name,
                        "degradation_reason": self.degradation_reasons.get(service_name),
                        "critical": critical
                    },
                    component="graceful_degradation",
                    operation="critical_service_check"
                )

            # Try primary function
            result = await func(*args, **kwargs)

            # Service recovered, remove from degraded set
            if service_name in self.degraded_services:
                self.degraded_services.discard(service_name)
                self.degradation_reasons.pop(service_name, None)

                logger = logging.getLogger(__name__)
                logger.info(
                    f"Service '{service_name}' recovered",
                    extra={"correlation_id": str(correlation_id) if correlation_id else None}
                )

            return result

        except Exception as e:
            # Service failed
            self.degraded_services.add(service_name)
            self.degradation_reasons[service_name] = str(e)

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Service '{service_name}' failed, attempting graceful degradation: {str(e)}",
                extra={
                    "correlation_id": str(correlation_id) if correlation_id else None,
                    "service_name": service_name,
                    "critical": critical,
                    "has_fallback": fallback_func is not None
                }
            )

            # If critical service, fail immediately
            if critical:
                if not isinstance(e, ModelOnexError):
                    raise ModelOnexError(
                        message=f"Critical service '{service_name}' failed: {str(e)}",
                        correlation_id=correlation_id,
                        error_context={
                            "service_name": service_name,
                            "critical": True,
                            "original_error": str(e),
                            "original_error_type": type(e).__name__
                        },
                        component="graceful_degradation",
                        operation="critical_service_failure",
                        recoverable=False
                    ) from e
                else:
                    raise

            # Try fallback function
            if fallback_func:
                try:
                    result = await fallback_func(*args, **kwargs)

                    logger.info(
                        f"Fallback succeeded for service '{service_name}'",
                        extra={"correlation_id": str(correlation_id) if correlation_id else None}
                    )

                    return result
                except Exception as fallback_error:
                    # Both primary and fallback failed
                    raise ModelOnexError(
                        message=f"Both primary and fallback failed for service '{service_name}'",
                        correlation_id=correlation_id,
                        error_context={
                            "service_name": service_name,
                            "primary_error": str(e),
                            "fallback_error": str(fallback_error),
                            "primary_error_type": type(e).__name__,
                            "fallback_error_type": type(fallback_error).__name__
                        },
                        component="graceful_degradation",
                        operation="fallback_failure",
                        recoverable=True
                    ) from fallback_error

            # No fallback available, return degraded response
            return self._create_degraded_response(service_name, correlation_id)

    def _create_degraded_response(
        self,
        service_name: str,
        correlation_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Create response indicating service degradation."""
        return {
            "degraded": True,
            "service_name": service_name,
            "degradation_reason": self.degradation_reasons.get(service_name),
            "correlation_id": str(correlation_id) if correlation_id else None,
            "timestamp": datetime.now(UTC).isoformat()
        }

    def get_service_health(self) -> Dict[str, Any]:
        """Get current service health status."""
        return {
            "degraded_services": list(self.degraded_services),
            "degradation_reasons": self.degradation_reasons.copy(),
            "healthy_services": [],  # Would be populated based on successful calls
            "overall_health": "degraded" if self.degraded_services else "healthy"
        }

# Usage Example
class ResilientComputeService(ModelServiceCompute, GracefulDegradationMixin):
    """COMPUTE node with graceful degradation."""

    async def process_data(
        self,
        data: Dict[str, Any],
        correlation_id: UUID
    ) -> Dict[str, Any]:
        """Process data with graceful degradation for non-critical services."""

        # Critical processing (must succeed)
        processed_data = await self.with_graceful_degradation(
            service_name="core_processor",
            func=self._core_processing,
            critical=True,  # No degradation allowed
            correlation_id=correlation_id,
            data=data
        )

        # Optional enrichment (can degrade)
        enriched_data = await self.with_graceful_degradation(
            service_name="data_enricher",
            func=self._enrich_data,
            fallback_func=self._basic_enrichment,
            critical=False,
            correlation_id=correlation_id,
            data=processed_data
        )

        # Optional analytics (can fail completely)
        analytics = await self.with_graceful_degradation(
            service_name="analytics_collector",
            func=self._collect_analytics,
            critical=False,
            correlation_id=correlation_id,
            data=enriched_data
        )

        return {
            "processed_data": processed_data,
            "enriched_data": enriched_data,
            "analytics": analytics,
            "service_health": self.get_service_health(),
            "correlation_id": str(correlation_id)
        }
```

## Error Monitoring and Observability

### Error Metrics Collection

```
from omnibase_core.types.typed_dict_performance_metric_data import TypedDictPerformanceMetricData

class ErrorMetricsCollector:
    """Collect and report error metrics for monitoring."""

    def __init__(self, metrics_service):
        self.metrics_service = metrics_service

    async def record_error(
        self,
        error: ModelOnexError,
        component: str,
        operation: str
    ):
        """Record error metrics for monitoring."""
        metrics = []

        # Error count metric
        metrics.append({
            "metric_name": "onex.error.count",
            "value": 1,
            "timestamp": datetime.now(UTC),
            "component_id": error.correlation_id or UUID("00000000-0000-0000-0000-000000000000"),
            "unit": "count",
            "tags": {
                "error_code": error.error_code,
                "component": component,
                "operation": operation,
                "recoverable": str(error.recoverable)
            },
            "context": {
                "correlation_id": str(error.correlation_id) if error.correlation_id else None,
                "error_message": error.message[:200]  # Truncate long messages
            }
        })

        # Error duration metric (if available in context)
        if "duration_ms" in error.error_context:
            metrics.append({
                "metric_name": "onex.error.duration",
                "value": error.error_context["duration_ms"],
                "timestamp": datetime.now(UTC),
                "component_id": error.correlation_id or UUID("00000000-0000-0000-0000-000000000000"),
                "unit": "ms",
                "tags": {
                    "error_code": error.error_code,
                    "component": component,
                    "operation": operation
                },
                "context": {
                    "correlation_id": str(error.correlation_id) if error.correlation_id else None
                }
            })

        # Send metrics
        await self.metrics_service.send_metrics(metrics)

    async def record_recovery(
        self,
        correlation_id: UUID,
        component: str,
        operation: str,
        recovery_method: str,
        attempts: int
    ):
        """Record successful error recovery."""
        metric = {
            "metric_name": "onex.error.recovery.success",
            "value": 1,
            "timestamp": datetime.now(UTC),
            "component_id": correlation_id,
            "unit": "count",
            "tags": {
                "component": component,
                "operation": operation,
                "recovery_method": recovery_method
            },
            "context": {
                "correlation_id": str(correlation_id),
                "recovery_attempts": attempts
            }
        }

        await self.metrics_service.send_metrics([metric])
```

### Error Alerting

```
class ErrorAlertManager:
    """Manage error alerts and notifications."""

    def __init__(self, alert_service, thresholds: Dict[str, int]):
        self.alert_service = alert_service
        self.thresholds = thresholds
        self.error_counts: Dict[str, int] = {}
        self.last_alert_times: Dict[str, datetime] = {}

    async def process_error(self, error: ModelOnexError, component: str):
        """Process error and trigger alerts if thresholds are exceeded."""
        error_key = f"{component}:{error.error_code}"

        # Update error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Check if threshold exceeded
        threshold = self.thresholds.get(error.error_code, 10)  # Default threshold
        if self.error_counts[error_key] >= threshold:
            await self._trigger_alert(error, component, self.error_counts[error_key])

            # Reset count after alert
            self.error_counts[error_key] = 0

    async def _trigger_alert(
        self,
        error: ModelOnexError,
        component: str,
        count: int
    ):
        """Trigger alert for error threshold breach."""
        alert_key = f"{component}:{error.error_code}"
        now = datetime.now(UTC)

        # Rate limit alerts (max one per hour for same error type)
        last_alert = self.last_alert_times.get(alert_key)
        if last_alert and now - last_alert < timedelta(hours=1):
            return

        alert_data = {
            "alert_type": "error_threshold_exceeded",
            "severity": "high" if not error.recoverable else "medium",
            "component": component,
            "error_code": error.error_code,
            "error_count": count,
            "correlation_id": str(error.correlation_id) if error.correlation_id else None,
            "error_message": error.message,
            "timestamp": now.isoformat(),
            "context": error.error_context
        }

        await self.alert_service.send_alert(alert_data)
        self.last_alert_times[alert_key] = now
```

## Testing Error Handling

### Unit Testing Error Scenarios

```
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

class TestErrorHandling:
    """Comprehensive tests for ONEX error handling."""

    async def test_contract_validation_error(self):
        """Test contract validation error handling."""
        correlation_id = uuid4()

        # Create invalid contract data
        invalid_data = {
            "correlation_id": correlation_id,
            # Missing required fields
        }

        with pytest.raises(ContractValidationError) as exc_info:
            ModelWorkflowConfig(**invalid_data)

        error = exc_info.value
        assert error.correlation_id == correlation_id
        assert error.error_code == "CONTRACT_VALIDATION_FAILED"
        assert error.recoverable is True
        assert "validation_errors" in error.error_context

    async def test_node_operation_error_propagation(self):
        """Test error propagation through node operations."""
        correlation_id = uuid4()

        # Mock a service that raises an exception
        mock_service = AsyncMock(side_effect=ConnectionError("Database unavailable"))

        effect_service = TestEffectService()
        effect_service.database_service = mock_service

        with pytest.raises(EffectNodeError) as exc_info:
            await effect_service.execute_database_operation(correlation_id)

        error = exc_info.value
        assert error.correlation_id == correlation_id
        assert error.error_code == "EFFECT_NODE_ERROR"
        assert "original_error" in error.error_context
        assert error.error_context["original_error"] == "Database unavailable"

    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker error handling."""
        correlation_id = uuid4()

        # Create circuit breaker
        circuit_breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1),
            correlation_id=correlation_id
        )

        # Mock function that always fails
        failing_func = AsyncMock(side_effect=Exception("Service failure"))

        # First failure
        with pytest.raises(ModelOnexError):
            await circuit_breaker.call(failing_func)

        # Second failure - should open circuit
        with pytest.raises(ModelOnexError):
            await circuit_breaker.call(failing_func)

        # Third call - should be rejected by open circuit
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await circuit_breaker.call(failing_func)

        error = exc_info.value
        assert error.correlation_id == correlation_id
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
        assert error.recoverable is True

    async def test_retry_logic(self):
        """Test retry logic with exponential backoff."""
        correlation_id = uuid4()

        # Mock function that fails twice then succeeds
        call_count = 0
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Temporary failure")
            return {"success": True}

        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        result = await retry_with_backoff(flaky_function, config, correlation_id)

        assert result == {"success": True}
        assert call_count == 3

    async def test_graceful_degradation(self):
        """Test graceful degradation behavior."""
        correlation_id = uuid4()

        service = TestServiceWithDegradation()

        # Mock primary service to fail, fallback to succeed
        primary_func = AsyncMock(side_effect=Exception("Primary service down"))
        fallback_func = AsyncMock(return_value={"degraded": True, "data": "fallback_data"})

        result = await service.with_graceful_degradation(
            service_name="test_service",
            func=primary_func,
            fallback_func=fallback_func,
            critical=False,
            correlation_id=correlation_id
        )

        assert result["degraded"] is True
        assert result["data"] == "fallback_data"
        assert "test_service" in service.degraded_services

    async def test_error_context_preservation(self):
        """Test that error context is preserved through error chain."""
        correlation_id = uuid4()
        original_context = {"user_id": "123", "operation": "data_processing"}

        try:
            # Simulate nested error creation
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ModelOnexError(
                    message="Processing failed",
                    correlation_id=correlation_id,
                    error_context=original_context,
                    component="processor",
                    operation="process_data"
                ) from e
        except ModelOnexError as final_error:
            assert final_error.correlation_id == correlation_id
            assert final_error.error_context["user_id"] == "123"
            assert final_error.error_context["operation"] == "data_processing"
            assert final_error.component == "processor"
            assert final_error.__cause__ is not None
            assert isinstance(final_error.__cause__, ValueError)

# Mock classes for testing
class TestEffectService:
    @standard_error_handling(
        error_class=EffectNodeError,
        component="test_effect",
        operation="database_operation"
    )
    async def execute_database_operation(self, correlation_id: UUID):
        await self.database_service()

class TestServiceWithDegradation(GracefulDegradationMixin):
    pass
```

## Validator Error Handling (Pydantic v2+)

### Pattern: ModelOnexError in @field_validator

**Decision**: Use `ModelOnexError` in Pydantic validators instead of `ValueError` or `PydanticCustomError`.

**Rationale**:
1. **Framework Consistency**: All ONEX errors use ModelOnexError (100% coverage across 200+ validators)
2. **Structured Context**: Machine-readable error codes, rich debugging context
3. **Future-Proof**: Compatible with Pydantic v2+, migration path documented for v3+

**Example**:
```python
from pydantic import BaseModel, field_validator
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class ModelReducerOutput(BaseModel):
    processing_time_ms: float

    @field_validator("processing_time_ms")
    @classmethod
    def validate_processing_time_ms(cls, v: float) -> float:
        """Validate processing_time_ms follows sentinel pattern.

        Raises:
            ModelOnexError: If validation fails
        """
        if v < -1.0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"processing_time_ms must be >= 0.0 or exactly -1.0, got {v}",
                context={
                    "value": v,
                    "field": "processing_time_ms",
                    "sentinel_value": -1.0,
                },
            )
        return v
```

**Pydantic Compatibility**:
- Pydantic v2 propagates ModelOnexError directly (no wrapping in ValidationError)
- Structured error context fully preserved (error_code, message, context dict)
- Callers receive ModelOnexError instances with all metadata intact

**Migration Strategy**:
- **If Pydantic v3 breaks compatibility**: Use adapter pattern (`to_pydantic_error`)
- **See**: [ADR-012: Validator Error Handling](../decisions/ADR-012-VALIDATOR-ERROR-HANDLING.md)

**Reference Implementation**:
- `model_reducer_output.py` - Sentinel value validation
- `model_typed_mapping.py` - Type validation (6 validators)
- `model_event_bus_output_state.py` - State validation (3 validators)

---

## Summary

This error handling framework provides:

1. **Structured Error Classes**: Comprehensive ONEX error hierarchy with correlation tracking
2. **Error Handling Patterns**: Decorators, circuit breakers, retry logic, and graceful degradation
3. **Recovery Strategies**: Multiple approaches to handle and recover from failures
4. **Monitoring Integration**: Error metrics collection and alerting capabilities
5. **Testing Framework**: Comprehensive testing patterns for all error scenarios
6. **Validator Error Handling**: ModelOnexError pattern for Pydantic validators with future migration path

All error handling follows ONEX principles with:
- Complete correlation ID preservation
- Structured error context
- Proper error classification
- Recovery and monitoring capabilities
- Zero tolerance for incomplete error information
- Framework consistency (100% ModelOnexError coverage)

### Related Documentation

- [Error Code Standards](ERROR_CODE_STANDARDS.md) - Complete error code format specification
- [Centralized Error Pattern](../../src/omnibase_core/constants/constants_error.py) - Single source of truth for error code validation
- [Centralized Exception Groups](../../src/omnibase_core/errors/exception_groups.py) - Standardized exception type tuples
- [Error Handling Decorators](../../src/omnibase_core/decorators/decorator_error_handling.py) - Boilerplate-eliminating decorators
- [ADR-012: Validator Error Handling](../decisions/ADR-012-VALIDATOR-ERROR-HANDLING.md) - Decision rationale and Pydantic compatibility
- [Node Building Guide](../guides/node-building/README.md) - Node validation patterns
- [Reducer Output Model](../../src/omnibase_core/models/reducer/model_reducer_output.py) - Reference implementation

---

*This error handling documentation ensures robust, maintainable, and observable error management across the entire ONEX Four-Node Architecture with comprehensive coverage of all failure scenarios.*
