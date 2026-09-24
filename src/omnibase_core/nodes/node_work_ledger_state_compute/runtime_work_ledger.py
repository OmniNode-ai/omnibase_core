# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex-work-ledger``: the read CLI of the typed work ledger (OMN-19405, plan T5).

The effect boundary around the pure fold node ``node_work_ledger_state_compute``.
It reads the JSON-lines ledger named by ``ONEX_WORK_LEDGER_PATH`` (no default),
folds it, asks one query, and prints one verdict. It never reads the md ledger.

It lives beside the fold as the node's ``runtime_*`` entry point, the pattern the
check nodes use (``runtime_no_utcnow_check``): all file, clock and environment
access happens here, never in the handler. ``omnibase_core.cli`` may not import
``omnibase_core.nodes`` (the core-execution-tier-no-nodes import-linter
contract), so the console script targets this module directly.

Usage::

    onex-work-ledger held --repo omnibase_infra --pr 4005 --action merge \\
        --runtime-affecting yes
    onex-work-ledger pauses --repo omnimarket [--runtime-affecting [yes|no|unknown]]
    onex-work-ledger claims [--ticket OMN-1] [--repo R --pr N] [--lane L]
    onex-work-ledger inbox --lane <lane>
    onex-work-ledger surface --surface <surface>
    onex-work-ledger health

Every output starts with one header line, so each call is a durable readback::

    ledger=<path> sha256=<hex|none> lines=<n> epoch=<uuid|none>

Exit codes: 0 CLEAR, 3 HELD or FOUND, 2 UNDECIDED. UNDECIDED covers an unset
``ONEX_WORK_LEDGER_PATH``, a missing or unreadable file, any line that does not
parse, a ledger with no epoch event, and a conflicting duplicate event_id. An
unterminated final line is an append still being written and is left out.

``--runtime-affecting`` given with no value, with ``unknown``, or not given at
all is treated as ``yes``: a PR of unknown class is held by runtime-only holds.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Final

from pydantic import ValidationError

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_work_ledger_line import (
    WORK_LEDGER_EVENTS_PATH_ENV,
    events_path_from_env,
)
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_fold_input import (
    ModelWorkLedgerFoldInput,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state import (
    ModelWorkLedgerState,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_verdict import (
    ModelWorkLedgerVerdict,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    NodeWorkLedgerStateCompute,
    complete_ledger_lines,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    actor_lane,
    health,
    inbox,
    is_held,
    open_claims,
    pauses_in_force,
    surface_lease,
)

__all__ = ["EXIT_UNDECIDED", "main"]

EXIT_UNDECIDED: Final = 2
"""Exit code of every answer that is not certain. Never 0."""

_RUNTIME_CHOICES: Final = ("yes", "no", "unknown")


_Read = tuple[str, str | None, tuple[str, ...], str | None]
"""What the CLI read from disk: path, file sha256, complete lines, and any doubt."""


def _read_ledger() -> _Read:
    """Read the ledger named by the environment. Never raises; doubts are recorded."""
    try:
        path = events_path_from_env()
    except KeyError:
        return (
            "<unset>",
            None,
            (),
            f"{WORK_LEDGER_EVENTS_PATH_ENV} is not set; it names the JSON-lines "
            "ledger and has no default",
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return str(path), None, (), f"ledger unreadable: {exc}"
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return str(path), digest, (), f"ledger is not UTF-8: {exc}"
    return str(path), digest, complete_ledger_lines(text), None


def _fold(lines: tuple[str, ...], doubt: str | None) -> ModelWorkLedgerState:
    state = NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=lines, as_of=datetime.now(UTC))
    )
    if doubt is None:
        return state
    return state.model_copy(
        update={"undecided_reasons": tuple(sorted({*state.undecided_reasons, doubt}))}
    )


def _one_line(text: str) -> str:
    """Collapse a reason onto one line, so each output line stays one item."""
    return " ".join(text.split())


def _runtime_affecting(value: str | None) -> bool:
    """``no`` is the only value that clears a runtime-only hold."""
    return value != "no"


def _scope_text(scope: ModelHoldScope) -> str:
    parts: list[str] = []
    if scope.all_repos:
        parts.append("all_repos")
    parts.extend(f"repo:{repo}" for repo in sorted(scope.repos))
    parts.extend(
        f"pr:{key.repo}#{key.number}"
        for key in sorted(scope.prs, key=lambda k: (k.repo, k.number))
    )
    parts.extend(f"surface:{name}" for name in sorted(scope.surfaces))
    parts.extend(f"lane:{name}" for name in sorted(scope.lanes))
    return ",".join(parts)


def _hold_line(held: ModelHoldInForce) -> str:
    hold = held.hold
    fields = [
        f"hold event={hold.event_id}",
        f"lane={actor_lane(hold.actor)}",
        f"emitted_at={hold.emitted_at.isoformat()}",
        f"blocks={','.join(sorted(block.value for block in hold.blocks))}",
        f"scope={_scope_text(hold.scope)}",
        f"runtime_only={'yes' if hold.runtime_only else 'no'}",
    ]
    if held.partial_releases:
        exempt = ";".join(
            _scope_text(release.partial_scope)
            for release in held.partial_releases
            if release.partial_scope is not None
        )
        fields.append(f"exempt={exempt}")
    if hold.expires_at is not None:
        fields.append(f"expires_at={hold.expires_at.isoformat()}")
    if held.expired_unreleased:
        fields.append("lease=EXPIRED-UNRELEASED")
    return " ".join(fields)


def _verdict_lines(verdict: ModelWorkLedgerVerdict, query: str) -> list[str]:
    out = [f"verdict={verdict.status.value} {query}"]
    out.extend(f"reason={_one_line(reason)}" for reason in verdict.undecided_reasons)
    out.extend(_hold_line(held) for held in verdict.holds)
    out.extend(
        f"claim event={claim.event_id} ticket={claim.ticket_id} "
        f"lane={actor_lane(claim.actor)} emitted_at={claim.emitted_at.isoformat()}"
        for claim in verdict.claims
    )
    out.extend(
        f"message event={message.event_id} from={actor_lane(message.actor)} "
        f"emitted_at={message.emitted_at.isoformat()}"
        for message in verdict.messages
    )
    return out


def _pr_key(repo: str | None, number: int | None) -> ModelPrKey | None:
    """The PR filter, when both halves are given; the parser refuses one half alone."""
    if repo is None or number is None:
        return None
    return ModelPrKey(repo=repo, number=number)


def _answer(
    args: argparse.Namespace, state: ModelWorkLedgerState
) -> tuple[int, list[str]]:
    command: str = args.command
    if command == "health":
        report = health(state)
        status = "clear" if state.decidable else "undecided"
        lines = [
            f"verdict={status} query=health events={report.event_count} "
            f"holds_in_force={report.holds_in_force_count} "
            f"invalid_releases={report.invalid_release_count} "
            f"epoch_seq={'none' if report.epoch_seq is None else report.epoch_seq} "
            "last_event_at="
            + (
                "none"
                if report.last_event_at is None
                else report.last_event_at.isoformat()
            )
        ]
        lines.extend(f"reason={_one_line(r)}" for r in report.undecided_reasons)
        return (0 if state.decidable else EXIT_UNDECIDED), lines

    if command == "held":
        pr = ModelPrKey(repo=args.repo, number=args.pr)
        action = EnumHoldBlock(args.action)
        verdict = is_held(state, pr, action, _runtime_affecting(args.runtime_affecting))
        query = (
            f"query=held repo={pr.repo} pr={pr.number} action={action.value} "
            f"runtime_affecting={args.runtime_affecting or 'unknown'}"
        )
    elif command == "pauses":
        repo = args.repo.lower()
        verdict = pauses_in_force(
            state, repo, _runtime_affecting(args.runtime_affecting)
        )
        query = (
            f"query=pauses repo={repo} "
            f"runtime_affecting={args.runtime_affecting or 'unknown'}"
        )
    elif command == "claims":
        pr_filter = _pr_key(args.repo, args.pr)
        verdict = open_claims(
            state, ticket_id=args.ticket, pr=pr_filter, lane=args.lane
        )
        query = "query=claims" + "".join(
            f" {name}={value}"
            for name, value in (
                ("ticket", args.ticket),
                ("repo", None if pr_filter is None else pr_filter.repo),
                ("pr", None if pr_filter is None else pr_filter.number),
                ("lane", args.lane),
            )
            if value is not None
        )
    elif command == "inbox":
        verdict = inbox(state, args.lane)
        query = f"query=inbox lane={args.lane}"
    else:
        verdict = surface_lease(state, args.surface)
        query = f"query=surface surface={args.surface}"
    return verdict.exit_code, _verdict_lines(verdict, query)


def _add_runtime_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--runtime-affecting",
        nargs="?",
        const="yes",
        default=None,
        choices=_RUNTIME_CHOICES,
        help=(
            "Whether the PR is runtime-affecting. No value, 'unknown' or leaving "
            "the option out is treated as yes (fail closed)."
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onex-work-ledger",
        description=(
            "Answer one question from the typed work ledger named by "
            f"{WORK_LEDGER_EVENTS_PATH_ENV}. Exit 0 CLEAR, 3 HELD or FOUND, "
            "2 UNDECIDED."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    held = sub.add_parser("held", help="Is an action on one PR held?")
    held.add_argument("--repo", required=True)
    held.add_argument("--pr", required=True, type=int)
    held.add_argument(
        "--action", required=True, choices=[block.value for block in EnumHoldBlock]
    )
    _add_runtime_option(held)

    pauses = sub.add_parser("pauses", help="Repo and all-repo holds covering a repo.")
    pauses.add_argument("--repo", required=True)
    _add_runtime_option(pauses)

    claims = sub.add_parser("claims", help="Open claims matching every filter given.")
    claims.add_argument("--ticket")
    claims.add_argument("--repo")
    claims.add_argument("--pr", type=int)
    claims.add_argument("--lane")

    inbox_parser = sub.add_parser("inbox", help="Unacknowledged items for a lane.")
    inbox_parser.add_argument("--lane", required=True)

    surface = sub.add_parser("surface", help="The lease in force on a surface.")
    surface.add_argument("--surface", required=True)

    sub.add_parser("health", help="Counts, last event, epoch and reasons for doubt.")
    return parser


def _header(
    path: str, sha256: str | None, line_count: int, state: ModelWorkLedgerState
) -> str:
    epoch = "none" if state.epoch is None else str(state.epoch.event_id)
    return f"ledger={path} sha256={sha256 or 'none'} lines={line_count} epoch={epoch}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one query and print its verdict. Returns the exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "claims" and (args.repo is None) != (args.pr is None):
        parser.error("claims: --repo and --pr are given together")
    path, sha256, ledger_lines, doubt = _read_ledger()
    state = _fold(ledger_lines, doubt)
    try:
        code, out = _answer(args, state)
    except ValidationError as exc:
        # A malformed repo name or PR number decides nothing: fail closed.
        first = exc.errors()[0]
        code = EXIT_UNDECIDED
        out = [
            f"verdict=undecided query={args.command}",
            f"reason=invalid argument: {_one_line(str(first['loc']))}: "
            f"{_one_line(str(first['msg']))}",
        ]
    header = _header(path, sha256, len(ledger_lines), state)
    sys.stdout.write("\n".join([header, *out]) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
