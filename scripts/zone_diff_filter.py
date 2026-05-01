# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI zone-diff filter: exit 0 for docs-only diffs, 1 otherwise (OMN-10356).

Usage:
    python scripts/zone_diff_filter.py --check docs-only

Exit codes:
    0  — all changed files are in the DOCS zone (CI matrix may be skipped)
    1  — at least one changed file is outside the DOCS zone (run full matrix)
    2  — bad usage / unknown mode
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _diff_files() -> list[Path]:
    fake = os.environ.get("ZONE_DIFF_FILTER_FAKE_DIFF")
    if fake is not None:
        return [Path(p) for p in fake.split(",") if p.strip()]
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main...HEAD"], text=True
    )
    return [Path(line) for line in out.splitlines() if line]


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--check" or sys.argv[2] != "docs-only":
        sys.stderr.write("usage: zone_diff_filter --check docs-only\n")
        return 2

    # Import after arg parse so the script fails fast on bad usage without
    # requiring omnibase_core to be installed.
    from omnibase_core.enums.enum_file_zone import EnumFileZone
    from omnibase_core.validation.zone_classifier import classify_path

    files = _diff_files()
    if not files:
        return 0

    zones = {classify_path(p) for p in files}
    return 0 if zones <= {EnumFileZone.DOCS} else 1


if __name__ == "__main__":
    sys.exit(main())
