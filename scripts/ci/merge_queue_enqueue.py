#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Reliable merge-queue enqueue decision logic (OMN-13214).

Root cause this module addresses
--------------------------------
During the 2026-06-17 dev merge wave, many PRs reached ``mergeStateStatus=CLEAN``
with all required checks green AND auto-merge armed (by the "Enable Auto-Merge"
GitHub Actions job), yet never entered the dev merge queue. Each one needed a
manual ``enqueuePullRequest`` GraphQL mutation (or a disable+re-arm with bare
``--auto``) to actually land.

Arming auto-merge is **not** the same as enqueuing. On a queue-controlled repo a
PR can sit CLEAN + armed indefinitely without GitHub ever placing it in the
queue. The reliable path is an explicit ``enqueuePullRequest`` after arming,
followed by a verification that the PR actually entered the queue. On
strict-update (require-branches-up-to-date) repos a branch-behind PR silently
blocks enqueue with no auto ``update-branch`` step.

This module is the deterministic, unit-tested core of the workflow step. The
``auto-merge.yml`` workflow shells out to it to decide what action to take and to
verify the outcome; all the branching that is worth testing in isolation lives
here rather than in untestable bash.

The module performs **no** network I/O. The workflow is responsible for fetching
PR JSON via ``gh`` and passing it in; this module only classifies and decides.
"""

from __future__ import annotations

import argparse
import json
import sys
from enum import StrEnum


class EnumEnqueueAction(StrEnum):
    """The action the workflow should take for a PR, derived from its state."""

    ALREADY_QUEUED = "already_queued"
    UPDATE_BRANCH_THEN_ENQUEUE = "update_branch_then_enqueue"
    ENQUEUE = "enqueue"
    WAIT = "wait"
    BLOCKED = "blocked"


# mergeStateStatus values that mean "GitHub will not let this PR merge / enqueue
# right now for a reason that is not a transient branch-behind". These are not
# our bug to fix; the workflow waits and re-fires on the next event.
_NON_ENQUEUEABLE_STATES = frozenset(
    {
        "BLOCKED",  # required checks pending/failing or required review missing
        "DIRTY",  # merge conflict
        "DRAFT",  # draft PR
        "UNKNOWN",  # GitHub still computing mergeability
    }
)

# gh / GraphQL error fragments that mean the repo simply has no merge queue.
# Enqueue is a no-op there; arming auto-merge is sufficient.
_NO_MERGE_QUEUE_MARKERS = (
    "does not have a merge queue",
    "merge queue is not enabled",
    "merge_queue_not_enabled",
    "merge queue not enabled",
)

# gh / GraphQL error fragments that are benign races — the PR is already on its
# way into the queue, or a concurrent run already enqueued it.
_BENIGN_ENQUEUE_MARKERS = (
    "already enqueued",
    "already queued",
    "already in the merge queue",
    "is already queued",
    "pull request is in the merge queue",
)


def _truthy(value: object) -> bool:
    """Coerce a JSON-ish value to bool without surprising falsy strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def is_no_merge_queue_error(message: str) -> bool:
    """True when an enqueue error means the repo has no merge queue (benign)."""
    lowered = message.lower()
    return any(marker in lowered for marker in _NO_MERGE_QUEUE_MARKERS)


def is_benign_enqueue_error(message: str) -> bool:
    """True when an enqueue error is a benign already-queued race (benign)."""
    lowered = message.lower()
    return any(marker in lowered for marker in _BENIGN_ENQUEUE_MARKERS)


def is_armed(pr: dict[str, object]) -> bool:
    """True when auto-merge is armed on the PR.

    ``gh pr view --json autoMergeRequest`` returns ``null`` when not armed and an
    object (with ``enabledBy``/``mergeMethod``) when armed.
    """
    return pr.get("autoMergeRequest") not in (None, {}, "")


def is_in_queue(pr: dict[str, object]) -> bool:
    """True when the PR is already in the merge queue."""
    return _truthy(pr.get("isInMergeQueue"))


def is_behind(pr: dict[str, object]) -> bool:
    """True when the PR head is behind its base (strict-update would block it).

    ``mergeStateStatus == BEHIND`` is the authoritative GitHub signal. We also
    treat an explicit ``behind`` integer (from a compare API) as behind.
    """
    if str(pr.get("mergeStateStatus", "")).upper() == "BEHIND":
        return True
    behind = pr.get("behind")
    return isinstance(behind, int) and behind > 0


def classify_pr(pr: dict[str, object], *, strict_update: bool) -> EnumEnqueueAction:
    """Decide what to do with a PR based on its current GitHub state.

    Args:
        pr: ``gh pr view --json ...`` payload (isInMergeQueue, mergeStateStatus,
            autoMergeRequest, mergeable, behind).
        strict_update: True when the target branch requires branches to be up to
            date before merging (require_status_checks.strict). On such repos a
            BEHIND PR must be updated before it can enqueue.

    Returns:
        The action the workflow should take.
    """
    if is_in_queue(pr):
        return EnumEnqueueAction.ALREADY_QUEUED

    state = str(pr.get("mergeStateStatus", "")).upper()

    # A branch-behind PR on a strict-update repo cannot enqueue until updated.
    # On a non-strict repo BEHIND does not block enqueue, so fall through.
    if is_behind(pr) and strict_update:
        return EnumEnqueueAction.UPDATE_BRANCH_THEN_ENQUEUE

    # CLEAN / HAS_HOOKS / UNSTABLE-but-mergeable: ready to enqueue.
    # (UNSTABLE = non-required checks failing; required checks still green.)
    if state in {"CLEAN", "HAS_HOOKS", "UNSTABLE"}:
        return EnumEnqueueAction.ENQUEUE

    # BEHIND on a non-strict repo: GitHub allows the queue to merge it; enqueue.
    if state == "BEHIND":
        return EnumEnqueueAction.ENQUEUE

    if state in _NON_ENQUEUEABLE_STATES:
        # BLOCKED/DIRTY/DRAFT/UNKNOWN: not our bug — wait for the next event.
        return EnumEnqueueAction.WAIT

    # Unrecognised state: do not silently enqueue; surface as blocked so the
    # workflow logs it rather than masking a new GitHub state.
    return EnumEnqueueAction.BLOCKED


def verify_enqueued(pr_after: dict[str, object]) -> bool:
    """Confirm a PR actually entered the queue after an enqueue attempt.

    This is the enforcement check that distinguishes "armed" from "actually
    enqueued" — the exact gap OMN-13214 closes.
    """
    return is_in_queue(pr_after)


def _load_pr(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("PR JSON must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI surface for the workflow.

    Subcommands:
        classify  --pr-json <json> --strict-update <true|false>
            Prints the EnumEnqueueAction value to stdout.
        verify    --pr-json <json>
            Exit 0 if the PR is in the queue, exit 1 otherwise.
    """
    parser = argparse.ArgumentParser(description="Merge-queue enqueue decision logic")
    sub = parser.add_subparsers(dest="command", required=True)

    p_classify = sub.add_parser("classify", help="Classify a PR into an action")
    p_classify.add_argument("--pr-json", required=True)
    p_classify.add_argument("--strict-update", default="false")

    p_verify = sub.add_parser("verify", help="Verify a PR actually entered the queue")
    p_verify.add_argument("--pr-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "classify":
        pr = _load_pr(args.pr_json)
        action = classify_pr(pr, strict_update=_truthy(args.strict_update))
        sys.stdout.write(action.value + "\n")
        return 0
    elif args.command == "verify":
        pr = _load_pr(args.pr_json)
        if verify_enqueued(pr):
            sys.stdout.write("in_queue\n")
            return 0
        sys.stdout.write("not_in_queue\n")
        return 1
    else:
        # argparse marks the subcommand required, so this is defensive only.
        # parser.error() raises SystemExit; raising keeps every branch of this
        # function terminating with an explicit return or raise (no implicit
        # fall-through that would silently return None).
        raise SystemExit(parser.error(f"unknown command: {args.command}"))


if __name__ == "__main__":
    raise SystemExit(main())
