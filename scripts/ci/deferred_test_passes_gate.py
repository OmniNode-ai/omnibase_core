# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI Summary's evaluation of deferred ``test_passes`` DoD items (OMN-18157).

A contract's ``test_passes`` item means "the PR's CI is green". The pinned
change-control runner judges it with ``gh pr checks`` and fails on any check
that is not SUCCESS, SKIPPED or NEUTRAL, so inside the Contract Compliance Check
job it fails on that job's own running check. ``defer_test_passes_driver.py``
records such items instead of judging them; this module judges them in the
``CI Summary`` job, after the CI Summary verdict itself is SUCCESS.

Same pass set as the pinned runner (SUCCESS, SKIPPED, NEUTRAL), with seven
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
* A cancelled matrix placeholder is dropped once its matrix expanded on this
  head. When a run is cancelled before a matrix is evaluated, GitHub leaves one
  row whose name still carries the unexpanded ``${{ ... }}`` expression. No
  later row can carry that name, so latest-wins would keep the cancellation for
  ever (omnibase_core#1772: CI run 36155199260, cancelled by its concurrency
  group, left ``Tests (Split ${{ matrix.split }}/...)`` beside run 36155334716,
  which expanded and passed the same matrix). Such a row is superseded when any
  other row's name matches the placeholder with each expression standing for
  non-empty text; the expanded copies are then judged under their own names.
  With no expanded copy the placeholder stays the verdict, and a placeholder
  that failed rather than was cancelled is always judged.
* A cancellation that its own workflow superseded is not a verdict (OMN-17427).
  A ``cancelled`` row is PENDING while a newer run of the same workflow is
  still running on this head, and is superseded (reported, not judged) when a
  newer run of that workflow on this head has finished, or when GitHub
  cancelled the row's run for a newer run in its concurrency group (the run's
  cancelled job carries GitHub's own annotation ``Canceling since a higher
  priority waiting request for <group> exists``). Measured on
  omnibase_core#1795, #1794 and #1793 (CI runs 36328548514, 36306444633,
  36306138828): ``auto-merge.yml`` keys its concurrency group on the PR
  number, a ``check_suite`` run on ``dev`` resolved to the same group and
  cancelled the head's run (``Enable Auto-Merge``, ``Resolve PR (fanout
  guard)``), and the replacement ran on a different sha, so no row on this
  head ever replaced the cancellation and every CI Summary on the head
  failed until someone re-ran the Auto-Merge run by hand. A failure is never
  superseded this way, a row with no run URL is judged as before, and an
  unreadable annotation leaves the row judged.

Exit codes: ``0`` success, ``1`` failure.
"""

from __future__ import annotations

import argparse
import json
import re
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

# GitHub's own annotation on a job it cancelled because a newer run entered the
# same concurrency group (OMN-17427). Read from check-runs/{id}/annotations.
CONCURRENCY_CANCEL_MARKER = "Canceling since a higher priority waiting request for "
_RUN_ID_RE = re.compile(r"/actions/runs/(\d+)")


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


def _latest_rows(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """One raw row per name, latest ``(started_at, id)`` wins; skipped rows compete."""

    best: dict[str, tuple[tuple[str, int], dict[str, object]]] = {}
    for raw in rows:
        name = str(raw.get("name") or "")
        if not name:
            continue
        key = (str(raw.get("started_at") or ""), _int(raw, "id"))
        if name in best and key <= best[name][0]:
            continue
        best[name] = (key, raw)
    return {name: raw for name, (_, raw) in best.items()}


def _state(name: str, raw: dict[str, object]) -> JobState:
    conclusion = raw.get("conclusion")
    completed_at = raw.get("completed_at")
    return JobState(
        name=name,
        status=str(raw.get("status") or ""),
        conclusion=None if conclusion is None else str(conclusion),
        run_attempt=1,
        completed_at=None if completed_at is None else str(completed_at),
    )


def _latest_by_name(rows: list[dict[str, object]]) -> dict[str, JobState]:
    """One row per name, latest ``(started_at, id)`` wins; skipped rows compete."""

    return {name: _state(name, raw) for name, raw in _latest_rows(rows).items()}


def _int(raw: dict[str, object], key: str) -> int:
    try:
        return int(str(raw.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def check_run_workflow_run_id(raw: dict[str, object]) -> int | None:
    """The Actions run that wrote this check-run, from its own URL, or ``None``."""

    for key in ("html_url", "details_url"):
        match = _RUN_ID_RE.search(str(raw.get(key) or ""))
        if match:
            return int(match.group(1))
    return None


def is_concurrency_cancellation(messages: list[str]) -> bool:
    """Whether a cancelled job's annotations say GitHub cancelled it for a newer
    run in the same concurrency group."""

    return any(CONCURRENCY_CANCEL_MARKER in message for message in messages)


def cancelled_supersession(
    raw: dict[str, object],
    workflow_runs: list[dict[str, object]] | None,
    concurrency_cancelled_runs: frozenset[int],
    own_run_ids: frozenset[int],
) -> tuple[str, str] | None:
    """How a ``cancelled`` row's own workflow superseded it, or ``None`` (OMN-17427).

    ``("pending", why)`` while a newer run of the same workflow is still running
    on this head (other than the run judging it, whose own jobs the CI Summary
    verdict already judged); ``("superseded", why)`` when a newer run of that
    workflow on this head has finished, or when GitHub cancelled the row's run
    for a newer run in its concurrency group. ``None`` leaves the row judged as
    before: no run URL, a run missing from the payload, no payload, or no
    concurrency annotation.
    """

    run_id = check_run_workflow_run_id(raw)
    if run_id is None:
        return None
    own = next((r for r in workflow_runs or [] if _int(r, "id") == run_id), None)
    workflow_id = 0 if own is None else _int(own, "workflow_id")
    newer = [
        r
        for r in workflow_runs or []
        if workflow_id
        and _int(r, "workflow_id") == workflow_id
        and _int(r, "id") > run_id
    ]
    running = [
        r
        for r in newer
        if str(r.get("status") or "") != "completed"
        and _int(r, "id") not in own_run_ids
    ]
    if running:
        latest = max(running, key=lambda r: _int(r, "id"))
        return (
            "pending",
            f"run {_int(latest, 'id')} of the same workflow is "
            f"{latest.get('status')} on this head",
        )
    if newer:
        latest = max(newer, key=lambda r: _int(r, "id"))
        return (
            "superseded",
            f"run {run_id} superseded by run {_int(latest, 'id')} of the same "
            "workflow on this head",
        )
    if run_id in concurrency_cancelled_runs:
        return (
            "superseded",
            f"run {run_id} cancelled by its concurrency group for a newer run",
        )
    return None


_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")


def _placeholder_pattern(name: str) -> re.Pattern[str] | None:
    """The expanded-name pattern of a matrix placeholder, or ``None``."""

    parts = _EXPRESSION.split(name)
    if len(parts) == 1:
        return None
    return re.compile(".+".join(re.escape(part) for part in parts))


def _drop_superseded_placeholders(
    latest: dict[str, JobState],
) -> tuple[dict[str, JobState], list[str]]:
    """Drop cancelled matrix placeholders whose matrix expanded on this head."""

    expanded = [name for name in latest if _placeholder_pattern(name) is None]
    kept: dict[str, JobState] = {}
    dropped: list[str] = []
    for name, st in latest.items():
        pattern = _placeholder_pattern(name)
        if (
            pattern is not None
            and st.status == "completed"
            and st.conclusion == "cancelled"
            and any(pattern.fullmatch(other) for other in expanded)
        ):
            dropped.append(name)
            continue
        kept[name] = st
    return kept, sorted(dropped)


def _is_actions_row(row: dict[str, object]) -> bool:
    app = row.get("app")
    if not isinstance(app, dict) or not app.get("slug"):
        return True
    return app.get("slug") == ACTIONS_APP_SLUG


def cancelled_run_ids(check_runs: list[dict[str, object]]) -> list[int]:
    """The runs whose cancelled row is the latest of its name (the only rows the
    concurrency annotation is ever read for)."""

    latest = _latest_rows([row for row in check_runs if _is_actions_row(row)])
    ids = {
        run_id
        for name, raw in latest.items()
        if name != SELF_JOB_NAME
        and raw.get("status") == "completed"
        and raw.get("conclusion") == "cancelled"
        and (run_id := check_run_workflow_run_id(raw)) is not None
    }
    return sorted(ids)


def evaluate_checks(
    check_runs: list[dict[str, object]],
    *,
    now: datetime | None,
    workflow_runs: list[dict[str, object]] | None = None,
    concurrency_cancelled_runs: frozenset[int] = frozenset(),
    own_run_ids: frozenset[int] = frozenset(),
) -> tuple[int, str]:
    """Judge one head's ``commits/{sha}/check-runs`` rows."""

    raw_latest = _latest_rows([row for row in check_runs if _is_actions_row(row)])
    latest = {name: _state(name, raw) for name, raw in raw_latest.items()}
    latest, superseded = _drop_superseded_placeholders(latest)
    others = {name: st for name, st in latest.items() if name != SELF_JOB_NAME}
    if not others:
        return EXIT_FAILURE, "  no checks observed besides CI Summary"
    failures: list[str] = []
    pending: list[str] = []
    replaced: list[str] = []
    for name, st in others.items():
        if st.status != "completed":
            pending.append(f"{name} ({st.status})")
            continue
        if st.conclusion in GOOD_CONCLUSIONS:
            continue
        verdict = (
            cancelled_supersession(
                raw_latest[name],
                workflow_runs,
                concurrency_cancelled_runs,
                own_run_ids,
            )
            if st.conclusion == "cancelled"
            else None
        )
        if verdict is not None and verdict[0] == "pending":
            pending.append(f"{name} (cancelled; {verdict[1]})")
        elif verdict is not None:
            replaced.append(f"{name} ({verdict[1]})")
        elif verdict_is_provisional(st, now):
            pending.append(
                f"{name} ({st.conclusion}, awaiting its automatic replacement)"
            )
        else:
            failures.append(f"{name} ({st.conclusion})")
    lines = [f"  checks observed: {len(others)} (latest per name, CI Summary excluded)"]
    if superseded:
        lines.append(
            "  cancelled matrix placeholders superseded by their expanded copies: "
            + ", ".join(superseded)
        )
    if replaced:
        lines.append(
            "  cancellations superseded by their own workflow (not judged): "
            + ", ".join(sorted(replaced))
        )
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


def _workflow_runs(repo: str, head: str) -> list[dict[str, object]] | None:
    return _gh_json_lines(
        f"repos/{repo}/actions/runs?head_sha={head}&per_page=100",
        ".workflow_runs[] | {id, workflow_id, status, conclusion, event}",
    )


def _run_cancelled_by_concurrency(repo: str, run_id: int) -> bool:
    """Whether GitHub annotated a cancelled job of this run as a concurrency
    cancellation. Any unreadable page answers ``False``: the row stays judged."""

    jobs = _gh_json_lines(
        f"repos/{repo}/actions/runs/{run_id}/jobs?filter=latest&per_page=100",
        ".jobs[] | {id, conclusion}",
    )
    for job in jobs or []:
        if job.get("conclusion") != "cancelled":
            continue
        notes = _gh_json_lines(
            f"repos/{repo}/check-runs/{_int(job, 'id')}/annotations?per_page=100",
            ".[] | {message}",
        )
        if notes and is_concurrency_cancellation(
            [str(note.get("message") or "") for note in notes]
        ):
            return True
    return False


def own_workflow_run_ids(
    jobs: list[dict[str, object]], current_run_id: int | None
) -> frozenset[int]:
    """This CI run's id, from ``--current-run-id`` and the jobs payload rows."""

    ids = {_int(raw, "run_id") for raw in jobs if isinstance(raw, dict)}
    if current_run_id:
        ids.add(current_run_id)
    ids.discard(0)
    return frozenset(ids)


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
    parser.add_argument(
        "--current-run-id",
        type=int,
        default=None,
        help="This workflow run's id (github.run_id). A newer run of a cancelled "
        "row's workflow that is this run is not waited on (OMN-17427).",
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
    own_run_ids = own_workflow_run_ids(jobs, args.current_run_id)
    concurrency_cancelled: dict[int, bool] = {}
    deadline = time.monotonic() + args.deadline_seconds
    report = "  no poll completed"
    while True:
        check_runs = _gh_json_lines(
            f"repos/{repo}/commits/{head}/check-runs?per_page=100", ".check_runs[]"
        )
        workflow_runs = (
            _workflow_runs(repo, head)
            if check_runs is not None and cancelled_run_ids(check_runs)
            else None
        )
        if check_runs is not None:
            for run_id in cancelled_run_ids(check_runs):
                if run_id not in concurrency_cancelled:
                    concurrency_cancelled[run_id] = _run_cancelled_by_concurrency(
                        repo, run_id
                    )
            code, report = evaluate_checks(
                check_runs,
                now=datetime.now(UTC),
                workflow_runs=workflow_runs,
                concurrency_cancelled_runs=frozenset(
                    run_id for run_id, hit in concurrency_cancelled.items() if hit
                ),
                own_run_ids=own_run_ids,
            )
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
