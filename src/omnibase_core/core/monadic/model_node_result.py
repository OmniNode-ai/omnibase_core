"""
Monadic NodeResult for ONEX contract-driven architecture.

This module provides the core monadic composition patterns for ModelNodeBase,
enabling observable state transitions, composable error handling, and
workflow orchestration integration.

Author: ONEX Framework Team
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generic, Optional, TypeVar

from omnibase_core.core.common_types import ModelStateValue
from omnibase_core.core.errors.core_errors import OnexError

T = TypeVar("T")
U = TypeVar("U")


class ErrorType(Enum):
    """Structured error classification for monadic error handling."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    AUTHORIZATION = "authorization"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"


@dataclass
class LogEntry:
    """Structured log entry for execution context."""

    level: str
    message: str
    timestamp: datetime
    metadata: dict[str, ModelStateValue] | None = None


@dataclass
class ExecutionContext:
    """
    Execution context for node runs with complete observability.

    Captures provenance, trust metrics, timing, and correlation data
    for full workflow traceability and debugging support.
    """

    provenance: list[str]  # trace of node invocations
    logs: list[LogEntry]  # structured logs per step
    trust_score: float  # numeric trust level (0.0-1.0)
    timestamp: datetime  # execution timestamp
    metadata: dict[str, ModelStateValue]  # additional ad hoc data
    session_id: str | None = None  # session identifier
    correlation_id: str | None = None  # correlation identifier
    node_id: str | None = None  # executing node identifier
    workflow_id: str | None = None  # workflow identifier
    parent_context: Optional["ExecutionContext"] = None  # parent execution context


@dataclass
class Event:
    """
    Structured event for side effects and observability.

    Events are emitted by NodeResult operations and can be observed
    by monitoring systems, debug intelligence, and other nodes.
    """

    type: str  # e.g., "workflow.step.completed"
    payload: dict[str, ModelStateValue]  # structured content
    timestamp: datetime
    source: str | None = None  # source node identifier
    correlation_id: str | None = None
    workflow_id: str | None = None
    session_id: str | None = None
    trust_score: float | None = None


@dataclass
class ErrorInfo:
    """Structured error information for monadic failure handling."""

    error_type: ErrorType
    message: str
    code: str | None = None
    trace: str | None = None
    context: dict | None = None
    retryable: bool = False
    backoff_strategy: str | None = None
    max_attempts: int | None = None
    correlation_id: str | None = None


class NodeResult(Generic[T]):
    """
    Monadic result wrapper for node execution with observable state transitions.

    This is the core abstraction that enables:
    - Monadic bind operations for composing nodes
    - Observable state transitions for monitoring
    - Composable error handling with context preservation
    - Event emission for side effect tracking
    - LlamaIndex workflow integration
    """

    def __init__(
        self,
        value: T,
        context: ExecutionContext,
        state_delta: dict | None = None,
        events: list[Event] | None = None,
        error: ErrorInfo | None = None,
    ):
        self.value = value
        self.context = context
        self.state_delta = state_delta or {}
        self.events = events or []
        self.error = error
        self._is_success = error is None

    @property
    def is_success(self) -> bool:
        """Check if this result represents a successful operation."""
        return self._is_success

    @property
    def is_failure(self) -> bool:
        """Check if this result represents a failed operation."""
        return not self._is_success

    async def bind(
        self,
        f: Callable[[T], Awaitable["NodeResult[U]"]],
    ) -> "NodeResult[U]":
        """
        Monadic bind operation for composing nodes with context propagation.

        If this result is a failure, propagates the failure.
        If this result is a success, applies the function and combines contexts.
        """
        if self.is_failure:
            # Propagate failure with context
            return NodeResult(
                value=None,
                context=self.context,
                state_delta=self.state_delta,
                events=self.events,
                error=self.error,
            )

        try:
            # Apply function and combine contexts
            next_result = await f(self.value)

            # Combine execution contexts
            combined_context = ExecutionContext(
                provenance=self.context.provenance + next_result.context.provenance,
                logs=self.context.logs + next_result.context.logs,
                trust_score=min(
                    self.context.trust_score,
                    next_result.context.trust_score,
                ),
                timestamp=next_result.context.timestamp,
                metadata={**self.context.metadata, **next_result.context.metadata},
                session_id=self.context.session_id or next_result.context.session_id,
                correlation_id=self.context.correlation_id
                or next_result.context.correlation_id,
                node_id=next_result.context.node_id,
                workflow_id=self.context.workflow_id or next_result.context.workflow_id,
                parent_context=self.context,
            )

            # Combine state deltas
            combined_state_delta = {**self.state_delta, **next_result.state_delta}

            # Combine events
            combined_events = self.events + next_result.events

            return NodeResult(
                value=next_result.value,
                context=combined_context,
                state_delta=combined_state_delta,
                events=combined_events,
                error=next_result.error,
            )

        except OnexError as e:
            # Convert OnexError to structured failure
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=e.message,
                code=e.error_code.value if e.error_code else None,
                context=e.context,
                correlation_id=e.correlation_id,
                retryable=False,
            )

            return NodeResult(
                value=None,
                context=self.context,
                state_delta=self.state_delta,
                events=[
                    *self.events,
                    Event(
                        type="node.operation.failed",
                        payload={"error": error_info.__dict__},
                        timestamp=datetime.now(),
                        correlation_id=self.context.correlation_id,
                    ),
                ],
                error=error_info,
            )

        except Exception as e:
            # Convert generic exception to structured failure
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=str(e),
                trace=str(e.__traceback__) if e.__traceback__ else None,
                retryable=False,
                correlation_id=self.context.correlation_id,
            )

            return NodeResult(
                value=None,
                context=self.context,
                state_delta=self.state_delta,
                events=[
                    *self.events,
                    Event(
                        type="node.operation.exception",
                        payload={"error": str(e), "type": type(e).__name__},
                        timestamp=datetime.now(),
                        correlation_id=self.context.correlation_id,
                    ),
                ],
                error=error_info,
            )

    def map(self, f: Callable[[T], U]) -> "NodeResult[U]":
        """
        Map operation for transforming successful values.

        If this result is a failure, propagates the failure.
        If this result is a success, applies the function to the value.
        """
        if self.is_failure:
            return NodeResult(
                value=None,
                context=self.context,
                state_delta=self.state_delta,
                events=self.events,
                error=self.error,
            )

        try:
            new_value = f(self.value)
            return NodeResult(
                value=new_value,
                context=self.context,
                state_delta=self.state_delta,
                events=self.events,
            )
        except Exception as e:
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Map operation failed: {e!s}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                correlation_id=self.context.correlation_id,
            )

            return NodeResult(
                value=None,
                context=self.context,
                state_delta=self.state_delta,
                events=[
                    *self.events,
                    Event(
                        type="node.map.failed",
                        payload={"error": str(e)},
                        timestamp=datetime.now(),
                        correlation_id=self.context.correlation_id,
                    ),
                ],
                error=error_info,
            )

    @staticmethod
    async def gather(
        results: list[Awaitable["NodeResult[T]"]],
    ) -> "NodeResult[list[T]]":
        """
        Gather multiple NodeResult operations, combining their contexts.

        If any operation fails, returns the first failure.
        If all succeed, returns combined results.
        """
        completed_results = await asyncio.gather(*results, return_exceptions=True)

        successful_results = []
        combined_context = None
        combined_state_delta = {}
        combined_events = []

        for result in completed_results:
            if isinstance(result, Exception):
                # Handle exception in gather
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Gather operation failed: {result!s}",
                    trace=str(result.__traceback__) if result.__traceback__ else None,
                )

                return NodeResult(
                    value=None,
                    context=ExecutionContext(
                        provenance=["gather.failed"],
                        logs=[
                            LogEntry(
                                "ERROR",
                                f"Gather failed: {result!s}",
                                datetime.now(),
                            ),
                        ],
                        trust_score=0.0,
                        timestamp=datetime.now(),
                        metadata={"error": str(result)},
                    ),
                    events=[
                        Event(
                            type="node.gather.failed",
                            payload={"error": str(result)},
                            timestamp=datetime.now(),
                        ),
                    ],
                    error=error_info,
                )

            if result.is_failure:
                # Return first failure encountered
                return result

            successful_results.append(result.value)

            # Combine contexts
            if combined_context is None:
                combined_context = result.context
            else:
                combined_context = ExecutionContext(
                    provenance=combined_context.provenance + result.context.provenance,
                    logs=combined_context.logs + result.context.logs,
                    trust_score=min(
                        combined_context.trust_score,
                        result.context.trust_score,
                    ),
                    timestamp=result.context.timestamp,
                    metadata={**combined_context.metadata, **result.context.metadata},
                    session_id=combined_context.session_id or result.context.session_id,
                    correlation_id=combined_context.correlation_id
                    or result.context.correlation_id,
                )

            # Combine state deltas and events
            combined_state_delta.update(result.state_delta)
            combined_events.extend(result.events)

        return NodeResult(
            value=successful_results,
            context=combined_context,
            state_delta=combined_state_delta,
            events=combined_events,
        )

    @staticmethod
    def success(
        value: T,
        provenance: list[str],
        trust_score: float = 1.0,
        metadata: dict[str, ModelStateValue] | None = None,
        state_delta: dict | None = None,
        events: list[Event] | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        node_id: str | None = None,
        workflow_id: str | None = None,
    ) -> "NodeResult[T]":
        """Create a successful NodeResult with the given parameters."""
        context = ExecutionContext(
            provenance=provenance,
            logs=[],
            trust_score=trust_score,
            timestamp=datetime.now(),
            metadata=metadata or {},
            session_id=session_id,
            correlation_id=correlation_id,
            node_id=node_id,
            workflow_id=workflow_id,
        )

        return NodeResult(
            value=value,
            context=context,
            state_delta=state_delta,
            events=events,
        )

    @staticmethod
    def failure(
        error: ErrorInfo,
        provenance: list[str],
        trust_score: float = 0.0,
        metadata: dict[str, ModelStateValue] | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        node_id: str | None = None,
        workflow_id: str | None = None,
    ) -> "NodeResult[None]":
        """Create a failed NodeResult with the given error information."""
        context = ExecutionContext(
            provenance=provenance,
            logs=[LogEntry("ERROR", error.message, datetime.now())],
            trust_score=trust_score,
            timestamp=datetime.now(),
            metadata=metadata or {},
            session_id=session_id,
            correlation_id=correlation_id,
            node_id=node_id,
            workflow_id=workflow_id,
        )

        return NodeResult(
            value=None,
            context=context,
            events=[
                Event(
                    type="node.operation.failed",
                    payload={"error": error.__dict__},
                    timestamp=datetime.now(),
                    source=node_id,
                    correlation_id=correlation_id,
                    workflow_id=workflow_id,
                    session_id=session_id,
                ),
            ],
            error=error,
        )


# Type aliases for common NodeResult patterns
NodeResultT = NodeResult[T]
AsyncNodeResult = Awaitable[NodeResult[T]]
NodeFunction = Callable[[T], AsyncNodeResult[U]]
