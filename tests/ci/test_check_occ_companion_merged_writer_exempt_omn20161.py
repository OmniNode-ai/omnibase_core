# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The writer app is exempt from the OCC companion-merged gate only when the
producer's head-SHA-bound outcome says dependency-pin-only (OMN-20161).

``DEPENDENCY_BOT_AUTHORS`` stays the unconditional list; the writer logins live
in the separate ``OCC_WRITER_BOT_AUTHORS`` set. The verdict is read through this
script's own outcome reader and its own ``is_no_companion_required``; the token
is never re-spelled here -- the parity test compares it with the wait module's.
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.ci import check_occ_companion_merged as gate
from scripts.ci.occ_preflight_wait import (
    AUTOBIND_NO_COMPANION_REQUIRED_REASONS as WAIT_REASONS,
)

pytestmark = pytest.mark.unit

HEAD = "a" * 40
WRITER_LOGINS = (
    "onexbot-occ-writer[bot]",
    "app/onexbot-occ-writer",
    "onexbot-occ-writer",
)
NEAR_MISSES = (
    "onexbot-occ-writer-fork",
    "app/onexbot-occ-writerx",
    "xonexbot-occ-writer",
)
PIN_REASON = WAIT_REASONS[0]


def _outcome_run(outcome: str, reason: str) -> dict[str, Any]:
    return {
        "name": gate.AUTOBIND_OUTCOME_CHECK_NAME,
        "status": "completed",
        "completed_at": "2026-09-30T16:00:00Z",
        "output": {
            "summary": (
                f"{gate.AUTOBIND_OUTCOME_MARKER_PREFIX} {outcome} repo=r pr=1 "
                f"correlation_id=c reason={reason}"
            )
        },
    }


class FakeFetcher(gate.GhFetcher):
    def __init__(
        self,
        author: str,
        check_runs: list[dict[str, Any]] | None,
        body: str = "",
    ) -> None:
        self.author = author
        self._check_runs = check_runs
        self.body = body
        self.check_run_shas: list[str] = []

    def pr_view(self, repo: str, number: str, fields: str) -> dict[str, object] | None:
        if repo != "o/r":
            return None
        return {
            "body": self.body,
            "author": {"login": self.author},
            "headRefOid": HEAD,
        }

    def check_runs(self, repo: str, head_sha: str) -> list[dict[str, object]] | None:
        self.check_run_shas.append(head_sha)
        return self._check_runs  # type: ignore[return-value]  # NOTE(OMN-20161): test double


def _eval(fetcher: FakeFetcher) -> gate.Verdict:
    return gate.evaluate_once(
        fetcher, event_name="pull_request", repo="o/r", pr_number="7"
    )


@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_with_pin_only_outcome_passes(login: str) -> None:
    fetcher = FakeFetcher(login, [_outcome_run("DECLINED", PIN_REASON)])
    verdict = _eval(fetcher)
    assert verdict.code == gate.EXIT_PASS
    assert login in verdict.reason
    assert "pin" in verdict.reason.lower()
    assert fetcher.check_run_shas == [HEAD]


def test_writer_pin_only_passes_even_when_a_stamp_is_already_cited() -> None:
    fetcher = FakeFetcher(
        WRITER_LOGINS[1],
        [_outcome_run("DECLINED", PIN_REASON)],
        body="Evidence-Source: OCC#99999",
    )
    assert _eval(fetcher).code == gate.EXIT_PASS


@pytest.mark.parametrize(
    "runs",
    [
        [_outcome_run("MINTED", "")],
        [_outcome_run("DECLINED", "skip:SOMETHING_ELSE")],
        [_outcome_run("DECLINED", "classifier refused " + PIN_REASON)],
        [],
        None,
    ],
    ids=["minted", "other-reason", "prose-mention", "absent", "unreadable"],
)
@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_without_a_pin_only_outcome_is_not_exempt(
    login: str, runs: list[dict[str, Any]] | None
) -> None:
    """Falls through unchanged: no Evidence-Source => PENDING, as for a human."""
    writer = _eval(FakeFetcher(login, runs))
    human = _eval(FakeFetcher("jonah", runs))
    assert writer.code == gate.EXIT_PENDING
    assert (writer.code, writer.reason) == (human.code, human.reason)


def test_writer_with_a_stamp_and_non_pin_outcome_follows_the_stamp_path() -> None:
    fetcher = FakeFetcher(
        WRITER_LOGINS[0],
        [_outcome_run("MINTED", "")],
        body="Evidence-Source: not-a-valid-ref",
    )
    human = FakeFetcher(
        "jonah", [_outcome_run("MINTED", "")], body="Evidence-Source: not-a-valid-ref"
    )
    assert (_eval(fetcher).code, _eval(fetcher).reason) == (
        _eval(human).code,
        _eval(human).reason,
    )


@pytest.mark.parametrize("login", ["jonah", "jonahgabriel", *NEAR_MISSES])
def test_human_and_near_miss_authors_never_reach_the_outcome_read(login: str) -> None:
    fetcher = FakeFetcher(login, [_outcome_run("DECLINED", PIN_REASON)])
    verdict = _eval(fetcher)
    assert verdict.code == gate.EXIT_PENDING
    # The only check-run read permitted is the pre-existing terminal-ERROR
    # probe on the no-stamp path; it is never a pin-only exemption.
    assert "pin" not in verdict.reason.lower()


@pytest.mark.parametrize("login", sorted(gate.DEPENDENCY_BOT_AUTHORS))
def test_dependency_bots_stay_exempt_without_reading_the_outcome(login: str) -> None:
    fetcher = FakeFetcher(login, None)
    assert _eval(fetcher).code == gate.EXIT_PASS
    assert fetcher.check_run_shas == []


def test_parity_with_the_wait_module_and_the_validator() -> None:
    from omnibase_core.validation.validator_receipt_gate import (
        DEPENDENCY_BOT_AUTHORS,
        OCC_WRITER_BOT_AUTHORS,
    )

    assert tuple(gate.AUTOBIND_NO_COMPANION_REQUIRED_REASONS) == tuple(WAIT_REASONS)
    assert gate.OCC_WRITER_BOT_AUTHORS == OCC_WRITER_BOT_AUTHORS
    assert frozenset(WRITER_LOGINS) == gate.OCC_WRITER_BOT_AUTHORS
    assert gate.DEPENDENCY_BOT_AUTHORS == DEPENDENCY_BOT_AUTHORS
    assert gate.is_no_companion_required(PIN_REASON) is True
    assert gate.is_no_companion_required("skip:OTHER") is False
