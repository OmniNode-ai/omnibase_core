# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Verdict tests for the occ-preflight bounded wait (OMN-17864).

``occ-preflight / eligibility``'s "Resolve Evidence-Source" step used to
``exit 1`` in 2-8 seconds whenever the PR body had no evidence-source stamp
yet, or the cited onex_change_control companion had not merged yet -- both
transient, both measured (see ``scripts/ci/occ_preflight_wait.py`` module
docstring: 53/53 PRs whose first CI run concluded before their companion
merged concluded FAILURE). These tests pin the fail-closed verdict table for
:func:`decide_preflight_wait`, the pure function that decides WAIT vs
FAIL_NOW vs DEADLINE vs PROCEED for one poll iteration.
"""

from __future__ import annotations

import pytest

from scripts.ci.occ_preflight_wait import (
    AUTOBIND_NO_COMPANION_REQUIRED_REASONS,
    DEFAULT_DEADLINE_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    EnumPreflightWaitOutcome,
    decide_preflight_wait,
    is_no_companion_required,
    read_autobind_outcome_from_check_runs,
)

pytestmark = pytest.mark.unit

DEADLINE = 1500
INTERVAL = 30


def test_stamp_absent_waits() -> None:
    decision = decide_preflight_wait(
        pr_body="Just a PR description, no stamp yet.",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"


def test_companion_open_waits() -> None:
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="OPEN",
        cited_sha_is_ancestor=False,
        elapsed_seconds=INTERVAL,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "companion_unmerged"


def test_companion_merged_inside_deadline_proceeds() -> None:
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="MERGED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=2 * INTERVAL,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "evidence_durable"


def test_full_fixture_sequence_stamp_then_open_then_merged() -> None:
    """The brief's exact fixture: absent -> open -> merged, in one sequence."""
    t0 = decide_preflight_wait(
        pr_body="no stamp here",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert t0.outcome is EnumPreflightWaitOutcome.WAIT

    t1 = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="OPEN",
        cited_sha_is_ancestor=False,
        elapsed_seconds=INTERVAL,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert t1.outcome is EnumPreflightWaitOutcome.WAIT

    t2 = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="MERGED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=16 * 60,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert t2.outcome is EnumPreflightWaitOutcome.PROCEED


def test_never_resolves_hits_deadline_exactly_and_not_one_poll_before() -> None:
    just_before = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="OPEN",
        cited_sha_is_ancestor=False,
        elapsed_seconds=DEADLINE - INTERVAL,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert just_before.outcome is EnumPreflightWaitOutcome.WAIT

    at_deadline = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="OPEN",
        cited_sha_is_ancestor=False,
        elapsed_seconds=DEADLINE,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert at_deadline.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert at_deadline.reason == "companion_unmerged"


def test_never_resolves_stamp_absent_hits_deadline() -> None:
    at_deadline = decide_preflight_wait(
        pr_body="no stamp",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=DEADLINE,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert at_deadline.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert at_deadline.reason == "stamp_absent"


def test_positive_control_companion_closed_unmerged_fails_now_with_zero_wait() -> None:
    """The OMN-15214 incident state: never poll on it."""
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="CLOSED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "companion_closed_unmerged"


def test_positive_control_malformed_stamp_fails_now() -> None:
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: not-a-valid-value",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "stamp_malformed"


@pytest.mark.parametrize("event_name", ["merge_group", "push", "workflow_dispatch"])
def test_non_pull_request_event_proceeds_immediately_regardless_of_state(
    event_name: str,
) -> None:
    """Invariant I2: merge_group re-validates fully and fails fast; the wait
    must never apply there, whatever the body/companion state looks like."""
    decision = decide_preflight_wait(
        pr_body=None,
        companion_state="CLOSED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=99999,
        deadline_seconds=DEADLINE,
        event_name=event_name,
    )
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "non_pull_request_event"


def test_genuine_ineligibility_still_fails_even_past_the_deadline() -> None:
    """The wait must never convert a real red into a green. A SHA that is not
    an ancestor of any OCC durable branch can never become one
    (onex_change_control is squash-only, OMN-15216) -- FAIL_NOW regardless of
    how much time has elapsed, never DEADLINE and never PROCEED."""
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: deadbeefcafe1234567890abcdef1234567890",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=DEADLINE * 10,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "sha_not_ancestor"


def test_ancestor_sha_proceeds() -> None:
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: deadbeefcafe1234567890abcdef1234567890",
        companion_state=None,
        cited_sha_is_ancestor=True,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "evidence_durable"


def test_unreadable_body_fails_now_without_waiting() -> None:
    decision = decide_preflight_wait(
        pr_body=None,
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "body_unreadable"


def test_companion_state_unresolved_retries_rather_than_fails() -> None:
    """A transient failure to read the companion's own state is retryable --
    it must not be conflated with an authoritative CLOSED."""
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "companion_state_unresolved"


def test_default_budget_matches_the_omn15214_gate() -> None:
    """1500/30 must stay pinned to the already-paid OMN-15214 budget -- see
    module docstring. A change here without a change there is the exact
    'invented a new number' failure mode this module exists to avoid."""
    assert DEFAULT_DEADLINE_SECONDS == 1500
    assert DEFAULT_POLL_INTERVAL_SECONDS == 30


# ---------------------------------------------------------------------------
# OMN-18848: a dependency-pin-only autobind outcome needs no companion.
#
# occ-preflight is a SECOND, independent gate that never read the producer's
# outcome at all: it polled 1500s for a stamp that can never arrive and failed
# closed with `stamp_absent` (live: omnimarket#2685, job 105923152940). These
# falsifiers pin the narrow exemption and, more importantly, pin that every
# other shape is untouched.
# ---------------------------------------------------------------------------

PIN_ONLY_REASON = "skip:DEPENDENCY_PIN_ONLY manifest+lockfile only"


def test_pin_only_declined_with_no_stamp_is_not_required() -> None:
    decision = decide_preflight_wait(
        pr_body="chore: release omnimarket 0.2.1 -- no stamp, none is coming",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", PIN_ONLY_REASON),
    )
    assert decision.outcome is EnumPreflightWaitOutcome.NOT_REQUIRED
    assert decision.reason == "no_companion_required"
    assert not decision.should_continue_polling
    assert not decision.is_terminal_failure
    assert "OMN-18848" in decision.detail


def test_no_red_derivable_declined_with_no_stamp_still_waits() -> None:
    """The general DECLINED case is deliberately untouched: a PR that owes
    hand-authored evidence must keep polling and then fail closed."""
    decision = decide_preflight_wait(
        pr_body="no stamp yet",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", "skip:NO_RED_DERIVABLE_CHECK see OMN-15247"),
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"

    at_deadline = decide_preflight_wait(
        pr_body="no stamp yet",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=DEADLINE,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", "skip:NO_RED_DERIVABLE_CHECK see OMN-15247"),
    )
    assert at_deadline.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert at_deadline.reason == "stamp_absent"


def test_absent_autobind_outcome_with_no_stamp_still_waits() -> None:
    """`None` means 'no outcome recorded, or the check-run list was
    unreadable'. Fail-OPEN on the read, which here means leaving the existing
    wait path exactly as it was -- an outage in another repo's runtime must
    never decide this gate."""
    decision = decide_preflight_wait(
        pr_body="no stamp yet",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=None,
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"


def test_error_outcome_with_no_stamp_behaves_exactly_as_today() -> None:
    decision = decide_preflight_wait(
        pr_body="no stamp yet",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("ERROR", "mint raised: connection reset"),
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"


def test_pin_only_outcome_never_overrides_a_stamp_that_is_present() -> None:
    """The exemption lives in the `stamp is None` branch ONLY. A PR that DOES
    cite evidence is evaluated on that evidence, whatever the producer said."""
    closed = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="CLOSED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", PIN_ONLY_REASON),
    )
    assert closed.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert closed.reason == "companion_closed_unmerged"

    merged = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#5012",
        companion_state="MERGED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", PIN_ONLY_REASON),
    )
    assert merged.outcome is EnumPreflightWaitOutcome.PROCEED
    assert merged.reason == "evidence_durable"

    malformed = decide_preflight_wait(
        pr_body="Evidence-Source: not-a-ref",
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", PIN_ONLY_REASON),
    )
    assert malformed.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert malformed.reason == "stamp_malformed"


def test_unreadable_body_still_fails_now_even_with_a_pin_only_outcome() -> None:
    decision = decide_preflight_wait(
        pr_body=None,
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", PIN_ONLY_REASON),
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "body_unreadable"


@pytest.mark.parametrize(
    "reason",
    [
        "skip:DEPENDENCY_PIN_ONLY",
        "skip:DEPENDENCY_PIN_ONLY manifest + lockfile only",
        "  skip:DEPENDENCY_PIN_ONLY trailing prose  ",
    ],
)
def test_predicate_matches_the_reason_token_at_the_start(reason: str) -> None:
    assert is_no_companion_required(reason)


@pytest.mark.parametrize(
    "reason",
    [
        "",
        "skip:NO_RED_DERIVABLE_CHECK",
        "skip:DEFER_HAND_AUTHORED",
        "skip:LEASE_HELD",
        "classifier refused skip:DEPENDENCY_PIN_ONLY because a source file changed",
        "not skip:DEPENDENCY_PIN_ONLY",
    ],
)
def test_predicate_does_not_match_prose_that_merely_mentions_the_token(
    reason: str,
) -> None:
    """Matched on the token the producer writes at the START of the reason,
    never on prose containing it -- a message that DESCRIBES the classifier
    refusing must not read as the classifier accepting."""
    assert not is_no_companion_required(reason)


def test_only_declined_carries_the_exemption() -> None:
    """A pin-only reason attached to any other outcome word is not an
    exemption. The producer only ever writes it on DECLINED."""
    for outcome_word in ("MINTED", "ERROR", "SKIPPED", ""):
        decision = decide_preflight_wait(
            pr_body="no stamp yet",
            companion_state=None,
            cited_sha_is_ancestor=False,
            elapsed_seconds=0,
            deadline_seconds=DEADLINE,
            event_name="pull_request",
            autobind_outcome=(outcome_word, PIN_ONLY_REASON),
        )
        assert decision.outcome is EnumPreflightWaitOutcome.WAIT, outcome_word
        assert decision.reason == "stamp_absent"


def test_pin_only_exemption_token_set_is_the_cross_repo_contract() -> None:
    """The token is a cross-repo contract with omnimarket's producer and its
    Companion Merged Gate (`AUTOBIND_NO_COMPANION_REQUIRED_REASONS` there).
    Widening this tuple here without widening it there splits the fleet's
    definition of 'needs no companion' in silence."""
    assert AUTOBIND_NO_COMPANION_REQUIRED_REASONS == ("skip:DEPENDENCY_PIN_ONLY",)


def test_read_autobind_outcome_takes_the_newest_completed_check_run() -> None:
    runs = [
        {
            "name": "occ-autobind / outcome",
            "status": "completed",
            "completed_at": "2026-09-19T10:00:00Z",
            "output": {
                "summary": "occ-autobind-outcome: DECLINED repo=r pr=1 "
                "correlation_id=c reason=skip:LEASE_HELD"
            },
        },
        {
            "name": "occ-autobind / outcome",
            "status": "completed",
            "completed_at": "2026-09-19T11:00:00Z",
            "output": {
                "summary": "occ-autobind-outcome: DECLINED repo=r pr=1 "
                "correlation_id=c reason=skip:DEPENDENCY_PIN_ONLY\nmore prose"
            },
        },
        {
            "name": "some other check",
            "status": "completed",
            "completed_at": "2026-09-19T12:00:00Z",
            "output": {"summary": "occ-autobind-outcome: MINTED reason=nope"},
        },
        {
            "name": "occ-autobind / outcome",
            "status": "in_progress",
            "completed_at": "2026-09-19T13:00:00Z",
            "output": {"summary": "occ-autobind-outcome: MINTED reason=nope"},
        },
    ]
    assert read_autobind_outcome_from_check_runs(runs) == (
        "DECLINED",
        "skip:DEPENDENCY_PIN_ONLY",
    )


def test_read_autobind_outcome_returns_none_when_no_outcome_is_posted() -> None:
    assert read_autobind_outcome_from_check_runs([]) is None
    assert (
        read_autobind_outcome_from_check_runs(
            [{"name": "other", "status": "completed", "output": {"summary": "x"}}]
        )
        is None
    )
