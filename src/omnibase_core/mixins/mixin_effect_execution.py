"""
Mixin for contract-driven effect execution.

This module provides a mixin class that adds contract-driven I/O execution
capabilities to NodeEffect instances. It orchestrates external interactions
(HTTP, DB, Kafka, Filesystem) with comprehensive resilience patterns including
retry policies, circuit breakers, and transaction management.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

IMPORTANT - Handler Protocol Extensibility:
    Effect handlers (ProtocolEffectHandler_HTTP, ProtocolEffectHandler_DB, etc.)
    are NOT defined in omnibase_core. They are EXTENSIBILITY POINTS that
    implementing applications MUST register via the container. See the
    _execute_operation() method docstring for registration details.

    Example handler registration (in your application code):
        container.register_service(
            "ProtocolEffectHandler_HTTP",
            MyHttpEffectHandler()  # Your implementation
        )

Thread Safety:
    The mixin methods are stateless and operate on passed arguments only.
    However, circuit breaker state is process-local and NOT thread-safe.
    NodeEffect instances using this mixin MUST be single-threaded or use
    explicit synchronization for circuit breaker access.

Execution Semantics:
    - Sequential operations only (v1.0)
    - Abort on first failure
    - operation_timeout_ms guards overall operation time including retries
    - Retry only idempotent operations
    - Template resolution happens ONCE before retry loop (v1.0 optimization)

Handler Contract:
    - Handlers receive fully-resolved context (ModelResolvedIOContext)
    - Handlers NEVER perform template resolution
    - Handlers are protocol-based and registered via container
    - Handler protocol: async def execute(context: ResolvedIOContext) -> object

Performance Characteristics:
    - Template resolution: O(n) where n = number of template variables
    - Retry overhead: Resolved context cached across attempts (v1.0 behavior)
    - Circuit breaker: O(1) lookup by operation_id
    - Field extraction: O(d) where d = field path depth (max 10)

    For high-throughput optimization opportunities, see PERFORMANCE NOTE
    comments in _execute_with_retry() and _resolve_io_context().

Usage:
    This mixin is designed to be used with NodeEffect classes that need to
    execute contract-driven I/O operations.

Example:
    >>> from omnibase_core.mixins import MixinEffectExecution
    >>> from omnibase_core.nodes import NodeEffect
    >>>
    >>> class MyEffectNode(NodeEffect, MixinEffectExecution):
    ...     async def process(self, input_data):
    ...         result = await self.execute_effect(input_data)
    ...         return result

See Also:
    - :mod:`omnibase_core.models.effect.model_effect_input`: Input model
    - :mod:`omnibase_core.models.effect.model_effect_output`: Output model
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_io_configs`: IO configs
    - :class:`ModelEffectSubcontract`: Effect contract specification
    - :class:`NodeEffect`: The primary node using this mixin
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - docs/guides/THREADING.md: Thread safety guidelines

Author: ONEX Framework Team
"""

import asyncio
import os
import random
import re
import threading
import time
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


# Import canonical allow_dict_any decorator directly from the specific module
# (not from omnibase_core.decorators package) to avoid potential circular imports.
# decorator_allow_dict_any.py has no omnibase_core imports, making this safe.
from omnibase_core.constants.constants_effect import (
    DEBUG_THREAD_SAFETY,
    DEFAULT_MAX_FIELD_EXTRACTION_DEPTH,
    DEFAULT_OPERATION_TIMEOUT_MS,
    DEFAULT_RETRY_JITTER_FACTOR,
    SAFE_FIELD_PATTERN,
    contains_denied_builtin,
)
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.context import ModelEffectInputData
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_resolved_context import (
    ModelResolvedDbContext,
    ModelResolvedFilesystemContext,
    ModelResolvedHttpContext,
    ModelResolvedKafkaContext,
    ResolvedIOContext,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_effect_operation_config import (
    ModelEffectOperationConfig,
)
from omnibase_core.types.type_effect_result import DbParamType, EffectResultType

__all__ = ["MixinEffectExecution"]

# Template placeholder pattern for ${...} resolution
TEMPLATE_PATTERN = re.compile(r"\$\{([^}]+)\}")


class MixinEffectExecution:
    """
    Mixin for contract-driven effect execution.

    Provides async I/O execution with comprehensive resilience patterns for
    NodeEffect instances that use contract-driven operations. This mixin
    orchestrates handler dispatch, template resolution, retry logic, circuit
    breakers, and transaction management.

    Thread Safety:
        The mixin methods themselves are stateless. However, circuit breaker
        state is stored in instance variables and is NOT thread-safe. When
        using with NodeEffect, each instance should be used from a single
        thread or with appropriate synchronization.

    Attributes:
        node_id (UUID): Expected to be provided by the mixing class. Used for
            logging and tracing purposes.
        container (ModelONEXContainer): Expected to be provided by the mixing
            class. Used for handler resolution and service lookup.
        _circuit_breakers (dict[UUID, ModelCircuitBreaker]): Internal circuit
            breaker state, keyed by operation_id (UUID). Each operation gets
            its own circuit breaker to track failure/success patterns
            independently. Process-local only in v1.0 (no cross-process state
            sharing). IMPORTANT: Must be initialized by the concrete class
            (e.g., NodeEffect), not by this mixin. The mixin provides methods
            that operate on this state but does not own its initialization.
            Note: The key is operation_id (not correlation_id) because circuit
            breaker state should be consistent per operation definition across
            multiple requests.

    Example:
        >>> class MyEffectNode(NodeEffect, MixinEffectExecution):
        ...     async def process(self, input_data):
        ...         # Execute effect with full resilience
        ...         result = await self.execute_effect(input_data)
        ...         if result.transaction_state == EnumTransactionState.COMMITTED:
        ...             return result.result
        ...         else:
        ...             raise EffectError(f"Effect failed: {result.metadata}")
    """

    # Type hints for attributes that should exist on the mixing class
    node_id: UUID
    container: "ModelONEXContainer"  # Forward reference to avoid circular import
    _circuit_breakers: dict[UUID, ModelCircuitBreaker]  # Initialized by concrete class

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize effect execution mixin.

        MRO Initialization Contract:
            This method uses cooperative multiple inheritance via super().__init__().
            The mixing class (e.g., NodeEffect) MUST be listed BEFORE this mixin
            in the inheritance chain to ensure proper MRO resolution.

            Correct MRO order (NodeEffect inherits from NodeCoreBase):
                class NodeEffect(NodeCoreBase, MixinEffectExecution):
                    pass  # NodeCoreBase.__init__ called first via super(), then mixin

            Incorrect MRO order (will likely fail):
                class NodeEffect(MixinEffectExecution, NodeCoreBase):
                    pass  # Mixin called first, may not have container initialized

            The MRO determines __init__ call order. With correct ordering:
            1. NodeEffect.__init__ calls super().__init__()
            2. Python's MRO calls NodeCoreBase.__init__ (sets up container, node_id)
            3. NodeCoreBase.__init__ calls super().__init__()
            4. MixinEffectExecution.__init__ is called (sets up thread safety only)
            5. MixinEffectExecution calls super().__init__() (reaches object)
            6. Control returns to NodeEffect.__init__ which initializes _circuit_breakers

            This ensures self.container and self.node_id exist before mixin methods
            are called. IMPORTANT: _circuit_breakers is NOT initialized by this mixin;
            the concrete class (NodeEffect) is responsible for initializing it after
            super().__init__() completes.

        Thread Safety:
            _circuit_breakers (initialized by concrete class) is instance-local state
            and NOT thread-safe. Each NodeEffect instance with this mixin should be
            used from a single thread or with explicit synchronization.

            Debug Mode Thread Safety Validation:
                When ONEX_DEBUG_THREAD_SAFETY=1 is set, runtime checks validate
                that this instance is only accessed from the creating thread.
                This helps catch threading violations during development with
                zero overhead in production (just a None check when disabled).

        Args:
            **kwargs: Passed to super().__init__() for cooperative MRO.
        """
        # Call super().__init__() FIRST to complete all base class initialization.
        # This ensures container and node_id are available on self.
        super().__init__(**kwargs)

        # NOTE: _circuit_breakers is NOT initialized here.
        # The concrete class (NodeEffect) is responsible for initializing _circuit_breakers
        # after all super().__init__() calls complete. This mixin provides methods that
        # operate on _circuit_breakers but does NOT own its initialization.
        # See NodeEffect.__init__ for the actual initialization.

        # Thread safety debugging (zero overhead when disabled).
        # When DEBUG_THREAD_SAFETY is enabled, we record the creating thread's ID
        # and validate access is only from that thread in key methods.
        # When disabled, _owner_thread_id is None and checks are skipped.
        if DEBUG_THREAD_SAFETY:
            self._owner_thread_id: int | None = threading.get_ident()
        else:
            self._owner_thread_id = None

    def _check_thread_safety(self) -> None:
        """
        Validate we're on the same thread that created this instance.

        Only active when ONEX_DEBUG_THREAD_SAFETY=1 environment variable is set.
        Has zero overhead in production (when disabled) - just a None check.

        This method is called at entry points of key public methods to detect
        threading violations early during development. It helps identify issues
        where NodeEffect instances are incorrectly shared across threads.

        Raises:
            ModelOnexError: If called from a different thread than the creator.
                The error includes both thread IDs and the node_id for debugging.

        Example:
            When ONEX_DEBUG_THREAD_SAFETY=1:
            >>> node = NodeEffect(container)  # Created on thread 123
            >>> # Later, on thread 456...
            >>> await node.execute_effect(input_data)  # Raises ModelOnexError

        See Also:
            - docs/guides/THREADING.md for thread safety guidelines
            - DEBUG_THREAD_SAFETY constant in constants_effect.py
        """
        if self._owner_thread_id is not None:
            current_thread = threading.get_ident()
            if current_thread != self._owner_thread_id:
                raise ModelOnexError(
                    message="Thread safety violation: node instance accessed from different thread",
                    error_code=EnumCoreErrorCode.THREAD_SAFETY_VIOLATION,
                    context={
                        "owner_thread": self._owner_thread_id,
                        "current_thread": current_thread,
                        "node_id": (
                            str(self.node_id) if hasattr(self, "node_id") else None
                        ),
                    },
                )

    @allow_dict_any
    async def execute_effect(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Execute effect operation with full resilience patterns.

        This is the main entry point for contract-driven effect execution.
        It orchestrates sequential operations with abort-on-first-failure
        semantics, retry policies, circuit breakers, and transaction management.

        Operation Source Priority (IMPORTANT - Contract Binding):
            Operations can be provided via two mechanisms, checked in priority order:

            1. **effect_subcontract key** (PREFERRED): Pass the full effect_subcontract
               object in operation_data["effect_subcontract"]. The mixin extracts
               operations automatically, preserving response_handling, retry_policy,
               and circuit_breaker configs from each operation.

                # Preferred pattern - pass subcontract directly:
                effect_subcontract = self.get_effect_subcontract()
                input_data.operation_data["effect_subcontract"] = effect_subcontract
                result = await self.execute_effect(input_data)

            2. **operations key** (ALTERNATIVE): Direct operations list in
               operation_data["operations"]. Use when manual control over
               operation serialization is needed.

                # Alternative pattern - manual operation list:
                input_data.operation_data["operations"] = [
                    {
                        "io_config": op.io_config.model_dump(),
                        "operation_timeout_ms": op.operation_timeout_ms,
                    }
                    for op in effect_subcontract.operations
                ]
                result = await self.execute_effect(input_data)

            This design separates the MIXIN (execution logic) from the NODE (contract
            binding). The mixin handles operation extraction from either source,
            while the node controls which source to use.

            Expected operation_data structure (with effect_subcontract):
                {
                    "effect_subcontract": ModelEffectSubcontract(...),  # Preferred
                    ... # Additional context for template resolution
                }

            Expected operation_data structure (with operations list):
                {
                    "operations": [
                        {
                            "io_config": {
                                "handler_type": "http",
                                "url_template": "...",
                                ...
                            },
                            "operation_timeout_ms": TIMEOUT_DEFAULT_MS,
                            "response_handling": {...},  # Optional
                            "retry_policy": {...},       # Optional
                            "circuit_breaker": {...}     # Optional
                        }
                    ],
                    ... # Additional context for template resolution
                }

        Thread Safety:
            Not thread-safe due to circuit breaker state. Use from single
            thread or with explicit synchronization.

        Args:
            input_data: Effect input containing operation configuration. Operations
                can be provided via operation_data["effect_subcontract"] (preferred)
                or operation_data["operations"] (alternative). Also includes retry policies,
                circuit breaker settings, and transaction configuration.

        Returns:
            ModelEffectOutput containing operation result, transaction state,
            timing metrics, and execution metadata.

        Raises:
            ModelOnexError: On validation errors, handler failures, or
                configuration issues. All errors are structured with proper
                error codes and context.

        Example:
            >>> # Preferred: Pass effect_subcontract directly
            >>> input_data = ModelEffectInput(
            ...     effect_type=EnumEffectType.API_CALL,
            ...     operation_data={
            ...         "effect_subcontract": effect_subcontract,  # Extracted automatically
            ...     },
            ...     retry_enabled=True,
            ...     max_retries=3,
            ... )
            >>> result = await self.execute_effect(input_data)
            >>> print(f"Success: {result.transaction_state}")
        """
        # Thread safety check (zero overhead when disabled)
        self._check_thread_safety()

        start_time = time.time()
        operation_id = input_data.operation_id

        # Extract operation configuration from input_data.operation_data
        # Priority order for operations:
        # 1. "effect_subcontract" key - if present, extract operations from subcontract
        # 2. "operations" key - direct operations list (alternative pattern)
        #
        # The subcontract pattern is preferred when the caller provides the full
        # subcontract object, allowing this mixin to extract operations directly.
        # For v1.0, we expect a single operation configuration.
        operations_config: list[ModelEffectOperationConfig] = []

        # Normalize operation_data to dict for key access
        operation_data_dict = self._normalize_operation_data(input_data.operation_data)

        # Check for subcontract first (preferred pattern)
        effect_subcontract = operation_data_dict.get("effect_subcontract")
        if effect_subcontract is not None:
            # Subcontract can be a dict (serialized) or object with .operations attribute
            if isinstance(effect_subcontract, dict):
                subcontract_ops = effect_subcontract.get("operations", [])
            elif hasattr(effect_subcontract, "operations"):
                subcontract_ops = effect_subcontract.operations
            else:
                subcontract_ops = []

            # Transform subcontract operations to ModelEffectOperationConfig
            # This preserves all operation-level configs including response_handling,
            # retry_policy, and circuit_breaker for use by handlers and execution.
            #
            # PERFORMANCE OPTIMIZATION (PR #240):
            # - Use from_effect_operation() for ModelEffectOperation to avoid model_dump()
            # - Pass typed models directly instead of serializing to dict
            for op in subcontract_ops:
                if isinstance(op, ModelEffectOperationConfig):
                    operations_config.append(op)
                elif isinstance(op, dict):
                    operations_config.append(ModelEffectOperationConfig.from_dict(op))
                elif isinstance(op, ModelEffectOperation):
                    # OPTIMIZED: Use factory method that passes typed models directly
                    # This avoids expensive model_dump() serialization
                    operations_config.append(
                        ModelEffectOperationConfig.from_effect_operation(op)
                    )
                elif hasattr(op, "io_config"):
                    # OPTIMIZED: Pass typed models directly to ModelEffectOperationConfig
                    # instead of serializing each field with model_dump()
                    # ModelEffectOperationConfig accepts both typed models and dicts
                    operations_config.append(
                        ModelEffectOperationConfig(
                            io_config=op.io_config,
                            operation_name=getattr(op, "operation_name", "unknown"),
                            description=getattr(op, "description", None),
                            operation_timeout_ms=getattr(
                                op, "operation_timeout_ms", None
                            ),
                            response_handling=getattr(op, "response_handling", None),
                            retry_policy=getattr(op, "retry_policy", None),
                            circuit_breaker=getattr(op, "circuit_breaker", None),
                            correlation_id=getattr(op, "correlation_id", None),
                            idempotent=getattr(op, "idempotent", None),
                        )
                    )
                elif hasattr(op, "model_dump"):
                    # Fallback for other Pydantic models - serialize to dict
                    # This path should rarely be hit since ModelEffectOperation
                    # is the primary Pydantic model used for operations
                    operations_config.append(
                        ModelEffectOperationConfig.from_dict(op.model_dump())
                    )

        # Fallback to direct operations list if subcontract not provided
        # PERFORMANCE OPTIMIZATION (PR #240): Use isinstance checks before model_dump fallback
        if not operations_config:
            raw_operations = operation_data_dict.get("operations", [])
            for raw_op in raw_operations:
                if isinstance(raw_op, ModelEffectOperationConfig):
                    operations_config.append(raw_op)
                elif isinstance(raw_op, dict):
                    operations_config.append(
                        ModelEffectOperationConfig.from_dict(raw_op)
                    )
                elif isinstance(raw_op, ModelEffectOperation):
                    # OPTIMIZED: Use factory method to avoid model_dump()
                    operations_config.append(
                        ModelEffectOperationConfig.from_effect_operation(raw_op)
                    )
                elif hasattr(raw_op, "model_dump"):
                    # Fallback for other Pydantic models
                    operations_config.append(
                        ModelEffectOperationConfig.from_dict(raw_op.model_dump())
                    )

        if not operations_config:
            raise ModelOnexError(
                message="No operations defined in effect input",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                context={"operation_id": str(operation_id)},
            )

        # v1.0: Only single operation execution is supported
        # If multiple operations are provided, raise an error rather than silently ignoring them
        if len(operations_config) > 1:
            raise ModelOnexError(
                message=f"v1.0 supports single operation only, but {len(operations_config)} "
                f"operations were provided. Use separate effect invocations for each operation "
                f"or upgrade to v2.0 for multi-operation support.",
                error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                context={
                    "operation_id": str(operation_id),
                    "operations_count": len(operations_config),
                },
            )

        # Sequential execution with abort-on-first-failure (v1.0)
        retry_count = 0
        # EffectResultType centralizes the type alias to avoid primitive soup unions.
        # Effect operations can return various types depending on handler.
        # See omnibase_core.types.type_effect_result for the type definition.
        final_result: EffectResultType = {}
        transaction_state = EnumTransactionState.PENDING

        try:
            # Execute first operation (v1.0: single operation only)
            operation_config = operations_config[0]

            # Parse operation configuration
            io_config = self._parse_io_config(operation_config)
            # Use default operation timeout from constants if not specified.
            # DEFAULT_OPERATION_TIMEOUT_MS (30s) matches resolved context timeout
            # defaults for consistency. Individual IO configs may specify their own
            # timeout_ms values.
            operation_timeout_ms = (
                operation_config.operation_timeout_ms or DEFAULT_OPERATION_TIMEOUT_MS
            )

            # Resolve IO context from templates
            resolved_context = self._resolve_io_context(io_config, input_data)

            # Execute operation with retry and circuit breaker
            # Pass operation_config for access to response_handling, retry_policy, etc.
            result, retry_count = await self._execute_with_retry(
                resolved_context,
                input_data,
                operation_timeout_ms,
                operation_config=operation_config,
            )

            final_result = result
            transaction_state = EnumTransactionState.COMMITTED

        except ModelOnexError:
            transaction_state = EnumTransactionState.ROLLED_BACK
            raise
        except Exception as e:  # fallback-ok: top-level error boundary wraps non-ModelOnexError into structured error
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit/CancelledError to propagate
            transaction_state = EnumTransactionState.ROLLED_BACK
            raise ModelOnexError(
                message=f"Effect execution failed: {e!s}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"operation_id": str(operation_id)},
            ) from e
        finally:
            processing_time_ms = (time.time() - start_time) * 1000

        return ModelEffectOutput(
            result=final_result,
            operation_id=operation_id,
            effect_type=input_data.effect_type,
            transaction_state=transaction_state,
            processing_time_ms=processing_time_ms,
            retry_count=retry_count,
            metadata=input_data.metadata,
        )

    def _parse_io_config(
        self, operation_config: ModelEffectOperationConfig
    ) -> EffectIOConfig:
        """
        Get typed IO config from operation configuration.

        Since ModelEffectOperationConfig.io_config is a discriminated union
        (EffectIOConfig), it's always already typed. This method simply returns it.

        Args:
            operation_config: Typed operation configuration.

        Returns:
            Typed EffectIOConfig (discriminated union).
        """
        # io_config is always typed via discriminated union - just return it
        return operation_config.io_config

    def _resolve_io_context(
        self,
        io_config: EffectIOConfig,
        input_data: ModelEffectInput,
    ) -> ResolvedIOContext:
        """
        Resolve template placeholders in IO config to concrete values.

        Template Resolution:
            - ${input.field} - from input_data.operation_data
            - ${env.VAR} - from os.environ
            - ${secret.KEY} - from container secret service (if available)

        v1.0 Behavior:
            Resolution happens ONCE before the retry loop for efficiency.
            The resolved context is cached and reused across retry attempts.
            This is intentional - see PERFORMANCE NOTE in _execute_with_retry().

        Thread Safety:
            Pure function, thread-safe. Environment variable access is
            inherently racy but this is expected behavior.

        Note:
            In v1.0, this method is called ONCE before the retry loop begins.
            The resolved values are cached and reused across retry attempts.
            See PERFORMANCE NOTE in _execute_with_retry() for future optimization
            opportunities to support per-retry re-resolution when needed.

        Args:
            io_config: Handler-specific IO configuration with template placeholders.
            input_data: Effect input containing operation data for substitution.

        Returns:
            Fully resolved IO context ready for handler execution.

        Raises:
            ModelOnexError: On template resolution failures or missing values.
        """
        # Resolution context - normalize operation_data to dict for field extraction
        context_data = self._normalize_operation_data(input_data.operation_data)

        def resolve_template(match: re.Match[str]) -> str:
            """Resolve a single ${...} placeholder."""
            placeholder = match.group(1)

            if placeholder.startswith("input."):
                # Extract from input_data.operation_data
                field_path = placeholder[6:]  # Remove "input."
                value = self._extract_field(context_data, field_path)
                return str(value) if value is not None else ""

            elif placeholder.startswith("env."):
                # Extract from environment
                var_name = placeholder[4:]  # Remove "env."
                value = os.environ.get(var_name)
                if value is None:
                    raise ModelOnexError(
                        message=f"Environment variable not found: {var_name}",
                        error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                        context={
                            "variable_name": var_name,
                            "placeholder": placeholder,
                            "operation_id": str(input_data.operation_id),
                        },
                    )
                return value

            elif placeholder.startswith("secret."):
                # Extract from secret service (if available)
                secret_key = placeholder[7:]  # Remove "secret."
                try:
                    # String-based DI lookup for extensibility; protocol not defined in core
                    secret_service: object = self.container.get_service(
                        "ProtocolSecretService"  # type: ignore[arg-type]
                    )  # String-based DI lookup for extensibility
                    # Runtime guard for duck-typed method call
                    if not hasattr(secret_service, "get_secret"):
                        raise ModelOnexError(
                            message="Secret service does not implement get_secret method. "
                            "Ensure ProtocolSecretService implementation provides get_secret(key: str) -> str | None.",
                            error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                            context={
                                "secret_key": secret_key,
                                "placeholder": placeholder,
                                "operation_id": str(input_data.operation_id),
                                "service_type": type(secret_service).__name__,
                            },
                        )
                    # Duck-typed method call; actual service implements get_secret at runtime
                    secret_value = secret_service.get_secret(
                        secret_key
                    )  # Duck-typed protocol method
                    if secret_value is None:
                        raise ModelOnexError(
                            message=f"Secret not found: {secret_key}",
                            error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                            context={
                                "secret_key": secret_key,
                                "placeholder": placeholder,
                                "operation_id": str(input_data.operation_id),
                            },
                        )
                    return str(secret_value)
                except ModelOnexError:
                    raise
                except (
                    AttributeError,
                    KeyError,
                    OSError,
                    RuntimeError,
                    ValueError,
                ) as e:
                    raise ModelOnexError(
                        message=f"Failed to resolve secret: {secret_key}",
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                        context={
                            "secret_key": secret_key,
                            "placeholder": placeholder,
                            "operation_id": str(input_data.operation_id),
                            "error_type": type(e).__name__,
                        },
                    ) from e

            else:
                raise ModelOnexError(
                    message=f"Unknown template prefix: {placeholder}",
                    error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                    context={
                        "placeholder": placeholder,
                        "supported_prefixes": ["input.", "env.", "secret."],
                        "operation_id": str(input_data.operation_id),
                    },
                )

        # Resolve based on handler type
        # NOTE: isinstance checks are required here (not duck typing) because io_config
        # is a Pydantic discriminated union (EffectIOConfig). Type narrowing via isinstance
        # allows proper access to model-specific attributes and mypy type checking.
        if isinstance(io_config, ModelHttpIOConfig):
            return ModelResolvedHttpContext(
                url=TEMPLATE_PATTERN.sub(resolve_template, io_config.url_template),
                method=io_config.method,
                headers={
                    k: TEMPLATE_PATTERN.sub(resolve_template, v)
                    for k, v in io_config.headers.items()
                },
                body=(
                    TEMPLATE_PATTERN.sub(resolve_template, io_config.body_template)
                    if io_config.body_template
                    else None
                ),
                query_params={
                    k: TEMPLATE_PATTERN.sub(resolve_template, v)
                    for k, v in io_config.query_params.items()
                },
                timeout_ms=io_config.timeout_ms,
                follow_redirects=io_config.follow_redirects,
                verify_ssl=io_config.verify_ssl,
            )

        elif isinstance(io_config, ModelDbIOConfig):
            # Resolve query template
            resolved_query = TEMPLATE_PATTERN.sub(
                resolve_template, io_config.query_template
            )

            # Resolve query params
            resolved_params: list[DbParamType] = []
            for param_template in io_config.query_params:
                resolved = TEMPLATE_PATTERN.sub(resolve_template, param_template)
                # Try to coerce to appropriate type
                resolved_params.append(self._coerce_param_value(resolved))

            return ModelResolvedDbContext(
                operation=io_config.operation,
                connection_name=io_config.connection_name,
                query=resolved_query,
                params=resolved_params,
                timeout_ms=io_config.timeout_ms,
                fetch_size=io_config.fetch_size,
                read_only=io_config.read_only,
            )

        elif isinstance(io_config, ModelKafkaIOConfig):
            return ModelResolvedKafkaContext(
                topic=TEMPLATE_PATTERN.sub(resolve_template, io_config.topic),
                partition_key=(
                    TEMPLATE_PATTERN.sub(
                        resolve_template, io_config.partition_key_template
                    )
                    if io_config.partition_key_template
                    else None
                ),
                headers={
                    k: TEMPLATE_PATTERN.sub(resolve_template, v)
                    for k, v in io_config.headers.items()
                },
                payload=TEMPLATE_PATTERN.sub(
                    resolve_template, io_config.payload_template
                ),
                timeout_ms=io_config.timeout_ms,
                acks=io_config.acks,
                compression=io_config.compression,
            )

        elif isinstance(io_config, ModelFilesystemIOConfig):
            # Filesystem content resolution strategy:
            #
            # Content sources (checked in priority order for write operations):
            # 1. "file_content" key in operation_data (preferred, for explicit content)
            # 2. "content" key in operation_data (alternative key)
            # 3. "content_template" key in operation_data (for templated content)
            # 4. None - content may be provided by handler (e.g., from stream/file)
            #
            # This design separates content from templates because:
            # 1. Large content bypasses template resolution overhead
            # 2. Binary content cannot be templated (use base64 encoding externally)
            # 3. Content may come from external sources (e.g., file uploads, streams)
            #
            # For read/delete/move/copy operations, content is always None as these
            # operations don't require input content.
            content: str | None = None

            if io_config.operation == "write":
                # Priority 1: Direct content from operation_data
                if "file_content" in context_data:
                    raw_content = context_data["file_content"]
                    if isinstance(raw_content, str):
                        content = raw_content
                        # Resolve templates if present
                        if TEMPLATE_PATTERN.search(content):
                            content = TEMPLATE_PATTERN.sub(resolve_template, content)
                    elif raw_content is not None:
                        # Non-string content - convert to string
                        content = str(raw_content)

                # Priority 2: Fallback to "content" key
                elif "content" in context_data:
                    raw_content = context_data["content"]
                    if isinstance(raw_content, str):
                        content = raw_content
                        # Resolve templates if present
                        if TEMPLATE_PATTERN.search(content):
                            content = TEMPLATE_PATTERN.sub(resolve_template, content)
                    elif raw_content is not None:
                        # Non-string content - convert to string
                        content = str(raw_content)

                # Priority 3: Template content key (always resolve templates)
                elif "content_template" in context_data:
                    template = context_data.get("content_template")
                    if isinstance(template, str):
                        content = TEMPLATE_PATTERN.sub(resolve_template, template)

                # If we still have no content for a write operation, raise clear error
                if content is None:
                    raise ModelOnexError(
                        message="Filesystem write operation requires content. "
                        "Provide 'file_content', 'content', or 'content_template' "
                        "in operation_data.",
                        error_code=EnumCoreErrorCode.INVALID_INPUT,
                        context={
                            "operation": io_config.operation,
                            "file_path_template": io_config.file_path_template,
                        },
                    )

            return ModelResolvedFilesystemContext(
                file_path=TEMPLATE_PATTERN.sub(
                    resolve_template, io_config.file_path_template
                ),
                operation=io_config.operation,
                content=content,
                timeout_ms=io_config.timeout_ms,
                atomic=io_config.atomic,
                create_dirs=io_config.create_dirs,
                encoding=io_config.encoding,
                mode=io_config.mode,
            )

        else:
            raise ModelOnexError(
                message=f"Unknown IO config type: {type(io_config)}",
                error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
            )

    @allow_dict_any
    def _extract_field(
        self,
        data: dict[str, Any],
        field_path: str,
        max_depth: int | None = None,
        operation_id: UUID | None = None,
    ) -> str | int | float | bool | dict[str, object] | list[object] | None:
        """
        Extract nested field from data using dotpath notation.

        Security:
            - Validates field_path characters against SAFE_FIELD_PATTERN to prevent
              injection attacks via malicious paths like __import__, eval(), etc.
            - Validates field_path segments against DENIED_BUILTINS to prevent
              access to Python built-ins and special attributes (defense-in-depth).
            - Enforces a maximum traversal depth to prevent denial-of-service
              attacks via deeply nested or maliciously crafted field paths.

            Allowed characters in field_path:
                - a-z, A-Z: Alphanumeric field names
                - 0-9: Numeric field names or array indices in path segments
                - _: Underscore for snake_case field names
                - .: Dot separator for nested field access

            Denied field names (explicit deny-list):
                - Code execution: import, __import__, eval, exec, compile
                - Introspection: globals, locals, vars, dir
                - Attribute manipulation: getattr, setattr, delattr, hasattr
                - Special attributes: __class__, __bases__, __builtins__, etc.
                - See DENIED_BUILTINS in constants_effect.py for full list

        Args:
            data: Source data dictionary.
            field_path: Dotted path like "user.id" or "config.timeout_ms".
                Must contain only alphanumeric characters, underscores, and dots.
                Must not contain any denied Python built-in names.
            max_depth: Maximum allowed path depth. Defaults to
                DEFAULT_MAX_FIELD_EXTRACTION_DEPTH (10). Paths deeper than
                this limit will return None.
            operation_id: Optional operation ID for error context.

        Returns:
            Extracted value or None if not found or depth limit exceeded.

        Raises:
            ModelOnexError: If field_path contains invalid characters
                (VALIDATION_ERROR code) or contains denied built-in names
                (SECURITY_VIOLATION code).
        """
        # Security: Validate field path characters to prevent injection attacks
        if not SAFE_FIELD_PATTERN.match(field_path):
            raise ModelOnexError(
                message=f"Invalid field path characters: {field_path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field_path=field_path,
                allowed_pattern="[a-zA-Z0-9_.]",
                operation_id=str(operation_id) if operation_id else None,
            )

        # Security: Check for denied Python built-ins (defense-in-depth)
        # This catches dangerous identifiers like __class__, eval, etc.
        # that pass the character pattern but could enable template injection
        denied_builtin = contains_denied_builtin(field_path)
        if denied_builtin is not None:
            raise ModelOnexError(
                message=f"Access to Python built-in or special attribute denied: {denied_builtin}",
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                field_path=field_path,
                denied_builtin=denied_builtin,
                operation_id=str(operation_id) if operation_id else None,
            )

        if max_depth is None:
            max_depth = DEFAULT_MAX_FIELD_EXTRACTION_DEPTH
        parts = field_path.split(".")

        # Enforce depth limit for security
        if len(parts) > max_depth:
            return None

        current: object = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        # Validate extracted value matches expected types for type safety
        # Return None for unexpected types (e.g., custom objects, callables)
        if isinstance(current, (str, int, float, bool, dict, list)) or current is None:
            return current  # isinstance narrows to valid union member
        return None

    def _coerce_param_value(self, value: str) -> DbParamType:
        """
        Coerce string value to appropriate type for DB parameters.

        Args:
            value: String value to coerce.

        Returns:
            Coerced value (int, float, bool, or original string).
        """
        # Try bool
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try None
        if value.lower() in ("none", "null"):
            return None

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    @allow_dict_any
    def _normalize_operation_data(
        self, operation_data: ModelEffectInputData | dict[str, Any]
    ) -> dict[str, Any]:
        """Convert operation_data to dict for template resolution.

        This method converts either form of operation_data to a dict for
        template placeholder resolution (${input.field_name} syntax).

        Design:
            - ModelEffectInputData (contract): serialized via model_dump()
            - dict (template context): used as-is, no coercion

        The result is a dict suitable for field extraction, NOT a validated
        contract. This is intentional - template contexts can have arbitrary keys.

        Args:
            operation_data: Strict contract (ModelEffectInputData) or
                template context (dict).

        Returns:
            Dict for template resolution and field extraction.
        """
        if isinstance(operation_data, dict):
            return operation_data
        return operation_data.model_dump()

    async def _execute_with_retry(
        self,
        resolved_context: ResolvedIOContext,
        input_data: ModelEffectInput,
        operation_timeout_ms: int,
        operation_config: ModelEffectOperationConfig | None = None,
    ) -> tuple[EffectResultType, int]:
        """
        Execute operation with retry logic and circuit breaker.

        Retry Policy:
            - Only retry if input_data.retry_enabled is True
            - Respect operation_timeout_ms overall timeout
            - Use exponential backoff with jitter

            NOTE on Idempotency: This method retries based on retry_enabled flag only.
            The caller (typically NodeEffect) is responsible for checking operation
            idempotency via ModelEffectOperation.get_effective_idempotency() before
            enabling retries. Non-idempotent operations (e.g., HTTP POST, DB INSERT)
            should typically have retry_enabled=False to prevent duplicate side effects.

        Circuit Breaker:
            - Check state before each attempt
            - Record success/failure after each attempt
            - Fast-fail if circuit is open

        Retry Count Semantic:
            The returned retry_count represents the number of FAILED ATTEMPTS
            before success or final failure. Specifically:
            - If operation succeeds on first try: retry_count = 0
            - If operation fails once, succeeds on retry: retry_count = 1
            - If operation fails all attempts: retry_count = max_retries + 1

            This semantic counts "how many times did we fail" rather than
            "how many retries did we perform", which is useful for metrics
            and debugging to understand the reliability of the operation.

        Thread Safety:
            Not thread-safe due to circuit breaker state access.

        PERFORMANCE NOTE: Template Resolution Strategy
        ==============================================
        Currently, template resolution happens ONCE before the retry loop
        (in execute_effect calling _resolve_io_context). This is efficient
        for most use cases but means retry attempts use cached resolved values.

        This design is intentional for v1.0:
        - Avoids redundant template parsing on each retry
        - Environment variables and secrets are resolved at operation start
        - Consistent behavior across all retry attempts

        FUTURE OPTIMIZATION OPPORTUNITY:
        For scenarios requiring fresh values on each retry (e.g., rotating
        secrets, dynamic environment), consider these enhancements:

        1. Template AST caching - Parse template structure once, evaluate
           variable substitutions on each retry without re-parsing
        2. Selective re-resolution - Only re-resolve ${secret.*} and ${env.*}
           templates on retry, cache ${input.*} values
        3. Static template detection - Skip re-resolution entirely for
           templates without ${...} placeholders (already partially
           implemented via TEMPLATE_PATTERN.search() checks)
        4. Lazy resolution - Resolve templates at first use within handler,
           enabling per-attempt freshness with minimal overhead

        For high-throughput scenarios (>1000 ops/sec), profiling shows
        template resolution accounts for ~5-15% of total operation time.
        The above optimizations could reduce this to <2% while preserving
        the option for fresh values when needed.

        See: docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md

        Args:
            resolved_context: Fully resolved IO context.
            input_data: Effect input with retry configuration.
            operation_timeout_ms: Overall operation timeout including all retries.
            operation_config: Optional typed operation configuration containing
                response_handling, retry_policy, circuit_breaker, and other
                per-operation settings. NOTE: In v1.0, per-operation retry_policy
                and circuit_breaker configs are serialized but NOT YET wired to
                the retry loop - only input_data.retry_enabled, input_data.max_retries,
                and input_data.circuit_breaker_enabled are honored. The operation_config
                is passed through to _execute_operation for handler access to
                response_handling and other metadata.

        Returns:
            Tuple of (result, retry_count) where retry_count is the number of
            failed attempts before success (0 if succeeded on first try).

        Raises:
            ModelOnexError: On operation failure or timeout.
        """
        # PERFORMANCE NOTE: Template Resolution in Retry Loop
        # ====================================================
        # Templates are resolved ONCE before this loop (in execute_effect).
        # This is intentional for v1.0 - see docstring PERFORMANCE NOTE above.
        #
        # For future re-resolution on retry:
        # 1. Move _resolve_io_context call inside loop
        # 2. Add caching layer for static templates
        # 3. Pass io_config instead of resolved_context
        #
        # Current trade-offs:
        # + Lower overhead per retry (no re-parsing)
        # + Consistent values across attempts
        # - Stale secrets if rotated during retries
        # - No dynamic environment variable refresh

        operation_id = input_data.operation_id
        max_retries = input_data.max_retries if input_data.retry_enabled else 0
        retry_delay_ms = input_data.retry_delay_ms

        start_time = time.time()
        retry_count = 0

        for attempt in range(max_retries + 1):
            # Check overall timeout
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= operation_timeout_ms:
                raise ModelOnexError(
                    message=f"Operation timeout after {elapsed_ms:.0f}ms",
                    error_code=EnumCoreErrorCode.TIMEOUT_EXCEEDED,
                    context={
                        "operation_id": str(operation_id),
                        "timeout_ms": operation_timeout_ms,
                        "attempts": attempt,
                    },
                )

            # Check circuit breaker (if enabled)
            if input_data.circuit_breaker_enabled:
                if not self._check_circuit_breaker(operation_id):
                    raise ModelOnexError(
                        message="Circuit breaker is open",
                        error_code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                        context={"operation_id": str(operation_id)},
                    )

            try:
                # Execute operation with operation_config for response_handling access
                result = await self._execute_operation(
                    resolved_context, input_data, operation_config
                )

                # Record success in circuit breaker
                if input_data.circuit_breaker_enabled:
                    self._record_circuit_breaker_result(operation_id, success=True)

                return result, retry_count

            except Exception as e:  # catch-all-ok: retry loop catches operation failures; KeyboardInterrupt/SystemExit propagate
                # Increment retry_count to track failed attempts
                # retry_count represents "number of failed attempts before success or final failure"
                # - First attempt fails: retry_count becomes 1
                # - Second attempt (first retry) fails: retry_count becomes 2
                # - etc.
                retry_count += 1

                # Record failure in circuit breaker
                if input_data.circuit_breaker_enabled:
                    self._record_circuit_breaker_result(operation_id, success=False)

                # Check if we should retry
                # attempt is 0-indexed, so attempt < max_retries means we have retries left
                if attempt < max_retries and input_data.retry_enabled:
                    # Exponential backoff with symmetric jitter
                    # Uses random.uniform() for proper randomness to prevent retry storms
                    # when multiple clients retry simultaneously (thundering herd problem).
                    # Jitter applies +/- jitter_factor * delay (e.g., +/-10% for 0.1 factor).
                    # Symmetric jitter provides better distribution than additive-only,
                    # reducing correlation between concurrent retry attempts.
                    delay_ms = retry_delay_ms * (2**attempt)
                    jitter = delay_ms * DEFAULT_RETRY_JITTER_FACTOR
                    actual_delay_ms = delay_ms + random.uniform(-jitter, jitter)

                    # Wait before retry
                    await asyncio.sleep(actual_delay_ms / 1000)
                elif isinstance(e, ModelOnexError):
                    # No more retries, raise the original error
                    raise
                else:
                    # No more retries, wrap and raise
                    # retry_count is total failed attempts (initial attempt + retries)
                    # attempt is 0-indexed, so actual retries performed = attempt
                    raise ModelOnexError(
                        message=f"Operation failed after {retry_count} attempt(s) "
                        f"({attempt} retry/retries)",
                        error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        context={
                            "operation_id": str(operation_id),
                            "failed_attempts": retry_count,
                            "retries_performed": attempt,
                            "max_retries": max_retries,
                        },
                    ) from e

        # Should never reach here, but for type checking
        raise ModelOnexError(
            message="Operation failed",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )

    async def _execute_operation(
        self,
        resolved_context: ResolvedIOContext,
        input_data: ModelEffectInput,
        operation_config: ModelEffectOperationConfig | None = None,
    ) -> EffectResultType:
        """
        Execute single operation by dispatching to appropriate handler.

        Handler Dispatch:
            - Handlers are resolved via container.get_service() using protocol naming
            - Protocol names follow pattern: "ProtocolEffectHandler_{TYPE}" where TYPE
              is the uppercase handler type (HTTP, DB, KAFKA, FILESYSTEM)
            - Handlers receive fully-resolved context (no template placeholders)
            - Handlers return raw result (dict, list, string, etc.)

        Handler Registration (IMPORTANT - Extensibility Point):
            This mixin expects handlers to be registered in the container by the
            implementing application. The handler protocols are NOT defined in
            omnibase_core itself - they are an extensibility point.

            To use this mixin, the implementing application MUST:
            1. Define handler protocols (e.g., ProtocolEffectHandler_HTTP)
            2. Implement handler classes that satisfy those protocols
            3. Register handlers in the container before effect execution

            Example registration in application code:
                container.register_service(
                    "ProtocolEffectHandler_HTTP",
                    HttpEffectHandler()
                )

            Handler Protocol Contract:
                async def execute(context: ResolvedIOContext) -> object

            If no handler is registered for a handler type, a ModelOnexError will
            be raised with HANDLER_EXECUTION_ERROR code.

        Response Handling (Caller-Owned Utility - Not Auto-Applied):
            The operation_config may contain response_handling with:
            - success_codes: HTTP status codes considered successful (e.g., [200, 201])
            - extract_fields: Map of output_name to JSONPath/dotpath expression
            - fail_on_empty: Whether to fail if extraction returns empty/null
            - extraction_engine: "jsonpath" or "dotpath"

            IMPORTANT: response_handling is NOT automatically applied by this method or
            by handlers. Handlers only receive the resolved_context (fully resolved IO
            parameters) and return raw responses. This is by design:

            1. Handlers are kept simple - they only execute I/O operations
            2. Response processing is CALLER responsibility (NodeEffect.process())
            3. Field extraction via _extract_response_fields() is a UTILITY method
               available to callers but NOT automatically invoked

            The intended flow is:
            1. Handler executes operation with resolved_context -> returns raw response
            2. This method returns the raw response to execute_effect()
            3. Caller (e.g., NodeEffect.process) may optionally use
               _extract_response_fields() on the response for field extraction
            4. Caller applies response_handling.success_codes validation if needed

            This separation keeps handlers focused on I/O while giving callers full
            control over response interpretation and field extraction. The utility
            method exists for convenience but callers must explicitly invoke it.

        Thread Safety:
            Thread-safe if handlers are thread-safe. Handlers should be
            stateless or use their own synchronization.

        Args:
            resolved_context: Fully resolved IO context.
            input_data: Effect input with operation metadata.
            operation_config: Optional typed operation configuration containing
                response_handling, retry_policy, circuit_breaker, and other
                per-operation settings. NOTE: This config is NOT passed to handlers
                and response_handling is NOT automatically applied. The config is
                available for caller-side response processing after handler returns.
                Handlers only receive resolved_context. See "Response Handling"
                section above for the intended usage pattern.

        Returns:
            Operation result (type depends on handler). This is the RAW response
            from the handler - no field extraction or response_handling processing
            is applied.

        Raises:
            ModelOnexError: On handler execution failure or if handler protocol
                is not registered in the container.
        """
        # Resolve handler from container based on handler_type
        # NOTE: Handler protocols (e.g., ProtocolEffectHandler_HTTP) are NOT defined
        # in omnibase_core. They are an extensibility point - implementing applications
        # must register their own handlers. See docstring for registration details.
        handler_type = resolved_context.handler_type
        handler_protocol = f"ProtocolEffectHandler_{handler_type.value.upper()}"

        # Attempt to resolve handler with explicit error for missing registration
        try:
            # String-based DI lookup for extensibility; handler protocols not defined in core
            handler: object = self.container.get_service(handler_protocol)  # type: ignore[arg-type]  # String-based DI lookup for extensibility
        except (
            AttributeError,
            KeyError,
            LookupError,
            RuntimeError,
            ValueError,
        ) as resolve_error:
            # Provide explicit guidance for handler registration
            raise ModelOnexError(
                message=f"Effect handler not registered: {handler_protocol}. "
                f"Handler protocols are an extensibility point - implementing applications "
                f"must register handlers via container.register_service('{handler_protocol}', handler_instance). "
                f"See MixinEffectExecution._execute_operation docstring for details.",
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                context={
                    "operation_id": str(input_data.operation_id),
                    "handler_type": handler_type.value,
                    "handler_protocol": handler_protocol,
                    "resolution_error": str(resolve_error),
                },
            ) from resolve_error

        # Execute handler with resolved context
        try:
            # Runtime guard for duck-typed handler execution
            if not hasattr(handler, "execute"):
                raise ModelOnexError(
                    message=f"Effect handler {handler_protocol} does not implement execute method. "
                    f"Handler implementations must provide async execute(context: ResolvedIOContext) -> object.",
                    error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                    context={
                        "operation_id": str(input_data.operation_id),
                        "handler_type": handler_type.value,
                        "handler_protocol": handler_protocol,
                        "handler_class": type(handler).__name__,
                    },
                )
            # Duck-typed handler execution; handler implements execute() per protocol contract
            result = await handler.execute(
                resolved_context
            )  # Duck-typed protocol method
        except ModelOnexError:
            raise
        except (
            Exception
        ) as exec_error:  # fallback-ok: handler errors wrapped in ModelOnexError
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit/CancelledError to propagate
            raise ModelOnexError(
                message=f"Handler execution failed for {handler_protocol}: {exec_error!s}",
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                context={
                    "operation_id": str(input_data.operation_id),
                    "handler_type": handler_type.value,
                },
            ) from exec_error

        # Handler returns Any, validate it matches expected return type
        if isinstance(result, (str, int, float, bool, dict, list)):
            # Validated via isinstance check; cast to EffectResultType
            return cast(EffectResultType, result)
        if result is None:
            # None not in EffectResultType, convert to empty dict
            return {}
        # Convert other types to string representation
        return str(result)

    def _check_circuit_breaker(self, operation_id: UUID) -> bool:
        """
        Check circuit breaker state before operation execution.

        Thread Safety:
            Not thread-safe. Caller must ensure exclusive access to
            _circuit_breakers dict.

        Args:
            operation_id: Operation identifier (used as circuit breaker key).

        Returns:
            True if operation should proceed, False if circuit is open.
        """
        circuit_breaker = self._circuit_breakers.get(operation_id)

        if circuit_breaker is None:
            # Initialize circuit breaker for this operation
            circuit_breaker = ModelCircuitBreaker.create_resilient()
            self._circuit_breakers[operation_id] = circuit_breaker

        # Check if request should be allowed
        return circuit_breaker.should_allow_request()

    def _record_circuit_breaker_result(self, operation_id: UUID, success: bool) -> None:
        """
        Record operation result in circuit breaker.

        Thread Safety:
            Not thread-safe. Caller must ensure exclusive access to
            _circuit_breakers dict.

        Args:
            operation_id: Operation identifier (used as circuit breaker key).
            success: Whether the operation succeeded.
        """
        circuit_breaker = self._circuit_breakers.get(operation_id)

        if circuit_breaker is None:
            # Should not happen, but handle gracefully
            circuit_breaker = ModelCircuitBreaker.create_resilient()
            self._circuit_breakers[operation_id] = circuit_breaker

        # Record result
        if success:
            circuit_breaker.record_success()
        else:
            circuit_breaker.record_failure()

    @allow_dict_any
    def _extract_response_fields(
        self,
        response: dict[str, Any],
        response_handling: dict[str, Any],
    ) -> dict[str, DbParamType]:
        """
        Extract fields from response using JSONPath or dotpath.

        This is a CALLER UTILITY method - intended for use by NodeEffect.process()
        or other code that calls execute_effect(), NOT by effect handlers themselves.

        Usage Pattern:
            # In NodeEffect.process() after execute_effect() returns:
            result = await self.execute_effect(input_data)
            if result.result and isinstance(result.result, dict):
                extracted = self._extract_response_fields(
                    result.result,
                    operation_config.get("response_handling", {})
                )

        Design Rationale:
            1. Handlers only execute I/O and return raw responses
            2. Response interpretation is CALLER responsibility
            3. Not all responses need field extraction (some are pass-through)
            4. Callers have access to operation_config with response_handling

        This method is NOT automatically called during effect execution. The
        caller must explicitly invoke it after receiving the handler response.

        Extraction Engines:
            - jsonpath: Full JSONPath syntax (requires jsonpath-ng)
            - dotpath: Simple $.field.subfield syntax (no dependencies)

        Both engines reject non-primitive extraction results. Only
        str, int, float, bool, and None are allowed.

        Thread Safety:
            Pure function, thread-safe.

        Args:
            response: Response data to extract from.
            response_handling: Response handling configuration with
                extraction_engine and extract_fields mapping.

        Returns:
            Dictionary of extracted field values.

        Raises:
            ModelOnexError: On extraction failure or invalid configuration.
        """
        extraction_engine = response_handling.get("extraction_engine", "jsonpath")
        extract_fields = response_handling.get("extract_fields", {})

        if not extract_fields:
            return {}

        extracted: dict[str, DbParamType] = {}

        for output_name, path_expr in extract_fields.items():
            try:
                if extraction_engine == "jsonpath":
                    # Use jsonpath-ng for extraction
                    try:
                        from jsonpath_ng import parse
                    except ImportError as e:
                        raise ModelOnexError(
                            message="jsonpath-ng package required for jsonpath extraction",
                            error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                        ) from e

                    jsonpath_expr = parse(path_expr)
                    matches = [match.value for match in jsonpath_expr.find(response)]

                    if not matches:
                        if response_handling.get("fail_on_empty", False):
                            raise ModelOnexError(
                                message=f"No matches found for path: {path_expr}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            )
                        value = None
                    else:
                        value = matches[0]  # Take first match

                elif extraction_engine == "dotpath":
                    # Simple dotpath extraction
                    value = self._extract_field(response, path_expr.lstrip("$."))

                    if value is None and response_handling.get("fail_on_empty", False):
                        raise ModelOnexError(
                            message=f"No value found for path: {path_expr}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        )

                else:
                    raise ModelOnexError(
                        message=f"Unknown extraction engine: {extraction_engine}",
                        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                    )

                # Validate primitive type
                if value is not None and not isinstance(
                    value, (str, int, float, bool, type(None))
                ):
                    raise ModelOnexError(
                        message=f"Extracted value must be primitive, got {type(value)}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )

                extracted[output_name] = value

            except ModelOnexError:
                raise
            except PYDANTIC_MODEL_ERRORS as e:
                raise ModelOnexError(
                    message=f"Field extraction failed for {output_name}: {e!s}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                ) from e
            except (
                Exception
            ) as e:  # catch-all-ok: extraction utility must not leak raw exceptions
                raise ModelOnexError(
                    message=f"Field extraction failed for {output_name}: {e!s}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                ) from e

        return extracted

    def get_registered_handlers(self) -> dict[str, bool]:
        """
        Get registration status of all known effect handler protocols.

        This debugging utility helps diagnose handler registration issues by
        checking which handlers are available in the container. Use this method
        when effects fail with "handler not registered" errors.

        Handler Protocol Names:
            - ProtocolEffectHandler_HTTP: HTTP/REST API handler
            - ProtocolEffectHandler_DB: Database query handler
            - ProtocolEffectHandler_KAFKA: Kafka message producer handler
            - ProtocolEffectHandler_FILESYSTEM: File system operations handler

        Returns:
            Dictionary mapping handler protocol names to registration status
            (True if registered, False if not).

        Example:
            >>> handlers = node.get_registered_handlers()
            >>> print(handlers)
            {
                'ProtocolEffectHandler_HTTP': True,
                'ProtocolEffectHandler_DB': False,
                'ProtocolEffectHandler_KAFKA': True,
                'ProtocolEffectHandler_FILESYSTEM': False,
            }
            >>> # Identify missing handlers
            >>> missing = [name for name, registered in handlers.items() if not registered]
            >>> print(f"Missing handlers: {missing}")

        Note:
            This method is intended for debugging and diagnostics. In production,
            ensure all required handlers are registered during application startup.

        See Also:
            - _execute_operation() for handler dispatch logic
            - MixinEffectExecution docstring for handler registration examples
        """
        handler_protocols = [
            "ProtocolEffectHandler_HTTP",
            "ProtocolEffectHandler_DB",
            "ProtocolEffectHandler_KAFKA",
            "ProtocolEffectHandler_FILESYSTEM",
        ]

        registration_status: dict[str, bool] = {}

        for protocol_name in handler_protocols:
            try:
                # String-based DI lookup for extensibility check
                self.container.get_service(protocol_name)  # type: ignore[arg-type]  # String-based DI lookup for extensibility
                registration_status[protocol_name] = True
            except (
                Exception
            ):  # fallback-ok: service not found indicates unregistered handler
                registration_status[protocol_name] = False

        return registration_status

    def get_handler_registration_report(self) -> str:
        """
        Get a human-readable report of handler registration status.

        Useful for debugging and logging when diagnosing effect execution issues.
        Provides a formatted report with registration status and guidance for
        missing handlers.

        Returns:
            Multi-line string report of handler registration status.

        Example:
            >>> print(node.get_handler_registration_report())
            Effect Handler Registration Status:
              [OK] ProtocolEffectHandler_HTTP: Registered
              [MISSING] ProtocolEffectHandler_DB: Not registered
              [OK] ProtocolEffectHandler_KAFKA: Registered
              [MISSING] ProtocolEffectHandler_FILESYSTEM: Not registered

            Missing handlers must be registered before use:
              container.register_service("ProtocolEffectHandler_DB", YourDbHandler())
              container.register_service("ProtocolEffectHandler_FILESYSTEM", YourFsHandler())
        """
        handlers = self.get_registered_handlers()
        lines = ["Effect Handler Registration Status:"]

        missing_handlers: list[str] = []

        for protocol_name, registered in handlers.items():
            if registered:
                lines.append(f"  [OK] {protocol_name}: Registered")
            else:
                lines.append(f"  [MISSING] {protocol_name}: Not registered")
                missing_handlers.append(protocol_name)

        if missing_handlers:
            lines.append("")
            lines.append("Missing handlers must be registered before use:")
            for handler in missing_handlers:
                lines.append(
                    f'  container.register_service("{handler}", YourHandler())'
                )

        return "\n".join(lines)
