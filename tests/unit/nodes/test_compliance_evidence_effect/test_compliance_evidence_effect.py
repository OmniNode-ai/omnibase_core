# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeComplianceEvidenceEffect.

Verifies that the compliance evidence EFFECT node writes report files
to disk with the correct structure and content.

Ticket: OMN-7071
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.compliance_evidence.model_compliance_check_entry import (
    ModelComplianceCheckEntry,
)
from omnibase_core.models.nodes.compliance_evidence.model_evidence_check_detail import (
    ModelEvidenceCheckDetail,
)
from omnibase_core.models.nodes.compliance_evidence.model_evidence_report_state import (
    ModelEvidenceReportState,
)
from omnibase_core.nodes.node_compliance_evidence_effect.handler import (
    NodeComplianceEvidenceEffect,
    NoOpCompletionEventBus,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_report() -> ModelEvidenceReportState:
    """Build a representative compliance report for testing."""
    return ModelEvidenceReportState(
        total=5,
        passed=4,
        failed=1,
        run_id="test-run-001",
        repo_root="/tmp/test-repo",
        scan_started_at="2026-03-30T12:00:00+00:00",
        results=[
            ModelEvidenceCheckDetail(
                node_id="node_alpha",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelEvidenceCheckDetail(
                node_id="node_beta",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelEvidenceCheckDetail(
                node_id="node_gamma",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelEvidenceCheckDetail(
                node_id="node_delta",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelEvidenceCheckDetail(
                node_id="node_epsilon",
                passed=False,
                checks=[
                    ModelComplianceCheckEntry(name="handler_resolution", passed=False)
                ],
            ),
        ],
    )


def test_evidence_writes_report_to_disk(
    tmp_path: Path,
    sample_report: ModelEvidenceReportState,
) -> None:
    """Effect node writes compliance report with correct structure."""
    handler = NodeComplianceEvidenceEffect(state_root=tmp_path)
    run_path = handler.execute(sample_report)

    # Latest alias exists and has correct content
    latest_path = tmp_path / "compliance" / "report.yaml"
    assert latest_path.exists()
    loaded = yaml.safe_load(latest_path.read_text())
    assert loaded["total"] == 5
    assert loaded["passed"] == 4
    assert loaded["failed"] == 1
    assert loaded["run_id"] == "test-run-001"
    assert loaded["repo_root"] == "/tmp/test-repo"
    assert loaded["timestamp"] == "2026-03-30T12:00:00+00:00"
    assert len(loaded["results"]) == 5

    # Run-specific durable copy exists
    assert run_path.exists()
    assert run_path == tmp_path / "compliance" / "runs" / "test-run-001.yaml"
    run_loaded = yaml.safe_load(run_path.read_text())
    assert run_loaded == loaded

    # Per-node details are present
    failing_node = next(r for r in loaded["results"] if r["node_id"] == "node_epsilon")
    assert failing_node["passed"] is False
    assert failing_node["checks"][0]["name"] == "handler_resolution"


class _RecordingBus:
    """Real observable stub — records every publish call (anti-MagicMock)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        self.calls.append((topic, payload))


def test_default_event_bus_is_no_op_stub_not_none(tmp_path: Path) -> None:
    """OMN-14634: the injectable_none_default violation is fixed — the
    default is a typed no-op stub instance, never a bare ``None``."""
    handler = NodeComplianceEvidenceEffect(state_root=tmp_path)
    assert handler._event_bus is not None
    assert isinstance(handler._event_bus, NoOpCompletionEventBus)


def test_injected_bus_publish_is_called_unconditionally(
    tmp_path: Path, sample_report: ModelEvidenceReportState
) -> None:
    """OMN-14634: the none_guard_publish_skip violation is fixed — publish()
    is invoked directly with no ``is not None`` guard around the call site.
    A real (non-None) bus must observe exactly one publish call."""
    bus = _RecordingBus()
    handler = NodeComplianceEvidenceEffect(
        state_root=tmp_path,
        event_bus=bus,
        completion_topic="onex.evt.core.compliance-scan-completed.v1",
    )
    handler.execute(sample_report)

    assert len(bus.calls) == 1
    topic, payload = bus.calls[0]
    assert topic == "onex.evt.core.compliance-scan-completed.v1"
    assert payload["total"] == 5
    assert payload["passed"] == 4
    assert payload["failed"] == 1


def test_explicit_none_event_bus_no_longer_silently_tolerated(
    tmp_path: Path, sample_report: ModelEvidenceReportState
) -> None:
    """OMN-14634 RED/GREEN discriminator for none_guard_publish_skip: with
    the ``is not None`` guard removed, explicitly passing ``event_bus=None``
    (misuse — omit the arg to get the no-op stub default) now fails loudly
    with AttributeError instead of being silently swallowed. Under the
    pre-fix guarded implementation this call did NOT raise (the guard
    caught it and logged-only) — this test is RED against that code and
    GREEN against the fixed handler, proving the guard is actually gone
    and not just cosmetically rewritten."""
    handler = NodeComplianceEvidenceEffect(
        state_root=tmp_path,
        event_bus=None,  # type: ignore[arg-type]
        completion_topic="onex.evt.core.compliance-scan-completed.v1",
    )
    with pytest.raises(AttributeError):
        handler.execute(sample_report)
