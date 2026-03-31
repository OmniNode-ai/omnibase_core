# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeComplianceEvidenceEffect — EFFECT node for compliance report persistence.

Writes the aggregated compliance report to disk in two locations:
  - Latest alias:   .onex_state/compliance/report.yaml  (overwritten each run)
  - Run-specific:   .onex_state/compliance/runs/{run_id}.yaml  (durable history)

After the durable write is confirmed, emits the completion topic declared in
the contract so downstream consumers can treat receipt as proof that evidence
is readable.

ONEX node type: EFFECT
Ticket: OMN-7071

.. versionadded:: OMN-7071
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from omnibase_core.models.nodes.compliance_evidence.model_compliance_report_state import (
    ModelComplianceReportState,
)

logger = logging.getLogger(__name__)

__all__ = ["NodeComplianceEvidenceEffect"]


class NodeComplianceEvidenceEffect:
    """EFFECT handler that persists compliance evidence to disk.

    Args:
        state_root: Root directory for state artifacts (typically ``.onex_state``).
        event_bus: Optional event bus for emitting completion events. When ``None``
            the completion event is logged but not published (local-dev fallback).
        completion_topic: Topic string from the contract's publish_topics.
    """

    def __init__(
        self,
        state_root: Path,
        event_bus: Any = None,
        completion_topic: str = "",
    ) -> None:
        self._state_root = Path(state_root)
        self._event_bus = event_bus
        self._completion_topic = completion_topic

    def execute(self, report: ModelComplianceReportState) -> Path:
        """Write the compliance report and emit the completion event.

        Returns:
            Path to the run-specific report file.
        """
        run_id = report.run_id or str(uuid4())
        timestamp = report.scan_started_at or datetime.now(tz=UTC).isoformat()

        report_data = report.model_dump(mode="json")
        report_data["run_id"] = run_id
        report_data["timestamp"] = timestamp

        compliance_dir = self._state_root / "compliance"
        runs_dir = compliance_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write run-specific durable copy first (most important)
        run_path = runs_dir / f"{run_id}.yaml"
        run_path.write_text(
            yaml.dump(report_data, default_flow_style=False, sort_keys=False)
        )

        # 2. Write latest alias (convenience, overwritten each run)
        latest_path = compliance_dir / "report.yaml"
        latest_path.write_text(
            yaml.dump(report_data, default_flow_style=False, sort_keys=False)
        )

        logger.info(
            "Compliance evidence written: %s (total=%d, passed=%d, failed=%d)",
            run_path,
            report.total,
            report.passed,
            report.failed,
        )

        # 3. Emit completion event AFTER durable write
        self._emit_completion(run_id=run_id, report_data=report_data)

        return run_path

    # ONEX_EXCLUDE: dict_str_any — report_data is model_dump output, typed at origin
    def _emit_completion(
        self,
        run_id: str,
        report_data: dict[str, Any],
    ) -> None:
        """Emit the completion event to the bus (or log if no bus)."""
        if not self._completion_topic:
            logger.info("No completion topic configured — skipping event emission")
            return

        event_payload = {
            "topic": self._completion_topic,
            "run_id": run_id,
            "total": report_data["total"],
            "passed": report_data["passed"],
            "failed": report_data["failed"],
        }
        if self._event_bus is not None:
            self._event_bus.publish(self._completion_topic, event_payload)
            logger.info("Completion event emitted: %s", self._completion_topic)
        else:
            logger.info(
                "No event bus configured — completion event logged only: %s",
                self._completion_topic,
            )
