# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime of the check-github-token-env-reads hook (OMN-13310, OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_github_token_env_reads_check_compute.runtime_github_token_env_reads_check \\
        [--report] [--verbose] file.py ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.validation.validator_github_token_env_reads import scan_paths

__all__ = ["main"]


def _emit(text: str) -> None:
    """Write one line of CLI output to stdout."""
    sys.stdout.write(f"{text}\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for pre-commit and standalone invocation.

    When invoked by pre-commit (``pass_filenames: true``) the filenames are
    passed as positional arguments.  Reads file bytes at the boundary, then
    delegates to the pure scanner.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 — no violations (or ``--report`` mode).
        1 — violations found (enforce mode, default).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Enforce: no raw GitHub-token env reads in source (OMN-13310). "
            "Bans os.environ[GH_PAT/GH_TOKEN/GITHUB_TOKEN] and equivalents."
        )
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to scan (passed by pre-commit)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Report violations but always exit 0 (warn-only / shadow mode).",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    if not args.files:
        # No files passed — nothing to scan (pre-commit passes an empty list
        # when no relevant files are staged; treat as clean).
        return 0

    scan_result = scan_paths(args.files)

    if scan_result.violations:
        mode = "WARN" if args.report else "FAIL"
        _emit(
            f"[github-token-env-gate] [{mode}] "
            f"{len(scan_result.violations)} raw GitHub-token env read(s) found:"
        )
        for v in scan_result.violations:
            _emit(
                f"  {v.file_path}:{v.line_number}: "
                f"raw GitHub-token env read {v.detail!r} — "
                f"use contract_secret_ref + resolve_api_key instead. "
                f"({v.line_text!r})"
            )
        if not args.report:
            _emit(
                "\nFix: replace os.environ/os.getenv with:\n"
                "    ref = contract_secret_ref(CONTRACT_PATH, 'GITHUB_TOKEN')\n"
                "    secret = resolve_api_key(ref)\n"
                "Use the repo-local contract_secret_ref and resolve_api_key APIs; "
                "see OMN-13310 / OMN-12856 for the contract-secret pattern.\n"
                "(OMN-13310 / OMN-12856)"
            )
            return 1
    elif args.verbose:
        _emit(
            f"[github-token-env-gate] OK — "
            f"scanned {scan_result.files_scanned} file(s), "
            f"skipped {scan_result.files_skipped}, "
            f"no violations."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
