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
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_triggered_emit import (
    HandlerValidatorTriggeredEmit,
)

__all__ = ["NodeValidationReportPublishEffect"]


class NodeValidationReportPublishEffect(NodeValidationReportWriteEffect):
    """The report writer that also publishes through the bus its container holds."""

    def __init__(self, container: ModelONEXContainer, run_topic: str) -> None:
        self._container = container
        self._run_topic = run_topic

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
            triggered = await HandlerValidatorTriggeredEmit(bus.publish).handle(
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
