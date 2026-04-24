# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for validate_pr_deploy_required.py (OMN-9685).

Covers:
- Enum/model/protocol-only diffs do NOT trigger the gate
- Runtime diffs (nodes, handlers, runtime kernel) DO trigger the gate
- skip-token in PR body is NOT a bypass (gate still fires)
- Real dod_evidence with deploy check_value → gate passes
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validation.validate_pr_deploy_required import (
    find_runtime_paths,
    validate_pr_deploy_gate,
)

# ---------------------------------------------------------------------------
# find_runtime_paths — unit tests for pattern matching
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindRuntimePaths:
    def test_enum_only_diff_not_matched(self) -> None:
        files = [
            "src/omnibase_core/enums/enum_node_kind.py",
            "src/omnibase_core/enums/enum_hook_bit.py",
        ]
        assert find_runtime_paths(files) == []

    def test_model_only_diff_not_matched(self) -> None:
        files = [
            "src/omnibase_core/models/model_event_envelope.py",
            "src/omnibase_core/models/core/model_deployment_topology.py",
        ]
        assert find_runtime_paths(files) == []

    def test_protocol_only_diff_not_matched(self) -> None:
        files = [
            "src/omnibase_core/protocols/protocol_event_bus.py",
            "src/omnibase_spi/protocols/protocol_logger.py",
        ]
        assert find_runtime_paths(files) == []

    def test_dto_only_diff_not_matched(self) -> None:
        files = [
            "src/omnibase_compat/dto/dto_event_wire.py",
        ]
        assert find_runtime_paths(files) == []

    def test_tests_not_matched(self) -> None:
        files = [
            "tests/unit/models/test_model_foo.py",
            "tests/integration/test_service_bar.py",
        ]
        assert find_runtime_paths(files) == []

    def test_docs_not_matched(self) -> None:
        files = [
            "docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md",
            "README.md",
        ]
        assert find_runtime_paths(files) == []

    def test_node_handler_matched(self) -> None:
        files = ["src/omnibase_core/nodes/node_merge_sweep/handlers/handler_merge.py"]
        hits = find_runtime_paths(files)
        assert len(hits) == 1
        assert hits[0] == files[0]

    def test_runtime_kernel_matched(self) -> None:
        files = ["src/omnibase_infra/runtime/service_kernel.py"]
        hits = find_runtime_paths(files)
        assert len(hits) == 1

    def test_docker_file_matched(self) -> None:
        assert find_runtime_paths(["docker/Dockerfile.runtime"]) != []

    def test_contract_yaml_matched(self) -> None:
        files = ["src/omnibase_core/nodes/node_x/contract.yaml"]
        hits = find_runtime_paths(files)
        assert len(hits) == 1

    def test_cli_file_matched(self) -> None:
        files = ["src/omnibase_core/cli/cli_commands.py"]
        hits = find_runtime_paths(files)
        assert len(hits) == 1

    def test_services_file_matched(self) -> None:
        files = ["src/omnibase_core/services/service_handler_registry.py"]
        hits = find_runtime_paths(files)
        assert len(hits) == 1

    def test_mixed_diff_returns_only_runtime_hits(self) -> None:
        files = [
            "src/omnibase_core/enums/enum_node_kind.py",
            "src/omnibase_core/nodes/node_x/handlers/handler_x.py",
        ]
        hits = find_runtime_paths(files)
        assert len(hits) == 1
        assert "handler" in hits[0]


# ---------------------------------------------------------------------------
# validate_pr_deploy_gate — integration tests using tmp contracts dir
# ---------------------------------------------------------------------------


def _write_contract(contracts_dir: Path, ticket_id: str, has_deploy: bool) -> None:
    data: dict = {"dod_evidence": []}
    if has_deploy:
        data["dod_evidence"] = [
            {"checks": [{"check_value": "deploy omnibase_core to .201"}]}
        ]
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.dump(data))


@pytest.mark.unit
class TestValidatePrDeployGate:
    def test_enum_only_diff_gate_skipped(self, tmp_path: Path) -> None:
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/enums/enum_node_kind.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert result.passed
        assert result.skipped

    def test_model_only_diff_gate_skipped(self, tmp_path: Path) -> None:
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/models/model_event_envelope.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert result.passed
        assert result.skipped

    def test_protocol_only_diff_gate_skipped(self, tmp_path: Path) -> None:
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/protocols/protocol_event_bus.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert result.passed
        assert result.skipped

    def test_runtime_diff_without_dod_fails(self, tmp_path: Path) -> None:
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert not result.passed
        assert "DEPLOY GATE FAILED" in result.message

    def test_skip_token_in_body_does_not_bypass(self, tmp_path: Path) -> None:
        """skip-deploy-gate token must NOT be a bypass (OMN-9685 Bug 2)."""
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="[skip-deploy-gate: emergency hotfix] Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert not result.passed
        assert "DEPLOY GATE FAILED" in result.message

    def test_real_deploy_evidence_passes(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "OMN-9000", has_deploy=True)
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert result.passed
        assert not result.skipped
        assert "DEPLOY GATE PASSED" in result.message

    def test_ticket_without_deploy_evidence_fails(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "OMN-9000", has_deploy=False)
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert not result.passed
        assert "DEPLOY GATE FAILED" in result.message
        assert "OMN-9000" in result.message

    def test_error_message_does_not_suggest_skip_token(self, tmp_path: Path) -> None:
        """Error message must not teach the skip-token bypass (OMN-9685 Bug 2)."""
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="Closes OMN-9000",
            contracts_dir=tmp_path,
        )
        assert not result.passed
        assert "skip-deploy-gate" not in result.message

    def test_no_ticket_cited_fails(self, tmp_path: Path) -> None:
        result = validate_pr_deploy_gate(
            changed_files=["src/omnibase_core/nodes/node_x/handlers/handler_x.py"],
            pr_body="Fix the thing without a ticket reference",
            contracts_dir=tmp_path,
        )
        assert not result.passed
        assert "cites no OMN-XXXX ticket" in result.message
