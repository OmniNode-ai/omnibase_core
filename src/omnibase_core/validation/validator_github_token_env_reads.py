# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorGithubTokenEnvReads — fleet-wide ban on raw GitHub-token env reads.

Port of omnimarket ``scripts/ci/check_github_token_env_reads.py`` (OMN-12856,
merged 2026-06-09) to a canonical **COMPUTE handler** in ``omnibase_core``.
Exposed as the remote pre-commit hook ``check-github-token-env-reads`` so all
GitHub-touching repos (omniclaude, onex_change_control, omnibase_infra) can
consume it without duplicating the scanner logic.

Tracked under OMN-13310 (fleet extension of OMN-12856).

## What it bans

Any ``os.environ["GH_PAT"]``, ``os.environ.get("GH_PAT")``,
``os.getenv("GH_PAT")``, or any equivalent access to ``GITHUB_TOKEN`` /
``GH_TOKEN`` / ``GH_PAT`` in production Python source outside the test tree.
The canonical replacement is:

    ref = contract_secret_ref(CONTRACT_PATH, "GITHUB_TOKEN")
    secret = resolve_api_key(ref)

(memory ``feedback_secrets_contract_ref_value_in_store``,
memory ``feedback_all_urls_from_contracts``)

## Module organisation

Classes are split per the single-class-per-file rule:
- ``models/validation/model_github_token_violation.py`` — ModelGithubTokenViolation
- ``models/validation/model_github_token_scan_request.py`` — ModelGithubTokenScanRequest
- ``models/validation/model_github_token_scan_result.py`` — ModelGithubTokenScanResult
- ``validators/handler_github_token_env_reads.py`` — HandlerGithubTokenEnvReads (COMPUTE)
- this file — pure scanner functions ``scan_source`` / ``scan_paths`` + CLI

## Scope / exclusions

Files matching any of ``_ALLOWLISTED_PATH_SEGMENTS`` (test paths, conftest,
pycache, etc.) are skipped.  Individual lines can be suppressed with the
annotations ``# omn-allow-env-read`` or ``# ONEX_EXCLUDE``.

## Port-equivalence

Pre-port source hash (OMN-12856 omnimarket script):
  sha256:0a3f715f3b13163c30df63f56081cdd194d8d54679c6205177064c72065130ea

The core scanner reproduces identical verdicts on the shared test corpus
(verified by ``tests/unit/validation/test_validator_github_token_env_reads.py``
shared-corpus tests).
"""

from __future__ import annotations

__all__ = [
    "scan_source",
    "scan_paths",
    "main",
]

import argparse
import ast
import sys
from pathlib import Path

from omnibase_core.models.validation.model_github_token_scan_result import (
    ModelGithubTokenScanResult,
)
from omnibase_core.models.validation.model_github_token_violation import (
    ModelGithubTokenViolation,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Secret-name literals that are GitHub-token env reads.
_GITHUB_TOKEN_ENV_NAMES: frozenset[str] = frozenset(
    {"GH_PAT", "GH_TOKEN", "GITHUB_TOKEN"}
)

#: Inline suppression annotations accepted on the read line or any line of a
#: multi-line call.
_SKIP_ANNOTATIONS: tuple[str, ...] = ("# omn-allow-env-read", "# ONEX_EXCLUDE")

#: Path segments that are always excluded from scanning.
#: Note: use "tests/" (directory) not "/test_" (would match pytest tmpdir names
#: like /private/var/.../test_foo0/). Only match what the origin script matched.
_ALLOWLISTED_PATH_SEGMENTS: tuple[str, ...] = (
    "tests/",
    "conftest.py",
    "__pycache__/",
    ".pyc",
)


# ---------------------------------------------------------------------------
# Pure scanner (no I/O — operates on source text strings)
# ---------------------------------------------------------------------------


def _arg_name(node: ast.expr) -> str:
    """Best-effort string repr of an env-lookup key."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _has_skip(lines: list[str], start: int, end: int) -> bool:
    """True if any line in [start-1 .. end) carries a skip annotation."""
    for ln in lines[max(0, start - 1) : end]:
        if any(ann in ln for ann in _SKIP_ANNOTATIONS):
            return True
    return False


def scan_source(
    source: str,
    file_path: str = "<unknown>",
) -> list[ModelGithubTokenViolation]:
    """Scan Python *source* text and return a list of violations.

    This is the pure, deterministic core of the validator.  No filesystem
    access; all input arrives via the ``source`` string.  Identical to the
    scanner in omnimarket ``scripts/ci/check_github_token_env_reads.py``
    (port-equivalence hash above).

    Args:
        source: UTF-8 Python source text to scan.
        file_path: Label to use in violation ``file_path`` fields.

    Returns:
        List of ``ModelGithubTokenViolation`` objects (empty when clean).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    violations: list[ModelGithubTokenViolation] = []

    for node in ast.walk(tree):
        lineno: int | None = None
        end_lineno: int = 0
        detail: str = ""

        # Pattern 1: os.environ["GH_PAT"] — Subscript form
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
        ):
            key = _arg_name(node.slice)
            if key in _GITHUB_TOKEN_ENV_NAMES:
                lineno = node.lineno
                end_lineno = getattr(node, "end_lineno", node.lineno)
                detail = f"os.environ[{key!r}]"

        # Pattern 2: os.getenv(...) and os.environ.get(...) — Call forms
        elif isinstance(node, ast.Call):
            func = node.func
            is_getenv = (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            )
            is_environ_get = (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "os"
            )
            key_node: ast.expr | None = None
            if node.args:
                key_node = node.args[0]
            else:
                for keyword in node.keywords:
                    if keyword.arg == "key":
                        key_node = keyword.value
                        break
            if (is_getenv or is_environ_get) and key_node is not None:
                key = _arg_name(key_node)
                if key in _GITHUB_TOKEN_ENV_NAMES:
                    lineno = node.lineno
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    call_form = "os.getenv" if is_getenv else "os.environ.get"
                    detail = f"{call_form}({key!r})"

        if lineno is not None and not _has_skip(lines, lineno, end_lineno):
            line_text = lines[lineno - 1].strip() if lineno <= len(lines) else ""
            violations.append(
                ModelGithubTokenViolation(
                    file_path=file_path,
                    line_number=lineno,
                    detail=detail,
                    line_text=line_text,
                )
            )

    return violations


def _is_allowlisted(path_str: str) -> bool:
    """Return True if *path_str* should be excluded from scanning."""
    return any(seg in path_str for seg in _ALLOWLISTED_PATH_SEGMENTS)


def scan_paths(paths: list[Path]) -> ModelGithubTokenScanResult:
    """Read *paths* from disk, scan each, and aggregate results.

    This is the EFFECT boundary: the only place in this module that performs
    filesystem I/O.  Call from CLI and pre-commit hooks; do NOT call from the
    COMPUTE handler (which receives pre-read source via the envelope payload).

    Args:
        paths: Absolute or relative Path objects to scan.

    Returns:
        Aggregated ``ModelGithubTokenScanResult``.
    """
    all_violations: list[ModelGithubTokenViolation] = []
    files_scanned = 0
    files_skipped = 0

    for path in sorted(paths):
        rel = str(path).replace("\\", "/")
        if _is_allowlisted(rel):
            files_skipped += 1
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            files_skipped += 1
            continue
        files_scanned += 1
        all_violations.extend(scan_source(source, file_path=str(path)))

    return ModelGithubTokenScanResult(
        violations=tuple(all_violations),
        files_scanned=files_scanned,
        files_skipped=files_skipped,
    )


# ---------------------------------------------------------------------------
# CLI / pre-commit entry point
# ---------------------------------------------------------------------------


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
            "Bans os.environ[GH_PAT/GH_TOKEN/GITHUB_TOKEN] and equivalents."  # env-var-ok: CLI help text names the banned patterns
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
        print(  # T201 — CLI output for pre-commit gate
            f"[github-token-env-gate] [{mode}] "
            f"{len(scan_result.violations)} raw GitHub-token env read(s) found:"
        )
        for v in scan_result.violations:
            print(  # T201 — CLI output for pre-commit gate
                f"  {v.file_path}:{v.line_number}: "
                f"raw GitHub-token env read {v.detail!r} — "
                f"use contract_secret_ref + resolve_api_key instead. "
                f"({v.line_text!r})"
            )
        if not args.report:
            print(  # T201 — CLI output for pre-commit gate
                "\nFix: replace os.environ/os.getenv with:\n"
                "    ref = contract_secret_ref(CONTRACT_PATH, 'GITHUB_TOKEN')\n"  # env-var-ok: fix guidance text
                "    secret = resolve_api_key(ref)\n"
                "Use the repo-local contract_secret_ref and resolve_api_key APIs; "
                "see OMN-13310 / OMN-12856 for the contract-secret pattern.\n"
                "(OMN-13310 / OMN-12856)"
            )
            return 1
    elif args.verbose:
        print(  # T201 — CLI output for pre-commit gate
            f"[github-token-env-gate] OK — "
            f"scanned {scan_result.files_scanned} file(s), "
            f"skipped {scan_result.files_skipped}, "
            f"no violations."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
