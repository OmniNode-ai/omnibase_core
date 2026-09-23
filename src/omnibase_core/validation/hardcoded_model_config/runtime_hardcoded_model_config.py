# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EFFECT boundary for check-hardcoded-model-config-compute (OMN-19252).

Owns every piece of I/O the pure handler must not do: reading the packaged
policy, the files to scan, the committed baseline and (with ``--base``) the
baseline as it stood at a git ref. The verdict is computed by the handler.

Modes:

* ``paths...`` (pre-commit passes the staged files): scan those files.
* ``--all``: scan every tracked file (``git ls-files``).

Ratchet contract, with ``--baseline <file>``:

* a finding that the baseline does not cover fails the run;
* a baseline entry that no longer matches a scanned (or deleted) file fails the
  run and is named, so the baseline shrinks as the values are removed;
* a retired lab value (family R) can never be baselined, on write or on read;
* ``--base <ref>`` also fails when the baseline carries an entry that the same
  file at ``<ref>`` did not: entries only leave.

There is no suppression marker, no skip flag and no advisory mode.

Exit codes: 0 clean, 1 findings / stale entries / growth / unreadable input.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.hardcoded_model_config.handler import (
    HandlerHardcodedModelConfigCompute,
    added_entries,
    compare_with_baseline,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigBaseline,
    ModelHardcodedModelConfigBaselineEntry,
    ModelHardcodedModelConfigFinding,
    ModelHardcodedModelConfigPolicy,
    ModelHardcodedModelConfigScanInput,
)

__all__ = [
    "build_parser",
    "load_policy",
    "main",
    "read_baseline_at_ref",
]

_POLICY_RESOURCE: Final[str] = "policy.yaml"
_SCANNED_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".pyi",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".sh",
        ".bash",
        ".cfg",
        ".ini",
        ".conf",
        ".service",
        ".env",
        ".tsv",
        ".txt",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".md",
        ".mdx",
        ".rst",
    }
)
_SCANNED_NAMES: Final[frozenset[str]] = frozenset({"Dockerfile", "Containerfile"})
_BASELINE_HEADER: Final[str] = """\
# Baseline for check-hardcoded-model-config-compute (OMN-19252).
# Plan: knowledge-base-internal beta/plans/2026-09-23-remove-hardcoded-model-config.md
# (task A1 and the per-repository ratchet of tasks A3.x).
#
# RULE: entries only leave. A finding not listed here fails. An entry that no
# longer matches its file fails until it is removed. CI refuses a pull request
# whose copy of this file carries an entry its base branch did not. Retired lab
# values (family R) are never admitted. Entries are keyed by line content
# (sha1 of the stripped line), not by line number.
#
# Regenerate only to SHRINK it:
#   python -m omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config \\
#     --all --baseline <this file> --write-baseline
"""


class _InputError(Exception):
    """An input the gate cannot read. The gate fails closed on it."""


def load_policy() -> ModelHardcodedModelConfigPolicy:
    """Read the policy shipped inside this package."""
    package = __package__ or "omnibase_core.validation.hardcoded_model_config"
    raw = resources.files(package).joinpath(_POLICY_RESOURCE).read_text("utf-8")
    try:
        policy = load_yaml_content_as_model(raw, ModelHardcodedModelConfigPolicy)
    except ModelOnexError as exc:
        raise _InputError(f"policy.yaml is invalid: {exc}") from exc
    last = policy.path_classes[-1] if policy.path_classes else None
    if last is None or last.name != "SOURCE" or last.globs != ("**",):
        raise _InputError("policy.yaml must end with a SOURCE class globbing '**'")
    return policy


def _is_scanned(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name in _SCANNED_NAMES or name.startswith(".env"):
        return True
    dot = name.rfind(".")
    return dot > 0 and name[dot:].lower() in _SCANNED_SUFFIXES


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise _InputError(f"git ls-files failed: {result.stderr.strip()}")
    return [p for p in result.stdout.split("\0") if p]


def _parse_baseline(
    raw: str, source: str
) -> list[ModelHardcodedModelConfigBaselineEntry]:
    try:
        document = load_yaml_content_as_model(raw, ModelHardcodedModelConfigBaseline)
    except ModelOnexError as exc:
        raise _InputError(f"{source}: not a valid baseline: {exc}") from exc
    entries = list(document.entries)
    retired = [e for e in entries if e.family == "R"]
    if retired:
        names = ", ".join(f"{e.path}@{e.content_sha1}" for e in retired)
        raise _InputError(
            f"{source}: retired lab values (family R) can never be baselined; "
            f"delete the value instead of listing it: {names}"
        )
    return entries


def read_baseline_at_ref(ref: str, path: str) -> str | None:
    """Return the baseline text at ``ref``, or None when the file is absent there.

    An unresolvable ref is an error, never an absent file.
    """
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        raise _InputError(f"--base {ref!r} does not resolve to a commit")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if exists.returncode != 0:
        return None
    show = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=False
    )
    if show.returncode != 0:
        raise _InputError(f"git show {ref}:{path} failed: {show.stderr.strip()}")
    return show.stdout


def _write_baseline(
    path: Path, entries: list[ModelHardcodedModelConfigBaselineEntry]
) -> None:
    """Write the baseline in the shape yamlfmt leaves unchanged: document start
    first, then the header, then one block mapping per entry."""
    lines = ["---", _BASELINE_HEADER, "schema_version: 1"]
    ordered = sorted(entries, key=lambda e: e.key())
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


def _print_finding(finding: ModelHardcodedModelConfigFinding) -> None:
    print(
        f"{finding.path}:{finding.line}: [{finding.family} in {finding.path_class}] "
        f"{finding.matched_text!r}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check-hardcoded-model-config-compute",
        description=(
            "Refuse new hardcoded lab model configuration: model ids, inference "
            "endpoints, private and lab-subnet hosts, retired lab values and "
            "loaded example files (OMN-19252)."
        ),
    )
    parser.add_argument("paths", nargs="*", help="Files to scan (pre-commit mode)")
    parser.add_argument(
        "--all", action="store_true", help="Scan every tracked file (git ls-files)"
    )
    parser.add_argument(
        "--baseline", help="Committed baseline of tolerated pre-existing findings"
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write the baseline from this scan instead of checking against it",
    )
    parser.add_argument(
        "--base",
        help="Git ref whose baseline this one may only shrink from",
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    policy = load_policy()
    handler = HandlerHardcodedModelConfigCompute(policy)

    candidates = _tracked_files() if args.all else list(args.paths)
    files = sorted({p.replace("\\", "/").removeprefix("./") for p in candidates})
    files = [p for p in files if _is_scanned(p) and Path(p).is_file()]

    findings: list[ModelHardcodedModelConfigFinding] = []
    for rel in files:
        try:
            text = Path(rel).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise _InputError(f"{rel}: unreadable: {exc}") from exc
        result = handler.handle(
            ModelHardcodedModelConfigScanInput(path=rel, content=text)
        )
        findings.extend(result.findings)

    if args.write_baseline:
        if not args.baseline:
            raise _InputError("--write-baseline needs --baseline <file>")
        retired = [f for f in findings if f.family == "R"]
        if retired:
            for finding in retired:
                _print_finding(finding)
            print(
                f"\nRefusing to write a baseline: {len(retired)} retired lab value(s) "
                "(family R) can never be baselined. Delete them first."
            )
            return 1
        entries = [
            ModelHardcodedModelConfigBaselineEntry(
                path=f.path, family=f.family, content_sha1=f.content_sha1
            )
            for f in findings
        ]
        _write_baseline(Path(args.baseline), entries)
        print(f"Wrote {len(entries)} baseline entries to {args.baseline}.")
        return 0

    baseline: list[ModelHardcodedModelConfigBaselineEntry] = []
    if args.baseline:
        baseline_path = Path(args.baseline)
        if not baseline_path.is_file():
            raise _InputError(f"baseline {args.baseline} does not exist")
        baseline = _parse_baseline(
            baseline_path.read_text(encoding="utf-8"), args.baseline
        )

    missing = frozenset(e.path for e in baseline if not Path(e.path).is_file())
    new, stale = compare_with_baseline(findings, baseline, frozenset(files), missing)

    grown: list[ModelHardcodedModelConfigBaselineEntry] = []
    if args.base:
        if not args.baseline:
            raise _InputError("--base needs --baseline <file>")
        base_raw = read_baseline_at_ref(args.base, args.baseline)
        if base_raw is None:
            print(
                f"NOTE: {args.baseline} does not exist at {args.base}; this change "
                "introduces it, so there is no earlier baseline to shrink from."
            )
        else:
            base_entries = _parse_baseline(base_raw, f"{args.base}:{args.baseline}")
            grown = added_entries(base_entries, baseline)

    for finding in new:
        _print_finding(finding)
    for entry in stale:
        print(
            f"{entry.path}: stale baseline entry family={entry.family} "
            f"content_sha1={entry.content_sha1} (no longer matches; remove it)"
        )
    for entry in grown:
        print(
            f"{entry.path}: baseline entry added against {args.base} "
            f"family={entry.family} content_sha1={entry.content_sha1} "
            "(entries only leave)"
        )

    if new or stale or grown:
        print(
            f"\n{len(new)} new finding(s), {len(stale)} stale baseline entr(y/ies), "
            f"{len(grown)} added baseline entr(y/ies). Lab hosts, lab ports, lab "
            "model backends and model ids belong in a config-store overlay, not in "
            "the repository. There is no suppression marker: an exception is a "
            "change to omnibase_core's hardcoded_model_config/policy.yaml."
        )
        return 1
    print(
        f"hardcoded-model-config: {len(files)} file(s) scanned, "
        f"{len(findings)} finding(s), all covered by {len(baseline)} baseline entries."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except _InputError as exc:
        print(f"check-hardcoded-model-config-compute: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
