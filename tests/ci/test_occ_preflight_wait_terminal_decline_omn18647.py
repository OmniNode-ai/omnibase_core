# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The preflight waiter tells a TERMINAL autobind decline from an in-flight mint (OMN-18647).

Before this change ``occ_preflight_wait`` had exactly one shape for "the PR
body carries no evidence-source stamp": wait, and fail at the 1500 s deadline
with reason ``stamp_absent``. That is right for a mint still in flight and
wrong for a decline the producer has already made and recorded, which no
amount of waiting will change. Measured cost of the conflation on
2026-09-20: six PRs, roughly 25 minutes of runner time each, and a
hand-authored companion raced an in-flight mint into a supersession-binding
collision that evicted a consumer for four and a half hours (OMN-18881).

Two properties are load-bearing and each has its own test below:

* the terminal set is an ALLOWLIST of producer reason TOKENS. An unknown
  reason, an unreadable check-run list and a reason that merely mentions a
  token all keep waiting, because classifying an in-flight mint as terminal
  is the dangerous direction -- it tells a lane to hand-author a companion
  into a race.
* every new behaviour is off unless the caller passes
  ``terminal_decline_fast_exit``. The canary caller sets it; every other
  caller on the fleet keeps today's behaviour, byte for byte, until the
  follow-up removes the flag.

Reason strings below are the LIVE producer output, read from the
``occ-autobind / outcome`` check-runs on omnibase_infra#3873 (a real terminal
decline), omnibase_infra#3872 and omnimarket#2702 (the mislabel: a DECLINED
outcome on a path that in fact succeeded) on 2026-09-20.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.occ_preflight_wait import (
    AUTOBIND_TERMINAL_DECLINE_REASONS,
    EnumAutobindReadStatus,
    EnumPreflightWaitOutcome,
    GhCli,
    ModelAutobindOutcomeRead,
    decide_preflight_wait,
    is_terminal_decline,
)

pytestmark = pytest.mark.unit

DEADLINE = 1500
INTERVAL = 30

# Live, 2026-09-20, omnibase_infra#3873 head fba0ed54.
TERMINAL_NO_RED = (
    "skip:NO_RED_DERIVABLE_CHECK — OmniNode-ai/omnibase_infra#3873: no "
    "changed-file candidate is RED-derivable against the merge base; "
    "hand-authored evidence is required (OMN-15247) | OCC companion NOT "
    "verified: no OCC companion verifier wired; fail-closed (cannot prove "
    "the companion was pushed)"
)

# The producer's other terminal stand-down: it found a contending companion
# and deliberately left the authoring to a hand.
TERMINAL_DEFER = (
    "skip:DEFER_HAND_AUTHORED — OmniNode-ai/omnimarket#2627: a contending "
    "companion for OMN-15247 is already open (OMN-15247)"
)

# THE dangerous input. A second producer holds the mint lease for this exact
# head SHA, so a companion is being written RIGHT NOW. Reading this as
# terminal is what produced the OMN-18881 collision.
IN_FLIGHT_LEASE_HELD = (
    "skip:LEASE_HELD — OmniNode-ai/omnimarket#2627@1346e01f companion "
    "already being minted by another producer (OMN-14793 / OMN-14783)"
)

# Live, 2026-09-20, omnibase_infra#3872 head 9410e689 and omnimarket#2702
# head 34615a6e. The producer reports DECLINED on a path that SUCCEEDED --
# the companion exists and the stamp is already on the body.
MISLABELLED_SUCCESS = (
    "no-op: OmniNode-ai/omnibase_infra#3872 already bound to OCC#10522 "
    "(Evidence-Source already an OCC source) | OCC companion NOT verified: "
    "no OCC companion verifier wired; fail-closed (cannot prove the "
    "companion was pushed)"
)

# Live, 2026-09-20T11:56:20Z, on THIS change's own pull request
# (omnibase_core#1724, head 8ca0290e). The SECOND mislabel shape, and the
# sharper one: the producer reports DECLINED on the path where it SUCCEEDED
# in authoring a companion, naming the companion it just created. Reading
# this as terminal would fail the very PRs autobind has served correctly.
MISLABELLED_AUTHORED = (
    "authored OCC companion Evidence-Source: OCC#10542 for OMN-18647 on "
    "OmniNode-ai/omnibase_core#1724 (product head "
    "8ca0290e783f55afbcb819ccafc8949a584b136b, branch "  # pragma: allowlist secret
    "auto/omninode-ai-omnibase_core-pr-1724-occ-autobind) | OCC companion "
    "NOT verified: no OCC companion verifier wired; fail-closed (cannot "
    "prove the companion was pushed)"
)

NO_STAMP_BODY = "A PR description carrying no evidence-source stamp."


def _decide(
    *,
    autobind: ModelAutobindOutcomeRead | None = None,
    pr_body: str | None = NO_STAMP_BODY,
    elapsed_seconds: int = 0,
    fast_exit: bool = True,
) -> Any:
    outcome_tuple = None
    read_failed = False
    if autobind is not None:
        if autobind.status is EnumAutobindReadStatus.READ:
            outcome_tuple = (autobind.outcome, autobind.reason)
        elif autobind.status is EnumAutobindReadStatus.UNREADABLE:
            read_failed = True
    return decide_preflight_wait(
        pr_body=pr_body,
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=elapsed_seconds,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=outcome_tuple,
        autobind_read_failed=read_failed,
        terminal_decline_fast_exit=fast_exit,
    )


def _read(outcome: str, reason: str) -> ModelAutobindOutcomeRead:
    return ModelAutobindOutcomeRead(
        status=EnumAutobindReadStatus.READ, outcome=outcome, reason=reason
    )


# ---------------------------------------------------------------------------
# Arm 1 -- a terminal decline bound to this head SHA stops immediately.
# ---------------------------------------------------------------------------


def test_no_red_derivable_decline_is_terminal_and_does_not_wait() -> None:
    """AC1. The exact failure that cost six PRs 25 minutes each."""
    decision = _decide(autobind=_read("DECLINED", TERMINAL_NO_RED))
    assert decision.outcome is EnumPreflightWaitOutcome.DECLINED_TERMINAL
    assert decision.reason == "autobind_declined_terminal"
    assert decision.is_terminal_failure
    assert not decision.should_continue_polling


def test_defer_hand_authored_decline_is_terminal() -> None:
    decision = _decide(autobind=_read("DECLINED", TERMINAL_DEFER))
    assert decision.outcome is EnumPreflightWaitOutcome.DECLINED_TERMINAL
    assert decision.is_terminal_failure


def test_terminal_decline_names_the_reason_and_the_hand_authoring_path() -> None:
    """AC3-shaped: the author must read the producer's reason, not a timeout.

    The old text said only ``stamp_absent -- poll deadline (1500s) reached``,
    which names a symptom and points at an outage that is not happening.
    """
    detail = _decide(autobind=_read("DECLINED", TERMINAL_NO_RED)).detail
    assert "NO_RED_DERIVABLE_CHECK" in detail
    assert "OMN-15247" in detail
    assert "poll deadline" not in detail


def test_terminal_decline_says_hand_authoring_is_safe_and_needs_a_second_lane() -> None:
    """The producer has stood down for this head SHA, so there is no mint to
    race -- and the companion may not be signed by the ticket's own author."""
    detail = _decide(autobind=_read("DECLINED", TERMINAL_NO_RED)).detail.lower()
    assert "safe" in detail
    assert "different lane" in detail or "another lane" in detail


def test_terminal_decline_is_immediate_at_zero_elapsed_seconds() -> None:
    """Seconds, not 1500 s: the verdict cannot depend on the elapsed clock."""
    for elapsed in (0, 1, INTERVAL, DEADLINE - 1, DEADLINE, DEADLINE + 900):
        decision = _decide(
            autobind=_read("DECLINED", TERMINAL_NO_RED), elapsed_seconds=elapsed
        )
        assert decision.outcome is EnumPreflightWaitOutcome.DECLINED_TERMINAL
        assert "poll deadline" not in decision.detail


# ---------------------------------------------------------------------------
# Arm 2 -- an in-flight mint keeps waiting. THE NEGATIVE CONTROL.
# ---------------------------------------------------------------------------


def test_negative_control_lease_held_is_never_terminal() -> None:
    """THE dangerous direction, and the one this whole allowlist exists for.

    ``skip:LEASE_HELD`` means a second producer holds the mint lease for this
    exact head SHA: a companion is being written as the gate reads this. On
    2026-09-20 a lane hand-authored into that window, OCC#10524 collided with
    the in-flight mint, ``SupersessionCheckBindingError`` fired 166 times and
    the ``node_occ_companion_effect`` consumer was evicted for four and a half
    hours (OMN-18881). A verdict of terminal here is that incident.
    """
    decision = _decide(autobind=_read("DECLINED", IN_FLIGHT_LEASE_HELD))
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.outcome is not EnumPreflightWaitOutcome.DECLINED_TERMINAL
    assert decision.should_continue_polling
    assert not is_terminal_decline(IN_FLIGHT_LEASE_HELD)


def test_negative_control_unknown_decline_reason_keeps_waiting() -> None:
    """The set is an allowlist: a reason nobody has classified waits, and a
    new producer token cannot silently start failing PRs on the day it ships.
    """
    for reason in (
        "skip:SOMETHING_NOBODY_HAS_CLASSIFIED_YET — new producer token",
        "skip:OCC_SELF_COMPANION — an OCC PR needs no companion",
        "",
        "   ",
    ):
        decision = _decide(autobind=_read("DECLINED", reason))
        assert decision.outcome is EnumPreflightWaitOutcome.WAIT, reason
        assert not is_terminal_decline(reason), reason


def test_negative_control_minted_and_error_are_never_terminal_declines() -> None:
    """Only DECLINED is eligible. A MINTED outcome is the success path and an
    ERROR is the producer's own retryable failure -- neither may fast-fail."""
    for outcome_word in ("MINTED", "ERROR", "declined_but_not_really", "UNKNOWN"):
        decision = _decide(autobind=_read(outcome_word, TERMINAL_NO_RED))
        assert decision.outcome is not EnumPreflightWaitOutcome.DECLINED_TERMINAL, (
            outcome_word
        )


def test_mislabelled_success_decline_is_not_terminal() -> None:
    """The live mislabel: the producer writes DECLINED with a ``no-op: ...
    already bound to OCC#N`` reason on a path where the companion EXISTS.
    Reading that as terminal would fail a PR whose evidence is already in
    place. Seen on three PRs, last omnimarket#2702 at 10:12:47Z 2026-09-20.
    """
    decision = _decide(autobind=_read("DECLINED", MISLABELLED_SUCCESS))
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert not is_terminal_decline(MISLABELLED_SUCCESS)


def test_mislabelled_authored_companion_decline_is_not_terminal() -> None:
    """The second live mislabel, reproduced on this change's own pull request.

    The producer emitted DECLINED with a reason beginning ``authored OCC
    companion`` while having just authored OCC#10542. The stamp lands on the
    body moments later, so the correct verdict is to wait for it. An
    allowlist gives that for free; a denylist of "reasons that look
    permanent" would have failed this PR on its own change.
    """
    decision = _decide(autobind=_read("DECLINED", MISLABELLED_AUTHORED))
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert not is_terminal_decline(MISLABELLED_AUTHORED)


def test_in_flight_wait_text_warns_that_hand_authoring_is_unsafe() -> None:
    """Arm 2's text. The waiter is the surface a lane reads before deciding to
    hand-author, so the unsafe window must be named where that decision is
    made, with the incident ticket."""
    detail = _decide(autobind=None).detail
    assert "OMN-18881" in detail
    assert "unsafe" in detail.lower()


def test_absent_outcome_still_waits_and_still_hits_the_deadline() -> None:
    """Arm 2 end to end: no outcome recorded yet is the ordinary in-flight
    case, and it still fails closed at the deadline rather than passing."""
    waiting = _decide(autobind=None, elapsed_seconds=0)
    assert waiting.outcome is EnumPreflightWaitOutcome.WAIT
    assert waiting.reason == "stamp_absent"

    expired = _decide(autobind=None, elapsed_seconds=DEADLINE)
    assert expired.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert expired.is_terminal_failure


# ---------------------------------------------------------------------------
# Arm 4 -- unreadable is not absent, and is never a decline.
# ---------------------------------------------------------------------------


def test_unreadable_outcome_waits_and_is_distinguishable_from_absent() -> None:
    """A rate limit, a 5xx or malformed JSON is a fact we could not READ. It
    must not read as ``the producer said nothing`` and must never read as a
    decline. omnibase_infra#3874 carried exactly this on 2026-09-20: the
    producer's own outcome was an ERROR whose reason was a 403 rate limit.
    """
    unreadable = ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
    decision = _decide(autobind=unreadable)
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "autobind_outcome_unreadable"
    assert decision.reason != "stamp_absent"
    assert "unreadable" in decision.detail.lower()


def test_unreadable_outcome_fails_closed_at_the_deadline() -> None:
    """Fail CLOSED, exactly as today -- an unreadable producer surface is not
    a pass, it is a wait that runs out."""
    unreadable = ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
    decision = _decide(autobind=unreadable, elapsed_seconds=DEADLINE)
    assert decision.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert decision.is_terminal_failure
    assert decision.reason == "autobind_outcome_unreadable"


def test_unreadable_body_still_fails_now_whatever_the_outcome_says() -> None:
    """An unreadable PR body is terminal ahead of any producer read, and a
    terminal decline does not change that -- the body is the surface the
    stamp lands on."""
    decision = _decide(
        autobind=_read("DECLINED", TERMINAL_NO_RED),
        pr_body=None,
    )
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "body_unreadable"


# ---------------------------------------------------------------------------
# Arm 3 and arm 5 -- the success path and the scope of the exemption.
# ---------------------------------------------------------------------------


def test_a_present_stamp_is_evaluated_on_its_evidence_not_on_the_outcome() -> None:
    """A terminal decline never overrides evidence the PR actually cites: the
    producer's outcome is consulted in the stamp-absent branch and nowhere
    else. A lane that hand-authors after a decline lands here."""
    decision = decide_preflight_wait(
        pr_body="Evidence-Source: OCC#10524",
        companion_state="MERGED",
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", TERMINAL_NO_RED),
        terminal_decline_fast_exit=True,
    )
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "evidence_durable"


def test_the_terminal_set_does_not_include_the_pin_only_exemption() -> None:
    """Arm 5. The OMN-18848 pin-only reason is a PASS, not a terminal failure,
    and widening either set into the other is a fleet-wide behaviour change.
    """
    assert "skip:DEPENDENCY_PIN_ONLY" not in AUTOBIND_TERMINAL_DECLINE_REASONS
    assert set(AUTOBIND_TERMINAL_DECLINE_REASONS) == {
        "skip:NO_RED_DERIVABLE_CHECK",
        "skip:DEFER_HAND_AUTHORED",
    }


def test_pin_only_outcome_is_still_not_required_not_terminal() -> None:
    decision = _decide(
        autobind=_read(
            "DECLINED",
            "skip:DEPENDENCY_PIN_ONLY — OmniNode-ai/omnimarket#2685: no "
            "companion required: dependency-pin-only diff (OMN-18848)",
        )
    )
    assert decision.outcome is EnumPreflightWaitOutcome.NOT_REQUIRED


def test_predicate_matches_the_token_at_the_start_never_prose_about_it() -> None:
    """Rule 15's shape, at the classifier: a message DESCRIBING the token --
    'the classifier considered skip:NO_RED_DERIVABLE_CHECK and rejected it' --
    must not read as the producer declaring it."""
    assert is_terminal_decline(TERMINAL_NO_RED)
    assert is_terminal_decline("  skip:DEFER_HAND_AUTHORED — padded  ")
    assert not is_terminal_decline(
        "considered skip:NO_RED_DERIVABLE_CHECK and rejected that classification"
    )
    assert not is_terminal_decline(
        "no-op: bound already, unlike skip:DEFER_HAND_AUTHORED"
    )


# ---------------------------------------------------------------------------
# The canary contract -- with the flag off, nothing changes for any caller.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        TERMINAL_NO_RED,
        TERMINAL_DEFER,
        IN_FLIGHT_LEASE_HELD,
        MISLABELLED_SUCCESS,
        MISLABELLED_AUTHORED,
    ],
)
def test_flag_off_keeps_every_decline_on_the_old_waiting_path(reason: str) -> None:
    """The canary is only a canary if every un-pinned caller is unchanged.
    With the flag absent, every input above returns today's verdict.
    """
    decision = _decide(autobind=_read("DECLINED", reason), fast_exit=False)
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"
    assert "OMN-18881" not in decision.detail


def test_flag_off_keeps_an_unreadable_read_indistinguishable_from_absent() -> None:
    unreadable = ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
    decision = _decide(autobind=unreadable, fast_exit=False)
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"


def test_flag_defaults_to_off() -> None:
    """A caller that passes nothing gets today's behaviour. This is the
    property the fleet relies on between this merge and the follow-up."""
    decision = decide_preflight_wait(
        pr_body=NO_STAMP_BODY,
        companion_state=None,
        cited_sha_is_ancestor=False,
        elapsed_seconds=0,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
        autobind_outcome=("DECLINED", TERMINAL_NO_RED),
    )
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "stamp_absent"


# ---------------------------------------------------------------------------
# The read is bound to the CURRENT head SHA, and sees past 100 check-runs.
# ---------------------------------------------------------------------------


class _RecordingGh(GhCli):
    """A GhCli whose single subprocess seam is replaced by canned output."""

    def __init__(self, responses: dict[str, str | None]) -> None:
        self.calls: list[list[str]] = []
        self._responses = responses

    def _run(self, argv: list[str]) -> str | None:  # type: ignore[override]
        self.calls.append(argv)
        for needle, response in self._responses.items():
            if any(needle in part for part in argv):
                return response
        return None


def _outcome_check_run(*, summary: str) -> dict[str, Any]:
    return {
        "name": "occ-autobind / outcome",
        "status": "completed",
        "completed_at": "2026-09-20T07:47:56Z",
        "output": {"summary": summary},
    }


def test_the_outcome_read_is_bound_to_the_live_head_sha() -> None:
    """A stale outcome recorded against an EARLIER head is never consulted:
    the check-runs URL is built from the head SHA read live in the same round,
    so an older head's verdict is not reachable from this call at all.
    """
    # A real commit SHA (omnibase_infra#3874's head on 2026-09-20), not a
    # credential -- this is the value the URL is asserted to carry.
    head = "cd2e98af9b539a748a725624d76a45eca4816429"  # pragma: allowlist secret
    stale_head = "0000000000000000000000000000000000000000"
    client = _RecordingGh(
        {
            "headRefOid": head,
            f"commits/{head}/check-runs": json.dumps(
                [
                    _outcome_check_run(
                        summary=f"occ-autobind-outcome: DECLINED reason={TERMINAL_NO_RED}"
                    )
                ]
            ),
            f"commits/{stale_head}/check-runs": json.dumps(
                [_outcome_check_run(summary="occ-autobind-outcome: MINTED reason=ok")]
            ),
        }
    )
    result = client.read_autobind_outcome(
        repo="OmniNode-ai/omnibase_infra", pr_number="3873"
    )
    assert result.status is EnumAutobindReadStatus.READ
    assert result.outcome == "DECLINED"
    check_run_calls = [c for c in client.calls if any("check-runs" in p for p in c)]
    assert check_run_calls, "expected a check-runs read"
    for call in check_run_calls:
        rendered = " ".join(call)
        assert head in rendered
        assert stale_head not in rendered


def test_the_outcome_read_survives_a_pr_with_more_than_one_page_of_checks() -> None:
    """omnibase_infra#3874 carried 233 check-runs on 2026-09-20 and its
    ``occ-autobind / outcome`` sat on page 2, so the old single-page read
    returned ABSENT for a PR whose outcome existed. A terminal-decline arm
    that cannot see the outcome on a busy PR does not fix anything.
    """
    head = "fba0ed54" + "0" * 32
    client = _RecordingGh(
        {
            "headRefOid": head,
            "check-runs": json.dumps(
                [
                    _outcome_check_run(
                        summary=f"occ-autobind-outcome: DECLINED reason={TERMINAL_NO_RED}"
                    )
                ]
            ),
        }
    )
    result = client.read_autobind_outcome(
        repo="OmniNode-ai/omnibase_infra", pr_number="3874"
    )
    assert result.status is EnumAutobindReadStatus.READ
    check_run_calls = [c for c in client.calls if any("check-runs" in p for p in c)]
    rendered = " ".join(check_run_calls[0])
    assert "check_name" in rendered, (
        "the outcome read must select the check-run by NAME server-side; a "
        "single unpaginated per_page=100 page silently misses it on a busy PR"
    )


def test_an_unreadable_check_run_list_reports_unreadable_not_absent() -> None:
    head = "fba0ed54" + "0" * 32
    for bad in (None, "not json at all", json.dumps({"not": "a list"})):
        client = _RecordingGh({"headRefOid": head, "check-runs": bad})
        result = client.read_autobind_outcome(
            repo="OmniNode-ai/omnibase_infra", pr_number="3873"
        )
        assert result.status is EnumAutobindReadStatus.UNREADABLE, bad


def test_a_readable_list_with_no_outcome_check_reports_absent() -> None:
    """The distinction arm 4 turns on: we asked, we got an answer, and the
    answer was that the producer has not reported yet."""
    head = "fba0ed54" + "0" * 32
    client = _RecordingGh({"headRefOid": head, "check-runs": json.dumps([])})
    result = client.read_autobind_outcome(
        repo="OmniNode-ai/omnibase_infra", pr_number="3873"
    )
    assert result.status is EnumAutobindReadStatus.ABSENT


def test_an_unreadable_head_sha_reports_unreadable() -> None:
    client = _RecordingGh({"headRefOid": None})
    result = client.read_autobind_outcome(
        repo="OmniNode-ai/omnibase_infra", pr_number="3873"
    )
    assert result.status is EnumAutobindReadStatus.UNREADABLE


# ---------------------------------------------------------------------------
# Workflow shape -- the canary scoping is mechanical, not a convention.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "occ-preflight.yml"


def _workflow() -> dict[Any, Any]:
    # PyYAML (YAML 1.1) parses the bare `on:` key as the boolean True.
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _workflow_call_inputs() -> dict[str, Any]:
    workflow = _workflow()
    on_block = workflow.get(True, workflow.get("on"))
    assert isinstance(on_block, dict)
    inputs = on_block["workflow_call"]["inputs"]
    assert isinstance(inputs, dict)
    return inputs


def _resolve_evidence_source_step() -> dict[str, Any]:
    for step in _workflow()["jobs"]["eligibility"]["steps"]:
        if step.get("id") == "resolve_evidence_source":
            assert isinstance(step, dict)
            return step
    raise AssertionError("no 'resolve_evidence_source' step in occ-preflight.yml")


def test_the_fast_exit_input_exists_and_defaults_to_the_old_behaviour() -> None:
    """The canary contract, mechanically. A default of true would flip every
    caller on the fleet in one merge, which is the thing the operator ruling
    of 2026-09-20 forbade."""
    inputs = _workflow_call_inputs()
    assert "terminal-decline-fast-exit" in inputs
    declared = inputs["terminal-decline-fast-exit"]
    assert declared.get("type") == "boolean"
    assert declared.get("default") is False
    assert declared.get("required") is False


def test_the_fast_exit_input_reaches_the_waiter_as_a_cli_flag() -> None:
    """An input nothing threads through is decoration. Walk the step: the
    input must reach the env block and the flag must reach the argv."""
    step = _resolve_evidence_source_step()
    rendered_env = str(step.get("env"))
    assert "inputs.terminal-decline-fast-exit" in rendered_env
    run_block = str(step.get("run"))
    assert "--terminal-decline-fast-exit" in run_block


def test_the_flag_is_omitted_entirely_when_the_caller_did_not_ask() -> None:
    """Not ``--terminal-decline-fast-exit=false``: the argv a default caller
    runs must be byte-identical to the one it ran before this input existed,
    so the flag is conditionally ASSEMBLED rather than always passed."""
    run_block = str(_resolve_evidence_source_step().get("run"))
    assert 'if [ "$TERMINAL_DECLINE_FAST_EXIT" = "true" ]' in run_block
    assert "--terminal-decline-fast-exit=" not in run_block
