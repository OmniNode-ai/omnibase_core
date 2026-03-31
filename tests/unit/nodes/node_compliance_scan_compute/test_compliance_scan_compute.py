# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeComplianceScanCompute.

Covers:
- Contract discovery (finds contract.yaml files)
- Handler importable passes
- Handler missing fails

Ticket: OMN-7069
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_compliance_scan_compute.handler import (
    NodeComplianceScanCompute,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def scanner() -> NodeComplianceScanCompute:
    return NodeComplianceScanCompute()


class TestComplianceScanFindsContracts:
    """Scanner discovers all contract.yaml files in a directory tree."""

    def test_finds_single_contract(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_test"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_test\nnode_kind: COMPUTE\n"
        )

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        assert results[0].node_id == "node_test"
        # Check 1 (contract parse) should pass
        assert results[0].checks[0].check_id == 1
        assert results[0].checks[0].passed is True

    def test_finds_multiple_contracts(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        for name in ["node_a", "node_b", "node_c"]:
            d = tmp_path / "nodes" / name
            d.mkdir(parents=True)
            (d / "contract.yaml").write_text(f"node_id: {name}\nnode_kind: COMPUTE\n")

        results = scanner.scan(str(tmp_path))
        assert len(results) == 3
        node_ids = {r.node_id for r in results}
        assert node_ids == {"node_a", "node_b", "node_c"}

    def test_empty_directory_returns_no_results(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        results = scanner.scan(str(tmp_path))
        assert results == []

    def test_invalid_yaml_fails_parse(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_bad"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text("{{invalid: yaml: [")

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].checks[0].check_id == 1
        assert results[0].checks[0].passed is False
        assert "YAML parse error" in results[0].checks[0].message


class TestHandlerImportable:
    """Check reports PASS when handler is importable."""

    def test_handler_importable_passes(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_test"
        node_dir.mkdir(parents=True)
        # Use a real importable module:class as the handler reference
        (node_dir / "contract.yaml").write_text(
            "node_id: node_test\n"
            "node_kind: COMPUTE\n"
            "handler_routing:\n"
            "  default_handler: os.path:join\n"
        )

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        # Check 2: handler resolution
        handler_check = results[0].checks[1]
        assert handler_check.check_id == 2
        assert handler_check.passed is True
        assert "importable" in handler_check.message


class TestHandlerMissingFails:
    """Check reports FAIL when handler is not importable."""

    def test_handler_missing_module_fails(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_test"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_test\n"
            "node_kind: COMPUTE\n"
            "handler_routing:\n"
            "  default_handler: nonexistent.module.path:SomeHandler\n"
        )

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        handler_check = results[0].checks[1]
        assert handler_check.check_id == 2
        assert handler_check.passed is False
        assert "Cannot import" in handler_check.message

    def test_handler_missing_attr_fails(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_test"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_test\n"
            "node_kind: COMPUTE\n"
            "handler_routing:\n"
            "  default_handler: os.path:NonExistentFunction\n"
        )

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        handler_check = results[0].checks[1]
        assert handler_check.check_id == 2
        assert handler_check.passed is False
        assert "not defined" in handler_check.message

    def test_all_eight_checks_present(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        """Every contract gets exactly 8 checks."""
        node_dir = tmp_path / "nodes" / "node_test"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_test\nnode_kind: COMPUTE\n"
        )

        results = scanner.scan(str(tmp_path))
        assert len(results) == 1
        assert len(results[0].checks) == 8
        check_ids = [c.check_id for c in results[0].checks]
        assert check_ids == [1, 2, 3, 4, 5, 6, 7, 8]
