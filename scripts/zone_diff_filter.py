# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI zone-diff filter: exit 0 for docs-only diffs, 1 otherwise (OMN-10356).

Usage:
    python scripts/zone_diff_filter.py --check docs-only

Exit codes:
    0  — all changed files are in the DOCS zone (CI matrix may be skipped)
    1  — at least one changed file is outside the DOCS zone (run full matrix)
    2  — bad usage / unknown mode
    3  — internal error (classifier unimportable, git diff failed, ...).
         Callers MUST treat 3 as "no verdict" and run the full matrix. It is
         deliberately distinct from 1: an uncaught exception exits 1, which a
         caller reads as the confident verdict "production/mixed diff". That
         conflation silently disabled the omnibase_core docs-only
         short-circuit for every PR (OMN-16619) — the classifier crashed on
         import and CI reported a normal non-docs verdict, so the failure was
         invisible in the step summary.
"""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from pathlib import Path


def _diff_files() -> list[Path]:
    fake = os.environ.get("ZONE_DIFF_FILTER_FAKE_DIFF")
    if fake is not None:
        return [Path(p) for p in fake.split(",") if p.strip()]
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main...HEAD"], text=True
    )
    return [Path(line) for line in out.splitlines() if line]


def _classify(files: list[Path]) -> int:
    # Imported here so the script fails fast on bad usage before requiring the
    # classifier. NOTE: this import path goes through omnibase_core/__init__.py
    # unless the caller stages the two pure-stdlib modules into a package tree
    # with empty __init__.py files. The real package init calls
    # importlib.metadata.version("omnibase-core"), which raises on a CI runner
    # that has not installed the distribution. Both the reusable
    # .github/workflows/zone-filter.yml and omnibase_core's own inline
    # zone-filter job stage the modules for exactly that reason (OMN-16619).
    from omnibase_core.enums.enum_file_zone import EnumFileZone
    from omnibase_core.validation.zone_classifier import classify_path

    zones = {classify_path(p) for p in files}
    return 0 if zones <= {EnumFileZone.DOCS} else 1


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--check" or sys.argv[2] != "docs-only":
        sys.stderr.write("usage: zone_diff_filter --check docs-only\n")
        return 2

    try:
        files = _diff_files()
        if not files:
            return 0
        return _classify(files)
    except Exception:  # noqa: BLE001  # boundary-ok: any classifier failure must fail closed as 'no verdict', never as verdict 1
        # Not a swallow: the full traceback is surfaced on stderr and the
        # distinct exit code 3 forces the caller onto the full matrix. The
        # alternative — letting the exception propagate — exits 1 and is
        # indistinguishable from a real "not docs-only" verdict.
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
