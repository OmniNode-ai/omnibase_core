# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Import every entry point of one installed distribution and write what failed (OMN-26670).

Run by the consumer's own interpreter, by path (`python -P <this file>`): it is
stdlib-only so that a broken candidate shows up as a named failure per entry
point and never as a crash of the harness. Each failure carries the failing
import statement, the name that is missing, and the files of the traceback.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
import traceback
from pathlib import Path

__all__ = ["main", "probe"]

_LOAD_ERRORS = (
    ImportError,
    AttributeError,
    SyntaxError,
    TypeError,
    ValueError,
    RuntimeError,
    OSError,
    LookupError,
    NameError,
    AssertionError,
)
_IMPORT_LINE = re.compile(r"^\s*(from\s+\S+\s+import\s|import\s)")
_CANNOT_IMPORT = re.compile(
    r"cannot import name '(?P<name>[^']+)' from '(?P<mod>[^']+)'"
)


def _missing_name(error: BaseException) -> str:
    match = _CANNOT_IMPORT.search(str(error))
    if match:
        return f"{match['mod']}.{match['name']}"
    if isinstance(error, ModuleNotFoundError) and error.name:
        return error.name
    attr = getattr(error, "name", None)
    if isinstance(error, AttributeError) and attr:
        owner = re.search(r"module '([^']+)'", str(error))
        return f"{owner[1]}.{attr}" if owner else str(attr)
    return f"{type(error).__name__}: {str(error)[:200]}"


def _shown(path: str) -> str:
    absolute = Path(path).resolve()
    cwd = Path.cwd()
    return (
        str(absolute.relative_to(cwd))
        if absolute.is_relative_to(cwd)
        else str(absolute)
    )


def _import_statement(error: BaseException, fallback: str) -> tuple[str, list[str]]:
    frames = [
        f
        for f in traceback.extract_tb(error.__traceback__)
        if not f.filename.startswith("<")
    ]
    chosen = next(
        (f for f in reversed(frames) if f.line and _IMPORT_LINE.match(f.line)),
        frames[-1] if frames else None,
    )
    files = [f.filename for f in frames]
    if chosen is None:
        return fallback, files
    return (
        f"{(chosen.line or fallback).strip()} ({_shown(chosen.filename)}:{chosen.lineno})",
        files,
    )


def probe(
    distribution: str, groups: tuple[str, ...], skip_groups: tuple[str, ...] = ()
) -> dict[str, object]:
    """Load every entry point of the distribution and describe each failure.

    A group in skip_groups holds metadata (help text), not importable references, so it is not loaded.
    """
    entry_points = [
        ep
        for ep in importlib.metadata.distribution(distribution).entry_points
        if (not groups or ep.group in groups) and ep.group not in skip_groups
    ]
    failures: list[dict[str, object]] = []
    imported = 0
    for ep in entry_points:
        try:
            ep.load()
        except _LOAD_ERRORS as error:
            statement, files = _import_statement(error, f"entry point {ep.value}")
            failures.append(
                {
                    "group": ep.group,
                    "name": ep.name,
                    "value": ep.value,
                    "error_type": type(error).__name__,
                    "message": str(error)[:500],
                    "missing_name": _missing_name(error),
                    "import_statement": statement,
                    "frame_files": files,
                }
            )
        else:
            imported += 1
    return {
        "distribution": distribution,
        "entry_points": len(entry_points),
        "imported": imported,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    """Write the probe result as JSON to --out; exit 0 whenever the probe itself ran."""
    parser = argparse.ArgumentParser(
        description="Import every entry point of one distribution."
    )
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--skip-group", action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = probe(args.distribution, tuple(args.group), tuple(args.skip_group))
    args.out.write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
