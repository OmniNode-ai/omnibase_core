#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Release-identity gate: no importable-surface change merges onto a published
version without a bump (OMN-13411).

omnibase_core is a published PyPI package that downstream repos (omnibase_infra,
omnimarket, ...) pin and ``uv sync`` against. If packaged source under ``src/``
changes but ``pyproject.toml``'s ``project.version`` is NOT bumped past the most
recently *published* version (the latest ``vX.Y.Z`` git tag), then two distinct
code states ship under the SAME version string.

This is the literal meta-root-cause behind OMN-13402 (A3) / OMN-13405 (A6): core
dev HEAD carried unreleased modules (e.g. ``enum_correction_failure_axis``,
OMN-13234) while still labelled 0.45.0 — the same version as the published wheel
that LACKS them. A workspace build installed the released enum-LESS wheel and
crash-looped on the missing import, because the version string could not
distinguish the two code states. The sibling repo omnibase_infra closed the same
gap with its own ``check_release_identity.py`` (OMN-13412); this is the
omnibase_core port that this ticket (OMN-13411) requires.

What it enforces
----------------
When the diff under inspection touches packaged source (``src/**``) AND any
published tag exists, ``pyproject.toml``'s ``project.version`` MUST be strictly
greater than the highest published version (latest ``v*`` / bare-semver tag).

A docs-only / tests-only / CI-only diff (no ``src/**`` change) is exempt: the
published wheel is unaffected, so no bump is required.

Modes
-----
* ``--base <ref>``    Compare the working tree against ``<ref>`` (e.g. ``origin/dev``)
                      to decide whether packaged source changed. CI passes the PR
                      base. If omitted, the gate assumes source MAY have changed
                      and always enforces the version-ahead invariant.
* ``--changed-file``  Explicit changed-file list (repeatable / newline list on
                      stdin via ``-``). Overrides ``--base`` diffing.

Usage::

    uv run python scripts/check_release_identity.py --base origin/dev
    uv run python scripts/check_release_identity.py   # strict: always require ahead

Exit codes:
    0 — version is correctly ahead of the latest published tag (or exempt diff)
    1 — packaged source changed without bumping past the latest published version
    2 — configuration error (no pyproject version, malformed version/tag)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.version import InvalidVersion, Version

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
# Packaged-source prefixes whose change requires a version bump.
_PACKAGED_PREFIXES = ("src/",)


def _read_pyproject_version() -> Version:
    with _PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("project", {}).get("version")
    if not raw:
        raise ValueError(f"no project.version in {_PYPROJECT}")
    try:
        return Version(str(raw))
    except InvalidVersion as exc:
        raise ValueError(f"malformed project.version {raw!r}: {exc}") from exc


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def _latest_published_version() -> Version | None:
    """Return the highest published semver tag, or None if there are no tags."""
    out = _git(["tag", "--list"])
    if not out:
        return None
    best: Version | None = None
    for line in out.splitlines():
        tag = line.strip()
        candidate = tag[1:] if tag.startswith("v") else tag
        try:
            ver = Version(candidate)
        except InvalidVersion:
            continue
        if best is None or ver > best:
            best = ver
    return best


def _packaged_source_changed(base: str | None, explicit: list[str]) -> bool:
    """Decide whether packaged source changed relative to base / explicit list."""
    if explicit:
        files = explicit
    elif base:
        diff = _git(["diff", "--name-only", f"{base}...HEAD"])
        files = [f for f in diff.splitlines() if f.strip()]
        if not files:
            # Fall back to a two-dot diff if the merge-base form yielded nothing.
            diff = _git(["diff", "--name-only", base])
            files = [f for f in diff.splitlines() if f.strip()]
    else:
        # No base and no explicit list: cannot prove the diff is exempt — enforce.
        return True
    return any(f.startswith(prefix) for f in files for prefix in _PACKAGED_PREFIXES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=None,
        help="Git ref to diff against (e.g. origin/dev) to detect src/ changes.",
    )
    parser.add_argument(
        "--changed-file",
        dest="changed_files",
        action="append",
        default=[],
        help="Explicit changed file (repeatable). Overrides --base diffing.",
    )
    args = parser.parse_args(argv)

    explicit = list(args.changed_files)
    if explicit == ["-"]:
        explicit = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]

    try:
        pyproject_version = _read_pyproject_version()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    latest = _latest_published_version()
    if latest is None:
        print("OK: no published tag yet — release-identity bump not required.")
        return 0

    changed = _packaged_source_changed(args.base, explicit)
    if not changed:
        print(
            "OK: no packaged src/** change in this diff — version bump not required "
            f"(pyproject {pyproject_version}, latest published {latest})."
        )
        return 0

    if pyproject_version > latest:
        print(f"OK: version {pyproject_version} is ahead of latest published {latest}.")
        return 0

    print(
        "FAIL: packaged source changed but pyproject version "
        f"{pyproject_version} is NOT ahead of the latest published version "
        f"{latest} (OMN-13411 release-identity gate).",
        file=sys.stderr,
    )
    print(
        "Merging code consumers import onto an already-published version aliases "
        "two code states under one wheel version. Bump project.version in "
        f"pyproject.toml past {latest} (e.g. "
        f"{Version(f'{latest.major}.{latest.minor}.{latest.micro + 1}')}).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
