# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeValidationReportWriteEffect — validation-report persistence EFFECT handler.

The filesystem write behind every converted check runtime's ``--report-json``
flag. Check runtime packages live under COMPUTE node packages and the
no-io-outside-effects gate forbids a write there, so the write is this EFFECT
node, on the definition-B ``handle(request) -> response`` shape (OMN-14355).

Ticket: OMN-20565 (validator conversion, omnibase_core first batch).
"""

from __future__ import annotations

from pathlib import Path

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
        return ModelValidationReportWriteOutput(
            report_path=request.report_path, bytes_written=len(payload)
        )
