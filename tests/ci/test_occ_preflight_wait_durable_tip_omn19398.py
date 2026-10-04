# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19398: a PROCEED evaluates the durable OCC tip, not the frozen companion.

The live case these tests replay is omnimarket#2886 at head ``19f04dd660``. Its
stamp cites OCC#11472, merged at ``0f4c21e95d``. The corrective PASS record for
its false FAIL merged later, in OCC#11646 at ``4e3715d2cf``. Before this change
the gate emitted ``sha=0f4c21e95d`` on every rerun, so the corrective record was
never in the checked-out tree. The shas below are the real ones.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.occ_preflight_wait import (
    OCC_DURABLE_BRANCHES,
    EnumAncestryRead,
    EnumAutobindReadStatus,
    ModelAutobindOutcomeRead,
    main,
)

pytestmark = pytest.mark.unit

CITED_11472_MERGE = (
    "0f4c21e95d3b17e475486bf141ae59c4933029a0"  # pragma: allowlist secret
)
OCC_11646_MERGE = "4e3715d2cfc762c10b4db617f9ecda7eda22ad05"  # pragma: allowlist secret
DEV_TIP = "2765a3082afa940aeefb2e426639d7fb788ab3b5"  # pragma: allowlist secret
MAIN_TIP = "1111111111111111111111111111111111111111"
BODY_2886 = (
    "## OMN-19514 (step 2)\n\nEvidence-Ticket: OMN-19514\nEvidence-Source: OCC#11472\n"
)


class _FakeGh:
    """Scripted :class:`GhPort`. ``contains`` maps (tip, sha) -> bool."""

    def __init__(
        self,
        *,
        body: str | None = BODY_2886,
        companion: tuple[str | None, str] = ("MERGED", CITED_11472_MERGE),
        tips: dict[str, str | None] | None = None,
        contains: dict[tuple[str, str], bool] | None = None,
        ancestor: bool = True,
    ) -> None:
        self.body = body
        self.companion = companion
        self.tips = tips if tips is not None else {"dev": DEV_TIP, "main": MAIN_TIP}
        self.contains = contains if contains is not None else {}
        self.ancestor = ancestor
        self.tip_reads: list[str] = []
        self.compares: list[tuple[str, str]] = []

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        return self.body

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        return self.companion

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        return sha

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> EnumAncestryRead:
        return (
            EnumAncestryRead.ANCESTOR
            if self.ancestor
            else EnumAncestryRead.NOT_ANCESTOR
        )

    def read_autobind_outcome(
        self, *, repo: str, pr_number: str
    ) -> ModelAutobindOutcomeRead:
        return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.ABSENT)

    def read_branch_tip(self, *, occ_repo: str, branch: str) -> str | None:
        self.tip_reads.append(branch)
        return self.tips.get(branch)

    def tip_contains_sha(self, *, occ_repo: str, tip: str, sha: str) -> bool:
        self.compares.append((tip, sha))
        return self.contains.get((tip, sha), False)


def _run(
    gh: _FakeGh, tmp_path: Path, *, event: str = "pull_request"
) -> tuple[int, dict[str, str]]:
    out = tmp_path / "github_output"
    out.write_text("")
    rc = main(
        [
            "--repo",
            "OmniNode-ai/omnimarket",
            "--pr-number",
            "2886",
            "--event-name",
            event,
            "--deadline-seconds",
            "0",
            "--poll-interval-seconds",
            "0",
            "--github-output-path",
            str(out),
        ],
        gh=gh,
    )
    outputs = dict(
        line.split("=", 1) for line in out.read_text().splitlines() if "=" in line
    )
    return rc, outputs


def test_merged_companion_evaluates_the_dev_tip_that_contains_it(
    tmp_path: Path,
) -> None:
    """RED on origin/dev: the gate emitted sha=0f4c21e95d, the frozen merge."""
    gh = _FakeGh(contains={(DEV_TIP, CITED_11472_MERGE): True})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == DEV_TIP
    assert outputs["cited_sha"] == CITED_11472_MERGE
    assert gh.compares == [(DEV_TIP, CITED_11472_MERGE)]


def test_merge_group_event_also_evaluates_the_durable_tip(tmp_path: Path) -> None:
    gh = _FakeGh(contains={(DEV_TIP, CITED_11472_MERGE): True})
    rc, outputs = _run(gh, tmp_path, event="merge_group")
    assert rc == 0
    assert outputs["sha"] == DEV_TIP


def test_cited_commit_that_is_the_tip_is_used_without_a_compare(
    tmp_path: Path,
) -> None:
    gh = _FakeGh(tips={"dev": CITED_11472_MERGE, "main": MAIN_TIP})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == CITED_11472_MERGE
    assert gh.compares == []


def test_falls_through_to_main_when_dev_does_not_contain_the_cited_sha(
    tmp_path: Path,
) -> None:
    gh = _FakeGh(contains={(MAIN_TIP, CITED_11472_MERGE): True})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == MAIN_TIP
    assert gh.tip_reads == list(OCC_DURABLE_BRANCHES)


def test_no_tip_contains_the_cited_sha_keeps_the_cited_sha(tmp_path: Path) -> None:
    """A tip that does not provably contain the evidence is never evaluated."""
    gh = _FakeGh(contains={})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == CITED_11472_MERGE


def test_unreadable_tips_keep_the_cited_sha(tmp_path: Path) -> None:
    gh = _FakeGh(tips={"dev": None, "main": None})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == CITED_11472_MERGE
    assert gh.compares == []


def test_sha_stamp_that_is_durable_also_advances_to_the_tip(tmp_path: Path) -> None:
    body = f"Evidence-Source: {OCC_11646_MERGE}\n"
    gh = _FakeGh(body=body, contains={(DEV_TIP, OCC_11646_MERGE): True})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["sha"] == DEV_TIP
    assert outputs["cited_sha"] == OCC_11646_MERGE


def test_open_companion_never_reads_a_tip_and_still_fails_closed(
    tmp_path: Path,
) -> None:
    """Durability is decided first; an unmerged companion never gets a tip."""
    gh = _FakeGh(companion=("OPEN", "abcdef0" * 5 + "abcde"))
    rc, outputs = _run(gh, tmp_path)
    assert rc == 1
    assert "sha" not in outputs
    assert gh.tip_reads == []


def test_closed_companion_never_reads_a_tip(tmp_path: Path) -> None:
    gh = _FakeGh(companion=("CLOSED", ""))
    rc, outputs = _run(gh, tmp_path)
    assert rc == 1
    assert "sha" not in outputs
    assert gh.tip_reads == []


def test_non_ancestor_sha_stamp_never_reads_a_tip(tmp_path: Path) -> None:
    body = "Evidence-Source: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
    gh = _FakeGh(body=body, ancestor=False)
    rc, outputs = _run(gh, tmp_path)
    assert rc == 1
    assert "sha" not in outputs
    assert gh.tip_reads == []


def test_fallback_to_the_cited_sha_is_reported_as_a_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fallback is the pre-OMN-19398 tree; the job log must say so."""
    gh = _FakeGh(tips={"dev": None, "main": None})
    rc, outputs = _run(gh, tmp_path)
    assert rc == 0
    assert outputs["cited_sha"] == CITED_11472_MERGE
    assert "::warning::no readable OCC durable-branch tip" in capsys.readouterr().out
