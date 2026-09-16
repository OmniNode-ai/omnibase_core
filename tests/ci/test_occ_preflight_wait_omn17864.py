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
    DEFAULT_DEADLINE_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    EnumPreflightWaitOutcome,
    decide_preflight_wait,
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
