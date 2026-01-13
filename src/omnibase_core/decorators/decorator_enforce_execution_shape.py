"""
Runtime enforcement decorator for ONEX execution shapes.

This module provides a decorator that validates message handlers only receive
allowed message categories based on their node type, enforcing the canonical
ONEX execution shapes at runtime.

The ONEX four-node architecture defines specific valid patterns for message
routing. This decorator provides runtime enforcement of those patterns.

See Also:
    - EnumExecutionShape: Defines the canonical shapes
    - ModelExecutionShapeValidation: Validates if a shape is allowed
    - CANONICAL_EXECUTION_SHAPES.md: Full documentation of allowed/forbidden patterns
"""

import asyncio
import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["enforce_execution_shape"]

P = ParamSpec("P")
T = TypeVar("T")


def enforce_execution_shape(
    source_category: EnumMessageCategory,
    target_node_kind: EnumNodeKind,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that enforces ONEX execution shape constraints at runtime.

    This decorator validates that the combination of source message category
    and target node kind is a valid canonical execution shape before allowing
    the decorated handler to execute. If the shape is forbidden, it raises
    a ModelOnexError with CONTRACT_VIOLATION error code.

    Use this decorator on message handlers to ensure they only process messages
    that conform to the ONEX four-node architecture patterns.

    Args:
        source_category: The message category being handled (EVENT, COMMAND, INTENT)
        target_node_kind: The node kind that handles the message
            (ORCHESTRATOR, REDUCER, EFFECT, COMPUTE)

    Returns:
        A decorator that wraps the function with execution shape validation

    Raises:
        ModelOnexError: With CONTRACT_VIOLATION error code if the execution
            shape is forbidden by ONEX canonical patterns

    Example:
        >>> from omnibase_core.decorators import enforce_execution_shape
        >>> from omnibase_core.enums import EnumMessageCategory, EnumNodeKind
        >>>
        >>> class NodeMyOrchestrator(NodeOrchestrator):
        ...     @enforce_execution_shape(
        ...         source_category=EnumMessageCategory.EVENT,
        ...         target_node_kind=EnumNodeKind.ORCHESTRATOR,
        ...     )
        ...     async def handle_event(self, event: ModelEvent) -> None:
        ...         # This handler only accepts events routed to orchestrators
        ...         pass

    Allowed Shapes (will pass validation):
        - EVENT -> ORCHESTRATOR: Events routed for workflow coordination
        - EVENT -> REDUCER: Events routed for state aggregation
        - INTENT -> EFFECT: Intents routed for external actions
        - COMMAND -> ORCHESTRATOR: Commands routed for workflow execution
        - COMMAND -> EFFECT: Commands routed for direct execution

    Forbidden Shapes (will raise ModelOnexError):
        - EVENT -> COMPUTE: Events cannot route directly to compute nodes
        - EVENT -> EFFECT: Events cannot route directly to effects
        - INTENT -> REDUCER: Intents cannot route to reducers
        - INTENT -> COMPUTE: Intents cannot route to compute nodes
        - INTENT -> ORCHESTRATOR: Intents cannot route to orchestrators
        - COMMAND -> COMPUTE: Commands cannot route directly to compute
        - COMMAND -> REDUCER: Commands cannot route directly to reducers
        - Any -> RUNTIME_HOST: No messages route to runtime hosts

    Note:
        This decorator performs validation at decoration time (when the class
        is defined), not at runtime. This provides fail-fast behavior for
        architectural violations.

        Cancellation and exit signals (SystemExit, KeyboardInterrupt,
        GeneratorExit, asyncio.CancelledError) are NEVER caught by this
        decorator. They propagate normally for proper shutdown semantics.
    """
    # Deferred import to avoid circular import issues
    # The decorators module is imported by many modules, and
    # ModelExecutionShapeValidation has a long import chain that may
    # include modules that import decorators.
    from omnibase_core.models.validation.model_execution_shape_validation import (
        ModelExecutionShapeValidation,
    )

    # Validate the execution shape at decoration time (fail-fast)
    validation = ModelExecutionShapeValidation.validate_shape(
        source_category=source_category,
        target_node_kind=target_node_kind,
    )

    if not validation.is_allowed:
        # Raise immediately at decoration time for forbidden shapes
        msg = (
            f"Forbidden execution shape: {source_category.value} -> "
            f"{target_node_kind.value}. {validation.rationale}"
        )
        raise ModelOnexError(
            msg,
            error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
            context={
                "source_category": source_category.value,
                "target_node_kind": target_node_kind.value,
                "rationale": validation.rationale,
            },
        )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Check if the function is async
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                # Shape already validated at decoration time
                # Just execute the function
                result: T = await func(*args, **kwargs)
                return result

            # NOTE(OMN-1302): Wrapper matches original signature but mypy cannot verify Callable compatibility.
            # Safe because functools.wraps preserves signature.
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Shape already validated at decoration time
            # Just execute the function
            result: T = func(*args, **kwargs)
            return result

        return sync_wrapper

    return decorator
