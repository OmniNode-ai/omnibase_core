# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enforcement gate: ban raw GitHub-token env reads in production source.

Fleet-wide port (OMN-13292) of omnimarket's ``check_github_token_env_reads``
(OMN-12856). Flags any ``os.environ["GITHUB_TOKEN"]``,
``os.environ.get("GH_TOKEN")``, ``os.getenv("GH_PAT")``, or any equivalent
access to ``GITHUB_TOKEN`` / ``GH_TOKEN`` / ``GH_PAT`` that appears outside the
test tree.

Rationale (memory ``feedback_secrets_contract_ref_value_in_store``): a GitHub
token is a contract-native secret. The contract declares the secret's reference
*name* (``api_key_ref`` / ``contract_secret_ref``) and the value is resolved at
the effect boundary via the secret resolver — never read directly from the
environment inside handler / adapter / consumer source. A raw env subscript in
production source is always a violation.

Detection (AST, deterministic, no I/O on the analysed code):

1. ``os.environ["GITHUB_TOKEN"]`` — ``ast.Subscript`` on ``os.environ``.
2. ``os.environ.get("GITHUB_TOKEN")`` — ``ast.Call`` on ``os.environ.get``.
3. ``os.getenv("GITHUB_TOKEN")`` — ``ast.Call`` on ``os.getenv``.

Scope: Python files passed on the command line (pre-commit passes staged
files) or, in ``--all`` mode, all ``*.py`` under the repo's source roots. Test
files, ``conftest.py``, and inline-annotated lines are excluded.

Suppression (boundary code that legitimately must read the env, e.g. a runtime
secret-resolver effect): add ``# github-token-env-ok: <reason>`` or
``# ONEX_EXCLUDE`` on the offending line (or any line of a multi-line call).

Exit codes:
    0 — no violations.
    1 — violations found (enforce mode, default).
    2 — usage / internal error.

Usage:
    # pre-commit (staged files)
    python -m omnibase_core.validators.github_token_env_reads file1.py ...

    # full-repo scan (CI)
    python -m omnibase_core.validators.github_token_env_reads --all --repo-root .
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Secret-name literals that are GitHub-token env reads. Any os.environ /
# os.getenv access to these names in production source is a violation — the
# value must come from a contract api_key_ref resolved at the effect boundary.
GITHUB_TOKEN_ENV_NAMES: frozenset[str] = frozenset(
    {"GH_PAT", "GH_TOKEN", "GITHUB_TOKEN"}
)

# Inline skip annotations accepted on the read line or any line of a multi-line call.
SUPPRESSION_TOKENS: tuple[str, ...] = ("# github-token-env-ok:", "# ONEX_EXCLUDE")

# Path segments that exclude a file from the scan (tests / build artifacts).
_EXCLUDED_PATH_SEGMENTS: tuple[str, ...] = (
    "/tests/",
    "conftest.py",
    "/__pycache__/",
    ".pyc",
)

# Default source roots scanned in --all mode (relative to repo root).
_DEFAULT_SRC_ROOTS: tuple[str, ...] = ("src",)


def _is_excluded(rel_path: str) -> bool:
    norm = "/" + rel_path.replace("\\", "/").lstrip("/")
    return any(seg in norm for seg in _EXCLUDED_PATH_SEGMENTS)


def _key_literal(node: ast.expr) -> str:
    """Best-effort string repr of an env-lookup key (only constants count)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _has_suppression(lines: list[str], start: int, end: int) -> bool:
    """True if any line in [start-1, end] (0-based slice) carries a suppression token."""
    for raw in lines[max(0, start - 1) : end]:
        if any(token in raw for token in SUPPRESSION_TOKENS):
            return True
    return False


def scan_source(source: str, display_path: str) -> list[str]:
    """Return violation strings for raw GitHub-token env reads in *source*.

    Pure function over the supplied text — performs no filesystem or network
    I/O on the analysed code.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    violations: list[str] = []

    for node in ast.walk(tree):
        lineno: int | None = None
        end_lineno: int = 0
        detail: str = ""

        # os.environ["GITHUB_TOKEN"] — Subscript
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
        ):
            key = _key_literal(node.slice)
            if key in GITHUB_TOKEN_ENV_NAMES:
                lineno = node.lineno
                end_lineno = getattr(node, "end_lineno", node.lineno) or node.lineno
                detail = f"os.environ[{key!r}]"

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
            if (is_getenv or is_environ_get) and node.args:
                key = _key_literal(node.args[0])
                if key in GITHUB_TOKEN_ENV_NAMES:
                    lineno = node.lineno
                    end_lineno = getattr(node, "end_lineno", node.lineno) or node.lineno
                    call_form = "os.getenv" if is_getenv else "os.environ.get"
                    detail = f"{call_form}({key!r})"

        if lineno is not None and not _has_suppression(lines, lineno, end_lineno):
            line_text = lines[lineno - 1].strip() if lineno <= len(lines) else ""
            violations.append(
                f"{display_path}:{lineno}: raw GitHub-token env read {detail!r} — "
                f"declare a contract api_key_ref and resolve at the effect boundary "
                f"instead. ({line_text!r})"
            )

    return violations


def scan_file(path: Path, display_path: str | None = None) -> list[str]:
    """Read *path* and return its violations. The only filesystem read."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_source(source, display_path or str(path))


def scan_tree(
    repo_root: Path, src_roots: tuple[str, ...] = _DEFAULT_SRC_ROOTS
) -> list[str]:
    """Scan every non-excluded ``*.py`` under *repo_root*'s source roots."""
    all_violations: list[str] = []
    for root_name in src_roots:
        src_root = repo_root / root_name
        if not src_root.exists():
            continue
        for py_file in sorted(src_root.rglob("*.py")):
            rel = str(py_file.relative_to(repo_root)).replace("\\", "/")
            if _is_excluded(rel):
                continue
            all_violations.extend(scan_file(py_file, rel))
    return all_violations


_FIX_HELP = (
    "\nFix: a GitHub token is a contract-native secret. Declare its reference "
    "name in the node/effect contract (api_key_ref) and resolve the value at "
    "the effect boundary via the secret resolver — do not read os.environ / "
    "os.getenv directly in handler/adapter/consumer source.\n"
    "Boundary code that must read the env may suppress with "
    "'# github-token-env-ok: <reason>' on the offending line.\n"
    "(OMN-12856 / OMN-13292; memory feedback_secrets_contract_ref_value_in_store)"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-github-token-env-reads",
        description=(
            "Ban raw GitHub-token (GH_PAT/GH_TOKEN/GITHUB_TOKEN) env reads in "
            "production source (OMN-13292; fleet port of OMN-12856)."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit file paths to scan (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan the full source tree under --repo-root instead of named files.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repo root for --all mode (default: cwd).",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    violations: list[str] = []

    if args.all:
        violations = scan_tree(Path(args.repo_root).resolve())
    else:
        paths = [Path(p) for p in args.files]
        if not paths:
            # No files supplied — pre-commit passes only staged files; nothing to do.
            return 0
        for path in paths:
            rel = path.name
            try:
                rel = str(path.resolve().relative_to(Path.cwd()))
            except ValueError:
                rel = str(path)
            if _is_excluded(rel) or path.suffix != ".py":
                continue
            violations.extend(scan_file(path, rel))

    if violations:
        sys.stderr.write(
            f"[check-github-token-env-reads] FAIL — "
            f"{len(violations)} raw GitHub-token env read(s) found:\n"
        )
        for v in violations:
            sys.stderr.write(f"  {v}\n")
        sys.stderr.write(_FIX_HELP + "\n")
        return 1

    if args.verbose:
        sys.stdout.write("[check-github-token-env-reads] OK — no violations.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
