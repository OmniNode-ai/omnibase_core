# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Count-locked ratchet over ``pull_request``-triggered workflow files (C7 / OMN-14907).

WHAT THIS CLOSES
----------------
``omnibase_core`` carries ~49 ``.github/workflows/*.yml`` files that trigger on
``pull_request`` / ``pull_request_target``. Every one fires a fresh check-run on
every push to every PR, INDEPENDENT of required-status-check count (required
status gates *merging*, not *execution*). That ~50-runs-per-PR standing baseline
is the C7 cost driver in ``docs/plans/2026-07-21-ci-capacity-recovery-plan.md``.

CLAUDE.md's net-negative-surface rule ("a new gate must retire an existing
surface") is meant to hold this line, but it is a *rule* and it demonstrably did
not: 7 net-new PR-triggered workflow files landed in five days. This module
expresses that rule as a *mechanism* — the same count-locked-ratchet shape already
used by ``no_noncanonical_lifecycle_classes`` (OMN-14350) and
``validator_standalone_workflow_registry`` (OMN-14430):

  * Every live PR-triggered workflow file must be enumerated in
    ``architecture-handshakes/pull-request-workflow-budget.yaml`` — either in the
    ``allowlisted_workflows`` budget or in a tracked, expiring ``waivers`` entry.
    A NEW un-enumerated file fails CLOSED (``UNREGISTERED``).
  * ``budget`` is a hard count lock: ``len(allowlisted_workflows) == budget``.
    Registering a net-new file bumps the list to ``budget + 1`` and fails
    (``BUDGET_MISMATCH``). The only sanctioned ways to add a PR-triggered
    workflow are therefore (a) *retire* an existing one (net-negative — the list
    and budget both drop by one, then rise by one, staying flat) or (b) add it to
    the ``waivers`` bucket with a ticket + expiry + justification.
  * The budget is ALSO frozen a second time in the test suite
    (``test_pull_request_workflow_ratchet.py``) exactly as OMN-14430 freezes its
    decorative count — so lowering (or raising) the budget is a deliberate,
    two-file, reviewed edit, never a silent drift. The ratchet is intended to
    move DOWN only; the two-place lock makes any move visible.
  * A registry entry with no matching live file fails (``STALE``) — you cannot
    delete a workflow without also removing its registry line and lowering the
    budget, which is how the count ratchets DOWN.
  * A waiver past its ``expires`` date fails (``WAIVER_EXPIRED``) so exceptions
    cannot become permanent.

Because a job that lives in a *separate* workflow file is structurally invisible
to ``ci.yml``'s ``ci-summary`` poller (the OMN-14430 finding), this gate runs as a
JOB INSIDE ``ci.yml`` and as a pre-commit hook — never as its own new
``pull_request``-triggered workflow file (which would be self-defeating).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.models.validation.model_workflow_ratchet_gap import (
    ModelWorkflowRatchetGap,
)

__all__ = [
    "verify_pull_request_workflow_ratchet",
    "triggers_on_pull_request",
    "live_pull_request_workflows",
    "main",
]

DEFAULT_REGISTRY_PATH = Path(
    "architecture-handshakes/pull-request-workflow-budget.yaml"
)

# Trigger keys that cause a fresh check-run on push-to-PR (the per-commit cost the
# ratchet governs). ``pull_request_review`` / ``pull_request_review_comment`` /
# ``issue_comment`` are the *comment*-driven treadmill (OMN-12562) and are out of
# scope here — this ratchet governs the push-to-PR fan-out only.
_PR_TRIGGER_KEYS: frozenset[str] = frozenset({"pull_request", "pull_request_target"})

_REQUIRED_WAIVER_FIELDS: tuple[str, ...] = (
    "workflow_file",
    "ticket",
    "expires",
    "justification",
    "retires",
)


def _load_yaml(
    path: Path,
) -> dict[str, Any]:  # ONEX_EXCLUDE: dict_str_any — raw YAML document
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(  # error-ok: shape validation at load boundary
            f"{path} must parse to a mapping"
        )
    return data


def triggers_on_pull_request(
    workflow: dict[str, Any],  # ONEX_EXCLUDE: dict_str_any — raw workflow YAML
) -> bool:
    """Return True iff *workflow* triggers on ``pull_request``/``pull_request_target``."""
    # PyYAML parses the bare `on:` key as the boolean-True key in YAML 1.1.
    untyped_workflow: dict[Any, Any] = workflow
    on = untyped_workflow.get("on", untyped_workflow.get(True))
    if isinstance(on, dict):
        keys: set[str] = {str(k) for k in on}
    elif isinstance(on, list):
        keys = {str(k) for k in on}
    else:
        keys = {str(on)}
    return bool(keys & _PR_TRIGGER_KEYS)


def live_pull_request_workflows(workflows_dir: Path) -> list[str]:
    """Return the sorted file names under *workflows_dir* that trigger on PR events."""
    names: list[str] = []
    for path in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        try:
            workflow = _load_yaml(path)
        except ValueError:
            # A malformed workflow file is not this gate's concern to parse, but a
            # file we cannot read must not be silently dropped — surface it as a
            # live PR trigger so it is forced through registration. Fail-closed.
            names.append(path.name)
            continue
        if triggers_on_pull_request(workflow):
            names.append(path.name)
    return sorted(names)


def _validate_waivers(
    waivers: list[Any], today: date
) -> tuple[set[str], list[ModelWorkflowRatchetGap]]:
    """Return (waived_file_names, gaps). A malformed or expired waiver is a gap."""
    waived: set[str] = set()
    gaps: list[ModelWorkflowRatchetGap] = []
    for entry in waivers:
        if not isinstance(entry, dict):
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file="<waiver>",
                    code="WAIVER_INCOMPLETE",
                    detail=f"waiver entry is not a mapping: {entry!r}",
                )
            )
            continue
        wf = str(entry.get("workflow_file", "<unknown>"))
        missing = [f for f in _REQUIRED_WAIVER_FIELDS if not entry.get(f)]
        if missing:
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file=wf,
                    code="WAIVER_INCOMPLETE",
                    detail=(
                        f"waiver missing required field(s) {missing} — a waiver must "
                        "carry ticket + expires + justification + retires"
                    ),
                )
            )
            continue
        waived.add(wf)
        try:
            expires = date.fromisoformat(str(entry["expires"]))
        except ValueError:
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file=wf,
                    code="WAIVER_INCOMPLETE",
                    detail=f"waiver expires is not an ISO date: {entry['expires']!r}",
                )
            )
            continue
        if expires < today:
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file=wf,
                    code="WAIVER_EXPIRED",
                    detail=(
                        f"waiver expired {expires.isoformat()} (ticket "
                        f"{entry['ticket']}) — migrate the workflow into ci.yml, "
                        "retire it, or renew the waiver with fresh justification"
                    ),
                )
            )
    return waived, gaps


def verify_pull_request_workflow_ratchet(
    *, repo_root: Path, registry_path: Path, today: date | None = None
) -> list[ModelWorkflowRatchetGap]:
    """Return count-locked-ratchet gaps. Empty list means the ratchet holds.

    A non-empty list means at least one of: a live PR-triggered workflow is not
    enumerated (``UNREGISTERED``); a registry entry has no live file (``STALE``);
    an allowlisted file no longer triggers on PR (``NOT_PR_TRIGGERED``); the
    budget count does not match the allowlist length (``BUDGET_MISMATCH``); or a
    waiver is expired/incomplete.

    Raises:
        ValueError: If the registry is malformed (fail loud, never silent).
    """
    today = today or datetime.now(UTC).date()
    registry = _load_yaml(registry_path)

    budget = registry.get("budget")
    if not isinstance(budget, int) or isinstance(budget, bool):
        raise ValueError(  # error-ok: registry shape validation
            f"budget must be an int, got {type(budget).__name__}"
        )

    allowlist_raw = registry.get("allowlisted_workflows", [])
    if not isinstance(allowlist_raw, list):
        raise ValueError(  # error-ok: registry shape validation
            f"allowlisted_workflows must be a list, got {type(allowlist_raw).__name__}"
        )
    allowlist = [str(entry) for entry in allowlist_raw]

    waivers_raw = registry.get("waivers", []) or []
    if not isinstance(waivers_raw, list):
        raise ValueError(  # error-ok: registry shape validation
            f"waivers must be a list, got {type(waivers_raw).__name__}"
        )

    gaps: list[ModelWorkflowRatchetGap] = []

    waived, waiver_gaps = _validate_waivers(waivers_raw, today)
    gaps.extend(waiver_gaps)

    # BUDGET_MISMATCH: the count lock. len(allowlist) must equal the declared
    # budget. Registering a net-new file (list -> budget+1) fails here; the test
    # suite freezes the budget a second time so any move is a deliberate edit.
    if len(allowlist) != budget:
        gaps.append(
            ModelWorkflowRatchetGap(
                workflow_file="<budget>",
                code="BUDGET_MISMATCH",
                detail=(
                    f"budget={budget} but allowlisted_workflows has {len(allowlist)} "
                    "entries — the count lock only moves DOWN: retire a workflow or "
                    "move the new one into the waivers bucket"
                ),
            )
        )

    allowlist_set = set(allowlist)
    registered = allowlist_set | waived

    workflows_dir = repo_root / ".github" / "workflows"
    live = live_pull_request_workflows(workflows_dir)
    live_set = set(live)

    # UNREGISTERED: every live PR-triggered workflow must be enumerated.
    for filename in live:
        if filename not in registered:
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file=filename,
                    code="UNREGISTERED",
                    detail=(
                        "triggers on pull_request but is not enumerated in "
                        f"{registry_path.name} — a NEW PR-triggered workflow must "
                        "retire an existing one (net-negative) or carry a waiver"
                    ),
                )
            )

    # STALE: every allowlisted file must still exist (forces the down-ratchet on
    # deletion). NOT_PR_TRIGGERED: an allowlisted file that stopped triggering on
    # PR must be removed and the budget lowered.
    for filename in allowlist:
        if filename not in live_set:
            path = workflows_dir / filename
            if path.exists():
                gaps.append(
                    ModelWorkflowRatchetGap(
                        workflow_file=filename,
                        code="NOT_PR_TRIGGERED",
                        detail=(
                            "listed in allowlisted_workflows but the live file no "
                            "longer triggers on pull_request — remove it and lower "
                            "the budget"
                        ),
                    )
                )
            else:
                gaps.append(
                    ModelWorkflowRatchetGap(
                        workflow_file=filename,
                        code="STALE",
                        detail=(
                            "listed in allowlisted_workflows but no matching file "
                            f"exists at {path} — remove the entry and lower the budget"
                        ),
                    )
                )

    # STALE waivers: a waiver for a file that is gone (or no longer PR-triggered).
    for wf in sorted(waived):
        if wf not in live_set:
            gaps.append(
                ModelWorkflowRatchetGap(
                    workflow_file=wf,
                    code="STALE",
                    detail=(
                        "waived but no matching live PR-triggered file exists — "
                        "remove the stale waiver"
                    ),
                )
            )

    return gaps


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count-locked ratchet over pull_request-triggered workflow files "
            "(C7 / OMN-14907). A NEW PR-triggered workflow must retire an existing "
            "one or carry an expiring waiver; the budget count only moves DOWN."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd).",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help=(
            "Path to the budget registry YAML "
            "(default: <repo-root>/architecture-handshakes/pull-request-workflow-budget.yaml)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root: Path = args.repo_root
    registry_path: Path = args.registry or (repo_root / DEFAULT_REGISTRY_PATH)

    try:
        gaps = verify_pull_request_workflow_ratchet(
            repo_root=repo_root, registry_path=registry_path
        )
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"pull-request-workflow-ratchet: registry error: {exc}\n")
        return 1

    if gaps:
        sys.stderr.write(
            "pull-request-workflow-ratchet: the count-locked ratchet over "
            "pull_request-triggered workflows is broken:\n"
        )
        for gap in gaps:
            sys.stderr.write(f"{gap.format()}\n")
        sys.stderr.write(
            "\n  This is CLAUDE.md's net-negative-surface rule as a mechanism. A "
            "NEW\n  PR-triggered workflow file must retire an existing one, or be "
            "added to\n  the waivers bucket (ticket + expires + justification + "
            "retires) in\n  architecture-handshakes/pull-request-workflow-budget.yaml. "
            "See C7 /\n  OMN-14907.\n\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: validator CLI process exit
