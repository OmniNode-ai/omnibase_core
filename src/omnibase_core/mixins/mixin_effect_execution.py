"""
Mixin for contract-driven effect execution.

This module provides a mixin class that adds contract-driven I/O execution
capabilities to NodeEffect instances. It orchestrates external interactions
(HTTP, DB, Kafka, Filesystem) with comprehensive resilience patterns including
retry policies, circuit breakers, and transaction management.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

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
    - Template resolution happens INSIDE retry loop (per spec)

Handler Contract:
    - Handlers receive fully-resolved context (ModelResolvedIOContext)
    - Handlers NEVER perform template resolution
    - Handlers are protocol-based and registered via container

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
import re
import time
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
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
        _circuit_breakers (dict): Internal circuit breaker state, keyed by
            operation correlation_id. Process-local only in v1.0.

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
    container: Any  # ModelONEXContainer - avoiding circular import

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize effect execution mixin.

        MRO Initialization Contract:
            This method uses cooperative multiple inheritance via super().__init__().
            The mixing class (e.g., NodeEffect) MUST be listed BEFORE this mixin
            in the inheritance chain to ensure proper MRO resolution.

            Correct MRO order:
                class MyEffectNode(NodeEffect, MixinEffectExecution):
                    pass  # NodeEffect.__init__ called first via super(), then mixin

            Incorrect MRO order (will likely fail):
                class MyEffectNode(MixinEffectExecution, NodeEffect):
                    pass  # Mixin called first, may not have container initialized

            The MRO determines __init__ call order. With correct ordering:
            1. MyEffectNode.__init__ calls super().__init__()
            2. Python's MRO calls NodeEffect.__init__ (sets up container, node_id)
            3. NodeEffect.__init__ calls super().__init__()
            4. MixinEffectExecution.__init__ is called (initializes _circuit_breakers)
            5. MixinEffectExecution calls super().__init__() (reaches object)

            This ensures self.container and self.node_id exist before mixin methods
            are called. The _circuit_breakers dict is initialized AFTER super().__init__()
            to guarantee all base class attributes are available.

        Thread Safety:
            _circuit_breakers is instance-local state and NOT thread-safe.
            Each NodeEffect instance with this mixin should be used from a
            single thread or with explicit synchronization.

        Args:
            **kwargs: Passed to super().__init__() for cooperative MRO.
        """
        # Call super().__init__() FIRST to complete all base class initialization.
        # This ensures container and node_id are available on self.
        super().__init__(**kwargs)

        # Circuit breaker state: operation_id -> ModelCircuitBreaker
        # Initialized AFTER super().__init__() to ensure base class setup completes first.
        # Thread Safety: NOT thread-safe - see class docstring for details.
        # Each operation_id gets its own circuit breaker instance.
        self._circuit_breakers: dict[UUID, ModelCircuitBreaker] = {}

    async def execute_effect(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Execute effect operation with full resilience patterns.

        This is the main entry point for contract-driven effect execution.
        It orchestrates sequential operations with abort-on-first-failure
        semantics, retry policies, circuit breakers, and transaction management.

        Operation Data Population (IMPORTANT):
            This method expects operations to be provided in input_data.operation_data
            under the "operations" key. The calling code (typically NodeEffect.process())
            is responsible for populating this data, which may include:

            1. Transforming effect_subcontract.operations into operation_data["operations"]
            2. Merging runtime parameters with static contract definitions
            3. Applying any preprocessing or validation

            This design separates the MIXIN (execution logic) from the NODE (contract
            binding). The mixin is contract-agnostic and works with raw operation_data,
            while the node handles the contract-to-data transformation.

            Expected operation_data structure:
                {
                    "operations": [
                        {
                            "io_config": {
                                "handler_type": "http",
                                "url_template": "...",
                                ...
                            },
                            "operation_timeout_ms": 60000
                        }
                    ],
                    ... # Additional context for template resolution
                }

        Thread Safety:
            Not thread-safe due to circuit breaker state. Use from single
            thread or with explicit synchronization.

        Args:
            input_data: Effect input containing operation configuration in
                operation_data["operations"], retry policies, circuit breaker
                settings, and transaction configuration. The caller is
                responsible for populating operation_data from effect_subcontract
                or other sources.

        Returns:
            ModelEffectOutput containing operation result, transaction state,
            timing metrics, and execution metadata.

        Raises:
            ModelOnexError: On validation errors, handler failures, or
                configuration issues. All errors are structured with proper
                error codes and context.

        Example:
            >>> input_data = ModelEffectInput(
            ...     effect_type=EnumEffectType.API_CALL,
            ...     operation_data={
            ...         "operations": [{
            ...             "io_config": {"handler_type": "http", "url_template": "..."},
            ...             "operation_timeout_ms": 30000
            ...         }]
            ...     },
            ...     retry_enabled=True,
            ...     max_retries=3,
            ... )
            >>> result = await self.execute_effect(input_data)
            >>> print(f"Success: {result.transaction_state}")
        """
        start_time = time.time()
        operation_id = input_data.operation_id

        # Extract operation configuration from input_data.operation_data
        # For v1.0, we expect a single operation configuration
        operations_config = input_data.operation_data.get("operations", [])
        if not operations_config:
            raise ModelOnexError(
                message="No operations defined in effect input",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                context={"operation_id": str(operation_id)},
            )

        # Sequential execution with abort-on-first-failure (v1.0)
        retry_count = 0
        final_result: str | int | float | bool | dict[str, Any] | list[Any] = {}
        transaction_state = EnumTransactionState.PENDING

        try:
            # Execute first operation (v1.0: single operation only)
            operation_config = operations_config[0]

            # Parse operation configuration
            io_config = self._parse_io_config(operation_config)
            operation_timeout_ms = operation_config.get("operation_timeout_ms", 60000)

            # Resolve IO context from templates
            resolved_context = self._resolve_io_context(io_config, input_data)

            # Execute operation with retry and circuit breaker
            result, retry_count = await self._execute_with_retry(
                resolved_context,
                input_data,
                operation_timeout_ms,
            )

            final_result = result
            transaction_state = EnumTransactionState.COMMITTED

        except ModelOnexError:
            transaction_state = EnumTransactionState.ROLLED_BACK
            raise
        except Exception as e:
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

    def _parse_io_config(self, operation_config: dict[str, Any]) -> EffectIOConfig:
        """
        Parse operation configuration into typed IO config.

        Args:
            operation_config: Raw operation configuration dictionary.

        Returns:
            Typed EffectIOConfig (discriminated union).

        Raises:
            ModelOnexError: On invalid configuration.
        """
        io_config_data = operation_config.get("io_config")
        if not io_config_data:
            raise ModelOnexError(
                message="Missing io_config in operation",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )

        handler_type = io_config_data.get("handler_type")

        try:
            if handler_type == "http":
                return ModelHttpIOConfig(**io_config_data)
            elif handler_type == "db":
                return ModelDbIOConfig(**io_config_data)
            elif handler_type == "kafka":
                return ModelKafkaIOConfig(**io_config_data)
            elif handler_type == "filesystem":
                return ModelFilesystemIOConfig(**io_config_data)
            else:
                raise ModelOnexError(
                    message=f"Unknown handler type: {handler_type}",
                    error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                )
        except Exception as e:
            raise ModelOnexError(
                message=f"Failed to parse io_config: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

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

        Resolution happens INSIDE retry loop per spec (allows for secret
        refresh and environment changes between retries).

        Thread Safety:
            Pure function, thread-safe. Environment variable access is
            inherently racy but this is expected behavior.

        Args:
            io_config: Handler-specific IO configuration with template placeholders.
            input_data: Effect input containing operation data for substitution.

        Returns:
            Fully resolved IO context ready for handler execution.

        Raises:
            ModelOnexError: On template resolution failures or missing values.
        """
        # Resolution context
        context_data = input_data.operation_data

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
                    )
                return value

            elif placeholder.startswith("secret."):
                # Extract from secret service (if available)
                secret_key = placeholder[7:]  # Remove "secret."
                try:
                    secret_service = self.container.get_service("ProtocolSecretService")
                    secret_value = secret_service.get_secret(secret_key)
                    if secret_value is None:
                        raise ModelOnexError(
                            message=f"Secret not found: {secret_key}",
                            error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                        )
                    return str(secret_value)
                except Exception as e:
                    raise ModelOnexError(
                        message=f"Failed to resolve secret: {secret_key}",
                        error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    ) from e

            else:
                raise ModelOnexError(
                    message=f"Unknown template prefix: {placeholder}",
                    error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                )

        # Resolve based on handler type
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
            resolved_params: list[str | int | float | bool | None] = []
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
            # For filesystem write operations, content is extracted from input_data.operation_data.
            # The content can be provided in multiple ways (in priority order):
            # 1. "file_content" key in operation_data (preferred)
            # 2. "content" key in operation_data (fallback)
            # 3. None - handler may have alternative content source
            #
            # This design separates content from templates because:
            # 1. Large content bypasses template resolution overhead
            # 2. Binary content cannot be templated (use base64 encoding externally)
            # 3. Content may come from external sources (e.g., file uploads, streams)
            #
            # For read/delete/move/copy operations, content is typically None as these
            # operations don't require input content.
            content: str | None = None
            if io_config.operation == "write":
                # Extract content from operation_data for write operations
                content = context_data.get("file_content") or context_data.get(
                    "content"
                )
                # If content is a template string, resolve it
                if content and TEMPLATE_PATTERN.search(content):
                    content = TEMPLATE_PATTERN.sub(resolve_template, content)

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

    def _extract_field(self, data: dict[str, Any], field_path: str) -> Any:
        """
        Extract nested field from data using dotpath notation.

        Args:
            data: Source data dictionary.
            field_path: Dotted path like "user.id" or "config.timeout_ms".

        Returns:
            Extracted value or None if not found.
        """
        parts = field_path.split(".")
        current: Any = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        return current

    def _coerce_param_value(self, value: str) -> str | int | float | bool | None:
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

    async def _execute_with_retry(
        self,
        resolved_context: ResolvedIOContext,
        input_data: ModelEffectInput,
        operation_timeout_ms: int,
    ) -> tuple[str | int | float | bool | dict[str, Any] | list[Any], int]:
        """
        Execute operation with retry logic and circuit breaker.

        Retry Policy:
            - Only retry if input_data.retry_enabled is True
            - Only retry idempotent operations (determined by handler type)
            - Respect operation_timeout_ms overall timeout
            - Use exponential backoff with jitter

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

        Args:
            resolved_context: Fully resolved IO context.
            input_data: Effect input with retry configuration.
            operation_timeout_ms: Overall operation timeout including all retries.

        Returns:
            Tuple of (result, retry_count) where retry_count is the number of
            failed attempts before success (0 if succeeded on first try).

        Raises:
            ModelOnexError: On operation failure or timeout.
        """
        operation_id = input_data.operation_id
        max_retries = input_data.max_retries if input_data.retry_enabled else 0
        retry_delay_ms = input_data.retry_delay_ms

        start_time = time.time()
        retry_count = 0
        last_error: Exception | None = None

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
                # Execute operation
                result = await self._execute_operation(resolved_context, input_data)

                # Record success in circuit breaker
                if input_data.circuit_breaker_enabled:
                    self._record_circuit_breaker_result(operation_id, success=True)

                return result, retry_count

            except Exception as e:
                last_error = e
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
                    # Exponential backoff with jitter
                    delay_ms = retry_delay_ms * (2**attempt)
                    jitter = delay_ms * 0.1  # 10% jitter
                    actual_delay_ms = delay_ms + (jitter * (time.time() % 1))

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
    ) -> str | int | float | bool | dict[str, Any] | list[Any]:
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
                async def execute(context: ResolvedIOContext) -> Any

            If no handler is registered for a handler type, a ModelOnexError will
            be raised with HANDLER_EXECUTION_ERROR code.

        Thread Safety:
            Thread-safe if handlers are thread-safe. Handlers should be
            stateless or use their own synchronization.

        Args:
            resolved_context: Fully resolved IO context.
            input_data: Effect input with operation metadata.

        Returns:
            Operation result (type depends on handler).

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
            handler = self.container.get_service(handler_protocol)
        except Exception as resolve_error:
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
            result = await handler.execute(resolved_context)
        except Exception as exec_error:
            raise ModelOnexError(
                message=f"Handler execution failed for {handler_protocol}: {exec_error!s}",
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                context={
                    "operation_id": str(input_data.operation_id),
                    "handler_type": handler_type.value,
                },
            ) from exec_error

        # Handler returns Any, validate it matches expected return type
        if isinstance(result, (str, int, float, bool, dict, list, type(None))):
            return result  # type: ignore[return-value]
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

    def _extract_response_fields(
        self,
        response: dict[str, Any],
        response_handling: dict[str, Any],
    ) -> dict[str, str | int | float | bool | None]:
        """
        Extract fields from response using JSONPath or dotpath.

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

        extracted: dict[str, str | int | float | bool | None] = {}

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
            except Exception as e:
                raise ModelOnexError(
                    message=f"Field extraction failed for {output_name}: {e!s}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                ) from e

        return extracted
