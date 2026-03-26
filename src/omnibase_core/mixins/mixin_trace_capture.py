# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
MixinTraceCapture - Automatic execution trace capture mixin.

Bridges the gap between the ONEX trace infrastructure (ModelExecutionTrace,
ServiceTraceRecording) and actual node execution. Previously, the trace models
and services existed but were never wired to the node lifecycle.

Usage::

    from omnibase_core.mixins import MixinTraceCapture

    class MyNode(NodeBase, MixinTraceCapture):
        async def process(self, input_data):
            result, trace = await self.run_traced(
                self._do_work(input_data),
            )
            return result

Thread Safety:
    Thread safety depends on the underlying ProtocolTraceStore implementation.
    When using ServiceTraceInMemoryStore (the default), this mixin is NOT
    thread-safe. Use separate instances per thread or inject a thread-safe store.

.. versionadded:: 0.6.6
    Added to wire existing trace infrastructure into node execution (OMN-2401)
"""

from __future__ import annotations

import traceback
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID, uuid4

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.trace.model_execution_trace import ModelExecutionTrace

if TYPE_CHECKING:
    from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
    from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore

T = TypeVar("T")

_TRACE_ERROR_MAX_LEN = 500  # chars; mirrors ModelExecutionTraceStep.error_summary cap


class MixinTraceCapture:
    """
    Mixin for automatic execution trace capture.

    Records a :class:`~omnibase_core.models.trace.ModelExecutionTrace` for
    every :meth:`run_traced` call, covering both success and failure paths.
    Uses an injected or automatically created
    :class:`~omnibase_core.services.trace.ServiceTraceInMemoryStore` backend.

    Attributes:
        _trace_store: The underlying store backend (lazy-initialised).
        _trace_enabled: Whether trace capture is active (default: True).

    Example:
        .. code-block:: python

            from omnibase_core.mixins import MixinTraceCapture
            from omnibase_core.services.trace.service_trace_in_memory_store import (
                ServiceTraceInMemoryStore,
            )

            class MyNode(MixinTraceCapture):
                async def run(self, payload: str) -> str:
                    result, trace = await self.run_traced(
                        self._transform(payload),
                    )
                    return result

                async def _transform(self, payload: str) -> str:
                    return payload.upper()

            node = MyNode()
            node.init_trace_capture()
            import asyncio
            asyncio.run(node.run("hello"))
            traces = asyncio.run(node.get_recorded_traces())
            assert len(traces) == 1
            assert traces[0].is_successful()

    See Also:
        - :class:`~omnibase_core.models.trace.ModelExecutionTrace`:
          The trace model emitted by this mixin
        - :class:`~omnibase_core.services.trace.ServiceTraceRecording`:
          Higher-level service wrapping :class:`ProtocolTraceStore`
        - :class:`~omnibase_core.protocols.storage.ProtocolTraceStore`:
          Storage protocol for pluggable backends

    .. versionadded:: 0.6.6
    """

    _trace_store: ProtocolTraceStore | None = None
    _trace_enabled: bool = True

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_trace_capture(
        self,
        store: ProtocolTraceStore | None = None,
        enabled: bool = True,
    ) -> None:
        """
        Initialise trace capture with an optional custom store.

        If *store* is ``None``, a fresh
        :class:`~omnibase_core.services.trace.ServiceTraceInMemoryStore` is
        created automatically. Call this method before the first
        :meth:`run_traced` invocation.

        Args:
            store: Optional custom :class:`ProtocolTraceStore` backend.
                Defaults to a new ``ServiceTraceInMemoryStore``.
            enabled: Whether trace capture is active. Defaults to ``True``.
                Set to ``False`` to make :meth:`run_traced` a transparent
                pass-through with no overhead.

        Example:
            >>> node = MyNode()
            >>> node.init_trace_capture()          # in-memory default
            >>> node.init_trace_capture(enabled=False)  # disable tracing
        """
        self._trace_enabled = enabled
        if store is not None:
            self._trace_store = store
        elif enabled:
            from omnibase_core.services.trace.service_trace_in_memory_store import (
                ServiceTraceInMemoryStore,
            )

            self._trace_store = ServiceTraceInMemoryStore()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def run_traced(
        self,
        coro: Coroutine[Any, Any, T],
        *,
        run_id: UUID | None = None,
        correlation_id: UUID | None = None,
        dispatch_id: UUID | None = None,
    ) -> tuple[T, ModelExecutionTrace | None]:
        """
        Await *coro* and record an :class:`ModelExecutionTrace` for the run.

        On success the trace status is :attr:`EnumExecutionStatus.SUCCESS`.
        On any exception the status is :attr:`EnumExecutionStatus.FAILED` and
        the exception is re-raised after the trace is persisted.

        If trace capture is disabled (``enabled=False`` in
        :meth:`init_trace_capture`) or the store has not been initialised,
        *coro* is awaited normally and ``None`` is returned in place of the
        trace.

        Args:
            coro: The coroutine to execute and trace.
            run_id: Identifies this specific execution run. Auto-generated
                if not supplied.
            correlation_id: Links related traces across distributed
                executions. Auto-generated if not supplied.
            dispatch_id: Dispatch ID if execution was triggered by a
                dispatcher. ``None`` if not applicable.

        Returns:
            A 2-tuple ``(result, trace)`` where *result* is the value
            returned by *coro* and *trace* is the recorded
            :class:`ModelExecutionTrace` (or ``None`` if tracing is off).

        Raises:
            Exception: Any exception raised by *coro* is re-raised after
                the failure trace is persisted.

        Example:
            .. code-block:: python

                result, trace = await self.run_traced(
                    self.fetch_data(url),
                    correlation_id=request_id,
                )
                assert trace is not None
                print(f"fetch took {trace.get_duration_ms():.1f} ms")
        """
        store = getattr(self, "_trace_store", None)
        enabled = getattr(self, "_trace_enabled", True)

        if not enabled or store is None:
            # Lazy auto-init: create a default in-memory store on first use.
            if enabled and store is None:
                from omnibase_core.services.trace.service_trace_in_memory_store import (
                    ServiceTraceInMemoryStore,
                )

                self._trace_store = ServiceTraceInMemoryStore()
                store = self._trace_store
            else:
                # Tracing fully disabled — transparent pass-through.
                result: T = await coro
                return result, None

        resolved_run_id: UUID = run_id if run_id is not None else uuid4()
        resolved_correlation_id: UUID = (
            correlation_id if correlation_id is not None else uuid4()
        )

        started_at: datetime = datetime.now(UTC)
        status: EnumExecutionStatus = EnumExecutionStatus.RUNNING
        error_text: str | None = None
        result_value: T | None = None

        try:
            result_value = await coro
            status = EnumExecutionStatus.SUCCESS
        except Exception as exc:
            status = EnumExecutionStatus.FAILED
            error_text = _format_error(exc)
            raise
        finally:
            ended_at: datetime = datetime.now(UTC)
            trace = ModelExecutionTrace(
                correlation_id=resolved_correlation_id,
                run_id=resolved_run_id,
                dispatch_id=dispatch_id,
                started_at=started_at,
                ended_at=ended_at,
                status=status,
            )
            await store.put(trace)

        return result_value, trace

    # ------------------------------------------------------------------
    # Store Access
    # ------------------------------------------------------------------

    def get_trace_store(self) -> ProtocolTraceStore | None:
        """
        Return the configured trace store.

        Returns:
            The :class:`ProtocolTraceStore` backend, or ``None`` if trace
            capture has not been initialised.
        """
        return getattr(self, "_trace_store", None)

    async def get_recorded_traces(
        self,
        filters: ModelTraceQuery | None = None,
    ) -> list[ModelExecutionTrace]:
        """
        Return all traces recorded by this mixin instance.

        If *filters* is supplied, only matching traces are returned. If no
        store has been initialised, returns an empty list.

        Args:
            filters: Optional :class:`~omnibase_core.models.trace_query.ModelTraceQuery`
                to narrow results. When ``None``, all traces are returned
                (up to the store's default limit).

        Returns:
            List of :class:`ModelExecutionTrace` objects, ordered by
            insertion (most recent last for the in-memory backend).

        Example:
            .. code-block:: python

                from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
                from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery

                failed_query = ModelTraceQuery(status=EnumExecutionStatus.FAILED)
                failures = await node.get_recorded_traces(filters=failed_query)
        """
        store = getattr(self, "_trace_store", None)
        if store is None:
            return []

        if filters is None:
            from omnibase_core.models.trace_query.model_trace_query import (
                ModelTraceQuery,
            )

            filters = ModelTraceQuery()

        return await store.query(filters)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_error(exc: BaseException) -> str:
    """Format an exception into a bounded string for trace storage."""
    lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    full = "".join(lines)
    if len(full) <= _TRACE_ERROR_MAX_LEN:
        return full
    return full[: _TRACE_ERROR_MAX_LEN - 3] + "..."


__all__ = ["MixinTraceCapture"]
