# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the compliance orchestrator node.

Unit test: orchestrator emits one check request per discovered contract.

.. versionadded:: OMN-7072
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.compliance_orchestrator.model_scan_request import (
    ModelScanRequest,
)
from omnibase_core.nodes.node_compliance_orchestrator.handler import (
    NodeComplianceOrchestrator,
)


def _create_minimal_contract(node_dir: Path, node_id: str) -> Path:
    """Create a minimal contract.yaml in a node directory."""
    node_path = node_dir / node_id
    node_path.mkdir(parents=True, exist_ok=True)
    contract = {
        "name": node_id,
        "node_type": "compute",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_version": {"major": 1, "minor": 0, "patch": 0},
        "description": f"Test contract for {node_id}",
    }
    contract_path = node_path / "contract.yaml"
    contract_path.write_text(yaml.dump(contract, default_flow_style=False))
    return contract_path


@pytest.mark.unit
class TestComplianceOrchestrator:
    """Unit tests for NodeComplianceOrchestrator."""

    def test_orchestrator_fans_out_per_contract(self, tmp_path: Path) -> None:
        """Orchestrator emits one check request per discovered contract."""
        nodes_dir = tmp_path / "nodes"
        _create_minimal_contract(nodes_dir, "node_alpha")
        _create_minimal_contract(nodes_dir, "node_beta")
        _create_minimal_contract(nodes_dir, "node_gamma")

        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir=str(tmp_path))
        result = handler.handle(request)

        assert result.contracts_discovered == 3
        assert len(result.intents) == 3

        node_ids = {intent.node_id for intent in result.intents}
        assert node_ids == {"node_alpha", "node_beta", "node_gamma"}

        for intent in result.intents:
            assert intent.run_id == result.run_id
            assert intent.contract_path.endswith("contract.yaml")

    def test_orchestrator_empty_directory(self, tmp_path: Path) -> None:
        """Orchestrator handles empty directory gracefully."""
        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir=str(tmp_path))
        result = handler.handle(request)

        assert result.contracts_discovered == 0
        assert len(result.intents) == 0

    def test_orchestrator_nonexistent_directory(self) -> None:
        """Orchestrator handles nonexistent directory gracefully."""
        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir="/nonexistent/path")
        result = handler.handle(request)

        assert result.contracts_discovered == 0
        assert len(result.intents) == 0

    def test_orchestrator_preserves_run_id(self, tmp_path: Path) -> None:
        """Orchestrator preserves the provided run_id across all intents."""
        nodes_dir = tmp_path / "nodes"
        _create_minimal_contract(nodes_dir, "node_test")

        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir=str(tmp_path), run_id="test-run-42")
        result = handler.handle(request)

        assert result.run_id == "test-run-42"
        assert result.intents[0].run_id == "test-run-42"

    def test_orchestrator_generates_run_id_when_missing(self, tmp_path: Path) -> None:
        """Orchestrator generates a UUID run_id when none is provided."""
        nodes_dir = tmp_path / "nodes"
        _create_minimal_contract(nodes_dir, "node_test")

        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir=str(tmp_path))
        result = handler.handle(request)

        assert result.run_id != ""
        assert len(result.run_id) > 0


@pytest.mark.unit
class TestComplianceWorkflowE2E:
    """End-to-end test: 3 contracts -> orchestrator -> check intents."""

    def test_three_contracts_full_workflow(self, tmp_path: Path) -> None:
        """3 minimal contracts -> orchestrator -> correct fan-out intents."""
        nodes_dir = tmp_path / "src" / "pkg" / "nodes"
        contract_a = _create_minimal_contract(nodes_dir, "node_a")
        contract_b = _create_minimal_contract(nodes_dir, "node_b")
        contract_c = _create_minimal_contract(nodes_dir, "node_c")

        handler = NodeComplianceOrchestrator()
        request = ModelScanRequest(target_dir=str(tmp_path))
        result = handler.handle(request)

        # All 3 contracts discovered
        assert result.contracts_discovered == 3

        # One intent per contract
        assert len(result.intents) == 3

        # Each intent has correct contract path
        intent_paths = {intent.contract_path for intent in result.intents}
        assert str(contract_a) in intent_paths
        assert str(contract_b) in intent_paths
        assert str(contract_c) in intent_paths

        # Run ID is consistent across all intents
        run_ids = {intent.run_id for intent in result.intents}
        assert len(run_ids) == 1
        assert result.run_id in run_ids

        # Workflow contract exists and declares all 4 nodes
        workflow_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "omnibase_core"
            / "workflows"
            / "compliance_workflow.yaml"
        )
        assert workflow_path.exists(), f"Workflow contract not found: {workflow_path}"
        workflow = yaml.safe_load(workflow_path.read_text())
        assert workflow["workflow_id"] == "compliance_scan"
        assert len(workflow["nodes"]) == 4
        assert (
            workflow["terminal_event"] == "onex.evt.core.compliance-scan-completed.v1"
        )
