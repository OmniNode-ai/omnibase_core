# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: configuration and scripts that still named onex_change_control are gone.

Covers the live references left after the S9 deploy-gate deletion that no
reusable-workflow caller needs: the downstream pin-bump manifest entry, the
config-propagation targets, the validator-requirements repo registry, the
boundary-parity repo list, the CodeQL required-check ref, and the receipt-gate
CLI wrapper script nothing invokes. The receipt-gate and occ-preflight
reusables stay hosted because ``@main`` callers outside this repository still
use them (see ``test_occ_unused_reusables_deleted_omn20074``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
_OCC = "onex_change_control"

_NO_OCC_FILES = (
    "docs/downstream-repos.yaml",
    ".github/propagation-targets.yaml",
    "architecture-handshakes/validator-requirements.yaml",
    ".github/required-checks.yaml",
)

_DELETED_SCRIPT = "scripts/validation/validate_pr_receipts.py"


def _live_lines(rel: str) -> list[str]:
    """Non-comment lines of ``rel`` that name onex_change_control, rationale text excluded."""
    return [
        line.strip()
        for line in (REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()
        if _OCC in line and not line.lstrip().startswith("#")
    ]


@pytest.mark.parametrize(
    "rel", ["docs/downstream-repos.yaml", ".github/propagation-targets.yaml"]
)
def test_manifests_declare_no_change_control_repo(rel: str) -> None:
    assert _live_lines(rel) == []


def test_validator_requirements_registry_lists_no_change_control_repo() -> None:
    spec = yaml.safe_load(
        (REPO_ROOT / "architecture-handshakes/validator-requirements.yaml").read_text(
            encoding="utf-8"
        )
    )

    def _walk(node: object) -> list[str]:
        if isinstance(node, str):
            return [node] if node == _OCC else []
        if isinstance(node, dict):
            return [hit for v in node.values() for hit in _walk(v)]
        if isinstance(node, list):
            return [hit for v in node for hit in _walk(v)]
        return []

    assert _walk(spec) == []


def test_required_checks_has_no_cross_repo_ref_into_change_control() -> None:
    entries = yaml.safe_load(
        (REPO_ROOT / ".github/required-checks.yaml").read_text(encoding="utf-8")
    )
    gates = entries["gates"]
    with_ref = [e for e in gates if e.get("cross_repo_ref")]
    assert with_ref, "positive control: the manifest declares cross_repo_ref gates"
    refs = [e["cross_repo_ref"] for e in with_ref if _OCC in e["cross_repo_ref"]]
    assert refs == []


def test_receipt_gate_cli_wrapper_script_is_deleted() -> None:
    assert not (REPO_ROOT / _DELETED_SCRIPT).exists()
    named_in = [
        rel
        for rel in (
            ".onex_ratchets/canonical_file_shape_baseline.txt",
            "tests/fixtures/validator_parity/ai_slop/ci_scope.json",
            "pyproject.toml",
        )
        if _DELETED_SCRIPT in (REPO_ROOT / rel).read_text(encoding="utf-8")
    ]
    assert named_in == []
