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
        for lineno, line in enumerate(f, 1):
            if PATTERN.search(line) and EXCLUDE_COMMENT not in line:
                violations.append(
                    f"{path}:{lineno}: untyped metadata dict — use TypedDict or add ONEX_EXCLUDE comment"
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
