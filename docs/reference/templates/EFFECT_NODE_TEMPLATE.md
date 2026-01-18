> **Navigation**: [Home](../../index.md) > [Reference](../README.md) > Templates > EFFECT Node

# EFFECT Node Template

## Overview

This template provides the unified architecture pattern for ONEX EFFECT nodes. EFFECT nodes are responsible for all external interactions and side effects within the ONEX ecosystem, including API calls, database operations, file system interactions, and event emission.

## Key Characteristics

- **External I/O Operations**: Handles all interactions with external systems
- **Transaction Support**: Atomic operations with automatic rollback on failure
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breaker**: Fault tolerance for repeated failures
- **Type Safety**: Full Pydantic validation with comprehensive error handling
- **Asynchronous Processing**: All operations are async for I/O efficiency

## Directory Structure

```
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_effect/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py
│                   ├── config.py
│                   ├── contracts/
│                   │   ├── __init__.py
│                   │   ├── effect_contract.py
│                   │   └── subcontracts/
│                   │       ├── __init__.py
│                   │       ├── effect_subcontract.yaml
│                   │       ├── input_subcontract.yaml
│                   │       ├── output_subcontract.yaml
│                   │       └── config_subcontract.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_effect_input.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_effect_output.py
│                   │   └── model_{DOMAIN}_{MICROSERVICE_NAME}_effect_config.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   └── enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type.py
│                   ├── handlers/
│                   │   ├── __init__.py
│                   │   ├── http_handler.py
│                   │   ├── database_handler.py
│                   │   └── file_handler.py
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_effect/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_config.py
                    ├── test_contracts.py
                    ├── test_handlers.py
                    └── test_models.py
```

## Template Files

### 1. Node Implementation (`node.py`)

```python
"""ONEX EFFECT node for {DOMAIN} {MICROSERVICE_NAME} operations."""

import asyncio
import time
from typing import Any
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

from pydantic import ValidationError
# v0.4.0 unified node imports
from omnibase_core.nodes import (
    NodeEffect,
    ModelEffectInput,
    ModelEffectOutput,
    ModelEffectTransaction,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import (
    EnumEffectType,
    EnumTransactionState,
    EnumCircuitBreakerState,
)
from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.utils.error_sanitizer import ErrorSanitizer

from .config import {DomainCamelCase}{MicroserviceCamelCase}EffectConfig
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_effect_input import Model{DomainCamelCase}{MicroserviceCamelCase}EffectInput
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_effect_output import Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType
from .handlers.http_handler import HttpHandler
from .handlers.database_handler import DatabaseHandler
from .handlers.file_handler import FileHandler


class Node{DomainCamelCase}{MicroserviceCamelCase}Effect(NodeEffect):
    """EFFECT node for {DOMAIN} {MICROSERVICE_NAME} external I/O operations.

    This node provides production-ready external interaction capabilities for {DOMAIN} domain
    operations, focusing on {MICROSERVICE_NAME} side effects with transaction support.

    Key Features:
    - Transaction management with automatic rollback
    - Retry logic with exponential backoff
    - Circuit breaker for fault tolerance
    - Comprehensive error handling with sanitization
    - Performance monitoring and metrics

    Thread Safety:
        WARNING: NodeEffect instances are NOT thread-safe. Do not share
        instances across threads. Each thread should create its own instance.

    Example:
        ```python
        from omnibase_core.models.container.model_onex_container import ModelONEXContainer

        container = ModelONEXContainer()
        node = Node{DomainCamelCase}{MicroserviceCamelCase}Effect(container)
        node.effect_subcontract = effect_subcontract  # Load from YAML

        result = await node.process(ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"endpoint": "/users", "method": "POST"},
        ))
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the EFFECT node with container dependency injection.

        Args:
            container: ONEX container for dependency injection and service resolution

        Note:
            After construction, set `effect_subcontract` before calling `process()`.
            Alternatively, use contract auto-loading via MixinContractMetadata.
        """
        super().__init__(container)

        # Initialize handlers for different effect types
        self._http_handler = HttpHandler()
        self._database_handler = DatabaseHandler()
        self._file_handler = FileHandler()
        self._error_sanitizer = ErrorSanitizer()

        # Performance tracking
        self._effect_metrics: list[dict[str, Any]] = []
        self._operation_counts: dict[str, int] = {}

        # Get logger from container
        self._logger = container.get_service("ProtocolLogger")

    @asynccontextmanager
    async def _performance_tracking(self, operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType):
        """Track performance metrics for effect operations."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._effect_metrics.append({
                "operation": operation_type,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
            self._operation_counts[str(operation_type)] = (
                self._operation_counts.get(str(operation_type), 0) + 1
            )

    async def execute_{DOMAIN}_{MICROSERVICE_NAME}_effect(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}EffectInput
    ) -> Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput:
        """Execute {DOMAIN} {MICROSERVICE_NAME} effect operation with typed interface.

        This is the business logic interface that provides type-safe effect
        execution without ONEX infrastructure concerns.

        Args:
            input_data: Validated input data for the effect operation

        Returns:
            Effect output with results, transaction state, and metadata

        Raises:
            ModelOnexError: If effect operation fails after all retries
        """
        start_time = time.perf_counter()

        async with self._performance_tracking(input_data.operation_type):
            try:
                # Convert domain model to ModelEffectInput
                effect_input = self._convert_to_effect_input(input_data)

                # Execute via base NodeEffect.process() for retry/circuit breaker
                effect_output = await self.process(effect_input)

                # Build domain-specific output
                return Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(
                    operation_type=input_data.operation_type,
                    success=(effect_output.transaction_state == EnumTransactionState.COMMITTED),
                    result=effect_output.result,
                    operation_id=effect_output.operation_id,
                    transaction_state=effect_output.transaction_state,
                    processing_time_ms=effect_output.processing_time_ms,
                    retry_count=effect_output.retry_count,
                    side_effects_applied=effect_output.side_effects_applied,
                    rollback_operations=effect_output.rollback_operations,
                    metadata=effect_output.metadata,
                )

            except ValidationError as e:
                sanitized_error = self._error_sanitizer.sanitize_validation_error(str(e))
                processing_time = (time.perf_counter() - start_time) * 1000
                return Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    operation_id=input_data.operation_id,
                    transaction_state=EnumTransactionState.FAILED,
                    processing_time_ms=processing_time,
                    error_message=f"Input validation failed: {sanitized_error}",
                )

            except asyncio.TimeoutError:
                processing_time = (time.perf_counter() - start_time) * 1000
                return Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    operation_id=input_data.operation_id,
                    transaction_state=EnumTransactionState.FAILED,
                    processing_time_ms=processing_time,
                    error_message="Effect operation timeout exceeded",
                )

            except ModelOnexError as e:
                processing_time = (time.perf_counter() - start_time) * 1000
                return Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    operation_id=input_data.operation_id,
                    transaction_state=EnumTransactionState.FAILED,
                    processing_time_ms=processing_time,
                    error_message=e.message,
                )

            except Exception as e:
                sanitized_error = self._error_sanitizer.sanitize_error(str(e))
                processing_time = (time.perf_counter() - start_time) * 1000
                return Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(
                    operation_type=input_data.operation_type,
                    success=False,
                    operation_id=input_data.operation_id,
                    transaction_state=EnumTransactionState.FAILED,
                    processing_time_ms=processing_time,
                    error_message=f"Effect operation failed: {sanitized_error}",
                )

    def _convert_to_effect_input(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}EffectInput
    ) -> ModelEffectInput:
        """Convert domain model to base ModelEffectInput.

        Args:
            input_data: Domain-specific input model

        Returns:
            Base ModelEffectInput for NodeEffect.process()
        """
        return ModelEffectInput(
            effect_type=self._map_operation_to_effect_type(input_data.operation_type),
            operation_data=input_data.operation_data,
            operation_id=input_data.operation_id,
            transaction_enabled=input_data.transaction_enabled,
            retry_enabled=input_data.retry_enabled,
            max_retries=input_data.max_retries,
            retry_delay_ms=input_data.retry_delay_ms,
            circuit_breaker_enabled=input_data.circuit_breaker_enabled,
            timeout_ms=input_data.timeout_ms,
            metadata=input_data.metadata,
        )

    def _map_operation_to_effect_type(
        self,
        operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType
    ) -> EnumEffectType:
        """Map domain operation type to ONEX effect type.

        Args:
            operation_type: Domain-specific operation type

        Returns:
            Corresponding EnumEffectType
        """
        mapping = {
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.HTTP_REQUEST: EnumEffectType.API_CALL,
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.DATABASE_QUERY: EnumEffectType.DATABASE_OPERATION,
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.FILE_WRITE: EnumEffectType.FILE_OPERATION,
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.FILE_READ: EnumEffectType.FILE_OPERATION,
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.EVENT_PUBLISH: EnumEffectType.EVENT_EMISSION,
        }
        return mapping.get(operation_type, EnumEffectType.API_CALL)

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get current performance metrics for monitoring.

        Returns:
            Dictionary with performance statistics
        """
        if not self._effect_metrics:
            return {
                "total_operations": 0,
                "average_duration_ms": 0.0,
                "operation_counts": {},
                "circuit_breaker_states": {},
            }

        total_operations = len(self._effect_metrics)
        average_duration = sum(m["duration_ms"] for m in self._effect_metrics) / total_operations

        return {
            "total_operations": total_operations,
            "average_duration_ms": round(average_duration, 2),
            "max_duration_ms": max(m["duration_ms"] for m in self._effect_metrics),
            "min_duration_ms": min(m["duration_ms"] for m in self._effect_metrics),
            "operation_counts": self._operation_counts.copy(),
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status information including handler states
        """
        try:
            # Check handler connectivity
            http_healthy = await self._http_handler.health_check()
            db_healthy = await self._database_handler.health_check()
            file_healthy = await self._file_handler.health_check()

            # Check recent performance
            recent_metrics = [
                m for m in self._effect_metrics
                if time.time() - m["timestamp"] < 300  # Last 5 minutes
            ]

            avg_performance = (
                sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)
                if recent_metrics else 0.0
            )

            all_healthy = all([http_healthy, db_healthy, file_healthy])

            return {
                "status": "healthy" if all_healthy else "degraded",
                "handlers": {
                    "http": "healthy" if http_healthy else "unhealthy",
                    "database": "healthy" if db_healthy else "unhealthy",
                    "file": "healthy" if file_healthy else "unhealthy",
                },
                "performance": {
                    "average_duration_ms": round(avg_performance, 2),
                    "recent_operations": len(recent_metrics),
                },
                "timestamp": time.time(),
            }

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "timestamp": time.time(),
            }
```

### 2. Configuration (`config.py`)

```python
"""Configuration for {DOMAIN} {MICROSERVICE_NAME} EFFECT node."""

from typing import Any, Type, TypeVar
from pydantic import BaseModel, Field, field_validator

ConfigT = TypeVar('ConfigT', bound='BaseModel')


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    base_delay_ms: int = Field(default=1000, ge=100, le=30000, description="Base delay between retries")
    max_delay_ms: int = Field(default=30000, ge=1000, le=120000, description="Maximum delay between retries")
    backoff_strategy: str = Field(default="exponential", pattern="^(constant|linear|exponential)$", description="Backoff strategy")


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""

    enabled: bool = Field(default=True, description="Enable circuit breaker")
    failure_threshold: int = Field(default=5, ge=1, le=100, description="Failures before opening")
    success_threshold: int = Field(default=3, ge=1, le=20, description="Successes before closing")
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="Time before half-open")


class TransactionConfig(BaseModel):
    """Configuration for transaction behavior."""

    enabled: bool = Field(default=True, description="Enable transaction support")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Transaction timeout")
    isolation_level: str = Field(default="read_committed", pattern="^(read_uncommitted|read_committed|repeatable_read|serializable)$")


class HttpConfig(BaseModel):
    """Configuration for HTTP operations."""

    timeout_ms: int = Field(default=30000, ge=1000, le=120000, description="HTTP request timeout")
    max_connections: int = Field(default=100, ge=1, le=1000, description="Max connection pool size")
    retry_on_status: list[int] = Field(default=[429, 502, 503, 504], description="Status codes to retry")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class DatabaseConfig(BaseModel):
    """Configuration for database operations."""

    connection_timeout_ms: int = Field(default=10000, ge=1000, le=60000, description="Connection timeout")
    query_timeout_ms: int = Field(default=30000, ge=1000, le=120000, description="Query timeout")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    pool_max_overflow: int = Field(default=20, ge=0, le=100, description="Pool overflow connections")


class FileConfig(BaseModel):
    """Configuration for file operations."""

    max_file_size_mb: float = Field(default=100.0, ge=0.1, le=10000.0, description="Max file size in MB")
    buffer_size_kb: int = Field(default=64, ge=4, le=1024, description="Buffer size for file operations")
    atomic_writes: bool = Field(default=True, description="Use atomic write operations")


class {DomainCamelCase}{MicroserviceCamelCase}EffectConfig(BaseModel):
    """Configuration for {DOMAIN} {MICROSERVICE_NAME} EFFECT operations."""

    # Core effect settings
    default_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="Default operation timeout in milliseconds"
    )

    max_concurrent_effects: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum concurrent effect operations"
    )

    # Component configurations
    retry_config: RetryConfig = Field(default_factory=RetryConfig)
    circuit_breaker_config: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    transaction_config: TransactionConfig = Field(default_factory=TransactionConfig)
    http_config: HttpConfig = Field(default_factory=HttpConfig)
    database_config: DatabaseConfig = Field(default_factory=DatabaseConfig)
    file_config: FileConfig = Field(default_factory=FileConfig)

    # Domain-specific settings
    domain_specific_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific configuration parameters"
    )

    @field_validator('default_timeout_ms')
    @classmethod
    def validate_timeout(cls, v: int, info) -> int:
        """Ensure default timeout is reasonable."""
        if v < 1000:
            raise ValueError("Timeout must be at least 1000ms for external operations")
        return v

    @classmethod
    def for_environment(cls: Type[ConfigT], environment: str) -> ConfigT:
        """Create environment-specific configuration.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Environment-optimized configuration
        """
        if environment == "production":
            return cls(
                default_timeout_ms=15000,
                max_concurrent_effects=100,
                retry_config=RetryConfig(
                    max_retries=3,
                    base_delay_ms=500,
                    backoff_strategy="exponential"
                ),
                circuit_breaker_config=CircuitBreakerConfig(
                    enabled=True,
                    failure_threshold=5,
                    timeout_seconds=30
                ),
                http_config=HttpConfig(
                    timeout_ms=15000,
                    max_connections=200
                ),
            )

        elif environment == "staging":
            return cls(
                default_timeout_ms=30000,
                max_concurrent_effects=50,
                retry_config=RetryConfig(
                    max_retries=3,
                    base_delay_ms=1000
                ),
            )

        else:  # development
            return cls(
                default_timeout_ms=60000,
                max_concurrent_effects=20,
                retry_config=RetryConfig(
                    max_retries=2,
                    base_delay_ms=2000
                ),
                circuit_breaker_config=CircuitBreakerConfig(
                    enabled=False
                ),
            )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }
```

### 3. Input Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_effect_input.py`)

```python
"""Input model for {DOMAIN} {MICROSERVICE_NAME} EFFECT operations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator

from ..enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType


class Model{DomainCamelCase}{MicroserviceCamelCase}EffectInput(BaseModel):
    """Input model for {DOMAIN} {MICROSERVICE_NAME} effect operations.

    Strongly typed input wrapper for side effect operations with comprehensive
    configuration for transactions, retries, circuit breakers, and timeouts.
    """

    operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType = Field(
        description="Type of effect operation to perform"
    )

    operation_data: dict[str, Any] = Field(
        description="Payload data for the operation"
    )

    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for tracking this operation"
    )

    # Transaction configuration
    transaction_enabled: bool = Field(
        default=True,
        description="Whether to wrap the operation in a transaction"
    )

    # Retry configuration
    retry_enabled: bool = Field(
        default=True,
        description="Whether to retry failed operations"
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )

    retry_delay_ms: int = Field(
        default=1000,
        ge=100,
        le=30000,
        description="Base delay between retries in milliseconds"
    )

    # Circuit breaker configuration
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether to use circuit breaker pattern"
    )

    # Timeout configuration
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="Maximum operation timeout in milliseconds"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata for tracking"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this input was created"
    )

    @field_validator('operation_data')
    @classmethod
    def validate_operation_data(cls, v: dict[str, Any], info) -> dict[str, Any]:
        """Validate operation data based on operation type."""
        if not isinstance(v, dict):
            raise ValueError("Operation data must be a dictionary")

        operation_type = info.data.get('operation_type')

        if operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.HTTP_REQUEST:
            required_fields = ['url', 'method']
            missing_fields = [field for field in required_fields if field not in v]
            if missing_fields:
                raise ValueError(f"HTTP operation missing required fields: {missing_fields}")

        elif operation_type == Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.DATABASE_QUERY:
            if 'query' not in v and 'operation' not in v:
                raise ValueError("Database operation requires 'query' or 'operation' field")

        elif operation_type in [
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.FILE_WRITE,
            Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType.FILE_READ
        ]:
            if 'path' not in v:
                raise ValueError("File operation requires 'path' field")

        return v

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "operation_type": "http_request",
                "operation_data": {
                    "url": "https://api.example.com/users",
                    "method": "POST",
                    "body": {"name": "John Doe"}
                },
                "transaction_enabled": True,
                "retry_enabled": True,
                "max_retries": 3,
                "timeout_ms": 30000
            }
        }
    }
```

### 4. Output Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_effect_output.py`)

```python
"""Output model for {DOMAIN} {MICROSERVICE_NAME} EFFECT operations."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumTransactionState
from ..enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type import Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType


class Model{DomainCamelCase}{MicroserviceCamelCase}EffectOutput(BaseModel):
    """Output model for {DOMAIN} {MICROSERVICE_NAME} effect operations.

    Strongly typed output wrapper containing the operation result along with
    transaction status, timing metrics, and execution audit trail.
    """

    operation_type: Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType = Field(
        description="Type of operation that was executed"
    )

    success: bool = Field(
        description="Whether the effect operation succeeded"
    )

    result: Any = Field(
        default=None,
        description="Operation result data"
    )

    operation_id: UUID = Field(
        description="Operation ID from the corresponding input"
    )

    transaction_state: EnumTransactionState = Field(
        description="Current state of the transaction"
    )

    processing_time_ms: float = Field(
        ge=0,
        description="Total processing time in milliseconds"
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of failed attempts before success or final failure"
    )

    side_effects_applied: list[str] = Field(
        default_factory=list,
        description="List of side effects successfully applied"
    )

    rollback_operations: list[str] = Field(
        default_factory=list,
        description="List of rollback operations if transaction was rolled back"
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this output was created"
    )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "operation_type": "http_request",
                "success": True,
                "result": {"id": 123, "status": "created"},
                "operation_id": "550e8400-e29b-41d4-a716-446655440000",
                "transaction_state": "committed",
                "processing_time_ms": 245.7,
                "retry_count": 0,
                "side_effects_applied": ["create_user_api_call"],
            }
        }
    }
```

### 5. Operation Type Enum (`enum_{DOMAIN}_{MICROSERVICE_NAME}_operation_type.py`)

```python
"""Operation type enumeration for {DOMAIN} {MICROSERVICE_NAME} EFFECT operations."""

from enum import Enum
from typing import Never, NoReturn


class Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType(str, Enum):
    """Enumeration of supported {DOMAIN} {MICROSERVICE_NAME} effect operation types."""

    HTTP_REQUEST = "http_request"
    """Make HTTP/HTTPS API requests to external services."""

    DATABASE_QUERY = "database_query"
    """Execute database queries and operations."""

    FILE_WRITE = "file_write"
    """Write data to the file system."""

    FILE_READ = "file_read"
    """Read data from the file system."""

    EVENT_PUBLISH = "event_publish"
    """Publish events to message bus or event stream."""

    CACHE_OPERATION = "cache_operation"
    """Interact with cache services (Redis, Memcached, etc.)."""

    EXTERNAL_SERVICE = "external_service"
    """Call external third-party services."""

    HEALTH_CHECK = "health_check"
    """Perform health check operations on external dependencies."""

    @classmethod
    def get_transactional_operations(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType"]:
        """Get operations that support transactions."""
        return [
            cls.DATABASE_QUERY,
            cls.FILE_WRITE,
        ]

    @classmethod
    def get_idempotent_operations(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType"]:
        """Get operations that are naturally idempotent."""
        return [
            cls.FILE_READ,
            cls.CACHE_OPERATION,
            cls.HEALTH_CHECK,
        ]

    @classmethod
    def get_retriable_operations(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}OperationType"]:
        """Get operations safe for automatic retry."""
        return [
            cls.HTTP_REQUEST,
            cls.DATABASE_QUERY,
            cls.CACHE_OPERATION,
            cls.EXTERNAL_SERVICE,
            cls.HEALTH_CHECK,
        ]

    def is_transactional(self) -> bool:
        """Check if this operation type supports transactions."""
        return self in self.get_transactional_operations()

    def is_idempotent(self) -> bool:
        """Check if this operation type is naturally idempotent."""
        return self in self.get_idempotent_operations()

    def is_retriable(self) -> bool:
        """Check if this operation type is safe for automatic retry."""
        return self in self.get_retriable_operations()

    def get_default_timeout_ms(self) -> int:
        """Get default timeout for this operation type."""
        timeout_map = {
            type(self).HTTP_REQUEST: 30000,
            type(self).DATABASE_QUERY: 30000,
            type(self).FILE_WRITE: 60000,
            type(self).FILE_READ: 10000,
            type(self).EVENT_PUBLISH: 5000,
            type(self).CACHE_OPERATION: 5000,
            type(self).EXTERNAL_SERVICE: 30000,
            type(self).HEALTH_CHECK: 5000,
        }
        return timeout_map.get(self, 30000)

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements."""
        raise AssertionError(f"Unhandled enum value: {value}")
```

### 6. Effect Subcontract YAML (`subcontracts/effect_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} EFFECT Subcontract
# Defines effect operations with retry, circuit breaker, and transaction config

api_version: "v1.0.0"
kind: "EffectSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-effect"
  description: "Effect operations for {DOMAIN} {MICROSERVICE_NAME}"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "EFFECT"

specification:
  version:
    major: 1
    minor: 0
    patch: 0
  subcontract_name: "{DOMAIN}_{MICROSERVICE_NAME}_effect"
  description: "External I/O operations for {DOMAIN} {MICROSERVICE_NAME}"
  execution_mode: sequential_abort  # Stop on first failure

# Default retry policy applied to all operations
default_retry_policy:
  max_retries: 3
  backoff_strategy: exponential
  base_delay_ms: 1000
  max_delay_ms: 30000

# Default circuit breaker settings
default_circuit_breaker:
  enabled: true
  failure_threshold: 5
  success_threshold: 3
  timeout_seconds: 60

# Transaction configuration
transaction:
  enabled: true
  timeout_seconds: 30
  isolation_level: read_committed

# Effect operations
operations:
  - operation_name: create_user_api
    description: "Create user via REST API"
    io_config:
      handler_type: http
      url_template: "https://api.example.com/users"
      method: POST
      body_template: '{"name": "${input.name}", "email": "${input.email}"}'
      headers:
        Content-Type: "application/json"
        Authorization: "Bearer ${env.API_TOKEN}"
      timeout_ms: 30000
    response_handling:
      success_codes: [200, 201]
      extract_fields:
        user_id: "$.id"
        created_at: "$.created_at"

  - operation_name: save_to_database
    description: "Persist data to database"
    io_config:
      handler_type: database
      operation: insert
      table: "users"
      fields:
        - name
        - email
        - external_id
      timeout_ms: 10000
    response_handling:
      success_indicator: rows_affected > 0
      extract_fields:
        record_id: "$.lastrowid"

  - operation_name: write_audit_log
    description: "Write audit log to file"
    io_config:
      handler_type: file
      operation: append
      path_template: "/var/log/{DOMAIN}/${date}/audit.log"
      format: json
      timeout_ms: 5000

  - operation_name: publish_event
    description: "Publish event to message bus"
    io_config:
      handler_type: event
      topic: "{DOMAIN}.{MICROSERVICE_NAME}.events"
      event_type: "user.created"
      payload_template:
        event_id: "${uuid}"
        timestamp: "${now}"
        data: "${input}"
      timeout_ms: 5000

examples:
  - name: "create_user_flow"
    description: "Complete user creation with API, DB, and events"
    data:
      input:
        name: "John Doe"
        email: "john@example.com"
      expected_operations:
        - create_user_api
        - save_to_database
        - write_audit_log
        - publish_event
```

### 7. Manifest (`manifest.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} EFFECT Node Manifest
# Defines metadata, dependencies, and deployment specifications

api_version: "v1.0.0"
kind: "NodeManifest"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-effect"
  description: "EFFECT node for {DOMAIN} {MICROSERVICE_NAME} external operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  microservice_name: "{MICROSERVICE_NAME}"
  node_type: "EFFECT"
  created_at: "2024-01-15T10:00:00Z"
  updated_at: "2024-01-15T10:00:00Z"
  maintainers:
    - "team@{DOMAIN}.com"
  tags:
    - "effect"
    - "external-io"
    - "api"
    - "database"
    - "{DOMAIN}"
    - "onex-v4"

specification:
  # Node classification
  node_class: "EFFECT"
  processing_type: "asynchronous"
  stateful: false

  # Performance characteristics
  performance:
    expected_latency_ms: 500
    max_latency_ms: 30000
    throughput_ops_per_second: 100
    memory_requirement_mb: 256
    cpu_requirement_cores: 0.5
    scaling_factor: "horizontal"

  # Reliability requirements
  reliability:
    availability_target: "99.9%"
    error_rate_target: "0.5%"
    recovery_time_target_seconds: 30
    circuit_breaker_enabled: true
    retry_policy: "exponential_backoff"
    transaction_support: true

  # Security requirements
  security:
    input_validation: "strict"
    output_sanitization: "enabled"
    secret_handling: "environment_variables"
    audit_logging: "enabled"
    encryption_in_transit: "required"

# Dependency specifications
dependencies:
  runtime:
    python: ">=3.12,<4.0"
    pydantic: ">=2.0.0"
    httpx: ">=0.24.0"
    asyncio: "builtin"

  internal:
    omnibase_core:
      version: ">=0.4.0"
      components:
        - "nodes.node_effect"
        - "models.effect.model_effect_input"
        - "models.effect.model_effect_output"
        - "enums.enum_effect_types"

  external:
    httpx: ">=0.24.0"      # HTTP client
    sqlalchemy: ">=2.0.0"  # Database ORM
    redis: ">=4.0.0"       # Cache client

# Interface contracts
contracts:
  effect:
    contract_file: "subcontracts/effect_subcontract.yaml"
    validation_level: "strict"

  input:
    contract_file: "subcontracts/input_subcontract.yaml"
    validation_level: "strict"

  output:
    contract_file: "subcontracts/output_subcontract.yaml"
    validation_level: "strict"

# Monitoring and observability
monitoring:
  metrics:
    - name: "effect_duration_seconds"
      type: "histogram"
      description: "Time spent on effect operations"
      labels: ["operation_type", "success", "retry_count"]

    - name: "effect_errors_total"
      type: "counter"
      description: "Total effect operation errors"
      labels: ["operation_type", "error_type"]

    - name: "circuit_breaker_state"
      type: "gauge"
      description: "Circuit breaker state (0=closed, 1=open, 2=half-open)"
      labels: ["handler"]

    - name: "transaction_rollbacks_total"
      type: "counter"
      description: "Total transaction rollbacks"
      labels: ["operation_type"]

  logging:
    level: "INFO"
    format: "structured_json"
    fields:
      - "timestamp"
      - "level"
      - "correlation_id"
      - "operation_id"
      - "operation_type"
      - "transaction_state"
      - "processing_time_ms"
      - "retry_count"

# Testing requirements
testing:
  unit_tests:
    coverage_minimum: 90
    test_files:
      - "test_node.py"
      - "test_config.py"
      - "test_handlers.py"
      - "test_models.py"

  integration_tests:
    required: true
    test_scenarios:
      - "http_request_success"
      - "http_request_retry"
      - "database_transaction_commit"
      - "database_transaction_rollback"
      - "circuit_breaker_activation"
      - "timeout_handling"
```

## Usage Instructions

### Template Customization

Replace the following placeholders throughout all files:

- `{REPOSITORY_NAME}`: Target repository name (e.g., "omniplan")
- `{DOMAIN}`: Business domain (e.g., "user_management", "orders", "payments")
- `{MICROSERVICE_NAME}`: Specific microservice name (e.g., "user_api", "order_processor")
- `{DomainCamelCase}`: Domain in CamelCase (e.g., "UserManagement", "Orders")
- `{MicroserviceCamelCase}`: Microservice in CamelCase (e.g., "UserApi", "OrderProcessor")

### Key Architectural Features

1. **Contract-Driven Execution**: All effect logic defined in YAML subcontracts
2. **Transaction Support**: Atomic operations with automatic rollback
3. **Retry with Backoff**: Exponential backoff for transient failures
4. **Circuit Breaker**: Fault tolerance for repeated failures
5. **Type Safety**: Full Pydantic validation on inputs and outputs
6. **Async-First**: All I/O operations are asynchronous
7. **Error Sanitization**: Security-focused error handling

### Common Patterns

#### HTTP API Call with Retry

```python
from omnibase_core.nodes import NodeEffect, ModelEffectInput
from omnibase_core.enums.enum_effect_types import EnumEffectType

# Create effect input for API call
input_data = ModelEffectInput(
    effect_type=EnumEffectType.API_CALL,
    operation_data={
        "url": "https://api.example.com/users",
        "method": "POST",
        "body": {"name": "John Doe"},
    },
    retry_enabled=True,
    max_retries=3,
    circuit_breaker_enabled=True,
    timeout_ms=30000,
)

# Execute effect
result = await node.process(input_data)
```

#### Database Operation with Transaction

```python
input_data = ModelEffectInput(
    effect_type=EnumEffectType.DATABASE_OPERATION,
    operation_data={
        "query": "INSERT INTO users (name, email) VALUES (:name, :email)",
        "params": {"name": "John", "email": "john@example.com"},
    },
    transaction_enabled=True,
    retry_enabled=True,
)

result = await node.process(input_data)

if result.transaction_state == EnumTransactionState.COMMITTED:
    print(f"User created: {result.result}")
else:
    print(f"Rollback performed: {result.rollback_operations}")
```

#### File Operation with Atomic Writes

```python
input_data = ModelEffectInput(
    effect_type=EnumEffectType.FILE_OPERATION,
    operation_data={
        "path": "/data/config.json",
        "action": "write",
        "content": '{"setting": "value"}',
        "atomic": True,
    },
    transaction_enabled=True,
)

result = await node.process(input_data)
```

### Implementation Checklist

- [ ] Replace all template placeholders
- [ ] Implement domain-specific handlers in `handlers/`
- [ ] Define effect subcontract with all operations
- [ ] Update enum values for domain-specific operations
- [ ] Customize configuration for domain needs
- [ ] Write comprehensive unit tests
- [ ] Test transaction rollback scenarios
- [ ] Test circuit breaker activation
- [ ] Test retry behavior with exponential backoff
- [ ] Update manifest with accurate specifications
- [ ] Validate contract compliance
- [ ] Set up monitoring and alerting

### Thread Safety Warning

**CRITICAL**: NodeEffect instances are NOT thread-safe. Do not share instances across threads.

```python
# WRONG - Do NOT do this
node = NodeEffect(container)
threading.Thread(target=lambda: asyncio.run(node.process(input_data))).start()  # UNSAFE

# CORRECT - Create separate instances per thread
def worker():
    node = NodeEffect(container)  # Each thread gets its own instance
    asyncio.run(node.process(input_data))
```

For debugging, set `ONEX_DEBUG_THREAD_SAFETY=1` to enable runtime thread affinity checks.

### See Also

- [EFFECT Node Tutorial](../../guides/node-building/04_EFFECT_NODE_TUTORIAL.md) - Step-by-step tutorial
- [Node Class Hierarchy](../../architecture/NODE_CLASS_HIERARCHY.md) - Choose the right base class
- [Threading Guide](../../guides/THREADING.md) - Thread safety guidelines
- [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error patterns

This template ensures all EFFECT nodes follow the unified ONEX architecture while providing production-ready external I/O capabilities with transaction support, retry logic, and circuit breaker patterns.
