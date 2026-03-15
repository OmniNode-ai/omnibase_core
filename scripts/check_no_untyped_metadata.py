#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-commit hook: fail if metadata fields use dict[str, Any] without ONEX_EXCLUDE.

Usage: python scripts/check_no_untyped_metadata.py [files...]
Exit code 0 = clean. Exit code 1 = violations found.
"""

import re
import sys

PATTERN = re.compile(
    r"metadata\s*:\s*(?:Optional\[)?dict\[str,\s*(?:Any|object)\]",
)
EXCLUDE_COMMENT = "ONEX_EXCLUDE:"


def check_file(path: str) -> list[str]:
    violations = []
    with open(path) as f:
        lines = f.readlines()
    for lineno_idx, line in enumerate(lines):
        if PATTERN.search(line) and EXCLUDE_COMMENT not in line:
            # Also check the next 2 lines for ONEX_EXCLUDE (ruff may wrap
            # long Field(...) calls onto the following line)
            found_exclude = False
            for offset in range(1, 3):
                if lineno_idx + offset < len(lines):
                    if EXCLUDE_COMMENT in lines[lineno_idx + offset]:
                        found_exclude = True
                        break
            if not found_exclude:
                violations.append(
                    f"{path}:{lineno_idx + 1}: untyped metadata dict — use TypedDict or add ONEX_EXCLUDE comment"
                )
    return violations


def main() -> int:
    files = sys.argv[1:]
    all_violations: list[str] = []
    for path in files:
        if path.endswith(".py"):
            all_violations.extend(check_file(path))
    if all_violations:
        for v in all_violations:
            print(v)
        print(
            f"\n{len(all_violations)} violation(s). Replace dict[str, Any] with TypedDict."
        )
        print("If intentional, add: # ONEX_EXCLUDE: dict_str_any - <reason>")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
