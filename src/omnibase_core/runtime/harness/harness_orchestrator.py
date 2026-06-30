# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Harness ORCHESTRATOR handler: command -> inference-request event (OMN-13420)."""

from __future__ import annotations

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_command import (
    ModelHarnessCommand,
)
from omnibase_core.models.runtime.harness.model_harness_infer_requested import (
    ModelHarnessInferRequested,
)
from omnibase_core.runtime.harness.harness_topics import infer_topic


class HarnessOrchestratorHandler:
    """ORCHESTRATOR: consumes the command, emits an inference-request event."""

    def __init__(self, workflow: str) -> None:
        self._workflow = workflow

    @property
    def handler_id(self) -> str:
        """Return the unique handler identifier."""
        return f"harness-{self._workflow}-orchestrator"

    @property
    def category(self) -> EnumMessageCategory:
        """Return the handled message category."""
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        """Accept all message types in the category."""
        return set()

    @property
    def node_kind(self) -> EnumNodeKind:
        """Return the ONEX node kind."""
        return EnumNodeKind.ORCHESTRATOR

    async def handle(
        self, envelope: ModelEventEnvelope[ModelHarnessCommand]
    ) -> ModelHandlerOutput[None]:
        """Emit an inference-request event for the command."""
        command = envelope.payload
        infer = ModelHarnessInferRequested(
            correlation_id=command.correlation_id,
            workflow=command.workflow,
            prompt=command.prompt,
            max_tokens=command.max_tokens,
        )
        emitted: ModelEventEnvelope[ModelHarnessInferRequested] = ModelEventEnvelope(
            payload=infer,
            correlation_id=command.correlation_id,
            event_type=infer_topic(command.workflow),
            payload_type="ModelHarnessInferRequested",
            source_tool=self.handler_id,
        )
        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=envelope.envelope_id,
            correlation_id=command.correlation_id,
            handler_id=self.handler_id,
            events=(emitted,),
        )


__all__ = ["HarnessOrchestratorHandler"]
