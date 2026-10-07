# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074 - the skip-token scan no longer carries a change-control preflight.

omniclaude#2540 (squash ``4358450cc`` on omniclaude ``dev``) removed the nested
``occ-preflight`` job from ``reject-deploy-gate-skip.yml`` and the ``needs:``
edge that held the token scan behind it; its own test,
``tests/ci/test_reject_skip_workflow_occ_independence.py``, proves the pinned
file runs the scan with no preflight. This repository adopts that by its own
pin bump, and the required-checks manifest and CI Summary audit stop naming
the nested context (``call-reject-skip-token / occ-preflight / eligibility``),
because nothing produces it any more. The token scan context stays declared,
and the change-control verdict stays enforced through the standalone
``occ-preflight / eligibility`` context until the cut-over. This caller's local
``occ-preflight`` job and the scan's ``needs: occ-preflight`` / ``if: always()``
stay unchanged; S6 part 2 deletes OCC callers.

The nested context is still required by branch protection on ``dev`` until the
S6 cut-over removes it, so this change lands with that ruleset change and not
before (plan S6, OMN-20068).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from tests.unit.scripts.ci.test_ci_summary_gate import DIRECT_REQUIRED_JOB_CONTEXTS

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER = REPO_ROOT / ".github" / "workflows" / "call-reject-skip.yml"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"
REUSABLE = "OmniNode-ai/omniclaude/.github/workflows/reject-deploy-gate-skip.yml"
# The squash commit of omniclaude#2540 on omniclaude dev, by its abbreviated
# sha; the pin itself must be the full 40-character sha.
PREFLIGHT_FREE_SHA_PREFIX = "4358450cc"
NESTED_PREFLIGHT = "call-reject-skip-token / occ-preflight / eligibility"
SCAN = "call-reject-skip-token / scan / reject-skip-gate-token"
STANDALONE_PREFLIGHT = "occ-preflight / eligibility"


def _caller_refs() -> list[str]:
    pattern = re.compile(rf"^\s*uses:\s*{re.escape(REUSABLE)}@(?P<ref>[^\s\"'#]+)")
    return [
        match["ref"]
        for line in CALLER.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
        for match in pattern.finditer(line)
    ]


def test_caller_pins_the_reusable_without_the_change_control_preflight() -> None:
    refs = _caller_refs()
    assert len(refs) == 1, refs
    assert re.fullmatch(r"[0-9a-f]{40}", refs[0]), refs
    assert refs[0].startswith(PREFLIGHT_FREE_SHA_PREFIX), refs


def test_required_checks_manifest_declares_no_nested_preflight_row() -> None:
    manifest = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    names = {row["name"] for row in manifest["gates"] if isinstance(row, dict)}
    assert NESTED_PREFLIGHT not in names
    assert SCAN in names
    assert STANDALONE_PREFLIGHT in names


def test_ci_summary_audit_no_longer_maps_the_caller_to_the_nested_preflight() -> None:
    assert DIRECT_REQUIRED_JOB_CONTEXTS[
        ("call-reject-skip.yml", "call-reject-skip-token")
    ] == (SCAN,)
