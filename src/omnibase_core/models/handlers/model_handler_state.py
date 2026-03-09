# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler State Model.

Defines ``HandlerStateModel`` — a Pydantic model that captures the **logical
(serializable) state** of a handler. This model is explicitly scoped to state
that can be snapshotted, serialized, and diffed.

Design Rationale
----------------
Handler state today is a mix of logical state (configuration, counters, timestamps)
and runtime state (open connections, async clients, file handles). This conflation
makes handlers impossible to serialize, snapshot, or migrate.

``HandlerStateModel`` establishes a clean separation:

* **Logical state** (this model): serializable, diffable, snapshotable.
  Lives in ``omnibase_core``.
* **Runtime resources**: non-serializable, managed externally by
  ``HandlerResourceManager`` in ``omnibase_infra``.

This is a prerequisite for future handler-as-nodes decomposition where ONEX
graph nodes operate on logical state and delegate resource acquisition to the
resource manager.

Monolithic handlers are **PRESERVED** for MVP — this model does not replace their
internal state; it defines what their logical state *should* look like when
externalized.

Constraints
-----------
* No runtime resource types (no ``httpx``, no ``asyncio`` primitives, no file handles)
* No imports from ``omnibase_infra``
* All fields must be JSON-serializable via Pydantic's ``.model_dump()``

Import Example
--------------
.. code-block:: python

    from omnibase_core.models.handlers import HandlerStateModel
    from omnibase_core.enums import EnumHandlerStatus

    state = HandlerStateModel(
        handler_id="onex:postgres-handler",
        handler_type="postgres",
        status=EnumHandlerStatus.READY,
    )
    snapshot = state.model_dump_json()

.. versionadded:: 0.8.0
    Added as part of OMN-4223 (define HandlerStateModel — logical state only).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_status import EnumHandlerStatus


class HandlerStateModel(BaseModel):
    """
    Logical (serializable) state snapshot of a handler.

    This model captures only the state that can be serialized, snapshotted,
    and diffed. It explicitly excludes runtime resources (httpx clients,
    Kafka producers, asyncio primitives, file handles, database connections).

    Use this model when:
        - Persisting handler state to a store or log
        - Comparing handler state across time (diffing)
        - Migrating handler state between processes
        - Reporting handler health metrics

    Do NOT include in this model:
        - Open network connections or clients (httpx, aiohttp)
        - Async primitives (asyncio.Event, asyncio.Queue)
        - File handles or OS resources
        - Kafka producers or consumers
        - Database sessions or connections

    Attributes:
        handler_id: Unique identifier for the handler instance. Matches the
            handler's registry key or configured identity.
        handler_type: Type string identifying the handler class or category
            (e.g., ``"postgres"``, ``"kafka-ingress"``, ``"http-client"``).
        status: Current operational status of the handler. See
            :class:`~omnibase_core.enums.enum_handler_status.EnumHandlerStatus`.
        initialized_at: UTC timestamp when the handler completed initialization.
            None if the handler has not yet reached READY status.
        last_heartbeat_at: UTC timestamp of the most recent heartbeat or
            health check. None if no heartbeat has been recorded.
        error_count: Cumulative count of errors encountered since last reset.
            Used for degradation detection and alerting thresholds.
        last_error_message: Human-readable description of the most recent
            error. None if no errors have occurred or after a successful reset.
        metadata: Arbitrary string key-value pairs for handler-specific
            annotations. All values must be strings (no nested objects).

    Example:
        >>> from omnibase_core.models.handlers import HandlerStateModel
        >>> from omnibase_core.enums import EnumHandlerStatus
        >>> state = HandlerStateModel(
        ...     handler_id="onex:postgres-handler",
        ...     handler_type="postgres",
        ...     status=EnumHandlerStatus.READY,
        ... )
        >>> state.status
        <EnumHandlerStatus.READY: 'ready'>
        >>> state.error_count
        0
        >>> state.model_dump_json()  # fully JSON-serializable
        '{"handler_id":"onex:postgres-handler","handler_type":"postgres",...}'

    Thread Safety:
        This model is mutable (default Pydantic config). Create a new instance
        or use ``model_copy(update={...})`` when updating state to avoid
        unintended mutation across threads.

    .. versionadded:: 0.8.0
    """

    model_config = ConfigDict(extra="forbid")

    handler_id: str = Field(
        ...,
        description=(
            "Unique identifier for the handler instance. "
            "Matches the handler's registry key or configured identity."
        ),
    )

    handler_type: str = Field(
        ...,
        description=(
            "Type string identifying the handler class or category. "
            "Examples: 'postgres', 'kafka-ingress', 'http-client'. "
            "Used for routing and observability labeling."
        ),
    )

    status: EnumHandlerStatus = Field(
        ...,
        description=(
            "Current operational status of the handler. "
            "Values: INITIALIZING, READY, DEGRADED, STOPPED."
        ),
    )

    initialized_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp when the handler completed initialization. "
            "None if the handler has not yet reached READY status."
        ),
    )

    last_heartbeat_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp of the most recent heartbeat or health check. "
            "None if no heartbeat has been recorded."
        ),
    )

    error_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Cumulative count of errors encountered since last reset. "
            "Used for degradation detection and alerting thresholds."
        ),
    )

    last_error_message: str | None = Field(
        default=None,
        description=(
            "Human-readable description of the most recent error. "
            "None if no errors have occurred."
        ),
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Arbitrary string key-value pairs for handler-specific annotations. "
            "All values must be strings — no nested objects or non-string values."
        ),
    )


__all__ = ["HandlerStateModel"]
