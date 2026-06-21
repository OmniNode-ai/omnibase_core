# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Harness REDUCER handler: terminal event -> projection row (OMN-13420).

Materializes a read-optimized projection (its single allowed output) into the
injected projection store. The harness store write is the projection side effect
for the in-process inner loop; the broker-backed lane uses the real projection
node.
"""

from __future__ import annotations

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_terminal import (
    ModelHarnessTerminal,
)
from omnibase_core.models.runtime.harness.model_projection_row import ModelProjectionRow
from omnibase_core.protocols.runtime.protocol_harness_projection_store import (
    ProtocolHarnessProjectionStore,
)
from omnibase_core.runtime.harness.harness_topics import completed_topic


class HarnessProjectionReducer:
    """REDUCER: consumes the terminal event, materializes a projection row."""

    def __init__(self, workflow: str, store: ProtocolHarnessProjectionStore) -> None:
        self._workflow = workflow
        self._store = store

    @property
    def handler_id(self) -> str:
        """Return the unique handler identifier."""
        return f"harness-{self._workflow}-projection-reducer"

    @property
    def category(self) -> EnumMessageCategory:
        """Return the handled message category."""
        return EnumMessageCategory.EVENT

    @property
    def message_types(self) -> set[str]:
        """Accept all message types in the category."""
        return set()

    @property
    def node_kind(self) -> EnumNodeKind:
        """Return the ONEX node kind."""
        return EnumNodeKind.REDUCER

    async def handle(
        self, envelope: ModelEventEnvelope[ModelHarnessTerminal]
    ) -> ModelHandlerOutput[None]:
        """Write the projection row and return it as the reducer projection."""
        terminal = envelope.payload
        row = ModelProjectionRow(
            correlation_id=terminal.correlation_id,
            workflow=terminal.workflow,
            terminal_topic=completed_topic(terminal.workflow),
            status=terminal.status,
            payload={
                "completion": terminal.completion,
                "model": terminal.model,
                "adapter": terminal.adapter,
            },
        )
        self._store.write(row)
        return ModelHandlerOutput.for_reducer(
            input_envelope_id=envelope.envelope_id,
            correlation_id=terminal.correlation_id,
            handler_id=self.handler_id,
            projections=(row,),
        )


__all__ = ["HarnessProjectionReducer"]
