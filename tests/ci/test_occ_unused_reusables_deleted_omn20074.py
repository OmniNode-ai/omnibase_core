# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074 S9: the change-control deploy gate no caller uses is gone.

``deploy-gate-reusable.yml`` (relocated here from omniclaude), its
``.github/actions/deploy-gate`` action and
``scripts/deploy-gate/checkout-occ-contracts.sh`` checked out
onex_change_control contracts for a deploy gate. No repository calls this
reusable at its default branch: omnibase_core's own ``deploy-gate.yml`` and
every other deploy-gate caller use omniclaude's reusable and validator. The
reusables other repositories still call stay hosted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

_DELETED = (
    ".github/workflows/deploy-gate-reusable.yml",
    ".github/actions/deploy-gate",
    "scripts/deploy-gate/checkout-occ-contracts.sh",
    "tests/unit/validation/test_deploy_gate_sparse_checkout.py",
    "tests/unit/validation/test_deploy_gate_evidence_contract.py",
)

# OMN-20074 (AC47): occ_preflight_wait.py and check_occ_companion_merged.py
# are deleted with the change-control evidence mode; receipt-gate.yml stays.
_STILL_CALLED = (".github/workflows/receipt-gate.yml",)


def test_unused_deploy_gate_files_are_deleted() -> None:
    present = [rel for rel in _DELETED if (REPO_ROOT / rel).exists()]
    assert not present, present


def test_no_tracked_list_names_a_deleted_path() -> None:
    lists = (
        ".onex_ratchets/canonical_file_shape_baseline.txt",
        "tests/fixtures/validator_parity/ai_slop/ci_scope.json",
    )
    offenders = [
        f"{rel}: {gone}"
        for rel in lists
        for gone in _DELETED
        if gone in (REPO_ROOT / rel).read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_reusables_with_live_callers_stay_hosted() -> None:
    missing = [rel for rel in _STILL_CALLED if not (REPO_ROOT / rel).is_file()]
    assert not missing, missing
