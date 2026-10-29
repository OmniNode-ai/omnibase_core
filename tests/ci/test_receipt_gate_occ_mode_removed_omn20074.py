# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: omnibase_core carries no change-control evidence mode.

The receipt-gate reusable runs caller evidence only: contracts/<OMN-N>.yaml at
the caller's own pull request head. The change-control evidence mode, the
occ-preflight reusable, its bounded-wait probe, the companion-merged gate, the
evidence-root resolver that pointed into the change-control clone, the CLI
defaults that named that clone and the boundary analyzer's registry entry for
it are gone. Positive controls keep each check from passing on an empty or
unreadable input.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_GATE = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
OCC_NAME = "onex_change_control"

REMOVED_PATHS = (
    ".github/workflows/occ-preflight.yml",
    "scripts/ci/occ_preflight_wait.py",
    "scripts/ci/check_occ_companion_merged.py",
)

CALLER_INPUTS = {
    "evidence-source",
    "verifier-version",
    "compare-with-occ",
    "shadow",
    "check-timeout-seconds",
}

CLI_MODULES = (
    "src/omnibase_core/nodes/node_receipt_reprobe_check_compute/runtime_receipt_reprobe_check.py",
    "src/omnibase_core/nodes/node_receipt_honesty_check_compute/runtime_receipt_honesty_check.py",
)


def _receipt_gate() -> dict[str, Any]:
    loaded = yaml.safe_load(RECEIPT_GATE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _workflow_call_inputs(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML reads the bare `on:` key as the boolean True.
    on_block = workflow.get("on", workflow.get(True))
    assert isinstance(on_block, dict)
    inputs = on_block["workflow_call"]["inputs"]
    assert isinstance(inputs, dict)
    return inputs


@pytest.mark.parametrize("relpath", REMOVED_PATHS)
def test_change_control_gate_files_are_absent(relpath: str) -> None:
    assert not (REPO_ROOT / relpath).exists(), f"{relpath} must be deleted"


def test_receipt_gate_declares_only_caller_inputs() -> None:
    inputs = _workflow_call_inputs(_receipt_gate())
    assert set(inputs) == CALLER_INPUTS
    assert inputs["evidence-source"]["default"] == "caller"


def test_receipt_gate_states_its_single_mode_as_evidence_source_caller() -> None:
    # OMN-17427: the queue-status `occ refs` reader treats a workflow file named
    # for the receipt gate as live change-control use unless the file itself
    # sets `evidence-source: caller`. The reusable accepts that one mode only, so
    # it says so in its own header, where the reader (and a caller's author)
    # finds it.
    text = RECEIPT_GATE.read_text(encoding="utf-8")
    assert re.search(r"evidence-source\s*:\s*[\"']?caller\b", text), (
        "receipt-gate.yml must state `evidence-source: caller` as its only mode"
    )
    # Negative control: the reader's pattern does not match a line that only
    # says the value must be caller.
    assert not re.search(
        r"evidence-source\s*:\s*[\"']?caller\b", 'evidence-source: must be "caller"'
    )


def test_receipt_gate_names_no_change_control_checkout_or_probe() -> None:
    text = RECEIPT_GATE.read_text(encoding="utf-8")
    # Positive control: the caller-evidence verifier is still there.
    assert "omnimarket.nodes.node_dod_verify" in text
    for needle in (
        OCC_NAME,
        "occ_preflight_wait",
        "check_occ_companion_merged",
        "occ-preflight",
    ):
        assert needle not in text, f"receipt-gate.yml still names {needle!r}"


def test_receipt_gate_jobs_run_caller_evidence_only() -> None:
    jobs = _receipt_gate()["jobs"]
    assert set(jobs) == {"verify", "dod-verify"}
    dod_steps = [step.get("name", "") for step in jobs["dod-verify"]["steps"]]
    assert "Verify the contract at the PR head" in dod_steps
    assert not any("OCC's verdict" in name for name in dod_steps)
    # verify keeps its check-run name for callers that require it, and runs
    # nothing but a single success no-op.
    verify_steps = jobs["verify"]["steps"]
    assert len(verify_steps) == 1
    assert "uses" not in verify_steps[0]


def test_evidence_root_resolver_is_removed() -> None:
    import omnibase_core.utils as utils
    from omnibase_core.utils import util_omni_home_paths

    assert not hasattr(util_omni_home_paths, "resolve_evidence_root")
    assert "resolve_evidence_root" not in utils.__all__
    # Positive control: the sibling resolvers stay.
    assert callable(util_omni_home_paths.resolve_worktrees_root)
    source = Path(util_omni_home_paths.__file__).read_text(encoding="utf-8")
    assert OCC_NAME not in source


@pytest.mark.parametrize("relpath", CLI_MODULES)
def test_cli_defaults_name_no_change_control_clone(relpath: str) -> None:
    tree = ast.parse((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    defaults: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "add_argument"
        ):
            for kw in node.keywords:
                if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    if isinstance(kw.value.value, str):
                        defaults.append(kw.value.value)
    # Positive control: each CLI still declares a string path default.
    assert any(d.endswith("dod_receipts") for d in defaults), defaults
    assert not [d for d in defaults if OCC_NAME in d]


def test_boundary_analyzer_registry_drops_change_control() -> None:
    from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
        REGISTRY_PACKAGES,
    )

    assert "omnibase_core" in REGISTRY_PACKAGES
    assert OCC_NAME not in REGISTRY_PACKAGES


def test_environment_reader_inventory_drops_deleted_script() -> None:
    from omnibase_core.validators import environment_reader_inventory as inv

    source = Path(inv.__file__).read_text(encoding="utf-8")
    assert "scripts/ci/detect_test_paths.py" in source
    assert "scripts/ci/check_occ_companion_merged.py" not in source
