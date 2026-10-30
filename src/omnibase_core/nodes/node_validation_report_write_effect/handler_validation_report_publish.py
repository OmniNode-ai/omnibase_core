# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeValidationReportPublishEffect — the report writer that also publishes (OMN-21529).

It resolves the validator-runtime bus from its container with ``get_service`` and never
builds one, puts exactly one ``ModelValidatorRunEvent`` for the run on the run topic and one
``onex.evt.platform.validator-triggered.v1`` event per failing validator. The bus is
whatever the container was composed with, so the in-memory overlay and the Redpanda
overlay differ by the overlay file alone. The writer starts the bus, publishes and
closes it inside one event loop: it is the bus's only user in the process. ``events.jsonl``
stays the offline copy the base writer leaves.
"""

from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
    ModelValidationReportWriteOutput,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_settings import (
    ModelValidatorRuntimeSettings,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_output import (
    ModelValidatorTriggeredEmitOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.models.validation.model_validator_run_events import (
    ModelValidatorRunEvents,
)
from omnibase_core.nodes.node_validation_report_write_effect._report_writer_interface import (
    ValidationReportWriterInterface,
)
from omnibase_core.nodes.node_validation_report_write_effect._run_events_interface import (
    ValidatorRunEventsInterface,
)
from omnibase_core.nodes.node_validation_report_write_effect._triggered_emitter_interface import (
    ValidatorTriggeredEmitterInterface,
)

__all__ = ["NodeValidationReportPublishEffect"]


_WRITER_TOKEN = cast(
    "type[ValidationReportWriterInterface[ModelValidationReportWriteInput, ModelValidationReportWriteOutput]]",
    ValidationReportWriterInterface,
)
_RUN_EVENTS_TOKEN = cast(
    "type[ValidatorRunEventsInterface[ModelValidationReport, ModelValidatorRunEvents]]",
    ValidatorRunEventsInterface,
)
_EMITTER_TOKEN = cast(
    "type[ValidatorTriggeredEmitterInterface[ModelValidatorTriggeredEmitInput, ModelValidatorTriggeredEmitOutput]]",
    ValidatorTriggeredEmitterInterface,
)


class NodeValidationReportPublishEffect:
    """The report writer that also publishes through the bus its container holds."""

    def __init__(self, container: ModelONEXContainer) -> None:
        self._writer = container.get_service(_WRITER_TOKEN)
        self._run_events = container.get_service(_RUN_EVENTS_TOKEN)
        self._emitter = container.get_service(_EMITTER_TOKEN)
        self._container = container
        self._run_topic = container.get_service(ModelValidatorRuntimeSettings).run_topic

    def handle(
        self, request: ModelValidationReportWriteInput
    ) -> ModelValidationReportWriteOutput:
        """Persist the offline copy, then publish through the composed bus."""
        output = self._writer.handle(request)
        run_event = self._run_events.handle(request.report).events[0]
        return output.model_copy(
            update={"events_published": self._publish(request, run_event)}
        )

    def _publish(
        self,
        request: ModelValidationReportWriteInput,
        run_event: ModelValidatorRunEvent,
    ) -> int:
        bus = self._container.get_service(ModelValidatorRuntimeBus)
        try:
            return asyncio.run(self._publish_all(bus, request, run_event))
        except RuntimeError as exc:
            raise ModelOnexError(
                message=f"the report writer publishes from a synchronous call: {exc}",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            ) from exc

    async def _publish_all(
        self,
        bus: ModelValidatorRuntimeBus,
        request: ModelValidationReportWriteInput,
        run_event: ModelValidatorRunEvent,
    ) -> int:
        """One run event, then one triggered event per failing validator."""
        failing = any(f.severity in ("FAIL", "ERROR") for f in request.report.findings)
        if failing and request.repository is None:
            raise ModelOnexError(
                message="publishing validator-triggered events needs the request's repository",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        await bus.start()
        try:
            await bus.publish(
                self._run_topic,
                request.report.report_id.encode("utf-8"),
                run_event.model_dump_json().encode("utf-8"),
            )
            triggered = await self._emitter.handle(
                ModelValidatorTriggeredEmitInput(
                    report=request.report,
                    repository=request.repository or "",
                    pull_request=request.pull_request,
                    head_sha=request.head_sha,
                    correlation_id=UUID(request.report.report_id),
                )
            )
        finally:
            await bus.close()
        return 1 + len(triggered.events)
