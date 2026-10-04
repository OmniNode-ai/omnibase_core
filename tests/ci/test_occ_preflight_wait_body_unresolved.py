# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An unreadable PR body is retried inside the existing budget (OMN-20427).

``GhCli.read_pr_body`` returns ``None`` on a 60 s timeout, an ``OSError`` or any
non-zero ``gh`` exit. Before this change ``decide_preflight_wait`` read that one
``None`` as ``FAIL_NOW`` / ``body_unreadable``, so a single transient GitHub API
failure ended a gate that is otherwise allowed 1500 s -- while the companion
state read, which fails the same way, already waited. The body read now takes the
same shape as ``companion_state_unresolved``: ``WAIT`` with the retryable reason
``body_unresolved``, re-read on the next poll, and ``DEADLINE`` (a terminal
failure) at the unchanged budget when the body never becomes readable.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.ci import occ_preflight_wait
from scripts.ci.occ_preflight_wait import (
    DEFAULT_DEADLINE_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    EXIT_ERROR,
    EXIT_OK,
    EnumAncestryRead,
    EnumAutobindReadStatus,
    EnumPreflightWaitOutcome,
    ModelAutobindOutcomeRead,
    ModelPreflightWaitDecision,
    decide_preflight_wait,
    main,
)

pytestmark = pytest.mark.unit

DEADLINE = DEFAULT_DEADLINE_SECONDS
INTERVAL = DEFAULT_POLL_INTERVAL_SECONDS


def _decide(
    *, elapsed: int, event_name: str = "pull_request"
) -> ModelPreflightWaitDecision:
    return decide_preflight_wait(
        pr_body=None,
        companion_state=None,
        cited_sha_ancestry=EnumAncestryRead.NOT_ANCESTOR,
        elapsed_seconds=elapsed,
        deadline_seconds=DEADLINE,
        event_name=event_name,
    )


# ---------------------------------------------------------------------------
# (a), (b), (e) -- the pure verdict.
# ---------------------------------------------------------------------------


def test_unreadable_body_waits_as_body_unresolved() -> None:
    decision = _decide(elapsed=0)
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "body_unresolved"
    assert not decision.is_terminal_failure


def test_unreadable_body_waits_until_the_last_second_then_hits_the_deadline() -> None:
    last = _decide(elapsed=DEADLINE - 1)
    assert last.outcome is EnumPreflightWaitOutcome.WAIT
    assert last.reason == "body_unresolved"

    expired = _decide(elapsed=DEADLINE)
    assert expired.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert expired.reason == "body_unresolved"
    assert expired.is_terminal_failure


def test_the_budget_is_not_widened() -> None:
    assert DEFAULT_DEADLINE_SECONDS == 1500


@pytest.mark.parametrize("event_name", ["merge_group", "push", "workflow_dispatch"])
def test_non_pull_request_event_still_proceeds_with_an_unreadable_body(
    event_name: str,
) -> None:
    decision = _decide(elapsed=0, event_name=event_name)
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "non_pull_request_event"


# ---------------------------------------------------------------------------
# (c), (d) -- the polling driver, with a scripted GhPort and a fake clock.
# ---------------------------------------------------------------------------

BODY_WITH_STAMP = "## OMN-20427\n\nEvidence-Source: OCC#12345\n"


class _FakeClock:
    """``time`` stand-in: ``sleep`` advances ``monotonic`` and spends nothing."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        # A runaway loop is a failed test, not a hung one.
        assert len(self.sleeps) < 200, "poll loop did not terminate"
        self.sleeps.append(seconds)
        self.now += seconds


class _FakeGh:
    """Scripted :class:`GhPort`; ``bodies`` is consumed one read at a time and
    its last element repeats."""

    def __init__(self, bodies: list[str | None]) -> None:
        self.bodies = bodies
        self.body_reads = 0

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        index = min(self.body_reads, len(self.bodies) - 1)
        self.body_reads += 1
        return self.bodies[index]

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        return "MERGED", "0" * 40

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        return sha

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> EnumAncestryRead:
        return EnumAncestryRead.ANCESTOR

    def read_autobind_outcome(
        self, *, repo: str, pr_number: str
    ) -> ModelAutobindOutcomeRead:
        return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.ABSENT)

    def read_branch_tip(self, *, occ_repo: str, branch: str) -> str | None:
        return None

    def tip_contains_sha(self, *, occ_repo: str, tip: str, sha: str) -> bool:
        return False


def _run_main(gh: _FakeGh, clock: _FakeClock, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(
        occ_preflight_wait,
        "time",
        SimpleNamespace(monotonic=clock.monotonic, sleep=clock.sleep),
    )
    return main(
        [
            "--repo",
            "OmniNode-ai/omnibase_infra",
            "--pr-number",
            "4521",
            "--event-name",
            "pull_request",
        ],
        gh=gh,
    )


def test_main_rereads_the_body_and_proceeds_once_it_is_readable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gh = _FakeGh([None, None, BODY_WITH_STAMP])
    clock = _FakeClock()

    rc = _run_main(gh, clock, monkeypatch)

    assert rc == EXIT_OK
    assert gh.body_reads >= 2
    assert gh.body_reads == 3
    assert clock.sleeps == [INTERVAL, INTERVAL]
    out = capsys.readouterr().out
    assert "body_unresolved" in out
    assert "evidence_durable" in out


def test_main_ends_as_a_terminal_failure_when_the_body_never_becomes_readable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gh = _FakeGh([None])
    clock = _FakeClock()

    rc = _run_main(gh, clock, monkeypatch)

    captured = capsys.readouterr()
    assert rc == EXIT_ERROR
    # It really waited: the body was re-read on every poll up to the budget,
    # and the clock never ran past it by more than one interval.
    assert gh.body_reads == DEADLINE // INTERVAL + 1
    assert DEADLINE <= clock.now < DEADLINE + INTERVAL
    assert "[deadline] body_unresolved" in captured.out
    assert "body_unreadable" not in captured.out
