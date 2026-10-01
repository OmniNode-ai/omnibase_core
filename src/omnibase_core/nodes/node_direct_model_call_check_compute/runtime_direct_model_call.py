# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EFFECT boundary for check-direct-model-call (OMN-20295).

Owns every piece of I/O the pure handler must not do: listing and reading the
repository's tracked files, reading the packaged policy, the committed baseline
and (with ``--base``) the baseline and hook configuration as they stood at a
git ref, and reading today's date. The verdict is computed by the handler.

The scan is always the whole repository (``git ls-files``), because a new call
site can be a new caller of an old one: the call graph needs every file.
Pre-commit runs it with ``pass_filenames: false`` and ``always_run: true``.

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
import subprocess
import sys
from datetime import UTC, date, datetime
from importlib import resources
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.nodes.node_direct_model_call_check_compute.handler import (
    HandlerDirectModelCallCompute,
    added_entries,
    compare_with_baseline,
    entry_problems,
)
from omnibase_core.nodes.node_direct_model_call_check_compute.models import (
    ModelDirectModelCallBaseline,
    ModelDirectModelCallBaselineEntry,
    ModelDirectModelCallFinding,
    ModelDirectModelCallPolicy,
    ModelDirectModelCallScanInput,
    ModelDirectModelCallSourceFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = [
    "HOOK_ID",
    "build_parser",
    "load_policy",
    "main",
]

HOOK_ID: Final[str] = "check-direct-model-call"
_POLICY_RESOURCE: Final[str] = "policy.yaml"
_SCANNED_SUFFIXES: Final[tuple[str, ...]] = (".py", ".pyi", ".sh", ".bash")
_SHEBANG_LIMIT: Final[int] = 1_000_000
_HOOK_CONFIGS: Final[tuple[str, ...]] = (
    ".pre-commit-config.yaml",
    ".github/workflows/direct-model-call.yml",
)
_BASELINE_HEADER: Final[str] = """\
# Baseline for check-direct-model-call (OMN-20295).
# A model call must sit inside a sanctioned delegation
# node package (omnibase_core nodes/node_direct_model_call_check_compute/policy.yaml).
#
# RULE: entries only leave. A site not listed here fails. An entry that no
# longer matches a site fails until it is removed. An entry past its expiry no
# longer covers its site. CI and the pre-commit hook refuse a change whose copy
# of this file carries an entry, a later expiry or another ticket that its
# base did not. Crush sites name OMN-20290 for their removal.
#
# Regenerate only to SHRINK it:
#   python -m omnibase_core.nodes.node_direct_model_call_check_compute.runtime_direct_model_call \\
#     --repo <repo> --baseline <this file> --write-baseline
"""


def _out(text: str) -> None:
    sys.stdout.write(f"{text}\n")


class _InputError(Exception):
    """An input the gate cannot read. The gate fails closed on it."""


def load_policy() -> ModelDirectModelCallPolicy:
    """Read the policy shipped inside this package."""
    package = __package__ or "omnibase_core.nodes.node_direct_model_call_check_compute"
    raw = resources.files(package).joinpath(_POLICY_RESOURCE).read_text("utf-8")
    try:
        return load_yaml_content_as_model(raw, ModelDirectModelCallPolicy)
    except ModelOnexError as exc:
        raise _InputError(f"policy.yaml is invalid: {exc}") from exc


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _tracked_files() -> list[str]:
    result = _git("ls-files", "-z")
    if result.returncode != 0:
        raise _InputError(f"git ls-files failed: {result.stderr.strip()}")
    return sorted(p for p in result.stdout.split("\0") if p)


def _load_sources(paths: list[str]) -> list[ModelDirectModelCallSourceFile]:
    sources: list[ModelDirectModelCallSourceFile] = []
    for rel in paths:
        path = Path(rel)
        if not path.is_file() or path.is_symlink():
            continue
        name = path.name
        if not rel.endswith(_SCANNED_SUFFIXES):
            if "." in name or path.stat().st_size > _SHEBANG_LIMIT:
                continue
            with path.open("rb") as handle:
                if handle.read(2) != b"#!":
                    continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise _InputError(f"{rel}: unreadable: {exc}") from exc
        sources.append(ModelDirectModelCallSourceFile(path=rel, content=text))
    return sources


def _parse_baseline(raw: str, source: str) -> list[ModelDirectModelCallBaselineEntry]:
    try:
        document = load_yaml_content_as_model(raw, ModelDirectModelCallBaseline)
    except ModelOnexError as exc:
        raise _InputError(f"{source}: not a valid baseline: {exc}") from exc
    return list(document.entries)


def _show_at_ref(ref: str, path: str) -> str | None:
    """Return ``path`` at ``ref``, or None when absent there. A bad ref is an error."""
    if _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
        raise _InputError(f"--base {ref!r} does not resolve to a commit")
    if _git("cat-file", "-e", f"{ref}:{path}").returncode != 0:
        return None
    show = _git("show", f"{ref}:{path}")
    if show.returncode != 0:
        raise _InputError(f"git show {ref}:{path} failed: {show.stderr.strip()}")
    return show.stdout


def _gate_wired_at(ref: str) -> bool:
    for config in _HOOK_CONFIGS:
        text = _show_at_ref(ref, config)
        if text is not None and (HOOK_ID in text or "direct_model_call" in text):
            return True
    return False


def _write_baseline(
    path: Path, entries: list[ModelDirectModelCallBaselineEntry]
) -> None:
    lines = ["---", _BASELINE_HEADER, "schema_version: 1"]
    ordered = sorted(entries, key=lambda e: (*e.key(), e.ticket, e.expires))
    if not ordered:
        lines.append("entries: []")
    else:
        lines.append("entries:")
        for entry in ordered:
            fields = entry.model_dump(mode="json")
            for index, (name, value) in enumerate(fields.items()):
                scalar = yaml.safe_dump(value, default_flow_style=True, width=10_000)
                scalar = scalar.removesuffix("\n...\n").strip()
                prefix = "  - " if index == 0 else "    "
                lines.append(f"{prefix}{name}: {scalar}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_finding(finding: ModelDirectModelCallFinding) -> None:
    _out(
        f"{finding.path}:{finding.line}: [{finding.kind} {finding.target} in "
        f"{finding.symbol}] {finding.evidence}"
    )


def _ticket_for(
    finding: ModelDirectModelCallFinding,
    policy: ModelDirectModelCallPolicy,
    rules: list[tuple[str, str]],
) -> str | None:
    required = policy.required_ticket_by_target.get(finding.target)
    if required is not None:
        return required
    for prefix, ticket in rules:
        if finding.path.startswith(prefix) or prefix == "*":
            return ticket
    return None


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


def _run(args: argparse.Namespace) -> int:
    import os

    os.chdir(args.repo_root)
    policy = load_policy()
    today = datetime.now(tz=UTC).date()
    sources = _load_sources(_tracked_files())
    handler = HandlerDirectModelCallCompute(policy)
    try:
        findings = handler.handle(
            ModelDirectModelCallScanInput(repo=args.repo, files=tuple(sources))
        )
    except SyntaxError as exc:
        raise _InputError(
            f"{exc.filename}:{exc.lineno}: does not parse, so it cannot be judged: {exc.msg}"
        ) from exc

    baseline_path = Path(args.baseline) if args.baseline else None
    baseline: list[ModelDirectModelCallBaselineEntry] = []
    if baseline_path is not None and baseline_path.is_file():
        baseline = _parse_baseline(baseline_path.read_text("utf-8"), str(baseline_path))

    if args.write_baseline:
        return _write(args, policy, findings, baseline, baseline_path, today)

    comparison = compare_with_baseline(findings, baseline, today)
    problems = entry_problems(policy, baseline)
    grown: list[ModelDirectModelCallBaselineEntry] = []
    if args.base:
        if baseline_path is None:
            raise _InputError("--base needs --baseline <file>")
        base_raw = _show_at_ref(args.base, str(baseline_path))
        if base_raw is None:
            if _gate_wired_at(args.base) and baseline:
                problems.append(
                    f"{baseline_path}: absent at {args.base} although {args.base} already "
                    "wires this gate; a deleted baseline cannot be re-created"
                )
            else:
                _out(
                    f"NOTE: {baseline_path} does not exist at {args.base} and {args.base} "
                    "does not wire this gate; this change introduces both."
                )
                problems.extend(
                    f"{e.path}: bootstrap entry already expired on {e.expires}"
                    for e in baseline
                    if e.expires < today
                )
        else:
            base_entries = _parse_baseline(base_raw, f"{args.base}:{baseline_path}")
            grown = added_entries(base_entries, baseline)

    for finding in comparison.new:
        _print_finding(finding)
    for entry in comparison.stale:
        _out(
            f"{entry.path}: stale baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] no longer matches a site; remove it"
        )
    for entry in comparison.expired:
        _out(
            f"{entry.path}: baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] expired on {entry.expires} ({entry.ticket})"
        )
    for entry in grown:
        _out(
            f"{entry.path}: baseline entry [{entry.kind} {entry.target} in "
            f"{entry.symbol}] {entry.ticket} {entry.expires} was added or widened "
            f"against {args.base} (entries only leave)"
        )
    for problem in problems:
        _out(problem)

    failed = bool(
        comparison.new or comparison.stale or comparison.expired or grown or problems
    )
    if failed:
        _out(
            f"\n{len(comparison.new)} new direct model call site(s), "
            f"{len(comparison.stale)} stale, {len(comparison.expired)} expired, "
            f"{len(grown)} added baseline entr(y/ies), {len(problems)} other. "
            "A model call goes through the delegation nodes (onex delegate, "
            "onex code-edit run, the delegation call effect), never directly. "
            "There is no suppression marker and no new baseline entry: a "
            "sanctioned package is a change to omnibase_core's "
            "nodes/node_direct_model_call_check_compute/policy.yaml."
        )
        return 1
    _out(
        f"{HOOK_ID}: {len(sources)} file(s) scanned, {len(findings)} site(s), "
        f"all covered by {len(baseline)} baseline entr(y/ies)."
    )
    return 0


def _write(
    args: argparse.Namespace,
    policy: ModelDirectModelCallPolicy,
    findings: tuple[ModelDirectModelCallFinding, ...],
    baseline: list[ModelDirectModelCallBaselineEntry],
    baseline_path: Path | None,
    today: date,
) -> int:
    if baseline_path is None:
        raise _InputError("--write-baseline needs --baseline <file>")
    if baseline_path.is_file():
        remaining = list(findings)
        kept: list[ModelDirectModelCallBaselineEntry] = []
        for entry in baseline:
            match = next((f for f in remaining if f.key() == entry.key()), None)
            if match is not None:
                remaining.remove(match)
                kept.append(entry)
        _write_baseline(baseline_path, kept)
        _out(
            f"Shrank {baseline_path} from {len(baseline)} to {len(kept)} entries; "
            f"{len(remaining)} site(s) are not covered and were NOT added."
        )
        return 1 if remaining else 0
    if not args.expires:
        raise _InputError("bootstrap needs --expires YYYY-MM-DD")
    expires = date.fromisoformat(args.expires)
    if expires < today:
        raise _InputError(f"--expires {expires} is in the past")
    rules: list[tuple[str, str]] = []
    for rule in args.ticket_rule:
        prefix, _, ticket = rule.partition("=")
        rules.append((prefix, ticket))
    entries: list[ModelDirectModelCallBaselineEntry] = []
    unticketed: list[ModelDirectModelCallFinding] = []
    for finding in findings:
        ticket = _ticket_for(finding, policy, rules)
        if ticket is None:
            unticketed.append(finding)
            continue
        entries.append(
            ModelDirectModelCallBaselineEntry(
                path=finding.path,
                kind=finding.kind,
                symbol=finding.symbol,
                target=finding.target,
                ticket=ticket,
                expires=expires,
            )
        )
    if unticketed:
        for finding in unticketed:
            _print_finding(finding)
        _out(
            f"\nRefusing to bootstrap: {len(unticketed)} site(s) have no removal ticket."
        )
        return 1
    _write_baseline(baseline_path, entries)
    _out(
        f"Bootstrapped {baseline_path} with {len(entries)} entries expiring {expires}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except _InputError as exc:
        _out(f"{HOOK_ID}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
