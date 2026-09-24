# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI Summary's evaluation of deferred ``test_passes`` DoD items (OMN-18157).

A contract's ``test_passes`` item means "the PR's CI is green". The pinned
change-control runner judges it with ``gh pr checks`` and fails on any check
that is not SUCCESS, SKIPPED or NEUTRAL, so inside the Contract Compliance Check
job it fails on that job's own running check. ``defer_test_passes_driver.py``
records such items instead of judging them; this module judges them in the
``CI Summary`` job, after the CI Summary verdict itself is SUCCESS.

Same pass set as the pinned runner (SUCCESS, SKIPPED, NEUTRAL), with five
differences, each because the in-job evaluation could not work or because
``gh pr checks`` is not how GitHub reads a head:

* It reads the exact head this run gates (``commits/{sha}/check-runs``), so a
  later push cannot change what it judges.
* It judges this repository's CI: the check-runs GitHub Actions posts. A
  check-run another App posts is that App's report, not CI (measured on
  omnibase_core#1745: the change-control App posted ``occ-autobind / outcome``
  red for "nothing to commit" on a PR whose evidence was already bound and
  merged; the evidence gates, which are Actions jobs, judge evidence). A row
  that names no App is judged. Commit statuses are not read: they are posted by
  integrations, not by Actions.
* Same-named check-runs resolve latest-wins by ``(started_at, id)``, the rule
  GitHub applies to a required context. ``gh pr checks`` keys by workflow as
  well, which keeps a superseded red from one caller of a reusable workflow
  alive beside the green that replaced it. Unlike ``ci_summary_gate``'s L4
  reading, a newer ``skipped`` row is NOT dropped in favour of an older
  non-skipped one: skipped is a pass here, so a rerun that skips a job replaces
  the cancelled row an earlier run left (measured on omnibase_core#1745).
* Every ``CI Summary`` row is excluded: CI Summary is the judge, and two runs
  on one head must not wait on each other.
* A still-running check is PENDING, polled until the deadline and then a
  failure; a cancellation or failure inside ``ci_summary_gate``'s measured
  replacement windows (OMN-18355, OMN-17864) is PENDING rather than final.

Exit codes: ``0`` success, ``1`` failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    SELF_JOB_NAME,
    JobState,
    dedup_latest,
    verdict_is_provisional,
)

__all__ = [
    "EXIT_FAILURE",
    "EXIT_PENDING",
    "EXIT_SUCCESS",
    "evaluate_checks",
    "load_record",
    "record_required",
]

CONTRACT_COMPLIANCE_JOB = "Contract Compliance Check"

# The pinned runner's pass set (contract_compliance_check._check_test_passes).
GOOD_CONCLUSIONS: frozenset[str] = frozenset({"success", "skipped", "neutral"})
ACTIONS_APP_SLUG = "github-actions"


def record_required(jobs: list[dict[str, object]], run_attempt: int | None) -> bool:
    """Whether Contract Compliance Check must have produced a deferral record.

    It uploads one on every path that ran (evaluation or dependency-bot
    exemption), so ``success`` requires a record and ``skipped`` has none.
    Anything else cannot reach this step (the CI Summary verdict would have
    failed first) and is refused.
    """

    state = dedup_latest(jobs, run_attempt=run_attempt).get(CONTRACT_COMPLIANCE_JOB)
    if state is not None and state.status == "completed":
        if state.conclusion == "success":
            return True
        if state.conclusion == "skipped":
            return False
    observed = "absent" if state is None else f"{state.status}/{state.conclusion}"
    raise ValueError(
        f"{CONTRACT_COMPLIANCE_JOB} is {observed}; expected success or skipped"
    )


def load_record(path: Path) -> list[dict[str, object]]:
    """Load the deferred items the Contract Compliance Check job recorded."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError(f"unrecognised deferral record schema in {path}")
    deferred = payload.get("deferred")
    if not isinstance(deferred, list) or not all(
        isinstance(item, dict) for item in deferred
    ):
        raise ValueError(f"deferral record {path} has no 'deferred' list of objects")
    return deferred


def _latest_by_name(rows: list[dict[str, object]]) -> dict[str, JobState]:
    """One row per name, latest ``(started_at, id)`` wins; skipped rows compete."""

    best: dict[str, tuple[tuple[str, int], JobState]] = {}
    for raw in rows:
        name = str(raw.get("name") or "")
        if not name:
            continue
        try:
            row_id = int(str(raw.get("id") or 0))
        except ValueError:
            row_id = 0
        key = (str(raw.get("started_at") or ""), row_id)
        if name in best and key <= best[name][0]:
            continue
        conclusion = raw.get("conclusion")
        completed_at = raw.get("completed_at")
        best[name] = (
            key,
            JobState(
                name=name,
                status=str(raw.get("status") or ""),
                conclusion=None if conclusion is None else str(conclusion),
                run_attempt=1,
                completed_at=None if completed_at is None else str(completed_at),
            ),
        )
    return {name: state for name, (_, state) in best.items()}


def _is_actions_row(row: dict[str, object]) -> bool:
    app = row.get("app")
    if not isinstance(app, dict) or not app.get("slug"):
        return True
    return app.get("slug") == ACTIONS_APP_SLUG


def evaluate_checks(
    check_runs: list[dict[str, object]], *, now: datetime | None
) -> tuple[int, str]:
    """Judge one head's ``commits/{sha}/check-runs`` rows."""

    latest = _latest_by_name([row for row in check_runs if _is_actions_row(row)])
    others = {name: st for name, st in latest.items() if name != SELF_JOB_NAME}
    if not others:
        return EXIT_FAILURE, "  no checks observed besides CI Summary"
    failures: list[str] = []
    pending: list[str] = []
    for name, st in others.items():
        if st.status != "completed":
            pending.append(f"{name} ({st.status})")
        elif st.conclusion in GOOD_CONCLUSIONS:
            continue
        elif verdict_is_provisional(st, now):
            pending.append(
                f"{name} ({st.conclusion}, awaiting its automatic replacement)"
            )
        else:
            failures.append(f"{name} ({st.conclusion})")
    lines = [f"  checks observed: {len(others)} (latest per name, CI Summary excluded)"]
    if failures:
        lines.append("  not green: " + ", ".join(sorted(failures)))
    if pending:
        lines.append("  pending: " + ", ".join(sorted(pending)))
    if failures:
        return EXIT_FAILURE, "\n".join(lines)
    if pending:
        return EXIT_PENDING, "\n".join(lines)
    return EXIT_SUCCESS, "\n".join(lines)


def _gh_json_lines(path: str, jq: str) -> list[dict[str, object]] | None:
    result = subprocess.run(
        ["gh", "api", "--paginate", path, "--jq", jq],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        print(  # noqa: T201
            f"  gh api {path} failed (rc={result.returncode}): {result.stderr.strip()}",
            flush=True,
        )
        return None
    try:
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError:
        print(f"  gh api {path} returned malformed JSON", flush=True)  # noqa: T201
        return None
    return rows if all(isinstance(row, dict) for row in rows) else None


def _pr_target(deferred: list[dict[str, object]]) -> tuple[str, str]:
    targets = {(str(item.get("pr_number")), str(item.get("repo"))) for item in deferred}
    if len(targets) != 1:
        raise ValueError(f"deferred items name {len(targets)} PR targets; expected 1")
    return targets.pop()


def _pr_head(pr_number: str, repo: str) -> str:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    head = result.stdout.strip()
    if result.returncode != 0 or not head:
        raise ValueError(
            f"could not resolve the head of {repo}#{pr_number}: {result.stderr.strip()}"
        )
    return head


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-file", required=True, type=Path)
    parser.add_argument("--run-attempt", type=int, default=None)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument(
        "--head-sha",
        default="",
        help="The head this run gates (pull_request). Empty: the recorded PR's head.",
    )
    parser.add_argument("--deadline-seconds", type=int, default=2400)
    parser.add_argument("--poll-interval-seconds", type=int, default=60)
    args = parser.parse_args(argv)

    try:
        jobs = json.loads(args.jobs_file.read_text(encoding="utf-8"))
        if not record_required(jobs, args.run_attempt):
            print(  # noqa: T201
                f"{CONTRACT_COMPLIANCE_JOB} was skipped; no deferred test_passes items."
            )
            return EXIT_SUCCESS
        if not args.record.is_file():
            print(f"::error::deferral record missing: {args.record}")  # noqa: T201
            return EXIT_FAILURE
        deferred = load_record(args.record)
        if not deferred:
            print("No test_passes items were deferred.")  # noqa: T201
            return EXIT_SUCCESS
        pr_number, repo = _pr_target(deferred)
        head = args.head_sha or _pr_head(pr_number, repo)
    except (OSError, ValueError) as exc:
        print(f"::error::deferred test_passes evaluation refused: {exc}")  # noqa: T201
        return EXIT_FAILURE

    print(  # noqa: T201
        f"Evaluating {len(deferred)} deferred test_passes item(s) for "
        f"{repo}#{pr_number} at {head}",
        flush=True,
    )
    deadline = time.monotonic() + args.deadline_seconds
    report = "  no poll completed"
    while True:
        check_runs = _gh_json_lines(
            f"repos/{repo}/commits/{head}/check-runs?per_page=100", ".check_runs[]"
        )
        if check_runs is not None:
            code, report = evaluate_checks(check_runs, now=datetime.now(UTC))
            print(report, flush=True)  # noqa: T201
            if code == EXIT_SUCCESS:
                print("Deferred test_passes: SUCCESS")  # noqa: T201
                return EXIT_SUCCESS
            if code == EXIT_FAILURE:
                print("::error::Deferred test_passes: FAILURE")  # noqa: T201
                return EXIT_FAILURE
        if time.monotonic() >= deadline:
            print(  # noqa: T201
                "::error::Deferred test_passes deadline reached with checks still "
                f"pending; failing closed.\n{report}"
            )
            return EXIT_FAILURE
        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
