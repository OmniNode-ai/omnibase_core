# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeValidationReportWriteEffect — validation-report persistence EFFECT handler.

The filesystem write behind every converted check runtime's ``--report-json``
flag. Check runtime packages live under COMPUTE node packages and the
no-io-outside-effects gate forbids a write there, so the write is this EFFECT
node, on the definition-B ``handle(request) -> response`` shape (OMN-14355).

Every converted check runtime writes its report through this node, so it is also
the one place a validator's run and fire events are derived: the events go, one
JSON line each, to ``<report_path>.events.jsonl`` (OMN-17427, RULING
2026-10-14T20:01:09Z). The CI collector adds the repository, the pull request
or commit and the duration, and carries the lines to the event bus.

Ticket: OMN-20565 (validator conversion, omnibase_core first batch).
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.handlers.handler_validator_run_events import (
    HandlerValidatorRunEvents,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
    ModelValidationReportWriteOutput,
)

__all__ = ["NodeValidationReportWriteEffect"]


class NodeValidationReportWriteEffect:
    """EFFECT handler that writes a canonical validation report as JSON."""

    def handle(
        self, request: ModelValidationReportWriteInput
    ) -> ModelValidationReportWriteOutput:
        """Write ``request.report`` to ``request.report_path``, creating parents."""
        target = Path(request.report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = request.report.model_dump_json(indent=2).encode("utf-8")
        target.write_bytes(payload)
        events = HandlerValidatorRunEvents().handle(request.report).events
        events_path = target.with_name(f"{target.name}.events.jsonl")
        with events_path.open("a", encoding="utf-8") as sink:
            sink.writelines(f"{event.model_dump_json()}\n" for event in events)
        return ModelValidationReportWriteOutput(
            report_path=request.report_path,
            bytes_written=len(payload),
            events_path=str(events_path),
            events_written=len(events),
        )
