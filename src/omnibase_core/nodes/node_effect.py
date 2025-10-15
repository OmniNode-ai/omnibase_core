"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

NodeEffect - Side Effect Management Node for 4-Node Architecture.

Specialized node type for managing side effects and external interactions with
transaction support, retry policies, and circuit breaker patterns.

Key Capabilities:
- Side-effect management with external interaction focus
- I/O operation abstraction (file, database, API calls)
- Transaction management for rollback support
- Retry policies and circuit breaker patterns
- Event bus publishing for state changes
- Atomic file operations for data integrity

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class EffectType(Enum):
    """Types of side effects that can be managed."""

    FILE_OPERATION = "file_operation"
    DATABASE_OPERATION = "database_operation"
    API_CALL = "api_call"
    EVENT_EMISSION = "event_emission"
    DIRECTORY_OPERATION = "directory_operation"
    TICKET_STORAGE = "ticket_storage"
    METRICS_COLLECTION = "metrics_collection"


class TransactionState(Enum):
    """Transaction state tracking."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class CircuitBreakerState(Enum):
    """Circuit breaker states for failure handling."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ModelEffectInput(BaseModel):
    """
    Input model for NodeEffect operations.

    Strongly typed input wrapper for side effect operations
    with transaction and retry configuration.
    """

    effect_type: EffectType
    operation_data: dict[str, Any]
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    transaction_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    circuit_breaker_enabled: bool = False
    timeout_ms: int = 30000
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelEffectOutput(BaseModel):
    """
    Output model for NodeEffect operations.

    Strongly typed output wrapper with transaction status
    and side effect execution metadata.
    """

    result: str | int | float | bool | dict | list
    operation_id: str
    effect_type: EffectType
    transaction_state: TransactionState
    processing_time_ms: float
    retry_count: int = 0
    side_effects_applied: list[str] = Field(default_factory=list)
    rollback_operations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Transaction:
    """
    Transaction management for side effect operations.

    Provides rollback capabilities and operation tracking
    for complex side effect sequences.
    """

    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        self.state = TransactionState.PENDING
        self.operations: list[dict[str, Any]] = []
        self.rollback_operations: list[Callable[..., Any]] = []
        self.started_at = datetime.now()
        self.committed_at: datetime | None = None

    def add_operation(
        self,
        operation_name: str,
        operation_data: dict[str, Any],
        rollback_func: Callable[..., Any] | None = None,
    ) -> None:
        """Add operation to transaction with optional rollback function."""
        self.operations.append(
            {
                "name": operation_name,
                "data": operation_data,
                "timestamp": datetime.now(),
            },
        )

        if rollback_func:
            self.rollback_operations.append(rollback_func)

    async def commit(self) -> None:
        """Commit transaction - marks as successful."""
        self.state = TransactionState.COMMITTED
        self.committed_at = datetime.now()

    async def rollback(self) -> None:
        """Rollback transaction - execute all rollback operations."""
        self.state = TransactionState.ROLLED_BACK

        for rollback_func in reversed(self.rollback_operations):
            try:
                if asyncio.iscoroutinefunction(rollback_func):
                    await rollback_func()
                else:
                    rollback_func()
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Rollback operation failed: {e!s}",
                    {"transaction_id": self.transaction_id, "error": str(e)},
                )


class CircuitBreaker:
    """
    Circuit breaker pattern for handling external service failures.

    Prevents cascading failures by temporarily disabling calls to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_attempts: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_attempts = half_open_max_attempts

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.half_open_attempts = 0

    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit breaker state."""
        now = datetime.now()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and now - self.last_failure_time > timedelta(
                seconds=self.recovery_timeout_seconds,
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_attempts = 0
                return True
            return False
        # HALF_OPEN
        return self.half_open_attempts < self.half_open_max_attempts

    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.half_open_attempts = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.half_open_attempts = 0
        elif (
            self.state == CircuitBreakerState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitBreakerState.OPEN


class NodeEffect(NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Side effect management node for external interactions.

    Implements managed side effects with transaction support, retry policies,
    and circuit breaker patterns. Handles I/O operations, file management,
    event emission, and external service interactions.

    Key Features:
    - Transaction management with rollback support
    - Retry policies with exponential backoff
    - Circuit breaker patterns for failure handling
    - Atomic file operations for data integrity
    - Event bus integration for state changes
    - Performance monitoring and logging
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeEffect with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Effect-specific configuration
        self.default_timeout_ms = 30000
        self.default_retry_delay_ms = 1000
        self.max_concurrent_effects = 10

        # Transaction management
        self.active_transactions: dict[str, Transaction] = {}

        # Circuit breakers for external services
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

        # Effect handlers registry
        self.effect_handlers: dict[EffectType, Callable[..., Any]] = {}

        # Semaphore for limiting concurrent effects
        self.effect_semaphore = asyncio.Semaphore(self.max_concurrent_effects)

        # Effect-specific metrics
        self.effect_metrics: dict[str, dict[str, float]] = {}

        # Register built-in effect handlers
        self._register_builtin_effect_handlers()

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        REQUIRED: Execute side effect operation.

        STABLE INTERFACE: This method signature is frozen for code generation.

        Args:
            input_data: Strongly typed effect input with configuration

        Returns:
            Strongly typed effect output with transaction status

        Raises:
            ModelOnexError: If side effect execution fails
        """
        start_time = time.time()
        transaction: Transaction | None = None
        retry_count = 0

        try:
            self._validate_effect_input(input_data)

            # Check circuit breaker if enabled
            if input_data.circuit_breaker_enabled:
                circuit_breaker = self._get_circuit_breaker(
                    input_data.effect_type.value
                )
                if not circuit_breaker.can_execute():
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"Circuit breaker open for {input_data.effect_type.value}",
                        context={
                            "node_id": str(self.node_id),
                            "operation_id": input_data.operation_id,
                            "effect_type": input_data.effect_type.value,
                        },
                    )

            # Create transaction if enabled
            if input_data.transaction_enabled:
                transaction = Transaction(input_data.operation_id)
                transaction.state = TransactionState.ACTIVE
                self.active_transactions[input_data.operation_id] = transaction

            # Execute with semaphore limit and retry logic
            async with self.effect_semaphore:
                result = await self._execute_with_retry(input_data, transaction)

            # Commit transaction if successful
            if transaction:
                await transaction.commit()
                del self.active_transactions[input_data.operation_id]

            processing_time = (time.time() - start_time) * 1000

            # Record success in circuit breaker
            if input_data.circuit_breaker_enabled:
                self._get_circuit_breaker(input_data.effect_type.value).record_success()

            # Update metrics
            await self._update_effect_metrics(
                input_data.effect_type.value, processing_time, True
            )
            await self._update_processing_metrics(processing_time, True)

            return ModelEffectOutput(
                result=result,
                operation_id=input_data.operation_id,
                effect_type=input_data.effect_type,
                transaction_state=(
                    transaction.state if transaction else TransactionState.COMMITTED
                ),
                processing_time_ms=processing_time,
                retry_count=retry_count,
                side_effects_applied=(
                    [str(op) for op in transaction.operations] if transaction else []
                ),
                metadata={
                    "timeout_ms": input_data.timeout_ms,
                    "transaction_enabled": input_data.transaction_enabled,
                    "circuit_breaker_enabled": input_data.circuit_breaker_enabled,
                },
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # Rollback transaction if active
            if transaction:
                try:
                    await transaction.rollback()
                except Exception as rollback_error:
                    emit_log_event(
                        LogLevel.ERROR,
                        f"Transaction rollback failed: {rollback_error!s}",
                        {
                            "node_id": str(self.node_id),
                            "operation_id": input_data.operation_id,
                        },
                    )

                if input_data.operation_id in self.active_transactions:
                    del self.active_transactions[input_data.operation_id]

            # Record failure in circuit breaker
            if input_data.circuit_breaker_enabled:
                self._get_circuit_breaker(input_data.effect_type.value).record_failure()

            # Update error metrics
            await self._update_effect_metrics(
                input_data.effect_type.value, processing_time, False
            )
            await self._update_processing_metrics(processing_time, False)

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Effect execution failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": input_data.operation_id,
                    "effect_type": input_data.effect_type.value,
                },
            ) from e

    @asynccontextmanager
    async def transaction_context(
        self, operation_id: str | None = None
    ) -> AsyncIterator[Transaction]:
        """
        Async context manager for transaction handling.

        Args:
            operation_id: Optional operation identifier

        Yields:
            Transaction: Active transaction instance
        """
        transaction_id = operation_id or str(uuid4())
        transaction = Transaction(transaction_id)
        transaction.state = TransactionState.ACTIVE

        try:
            self.active_transactions[transaction_id] = transaction
            yield transaction
            await transaction.commit()
        except Exception:
            await transaction.rollback()
            raise
        finally:
            if transaction_id in self.active_transactions:
                del self.active_transactions[transaction_id]

    async def execute_file_operation(
        self,
        operation_type: str,
        file_path: str | Path,
        data: Any | None = None,
        atomic: bool = True,
    ) -> dict[str, Any]:
        """
        Execute atomic file operation for work ticket management.

        Args:
            operation_type: Type of file operation (read, write, move, delete)
            file_path: Path to target file
            data: Data for write operations
            atomic: Whether to use atomic operations

        Returns:
            Operation result with file metadata

        Raises:
            ModelOnexError: If file operation fails
        """
        effect_input = ModelEffectInput(
            effect_type=EffectType.FILE_OPERATION,
            operation_data={
                "operation_type": operation_type,
                "file_path": str(file_path),
                "data": data,
                "atomic": atomic,
            },
            transaction_enabled=atomic,
            retry_enabled=True,
            max_retries=3,
        )

        result = await self.process(effect_input)
        return dict(result.result) if isinstance(result.result, dict) else {}

    async def emit_state_change_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
    ) -> bool:
        """
        Emit state change event to event bus.

        Args:
            event_type: Type of event to emit
            payload: Event payload data
            correlation_id: Optional correlation ID

        Returns:
            True if event was emitted successfully

        Raises:
            ModelOnexError: If event emission fails
        """
        effect_input = ModelEffectInput(
            effect_type=EffectType.EVENT_EMISSION,
            operation_data={
                "event_type": event_type,
                "payload": payload,
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
            transaction_enabled=False,
            retry_enabled=True,
            max_retries=2,
        )

        result = await self.process(effect_input)
        return bool(result.result)

    async def get_effect_metrics(self) -> dict[str, dict[str, float]]:
        """Get detailed effect performance metrics."""
        circuit_breaker_metrics = {}
        for service_name, cb in self.circuit_breakers.items():
            circuit_breaker_metrics[f"circuit_breaker_{service_name}"] = {
                "state": float(1 if cb.state == CircuitBreakerState.CLOSED else 0),
                "failure_count": float(cb.failure_count),
                "is_open": float(1 if cb.state == CircuitBreakerState.OPEN else 0),
            }

        return {
            **self.effect_metrics,
            **circuit_breaker_metrics,
            "transaction_management": {
                "active_transactions": float(len(self.active_transactions)),
                "max_concurrent_effects": float(self.max_concurrent_effects),
                "semaphore_available": float(self.effect_semaphore._value),
            },
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize effect-specific resources."""
        emit_log_event(
            LogLevel.INFO,
            "NodeEffect resources initialized",
            {
                "node_id": str(self.node_id),
                "max_concurrent_effects": self.max_concurrent_effects,
                "default_timeout_ms": self.default_timeout_ms,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup effect-specific resources."""
        for transaction_id, transaction in list(self.active_transactions.items()):
            try:
                await transaction.rollback()
                emit_log_event(
                    LogLevel.WARNING,
                    f"Rolled back active transaction during cleanup: {transaction_id}",
                    {"node_id": str(self.node_id), "transaction_id": transaction_id},
                )
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to rollback transaction during cleanup: {e!s}",
                    {"node_id": str(self.node_id), "transaction_id": transaction_id},
                )

        self.active_transactions.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeEffect resources cleaned up",
            {"node_id": str(self.node_id)},
        )

    def _validate_effect_input(self, input_data: ModelEffectInput) -> None:
        """Validate effect input data."""
        super()._validate_input_data(input_data)

        if not isinstance(input_data.effect_type, EffectType):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Effect type must be valid EffectType enum",
                context={"node_id": str(self.node_id)},
            )

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]

    async def _execute_with_retry(
        self, input_data: ModelEffectInput, transaction: Transaction | None
    ) -> Any:
        """Execute effect with retry logic."""
        retry_count = 0
        last_exception: Exception = ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message="No retries executed",
        )

        while retry_count <= input_data.max_retries:
            try:
                return await self._execute_effect(input_data, transaction)

            except Exception as e:
                last_exception = e
                retry_count += 1

                if not input_data.retry_enabled or retry_count > input_data.max_retries:
                    raise

                # Exponential backoff
                delay_ms = input_data.retry_delay_ms * (2 ** (retry_count - 1))
                await asyncio.sleep(delay_ms / 1000.0)

                emit_log_event(
                    LogLevel.WARNING,
                    f"Effect retry {retry_count}/{input_data.max_retries}: {e!s}",
                    {
                        "node_id": str(self.node_id),
                        "operation_id": input_data.operation_id,
                    },
                )

        raise last_exception

    async def _execute_effect(
        self, input_data: ModelEffectInput, transaction: Transaction | None
    ) -> Any:
        """Execute the actual effect operation."""
        effect_type = input_data.effect_type

        if effect_type in self.effect_handlers:
            handler = self.effect_handlers[effect_type]
            return await handler(input_data.operation_data, transaction)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"No handler registered for effect type: {effect_type.value}",
            context={"node_id": str(self.node_id), "effect_type": effect_type.value},
        )

    async def _update_effect_metrics(
        self, effect_type: str, processing_time_ms: float, success: bool
    ) -> None:
        """Update effect-specific metrics."""
        if effect_type not in self.effect_metrics:
            self.effect_metrics[effect_type] = {
                "total_operations": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "avg_processing_time_ms": 0.0,
                "min_processing_time_ms": float("inf"),
                "max_processing_time_ms": 0.0,
            }

        metrics = self.effect_metrics[effect_type]
        metrics["total_operations"] += 1

        if success:
            metrics["success_count"] += 1
        else:
            metrics["error_count"] += 1

        metrics["min_processing_time_ms"] = min(
            metrics["min_processing_time_ms"], processing_time_ms
        )
        metrics["max_processing_time_ms"] = max(
            metrics["max_processing_time_ms"], processing_time_ms
        )

        total_ops = metrics["total_operations"]
        current_avg = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg * (total_ops - 1) + processing_time_ms
        ) / total_ops

    def _register_builtin_effect_handlers(self) -> None:
        """Register built-in effect handlers."""

        async def file_operation_handler(
            operation_data: dict[str, Any], transaction: Transaction | None
        ) -> dict[str, Any]:
            """Handle file operations with atomic guarantees."""
            operation_type = operation_data["operation_type"]
            file_path = Path(operation_data["file_path"])
            data = operation_data.get("data")
            atomic = operation_data.get("atomic", True)

            result = {"operation_type": operation_type, "file_path": str(file_path)}

            if operation_type == "read":
                if not file_path.exists():
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                        message=f"File not found: {file_path}",
                        context={"file_path": str(file_path)},
                    )

                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                result["content"] = content
                result["size_bytes"] = len(content.encode("utf-8"))

            elif operation_type == "write":
                if atomic:
                    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(str(data))
                        temp_path.replace(file_path)

                        if transaction:

                            def rollback_write() -> None:
                                if file_path.exists():
                                    file_path.unlink()

                            transaction.add_operation(
                                "write",
                                {"file_path": str(file_path)},
                                rollback_write,
                            )

                    except Exception:
                        if temp_path.exists():
                            temp_path.unlink()
                        raise
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(str(data))

                result["bytes_written"] = len(str(data).encode("utf-8"))

            elif operation_type == "delete":
                if file_path.exists():
                    backup_content = None
                    if transaction:
                        with open(file_path, encoding="utf-8") as f:
                            backup_content = f.read()

                    file_path.unlink()
                    result["deleted"] = True

                    if transaction and backup_content:

                        def rollback_delete() -> None:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(backup_content)

                        transaction.add_operation(
                            "delete",
                            {"file_path": str(file_path)},
                            rollback_delete,
                        )
                else:
                    result["deleted"] = False

            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown file operation: {operation_type}",
                    context={"operation_type": operation_type},
                )

            return result

        async def event_emission_handler(
            operation_data: dict[str, Any], transaction: Transaction | None
        ) -> bool:
            """Handle event emission to event bus."""
            event_type = operation_data["event_type"]
            payload = operation_data["payload"]
            correlation_id = operation_data.get("correlation_id")

            try:
                event_bus = self.container.get_service("event_bus")
                if not event_bus:
                    emit_log_event(
                        LogLevel.WARNING,
                        "Event bus not available, skipping event emission",
                        {"event_type": event_type},
                    )
                    return False

                if hasattr(event_bus, "emit_event"):
                    await event_bus.emit_event(
                        event_type=event_type,
                        payload=payload,
                        correlation_id=UUID(correlation_id) if correlation_id else None,
                    )
                    return True

                return False

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Event emission failed: {e!s}",
                    {"event_type": event_type, "error": str(e)},
                )
                return False

        self.effect_handlers[EffectType.FILE_OPERATION] = file_operation_handler
        self.effect_handlers[EffectType.EVENT_EMISSION] = event_emission_handler
