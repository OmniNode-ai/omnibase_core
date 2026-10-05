# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Characterization tests for the OMN-20559 ratchet burn-down.

These pin the verdict of every gate the burn-down touches, on the real tree and
on a planted violation, through the entry point that survives the burn-down.
They are committed and proven green on the unchanged code first, and they must
pass unchanged after each baseline is emptied and its ratchet becomes a plain
check. That is the idempotency proof: removing an empty exemption surface must
not change what any gate accepts or refuses.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import scripts.ci.canonical_handler_shape as shape
import scripts.ci.rsd_provenance_stamp as stamp
from omnibase_core.validation.validator_runtime_profiles import (
    RULE_RUNTIME_PROFILES_MISSING,
    ValidatorRuntimeProfiles,
)
from omnibase_core.validation.validator_url_authority import scan_tree

REPO_ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.unit


def _pin_module_scope(monkeypatch: pytest.MonkeyPatch, module: object) -> None:
    """Snapshot the scope globals ``main()`` rewrites, so teardown restores them."""
    for name in (
        "PACKAGE",
        "SRC_ROOT",
        "NODES_GLOB",
        "BASELINE_PATH",
        "RECEIPTS_DIR",
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, getattr(module, name))


def _plant_bare_node(src_root: Path, node_name: str) -> Path:
    """A node with a contract and no handler: non-canonical and unstamped."""
    node = src_root / "omnibase_core" / "nodes" / node_name
    node.mkdir(parents=True)
    (node / "__init__.py").write_text("", encoding="utf-8")
    contract = node / "contract.yaml"
    contract.write_text(f"name: {node_name}\n", encoding="utf-8")
    return contract


# --------------------------------------------------------------------------- #
# Canonical handler-shape gate (OMN-14355)
# --------------------------------------------------------------------------- #


def test_handler_shape_real_tree_is_all_canonical() -> None:
    findings = shape.classify_all()
    assert findings, "positive control: the scan must see core's nodes"
    assert shape.current_non_canonical(findings) == []


def test_handler_shape_full_scan_passes_on_real_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_module_scope(monkeypatch, shape)
    assert shape.main(["--scope", "full"]) == 0


def test_handler_shape_planted_non_canonical_node_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pin_module_scope(monkeypatch, shape)
    _plant_bare_node(tmp_path, "node_planted_noncanonical")
    rc = shape.main(
        ["--scope", "full", "--package", "omnibase_core", "--src-root", str(tmp_path)]
    )
    assert rc == 1


# --------------------------------------------------------------------------- #
# RSD provenance-stamp gate (OMN-15011)
# --------------------------------------------------------------------------- #


def test_provenance_real_tree_has_no_unstamped_node() -> None:
    findings = stamp.classify_all()
    assert findings, "positive control: the scan must see core's nodes"
    assert stamp.current_unstamped(findings) == []


def test_provenance_gate_passes_on_real_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_module_scope(monkeypatch, stamp)
    assert stamp.main([]) == 0


def test_provenance_planted_unstamped_node_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pin_module_scope(monkeypatch, stamp)
    _plant_bare_node(tmp_path, "node_planted_unstamped")
    rc = stamp.main(["--package", "omnibase_core", "--src-root", str(tmp_path)])
    assert rc == 1


# --------------------------------------------------------------------------- #
# Transport-import gate (OMN-220)
# --------------------------------------------------------------------------- #


def _run_transport(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check_transport_imports.py", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_transport_imports_pass_on_real_tree() -> None:
    result = _run_transport()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Total violations: 0" in result.stdout


def test_transport_imports_planted_violation_fails(tmp_path: Path) -> None:
    (tmp_path / "planted_transport.py").write_text("import httpx\n", encoding="utf-8")
    result = _run_transport("--src-dir", str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "httpx" in result.stdout


# --------------------------------------------------------------------------- #
# Runtime-profiles validator (OMN-9886), default construction
# --------------------------------------------------------------------------- #


def _orphan_command_consumer(tmp_path: Path) -> Path:
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "name": "node_planted_orphan_orchestrator",
                "node_type": "orchestrator",
                "event_bus": {"subscribe_topics": ["onex.cmd.planted.start.v1"]},
            }
        ),
        encoding="utf-8",
    )
    return contract


def test_runtime_profiles_default_validator_blocks_planted_orphan(
    tmp_path: Path,
) -> None:
    validator = ValidatorRuntimeProfiles()
    contract = _orphan_command_consumer(tmp_path)
    issues = validator._validate_file(contract, validator.contract)
    assert [issue.code for issue in issues] == [RULE_RUNTIME_PROFILES_MISSING]


def test_runtime_profiles_cli_passes_on_real_tree() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_runtime_profiles",
            "src/",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# URL-authority gate (OMN-12803), omnibase_core's own findings
# --------------------------------------------------------------------------- #

# Every url-authority finding the scan reports for omnibase_core today, as
# (rule, path). The burn-down removes baseline entries only; it must not change
# what the scanner itself finds.
_CORE_URL_AUTHORITY_FINDINGS = {
    (
        "url-const-assignment",
        "examples/demo/handlers/support_assistant/handler_anthropic.py",
    ),
    ("env-url-read", "examples/demo/handlers/support_assistant/handler_local.py"),
    (
        "url-const-assignment",
        "examples/demo/handlers/support_assistant/handler_openai.py",
    ),
    (
        "public-https-literal",
        "examples/demo/handlers/support_assistant/handler_openai.py",
    ),
    ("public-https-literal", "scripts/emit_ts_types.py"),
    ("public-https-literal", "src/omnibase_core/doctor/checks/check_linear.py"),
}


def test_url_authority_scan_of_core_is_pinned() -> None:
    found = {(v.rule, v.path) for v in scan_tree("omnibase_core", REPO_ROOT)}
    assert found == _CORE_URL_AUTHORITY_FINDINGS


def test_url_authority_gate_passes_on_real_tree() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_url_authority",
            "--repo",
            "omnibase_core",
            "--repo-root",
            ".",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
