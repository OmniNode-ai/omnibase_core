# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""omnibase_core requires ``repo-evidence / dod-verify`` on dev (OMN-21504, adopting OMN-21479).

The manifest row names the context the caller produces, and the caller pins the
same receipt-gate reusable (a dev-merge tag) and the same verifier version as
omnimarket's caller. The two values below are spelled here because a test cannot
read another repository's clone on every runner; they are omnimarket's
``call-repo-evidence-gate.yml`` ``uses:`` tag and ``verifier-version`` on its dev
branch (omnimarket fa159ce9), and the verifier floor of the reusable itself.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "call-repo-evidence-gate.yml"
MANIFEST_PATH = REPO_ROOT / ".github" / "required-checks.yaml"
RECEIPT_GATE_TAG = "dev-20261022114039-578228977721"
RECEIPT_GATE_USES = (
    f"OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@{RECEIPT_GATE_TAG}"
)
VERIFIER_VERSION = "0.4.305"
VERIFIER_FLOOR = (0, 4, 303)
CONTEXT = "repo-evidence / dod-verify"


def _caller_job() -> dict[str, Any]:
    return yaml.safe_load(CALLER_PATH.read_text())["jobs"]["repo-evidence"]


def _row() -> dict[str, Any]:
    gates = yaml.safe_load(MANIFEST_PATH.read_text())["gates"]
    rows = [gate for gate in gates if gate["name"] == CONTEXT]
    assert len(rows) == 1, f"expected exactly one {CONTEXT!r} row, found {len(rows)}"
    return rows[0]


def test_the_manifest_requires_the_context_on_dev() -> None:
    row = _row()
    assert row["mode"] == "REQUIRED"
    assert row["branch"] == "dev"
    assert row["skip_semantics"] == "never"


def test_the_row_names_the_caller_and_the_reusable_the_caller_pins() -> None:
    row = _row()
    assert row["caller_workflow"] == "call-repo-evidence-gate.yml"
    assert row["caller_job"] == "repo-evidence"
    assert row["cross_repo_ref"] == _caller_job()["uses"]


def test_the_caller_pins_omnimarkets_receipt_gate_by_dev_merge_tag() -> None:
    assert _caller_job()["uses"] == RECEIPT_GATE_USES
    assert re.fullmatch(r"dev-\d{14}-[0-9a-f]{12}", RECEIPT_GATE_TAG)


def test_the_caller_pins_omnimarkets_verifier_version_at_or_above_the_floor() -> None:
    version = _caller_job()["with"]["verifier-version"]
    assert version == VERIFIER_VERSION
    assert tuple(int(part) for part in version.split(".")) >= VERIFIER_FLOOR


def test_control_a_row_naming_another_context_does_not_satisfy_the_check() -> None:
    gates = yaml.safe_load(MANIFEST_PATH.read_text())["gates"]
    assert not [gate for gate in gates if gate["name"] == "repo-evidence / verify"]
