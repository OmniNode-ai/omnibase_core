# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20969: stop the S5 comparison before removing its OCC producer."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

CALLER_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/call-repo-evidence-gate.yml"
)
# Verbatim caller from dev 60ce70d13e07ddfa34539d00527443c90bb0c521.
BASE_CALLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Repo Evidence Gate caller (OMN-20074, OCC retirement OR.6) verifies
# omnibase_core's own contracts/<OMN-N>.yaml at the PR head through this
# repository's receipt-gate reusable with evidence-source: caller.
# This is the path omnimarket proved as the canary (OMN-20070, OMN-20072).
#
# Why pull_request_target: GitHub reads the workflow definition from the BASE
# branch, so a pull request that edits this file or the reusable's pin does not
# change which definition runs on it. The reusable refuses fork heads before
# any checkout. For a same-repository head it runs the cited contract's checks
# (its bound tests) at the head and at the merge base on the trusted runner
# fleet; the definition that runs them is still the base branch's.
#
# dev and main are the integration branches. The activity types cover new heads,
# reopened and ready PRs, and edits to the ticket citation or base branch.
# Per-PR concurrency cancels superseded runs so the latest event gets a verdict.
# Read-only contents and pull-requests permissions are all this caller needs;
# checkout and verification belong to the reusable, with no caller secrets.
# The full-SHA pin makes the reusable immutable; verifier-version pins the
# released verifier used to read the caller's contracts.
#
# The job id is the context prefix: repo-evidence / dod-verify carries the
# verdict, so do not add a job name. The reusable also reports a skipped
# repo-evidence / verify job in this mode (the OCC path, switched off by the
# input); only repo-evidence / dod-verify carries a verdict.
#
# The reusable is pinned by full SHA to omnibase_core#1914's squash commit on dev,
# which carries #1912's contract-home marker and caller-mode verify no-op.
# verifier-version 0.4.305 is the first omnimarket release carrying
# omnimarket#3563 (node_dod_verify names contract_in_another_repo), the verifier
# half of #1912. It is not called as
# ./.github/workflows/receipt-gate.yml. A pull request that edits
# receipt-gate.yml in this repository does not change the definition that
# judges it.
#
# S5 shadow count (OMN-20074): compare-with-occ is "true" so every run records
# this head's new-path verdict beside OCC's occ-preflight / eligibility verdict
# on the same head. S6 part 1: CI Summary expects repo-evidence / dod-verify on
# pull_request runs (EXPECTED_EXTERNAL_CONTEXTS in scripts/ci/ci_summary_gate.py),
# so an absent verdict holds the required CI Summary context and a red one
# fails it. Every OCC context stays required until S6 part 2 deletes the OCC
# callers; that change sets compare-with-occ back to "false".
#
# PR-workflow budget (architecture-handshakes/pull-request-workflow-budget.yaml,
# OMN-14907): this file takes the slot of call-occ-preflight.yml, retired in
# the same change. That file was a duplicate producer of the required
# occ-preflight / eligibility context; call-receipt-gate.yml's occ-preflight
# job still produces it on every pull request into main or dev and on
# merge_group. The budget stays 30.

name: Repo Evidence Gate

on:
  pull_request_target:
    types: [opened, synchronize, reopened, edited, ready_for_review]
    branches: [dev, main]

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: read

jobs:
  repo-evidence:
    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@fb0c6c2117d5868a398b0920cd0048d0824415b1 # OMN-20074: immutable full-SHA pin, the squash commit of omnibase_core#1914 on dev (carries #1912's contract-home marker and caller-mode verify no-op, #1911's in-job pin-only verdict, and adds the OCC writer app's release-cut exemption)
    with:
      evidence-source: caller
      verifier-version: 0.4.305
      compare-with-occ: "true"
"""


DEV_MERGE_TAG_USES_TAIL = (
    "@dev-20261101005012-ac2f26e3e5bf # omnibase_core dev-merge tag (OMN-21859)."
)

# OMN-21859: the caller installs its verifier from an omnimarket dev-merge tag
# (verifier-tag) and passes no verifier-version; the header comments that
# described verifier-version as the pin say so. Restore the merge base's lines
# so every other byte compares.
VERIFIER_TAG_LINE = "verifier-tag: dev-20261101000200-949993edf3b7"
BASE_VERIFIER_VERSION_LINE = "verifier-version: 0.4.305"
VERIFIER_PIN_COMMENT_RESTORES = (
    (
        """# The dev-merge tag pin makes the reusable immutable; verifier-tag names the
# omnimarket dev-merge tag the verifier that reads the caller's contracts is
# installed from (OMN-21859).
""",
        """# The full-SHA pin makes the reusable immutable; verifier-version pins the
# released verifier used to read the caller's contracts.
""",
    ),
    (
        """# The reusable resolves verifier-tag to a commit and refuses a moved tag, a tag
# not on omnimarket dev and a tag not descending from its floor commit
# (OMN-21676); verifier-version is only its warned fallback, so this caller
# does not pass it. The reusable is not called as
""",
        """# verifier-version 0.4.305 is the first omnimarket release carrying
# omnimarket#3563 (node_dod_verify names contract_in_another_repo), the verifier
# half of #1912. It is not called as
""",
    ),
)


def _without_s5_comment(text: str) -> str:
    return re.sub(
        r"# S5 shadow count.*?(?=#\n# PR-workflow budget)", "", text, flags=re.DOTALL
    )


def test_caller_disables_occ_comparison() -> None:
    caller = yaml.safe_load(CALLER_PATH.read_text(encoding="utf-8"))
    assert caller["jobs"]["repo-evidence"]["with"]["compare-with-occ"] == "false"


def _assert_preserved(text: str) -> None:
    # OMN-21495 (K11): the reusable is named by a dev-merge tag, not the merge
    # base's full sha; restore the merge base's line so every other byte compares.
    base_uses_tail = next(
        line for line in BASE_CALLER.splitlines() if "receipt-gate.yml@" in line
    ).split("receipt-gate.yml", 1)[1]
    text = text.replace(DEV_MERGE_TAG_USES_TAIL, base_uses_tail)
    text = text.replace(VERIFIER_TAG_LINE, BASE_VERIFIER_VERSION_LINE)
    for current, base_text in VERIFIER_PIN_COMMENT_RESTORES:
        text = text.replace(current, base_text)
    base = yaml.safe_load(BASE_CALLER)
    actual = yaml.safe_load(text)
    base["jobs"]["repo-evidence"]["with"]["compare-with-occ"] = "false"
    assert actual == base
    restored = text.replace('compare-with-occ: "false"', 'compare-with-occ: "true"')
    assert _without_s5_comment(restored) == _without_s5_comment(BASE_CALLER)


def test_every_other_input_pin_and_line_matches_the_merge_base() -> None:
    _assert_preserved(CALLER_PATH.read_text(encoding="utf-8"))


def test_scope_control_rejects_another_input_pin_or_line() -> None:
    text = CALLER_PATH.read_text(encoding="utf-8")
    for old in (
        "evidence-source: caller",
        VERIFIER_TAG_LINE,
        yaml.safe_load(text)["jobs"]["repo-evidence"]["uses"],
    ):
        with pytest.raises(AssertionError):
            _assert_preserved(text.replace(old, old + "drift"))
    with pytest.raises(AssertionError):
        _assert_preserved(text + "# unrelated edit\n")
