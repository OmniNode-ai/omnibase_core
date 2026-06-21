# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Harness EFFECT handler: inference-request -> terminal completed event (OMN-13420)."""

from __future__ import annotations

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_infer_requested import (
    ModelHarnessInferRequested,
)
from omnibase_core.models.runtime.harness.model_harness_terminal import (
    ModelHarnessTerminal,
)
from omnibase_core.models.runtime.harness.model_inference_request import (
    ModelInferenceRequest,
)
from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
    ProtocolHarnessInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_topics import completed_topic


class HarnessEffectHandler:
    """EFFECT: runs inference behind the adapter seam, emits the terminal event."""

    def __init__(self, workflow: str, adapter: ProtocolHarnessInferenceAdapter) -> None:
        self._workflow = workflow
        self._adapter = adapter

    @property
    def handler_id(self) -> str:
        """Return the unique handler identifier."""
        return f"harness-{self._workflow}-effect"

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
        return EnumNodeKind.EFFECT

    async def handle(
        self, envelope: ModelEventEnvelope[ModelHarnessInferRequested]
    ) -> ModelHandlerOutput[None]:
        """Run inference and emit the terminal completed event."""
        infer = envelope.payload
        result = self._adapter.infer(
            ModelInferenceRequest(prompt=infer.prompt, max_tokens=infer.max_tokens)
        )
        terminal = ModelHarnessTerminal(
            correlation_id=infer.correlation_id,
            workflow=infer.workflow,
            status="success",
            completion=result.completion,
            model=result.model,
            adapter=result.adapter,
        )
        emitted: ModelEventEnvelope[ModelHarnessTerminal] = ModelEventEnvelope(
            payload=terminal,
            correlation_id=infer.correlation_id,
            event_type=completed_topic(infer.workflow),
            payload_type="ModelHarnessTerminal",
            source_tool=self.handler_id,
        )
        return ModelHandlerOutput.for_effect(
            input_envelope_id=envelope.envelope_id,
            correlation_id=infer.correlation_id,
            handler_id=self.handler_id,
            events=(emitted,),
        )


__all__ = ["HarnessEffectHandler"]
