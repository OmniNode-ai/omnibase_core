# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-io-outside-effects CLI runtime (OMN-14694 / OMN-14662).

Covers both invocation modes: pre-commit's explicit-filenames mode (node-dir
context resolved at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoIoOutsideEffectsCheckCompute`` handler. The full-tree RED case is the
end-to-end mirror of the handler-level RED proof: a real on-disk non-EFFECT
package whose module does I/O exits non-zero, while an EFFECT package with the
same I/O exits zero.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check import (
    main,
)

pytestmark = pytest.mark.unit


def _contract(archetype: str) -> str:
    return (
        f"name: node_x\nnode_type: {archetype}\n"
        f"descriptor:\n  node_archetype: {archetype}\n"
    )


_ORCHESTRATOR_CONTRACT = _contract("orchestrator")
_COMPUTE_CONTRACT = _contract("compute")
_EFFECT_CONTRACT = _contract("effect")
# A GitPython invocation — one of the genuinely-new surfaces the DB-only seed
# never detected. Single forbidden surface, so exactly one finding.
_GIT_HANDLER = (
    "import git\n\n\ndef clone(url):\n    return git.Repo.clone_from(url, '.')\n"
)
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


def test_filenames_mode_non_effect_io_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(
        tmp_path, "node_x_orchestrator", _ORCHESTRATOR_CONTRACT, _GIT_HANDLER
    )

    # pre-commit stages only the handler; the CLI resolves the sibling contract.
    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 I/O-outside-EFFECT violation(s)" in out
    assert "git invocation" in out


def test_filenames_mode_effect_io_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(tmp_path, "node_x_effect", _EFFECT_CONTRACT, _GIT_HANDLER)

    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No forbidden I/O found in non-EFFECT node packages" in out


def test_filenames_mode_clean_non_effect_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    node_dir = _make_node(tmp_path, "node_x_compute", _COMPUTE_CONTRACT, _CLEAN_HANDLER)

    exit_code = main([str(node_dir / "handler.py")])

    assert exit_code == 0


def test_filenames_mode_file_outside_node_package_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A staged .py whose directory has no contract.yaml is not a node package."""
    loose = tmp_path / "adhoc.py"
    loose.write_text(_GIT_HANDLER)

    exit_code = main([str(loose)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No forbidden I/O found in non-EFFECT node packages" in out


def test_filenames_mode_contract_flip_to_non_effect_detected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Staging only the contract.yaml (e.g. an effect node flipped to compute)
    still pulls in the sibling handler and flags it."""
    node_dir = _make_node(tmp_path, "node_x", _COMPUTE_CONTRACT, _GIT_HANDLER)

    exit_code = main([str(node_dir / "contract.yaml")])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 I/O-outside-EFFECT violation(s)" in out


# =============================================================================
# full-tree walk mode
# =============================================================================


def test_full_tree_mode_flags_non_effect_io(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    _make_node(
        src / "nodes", "node_bad_orchestrator", _ORCHESTRATOR_CONTRACT, _GIT_HANDLER
    )
    _make_node(src / "nodes", "node_ok_effect", _EFFECT_CONTRACT, _GIT_HANDLER)

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 I/O-outside-EFFECT violation(s)" in out
    assert "node_bad_orchestrator/handler.py" in out
    # The EFFECT package with the identical git invocation is NOT reported.
    assert "node_ok_effect" not in out


def test_full_tree_mode_clean_tree_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    _make_node(src / "nodes", "node_x_compute", _COMPUTE_CONTRACT, _CLEAN_HANDLER)

    exit_code = main(["--root", str(src)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: No forbidden I/O found in non-EFFECT node packages" in out


def test_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    exit_code = main(["--root", str(empty)])

    assert exit_code == 0
