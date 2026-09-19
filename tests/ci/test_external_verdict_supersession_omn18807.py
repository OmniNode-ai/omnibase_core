# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI Summary waits a bounded window for a red external context (OMN-18807).

WHAT IS UNDER TEST
    The REAL L4 external-context resolution in ``scripts/ci/ci_summary_gate.py``,
    imported as the module CI runs.

THE INCIDENT
    ``CI Summary`` records a terminal FAILURE on an external context that is
    red only because the change-control evidence companion has not been minted
    yet, and then never re-polls. On a ticketed PR the companion is minted by
    AUTOMATION after the PR opens; until it lands the PR body carries no
    evidence-source stamp and the Receipt Gate is legitimately red. When the
    companion merges, automation PATCHes the PR body, the body edit re-fires
    every workflow whose ``types:`` include ``edited``, and the Receipt Gate
    re-runs and goes green ON ITS OWN. By then ``CI Summary`` has already
    exited, and the armed auto-merge is held by a verdict no longer true of the
    head. Only a human rerun cleared it, and that rerun passed with NO CHANGE
    TO THE PR.

    Measured in ``omnibase_infra`` over 30 merged ``dev`` PRs: 16 exhibited the
    shape, every one recovered, the slowest in 6.8 minutes, the median in 1.9.
    Landed there as ``#3793`` (squash ``69ba4fc5``); this is the port into this
    repository's own copy, which had none of it.

THE SECOND DEFECT, AND IT IS NOT THE SAME ONE
    OMN-16332 asked whether each vendored copy resolves same-name check-run
    rows safely. This one did not. ``_external_check_states`` kept the row with
    the greatest ``started_at`` and broke a TIE by keeping whichever row came
    LAST IN THE PAYLOAD ARRAY. ``started_at`` is second-granular and the
    check-runs endpoint guarantees no ordering, so a stale failure arriving
    last silently outranked a same-second success.
    :class:`TestNewestAttemptSelection` pins the repaired ``(started_at, id)``
    rule, and every case in it runs with both windows deliberately EXPIRED so
    it proves resolution on its own rather than riding on a grace.

THIS DOES NOT REOPEN THE SKIP-AS-PASS VECTOR (OMN-15057 / OMN-14854)
    That vector is ``skipped`` read as SUCCESS.
    :class:`TestSkippedIsNeverSuccess` is the control: a skip is held pending,
    a real verdict may supersede it, and if none arrives it FAILS at the
    window.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.ci import ci_summary_gate as gate
from scripts.ci.ci_summary_gate import (
    CANCELLED_SUPERSESSION_GRACE_S,
    EXTERNAL_FAILURE_SUPERSESSION_GRACE_S,
    SUPERSEDABLE_CONCLUSIONS,
    JobState,
    cancellation_is_provisional,
    evaluate_external,
    provisional_external_verdicts,
    supersedable_verdict_is_provisional,
    verdict_is_provisional,
)

pytestmark = pytest.mark.unit

CONTEXT = "verify / verify"
HEAD = "c" * 40
NOW = datetime(2026, 9, 19, 3, 5, 36, tzinfo=UTC)

#: Far enough past every window that no case in a class using it can pass
#: because of a grace rather than because of the property under test.
EXPIRED_S = EXTERNAL_FAILURE_SUPERSESSION_GRACE_S + 3600


def _z(when: datetime) -> str:
    return when.isoformat().replace("+00:00", "Z")


def _row(
    conclusion: str | None,
    *,
    age_s: float,
    run_id: int = 1,
    name: str = CONTEXT,
    status: str = "completed",
    started_age_s: float | None = None,
    completed_at: str | None | object = ...,
) -> dict[str, object]:
    """One check-run row that concluded ``age_s`` seconds before :data:`NOW`."""

    completed = NOW - timedelta(seconds=age_s)
    started = NOW - timedelta(
        seconds=age_s + 30 if started_age_s is None else started_age_s
    )
    row: dict[str, object] = {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "id": run_id,
        "head_sha": HEAD,
        "started_at": _z(started),
        "completed_at": _z(completed) if completed_at is ... else completed_at,
    }
    if status != "completed":
        row["conclusion"] = None
        row["completed_at"] = None
    return row


def _state(
    conclusion: str | None, *, age_s: float, completed_at: str | None | object = ...
) -> JobState:
    completed = NOW - timedelta(seconds=age_s)
    return JobState(
        name=CONTEXT,
        status="completed",
        conclusion=conclusion,
        run_attempt=1,
        completed_at=_z(completed) if completed_at is ... else completed_at,
    )


def _external(
    rows: list[dict[str, object]], *, now: datetime | None = NOW
) -> tuple[list[str], list[str]]:
    return evaluate_external(rows, expected=(CONTEXT,), now=now)


class TestAFreshRedIsPendingNotFailed:
    """AC1 -- the behaviour the ticket exists for."""

    @pytest.mark.parametrize("conclusion", ["failure", "skipped", "cancelled"])
    def test_inside_its_window_the_context_is_pending(self, conclusion: str) -> None:
        failures, pending = _external([_row(conclusion, age_s=38)])
        assert failures == []
        assert pending == [CONTEXT]

    @pytest.mark.parametrize("conclusion", ["failure", "skipped", "cancelled"])
    def test_outside_its_window_it_still_fails(self, conclusion: str) -> None:
        failures, pending = _external([_row(conclusion, age_s=EXPIRED_S)])
        assert failures == [CONTEXT]
        assert pending == []

    def test_the_two_windows_are_separate_and_the_cancelled_one_is_shorter(
        self,
    ) -> None:
        assert CANCELLED_SUPERSESSION_GRACE_S < EXTERNAL_FAILURE_SUPERSESSION_GRACE_S
        between = CANCELLED_SUPERSESSION_GRACE_S + 60
        assert not cancellation_is_provisional(_state("cancelled", age_s=between), NOW)
        assert supersedable_verdict_is_provisional(
            _state("failure", age_s=between), NOW
        )

    def test_the_supersedable_set_is_failure_and_skipped_only(self) -> None:
        assert frozenset({"failure", "skipped"}) == SUPERSEDABLE_CONCLUSIONS

    def test_the_pending_reason_is_reported_distinctly(self) -> None:
        held = provisional_external_verdicts(
            [_row("failure", age_s=38)], expected=(CONTEXT,), now=NOW
        )
        assert held == [CONTEXT]
        _code, report = gate.evaluate(
            [],
            external_check_runs=[_row("failure", age_s=38)],
            external_contexts=(CONTEXT,),
            now=NOW,
        )
        assert "awaiting an automatic replacement" in report

    def test_a_settled_red_is_not_reported_as_awaiting_anything(self) -> None:
        assert (
            provisional_external_verdicts(
                [_row("failure", age_s=EXPIRED_S)], expected=(CONTEXT,), now=NOW
            )
            == []
        )


class TestUngracedConclusionsStayTerminal:
    """``timed_out`` and ``action_required`` are not a re-run shape."""

    @pytest.mark.parametrize("conclusion", ["timed_out", "action_required", "neutral"])
    @pytest.mark.parametrize("age_s", [0, 38, 601, 1201])
    def test_they_fail_on_the_poll_that_observes_them(
        self, conclusion: str, age_s: float
    ) -> None:
        assert not verdict_is_provisional(_state(conclusion, age_s=age_s), NOW)
        failures, _pending = _external([_row(conclusion, age_s=age_s)])
        assert failures == [CONTEXT]


class TestFailClosedOnUncertainty:
    """AC4 -- every uncertain input restores the strict pre-grace reading."""

    @pytest.mark.parametrize("conclusion", ["failure", "skipped", "cancelled"])
    def test_no_clock_fails_now(self, conclusion: str) -> None:
        assert not verdict_is_provisional(_state(conclusion, age_s=38), None)
        failures, _pending = _external([_row(conclusion, age_s=38)], now=None)
        assert failures == [CONTEXT]

    @pytest.mark.parametrize("completed_at", [None, "", "not-a-timestamp"])
    def test_an_unreadable_completion_time_fails_now(
        self, completed_at: str | None
    ) -> None:
        assert not verdict_is_provisional(
            _state("failure", age_s=38, completed_at=completed_at), NOW
        )
        failures, _pending = _external(
            [_row("failure", age_s=38, completed_at=completed_at)]
        )
        assert failures == [CONTEXT]

    def test_a_completion_far_in_the_future_fails_now(self) -> None:
        skewed = -(EXTERNAL_FAILURE_SUPERSESSION_GRACE_S + 60)
        assert not verdict_is_provisional(_state("failure", age_s=skewed), NOW)
        failures, _pending = _external([_row("failure", age_s=skewed)])
        assert failures == [CONTEXT]

    def test_ordinary_clock_skew_stays_provisional(self) -> None:
        """A ``completed_at`` seconds in the future is skew, not a wrong clock."""
        assert verdict_is_provisional(_state("failure", age_s=-5), NOW)

    def test_an_absent_context_is_pending_never_green(self) -> None:
        failures, pending = _external([])
        assert failures == []
        assert pending == [CONTEXT]

    def test_a_still_running_context_is_pending_never_green(self) -> None:
        failures, pending = _external([_row(None, age_s=0, status="in_progress")])
        assert failures == []
        assert pending == [CONTEXT]


class TestSkippedIsNeverSuccess:
    """AC3 -- the control on the skip-as-pass vector (OMN-15057 / OMN-14854)."""

    @pytest.mark.parametrize(
        ("age_s", "now"),
        [(38, None), (38, NOW), (EXPIRED_S, NOW)],
        ids=["no-clock", "inside-grace", "past-grace"],
    )
    def test_a_lone_skip_never_resolves_the_context(
        self, age_s: float, now: datetime | None
    ) -> None:
        failures, pending = _external([_row("skipped", age_s=age_s)], now=now)
        assert failures or pending, "a lone skip must never resolve the context"

    def test_a_lone_skip_fails_once_the_window_expires(self) -> None:
        failures, pending = _external([_row("skipped", age_s=EXPIRED_S)])
        assert failures == [CONTEXT]
        assert pending == []

    def test_a_real_success_supersedes_a_fresh_skip(self) -> None:
        failures, pending = _external(
            [_row("skipped", age_s=38, run_id=1), _row("success", age_s=0, run_id=2)]
        )
        assert (failures, pending) == ([], [])


class TestNewestAttemptSelection:
    """AC2 -- resolution by ``(started_at, id)``, with every window EXPIRED.

    Nothing in this class can pass because a window held a row provisional:
    every row is older than :data:`EXPIRED_S`.
    """

    def test_a_newer_success_beats_a_stale_failure(self) -> None:
        failures, pending = _external(
            [
                _row("failure", age_s=EXPIRED_S + 600, run_id=1),
                _row("success", age_s=EXPIRED_S, run_id=2),
            ]
        )
        assert (failures, pending) == ([], [])

    def test_payload_row_order_does_not_decide(self) -> None:
        failures, _pending = _external(
            [
                _row("success", age_s=EXPIRED_S, run_id=2),
                _row("failure", age_s=EXPIRED_S + 600, run_id=1),
            ]
        )
        assert failures == []

    def test_a_tied_started_at_is_broken_by_the_check_run_id_not_array_order(
        self,
    ) -> None:
        """The OMN-16332 defect in this copy, stated as a test.

        Both rows carry the SAME second-granular ``started_at``. Before this
        change the resolver kept whichever came last in the array, so the
        stale failure below won by position. The monotonically increasing
        check-run ``id`` decides it now.
        """

        tied = EXPIRED_S
        failures, _pending = _external(
            [
                _row("success", age_s=tied, run_id=2, started_age_s=tied),
                _row("failure", age_s=tied, run_id=1, started_age_s=tied),
            ]
        )
        assert failures == []

    def test_a_tied_started_at_with_the_failure_newer_still_fails(self) -> None:
        """The same tie resolved the other way round is a genuine red."""

        tied = EXPIRED_S
        failures, _pending = _external(
            [
                _row("success", age_s=tied, run_id=1, started_age_s=tied),
                _row("failure", age_s=tied, run_id=2, started_age_s=tied),
            ]
        )
        assert failures == [CONTEXT]

    def test_a_row_with_no_id_loses_a_tie_to_one_that_has_an_id(self) -> None:
        """An absent id sorts as 0 rather than winning by position."""

        tied = EXPIRED_S
        stale = _row("failure", age_s=tied, started_age_s=tied)
        del stale["id"]
        fresh = _row("success", age_s=tied, run_id=7, started_age_s=tied)
        assert _external([fresh, stale])[0] == []
        assert _external([stale, fresh])[0] == []

    def test_a_newer_running_attempt_is_pending_not_a_stale_failure(self) -> None:
        failures, pending = _external(
            [
                _row("failure", age_s=EXPIRED_S + 600, run_id=1),
                _row(None, age_s=EXPIRED_S, run_id=2, status="in_progress"),
            ]
        )
        assert failures == []
        assert pending == [CONTEXT]

    def test_three_attempts_resolve_on_the_newest_not_the_worst(self) -> None:
        failures, _pending = _external(
            [
                _row("success", age_s=EXPIRED_S + 1200, run_id=1),
                _row("failure", age_s=EXPIRED_S + 600, run_id=2),
                _row("success", age_s=EXPIRED_S, run_id=3),
            ]
        )
        assert failures == []

    def test_a_newer_failure_after_a_success_still_fails(self) -> None:
        failures, _pending = _external(
            [
                _row("success", age_s=EXPIRED_S + 600, run_id=1),
                _row("failure", age_s=EXPIRED_S, run_id=2),
            ]
        )
        assert failures == [CONTEXT]


class TestTheCliHandsTheGateAClock:
    """AC5 -- the un-forgeability of both windows rests on this.

    Both windows return ``False`` when ``now`` is ``None`` -- deliberate and
    fail-closed, so a caller that forgets the time enforces the old strict
    reading rather than waiting on a red forever. That is the right default and
    a terrible SILENT outcome: the first port of this change into a sibling
    repository changed the gate module and not its poller, and the gate shipped
    completely inert with every unit test green and mypy clean.

    No flag is the load-bearing half. A caller-assertable observation time
    would let a long-dead red be held provisional indefinitely, which is the
    one way these windows could become a bypass. It is asserted BEHAVIOURALLY
    -- by invoking the CLI with each candidate flag and requiring a parse error
    -- so an option added by any route is caught, not only one spelled the way
    this file guesses.
    """

    FLAGS = ("--now", "--observed-at", "--clock", "--as-of", "--at")

    @pytest.mark.parametrize("flag", FLAGS)
    def test_no_cli_option_supplies_the_observation_time(
        self, flag: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises((SystemExit, argparse.ArgumentError)):
            gate.main(["--jobs-file", "-", flag, _z(NOW)])
        captured = capsys.readouterr()
        assert "unrecognized arguments" in captured.err or "invalid" in captured.err

    def test_main_reaches_evaluate_with_a_current_aware_clock(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        jobs = tmp_path / "jobs.json"
        jobs.write_text(json.dumps([]), encoding="utf-8")

        seen: list[datetime | None] = []
        real = gate.evaluate

        def _spy(*args: object, **kwargs: object):
            seen.append(kwargs.get("now"))
            return real(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(gate, "evaluate", _spy)
        before = datetime.now(UTC)
        gate.main(["--jobs-file", str(jobs), "--report-only"])
        after = datetime.now(UTC)

        assert len(seen) == 1
        now = seen[0]
        assert isinstance(now, datetime)
        assert now.tzinfo is not None, "a naive clock cannot be compared to GitHub's"
        assert before <= now <= after, "the clock must be read at call time"
