# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20448: an ancestry read that FAILED is not an ancestry read that said no.

``GhCli.sha_is_ancestor`` used to return ``False`` both when every compare
against the durable branches succeeded and was diverged, and when ``gh`` could
not be asked at all (``_run`` returned ``None``). ``decide_preflight_wait`` then
failed a SHA-shaped stamp closed as ``sha_not_ancestor`` on a transient
failure. The read is now three-state (:class:`EnumAncestryRead`): only a
definitive NOT_ANCESTOR is terminal; UNRESOLVED retries inside the existing
budget like ``companion_state_unresolved``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.ci import occ_preflight_wait
from scripts.ci.occ_preflight_wait import (
    DEFAULT_DEADLINE_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    EXIT_OK,
    OCC_DURABLE_BRANCHES,
    EnumAncestryRead,
    EnumAutobindReadStatus,
    EnumPreflightWaitOutcome,
    GhCli,
    ModelAutobindOutcomeRead,
    ModelPreflightWaitDecision,
    decide_preflight_wait,
    main,
)

pytestmark = pytest.mark.unit

DEADLINE = DEFAULT_DEADLINE_SECONDS
INTERVAL = DEFAULT_POLL_INTERVAL_SECONDS
SHA = "a" * 40
BODY = f"## OMN-20448\n\nEvidence-Source: {SHA}\n"


def _decide(ancestry: EnumAncestryRead, *, elapsed: int) -> ModelPreflightWaitDecision:
    return decide_preflight_wait(
        pr_body=BODY,
        companion_state=None,
        cited_sha_ancestry=ancestry,
        elapsed_seconds=elapsed,
        deadline_seconds=DEADLINE,
        event_name="pull_request",
    )


# ---------------------------------------------------------------------------
# AC1-AC3 -- the pure verdict.
# ---------------------------------------------------------------------------


def test_unresolved_ancestry_waits_at_elapsed_zero() -> None:
    decision = _decide(EnumAncestryRead.UNRESOLVED, elapsed=0)
    assert decision.outcome is EnumPreflightWaitOutcome.WAIT
    assert decision.reason == "sha_ancestry_unresolved"
    assert not decision.is_terminal_failure


def test_unresolved_ancestry_waits_until_the_last_second_then_hits_the_deadline() -> (
    None
):
    last = _decide(EnumAncestryRead.UNRESOLVED, elapsed=DEADLINE - 1)
    assert last.outcome is EnumPreflightWaitOutcome.WAIT
    assert last.reason == "sha_ancestry_unresolved"

    expired = _decide(EnumAncestryRead.UNRESOLVED, elapsed=DEADLINE)
    assert expired.outcome is EnumPreflightWaitOutcome.DEADLINE
    assert expired.reason == "sha_ancestry_unresolved"
    assert expired.is_terminal_failure


def test_a_definitive_diverged_read_still_fails_now() -> None:
    decision = _decide(EnumAncestryRead.NOT_ANCESTOR, elapsed=0)
    assert decision.outcome is EnumPreflightWaitOutcome.FAIL_NOW
    assert decision.reason == "sha_not_ancestor"


def test_an_ancestor_read_still_proceeds() -> None:
    decision = _decide(EnumAncestryRead.ANCESTOR, elapsed=0)
    assert decision.outcome is EnumPreflightWaitOutcome.PROCEED
    assert decision.reason == "evidence_durable"


def test_the_budget_is_not_widened() -> None:
    assert DEFAULT_DEADLINE_SECONDS == 1500


# ---------------------------------------------------------------------------
# AC4 -- GhCli with a stubbed ``_run``.
# ---------------------------------------------------------------------------


def _gh_cli_with(
    monkeypatch: pytest.MonkeyPatch, statuses: dict[str, str | None]
) -> GhCli:
    """``statuses`` maps a durable branch to the compare status ``gh`` returns
    for it (``None`` is a failed read)."""
    cli = GhCli()

    def fake_run(argv: list[str]) -> str | None:
        compare = argv[2]
        branch = compare.split("/compare/")[1].split("...")[0]
        return statuses[branch]

    monkeypatch.setattr(cli, "_run", fake_run)
    return cli


def _read(cli: GhCli) -> EnumAncestryRead:
    return cli.sha_is_ancestor(
        occ_repo="OmniNode-ai/onex_change_control",
        sha=SHA,
        branches=OCC_DURABLE_BRANCHES,
    )


def test_every_branch_read_failing_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _gh_cli_with(monkeypatch, dict.fromkeys(OCC_DURABLE_BRANCHES))
    assert _read(cli) is EnumAncestryRead.UNRESOLVED


@pytest.mark.parametrize("proving", ["identical", "behind"])
def test_one_proving_branch_wins_over_a_failing_one(
    monkeypatch: pytest.MonkeyPatch, proving: str
) -> None:
    statuses: dict[str, str | None] = dict.fromkeys(OCC_DURABLE_BRANCHES)
    statuses[OCC_DURABLE_BRANCHES[-1]] = proving
    cli = _gh_cli_with(monkeypatch, statuses)
    assert _read(cli) is EnumAncestryRead.ANCESTOR


@pytest.mark.parametrize("status", ["diverged", "ahead"])
def test_all_successful_non_ancestor_reads_are_definitive(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    cli = _gh_cli_with(monkeypatch, dict.fromkeys(OCC_DURABLE_BRANCHES, status))
    assert _read(cli) is EnumAncestryRead.NOT_ANCESTOR


def test_a_failed_read_beside_a_diverged_one_is_still_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses: dict[str, str | None] = dict.fromkeys(OCC_DURABLE_BRANCHES, "diverged")
    statuses[OCC_DURABLE_BRANCHES[0]] = None
    cli = _gh_cli_with(monkeypatch, statuses)
    assert _read(cli) is EnumAncestryRead.UNRESOLVED


# ---------------------------------------------------------------------------
# AC5 -- the polling driver.
# ---------------------------------------------------------------------------


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        assert len(self.sleeps) < 200, "poll loop did not terminate"
        self.sleeps.append(seconds)
        self.now += seconds


class _FakeGh:
    """Scripted :class:`GhPort`; ``reads`` is consumed one ancestry read at a
    time and its last element repeats."""

    def __init__(self, reads: list[EnumAncestryRead]) -> None:
        self.reads = reads
        self.ancestry_reads = 0

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        return BODY

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        raise AssertionError("a SHA-shaped stamp reads no companion")

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        return sha

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> EnumAncestryRead:
        index = min(self.ancestry_reads, len(self.reads) - 1)
        self.ancestry_reads += 1
        return self.reads[index]

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


def test_main_retries_an_unresolved_ancestry_read_and_proceeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gh = _FakeGh([EnumAncestryRead.UNRESOLVED, EnumAncestryRead.ANCESTOR])
    clock = _FakeClock()

    rc = _run_main(gh, clock, monkeypatch)

    assert rc == EXIT_OK
    assert gh.ancestry_reads == 2
    assert clock.sleeps == [INTERVAL]
    out = capsys.readouterr().out
    assert "sha_ancestry_unresolved" in out
    assert "evidence_durable" in out


def test_main_ends_as_a_deadline_when_the_read_never_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gh = _FakeGh([EnumAncestryRead.UNRESOLVED])
    clock = _FakeClock()

    rc = _run_main(gh, clock, monkeypatch)

    assert rc != EXIT_OK
    assert gh.ancestry_reads == DEADLINE // INTERVAL + 1
    assert DEADLINE <= clock.now < DEADLINE + INTERVAL
    assert "[deadline] sha_ancestry_unresolved" in capsys.readouterr().out
