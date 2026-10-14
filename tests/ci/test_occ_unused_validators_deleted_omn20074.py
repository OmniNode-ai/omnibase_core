# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: the change-control validators and CLIs no workflow calls are gone.

``validator_evidence_commit_binding`` (with its CLI) and ``validator_receipt_gate_cli``
were invoked only by the hosted ``receipt-gate.yml`` and ``occ-preflight.yml``
reusables. Once those reusables stopped calling them, nothing in any canonical
clone imported or ran them. ``validator_receipt_gate`` and
``validator_occ_merge_eligibility`` stay: other repositories import them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

_DELETED = (
    "src/omnibase_core/validation/validator_evidence_commit_binding.py",
    "src/omnibase_core/validation/validator_evidence_commit_binding_cli.py",
    "src/omnibase_core/validation/validator_receipt_gate_cli.py",
    "tests/unit/validation/test_evidence_commit_binding.py",
    "tests/unit/validation/test_receipt_gate_cli.py",
)

_KEPT = (
    "src/omnibase_core/validation/validator_receipt_gate.py",
    "src/omnibase_core/validation/validator_occ_merge_eligibility.py",
)

_REGISTRIES = (
    ".onex_ratchets/canonical_file_shape_baseline.txt",
    "tests/fixtures/validator_parity/ai_slop/ci_scope.json",
    "pyproject.toml",
)


@pytest.mark.parametrize("rel", _DELETED)
def test_validator_is_deleted(rel: str) -> None:
    assert not (REPO_ROOT / rel).exists()


@pytest.mark.parametrize("rel", _KEPT)
def test_validator_with_outside_importers_is_kept(rel: str) -> None:
    assert (REPO_ROOT / rel).is_file()


def test_no_registry_names_a_deleted_validator() -> None:
    named_in = [
        (reg, rel)
        for reg in _REGISTRIES
        for rel in _DELETED
        if rel in (REPO_ROOT / reg).read_text(encoding="utf-8")
    ]
    assert named_in == []


def test_registries_still_name_a_kept_validator() -> None:
    """Positive control: the registry scan above can find a validator path at all."""
    baseline = (REPO_ROOT / _REGISTRIES[0]).read_text(encoding="utf-8")
    assert _KEPT[0] in baseline
