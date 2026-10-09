# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18338: replay the same companion records through the existing gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.ci.check_occ_companion_merged import (
    EXIT_PASS,
    GhFetcher,
    evaluate_once,
)
from scripts.ci.occ_preflight_wait import (
    EnumPreflightWaitOutcome,
    GhCli,
    _resolve_facts,
    decide_preflight_wait,
    main,
)

pytestmark = pytest.mark.unit
REPO = "OmniNode-ai/omnibase_core"
OCC = "OmniNode-ai/onex_change_control"
SHA = "a" * 40


def candidate(number: int = 7001, *, title: str | None = None) -> dict[str, object]:
    return {
        "number": number,
        "title": title or f"evidence(OMN-18338): OCC companion for {REPO}#2500",
        "state": "MERGED",
        "mergeCommit": {"oid": SHA},
    }


class RecordedGh(GhCli, GhFetcher):
    """Exercise both real adapters at their subprocess seam, with no network."""

    def __init__(self, body: str, records: list[dict[str, object]] | None) -> None:
        self.body = body
        self.records = records
        self.reads: list[list[str]] = []

    def _run(self, argv: list[str]) -> str | None:
        self.reads.append(argv)
        if argv[:3] == ["gh", "pr", "list"]:
            return None if self.records is None else json.dumps(self.records)
        if argv[:3] == ["gh", "pr", "view"]:
            if "--repo" in argv and argv[argv.index("--repo") + 1] == OCC:
                return json.dumps({"state": "MERGED", "mergeCommit": {"oid": SHA}})
            if "--jq" in argv:
                return "b" * 40
            return json.dumps({"body": self.body, "author": {"login": "developer"}})
        if argv[:2] == ["gh", "api"]:
            if "/pulls/" in argv[2]:
                return self.body
            if "check-runs" in argv[2]:
                return "[]"
            if "/compare/" in argv[2]:
                return "behind"
        raise AssertionError(f"unexpected read: {argv}")


@pytest.mark.parametrize(
    ("body", "records", "passes"),
    [
        ("description lost its line", [candidate()], True),
        ("description lost its line", [], False),
        ("Evidence-Source: OCC#9999", [candidate()], True),
        ("Evidence-Source: OCC#7001", [], True),
        ("description lost its line", [candidate(), candidate(7002)], False),
        ("description lost its line", None, False),
        (
            "description lost its line",
            [candidate(title=f"OCC companion for {REPO}#25000")],
            False,
        ),
    ],
    ids=[
        "lost-line",
        "no-evidence",
        "wrong-line",
        "legacy",
        "ambiguous",
        "unreadable",
        "number-trap",
    ],
)
def test_both_gate_verdicts(
    body: str, records: list[dict[str, object]] | None, passes: bool
) -> None:
    gh = RecordedGh(body, records)
    verdict = evaluate_once(gh, event_name="pull_request", repo=REPO, pr_number="2500")
    resolved_body, state, ancestry, sha, _ = _resolve_facts(
        gh, repo=REPO, pr_number="2500", occ_repo=OCC
    )
    decision = decide_preflight_wait(
        pr_body=resolved_body,
        companion_state=state,
        cited_sha_ancestry=ancestry,
        elapsed_seconds=0,
        deadline_seconds=0,
        event_name="pull_request",
    )
    assert (verdict.code == EXIT_PASS) == passes
    assert (decision.outcome is EnumPreflightWaitOutcome.PROCEED) == passes
    if passes:
        assert sha == SHA
    if records == [] and body == "description lost its line":
        assert decision.reason == "stamp_absent"
        assert verdict.reason == (
            f"{REPO}#2500 body has no 'Evidence-Source:' line yet "
            "(occ-autobind mint may still be in flight)"
        )
    if records and passes:
        assert "OCC#7001" in (resolved_body or "")
        occ_reads = [
            a[3] for a in gh.reads if a[:3] == ["gh", "pr", "view"] and OCC in a
        ]
        assert occ_reads == ["7001", "7001"]


def test_receipt_workflow_uses_shared_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = yaml.safe_load(Path(".github/workflows/receipt-gate.yml").read_text())
    step = next(
        s
        for s in workflow["jobs"]["verify"]["steps"]
        if s.get("id") == "resolve_evidence_source"
    )
    run = step["run"]
    assert "--resolve-evidence-source" in run
    assert run.index("--resolve-evidence-source") < run.index(
        'if [ -z "$evidence_source" ]'
    )
    gh = RecordedGh("lost line", [candidate()])
    rc = main(
        ["--repo", REPO, "--pr-number", "2500", "--resolve-evidence-source"], gh=gh
    )
    assert rc == 0
    assert capsys.readouterr().out == "OCC#7001\n"


def test_batch_companion_names_product_in_its_record() -> None:
    record = candidate(title=f"evidence(OMN-18338): OCC batch window for {REPO}")
    record["body"] = f"Batch members:\n- {REPO}#2500\n"
    gh = RecordedGh("lost line", [record])
    body, state, _, sha, _ = _resolve_facts(
        gh, repo=REPO, pr_number="2500", occ_repo=OCC
    )
    assert "OCC#7001" in (body or "")
    assert state == "MERGED"
    assert sha == SHA


@pytest.mark.parametrize("body", ["lost line", "Evidence-Source: OCC#7001"])
@pytest.mark.parametrize(
    "records", [None, [candidate(), candidate(7002)], [candidate()] * 50]
)
def test_receipt_resolution_refuses_unreadable_or_ambiguous_records(
    body: str,
    records: list[dict[str, object]] | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(
        ["--repo", REPO, "--pr-number", "2500", "--resolve-evidence-source"],
        gh=RecordedGh(body, records),
    )
    assert rc == 1
    assert capsys.readouterr().err
