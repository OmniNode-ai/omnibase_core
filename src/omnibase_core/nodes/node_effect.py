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
- ModelEffectTransaction management for rollback support
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
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import (
    EnumCircuitBreakerState,
    EnumEffectType,
    EnumTransactionState,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_effect_transaction import (
    ModelEffectTransaction,
)
from omnibase_core.models.model_effect_input import ModelEffectInput
from omnibase_core.models.model_effect_output import ModelEffectOutput


class NodeEffect(NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Side effect management node for external interactions.

    Implements managed side effects with transaction support, retry policies,
    and circuit breaker patterns. Handles I/O operations, file management,
    event emission, and external service interactions.

    Key Features:
    - ModelEffectTransaction management with rollback support
    - Retry policies with exponential backoff
    - Circuit breaker patterns for failure handling
    - Atomic file operations for data integrity
    - Event bus integration for state changes
    - Performance monitoring and logging

    Thread Safety:
        - Circuit breaker state NOT thread-safe (failure counts, timers)
        - Transactions NOT shareable across threads
        - Create separate instances per thread for concurrent effects
        - See docs/THREADING.md for production guidelines and mitigation strategies
    """

    # Type annotations for attributes set via object.__setattr__()
    default_timeout_ms: int
    default_retry_delay_ms: int
    max_concurrent_effects: int
    active_transactions: dict[UUID, ModelEffectTransaction]
    circuit_breakers: dict[str, ModelCircuitBreaker]
    effect_handlers: dict[
        EnumEffectType, Callable[[dict[str, Any], ModelEffectTransaction | None], Any]
    ]
    effect_semaphore: asyncio.Semaphore
    _active_effects_count: int
    effect_metrics: dict[str, dict[str, float]]
    on_rollback_failure: (
        Callable[[ModelEffectTransaction, list[ModelOnexError]], None] | None
    )

    def __init__(
        self,
        container: ModelONEXContainer,
        on_rollback_failure: (
            Callable[[ModelEffectTransaction, list[ModelOnexError]], None] | None
        ) = None,
    ) -> None:
        """
        Initialize NodeEffect with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection
            on_rollback_failure: Optional callback invoked on rollback failures.
                                 Useful for alerting, metrics, or custom recovery logic.
                                 Signature: (transaction, errors) -> None

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Use object.__setattr__() to bypass Pydantic validation for internal state
        # Effect-specific configuration (defaults, overridden in _initialize_node_resources)
        # These defaults are used if ProtocolNodeConfiguration is not available
        object.__setattr__(self, "default_timeout_ms", 30000)
        object.__setattr__(self, "default_retry_delay_ms", 1000)
        object.__setattr__(self, "max_concurrent_effects", 10)

        # ModelEffectTransaction management
        object.__setattr__(self, "active_transactions", {})

        # Circuit breakers for external services
        object.__setattr__(self, "circuit_breakers", {})

        # Effect handlers registry
        object.__setattr__(self, "effect_handlers", {})

        # Semaphore for limiting concurrent effects
        object.__setattr__(
            self, "effect_semaphore", asyncio.Semaphore(self.max_concurrent_effects)
        )

        # Track active effects count (don't access semaphore._value)
        object.__setattr__(self, "_active_effects_count", 0)

        # Effect-specific metrics
        object.__setattr__(self, "effect_metrics", {})

        # Rollback failure callback
        object.__setattr__(self, "on_rollback_failure", on_rollback_failure)

        # Register built-in effect handlers
        self._register_builtin_effect_handlers()

    async def execute_effect(
        self,
        contract: Any,  # ModelContractEffect - imported in method to avoid circular dependency
    ) -> ModelEffectOutput:
        """
        Execute effect based on contract specification.

        REQUIRED INTERFACE: This public method implements the ModelContractEffect interface
        per ONEX guidelines. Subclasses implementing custom effect nodes should override
        this method or use the default contract-to-input conversion.

        Args:
            contract: Effect contract specifying the operation configuration

        Returns:
            ModelEffectOutput: Operation results with transaction status and metadata

        Raises:
            ModelOnexError: If effect execution fails or contract is invalid
        """
        # Import here to avoid circular dependency
        from omnibase_core.models.contracts.model_contract_effect import (
            ModelContractEffect,
        )

        if not isinstance(contract, ModelContractEffect):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Invalid contract type - must be ModelContractEffect",
                context={
                    "node_id": str(self.node_id),
                    "provided_type": type(contract).__name__,
                },
            )

        # Convert contract to ModelEffectInput
        effect_input = self._contract_to_input(contract)

        # Execute via existing process() method
        return await self.process(effect_input)

    def _contract_to_input(
        self, contract: Any
    ) -> ModelEffectInput:  # ModelContractEffect
        """
        Convert ModelContractEffect to ModelEffectInput.

        Args:
            contract: Effect contract to convert

        Returns:
            ModelEffectInput: Input model for process() method

        Raises:
            ModelOnexError: If contract has no I/O operations or conversion fails
        """
        if not contract.io_operations:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Contract must have at least one I/O operation",
                context={"node_id": str(self.node_id)},
            )

        # Use the first I/O operation as the primary operation
        primary_operation = contract.io_operations[0]

        # Map operation type to EnumEffectType
        effect_type = self._map_operation_type_to_effect_type(
            primary_operation.operation_type
        )

        # Build operation data from contract
        operation_data: dict[str, Any] = {
            "operation_type": primary_operation.operation_type,
            "atomic": primary_operation.atomic,
            "backup_enabled": primary_operation.backup_enabled,
            "permissions": primary_operation.permissions,
            "recursive": primary_operation.recursive,
            "buffer_size": primary_operation.buffer_size,
            "timeout_seconds": primary_operation.timeout_seconds,
            "validation_enabled": primary_operation.validation_enabled,
        }

        # Merge input state data into operation_data (infrastructure patterns)
        # This allows file_path and other operation-specific data to be accessible
        if contract.input_state:
            operation_data.update(contract.input_state)

        # Add output state and actions if present
        if contract.output_state:
            operation_data["output_state"] = contract.output_state
        if contract.actions:
            operation_data["actions"] = contract.actions

        # Create ModelEffectInput from contract configuration
        return ModelEffectInput(
            effect_type=effect_type,
            operation_data=operation_data,
            operation_id=contract.execution_id,
            transaction_enabled=contract.transaction_management.enabled,
            retry_enabled=(contract.retry_policies.max_attempts > 1),
            max_retries=contract.retry_policies.max_attempts,
            retry_delay_ms=contract.retry_policies.base_delay_ms,
            circuit_breaker_enabled=contract.retry_policies.circuit_breaker_enabled,
            timeout_ms=primary_operation.timeout_seconds * 1000,
            metadata={
                "correlation_id": str(contract.correlation_id),
                "idempotent": contract.idempotent_operations,
                "audit_trail_enabled": contract.audit_trail_enabled,
                "contract_name": contract.name,
                "contract_version": str(contract.version),
            },
        )

    def _map_operation_type_to_effect_type(self, operation_type: str) -> EnumEffectType:
        """
        Map contract operation type to EnumEffectType.

        Args:
            operation_type: Operation type from contract (e.g., "file_write", "db_query")

        Returns:
            EnumEffectType: Mapped effect type enum value

        Raises:
            ModelOnexError: If operation type cannot be mapped
        """
        # Map common operation types to EnumEffectType values
        operation_type_lower = operation_type.lower()

        if any(
            op in operation_type_lower
            for op in ["file", "read", "write", "delete", "move"]
        ):
            return EnumEffectType.FILE_OPERATION

        if any(op in operation_type_lower for op in ["event", "emit", "publish"]):
            return EnumEffectType.EVENT_EMISSION

        # Default to FILE_OPERATION for unknown types
        # This allows custom operation types to be handled by registered handlers
        emit_log_event(
            LogLevel.WARNING,
            f"Unknown operation type '{operation_type}', defaulting to FILE_OPERATION",
            {"node_id": str(self.node_id), "operation_type": operation_type},
        )
        return EnumEffectType.FILE_OPERATION

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
        start_time = time.perf_counter()
        transaction: ModelEffectTransaction | None = None
        retry_count = 0

        try:
            self._validate_effect_input(input_data)

            # Check circuit breaker if enabled
            if input_data.circuit_breaker_enabled:
                circuit_breaker = self._get_circuit_breaker(
                    input_data.effect_type.value
                )
                if not circuit_breaker.should_allow_request():
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"Circuit breaker open for {input_data.effect_type.value}",
                        context={
                            "node_id": str(self.node_id),
                            "operation_id": str(input_data.operation_id),
                            "effect_type": input_data.effect_type.value,
                        },
                    )

            # Create transaction if enabled
            if input_data.transaction_enabled:
                transaction = ModelEffectTransaction(input_data.operation_id)
                transaction.state = EnumTransactionState.ACTIVE
                self.active_transactions[input_data.operation_id] = transaction

            # Execute with semaphore limit and retry logic
            async with self.effect_semaphore:
                self._active_effects_count += 1
                try:
                    result, retry_count = await self._execute_with_retry(
                        input_data, transaction
                    )
                finally:
                    self._active_effects_count -= 1

            # Commit transaction if successful
            if transaction:
                await transaction.commit()
                del self.active_transactions[input_data.operation_id]

            processing_time = (time.perf_counter() - start_time) * 1000

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
                    transaction.state if transaction else EnumTransactionState.COMMITTED
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
            processing_time = (time.perf_counter() - start_time) * 1000

            # Rollback transaction if active
            if transaction:
                success, rollback_errors = await transaction.rollback()

                if not success:
                    # Rollback failed - this is CRITICAL
                    emit_log_event(
                        LogLevel.ERROR,
                        f"Transaction rollback failed with {len(rollback_errors)} errors",
                        {
                            "node_id": str(self.node_id),
                            "operation_id": str(input_data.operation_id),
                            "transaction_id": str(transaction.transaction_id),
                            "rollback_errors": [str(err) for err in rollback_errors],
                            "original_error": str(e),
                        },
                    )

                    # Invoke callback for critical failures if configured
                    if self.on_rollback_failure:
                        try:
                            self.on_rollback_failure(transaction, rollback_errors)
                        except Exception as callback_error:
                            emit_log_event(
                                LogLevel.ERROR,
                                f"Rollback failure callback raised exception: {callback_error!s}",
                                {
                                    "node_id": str(self.node_id),
                                    "transaction_id": str(transaction.transaction_id),
                                    "callback_error": str(callback_error),
                                },
                            )

                    # Update rollback failure metrics
                    await self._update_rollback_failure_metrics(
                        transaction, rollback_errors
                    )

                    # Chain the rollback errors to the original exception
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        message="Effect failed AND rollback failed (data may be inconsistent)",
                        node_id=str(self.node_id),
                        operation_id=str(input_data.operation_id),
                        original_error=str(e),
                        rollback_errors=[str(err) for err in rollback_errors],
                        transaction_id=str(transaction.transaction_id),
                        effect_type=input_data.effect_type.value,
                    ) from e

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
                    "operation_id": str(input_data.operation_id),
                    "effect_type": input_data.effect_type.value,
                },
            ) from e

    @asynccontextmanager
    async def transaction_context(
        self, operation_id: UUID | None = None
    ) -> AsyncIterator[ModelEffectTransaction]:
        """
        Async context manager for transaction handling with rollback failure detection.

        Args:
            operation_id: Optional operation identifier (UUID)

        Yields:
            ModelEffectTransaction: Active transaction instance

        Raises:
            ModelOnexError: If rollback fails during exception handling
        """
        transaction_id = operation_id or uuid4()
        transaction = ModelEffectTransaction(transaction_id)
        transaction.state = EnumTransactionState.ACTIVE

        try:
            self.active_transactions[transaction_id] = transaction
            yield transaction
            await transaction.commit()
        except Exception as e:
            success, rollback_errors = await transaction.rollback()

            if not success:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Transaction context rollback failed with {len(rollback_errors)} errors",
                    {
                        "node_id": str(self.node_id),
                        "transaction_id": str(transaction_id),
                        "rollback_errors": [str(err) for err in rollback_errors],
                    },
                )

                # Update rollback failure metrics
                await self._update_rollback_failure_metrics(
                    transaction, rollback_errors
                )

                # Invoke callback if configured
                if self.on_rollback_failure:
                    try:
                        self.on_rollback_failure(transaction, rollback_errors)
                    except Exception as callback_error:
                        emit_log_event(
                            LogLevel.ERROR,
                            f"Rollback failure callback raised exception: {callback_error!s}",
                            {
                                "node_id": str(self.node_id),
                                "transaction_id": str(transaction_id),
                                "callback_error": str(callback_error),
                            },
                        )

                # Re-raise with context about rollback failure
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message="Transaction failed AND rollback failed (data may be inconsistent)",
                    node_id=str(self.node_id),
                    transaction_id=str(transaction_id),
                    original_error=str(e),
                    rollback_errors=[str(err) for err in rollback_errors],
                ) from e

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
            effect_type=EnumEffectType.FILE_OPERATION,
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
            effect_type=EnumEffectType.EVENT_EMISSION,
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
                "state": float(
                    1 if cb.state == EnumCircuitBreakerState.CLOSED.value else 0
                ),
                "failure_count": float(cb.failure_count),
                "is_open": float(
                    1 if cb.state == EnumCircuitBreakerState.OPEN.value else 0
                ),
            }

        # Merge stored transaction metrics with real-time transaction stats
        transaction_mgmt_metrics = self.effect_metrics.get(
            "transaction_management", {}
        ).copy()
        transaction_mgmt_metrics.update(
            {
                "active_transactions": float(len(self.active_transactions)),
                "max_concurrent_effects": float(self.max_concurrent_effects),
                "active_effects": float(self._active_effects_count),
                "semaphore_available": float(
                    self.max_concurrent_effects - self._active_effects_count
                ),
            }
        )

        return {
            **self.effect_metrics,
            **circuit_breaker_metrics,
            "transaction_management": transaction_mgmt_metrics,
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize effect-specific resources."""
        # Load configuration from NodeConfigProvider if available
        config = self.container.get_service_optional(NodeConfigProvider)
        if config:
            # Load timeout configurations
            default_timeout_value = await config.get_timeout_ms(
                "effect.default_timeout_ms", default_ms=self.default_timeout_ms
            )
            retry_delay_value = await config.get_timeout_ms(
                "effect.default_retry_delay_ms", default_ms=self.default_retry_delay_ms
            )

            # Load performance configurations
            max_concurrent_value = await config.get_performance_config(
                "effect.max_concurrent_effects", default=self.max_concurrent_effects
            )

            # Update configuration values with type checking
            if isinstance(default_timeout_value, int):
                self.default_timeout_ms = default_timeout_value
            if isinstance(retry_delay_value, int):
                self.default_retry_delay_ms = retry_delay_value
            if isinstance(max_concurrent_value, (int, float)):
                self.max_concurrent_effects = int(max_concurrent_value)
                # Update semaphore with new value
                self.effect_semaphore = asyncio.Semaphore(self.max_concurrent_effects)

            emit_log_event(
                LogLevel.INFO,
                "NodeEffect loaded configuration from NodeConfigProvider",
                {
                    "node_id": str(self.node_id),
                    "default_timeout_ms": self.default_timeout_ms,
                    "default_retry_delay_ms": self.default_retry_delay_ms,
                    "max_concurrent_effects": self.max_concurrent_effects,
                },
            )

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
        """Cleanup effect-specific resources with rollback failure handling."""
        for transaction_id, transaction in list(self.active_transactions.items()):
            success, rollback_errors = await transaction.rollback()

            if success:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Rolled back active transaction during cleanup: {transaction_id}",
                    {
                        "node_id": str(self.node_id),
                        "transaction_id": str(transaction_id),
                    },
                )
            else:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to rollback transaction during cleanup with {len(rollback_errors)} errors",
                    {
                        "node_id": str(self.node_id),
                        "transaction_id": str(transaction_id),
                        "rollback_errors": [str(e) for e in rollback_errors],
                    },
                )

                # Update metrics for cleanup rollback failures
                await self._update_rollback_failure_metrics(
                    transaction, rollback_errors
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

        if not isinstance(input_data.effect_type, EnumEffectType):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Effect type must be valid EnumEffectType enum",
                context={"node_id": str(self.node_id)},
            )

    def _get_circuit_breaker(self, service_name: str) -> ModelCircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = ModelCircuitBreaker()
        return self.circuit_breakers[service_name]

    async def _execute_with_retry(
        self, input_data: ModelEffectInput, transaction: ModelEffectTransaction | None
    ) -> tuple[Any, int]:
        """Execute effect with retry logic.

        Returns:
            Tuple of (result, retry_count) where retry_count is the actual number of retries performed
        """
        retry_count = 0
        last_exception: Exception = ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message="No retries executed",
        )

        while retry_count <= input_data.max_retries:
            try:
                result = await self._execute_effect(input_data, transaction)

                return (result, retry_count)

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
                        "operation_id": str(input_data.operation_id),
                    },
                )

        raise last_exception

    async def _execute_effect(
        self, input_data: ModelEffectInput, transaction: ModelEffectTransaction | None
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

    async def _update_rollback_failure_metrics(
        self, transaction: ModelEffectTransaction, rollback_errors: list[ModelOnexError]
    ) -> None:
        """
        Update metrics for rollback failures.

        Args:
            transaction: Transaction that experienced rollback failures
            rollback_errors: List of errors encountered during rollback

        Metrics Updated:
            - transaction.rollback_failures_total: Total count of rollback failures
            - transaction.failed_operation_count: Histogram of failed operation counts per transaction
        """
        # Initialize transaction metrics if not exists
        if "transaction_management" not in self.effect_metrics:
            self.effect_metrics["transaction_management"] = {
                "rollback_failures_total": 0.0,
                "failed_operation_count_min": float("inf"),
                "failed_operation_count_max": 0.0,
                "failed_operation_count_avg": 0.0,
                "failed_operation_count_samples": 0.0,
            }

        tx_metrics = self.effect_metrics["transaction_management"]

        # Increment total rollback failures
        tx_metrics["rollback_failures_total"] += 1

        # Update failed operation count histogram
        failed_count = len(rollback_errors)
        tx_metrics["failed_operation_count_min"] = min(
            tx_metrics["failed_operation_count_min"], float(failed_count)
        )
        tx_metrics["failed_operation_count_max"] = max(
            tx_metrics["failed_operation_count_max"], float(failed_count)
        )

        # Update average
        samples = tx_metrics["failed_operation_count_samples"]
        current_avg = tx_metrics["failed_operation_count_avg"]
        new_samples = samples + 1
        tx_metrics["failed_operation_count_avg"] = (
            current_avg * samples + failed_count
        ) / new_samples
        tx_metrics["failed_operation_count_samples"] = new_samples

        emit_log_event(
            LogLevel.INFO,
            "Rollback failure metrics updated",
            {
                "transaction_id": str(transaction.transaction_id),
                "failed_operations": failed_count,
                "total_rollback_failures": tx_metrics["rollback_failures_total"],
            },
        )

    def _register_builtin_effect_handlers(self) -> None:
        """Register built-in effect handlers."""

        async def file_operation_handler(
            operation_data: dict[str, Any], transaction: ModelEffectTransaction | None
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
                    # Capture state before write to enable proper rollback
                    pre_existed = file_path.exists()
                    prev_content: str | None = None
                    if pre_existed:
                        with open(file_path, encoding="utf-8") as f:
                            prev_content = f.read()

                    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(str(data))
                        temp_path.replace(file_path)

                        if transaction:

                            def rollback_write() -> None:
                                # Restore previous content if file existed, delete if it didn't
                                if pre_existed and prev_content is not None:
                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write(prev_content)
                                elif file_path.exists():
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

                    if transaction and backup_content is not None:

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
            operation_data: dict[str, Any], transaction: ModelEffectTransaction | None
        ) -> bool:
            """Handle event emission to event bus."""
            event_type = operation_data["event_type"]
            payload = operation_data["payload"]
            correlation_id = operation_data.get("correlation_id")

            try:
                event_bus: Any = self.container.get_service("event_bus")  # type: ignore[arg-type]
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

            except (
                Exception
            ) as e:  # fallback-ok: event emission is non-critical, graceful failure
                emit_log_event(
                    LogLevel.ERROR,
                    f"Event emission failed: {e!s}",
                    {"event_type": event_type, "error": str(e)},
                )
                return False

        self.effect_handlers[EnumEffectType.FILE_OPERATION] = file_operation_handler
        self.effect_handlers[EnumEffectType.EVENT_EMISSION] = event_emission_handler
