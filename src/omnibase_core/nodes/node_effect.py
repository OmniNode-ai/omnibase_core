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

        # Create effect node
        node = NodeMyEffect(container)
        node.effect_subcontract = effect_subcontract  # Or auto-loaded from contract

        # Execute effect
        result = await node.process(ModelEffectInput(
            operation_data={"name": "John Doe"}
        ))
        ```

    Thread Safety:
        - Circuit breaker state is process-local and NOT thread-safe
        - Each thread should have its own NodeEffect instance
        - See docs/THREADING.md for guidelines

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

        # Process-local circuit breaker state keyed by operation correlation_id
        # NOT thread-safe - each thread needs its own NodeEffect instance
        object.__setattr__(self, "_circuit_breakers", {})

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Execute effect operations defined in the subcontract.

        REQUIRED: This method implements the NodeEffect interface for contract-driven
        effect execution. All effect logic is driven by the effect_subcontract.

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

        Circuit breakers are keyed by operation correlation_id and maintain
        process-local state for failure tracking and recovery.

        Args:
            operation_id: Operation identifier (typically correlation_id UUID)

        Returns:
            ModelCircuitBreaker instance for the operation

        Note:
            Circuit breakers are NOT thread-safe. Each thread should use
            its own NodeEffect instance.
        """
        if operation_id not in self._circuit_breakers:
            self._circuit_breakers[operation_id] = ModelCircuitBreaker()
        return self._circuit_breakers[operation_id]

    def reset_circuit_breakers(self) -> None:
        """
        Reset all circuit breakers to closed state.

        Useful for testing or after a system recovery. Clears all
        circuit breaker state, allowing operations to proceed normally.
        """
        self._circuit_breakers.clear()

    async def _initialize_node_resources(self) -> None:
        """Initialize effect-specific resources."""
        # Circuit breakers are lazily initialized
        # No additional resources needed for contract-driven execution
        pass

    async def _cleanup_node_resources(self) -> None:
        """Cleanup effect-specific resources."""
        # Clear circuit breaker state
        self._circuit_breakers.clear()
