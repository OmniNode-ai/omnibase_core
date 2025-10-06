import uuid
from typing import Callable, Dict, List, Optional, TypeVar

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
NodeEffect - Side Effect Management Node for 4-Node ModelArchitecture.

Specialized node type for managing side effects and external interactions with
transaction support, retry policies, and circuit breaker patterns.

Key Capabilities:
- Side-effect management with external interaction focus
- I/O operation abstraction (file, database, API calls)
- Transaction management for rollback support
- Retry policies and circuit breaker patterns
- RSD Storage Integration (work ticket file operations)
- Directory orchestration and file movement
- Event bus publishing for state changes
- Metrics collection and performance logging

Author: ONEX Framework Team
"""

import asyncio
import time
from collections.abc import AsyncIterator
from collections.abc import Callable as CallableABC
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar
from uuid import UUID, uuid4

from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.enums.enum_effect_type import EnumEffectType
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_transaction_state import EnumTransactionState
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Import contract model for effect nodes
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

# Import extracted models
from omnibase_core.models.infrastructure.model_circuit_breaker import (
    ModelCircuitBreaker,
)
from omnibase_core.models.infrastructure.model_transaction import ModelTransaction
from omnibase_core.models.operations.model_effect_input import ModelEffectInput
from omnibase_core.models.operations.model_effect_output import ModelEffectOutput
from omnibase_core.models.operations.model_effect_result import (
    ModelEffectResult,
    ModelEffectResultBool,
    ModelEffectResultDict,
    ModelEffectResultList,
    ModelEffectResultStr,
)
from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

T = TypeVar("T")


def _convert_to_scalar_dict(data: dict[str, Any]) -> dict[str, ModelSchemaValue]:
    """
    Convert a dict[str, Any]ionary of primitive values to ModelScalarValue objects.

    This utility function ensures type safety by converting primitive Python values
    to strongly-typed ModelScalarValue objects as required by the ONEX architecture.

    Args:
        data: Dictionary containing primitive values (str, int, float, bool)

    Returns:
        Dict[str, ModelScalarValue]: Dictionary with ModelScalarValue objects

    Raises:
        ValueError: If a value cannot be converted to ModelScalarValue
    """
    converted = {}
    for key, value in data.items():
        if isinstance(value, str):
            converted[key] = ModelSchemaValue.from_value(value)
        elif isinstance(value, int):
            converted[key] = ModelSchemaValue.from_value(value)
        elif isinstance(value, float):
            converted[key] = ModelSchemaValue.from_value(value)
        elif isinstance(value, bool):
            converted[key] = ModelSchemaValue.from_value(value)
        elif value is None:
            # Handle None by creating a string representation
            converted[key] = ModelSchemaValue.from_value("null")
        else:
            # For complex types, convert to string representation
            converted[key] = ModelSchemaValue.from_value(str(value))
    return converted


# Note: Enums and models have been extracted to separate modules
# - EnumEffectType → omnibase_core.enums.enum_effect_type
# - EnumTransactionState → omnibase_core.enums.enum_transaction_state
# - EnumCircuitBreakerState → omnibase_core.enums.enum_circuit_breaker_state
# - ModelEffectInput → omnibase_core.models.operations.model_effect_input
# - ModelEffectOutput → omnibase_core.models.operations.model_effect_output
# - ModelEffectResult* → omnibase_core.models.operations.model_effect_result
# - Transaction → omnibase_core.models.infrastructure.model_transaction
# - CircuitBreaker → omnibase_core.models.infrastructure.model_circuit_breaker


class NodeEffect(NodeCoreBase):
    """
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

    RSD Storage Integration:
    - Work ticket file operations with atomic updates
    - Directory orchestration and file movement
    - Event bus publishing for state changes
    - Metrics collection and performance logging
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

        # CANONICAL PATTERN: Load contract model for Effect node type
        self.contract_model: ModelContractEffect = self._load_contract_model()

        # Effect-specific configuration
        self.default_timeout_ms = 30000
        self.default_retry_delay_ms = 1000
        self.max_concurrent_effects = 10

        # Transaction management
        self.active_transactions: dict[str, ModelTransaction] = {}

        # Circuit breakers for external services
        self.circuit_breakers: dict[str, ModelCircuitBreaker] = {}

        # Effect handlers registry
        self.effect_handlers: dict[EnumEffectType, Callable[..., Any]] = {}

        # Semaphore for limiting concurrent effects
        self.effect_semaphore = asyncio.Semaphore(self.max_concurrent_effects)

        # Performance tracking
        self.effect_metrics: dict[str, dict[str, float]] = {}

        # Register built-in effect handlers
        self._register_builtin_effect_handlers()

    def _load_contract_model(self) -> ModelContractEffect:
        """
        Load and validate contract model for Effect node type.

        CANONICAL PATTERN: Centralized contract loading for all Effect nodes.
        Provides type-safe contract configuration with I/O operation validation.

        Returns:
            ModelContractEffect: Validated contract model for this node type

        Raises:
            ModelOnexError: If contract loading or validation fails
        """
        try:
            # Load actual contract from file with subcontract resolution

            from omnibase_core.utils.generation.utility_reference_resolver import (
                UtilityReferenceResolver,
            )
            from omnibase_core.utils.io.utility_filesystem_reader import (
                UtilityFileSystemReader,
            )

            # Get contract path - find the node.py file and look for contract.yaml
            contract_path = self._find_contract_path()

            # Load and resolve contract with subcontract support
            file_reader = UtilityFileSystemReader()
            reference_resolver = UtilityReferenceResolver()

            # Load and validate contract using utility function
            validated_contract = load_and_validate_yaml_model(
                contract_path,
                ModelContractEffect,
            )
            contract_data = validated_contract.model_dump()

            # Resolve any $ref references in the contract
            resolved_contract = self._resolve_contract_references(
                contract_data,
                contract_path.parent,
                reference_resolver,
            )

            # Create ModelContractEffect from resolved contract data
            contract_model = ModelContractEffect(**resolved_contract)

            # CANONICAL PATTERN: Validate contract model consistency
            contract_model.validate_node_specific_config()

            emit_log_event(
                LogLevel.INFO,
                "Contract model loaded successfully for NodeEffect",
                {
                    "contract_type": "ModelContractEffect",
                    "node_type": contract_model.node_type,
                    "version": contract_model.version,
                    "contract_path": str(contract_path),
                },
            )

            return contract_model

        except Exception as e:
            # CANONICAL PATTERN: Wrap contract loading errors
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Contract model loading failed for NodeEffect: {e!s}",
                details={
                    "contract_model_type": "ModelContractEffect",
                    "error_type": type(e).__name__,
                },
                cause=e,
            )

    def _find_contract_path(self) -> Path:
        """
        Find the contract.yaml file for this effect node.

        Uses inspection to find the module file and look for contract.yaml in the same directory.

        Returns:
            Path: Path to the contract.yaml file

        Raises:
            ModelOnexError: If contract file cannot be found
        """
        import inspect

        from omnibase_core.constants.contract_constants import CONTRACT_FILENAME

        try:
            # Get the module file for the calling class
            frame = inspect.currentframe()
            while frame:
                frame = frame.f_back
                if frame and "self" in frame.f_locals:
                    caller_self = frame.f_locals["self"]
                    if hasattr(caller_self, "__module__"):
                        module = inspect.getmodule(caller_self)
                        if module and hasattr(module, "__file__"):
                            module_path = Path(module.__file__)
                            contract_path = module_path.parent / CONTRACT_FILENAME
                            if contract_path.exists():
                                return contract_path

            # Fallback: this shouldn't happen but provide error
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Could not find contract.yaml file for effect node",
                details={"contract_filename": CONTRACT_FILENAME},
            )

        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Error finding contract path: {e!s}",
                cause=e,
            )

    def _resolve_contract_references(
        self,
        data: Any,
        base_path: Path,
        reference_resolver: Any,
    ) -> Any:
        """
        Recursively resolve all $ref references in contract data.

        Enhanced to properly handle FSM subcontracts with Pydantic model validation.

        Args:
            data: Contract data structure (dict[str, Any], list[Any], or primitive)
            base_path: Base directory path for resolving relative references
            reference_resolver: Reference resolver utility

        Returns:
            Any: Resolved contract data with all references loaded

        Raises:
            ModelOnexError: If reference resolution fails
        """
        try:
            if isinstance(data, dict):
                if "$ref" in data:
                    # Resolve reference to another file
                    ref_file = data["$ref"]
                    if ref_file.startswith(("./", "../")):
                        # Relative path reference
                        ref_path = (base_path / ref_file).resolve()
                    else:
                        # Absolute or root-relative reference
                        ref_path = Path(ref_file)

                    return reference_resolver.resolve_reference(
                        str(ref_path),
                        base_path,
                    )
                # Recursively resolve nested dict[str, Any]ionaries
                return {
                    key: self._resolve_contract_references(
                        value,
                        base_path,
                        reference_resolver,
                    )
                    for key, value in data.items()
                }
            if isinstance(data, list):
                # Recursively resolve list[Any]s
                return [
                    self._resolve_contract_references(
                        item,
                        base_path,
                        reference_resolver,
                    )
                    for item in data
                ]
            # Return primitives as-is
            return data

        except Exception as e:
            # Log error but don't stop processing
            emit_log_event(
                LogLevel.WARNING,
                "Failed to resolve contract reference, using original data",
                {"error": str(e), "error_type": type(e).__name__},
            )

        return None

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Managed side effects with transaction support.

        Args:
            input_data: Strongly typed effect input with configuration

        Returns:
            Strongly typed effect output with transaction status

        Raises:
            ModelOnexError: If side effect execution fails
        """
        start_time = time.time()
        transaction: ModelTransaction | None = None
        retry_count = 0

        try:
            # Validate input
            self._validate_effect_input(input_data)

            # Check circuit breaker if enabled
            if input_data.circuit_breaker_enabled:
                circuit_breaker = self._get_circuit_breaker(
                    input_data.effect_type.value,
                )
                if not circuit_breaker.can_execute():
                    raise ModelOnexError(
                        code=EnumCoreErrorCode.OPERATION_FAILED,
                        message=f"Circuit breaker open for {input_data.effect_type.value}",
                        context={
                            "node_id": str(self.node_id),
                            "operation_id": str(input_data.operation_id),
                            "effect_type": input_data.effect_type.value,
                            "circuit_breaker_state": circuit_breaker.state.value,
                        },
                    )

            # Create transaction if enabled
            if input_data.transaction_enabled:
                transaction = ModelTransaction(input_data.operation_id)
                transaction.state = EnumTransactionState.ACTIVE
                self.active_transactions[str(input_data.operation_id)] = transaction

            # Execute with semaphore limit
            async with self.effect_semaphore:
                # Execute effect with retry logic
                result = await self._execute_with_retry(input_data, transaction)

            # Commit transaction if successful
            if transaction:
                await transaction.commit()
                del self.active_transactions[str(input_data.operation_id)]

            processing_time = (time.time() - start_time) * 1000

            # Record success in circuit breaker
            if input_data.circuit_breaker_enabled:
                circuit_breaker = self._get_circuit_breaker(
                    input_data.effect_type.value,
                )
                circuit_breaker.record_success()

            # Update metrics
            await self._update_effect_metrics(
                input_data.effect_type.value,
                processing_time,
                True,
            )
            await self._update_processing_metrics(processing_time, True)

            # Wrap result in discriminated union based on type
            if isinstance(result, dict):
                wrapped_result = ModelEffectResultDict(value=result)
            elif isinstance(result, bool):
                wrapped_result = ModelEffectResultBool(value=result)
            elif isinstance(result, str):
                wrapped_result = ModelEffectResultStr(value=result)
            elif isinstance(result, list):
                wrapped_result = ModelEffectResultList(value=result)
            else:
                # Fallback: convert to string
                wrapped_result = ModelEffectResultStr(value=str(result))

            # Create output
            output = ModelEffectOutput(
                result=wrapped_result,
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

            emit_log_event(
                LogLevel.INFO,
                f"Effect completed: {input_data.effect_type.value}",
                {
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "processing_time_ms": processing_time,
                    "retry_count": retry_count,
                    "transaction_id": (
                        str(transaction.transaction_id) if transaction else None
                    ),
                },
            )

            return output

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
                            "operation_id": str(input_data.operation_id),
                            "original_error": str(e),
                            "rollback_error": str(rollback_error),
                        },
                    )

                if str(input_data.operation_id) in self.active_transactions:
                    del self.active_transactions[str(input_data.operation_id)]

            # Record failure in circuit breaker
            if input_data.circuit_breaker_enabled:
                circuit_breaker = self._get_circuit_breaker(
                    input_data.effect_type.value,
                )
                circuit_breaker.record_failure()

            # Update error metrics
            await self._update_effect_metrics(
                input_data.effect_type.value,
                processing_time,
                False,
            )
            await self._update_processing_metrics(processing_time, False)

            raise ModelOnexError(
                code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Effect execution failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "effect_type": input_data.effect_type.value,
                    "processing_time_ms": processing_time,
                    "transaction_state": (
                        transaction.state.value if transaction else "none"
                    ),
                    "error": str(e),
                },
            ) from e

    @asynccontextmanager
    async def transaction_context(
        self,
        operation_id: UUID | None = None,
    ) -> AsyncIterator[ModelTransaction]:
        """
        Async context manager for transaction handling.

        Args:
            operation_id: Optional operation identifier

        Yields:
            Transaction: Active transaction instance
        """
        transaction_id = operation_id or uuid4()
        transaction = ModelTransaction(transaction_id)
        transaction.state = EnumTransactionState.ACTIVE

        try:
            self.active_transactions[str(transaction_id)] = transaction
            yield transaction
            await transaction.commit()
        except Exception:
            await transaction.rollback()
            raise
        finally:
            if str(transaction_id) in self.active_transactions:
                del self.active_transactions[str(transaction_id)]

    async def execute_file_operation(
        self,
        operation_type: str,
        file_path: str | Path,
        data: Any | None = None,
        atomic: bool = True,
    ) -> dict[str, Any]:
        """
        Execute atomic file operation for RSD work ticket management.

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
            operation_data=_convert_to_scalar_dict(
                {
                    "operation_type": operation_type,
                    "file_path": str(file_path),
                    "data": data,
                    "atomic": atomic,
                },
            ),
            transaction_enabled=atomic,
            retry_enabled=True,
            max_retries=3,
        )

        result = await self.process(effect_input)
        # Extract value from discriminated union (file operations return dict[str, Any])
        if isinstance(result.result, ModelEffectResultDict):
            return result.result.value
        raise ModelOnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="File operation did not return expected dict[str, Any]result",
            context={"result_type": result.result.result_type},
        )

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
            operation_data=_convert_to_scalar_dict(
                {
                    "event_type": event_type,
                    "payload": payload,
                    "correlation_id": str(correlation_id) if correlation_id else None,
                },
            ),
            transaction_enabled=False,  # Events don't need transactions
            retry_enabled=True,
            max_retries=2,
        )

        result = await self.process(effect_input)
        # Extract value from discriminated union (event emissions return bool)
        if isinstance(result.result, ModelEffectResultBool):
            return result.result.value
        raise ModelOnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="Event emission did not return expected bool result",
            context={"result_type": result.result.result_type},
        )

    async def get_effect_metrics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed effect performance metrics.

        Returns:
            Dictionary of metrics by effect type
        """
        # Add circuit breaker states
        circuit_breaker_metrics = {}
        for service_name, cb in self.circuit_breakers.items():
            circuit_breaker_metrics[f"circuit_breaker_{service_name}"] = {
                "state": float(1 if cb.state == EnumCircuitBreakerState.CLOSED else 0),
                "failure_count": float(cb.failure_count),
                "is_open": float(1 if cb.state == EnumCircuitBreakerState.OPEN else 0),
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
        # Rollback any active transactions
        for transaction_id, transaction in list[Any](self.active_transactions.items()):
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
        """
        Validate effect input data.

        Args:
            input_data: Input data to validate

        Raises:
            ModelOnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not isinstance(input_data.effect_type, EnumEffectType):
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Effect type must be valid EnumEffectType enum",
                context={
                    "node_id": str(self.node_id),
                    "effect_type": str(input_data.effect_type),
                },
            )

        if not isinstance(input_data.operation_data, dict):
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Operation data must be a dict[str, Any]ionary",
                context={
                    "node_id": str(self.node_id),
                    "operation_data_type": type(input_data.operation_data).__name__,
                },
            )

    def _get_circuit_breaker(self, service_name: str) -> ModelCircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = ModelCircuitBreaker()
        return self.circuit_breakers[service_name]

    async def _execute_with_retry(
        self,
        input_data: ModelEffectInput,
        transaction: ModelTransaction | None,
    ) -> Any:
        """Execute effect with retry logic."""
        retry_count = 0
        last_exception: Exception = ModelOnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="No retries executed",
        )

        while retry_count <= input_data.max_retries:
            try:
                # Execute the effect
                return await self._execute_effect(input_data, transaction)

            except Exception as e:
                last_exception = e
                retry_count += 1

                if not input_data.retry_enabled or retry_count > input_data.max_retries:
                    raise

                # Wait before retry with exponential backoff
                delay_ms = input_data.retry_delay_ms * (2 ** (retry_count - 1))
                await asyncio.sleep(delay_ms / 1000.0)

                emit_log_event(
                    LogLevel.WARNING,
                    f"Effect retry {retry_count}/{input_data.max_retries}: {e!s}",
                    {
                        "node_id": str(self.node_id),
                        "operation_id": str(input_data.operation_id),
                        "effect_type": input_data.effect_type.value,
                        "retry_count": retry_count,
                        "delay_ms": delay_ms,
                    },
                )

        # If we get here, all retries failed
        raise last_exception

    async def _execute_effect(
        self,
        input_data: ModelEffectInput,
        transaction: ModelTransaction | None,
    ) -> Any:
        """Execute the actual effect operation."""
        effect_type = input_data.effect_type

        if effect_type in self.effect_handlers:
            handler = self.effect_handlers[effect_type]
            return await handler(input_data.operation_data, transaction)
        raise ModelOnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"No handler registered for effect type: {effect_type.value}",
            context={
                "node_id": str(self.node_id),
                "effect_type": effect_type.value,
                "available_types": [et.value for et in self.effect_handlers],
            },
        )

    async def _update_effect_metrics(
        self,
        effect_type: str,
        processing_time_ms: float,
        success: bool,
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

        # Update timing metrics
        metrics["min_processing_time_ms"] = min(
            metrics["min_processing_time_ms"],
            processing_time_ms,
        )
        metrics["max_processing_time_ms"] = max(
            metrics["max_processing_time_ms"],
            processing_time_ms,
        )

        # Update rolling average
        total_ops = metrics["total_operations"]
        current_avg = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg * (total_ops - 1) + processing_time_ms
        ) / total_ops

    def _register_builtin_effect_handlers(self) -> None:
        """Register built-in effect handlers."""

        async def file_operation_handler(
            operation_data: dict[str, Any],
            transaction: ModelTransaction | None,
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
                        code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                        message=f"File not found: {file_path}",
                        context={"file_path": str(file_path)},
                    )

                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                result["content"] = content
                result["size_bytes"] = len(content.encode("utf-8"))

            elif operation_type == "write":
                if atomic:
                    # Atomic write using temporary file
                    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
                    try:
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(str(data))
                        temp_path.replace(file_path)  # Atomic on most filesystems

                        # Add rollback operation
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
                    # Backup content for rollback
                    backup_content = None
                    if transaction:
                        with open(file_path, encoding="utf-8") as f:
                            backup_content = f.read()

                    file_path.unlink()
                    result["deleted"] = True

                    # Add rollback operation
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
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown file operation: {operation_type}",
                    context={"operation_type": operation_type},
                )

            return result

        async def event_emission_handler(
            operation_data: dict[str, Any],
            transaction: ModelTransaction | None,
        ) -> bool:
            """Handle event emission to event bus."""
            event_type = operation_data["event_type"]
            payload = operation_data["payload"]
            correlation_id = operation_data.get("correlation_id")

            try:
                # Get event bus from container
                event_bus: Any = self.container.get_service("event_bus")
                if not event_bus:
                    emit_log_event(
                        LogLevel.WARNING,
                        "Event bus not available, skipping event emission",
                        {"event_type": event_type},
                    )
                    return False

                # Emit event
                if hasattr(event_bus, "emit_event"):
                    await event_bus.emit_event(
                        event_type=event_type,
                        payload=payload,
                        correlation_id=UUID(correlation_id) if correlation_id else None,
                    )
                    return True
                emit_log_event(
                    LogLevel.WARNING,
                    "Event bus does not support emit_event method",
                    {"event_type": event_type},
                )
                return False

            except (
                Exception
            ) as e:  # fallback-ok: event emission is non-critical, introspection should degrade gracefully
                emit_log_event(
                    LogLevel.ERROR,
                    f"Event emission failed: {e!s}",
                    {"event_type": event_type, "error": str(e)},
                )
                return False  # fallback-ok: graceful degradation for optional functionality

        # Register handlers
        self.effect_handlers[EnumEffectType.FILE_OPERATION] = file_operation_handler
        self.effect_handlers[EnumEffectType.EVENT_EMISSION] = event_emission_handler

    def get_introspection_data(self) -> dict[str, Any]:
        """
        Get comprehensive introspection data for NodeEffect.

        Returns specialized side effect node information including transaction management,
        circuit breaker status, retry policies, and I/O operation capabilities.

        Returns:
            dict[str, Any]: Comprehensive introspection data with effect-specific information
        """
        try:
            # Get base introspection data from NodeCoreBase
            base_data = {
                "node_type": "NodeEffect",
                "node_classification": "effect",
                "node_id": self.node_id,
                "version": self.version,
                "created_at": self.created_at.isoformat(),
                "current_status": self.state.get("status", "unknown"),
            }

            # 1. Node Capabilities (Effect-specific)
            node_capabilities = {
                **base_data,
                "architecture_classification": "side_effect_management",
                "effect_patterns": [
                    "transaction_management",
                    "retry_policies",
                    "circuit_breaker",
                ],
                "available_operations": self._extract_effect_operations(),
                "input_output_specifications": self._extract_effect_io_specifications(),
                "performance_characteristics": self._extract_effect_performance_characteristics(),
            }

            # 2. Contract Details (Effect-specific)
            contract_details = {
                "contract_type": "ModelContractEffect",
                "contract_validation_status": "validated",
                "io_operations_configuration": self._extract_io_operations_configuration(),
                "effect_constraints": self._extract_effect_constraints(),
                "supported_effect_types": [
                    effect_type.value for effect_type in self.effect_handlers
                ],
            }

            # 3. Runtime Information (Effect-specific)
            runtime_info = {
                "current_health_status": self._get_effect_health_status(),
                "effect_metrics": self._get_effect_metrics_sync(),
                "resource_usage": self._get_effect_resource_usage(),
                "transaction_status": self._get_transaction_status(),
                "circuit_breaker_status": self._get_circuit_breaker_status(),
            }

            # 4. Effect Management Information
            effect_management_info = {
                "registered_effect_handlers": list[Any](self.effect_handlers.keys()),
                "effect_handler_count": len(self.effect_handlers),
                "transaction_management_enabled": True,
                "retry_policies_enabled": True,
                "circuit_breaker_enabled": True,
                "atomic_operations_supported": True,
            }

            # 5. Configuration Details
            configuration_details = {
                "default_timeout_ms": self.default_timeout_ms,
                "default_retry_delay_ms": self.default_retry_delay_ms,
                "max_concurrent_effects": self.max_concurrent_effects,
                "semaphore_available": self.effect_semaphore._value,
                "transaction_configuration": {
                    "rollback_support": True,
                    "nested_transactions": False,
                    "automatic_commit": True,
                },
            }

            return {
                "node_capabilities": node_capabilities,
                "contract_details": contract_details,
                "runtime_information": runtime_info,
                "effect_management_information": effect_management_info,
                "configuration_details": configuration_details,
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "node_type": "NodeEffect",
                    "supports_full_introspection": True,
                    "specialization": "side_effect_management_with_transactions_and_circuit_breakers",
                },
            }

        except (
            Exception
        ) as e:  # fallback-ok: introspection is non-critical monitoring, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to generate full effect introspection data: {e!s}, using fallback",
                {"node_id": str(self.node_id), "error": str(e)},
            )

            return {  # fallback-ok: graceful degradation for optional functionality
                "node_capabilities": {
                    "node_type": "NodeEffect",
                    "node_classification": "effect",
                    "node_id": self.node_id,
                },
                "runtime_information": {
                    "current_health_status": "unknown",
                    "effect_handler_count": len(self.effect_handlers),
                },
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "supports_full_introspection": False,
                    "fallback_reason": str(e),
                },
            }

    def _extract_effect_operations(self) -> list[Any]:
        """Extract available effect operations."""
        operations = [
            "process",
            "execute_file_operation",
            "emit_state_change_event",
            "get_effect_metrics",
        ]

        try:
            # Add effect type operations
            for effect_type in self.effect_handlers:
                operations.append(f"handle_{effect_type.value}")

            # Add transaction operations
            operations.extend(
                ["transaction_context", "rollback_transaction", "commit_transaction"],
            )

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract all effect operations: {e!s}",
                {"node_id": str(self.node_id)},
            )

        return operations

    def _extract_effect_io_specifications(self) -> dict[str, Any]:
        """Extract input/output specifications for effect operations."""
        return {
            "input_model": "omnibase.core.node_effect.ModelEffectInput",
            "output_model": "omnibase.core.node_effect.ModelEffectOutput",
            "supports_streaming": False,
            "supports_batch_processing": False,
            "supports_transaction_management": True,
            "effect_types": [effect_type.value for effect_type in EnumEffectType],
            "input_requirements": ["effect_type", "operation_data"],
            "output_guarantees": [
                "result",
                "transaction_state",
                "processing_time_ms",
                "retry_count",
            ],
        }

    def _extract_effect_performance_characteristics(self) -> dict[str, Any]:
        """Extract performance characteristics specific to effect operations."""
        return {
            "expected_response_time_ms": f"< {self.default_timeout_ms}",
            "throughput_capacity": f"up_to_{self.max_concurrent_effects}_concurrent_effects",
            "memory_usage_pattern": "transaction_tracking_with_rollback_operations",
            "cpu_intensity": "low_to_medium_depending_on_io_operations",
            "supports_parallel_processing": True,
            "caching_enabled": False,
            "performance_monitoring": True,
            "deterministic_operations": False,  # Effects can have side effects
            "side_effects": True,
            "atomic_operations": True,
            "rollback_capabilities": True,
        }

    def _extract_io_operations_configuration(self) -> dict[str, Any]:
        """Extract I/O operations configuration from contract."""
        try:
            io_ops = []
            if hasattr(self.contract_model, "io_operations"):
                for io_op in self.contract_model.io_operations:
                    io_ops.append(
                        {
                            "operation_type": io_op.operation_type,
                            "atomic": io_op.atomic,
                            "timeout_seconds": io_op.timeout_seconds,
                        },
                    )

            return {
                "io_operations": io_ops,
                "supports_atomic_operations": True,
                "supports_file_operations": True,
                "supports_event_emission": True,
            }
        except (
            Exception
        ) as e:  # fallback-ok: I/O config extraction is non-critical introspection, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract I/O operations configuration: {e!s}",
                {"node_id": str(self.node_id)},
            )
            return {
                "io_operations": []
            }  # fallback-ok: graceful degradation for optional functionality

    def _extract_effect_constraints(self) -> dict[str, Any]:
        """Extract effect constraints and requirements."""
        return {
            "requires_container": True,
            "supports_transactions": True,
            "supports_rollback": True,
            "requires_event_bus_for_emissions": True,
            "max_concurrent_effects": self.max_concurrent_effects,
            "default_timeout_ms": self.default_timeout_ms,
            "retry_enabled_by_default": True,
            "circuit_breaker_configurable": True,
        }

    def _get_effect_health_status(self) -> str:
        """Get health status specific to effect operations."""
        try:
            # Check if basic effect handling works
            test_input = ModelEffectInput(
                effect_type=EnumEffectType.METRICS_COLLECTION,
                operation_data=_convert_to_scalar_dict({"test": True}),
                transaction_enabled=False,
                retry_enabled=False,
            )

            # For health check, we'll just validate the input without processing
            self._validate_effect_input(test_input)
            return "healthy"

        except Exception:
            return "unhealthy"  # fallback-ok: graceful degradation for optional functionality

    def _get_effect_metrics_sync(self) -> dict[str, Any]:
        """Get effect metrics synchronously for introspection."""
        try:
            # Get circuit breaker states
            circuit_breaker_metrics = {}
            for service_name, cb in self.circuit_breakers.items():
                circuit_breaker_metrics[f"circuit_breaker_{service_name}"] = {
                    "state": float(
                        1 if cb.state == EnumCircuitBreakerState.CLOSED else 0
                    ),
                    "failure_count": float(cb.failure_count),
                    "is_open": float(
                        1 if cb.state == EnumCircuitBreakerState.OPEN else 0
                    ),
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
        except (
            Exception
        ) as e:  # fallback-ok: metrics collection is non-critical monitoring, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get effect metrics: {e!s}",
                {"node_id": str(self.node_id)},
            )
            return {
                "status": "unknown",
                "error": str(e),
            }  # fallback-ok: graceful degradation for optional functionality

    def _get_effect_resource_usage(self) -> dict[str, Any]:
        """Get resource usage specific to effect operations."""
        try:
            return {
                "active_transactions": len(self.active_transactions),
                "effect_semaphore_available": self.effect_semaphore._value,
                "circuit_breakers_count": len(self.circuit_breakers),
                "effect_handlers_registered": len(self.effect_handlers),
                "max_concurrent_effects": self.max_concurrent_effects,
            }
        except (
            Exception
        ) as e:  # fallback-ok: resource usage monitoring is non-critical, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get effect resource usage: {e!s}",
                {"node_id": str(self.node_id)},
            )
            return {
                "status": "unknown"
            }  # fallback-ok: graceful degradation for optional functionality

    def _get_transaction_status(self) -> dict[str, Any]:
        """Get transaction management status."""
        try:
            transaction_states = {}
            for transaction_id, transaction in self.active_transactions.items():
                transaction_states[transaction_id] = {
                    "state": transaction.state.value,
                    "operations_count": len(transaction.operations),
                    "rollback_operations_count": len(transaction.rollback_operations),
                    "started_at": transaction.started_at.isoformat(),
                }

            return {
                "active_transaction_count": len(self.active_transactions),
                "transaction_details": transaction_states,
                "supports_nested_transactions": False,
                "supports_rollback": True,
            }
        except (
            Exception
        ) as e:  # fallback-ok: transaction status monitoring is non-critical, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get transaction status: {e!s}",
                {"node_id": str(self.node_id)},
            )
            return {
                "status": "unknown",
                "error": str(e),
            }  # fallback-ok: graceful degradation for optional functionality

    def _get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        try:
            circuit_breaker_states = {}
            for service_name, cb in self.circuit_breakers.items():
                circuit_breaker_states[service_name] = {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "failure_threshold": cb.failure_threshold,
                    "recovery_timeout_seconds": cb.recovery_timeout_seconds,
                    "last_failure_time": (
                        cb.last_failure_time.isoformat()
                        if cb.last_failure_time
                        else None
                    ),
                }

            return {
                "circuit_breaker_count": len(self.circuit_breakers),
                "circuit_breaker_details": circuit_breaker_states,
                "default_failure_threshold": 5,
                "default_recovery_timeout_seconds": 60,
            }
        except (
            Exception
        ) as e:  # fallback-ok: circuit breaker status monitoring is non-critical, should degrade gracefully
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get circuit breaker status: {e!s}",
                {"node_id": str(self.node_id)},
            )
            return {
                "status": "unknown",
                "error": str(e),
            }  # fallback-ok: graceful degradation for optional functionality
