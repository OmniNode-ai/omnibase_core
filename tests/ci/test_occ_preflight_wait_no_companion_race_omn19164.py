# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The Receipt Gate's pin-only probe must WAIT for the producer (OMN-19164).

OMN-18882 gave the Receipt Gate a derived, un-forgeable exemption for a
dependency-pin-only diff, and it is correct. It was unreachable in practice on
the one PR class it was written for, because it read the producer's outcome
ONCE and the producer had not posted yet.

Measured, live, on ``OmniNode-ai/omnimarket#2775``, head
``96fd645574c5ab9271913021fc53af770a361166``::

    verify / verify              2026-09-22T07:44:08Z  failure
    occ-autobind / mint status   2026-09-22T07:44:10Z  neutral  declined: dependency-pin-only
    occ-autobind / outcome       2026-09-22T07:44:12Z  neutral  DECLINED: skip:DEPENDENCY_PIN_ONLY

and on ``#2776``, the very next bump of the same shape, the same two events
landed in the other order and the gate passed. Across 24 sampled bump PRs in
two repositories, every failure was this race and the near-miss margin was 1
to 4 seconds: which way a post-release bump resolved was decided by runner
scheduling. Re-running ``verify / verify`` alone on #2775's head after the
producer had reported turned it green with no code change, which is the
diagnosis proven before any code was written.

WHAT THIS MODULE PINS, and the distinction it exists to defend: the fix is
ORDERING, NOT PERMISSION. Nothing about what qualifies for the exemption
moved. "Not reported yet" and "will never be reported" stopped being one
state; only the first waits, and the deadline still fails closed. Every test
below is either the race resolving (AC1), or a positive control proving some
refusal the fix must NOT have loosened (AC2, AC4, AC5).
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.ci.occ_preflight_wait import (
    AUTOBIND_NO_COMPANION_REQUIRED_REASONS,
    DEFAULT_NO_COMPANION_DEADLINE_SECONDS,
    DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS,
    EXIT_ERROR,
    EXIT_OK,
    EnumAutobindReadStatus,
    EnumNoCompanionProbeVerdict,
    ModelAutobindOutcomeRead,
    _build_parser,
    classify_no_companion_required,
    main,
    read_autobind_outcome_from_check_runs,
    wait_for_no_companion_required,
)

pytestmark = pytest.mark.unit

REPO = "OmniNode-ai/omnimarket"
PR_NUMBER = "2775"
# The real head of omnimarket#2775 -- a public git commit SHA, kept verbatim
# because it is the evidence this module exists for and the one a reader
# re-probes. Flagged by detect-secrets purely as a high-entropy hex string.
HEAD_SHA = "96fd645574c5ab9271913021fc53af770a361166"  # pragma: allowlist secret
OTHER_SHA = "b" * 40

PIN_ONLY_REASON = AUTOBIND_NO_COMPANION_REQUIRED_REASONS[0]


def _outcome_run(*, outcome: str, reason: str) -> dict[str, Any]:
    """One ``occ-autobind / outcome`` check-run, in the producer's own shape."""
    return {
        "name": "occ-autobind / outcome",
        "status": "completed",
        "completed_at": "2026-09-22T07:44:12Z",
        "output": {
            "summary": (
                f"occ-autobind-outcome: {outcome} repo={REPO} pr={PR_NUMBER} "
                f"correlation_id=c-1 reason={reason}\n\nHuman prose follows."
            )
        },
    }


PIN_ONLY_RUN = _outcome_run(outcome="DECLINED", reason=PIN_ONLY_REASON)


class _ScriptedGh:
    """A :class:`GhPort` that replays a SCRIPT of reads, one per poll.

    Modelling the race needs a client whose answer CHANGES between polls,
    which a static fixture cannot express. Each entry is what
    ``read_autobind_outcome`` returns on that poll; the last entry repeats
    forever, so a script ending in an absent read is a producer that never
    reports.

    Every other port method raises. The probe must consult the producer's
    check-run and nothing else -- in particular never the PR body, the one
    surface an author controls.
    """

    def __init__(self, script: list[ModelAutobindOutcomeRead]) -> None:
        assert script, "a scripted client needs at least one read"
        self.script = script
        self.reads = 0
        self.sleeps: list[float] = []

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        raise AssertionError("the pin-only probe must not read the PR body")

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
        index = min(self.reads, len(self.script) - 1)
        self.reads += 1
        return self.script[index]

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


ABSENT = ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.ABSENT)
UNREADABLE = ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)


def _read(run: dict[str, Any]) -> ModelAutobindOutcomeRead:
    parsed = read_autobind_outcome_from_check_runs([run])
    assert parsed is not None
    return ModelAutobindOutcomeRead(
        status=EnumAutobindReadStatus.READ, outcome=parsed[0], reason=parsed[1]
    )


def _wait(
    gh: _ScriptedGh,
    *,
    deadline_seconds: int = 180,
    tick_seconds: float = 5.0,
    emitted: list[str] | None = None,
) -> tuple[bool, str]:
    """Drive the real wait on a fake clock that advances only when it sleeps."""
    clock = {"now": 0.0}
    sink = emitted if emitted is not None else []

    def _sleep(seconds: float) -> None:
        gh.sleep(seconds)
        clock["now"] += tick_seconds

    return wait_for_no_companion_required(
        repo=REPO,
        pr_number=PR_NUMBER,
        client=gh,  # type: ignore[arg-type]
        deadline_seconds=deadline_seconds,
        poll_interval_seconds=5,
        sleep=_sleep,
        monotonic=lambda: clock["now"],
        emit=sink.append,
    )


# --------------------------------------------------------------------------
# AC1 -- the race resolves instead of refusing on the first read
# --------------------------------------------------------------------------


def test_absent_then_present_resolves_the_exemption() -> None:
    """THE regression. This is omnimarket#2775 exactly: the gate looks, the
    producer has not posted, the producer posts, the gate looks again. Before
    this ticket the first read was the whole probe and this PR was red."""
    gh = _ScriptedGh([ABSENT, _read(PIN_ONLY_RUN)])
    exempt, detail = _wait(gh)
    assert exempt is True
    assert gh.reads == 2, "the probe must look again after an absent read"
    assert "dependency-pin-only" in detail


def test_the_race_resolves_across_several_polls() -> None:
    """A producer slower than one poll interval is still the same race."""
    gh = _ScriptedGh([ABSENT, ABSENT, ABSENT, _read(PIN_ONLY_RUN)])
    exempt, _ = _wait(gh)
    assert exempt is True
    assert gh.reads == 4


def test_an_unreadable_read_is_retried_not_treated_as_a_verdict() -> None:
    """A failed read is not the producer declining and never becomes one. It
    waits on the same budget, because a transient transport error and the race
    are the same shape from here, and it fails closed if it never clears."""
    gh = _ScriptedGh([UNREADABLE, _read(PIN_ONLY_RUN)])
    exempt, _ = _wait(gh)
    assert exempt is True
    assert gh.reads == 2


def test_the_exempt_path_stops_polling_the_moment_it_resolves() -> None:
    gh = _ScriptedGh([ABSENT, _read(PIN_ONLY_RUN), ABSENT, ABSENT])
    exempt, _ = _wait(gh)
    assert exempt is True
    assert gh.reads == 2, "no poll may follow a resolved verdict"


def test_the_cli_resolves_the_race_end_to_end(tmp_path: Any) -> None:
    """AC1 through the entrypoint the Receipt Gate's bash actually invokes,
    including the output the workflow step reads to gate everything after it."""
    out = tmp_path / "gh_output"
    out.write_text("")
    gh = _ScriptedGh([ABSENT, _read(PIN_ONLY_RUN)])
    assert (
        main(
            [
                "--check-no-companion-required",
                "--repo",
                REPO,
                "--pr-number",
                PR_NUMBER,
                "--github-output-path",
                str(out),
                "--no-companion-deadline-seconds",
                "60",
                "--no-companion-poll-interval-seconds",
                "0",
            ],
            gh=gh,  # type: ignore[arg-type]
        )
        == EXIT_OK
    )
    assert "evidence_not_required=true" in out.read_text()


# --------------------------------------------------------------------------
# AC2 -- the head-SHA binding is untouched by the wait
# --------------------------------------------------------------------------


def test_an_outcome_bound_to_another_sha_is_still_invisible() -> None:
    """POSITIVE CONTROL. The client reads check-runs for the PR's CURRENT head
    alone, so an outcome posted on an earlier commit reads as ABSENT -- and
    now that ABSENT waits, this is the case that would silently start passing
    if the wait had been wired to a stale SHA. It must still refuse."""

    class _HeadBoundGh(_ScriptedGh):
        """Models GhCli: resolve the head, read only that SHA's check-runs."""

        def read_autobind_outcome(
            self, *, repo: str, pr_number: str
        ) -> ModelAutobindOutcomeRead:
            self.reads += 1
            runs_by_sha = {OTHER_SHA: [PIN_ONLY_RUN]}
            parsed = read_autobind_outcome_from_check_runs(
                runs_by_sha.get(HEAD_SHA, [])
            )
            if parsed is None:
                return ABSENT
            return ModelAutobindOutcomeRead(
                status=EnumAutobindReadStatus.READ,
                outcome=parsed[0],
                reason=parsed[1],
            )

    gh = _HeadBoundGh([ABSENT])
    exempt, detail = _wait(gh, deadline_seconds=20)
    assert exempt is False
    assert "current head" in detail


def test_the_head_is_re_resolved_on_every_poll() -> None:
    """A commit landing mid-wait must be read against its OWN sha: the binding
    holds across the wait rather than being snapshotted when it began. The
    client is asked afresh each poll, which is what makes that true."""
    gh = _ScriptedGh([ABSENT, ABSENT, _read(PIN_ONLY_RUN)])
    _wait(gh)
    assert gh.reads == 3, "each poll must be a fresh read, never a cached one"


# --------------------------------------------------------------------------
# AC3 -- the timeout fails closed, under its own distinct reason
# --------------------------------------------------------------------------


def test_a_producer_that_never_reports_fails_closed() -> None:
    gh = _ScriptedGh([ABSENT])
    exempt, _ = _wait(gh, deadline_seconds=20)
    assert exempt is False


def test_the_timeout_reason_is_distinct_from_the_absent_reason() -> None:
    """AC3. Both refuse, and a reader who cannot tell them apart chases the
    wrong remedy: a lost race is re-run, a genuine no-outcome case is
    hand-authored. The timeout sentence must name the budget it spent."""
    timed_out = _wait(_ScriptedGh([ABSENT]), deadline_seconds=20)[1]
    one_read = classify_no_companion_required(ABSENT).detail

    assert timed_out != one_read
    assert "budget" in timed_out and "budget" not in one_read
    assert "20s" in timed_out, "the timeout must name the budget it exhausted"
    assert "OMN-19164" in timed_out


def test_the_timeout_says_it_is_not_a_verdict_that_evidence_is_owed() -> None:
    """The refusal is honest about what it does and does not know. A timeout
    is the absence of an answer, never the producer saying a companion is
    owed, and the sentence a human reads must not imply otherwise."""
    detail = _wait(_ScriptedGh([ABSENT]), deadline_seconds=20)[1]
    assert "NOT a verdict" in detail


def test_the_timeout_exits_non_zero_through_the_cli(tmp_path: Any) -> None:
    out = tmp_path / "gh_output"
    out.write_text("")
    gh = _ScriptedGh([ABSENT])
    assert (
        main(
            [
                "--check-no-companion-required",
                "--repo",
                REPO,
                "--pr-number",
                PR_NUMBER,
                "--github-output-path",
                str(out),
                "--no-companion-deadline-seconds",
                "0",
                "--no-companion-poll-interval-seconds",
                "0",
            ],
            gh=gh,  # type: ignore[arg-type]
        )
        == EXIT_ERROR
    )
    assert "evidence_not_required" not in out.read_text(), (
        "a timed-out probe must write no output; the workflow reads that "
        "output as permission to skip the evidence requirement"
    )


def test_every_poll_it_spends_is_announced() -> None:
    """A gate that waits silently reads, in a job log, exactly like the
    one-shot probe this replaces -- so the one fact a reader debugging a slow
    producer needs (that it is WAITING, not that it has already refused) would
    be invisible precisely when it matters. Each poll says so, with its
    elapsed budget."""
    emitted: list[str] = []
    gh = _ScriptedGh([ABSENT, ABSENT, _read(PIN_ONLY_RUN)])
    exempt, _ = _wait(gh, emitted=emitted)

    assert exempt is True
    assert len(emitted) == 2, "one line per poll actually spent"
    assert all("waiting" in line for line in emitted)
    assert "0s/180s" in emitted[0] and "5s/180s" in emitted[1], (
        "each line must carry the elapsed budget, or a reader cannot tell a "
        "wait that is about to expire from one that just began"
    )


def test_a_terminal_first_read_announces_no_wait() -> None:
    """Nothing is printed about waiting when nothing waited."""
    emitted: list[str] = []
    gh = _ScriptedGh([_read(PIN_ONLY_RUN)])
    _wait(gh, emitted=emitted)
    assert emitted == []


def test_the_wait_is_bounded_and_does_not_poll_forever() -> None:
    gh = _ScriptedGh([ABSENT])
    _wait(gh, deadline_seconds=20, tick_seconds=5.0)
    assert gh.reads <= 6, f"unbounded wait: {gh.reads} reads against a 20s budget"
    assert gh.sleeps, "a wait that never slept did not actually poll"


# --------------------------------------------------------------------------
# AC4 -- every refusal the fix must NOT have loosened
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        ("MINTED", PIN_ONLY_REASON),
        ("MINTED", "minted companion"),
        ("ERROR", PIN_ONLY_REASON),
        ("DECLINED", "skip:NO_RED_DERIVABLE_CHECK"),
        ("DECLINED", "skip:DEFER_HAND_AUTHORED"),
        ("DECLINED", "skip:LEASE_HELD"),
        ("DECLINED", ""),
    ],
)
def test_a_pr_that_owes_evidence_still_fails(outcome: str, reason: str) -> None:
    """POSITIVE CONTROL for the whole ticket: a diff that is genuinely not
    pin-only, with no stamp line, is refused exactly as before. If the wait
    had been written as leniency rather than ordering, these would pass."""
    gh = _ScriptedGh([_read(_outcome_run(outcome=outcome, reason=reason))])
    exempt, _ = _wait(gh)
    assert exempt is False


def test_a_verdict_the_producer_reached_is_terminal_on_the_first_read() -> None:
    """A MINTED outcome means a companion EXISTS and is owed. No later poll
    changes that, so waiting on it would only delay a PR that must fail."""
    gh = _ScriptedGh([_read(_outcome_run(outcome="MINTED", reason="minted"))])
    exempt, _ = _wait(gh, deadline_seconds=600)
    assert exempt is False
    assert gh.reads == 1
    assert not gh.sleeps, "a verdict in hand must never be slept on"


def test_a_non_pin_decline_does_not_become_exempt_by_waiting() -> None:
    """The producer's verdict cannot be outlasted: polling past a decline
    until something else appears would be a bypass wearing a wait's clothes."""
    gh = _ScriptedGh(
        [_read(_outcome_run(outcome="DECLINED", reason="skip:NO_RED_DERIVABLE_CHECK"))]
    )
    exempt, _ = _wait(gh, deadline_seconds=600)
    assert exempt is False
    assert gh.reads == 1


def test_the_token_in_prose_only_is_still_not_exempt() -> None:
    """A summary DESCRIBING the classifier refusing must not read as the
    classifier accepting, wait or no wait."""
    gh = _ScriptedGh(
        [
            _read(
                _outcome_run(
                    outcome="DECLINED",
                    reason=f"classifier refused {PIN_ONLY_REASON}: a source file changed",
                )
            )
        ]
    )
    assert _wait(gh)[0] is False


# --------------------------------------------------------------------------
# AC5 -- no bypass surface was added
# --------------------------------------------------------------------------


def test_the_parser_declares_no_bypass_option() -> None:
    """AC5, read off the entrypoint's OWN option strings rather than by
    matching source text, so adding a bypass input is a red test rather than
    something a reviewer has to catch.

    The two options this ticket adds are knobs on the WAIT, never on the
    verdict, and neither can admit a PR the probe would otherwise refuse: a
    shorter budget only reaches the same fail-closed timeout sooner, a longer
    one only spends more seconds before the identical refusal.
    """
    options = {
        option
        for action in _build_parser()._actions
        for option in action.option_strings
    }
    forbidden = (
        "skip",
        "force",
        "bypass",
        "override",
        "allow",
        "exempt",
        "assume",
        "no-verify",
        "ignore",
        "disable",
    )
    offenders = sorted(
        option
        for option in options
        if any(word in option.lower() for word in forbidden)
    )
    assert not offenders, f"the probe declares a bypass-shaped option: {offenders}"


def test_the_probe_cannot_be_told_the_answer() -> None:
    """No option carries a health-, outcome- or verdict-shaped VALUE either.
    The exemption is DERIVED from the producer's check-run; the day a caller
    can assert it on the command line it stops being evidence."""
    options = {
        option
        for action in _build_parser()._actions
        for option in action.option_strings
    }
    assert "--autobind-outcome" not in options
    assert "--no-companion-required-value" not in options
    assert "--evidence-not-required" not in options


def test_the_live_defaults_are_the_ones_the_gate_runs_with() -> None:
    """The defaults are the live behaviour: the Receipt Gate's bash passes
    neither flag, so a test that only ever exercised an injected budget would
    prove nothing about production."""
    parsed = _build_parser().parse_args(
        ["--check-no-companion-required", "--repo", REPO, "--pr-number", PR_NUMBER]
    )
    assert parsed.no_companion_deadline_seconds == (
        DEFAULT_NO_COMPANION_DEADLINE_SECONDS
    )
    assert parsed.no_companion_poll_interval_seconds == (
        DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS
    )
    assert DEFAULT_NO_COMPANION_DEADLINE_SECONDS >= 120, (
        "the budget must clear the widest producer latency measured "
        "(~97s on omnibase_infra#3942), or the race it exists to close reopens"
    )
    assert 0 < DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS <= 15, (
        "an interval this coarse would not resolve the measured 1-4s margin"
    )


# --------------------------------------------------------------------------
# The pure classifier, exhaustively
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("read", "expected"),
    [
        (ABSENT, EnumNoCompanionProbeVerdict.INDETERMINATE),
        (UNREADABLE, EnumNoCompanionProbeVerdict.INDETERMINATE),
        (_read(PIN_ONLY_RUN), EnumNoCompanionProbeVerdict.EXEMPT),
        (
            _read(_outcome_run(outcome="MINTED", reason=PIN_ONLY_REASON)),
            EnumNoCompanionProbeVerdict.NOT_EXEMPT,
        ),
        (
            _read(_outcome_run(outcome="DECLINED", reason="skip:LEASE_HELD")),
            EnumNoCompanionProbeVerdict.NOT_EXEMPT,
        ),
    ],
)
def test_classifier_verdicts(
    read: ModelAutobindOutcomeRead, expected: EnumNoCompanionProbeVerdict
) -> None:
    assert classify_no_companion_required(read).verdict is expected


def test_only_indeterminate_is_non_terminal() -> None:
    """The property the driver's loop turns on: exactly one verdict waits."""
    waiting = [
        verdict
        for verdict in EnumNoCompanionProbeVerdict
        if not classify_no_companion_required(ABSENT)
        .__class__(verdict=verdict, detail="")
        .is_terminal
    ]
    assert waiting == [EnumNoCompanionProbeVerdict.INDETERMINATE]


def test_every_verdict_carries_a_detail_sentence() -> None:
    """The detail is contract, not decoration: it is the only thing a human
    reading a red Receipt Gate sees about why."""
    for read in (ABSENT, UNREADABLE, _read(PIN_ONLY_RUN)):
        assert classify_no_companion_required(read).detail.strip()
