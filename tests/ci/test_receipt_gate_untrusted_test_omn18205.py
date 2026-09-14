# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18205: the Receipt Gate's untrusted test is the fork test.

`receipt-gate.yml` is a cross-repo reusable. Fourteen repositories consume it
and surface its job as the required context `verify / verify`, so its
`runs-on` selector decides runner placement for repositories whose maintainers
cannot see the expression at all.

It used to route EVERY pull-request event to the untrusted public class.
That is not a trust boundary -- a same-repo pull request is written by
somebody who can already push to the repository the gate protects -- and what
it actually produced was a required check pinned to GitHub-hosted runners in
every consuming repository, overriding that repository's own routing shadow
with no signal on any routing surface.

The assertion runs over the live workflow file, so reintroducing the clause is
a red test rather than a review catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)

FORK_TEST = "github.event.pull_request.head.repo.full_name != github.repository"

NON_TRUST_CLAUSES = (
    "github.base_ref ==",
    "github.base_ref !=",
    "github.event_name != 'pull_request'",
)


def _selector() -> str:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = document["jobs"]
    runs_on = jobs["verify"]["runs-on"]
    assert isinstance(runs_on, str), "the selector is an expression, not a literal"
    return re.sub(r"\s+", " ", runs_on)


def test_the_gate_is_a_cross_repo_reusable() -> None:
    """Positive control: the assertion below only matters because of this."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = document.get(True) or document.get("on")
    assert "workflow_call" in triggers, (
        "if this stops being a reusable workflow the placement it decides is "
        "local, and this test is asserting something that no longer matters"
    )


def test_the_untrusted_class_is_gated_on_the_fork_test_alone() -> None:
    selector = _selector()
    assert FORK_TEST.replace(" ", "") in selector.replace(" ", ""), (
        "the fork test is the only thing that makes a pull request untrusted"
    )
    offending = [clause for clause in NON_TRUST_CLAUSES if clause in selector]
    assert not offending, (
        f"the Receipt Gate routes pull requests to the untrusted public runner "
        f"class on {offending}, which is not a trust boundary. Every consuming "
        "repository then has `verify / verify` pinned to GitHub-hosted runners "
        "regardless of its own routing shadow -- forbidden for private "
        "repositories by the 2026-09-14 operator ruling, and unrunnable at all "
        "since the enterprise hosted-runner switch."
    )


def test_a_fork_pull_request_still_reaches_the_public_class() -> None:
    """The boundary OMN-16683 exists to hold is unchanged by the narrowing."""
    selector = _selector()
    assert "vars.OMNI_PUBLIC_PR_RUNS_ON_JSON" in selector
    assert "vars.OMNI_TRUSTED_CI_RUNS_ON_JSON" in selector
    fork_index = selector.index(FORK_TEST.split(" != ")[0])
    public_index = selector.index("vars.OMNI_PUBLIC_PR_RUNS_ON_JSON")
    assert fork_index < public_index, (
        "the fork test must select the public class, not the trusted one"
    )
