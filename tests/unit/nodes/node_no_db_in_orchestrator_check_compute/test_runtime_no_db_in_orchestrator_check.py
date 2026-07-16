# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-db-in-orchestrator CLI runtime (OMN-14694, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (node-dir
context resolved at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoDbInOrchestratorCheckCompute`` handler. The full-tree RED case is the
end-to-end mirror of the handler-level RED proof: a real on-disk orchestrator
package whose handler imports a DB driver exits non-zero, while a COMPUTE
package with the same import exits zero.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_db_in_orchestrator_check_compute.runtime_no_db_in_orchestrator_check import (
    main,
)

pytestmark = pytest.mark.unit

_ORCHESTRATOR_CONTRACT = (
    "name: node_x\n"
    "node_type: orchestrator\n"
    "descriptor:\n"
    "  node_archetype: orchestrator\n"
)
_COMPUTE_CONTRACT = (
    "name: node_x\nnode_type: compute\ndescriptor:\n  node_archetype: compute\n"
)
_DB_HANDLER = "import sqlite3\n\n\ndef run(path):\n    return sqlite3.connect(path)\n"
_CLEAN_HANDLER = "def run(intents):\n    return intents\n"


def _make_node(base: Path, name: str, contract: str, handler: str) -> Path:
    node_dir = base / name
    node_dir.mkdir(parents=True)
    (node_dir / "contract.yaml").write_text(contract)
    (node_dir / "handler.py").write_text(handler)
    return node_dir


# =============================================================================
# pre-commit (explicit filenames) mode
# =============================================================================


def test_filenames_mode_orchestrator_db_io_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(
        tmp_path, "node_x_orchestrator", _ORCHESTRATOR_CONTRACT, _DB_HANDLER
    )

    # pre-commit stages only the handler; the CLI resolves the sibling contract.
    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 database-access violation(s)" in out
    assert "DB access in ORCHESTRATOR node" in out


def test_filenames_mode_compute_db_io_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(tmp_path, "node_x_compute", _COMPUTE_CONTRACT, _DB_HANDLER)

    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No database I/O found in ORCHESTRATOR node packages" in out


def test_filenames_mode_clean_orchestrator_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(
        tmp_path, "node_x_orchestrator", _ORCHESTRATOR_CONTRACT, _CLEAN_HANDLER
    )

    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 0


def test_filenames_mode_file_outside_node_package_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A staged .py whose directory has no contract.yaml is not a node package."""
    loose = tmp_path / "adhoc.py"
    loose.write_text(_DB_HANDLER)

    exit_code = main([str(loose)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No database I/O found in ORCHESTRATOR node packages" in out


def test_filenames_mode_contract_flip_to_orchestrator_detected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Staging only the contract.yaml (e.g. a compute node flipped to
    orchestrator) still pulls in the sibling handler and flags it."""
    node_dir = _make_node(tmp_path, "node_x", _ORCHESTRATOR_CONTRACT, _DB_HANDLER)

    exit_code = main([str(node_dir / "contract.yaml")])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 database-access violation(s)" in out


# =============================================================================
# full-tree walk mode
# =============================================================================


def test_full_tree_mode_flags_orchestrator_db_io(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    _make_node(
        src / "nodes", "node_bad_orchestrator", _ORCHESTRATOR_CONTRACT, _DB_HANDLER
    )
    _make_node(src / "nodes", "node_ok_compute", _COMPUTE_CONTRACT, _DB_HANDLER)

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 database-access violation(s)" in out
    assert "node_bad_orchestrator/handler.py" in out
    # The compute package with the identical DB import is NOT reported.
    assert "node_ok_compute" not in out


def test_full_tree_mode_clean_tree_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    _make_node(
        src / "nodes", "node_x_orchestrator", _ORCHESTRATOR_CONTRACT, _CLEAN_HANDLER
    )

    exit_code = main(["--root", str(src)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No database I/O found in ORCHESTRATOR node packages" in out


def test_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    exit_code = main(["--root", str(empty)])

    assert exit_code == 0
