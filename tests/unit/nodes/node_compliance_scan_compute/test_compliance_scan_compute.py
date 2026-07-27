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


class TestSourceOnlyFlag:
    """source_only=True excludes contracts under .venv directories (OMN-9537)."""

    def test_source_only_excludes_venv_contracts(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        source_dir = tmp_path / "src" / "mypkg" / "nodes" / "node_real"
        source_dir.mkdir(parents=True)
        (source_dir / "contract.yaml").write_text(
            "node_id: node_real\nnode_kind: COMPUTE\n"
        )

        venv_dir = (
            tmp_path
            / ".venv"
            / "lib"
            / "python3.12"
            / "site-packages"
            / "some_dep"
            / "nodes"
            / "node_dep"
        )
        venv_dir.mkdir(parents=True)
        (venv_dir / "contract.yaml").write_text(
            "node_id: node_dep\nnode_kind: EFFECT\n"
        )

        results = scanner.scan(str(tmp_path), source_only=True)
        assert len(results) == 1
        assert results[0].node_id == "node_real"

    def test_source_only_false_includes_venv_contracts(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        source_dir = tmp_path / "src" / "node_real"
        source_dir.mkdir(parents=True)
        (source_dir / "contract.yaml").write_text(
            "node_id: node_real\nnode_kind: COMPUTE\n"
        )

        venv_dir = tmp_path / ".venv" / "lib" / "node_dep"
        venv_dir.mkdir(parents=True)
        (venv_dir / "contract.yaml").write_text(
            "node_id: node_dep\nnode_kind: EFFECT\n"
        )

        # Explicit source_only=False
        results = scanner.scan(str(tmp_path), source_only=False)
        assert len(results) == 2
        # No-arg call must also include .venv contracts (default=False is backwards-compat)
        results_default = scanner.scan(str(tmp_path))
        assert len(results_default) == 2

    def test_source_only_excludes_bare_venv_dir(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        source_dir = tmp_path / "src" / "node_real"
        source_dir.mkdir(parents=True)
        (source_dir / "contract.yaml").write_text(
            "node_id: node_real\nnode_kind: COMPUTE\n"
        )

        # "venv" (no dot) is also pruned
        venv_dir = tmp_path / "venv" / "lib" / "node_dep"
        venv_dir.mkdir(parents=True)
        (venv_dir / "contract.yaml").write_text(
            "node_id: node_dep\nnode_kind: EFFECT\n"
        )

        results = scanner.scan(str(tmp_path), source_only=True)
        assert len(results) == 1
        assert results[0].node_id == "node_real"


class TestOrChainFallbackPrecedence:
    """Behavioral proof for OMN-14634: the 3 or-chains that were rewritten as
    explicit if/elif precedence must keep IDENTICAL cascade behavior — same
    winner at every fallback depth, including when a higher-precedence field
    is present alongside a lower-precedence one (a bug here would silently
    pick the WRONG field, not crash — the RED case is "exists but wrong",
    not "absent").
    """

    def test_node_id_falls_back_to_handler_id_when_node_id_absent(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_x"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text("handler_id: my_handler\n")

        results = scanner.scan(str(tmp_path))
        assert results[0].node_id == "my_handler"

    def test_node_id_prefers_node_id_over_handler_id(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_y"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: canonical_id\nhandler_id: my_handler\n"
        )

        results = scanner.scan(str(tmp_path))
        assert results[0].node_id == "canonical_id"

    def test_node_id_falls_back_to_name_when_node_id_and_handler_id_absent(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_z"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text("name: friendly_name\n")

        results = scanner.scan(str(tmp_path))
        assert results[0].node_id == "friendly_name"

    def test_node_id_falls_back_to_directory_name_when_all_fields_absent(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_dirname_fallback"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text("description: no identifying fields\n")

        results = scanner.scan(str(tmp_path))
        assert results[0].node_id == "node_dirname_fallback"

    def test_node_kind_check_falls_back_to_node_type(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_k"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text("node_id: node_k\nnode_type: EFFECT\n")

        results = scanner.scan(str(tmp_path))
        check4 = next(c for c in results[0].checks if c.check_id == 4)
        assert check4.passed is True
        assert "EFFECT" in check4.message

    def test_node_kind_prefers_node_kind_over_node_type(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_k2"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_k2\nnode_kind: COMPUTE\nnode_type: EFFECT\n"
        )

        results = scanner.scan(str(tmp_path))
        check4 = next(c for c in results[0].checks if c.check_id == 4)
        assert check4.passed is True
        assert "COMPUTE" in check4.message
        assert "EFFECT" not in check4.message

    def test_config_readiness_missing_mapping_falls_back_to_name(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_cfg"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_cfg\n"
            "node_kind: COMPUTE\n"
            "config_requirements:\n"
            "  - name: MY_SETTING\n"
        )

        results = scanner.scan(str(tmp_path))
        check7 = next(c for c in results[0].checks if c.check_id == 7)
        assert check7.passed is False
        assert "MY_SETTING" in check7.message

    def test_config_readiness_prefers_key_over_name(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_cfg2"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_cfg2\n"
            "node_kind: COMPUTE\n"
            "config_requirements:\n"
            "  - key: MY_KEY\n"
            "    name: MY_SETTING\n"
        )

        results = scanner.scan(str(tmp_path))
        check7 = next(c for c in results[0].checks if c.check_id == 7)
        assert check7.passed is False
        assert "MY_KEY" in check7.message
        assert "MY_SETTING" not in check7.message

    def test_config_readiness_falls_back_to_str_item_when_no_key_or_name(
        self, scanner: NodeComplianceScanCompute, tmp_path: Path
    ) -> None:
        node_dir = tmp_path / "nodes" / "node_cfg3"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(
            "node_id: node_cfg3\n"
            "node_kind: COMPUTE\n"
            "config_requirements:\n"
            "  - description: unnamed requirement\n"
        )

        results = scanner.scan(str(tmp_path))
        check7 = next(c for c in results[0].checks if c.check_id == 7)
        assert check7.passed is False
        assert "unnamed requirement" in check7.message
