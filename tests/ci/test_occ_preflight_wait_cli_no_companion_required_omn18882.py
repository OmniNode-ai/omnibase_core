# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI tests for the Receipt Gate's pin-only probe (OMN-18882).

``.github/workflows/receipt-gate.yml`` is the THIRD gate in the OMN-18848
family and, until this ticket, the only one that never read the occ-autobind
producer's outcome. A dependency-pin-only PR -- a post-release manifest +
lockfile bump -- can never satisfy its ``Evidence-Source:`` requirement,
because the producer correctly DECLINES to mint a companion for a diff with
no behavioural claim (measured on omnimarket#2701 at 10:38:18Z).

The Receipt Gate is a bash gate, so it needs a decisive process-level answer
rather than an importable predicate. This module pins that entrypoint:
``occ_preflight_wait.py --check-no-companion-required``, which reuses the very
same :data:`AUTOBIND_NO_COMPANION_REQUIRED_REASONS` token set, predicate and
check-run reader the bounded wait uses (AC7: the token is defined once, in one
module, for all three gates).

Every branch fails CLOSED here, which is the opposite of the bounded wait's
read: in the wait an unreadable outcome leaves the existing poll path intact,
whereas here an unreadable outcome must leave the Receipt Gate's existing hard
fail intact. Exit 0 means, and only means, "the producer affirmatively
classified THIS head's diff as dependency-pin-only".
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.ci.occ_preflight_wait import (
    AUTOBIND_NO_COMPANION_REQUIRED_REASONS,
    EXIT_ERROR,
    EXIT_OK,
    EnumAutobindReadStatus,
    ModelAutobindOutcomeRead,
    main,
    read_autobind_outcome_from_check_runs,
)

pytestmark = pytest.mark.unit

REPO = "OmniNode-ai/omnimarket"
PR_NUMBER = "2701"
HEAD_SHA = "a" * 40
OTHER_SHA = "b" * 40

PIN_ONLY_REASON = AUTOBIND_NO_COMPANION_REQUIRED_REASONS[0]


def _outcome_run(
    *, outcome: str, reason: str, completed_at: str = "2026-09-20T10:38:18Z"
) -> dict[str, Any]:
    """One ``occ-autobind / outcome`` check-run, in the producer's own shape."""
    return {
        "name": "occ-autobind / outcome",
        "status": "completed",
        "completed_at": completed_at,
        "output": {
            "summary": (
                f"occ-autobind-outcome: {outcome} repo={REPO} pr={PR_NUMBER} "
                f"correlation_id=c-1 reason={reason}\n\nHuman prose follows."
            )
        },
    }


class _FakeGh:
    """A :class:`GhPort` that models ``GhCli``'s head-SHA binding.

    ``read_autobind_outcome`` resolves the PR's CURRENT head and reads only
    the check-runs recorded against THAT sha, exactly as the live client does
    (it fetches ``repos/<r>/commits/<head>/check-runs``). Every other port
    method raises: the probe must consult the producer's check-run and nothing
    else -- in particular it must never read the PR body, which is the surface
    an author controls.
    """

    def __init__(
        self,
        *,
        head_sha: str | None,
        check_runs_by_sha: dict[str, list[dict[str, Any]]],
        pr_body: str = "",
    ) -> None:
        self.head_sha = head_sha
        self.check_runs_by_sha = check_runs_by_sha
        self.pr_body = pr_body
        self.body_reads = 0

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        self.body_reads += 1
        return self.pr_body

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        raise AssertionError("the pin-only probe must not read an OCC companion")

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        raise AssertionError("the pin-only probe must not canonicalize a SHA")

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> bool:
        raise AssertionError("the pin-only probe must not resolve ancestry")

    def read_autobind_outcome(
        self, *, repo: str, pr_number: str
    ) -> ModelAutobindOutcomeRead:
        # OMN-18647 retyped this port to a tri-state so a read that FAILED is
        # distinguishable from a producer that has not reported. Both still
        # fail this probe closed; only the message differs.
        if not self.head_sha:
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
        parsed = read_autobind_outcome_from_check_runs(
            self.check_runs_by_sha.get(self.head_sha, [])
        )
        if parsed is None:
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.ABSENT)
        return ModelAutobindOutcomeRead(
            status=EnumAutobindReadStatus.READ, outcome=parsed[0], reason=parsed[1]
        )


def _run(gh: _FakeGh, *, github_output_path: str = "") -> int:
    return main(
        [
            "--check-no-companion-required",
            "--repo",
            REPO,
            "--pr-number",
            PR_NUMBER,
            "--github-output-path",
            github_output_path,
        ],
        gh=gh,
    )


def test_pin_only_declined_on_the_current_head_is_exit_zero() -> None:
    """The one and only new pass: an affirmative pin-only outcome bound to the
    PR's current head SHA."""
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [_outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)]
        },
    )
    assert _run(gh) == EXIT_OK


def test_pin_only_probe_never_reads_the_pr_body() -> None:
    """This is a DERIVED exemption, not a token. The probe reads the
    producer's head-SHA-bound check-run and nothing an author can type."""
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [_outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)]
        },
        pr_body=f"Evidence-Source: OCC#1 and also {PIN_ONLY_REASON}",
    )
    assert _run(gh) == EXIT_OK
    assert gh.body_reads == 0, (
        "the pin-only probe read the PR body; the exemption must be derived "
        "from the producer's check-run alone"
    )


def test_generic_not_red_derivable_declined_is_not_exempt() -> None:
    """Positive control: a non-pin DECLINED is still an ordinary PR that owes
    an Evidence-Source citation, and the Receipt Gate must still hard fail."""
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [
                _outcome_run(
                    outcome="DECLINED", reason="skip:NO_RED_DERIVABLE_CHECK generic"
                )
            ]
        },
    )
    assert _run(gh) == EXIT_ERROR


def test_no_outcome_at_all_is_not_exempt() -> None:
    gh = _FakeGh(head_sha=HEAD_SHA, check_runs_by_sha={HEAD_SHA: []})
    assert _run(gh) == EXIT_ERROR


def test_outcome_recorded_only_under_a_different_sha_is_not_exempt() -> None:
    """A new commit invalidates the exemption: the outcome is bound to the sha
    it was posted on, and the current head carries none."""
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            OTHER_SHA: [_outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)]
        },
    )
    assert _run(gh) == EXIT_ERROR


def test_unresolvable_head_sha_is_not_exempt() -> None:
    gh = _FakeGh(
        head_sha=None,
        check_runs_by_sha={
            HEAD_SHA: [_outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)]
        },
    )
    assert _run(gh) == EXIT_ERROR


def test_the_token_in_prose_only_is_not_exempt() -> None:
    """A summary that DESCRIBES the classifier refusing must not read as the
    classifier accepting, and neither must a PR body that spells the token."""
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [
                _outcome_run(
                    outcome="DECLINED",
                    reason=(
                        f"classifier refused {PIN_ONLY_REASON} because a source "
                        "file changed"
                    ),
                )
            ]
        },
        pr_body=f"This PR is not {PIN_ONLY_REASON}, honest.",
    )
    assert _run(gh) == EXIT_ERROR


@pytest.mark.parametrize("outcome_word", ["MINTED", "ERROR", "SKIPPED", ""])
def test_only_declined_carries_the_exemption(outcome_word: str) -> None:
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [_outcome_run(outcome=outcome_word, reason=PIN_ONLY_REASON)]
        },
    )
    assert _run(gh) == EXIT_ERROR


def test_missing_pr_number_is_not_exempt() -> None:
    """Fail closed on an unresolvable PR: the Receipt Gate's own hard fail
    must stay in place rather than a probe that cannot address anything
    returning a pass."""
    gh = _FakeGh(head_sha=HEAD_SHA, check_runs_by_sha={})
    assert (
        main(
            ["--check-no-companion-required", "--repo", REPO, "--pr-number", ""], gh=gh
        )
        == EXIT_ERROR
    )


def test_exempt_run_writes_the_evidence_not_required_output(tmp_path: Any) -> None:
    """The workflow step reads this output to gate every downstream step."""
    out = tmp_path / "gh_output"
    out.write_text("")
    gh = _FakeGh(
        head_sha=HEAD_SHA,
        check_runs_by_sha={
            HEAD_SHA: [_outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)]
        },
    )
    assert _run(gh, github_output_path=str(out)) == EXIT_OK
    assert "evidence_not_required=true" in out.read_text()


def test_non_exempt_run_writes_no_output(tmp_path: Any) -> None:
    out = tmp_path / "gh_output"
    out.write_text("")
    gh = _FakeGh(head_sha=HEAD_SHA, check_runs_by_sha={HEAD_SHA: []})
    assert _run(gh, github_output_path=str(out)) == EXIT_ERROR
    assert "evidence_not_required" not in out.read_text()


def test_the_probe_does_not_poll() -> None:
    """The Receipt Gate runs after the bounded wait has already had its
    budget; this probe must answer in one read, never sleep."""
    gh = _FakeGh(head_sha=HEAD_SHA, check_runs_by_sha={HEAD_SHA: []})
    import time as _time

    start = _time.monotonic()
    assert _run(gh) == EXIT_ERROR
    assert _time.monotonic() - start < 5.0
