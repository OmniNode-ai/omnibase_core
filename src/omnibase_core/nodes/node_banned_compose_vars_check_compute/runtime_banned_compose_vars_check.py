# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Banned compose vars check CLI runtime.

Does the file and directory I/O and runs the pure checker in
``omnibase_core.validation.validator_banned_compose_vars``.
Keeps the pre-node command-line flags, output and exit codes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.validator_banned_compose_vars import (
    BANNED_CONSTANT_NAME,
    ValidatorBannedComposeVars,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Exit codes:
        0 — no drift
        2 — drift detected or empty banned set (misconfigured)
    """
    parser = argparse.ArgumentParser(
        prog="check-banned-compose-vars",
        description=(
            "Detect compose / k8s env vars whose name is in the kernel's "
            "_DEPRECATED_TOPIC_ENV_VARS banned set. Exits 2 on any violation "
            "or if the banned set is empty."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to scan (default: current directory)",
    )
    parser.add_argument(
        "--kernel-source",
        type=Path,
        required=True,
        help=(
            "Path to service_kernel.py whose _DEPRECATED_TOPIC_ENV_VARS "
            "tuple is the canonical banned set."
        ),
    )
    parser.add_argument(
        "--extra-banned",
        action="append",
        default=[],
        metavar="VAR_NAME",
        help="Additional env var name to treat as banned (repeatable).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress the summary footer",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorBannedComposeVars(
        kernel_source_path=parsed.kernel_source,
        extra_banned=frozenset(parsed.extra_banned),
    )

    banned = validator.banned_env_vars()
    if not banned:
        sys.stderr.write(
            f"ERROR: banned set is empty. Check --kernel-source "
            f"({parsed.kernel_source}) contains {BANNED_CONSTANT_NAME}.\n"
        )
        return 2

    violations = validator.check_paths(parsed.paths)

    for v in violations:
        sys.stdout.write(
            f"{v.compose_path}: [{v.kind.value}] {v.var_name}: {v.message}\n"
        )

    if not parsed.quiet:
        if violations:
            sys.stderr.write(
                f"\n{len(violations)} banned compose env var violation(s) "
                f"(banned set size: {len(banned)}).\n"
            )
        else:
            sys.stderr.write(
                f"No banned compose env vars found (banned set size: {len(banned)}).\n"
            )

    return 2 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
