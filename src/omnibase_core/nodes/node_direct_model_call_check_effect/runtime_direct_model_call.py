# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for check-direct-model-call (OMN-20295): pre-commit hook and CI command.

The EFFECT handler (``HandlerDirectModelCallCheckEffect``) reads the
repository, the policy and the baseline; the COMPUTE handler
(``HandlerDirectModelCallCompute``) judges them; this module prints the
verdict and, with ``--write-baseline``, writes the baseline the COMPUTE side
rendered.

Pre-commit runs it with ``pass_filenames: false`` and ``always_run: true``:
the scan is always the whole repository.

Ratchet contract, with ``--baseline <file>``:

* a site the baseline does not cover fails the run;
* a baseline entry that no longer matches a site fails the run and is named,
  so the baseline shrinks as the sites are removed;
* an entry past its ``expires`` date no longer covers its site;
* an entry whose target has a required removal ticket (crush: OMN-20290) and
  names another ticket fails;
* ``--base <ref>`` fails when the baseline carries an entry, or a later expiry,
  or another ticket, that the same file at ``<ref>`` did not: entries only
  leave. A baseline absent at ``<ref>`` is accepted only when ``<ref>`` did not
  wire this gate yet, so deleting the baseline and re-creating it is refused.

There is no suppression marker, no skip flag and no advisory mode.

Exit codes: 0 clean, 1 findings / stale / expired / growth / unreadable input.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_input import (
    ModelDirectModelCallCheckInput,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_request import (
    ModelDirectModelCallCheckRequest,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
    ModelDirectModelCallFinding,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._baseline import (
    bootstrap_entries,
    render_baseline,
    shrink_entries,
)
from omnibase_core.nodes.node_direct_model_call_check_compute.handler import (
    HandlerDirectModelCallCompute,
)
from omnibase_core.nodes.node_direct_model_call_check_effect.handler import (
    HOOK_ID,
    HandlerDirectModelCallCheckEffect,
)

__all__ = ["build_parser", "main"]


def _out(text: str) -> None:
    sys.stdout.write(f"{text}\n")


def _print_finding(finding: ModelDirectModelCallFinding) -> None:
    _out(
        f"{finding.path}:{finding.line}: [{finding.kind} {finding.target} in "
        f"{finding.symbol}] {finding.evidence}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=HOOK_ID,
        description=(
            "Refuse a direct model call (HTTP to a model endpoint, provider or "
            "base_url; a model CLI exec; a model SDK import; or a caller of one) "
            "outside the sanctioned delegation node packages (OMN-20295)."
        ),
    )
    parser.add_argument("--repo", required=True, help="Repository name in policy.yaml")
    parser.add_argument("--repo-root", default=".", help="Repository root (default .)")
    parser.add_argument("--baseline", help="Committed shrink-only baseline")
    parser.add_argument(
        "--base", help="Git ref whose baseline this one may only shrink from"
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help=(
            "Shrink the baseline to the sites still present. Only when no baseline "
            "exists yet does it create one, from --ticket-rule and --expires."
        ),
    )
    parser.add_argument(
        "--ticket-rule",
        action="append",
        default=[],
        metavar="PATH_PREFIX=OMN-N",
        help="Bootstrap only: removal ticket for sites under a path prefix ('*' = any)",
    )
    parser.add_argument("--expires", help="Bootstrap only: expiry date (YYYY-MM-DD)")
    parser.add_argument(
        "paths", nargs="*", help="Ignored: the whole repository is always scanned"
    )
    return parser


def _judge(check_input: ModelDirectModelCallCheckInput) -> int:
    try:
        verdict = HandlerDirectModelCallCompute().handle(check_input)
    except SyntaxError as exc:
        _out(
            f"{HOOK_ID}: {exc.filename}:{exc.lineno}: does not parse, so it cannot "
            f"be judged: {exc.msg}"
        )
        return 1
    for note in verdict.notes:
        _out(note)
    for finding in verdict.new:
        _print_finding(finding)
    for entry in verdict.stale:
        _out(
            f"{entry.path}: stale baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] no longer matches a site; remove it"
        )
    for entry in verdict.expired:
        _out(
            f"{entry.path}: baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] expired on {entry.expires} ({entry.ticket})"
        )
    for entry in verdict.grown:
        _out(
            f"{entry.path}: baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] {entry.ticket} {entry.expires} was added or widened "
            f"against {check_input.base_ref} (entries only leave)"
        )
    for problem in verdict.problems:
        _out(problem)
    if not verdict.passed:
        _out(
            f"\n{len(verdict.new)} new direct model call site(s), "
            f"{len(verdict.stale)} stale, {len(verdict.expired)} expired, "
            f"{len(verdict.grown)} added baseline entr(y/ies), "
            f"{len(verdict.problems)} other. "
            "A model call goes through the delegation nodes (onex delegate, "
            "onex code-edit run, the delegation call effect), never directly. "
            "There is no suppression marker and no new baseline entry: a "
            "sanctioned package is a change to omnibase_core's "
            "nodes/node_direct_model_call_check_compute/policy.yaml."
        )
        return 1
    _out(
        f"{HOOK_ID}: {len(check_input.files)} file(s) scanned, "
        f"{len(verdict.findings)} site(s), all covered by "
        f"{len(check_input.baseline)} baseline entr(y/ies)."
    )
    return 0


def _write(
    args: argparse.Namespace, check_input: ModelDirectModelCallCheckInput
) -> int:
    if args.baseline is None:
        _out(f"{HOOK_ID}: --write-baseline needs --baseline <file>")
        return 1
    findings = HandlerDirectModelCallCompute().handle(check_input).findings
    target = Path(args.repo_root) / args.baseline
    if target.is_file():
        kept, remaining = shrink_entries(findings, check_input.baseline)
        target.write_text(render_baseline(kept), encoding="utf-8")
        _out(
            f"Shrank {args.baseline} from {len(check_input.baseline)} to {len(kept)} "
            f"entries; {len(remaining)} site(s) are not covered and were NOT added."
        )
        return 1 if remaining else 0
    if not args.expires:
        _out(f"{HOOK_ID}: bootstrap needs --expires YYYY-MM-DD")
        return 1
    expires = date.fromisoformat(args.expires)
    if expires < check_input.today:
        _out(f"{HOOK_ID}: --expires {expires} is in the past")
        return 1
    rules = [tuple(rule.partition("=")[::2]) for rule in args.ticket_rule]
    entries, unticketed = bootstrap_entries(
        check_input.policy, findings, rules, expires
    )
    if unticketed:
        for finding in unticketed:
            _print_finding(finding)
        _out(
            f"\nRefusing to bootstrap: {len(unticketed)} site(s) have no removal ticket."
        )
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_baseline(entries), encoding="utf-8")
    _out(
        f"Bootstrapped {args.baseline} with {len(entries)} entries expiring {expires}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        check_input = HandlerDirectModelCallCheckEffect().handle(
            ModelDirectModelCallCheckRequest(
                repo=args.repo,
                repo_root=args.repo_root,
                baseline_path=args.baseline,
                base_ref=args.base,
            )
        )
    except ModelOnexError as exc:
        _out(f"{HOOK_ID}: {exc.message}")
        return 1
    if args.write_baseline:
        return _write(args, check_input)
    return _judge(check_input)


if __name__ == "__main__":
    sys.exit(main())
