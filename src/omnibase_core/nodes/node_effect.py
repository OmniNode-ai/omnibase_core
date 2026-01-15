"""
NodeEffect - Contract-driven effect node for external I/O operations.

Contract-driven implementation using ModelEffectSubcontract for declarative I/O.
Zero custom Python code required - all effect logic defined in YAML contracts.

VERSION: 2.0.0
STABILITY GUARANTEE: Effect subcontract interface is stable.

Key Capabilities:
- Side-effect management with external interaction focus
- I/O operation abstraction (file, database, API calls)
- ModelEffectTransaction management for rollback support
- Retry policies and circuit breaker patterns
- Event bus publishing for state changes
- Atomic file operations for data integrity
- Contract-driven handler routing via MixinHandlerRouting (OMN-1293)

.. versionchanged:: 0.4.0
    Refactored from code-driven to contract-driven implementation.

Author: ONEX Framework Team
"""

import warnings
from uuid import UUID

from omnibase_core.constants.constants_effect import DEFAULT_OPERATION_TIMEOUT_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution
from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting
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

# Warning messages for v1.0 limitations
_WARN_PER_OP_CONFIG_NOT_HONORED = (
    "v1.0 LIMITATION: Per-operation '{config_name}' detected but will NOT be applied. "
    "Only subcontract-level defaults are honored in v1.0. "
    "This will be fully implemented in v2.0. See: OMN-467"
)

# Module-level flags to emit warnings only once per session (matching compute_executor pattern)
#
# Thread Safety Notes:
# - These are Python interpreter-level singletons, shared across all NodeEffect instances
# - In pytest-xdist parallel tests, each worker process has its own copy (isolated)
# - NOT thread-safe: race condition possible if multiple threads create NodeEffect
#   instances simultaneously during initialization
# - This is acceptable because:
#   1. ONEX nodes are NOT thread-safe by default (see CLAUDE.md Thread Safety Matrix)
#   2. Pattern matches existing compute_executor.py behavior
#   3. Worst case impact: a few duplicate warnings (not data corruption)
# - If thread-safe "emit once" behavior is needed in future, use threading.Lock
_per_op_retry_warning_emitted: bool = False
_per_op_circuit_breaker_warning_emitted: bool = False
_per_op_response_handling_warning_emitted: bool = False


class NodeEffect(NodeCoreBase, MixinEffectExecution, MixinHandlerRouting):
    """
    Contract-driven effect node for external I/O operations.

    Enables creating effect nodes entirely from YAML contracts without custom Python code.
    Effect operations, retry policies, circuit breakers, and transaction boundaries
    are all defined declaratively in effect subcontracts.

    Pattern:
        class NodeMyEffect(NodeEffect):
            # No custom code needed - driven entirely by YAML contract
            pass

    .. versionadded:: 0.4.0
        Primary EFFECT node implementation for ONEX 4-node architecture.
        Provides transaction management, retry policies, and circuit breaker
        patterns for external I/O operations.

    Key Features:
    - ModelEffectTransaction management with rollback support
    - Retry policies with exponential backoff
    - Circuit breaker patterns for failure handling
    - Atomic file operations for data integrity
    - Event bus integration for state changes
    - Performance monitoring and logging
    - Contract-driven handler routing via MixinHandlerRouting

    Handler Routing (via MixinHandlerRouting):
        Enables routing messages to handlers based on YAML contract configuration.
        Use ``operation_match`` routing strategy for effect nodes to route by
        operation field value (e.g., "http.get", "db.insert").

        Example handler_routing contract section:
            handler_routing:
              version: { major: 1, minor: 0, patch: 0 }
              routing_strategy: operation_match
              handlers:
                - routing_key: http.get
                  handler_key: handle_http_get
                - routing_key: db.insert
                  handler_key: handle_db_insert
              default_handler: handle_unknown_operation

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
          subcontract_name: user_api_effect
          description: "Create user via REST API"
          # execution_mode controls failure handling behavior:
          #   - sequential_abort: Stop on first failure, raise immediately (default)
          #   - sequential_continue: Run all operations, report all outcomes
          # Note: v1.0 only supports single-operation effects.
          execution_mode: sequential_abort

          default_retry_policy:
            max_retries: 3
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
        import logging
        from omnibase_core.nodes import NodeEffect
        from omnibase_core.models.effect import ModelEffectInput
        from omnibase_core.enums.enum_effect_types import EnumEffectType

        logger = logging.getLogger(__name__)

        # Create effect node
        node = NodeMyEffect(container)
        node.effect_subcontract = effect_subcontract  # Or auto-loaded from contract

        # Execute effect - effect_type and operation_data are required fields
        # Note: The 'operations' key in operation_data is populated automatically
        # from effect_subcontract.operations by the process() method.
        # Caller-provided data in operation_data is used for template resolution
        # (e.g., ${input.name} will resolve to "John Doe").
        #
        # Merge Strategy (caller-takes-precedence):
        # - Subcontract defaults (default_retry_policy, default_circuit_breaker,
        #   transaction) provide baseline configuration
        # - Caller-provided values in ModelEffectInput take precedence
        # - Per-operation configs (response_handling, retry_policy, circuit_breaker)
        #   are serialized into operation_data["operations"] for handler access
        result = await node.process(ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                # Template resolution context - values used in ${input.field} templates
                "name": "John Doe",
                "email": "john@example.com",
            },
            # Optional: override retry behavior (caller values take precedence)
            # retry_enabled=True,  # Default: True
            # max_retries=5,  # Overrides subcontract.default_retry_policy.max_retries
            # circuit_breaker_enabled=True,  # Overrides subcontract.default_circuit_breaker
        ))

        # Access result
        if result.transaction_state == EnumTransactionState.COMMITTED:
            logger.info("Effect succeeded: %s", result.result)
        else:
            logger.error("Effect failed: %s", result.metadata)

        # Example with minimal required fields:
        result = await node.process(ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"path": "/data/output.json"},
        ))
        ```

    Thread Safety:
        WARNING: NodeEffect instances are NOT thread-safe. Do not share
        instances across threads. Each thread should create its own instance.

        For debugging, set ONEX_DEBUG_THREAD_SAFETY=1 to enable runtime
        thread affinity checks that will raise ModelOnexError if cross-thread
        access is detected. See docs/guides/THREADING.md for details.

        Technical notes:
        - Circuit breaker state is process-local and NOT thread-safe
        - Each thread should have its own NodeEffect instance

    v1.0 Limitations:
        Per-operation configs (response_handling, retry_policy, circuit_breaker,
        transaction_config) are parsed from YAML but not yet fully honored.
        Only subcontract-level defaults are applied. See process() docstring
        for details on what is and is not supported in v1.0.

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

        # Note: Handler routing initialization is not performed here because
        # ModelEffectSubcontract does not include handler_routing configuration.
        # Effect nodes use effect_subcontract for operation definitions, which
        # handles I/O operations directly rather than routing to message handlers.
        # For nodes that need handler routing (e.g., NodeOrchestrator), the
        # MixinHandlerRouting can be initialized with a contract that includes
        # handler_routing subcontract configuration.

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Execute effect operations defined in the subcontract.

        REQUIRED: This method implements the NodeEffect interface for contract-driven
        effect execution. All effect logic is driven by the effect_subcontract.

        Operation Source:
            Operations are sourced from self.effect_subcontract.operations and
            transformed into operation_data["operations"] format before delegation
            to the mixin. This transformation:
            1. Serializes each ModelEffectOperation to dict format
            2. Merges per-operation retry_policy/circuit_breaker with subcontract defaults
            3. Includes response_handling, timeout, and other operation configs
            4. Preserves all operation metadata for handler access

            Callers can also pre-populate operation_data["operations"] directly to
            bypass this transformation (advanced usage for custom operation sources).

        Timeout Behavior:
            Timeouts are checked at the start of each retry attempt, not during
            operation execution. This means an operation that starts before the
            timeout may complete even if it exceeds the overall timeout window.
            For strict timeout enforcement during execution, handlers should
            implement their own timeout logic (e.g., HTTP client timeouts).

        Note:
            **v1.0 Limitation - Per-Operation Configs Not Yet Honored**

            Per-operation configuration settings (response_handling, retry_policy,
            circuit_breaker, transaction_config) are parsed from the YAML contract
            and serialized into operation_data["operations"]. However, in v1.0,
            these per-operation settings are NOT YET fully honored by the effect
            execution pipeline:

            - **response_handling**: Parsed and included in operation_config, but
              handlers only receive ResolvedIOContext. Field extraction via
              extract_fields is available as a utility (_extract_response_fields)
              but not automatically applied. Callers must implement their own
              response processing logic.

            - **retry_policy** (per-operation): Parsed but NOT wired to the retry
              loop. Only subcontract-level default_retry_policy (applied to
              input_data.max_retries and retry_delay_ms) is honored.

            - **circuit_breaker** (per-operation): Parsed but NOT wired to circuit
              breaker checks. Only input_data.circuit_breaker_enabled is checked,
              using a default ModelCircuitBreaker configuration.

            - **transaction_config**: Subcontract-level only; per-operation
              transaction boundaries are not supported.

            Future versions will wire these configurations to handlers or adjust
            the handler contract to receive full operation_config. See
            docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md for the v1.0
            specification and planned enhancements.

        Args:
            input_data: Effect input containing operation_data for template resolution

        Returns:
            ModelEffectOutput with operation results, timing, and transaction state

        Raises:
            ModelOnexError: If effect_subcontract is not loaded or execution fails
        """
        # Thread safety check (zero overhead when disabled)
        self._check_thread_safety()

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
        # Merge Strategy (caller-takes-precedence):
        # - Subcontract defaults provide baseline configuration
        # - Caller-provided values in input_data take precedence over subcontract defaults
        # - This allows callers to override contract defaults for specific use cases
        #   while still benefiting from sensible defaults when not specified
        #
        # Detection of caller-provided values:
        # - We compare against ModelEffectInput's Pydantic field defaults
        # - If value differs from the field default, caller explicitly set it
        # - This approach uses Pydantic introspection to avoid hardcoded defaults
        #
        # IMPORTANT LIMITATION: If caller explicitly sets a value that equals the
        # model default (e.g., max_retries=3), the subcontract default will be applied
        # instead. This is a detection limitation - we cannot distinguish "caller set
        # to default value" from "caller omitted and Pydantic used default". If you
        # need precise control, ensure caller values differ from ModelEffectInput
        # defaults, or set subcontract defaults to match desired fallback values.
        default_retry = self.effect_subcontract.default_retry_policy
        default_cb = self.effect_subcontract.default_circuit_breaker
        default_tx = self.effect_subcontract.transaction

        # Get ModelEffectInput field defaults for comparison
        # This uses Pydantic's model_fields to get declared defaults
        model_defaults = {
            name: field.default
            for name, field in ModelEffectInput.model_fields.items()
            if field.default is not None
        }

        # Build update dict with subcontract defaults (caller-takes-precedence)
        input_updates: dict[str, object] = {}

        # Retry policy: apply subcontract defaults only if caller used defaults
        # Caller-provided values take precedence over subcontract defaults
        if input_data.retry_enabled:
            # Only apply subcontract max_retries if caller didn't explicitly set it
            if input_data.max_retries == model_defaults.get("max_retries", 3):
                input_updates["max_retries"] = default_retry.max_retries
            # Only apply subcontract retry_delay_ms if caller didn't explicitly set it
            if input_data.retry_delay_ms == model_defaults.get("retry_delay_ms", 1000):
                input_updates["retry_delay_ms"] = default_retry.base_delay_ms

        # Circuit breaker: enable if subcontract specifies it AND caller didn't disable
        # Caller explicitly setting circuit_breaker_enabled=False takes precedence
        if default_cb.enabled:
            # Only enable if caller used the default (False)
            if input_data.circuit_breaker_enabled == model_defaults.get(
                "circuit_breaker_enabled", False
            ):
                input_updates["circuit_breaker_enabled"] = True

        # Transaction: enable if subcontract specifies AND caller hasn't explicitly disabled
        # Note: transaction_enabled defaults to True in ModelEffectInput, so this check
        # effectively validates the caller hasn't set transaction_enabled=False.
        # We don't need to apply an update if both agree (True), but we include it
        # for consistency with the pattern and to support future default changes.
        if default_tx.enabled and input_data.transaction_enabled:
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
                # otherwise fall back to DEFAULT_OPERATION_TIMEOUT_MS (30s).
                # NOTE: We intentionally do NOT use max_delay_ms (max delay between
                # retries) as a fallback because it has different semantics.
                # For precise control, always set operation_timeout_ms explicitly
                # in the operation definition.
                timeout_ms = op.operation_timeout_ms or DEFAULT_OPERATION_TIMEOUT_MS

                # Merge operation-level overrides with subcontract defaults
                # Operation retry_policy/circuit_breaker override subcontract defaults
                # Note: transaction_config is subcontract-level only (not per-operation)
                op_retry = op.retry_policy or default_retry
                op_cb = op.circuit_breaker or default_cb
                op_tx = default_tx

                # v1.0 LIMITATION: Emit runtime warnings when per-operation configs
                # are detected. These configs are parsed but NOT honored in v1.0.
                # Only subcontract-level defaults are applied during execution.
                # Warnings are emitted once per session to avoid noise (matching
                # compute_executor.py pattern).
                global _per_op_retry_warning_emitted
                global _per_op_circuit_breaker_warning_emitted
                global _per_op_response_handling_warning_emitted

                if op.retry_policy is not None and not _per_op_retry_warning_emitted:
                    warnings.warn(
                        _WARN_PER_OP_CONFIG_NOT_HONORED.format(
                            config_name="retry_policy",
                        ),
                        UserWarning,
                        stacklevel=2,
                    )
                    _per_op_retry_warning_emitted = True
                if (
                    op.circuit_breaker is not None
                    and not _per_op_circuit_breaker_warning_emitted
                ):
                    warnings.warn(
                        _WARN_PER_OP_CONFIG_NOT_HONORED.format(
                            config_name="circuit_breaker",
                        ),
                        UserWarning,
                        stacklevel=2,
                    )
                    _per_op_circuit_breaker_warning_emitted = True
                if (
                    op.response_handling is not None
                    and not _per_op_response_handling_warning_emitted
                ):
                    warnings.warn(
                        _WARN_PER_OP_CONFIG_NOT_HONORED.format(
                            config_name="response_handling",
                        ),
                        UserWarning,
                        stacklevel=2,
                    )
                    _per_op_response_handling_warning_emitted = True

                op_dict: dict[str, object] = {
                    "operation_name": op.operation_name,
                    "description": op.description,
                    "io_config": op.io_config.model_dump(),
                    "operation_timeout_ms": timeout_ms,
                    # Include response handling for field extraction
                    "response_handling": (
                        op.response_handling.model_dump()
                        if op.response_handling is not None
                        else {}
                    ),
                    # Include merged retry/circuit breaker/transaction configs
                    "retry_policy": op_retry.model_dump(),
                    "circuit_breaker": op_cb.model_dump(),
                    "transaction_config": op_tx.model_dump(),
                }
                # TODO(OMN-TBD): [v2.0] Per-operation configs (response_handling, retry_policy,
                # circuit_breaker) are serialized into operation_data but NOT YET
                # wired to the execution pipeline. Only subcontract-level defaults
                # are honored. See process() docstring "v1.0 Limitation" note.  [NEEDS TICKET]
                operations.append(op_dict)

            # Create new input_data with operations populated
            # Convert operation_data to dict for unpacking (handles ModelEffectInputData)
            operation_data_dict = (
                input_data.operation_data
                if isinstance(input_data.operation_data, dict)
                else input_data.operation_data.model_dump()
            )
            updated_operation_data = {
                **operation_data_dict,
                "operations": operations,
            }
            input_data = input_data.model_copy(
                update={"operation_data": updated_operation_data}
            )

        # Delegate to mixin's execute_effect which handles:
        # - Sequential operation execution
        # - Template resolution
        # - Retry with idempotency awareness (using subcontract defaults)
        # - Circuit breaker management (using subcontract defaults)
        #
        # NOTE: Transaction boundaries and response field extraction are NOT
        # automatically handled by the mixin. Callers must implement these
        # if needed. See MixinEffectExecution._extract_response_fields() for
        # field extraction utility.
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

            When ONEX_DEBUG_THREAD_SAFETY=1 is set, this method validates
            thread safety at runtime.
        """
        # Thread safety check (zero overhead when disabled)
        self._check_thread_safety()

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
