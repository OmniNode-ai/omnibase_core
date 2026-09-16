# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Every automated branch push carries the App identity and names its run (OMN-18273).

OMN-18273's first two acceptance criteria are that every automated push carries a
distinct bot identity rather than a human's or a generic one, and that every
automated commit carries a trailer naming the workflow and the run that produced it.
Both were unmet in this repository: the downstream pin-bump job minted an
``onexbot-occ-writer`` installation token and then committed as ``onex-pin-bump-bot
<bot@omninode.ai>`` — an address that resolves to no GitHub account — the dependency
cascade minted the same token and committed as ``github-actions[bot]``, and the
shadow-metrics harvester pushed with the default workflow token under a fabricated
``onex-shadow-harvester[bot]`` identity.

Operating Rule #5: detection that is not a gate is advisory. This file is the gate.

Two properties are asserted, and the second is the one that keeps the first honest:

1. every job that pushes a **branch** mints the App token, checks that mint
   fail-closed (never ``|| secrets.GITHUB_TOKEN``), sets the App's real committer
   identity, and stamps ``Onex-Workflow`` / ``Onex-Run`` trailers on the commit it
   pushes;
2. the set of workflow files containing ``git push`` is exactly the classified set
   below. A new pusher added without a classification fails this test rather than
   silently inheriting no requirement at all.

The App's committer identity is not invented here. It is read off real commits the
App authored, e.g. ``onex_change_control`` ``30caec1a``:
``onexbot-occ-writer[bot] <307849072+onexbot-occ-writer[bot]@users.noreply.github.com>``.
The numeric ``307849072+`` prefix is load-bearing — without it GitHub does not link
the commit to the bot account.

Why an App-token push is required rather than merely allowed: a push made with the
default workflow token does not start push-driven CI, so a bot PR opened that way
sits with no checks. An App-token push does start it — verified 2026-09-16 on
``omnibase_spi`` run ``35134173847`` (``event: push``,
``actor: onexbot-occ-writer[bot]``, ``conclusion: success``). The earlier org finding
that App tokens were suppressed too was a credential confound: a default
``actions/checkout`` persists a basic-auth ``extraheader`` carrying the workflow
token, which overrides any credential in the remote URL. That is why property 1
requires the mint to fail closed — a fallback expression reintroduces exactly that
confound.

Companion gates in the sibling repos: ``omnimarket`` (PR 2608) and ``omnibase_infra``
(PR 3657) carry the same registry against their own pusher sets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

APP_BOT_NAME = "onexbot-occ-writer[bot]"
APP_BOT_EMAIL = "307849072+onexbot-occ-writer[bot]@users.noreply.github.com"

# Workflow file -> job ids that push a branch and must therefore comply.
BRANCH_PUSHERS: dict[str, tuple[str, ...]] = {
    "publish-downstream-pin-bump.yml": ("bump",),
    "dependency-cascade.yml": ("open-bump-pr",),
    "shadow-metrics-harvest.yml": ("harvest",),
}

# Workflow file -> why it is out of scope. Every exemption is a stated reason, not a
# blanket.
EXEMPT: dict[str, str] = {
    "auto-tag-reusable.yml": (
        "pushes a tag only; a tag carries no commit, so no trailer can attach to it"
    ),
}

TRAILER_WORKFLOW = "Onex-Workflow:"
TRAILER_RUN = "Onex-Run:"

# A push whose refspec names a tag. Tags carry no commit message, so the trailer
# requirement cannot apply to them.
_TAG_PUSH = re.compile(
    r"git push\s+\S*\s*(\"?refs/tags/|\"?\$\{?\{?\s*steps\.\w+\.outputs\.tag)"
)


def _workflow_files() -> list[Path]:
    return sorted(p for p in WORKFLOWS.glob("*.yml"))


def _files_containing_git_push() -> set[str]:
    found = set()
    for path in _workflow_files():
        text = path.read_text(encoding="utf-8")
        if "git push" in text:
            found.add(path.name)
    return found


def _job_run_text(workflow: str, job_id: str) -> str:
    data = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    jobs = data.get("jobs", {})
    assert job_id in jobs, f"{workflow}: job '{job_id}' not found; jobs={sorted(jobs)}"
    job = jobs[job_id]
    chunks: list[str] = []
    for step in job.get("steps", []) or []:
        chunks.append(yaml.safe_dump(step, default_flow_style=False))
    return "\n".join(chunks)


def test_every_git_push_workflow_is_classified() -> None:
    """A new automated pusher cannot appear without a classification.

    Without this, adding a workflow that pushes a branch would inherit no requirement
    and this gate would report green over it.
    """
    classified = set(BRANCH_PUSHERS) | set(EXEMPT)
    actual = _files_containing_git_push()

    unclassified = actual - classified
    assert not unclassified, (
        "workflow(s) run `git push` but are neither listed in BRANCH_PUSHERS nor "
        f"given a stated EXEMPT reason: {sorted(unclassified)}. Classify them in "
        f"{Path(__file__).name} — an unclassified pusher is an unenforced one."
    )

    stale = classified - actual
    assert not stale, (
        f"classified workflow(s) no longer contain `git push`: {sorted(stale)}. "
        "Remove the stale entries so the registry keeps meaning something."
    )


@pytest.mark.parametrize(
    ("workflow", "job_id"),
    [(wf, job) for wf, jobs in BRANCH_PUSHERS.items() for job in jobs],
)
def test_branch_pusher_mints_the_app_token_fail_closed(
    workflow: str, job_id: str
) -> None:
    text = _job_run_text(workflow, job_id)

    assert "actions/create-github-app-token" in text, (
        f"{workflow}:{job_id} pushes a branch but never mints an App installation "
        "token. A push made with the default workflow token does not start "
        "push-driven CI, and it attributes the commit to github-actions[bot] rather "
        "than to a bot this org owns."
    )
    # Match a real `secrets.` reference, not a mention in a log line. A reusable
    # workflow receives the org secrets as hyphenated `workflow_call` secret
    # inputs, so both spellings are legitimate; a prose mention of the org secret
    # name is not.
    app_id_ref = re.search(
        r"secrets\.(?:ONEXBOT_OCC_APP_ID|onexbot-occ-app-id)\b", text
    )
    key_ref = re.search(
        r"secrets\.(?:ONEXBOT_OCC_PRIVATE_KEY|onexbot-occ-private-key)\b", text
    )
    assert app_id_ref is not None and key_ref is not None, (
        f"{workflow}:{job_id} must mint from the onexbot-occ-writer credentials "
        "(org secrets ONEXBOT_OCC_APP_ID / ONEXBOT_OCC_PRIVATE_KEY, or the "
        "hyphenated workflow_call secret inputs that carry them)."
    )

    # Fail closed. A fallback silently restores the workflow token and with it the
    # exact credential confound that produced the wrong org-wide finding in August.
    fallback = re.search(
        r"steps\.[\w-]+\.outputs\.token\s*\|\|\s*secrets\.GITHUB_TOKEN", text
    )
    assert fallback is None, (
        f"{workflow}:{job_id} falls back to secrets.GITHUB_TOKEN when the mint "
        "fails. That silently pushes as the workflow token, which is suppressed and "
        "mis-attributed, while the job still reports success."
    )


@pytest.mark.parametrize(
    ("workflow", "job_id"),
    [(wf, job) for wf, jobs in BRANCH_PUSHERS.items() for job in jobs],
)
def test_branch_pusher_commits_as_the_app_identity(workflow: str, job_id: str) -> None:
    text = _job_run_text(workflow, job_id)

    assert APP_BOT_NAME in text, (
        f"{workflow}:{job_id} does not set user.name to {APP_BOT_NAME!r}. The "
        "identity a bot commits under is what makes attribution recoverable from "
        "git alone (OMN-18273 AC-4)."
    )
    assert APP_BOT_EMAIL in text, (
        f"{workflow}:{job_id} does not set user.email to {APP_BOT_EMAIL!r}. A "
        "fabricated address such as bot@omninode.ai resolves to no GitHub account, "
        "so the commit renders unlinked and the identity proves nothing. The "
        "numeric prefix is what links the address to the bot account."
    )
    # Match the assignment, not any mention. Prose that explains why an old
    # identity was replaced must not read as the identity still being set —
    # otherwise the only way to pass is to leave the change unexplained.
    for forbidden in (
        "bot@omninode.ai",
        "41898282+github-actions[bot]",
        "github-actions[bot]",
        "onex-pin-bump-bot",
        "onex-shadow-harvester[bot]",
        "shadow-harvester@omninode.ai",
    ):
        assignment = re.search(
            r"git config (?:--global )?user\.(?:name|email) [\"']?"
            + re.escape(forbidden),
            text,
        )
        assert assignment is None, (
            f"{workflow}:{job_id} still assigns the {forbidden!r} identity via "
            "`git config`."
        )


@pytest.mark.parametrize(
    ("workflow", "job_id"),
    [(wf, job) for wf, jobs in BRANCH_PUSHERS.items() for job in jobs],
)
def test_branch_pusher_stamps_workflow_and_run_trailers(
    workflow: str, job_id: str
) -> None:
    text = _job_run_text(workflow, job_id)

    assert TRAILER_WORKFLOW in text, (
        f"{workflow}:{job_id} does not stamp an {TRAILER_WORKFLOW} trailer. "
        "OMN-18273 AC-2 requires every automated commit to name the workflow that "
        "produced it."
    )
    assert TRAILER_RUN in text, (
        f"{workflow}:{job_id} does not stamp an {TRAILER_RUN} trailer. AC-2 "
        "requires the run to be nameable from the commit, with no ledger row and no "
        "session transcript in the path."
    )
    assert "GITHUB_RUN_ID" in text or "github.run_id" in text, (
        f"{workflow}:{job_id} stamps an {TRAILER_RUN} trailer that does not "
        "interpolate the run id, so it names no run."
    )


def test_tag_only_pushes_are_not_silently_counted_as_branch_pushes() -> None:
    """Positive control for the tag/branch split the exemptions rely on.

    A zero from the branch-pusher scan would look identical whether the split works
    or the regex matches nothing at all. This pins a known tag push and a known
    branch push against it.
    """
    tag_line = 'git push origin "refs/tags/${TAG}"'
    branch_line = 'git push origin "$BRANCH"'
    assert _TAG_PUSH.search(tag_line) is not None, "tag push should classify as a tag"
    assert _TAG_PUSH.search(branch_line) is None, (
        "branch push must not classify as a tag"
    )


def test_scan_finds_the_known_pushers() -> None:
    """Positive control for the scan itself.

    ``_files_containing_git_push`` returning an empty set — a wrong workflows path, a
    glob that matches nothing — would make every registry assertion above pass
    vacuously. Pin a known-present pusher and a known-absent file against it.
    """
    found = _files_containing_git_push()
    assert "publish-downstream-pin-bump.yml" in found, (
        "the scan cannot see a workflow that demonstrably contains `git push`; "
        f"WORKFLOWS={WORKFLOWS} resolved to something wrong (found={sorted(found)})."
    )
    assert "pr-title-check.yml" not in found, (
        "the scan reports `git push` in a workflow that does not push, so its "
        "verdicts carry no information."
    )
