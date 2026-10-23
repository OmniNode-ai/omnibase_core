# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerValidatorTriggeredEmit — a triggered validator emits a bus event.

RULING 2026-10-14T20:01:09Z (OMN-21277): "validators emit a bus event when
they trigger". Given a canonical OMN-2362 ValidationReport, this EFFECT
handler publishes one ``onex.evt.platform.validator-triggered.v1`` event per
validator that has a FAIL or ERROR finding, keyed by the validator id, through
the injected event bus ``publish`` call
(``EventBusInmemory.publish`` or a broker-backed bus's). WARN, PASS and SKIP findings publish nothing.

The topic comes from :class:`omnibase_core.topics.TopicBase`, registered in
``contracts/topic_registry.yaml``. The handler reads no clock: the bus headers
carry the publish time and the caller supplies the correlation id.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_input import (
    ModelValidatorTriggeredEmitInput,
)
from omnibase_core.models.nodes.validator_triggered_emit.model_validator_triggered_emit_output import (
    ModelValidatorTriggeredEmitOutput,
)
from omnibase_core.models.validation.model_validator_triggered_event import (
    ModelValidatorTriggeredEvent,
)
from omnibase_core.topics import TopicBase

__all__ = ["HandlerValidatorTriggeredEmit", "PublishFn"]

# The bus publish call every backend exposes: ``publish(topic, key, value)``.
PublishFn = Callable[[str, bytes | None, bytes], Awaitable[None]]

_TRIGGERING: frozenset[str] = frozenset({"FAIL", "ERROR"})


class HandlerValidatorTriggeredEmit:
    """Publish one validator-triggered event per failing validator."""

    def __init__(self, publish: PublishFn) -> None:
        self._publish = publish

    async def handle(
        self, request: ModelValidatorTriggeredEmitInput
    ) -> ModelValidatorTriggeredEmitOutput:
        """Definition-B canonical entry-point (OMN-14355)."""
        triggered: dict[str, list[tuple[str, str | None]]] = {}
        for finding in request.report.findings:
            if finding.severity in _TRIGGERING:
                triggered.setdefault(finding.validator_id, []).append(
                    (finding.severity, finding.location)
                )

        events: list[ModelValidatorTriggeredEvent] = []
        for validator_id, findings in triggered.items():
            severity: Literal["FAIL", "ERROR"] = (
                "ERROR" if any(s == "ERROR" for s, _ in findings) else "FAIL"
            )
            event = ModelValidatorTriggeredEvent(
                validator_name=validator_id,
                severity=severity,
                finding_count=len(findings),
                locations=tuple(loc for _, loc in findings if loc is not None),
                repository=request.repository,
                pull_request=request.pull_request,
                head_sha=request.head_sha,
                correlation_id=request.correlation_id,
            )
            await self._publish(
                TopicBase.VALIDATOR_TRIGGERED,
                validator_id.encode("utf-8"),
                event.model_dump_json().encode("utf-8"),
            )
            events.append(event)
        return ModelValidatorTriggeredEmitOutput(events=tuple(events))
