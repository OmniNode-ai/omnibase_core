# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An advisory reviewer's ``neutral`` must not redden a head nothing is wrong with.

On 2026-11-07 omnibase_core had merged nothing for 5.4 hours with six pull
requests waiting, and four of the six non-draft ones were red on ``CI Summary``
and on NOTHING else: #2281, #2279, #2278, #2273. Two sampled jobs end on the
same line -- job 128518750571 over 53 green jobs, job 128503918804 over 71:

    CI Summary verdict: FAILURE
      external sweep failures (red, and named by NOTHING else): Tessl Reviewer (neutral)
      external sweep exclusions applied: Enable Auto-Merge
    ##[error]CI Summary = FAILURE (fail-closed: a gating job failed/cancelled)

``SWEEP_GOOD_CONCLUSIONS`` admits ``success`` alone, and the ``tessl-reviewer``
app reports ``neutral`` as its normal outcome -- its own check-run says "Tessl
Reviewer completed an advisory review" and "This repository runs Tessl Reviewer
in advisory mode, so the review doesn't block merging". A bot the repository
configured not to block was blocking every pull request. It is pull_request-only,
so the dev head never carries it and dev's own CI Summary stayed green, which is
why reading dev could not find this.

The fix is one ``EXTERNAL_SWEEP_EXCLUSIONS`` entry, the mechanism this repository
already built for a reasoned, ticketed, dated and expiring admission -- the same
shape as the four entries OMN-17427 measured. These tests pin the three
directions that matter: the advisory neutral passes, the exclusion is held to the
same validation as every other entry, and it buys nothing for any other context
or for a real red.

Deliberately NOT tested here, because deliberately NOT done: widening
``SWEEP_GOOD_CONCLUSIONS`` to accept ``neutral`` everywhere. That relaxes a
default-deny control for every swept context at once and belongs to a ruling on
OMN-18355, not to this fix.

Same cause as OMN-23029 (omnimarket) and OMN-22478 (omniclaude).

Ticket: OMN-23034
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.ci import ci_summary_gate as gate
from scripts.ci.ci_summary_gate import EXIT_FAILURE, EXIT_SUCCESS

from .test_ci_summary_gate import _ALL_EXTERNAL_GREEN, _all_good, _check_run

pytestmark = pytest.mark.unit

#: The swept context and the conclusion it reports when it has nothing to block on.
TESSL = "Tessl Reviewer"
ADVISORY = "neutral"

#: After the entry's ``added`` date and before its ``expires`` date.
NOW = datetime(2026, 11, 7, 21, tzinfo=UTC)


def _evaluate(extra: list[dict], *, now: datetime) -> tuple[int, str]:
    """Evaluate a fully-green run whose external rows carry ``extra`` as well."""
    return gate.evaluate(
        _all_good(), external_check_runs=[*_ALL_EXTERNAL_GREEN, *extra], now=now
    )


def test_the_advisory_neutral_no_longer_fails_the_sweep() -> None:
    """AC1. The live shape: one advisory neutral among otherwise green rows."""
    code, report = _evaluate([_check_run(TESSL, ADVISORY)], now=NOW)
    assert code == EXIT_SUCCESS, report
    assert f"{TESSL} ({ADVISORY})" not in report
    assert f"exclusions applied: {TESSL}" in report


def test_the_exclusion_is_registered_reasoned_ticketed_and_bounded() -> None:
    """AC2. It is held to the same validation as every other entry."""
    entry = gate.EXTERNAL_SWEEP_EXCLUSIONS[TESSL]
    assert gate.validate_sweep_exclusions({TESSL: entry}) == []
    assert entry.ticket == "OMN-22478"  # registered by #2280; this PR rides on it
    assert "neutral" in entry.reason.lower()
    assert entry.expires > entry.added

    active, expired = gate.active_sweep_exclusions({TESSL: entry}, now=NOW)
    assert active == frozenset({TESSL})
    assert expired == ()


def test_a_malformed_version_of_this_entry_is_still_refused() -> None:
    """AC2. The exclusion mechanism is not loosened by using it."""
    good = gate.EXTERNAL_SWEEP_EXCLUSIONS[TESSL]
    fields = {
        "reason": good.reason,
        "ticket": good.ticket,
        "added": good.added,
        "expires": good.expires,
    }
    for field, bad in (
        ("reason", "   "),
        ("ticket", "OMN23034"),
        ("added", "07-11-2026"),
        ("expires", ""),
    ):
        broken = gate.SweepExclusion(**{**fields, field: bad})
        assert gate.validate_sweep_exclusions({TESSL: broken}), (
            f"a {field} of {bad!r} was accepted"
        )


def test_the_entry_expires_and_the_sweep_rearms() -> None:
    """AC2. An exception nobody revisits is not an exception, it is a hole."""
    entry = gate.EXTERNAL_SWEEP_EXCLUSIONS[TESSL]
    after = datetime.fromisoformat(f"{entry.expires}T00:00:00+00:00")
    active, expired = gate.active_sweep_exclusions({TESSL: entry}, now=after)
    assert active == frozenset()
    assert expired == (TESSL,)

    code, report = _evaluate([_check_run(TESSL, ADVISORY)], now=after)
    assert code == EXIT_FAILURE, report
    assert f"{TESSL} ({ADVISORY})" in report


def test_it_buys_nothing_for_another_context_or_for_a_real_red() -> None:
    """AC3. The sweep still denies by default around the one admitted name."""
    code, report = _evaluate(
        [_check_run("Another Unregistered Gate", ADVISORY)], now=NOW
    )
    assert code == EXIT_FAILURE, report
    assert f"Another Unregistered Gate ({ADVISORY})" in report

    # A red beside the admitted name is still a red. Only the `failure` wording
    # is pinned: `cancelled` reaches the same verdict through the provisional-
    # cancellation path, which reports a due re-run instead of naming the
    # conclusion, and pinning that phrasing here would test a message rather
    # than the denial.
    for conclusion in ("failure", "cancelled", "timed_out", "action_required"):
        rows = [_check_run(TESSL, ADVISORY), _check_run("Red Gate", conclusion)]
        code, report = _evaluate(rows, now=NOW)
        assert code == EXIT_FAILURE, (conclusion, report)
        assert "Red Gate" in report, (conclusion, report)
    rows = [_check_run(TESSL, ADVISORY), _check_run("Red Gate", "failure")]
    assert "Red Gate (failure)" in _evaluate(rows, now=NOW)[1]


def test_the_excluded_name_is_not_also_an_asserted_context() -> None:
    """AC3. Excluding a name the gate asserts elsewhere would silence that too."""
    assert TESSL not in gate.EXPECTED_EXTERNAL_CONTEXTS
