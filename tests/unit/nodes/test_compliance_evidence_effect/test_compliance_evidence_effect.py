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

from omnibase_core.models.nodes.compliance_evidence.model_compliance_check_detail import (
    ModelComplianceCheckDetail,
)
from omnibase_core.models.nodes.compliance_evidence.model_compliance_check_entry import (
    ModelComplianceCheckEntry,
)
from omnibase_core.models.nodes.compliance_evidence.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.nodes.node_compliance_evidence_effect.handler import (
    NodeComplianceEvidenceEffect,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_report() -> ModelComplianceReportState:
    """Build a representative compliance report for testing."""
    return ModelComplianceReportState(
        total=5,
        passed=4,
        failed=1,
        run_id="test-run-001",
        repo_root="/tmp/test-repo",
        scan_started_at="2026-03-30T12:00:00+00:00",
        results=[
            ModelComplianceCheckDetail(
                node_id="node_alpha",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelComplianceCheckDetail(
                node_id="node_beta",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelComplianceCheckDetail(
                node_id="node_gamma",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelComplianceCheckDetail(
                node_id="node_delta",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelComplianceCheckDetail(
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
    sample_report: ModelComplianceReportState,
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
