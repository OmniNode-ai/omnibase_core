"""
NodeEffect - Contract-driven effect node for external I/O operations.

Contract-driven implementation using ModelEffectSubcontract for declarative I/O.
Zero custom Python code required - all effect logic defined in YAML contracts.

VERSION: 2.0.0
STABILITY GUARANTEE: Effect subcontract interface is stable.

.. versionchanged:: 0.4.0
    Refactored from code-driven to contract-driven implementation.
    Legacy code-driven implementation available in nodes/legacy/node_effect_legacy.py

Author: ONEX Framework Team
"""

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Error messages
_ERR_EFFECT_SUBCONTRACT_NOT_LOADED = "Effect subcontract not loaded"


class NodeEffect(NodeCoreBase, MixinEffectExecution):
    """
    Contract-driven effect node for external I/O operations.

    Enables creating effect nodes entirely from YAML contracts without custom Python code.
    Effect operations, retry policies, circuit breakers, and transaction boundaries
    are all defined declaratively in effect subcontracts.

    Pattern:
        class NodeMyEffect(NodeEffect):
            # No custom code needed - driven entirely by YAML contract
            pass

    Contract Injection:
        The node requires an effect subcontract to be provided. Two approaches:

        1. **Manual Injection** (recommended for testing/simple usage):
            ```python
            node = NodeMyEffect(container)
            node.effect_subcontract = ModelEffectSubcontract(...)
            ```

        2. **Automatic Loading** (for production with YAML contracts):
            - Use `MixinContractMetadata` to auto-load from YAML files
            - The mixin provides `self.contract` with effect_operations field
            - See `docs/guides/contracts/` for contract loading patterns

    Example YAML Contract:
        ```yaml
        effect_operations:
          version:
            major: 1
            minor: 0
            patch: 0
          operation_name: user_api_effect
          operation_version: "1.0.0"
          description: "Create user via REST API"
          execution_order: forward

          default_retry_policy:
            max_attempts: 3
            backoff_strategy: exponential
            base_delay_ms: 1000

          operations:
            - operation_name: create_user
              description: "POST user to API"
              io_config:
                handler_type: http
                url_template: "https://api.example.com/users"
                method: POST
                body_template: '{"name": "${input.name}"}'
                timeout_ms: 5000
              response_handling:
                success_codes: [200, 201]
                extract_fields:
                  user_id: "$.id"
        ```

    Usage:
        ```python
        from omnibase_core.nodes import NodeEffect
        from omnibase_core.models.effect import ModelEffectInput
        from omnibase_core.enums.enum_effect_types import EnumEffectType

        # Create effect node
        node = NodeMyEffect(container)
        node.effect_subcontract = effect_subcontract  # Or auto-loaded from contract

        # Execute effect - effect_type and operation_data are required fields
        result = await node.process(ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "name": "John Doe",
                "email": "john@example.com",
            },
            retry_enabled=True,
            max_retries=3,
            timeout_ms=5000,
        ))
        ```

    Thread Safety:
        - Circuit breaker state is process-local and NOT thread-safe
        - Each thread should have its own NodeEffect instance
        - See docs/guides/THREADING.md for guidelines

    See Also:
        - :class:`MixinEffectExecution`: Provides execute_effect() implementation
        - :class:`ModelEffectSubcontract`: Effect contract specification
        - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification

    .. versionchanged:: 0.4.0
        Refactored to contract-driven pattern using MixinEffectExecution.
    """

    # Type annotations for attributes
    effect_subcontract: ModelEffectSubcontract | None
    _circuit_breakers: dict[UUID, ModelCircuitBreaker]

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeEffect with container dependency injection.

        Args:
            container: ONEX container for dependency injection and service resolution

        Note:
            After construction, set `effect_subcontract` before calling `process()`.
            Alternatively, use contract auto-loading via MixinContractMetadata.
        """
        super().__init__(container)

        # Effect subcontract - set after construction or via contract loading
        object.__setattr__(self, "effect_subcontract", None)

        # Process-local circuit breaker state keyed by operation_id.
        # operation_id is stable per operation definition (from the contract),
        # providing consistent circuit breaker state across requests.
        # NOT thread-safe - each thread needs its own NodeEffect instance.
        object.__setattr__(self, "_circuit_breakers", {})

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Execute effect operations defined in the subcontract.

        REQUIRED: This method implements the NodeEffect interface for contract-driven
        effect execution. All effect logic is driven by the effect_subcontract.

        Timeout Behavior:
            Timeouts are checked at the start of each retry attempt, not during
            operation execution. This means an operation that starts before the
            timeout may complete even if it exceeds the overall timeout window.
            For strict timeout enforcement during execution, handlers should
            implement their own timeout logic (e.g., HTTP client timeouts).

        Args:
            input_data: Effect input containing operation_data for template resolution

        Returns:
            ModelEffectOutput with operation results, timing, and transaction state

        Raises:
            ModelOnexError: If effect_subcontract is not loaded or execution fails
        """
        if self.effect_subcontract is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                message=_ERR_EFFECT_SUBCONTRACT_NOT_LOADED,
                context={"node_id": str(self.node_id)},
            )

        # Map subcontract-level defaults to ModelEffectInput fields
        # This ensures the mixin receives properly configured input with:
        # - Retry settings from default_retry_policy
        # - Circuit breaker settings from default_circuit_breaker
        # - Transaction settings from default_transaction_config
        #
        # Input values take precedence over subcontract defaults (caller override).
        # This allows callers to override subcontract defaults at runtime.
        default_retry = self.effect_subcontract.default_retry_policy
        default_cb = self.effect_subcontract.default_circuit_breaker
        default_tx = self.effect_subcontract.default_transaction_config

        # Build update dict with subcontract defaults, respecting existing input values
        input_updates: dict[str, object] = {}

        # Retry policy: use subcontract defaults unless input explicitly differs
        # We check against ModelEffectInput defaults to detect caller overrides
        if input_data.retry_enabled and input_data.max_retries == 3:  # default value
            input_updates["max_retries"] = default_retry.max_attempts
        if input_data.retry_enabled and input_data.retry_delay_ms == 1000:  # default
            input_updates["retry_delay_ms"] = default_retry.base_delay_ms

        # Circuit breaker: inherit from subcontract if enabled there
        if not input_data.circuit_breaker_enabled and default_cb.enabled:
            input_updates["circuit_breaker_enabled"] = True

        # Transaction: inherit from subcontract if enabled there
        if input_data.transaction_enabled and default_tx.enabled:
            # Transaction is already enabled by default in ModelEffectInput,
            # so we just ensure it stays enabled if subcontract wants it
            pass
        elif not input_data.transaction_enabled and default_tx.enabled:
            input_updates["transaction_enabled"] = True

        # Apply updates if any
        if input_updates:
            input_data = input_data.model_copy(update=input_updates)

        # Transform effect_subcontract.operations into operation_data format
        # The mixin expects operations in input_data.operation_data["operations"]
        # This transformation bridges the contract (YAML) and execution (mixin)
        if "operations" not in input_data.operation_data:
            # Serialize subcontract operations to the format expected by the mixin
            operations: list[dict[str, object]] = []
            for op in self.effect_subcontract.operations:
                # Timeout fallback: use operation-specific timeout if defined,
                # otherwise fall back to 30s as a safe default.
                # NOTE: We intentionally do NOT use max_delay_ms (max delay between
                # retries) as a fallback because it has different semantics.
                # For precise control, always set operation_timeout_ms explicitly
                # in the operation definition.
                timeout_ms = op.operation_timeout_ms or 30000

                # Merge operation-level overrides with subcontract defaults
                # Operation retry_policy/circuit_breaker override subcontract defaults
                op_retry = op.retry_policy or default_retry
                op_cb = op.circuit_breaker or default_cb
                op_tx = op.transaction_config or default_tx

                op_dict: dict[str, object] = {
                    "operation_name": op.operation_name,
                    "description": op.description,
                    "io_config": (
                        op.io_config.model_dump()
                        if hasattr(op.io_config, "model_dump")
                        else op.io_config
                    ),
                    "operation_timeout_ms": timeout_ms,
                    # Include response handling for field extraction
                    "response_handling": (
                        op.response_handling.model_dump()
                        if hasattr(op.response_handling, "model_dump")
                        else {}
                    ),
                    # Include merged retry/circuit breaker/transaction configs
                    "retry_policy": (
                        op_retry.model_dump() if hasattr(op_retry, "model_dump") else {}
                    ),
                    "circuit_breaker": (
                        op_cb.model_dump() if hasattr(op_cb, "model_dump") else {}
                    ),
                    "transaction_config": (
                        op_tx.model_dump() if hasattr(op_tx, "model_dump") else {}
                    ),
                }
                operations.append(op_dict)

            # Create new input_data with operations populated
            updated_operation_data = {
                **input_data.operation_data,
                "operations": operations,
            }
            input_data = input_data.model_copy(
                update={"operation_data": updated_operation_data}
            )

        # Delegate to mixin's execute_effect which handles:
        # - Sequential operation execution
        # - Template resolution
        # - Retry with idempotency awareness
        # - Circuit breaker management
        # - Transaction boundaries
        # - Response field extraction
        return await self.execute_effect(input_data)

    def get_circuit_breaker(self, operation_id: UUID) -> ModelCircuitBreaker:
        """
        Get or create circuit breaker for an operation.

        Circuit breakers are keyed by operation_id and maintain
        process-local state for failure tracking and recovery.

        Default Configuration:
            Uses ModelCircuitBreaker.create_resilient() which provides production-ready
            defaults (failure_threshold=10, success_threshold=5, timeout_seconds=120).
            This aligns with MixinEffectExecution._check_circuit_breaker() for
            consistent behavior between NodeEffect and the mixin.

        Args:
            operation_id: Unique identifier for the operation being protected

        Returns:
            ModelCircuitBreaker instance for the operation with resilient defaults

        Note:
            Circuit breakers are NOT thread-safe. Each thread should use
            its own NodeEffect instance.
        """
        if operation_id not in self._circuit_breakers:
            # Use create_resilient() for production-ready defaults, matching mixin behavior
            self._circuit_breakers[operation_id] = (
                ModelCircuitBreaker.create_resilient()
            )
        return self._circuit_breakers[operation_id]

    def reset_circuit_breakers(self) -> None:
        """
        Reset all circuit breakers to closed state.

        Useful for testing or after a system recovery. Clears all
        circuit breaker state, allowing operations to proceed normally.
        """
        self._circuit_breakers.clear()

    async def _initialize_node_resources(self) -> None:  # stub-ok
        """Initialize effect-specific resources.

        Circuit breakers are lazily initialized on first use via get_circuit_breaker().
        No additional resources needed for contract-driven execution.
        """

    async def _cleanup_node_resources(self) -> None:
        """Cleanup effect-specific resources."""
        # Clear circuit breaker state
        self._circuit_breakers.clear()
