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

Since the operator rule of 2026-10-19 a private repository may not run on a
GitHub-hosted label at all, fork pull requests included, and a hosted default
behind a variable counts (OMN-21216). A public caller already always ran on
ubuntu-latest (OMN-21280), so the fork arm was reachable only from a private
caller, where it is now forbidden. It is gone: a private caller runs every
event on its own trusted variable with no default, and a public caller on
ubuntu-latest (OMN-20074).

The assertions run over the live workflow file, so reintroducing a hosted arm
for a private caller, or a non-trust clause, is a red test rather than a
review catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)

NON_TRUST_CLAUSES = (
    "github.base_ref ==",
    "github.base_ref !=",
    "github.event_name != 'pull_request'",
)

SELECTOR = (
    "${{ github.event.repository.private && ( "
    "fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON) ) || 'ubuntu-latest' }}"
)


def _selector(job: str = "verify") -> str:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = document["jobs"]
    runs_on = jobs[job]["runs-on"]
    assert isinstance(runs_on, str), "the selector is an expression, not a literal"
    return re.sub(r"\s+", " ", runs_on).strip()


def test_the_gate_is_a_cross_repo_reusable() -> None:
    """Positive control: the assertion below only matters because of this."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = document.get(True) or document.get("on")
    assert "workflow_call" in triggers, (
        "if this stops being a reusable workflow the placement it decides is "
        "local, and this test is asserting something that no longer matters"
    )


def test_no_pull_request_is_routed_on_a_non_trust_clause() -> None:
    selector = _selector()
    offending = [clause for clause in NON_TRUST_CLAUSES if clause in selector]
    assert not offending, (
        f"the Receipt Gate routes pull requests to the untrusted public runner "
        f"class on {offending}, which is not a trust boundary. Every consuming "
        "repository then has `verify / verify` pinned to GitHub-hosted runners "
        "regardless of its own routing shadow -- forbidden for private "
        "repositories by the 2026-09-14 operator ruling, and unrunnable at all "
        "since the enterprise hosted-runner switch."
    )


@pytest.mark.parametrize("job", ["verify", "dod-verify"])
def test_a_private_caller_never_reaches_a_hosted_arm(job: str) -> None:
    """OMN-20074: no public-class arm and no hosted default for a private caller.

    The fork pull request of a private caller used to resolve to
    OMNI_PUBLIC_PR_RUNS_ON_JSON or its ubuntu-latest default, which the
    2026-10-19 rule forbids. The only hosted label left is the one a public
    caller gets, behind the private-caller test.
    """
    selector = _selector(job)
    assert "OMNI_PUBLIC_PR_RUNS_ON_JSON" not in selector, (
        f"{job} still routes some pull request to the public runner class; a "
        "public caller always gets ubuntu-latest, so that arm is reachable only "
        "from a private caller, where a hosted label is forbidden"
    )
    assert selector == SELECTOR, (
        f"{job} runs-on is {selector!r}; a private caller must take its own "
        "trusted variable with no literal default (an unset variable fails "
        "the job rather than choosing a placement), and a public caller "
        "ubuntu-latest"
    )
