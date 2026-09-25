# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18202 AC1 -- a cascade bump PR body must carry no foreign evidence stamp.

``dependency-cascade.yml`` used to write the RELEASING PR's own evidence
ticket/source pair into every downstream bump PR body, verbatim. That citation
does not bind to the downstream PR: ``occ-preflight`` checks out the stamped
change-control commit, finds no receipt for the downstream PR's own number or
head sha, and fails with ``reason=pr_ticket_mismatch``. No rerun clears it,
because the stamped tree never changes.

It also cannot be repaired afterwards. The downstream repo's own OCC autobind
mints a companion bound to the bump PR, but its stamp writer refuses to replace
a stamp that names a MERGED companion (OMN-18089), and the upstream release's
companion is always merged before the cascade opens. The in-session body-edit
guard (OMN-18335) likewise refuses to drop the line. Live on the 0.47.23 wave,
2026-09-25: ``omniclaude#2338`` and ``omnimemory#533`` both carry the stamp for
``OCC#11192`` (the evidence for ``omnibase_core#1763``) while their own
companions ``OCC#11213`` and ``OCC#11211`` merged unused.

``omnibase_infra``'s copy of this generator was fixed by ``omnibase_infra#3998``;
this module pins the same invariant on omnibase_core's copy, which the
omnibase_core release workflow calls with ``uses: ./.github/workflows/...``.

The fix: the generator emits NO evidence ticket/source line at all, leaving the
downstream autobind as the only writer of that field, and a read-back step fails
the cascade run if a PR it just opened carries one anyway.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"

_JOB_NAME = "open-bump-pr"
_PR_STEP_NAME = "Open pull request"
_VERIFY_STEP_NAME = "Verify no foreign Evidence-Source stamp was emitted (OMN-18202)"

#: The line shape occ-preflight, the Receipt Gate and the companion-merged gate
#: parse. This is the parsing logic itself, the one place the literal belongs.
_STAMP_LINE_RE = re.compile(r"^[ \t]*Evidence-(Ticket|Source):", re.MULTILINE)


def _steps() -> list[dict[str, object]]:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    steps = document["jobs"][_JOB_NAME]["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"job {_JOB_NAME!r} has no step named {name!r}")


def _body_template() -> str:
    run = _step(_PR_STEP_NAME).get("run", "")
    assert isinstance(run, str)
    opener = "<<'PREOF'"
    start = run.find(opener)
    assert start != -1, "the `gh pr create` body is no longer a quoted heredoc"
    start = run.index("\n", start) + 1
    end = run.find("PREOF", start)
    assert end != -1, "unterminated body heredoc in the `gh pr create` step"
    return textwrap.dedent(run[start:end])


def _stamp_lines(body: str) -> list[str]:
    return [m.group(0) for m in _STAMP_LINE_RE.finditer(body)]


@pytest.mark.unit
def test_the_generated_body_carries_no_evidence_stamp_line() -> None:
    """AC1: the body template writes no evidence ticket/source line."""
    found = _stamp_lines(_body_template())
    assert not found, (
        "the cascade's pull request body template writes an evidence "
        f"ticket/source line ({found}). That stamps the downstream bump with "
        "the upstream release's companion, which binds no receipt to the bump "
        "and which the autobind stamp writer then refuses to replace "
        "(OMN-18202, OMN-18853, OMN-18089)."
    )


@pytest.mark.unit
def test_the_stamp_reader_would_catch_a_stamped_body() -> None:
    """Negative control: the reader above is not vacuous."""
    stamped = "## Test plan\n\nEvidence-Ticket: OMN-1\nEvidence-Source: OCC#2\n"
    assert len(_stamp_lines(stamped)) == 2


@pytest.mark.unit
def test_the_body_still_opens_a_real_pull_request() -> None:
    """A body with no stamp is not the same defect as no pull request."""
    run = _step(_PR_STEP_NAME).get("run", "")
    assert isinstance(run, str)
    assert "gh pr create" in run
    assert '--head "$BRANCH"' in run
    assert 'echo "created=true" >> "$GITHUB_OUTPUT"' in run
    assert _step(_PR_STEP_NAME).get("id") == "open_pr"


@pytest.mark.unit
def test_a_read_back_step_fails_the_run_on_a_stamped_pull_request() -> None:
    """The structural guard reads back only a PR this run created."""
    names = [step.get("name") for step in _steps()]
    assert _VERIFY_STEP_NAME in names
    assert names.index(_VERIFY_STEP_NAME) == names.index(_PR_STEP_NAME) + 1
    step = _step(_VERIFY_STEP_NAME)
    condition = str(step.get("if", ""))
    assert "steps.open_pr.outputs.created == 'true'" in condition
    run = str(step.get("run", ""))
    assert "grep -qE '^Evidence-(Ticket|Source):'" in run
    assert "exit 1" in run
