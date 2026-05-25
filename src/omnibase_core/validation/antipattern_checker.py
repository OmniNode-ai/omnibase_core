# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-commit antipattern checker (OMN-11923).

Loads the resolved antipattern registry, filters to non-semantic rules only
(offline — no network), and validates staged files. Outputs registry version
and SHA-256 hash for reproducibility.

Usage (pre-commit passes staged filenames as positional args)::

    python -m omnibase_core.validation.antipattern_checker file1.py file2.yaml

Exit codes:
    0 — no violations
    1 — violations found
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import re
import sys
from pathlib import Path

from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)
from omnibase_core.validation.antipattern_registry_loader import resolve_antipatterns

_NON_SEMANTIC_TYPES = frozenset(
    {"regex_line", "regex_ast_docstring", "grep_code", "ast_check"}
)


def _registry_hash(registry: ModelAntipatternRegistry) -> str:
    """SHA-256 of the serialised registry for reproducibility."""
    data = registry.model_dump_json(indent=None).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _extract_docstrings(source: str) -> list[tuple[int, str]]:
    """Return (start_lineno, docstring_text) for every docstring in source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                ds_node = node.body[0]
                results.append((ds_node.lineno, node.body[0].value.value))
    return results


def _file_matches_glob(filename: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(filename, g) for g in globs)


def _check_file(
    path: Path,
    entries: list[ModelAntipatternEntry],
) -> list[tuple[int, str, str]]:
    """Return list of (lineno, rule_name, matched_text) violations."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = source.splitlines()
    violations: list[tuple[int, str, str]] = []
    filename = path.name

    # Group entries by type for efficient processing
    docstring_entries = [e for e in entries if e.pattern_type == "regex_ast_docstring"]
    line_entries = [e for e in entries if e.pattern_type in ("regex_line", "grep_code")]

    # --- regex_ast_docstring: run against docstring lines ---
    if docstring_entries:
        applicable_ds_entries = [
            e for e in docstring_entries if _file_matches_glob(filename, e.file_globs)
        ]
        if applicable_ds_entries:
            docstrings = _extract_docstrings(source)
            for ds_lineno, ds_text in docstrings:
                ds_lines = ds_text.splitlines()
                for rel_idx, ds_line in enumerate(ds_lines):
                    abs_lineno = ds_lineno + rel_idx
                    # Check suppression against the actual source line
                    src_line = lines[abs_lineno - 1] if abs_lineno <= len(lines) else ""
                    for entry in applicable_ds_entries:
                        if (
                            entry.suppression_annotation
                            and entry.suppression_annotation in src_line
                        ):
                            continue
                        try:
                            m = re.search(entry.pattern, ds_line)
                        except re.error:
                            continue
                        if m:
                            violations.append((abs_lineno, entry.name, m.group()))

    # --- regex_line / grep_code: run against every source line ---
    if line_entries:
        applicable_line_entries = [
            e for e in line_entries if _file_matches_glob(filename, e.file_globs)
        ]
        for lineno, line in enumerate(lines, start=1):
            for entry in applicable_line_entries:
                if (
                    entry.suppression_annotation
                    and entry.suppression_annotation in line
                ):
                    continue
                try:
                    m = re.search(entry.pattern, line)
                except re.error:
                    continue
                if m:
                    violations.append((lineno, entry.name, m.group()))

    return violations


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-antipatterns",
        description=(
            "Offline antipattern checker (pre-commit). "
            "Loads resolved registry, filters non-semantic rules, validates staged files."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Staged files to check (passed by pre-commit)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(),
        help="Repo root for override resolution (default: cwd)",
    )
    parsed = parser.parse_args(argv)

    repo_root = parsed.repo_root.resolve()
    registry = resolve_antipatterns(repo_root)
    reg_hash = _registry_hash(registry)

    # Filter: non-semantic rules only (offline-safe)
    offline_entries = [
        e for e in registry.entries if e.pattern_type in _NON_SEMANTIC_TYPES
    ]

    print(
        f"[check-antipatterns] registry={registry.version} sha256={reg_hash[:16]}... "
        f"rules={len(offline_entries)}/{len(registry.entries)} (non-semantic)",
        file=sys.stderr,
    )

    all_violations: list[tuple[Path, int, str, str]] = []

    for file_path in parsed.files:
        if not file_path.exists():
            continue
        violations = _check_file(file_path, offline_entries)
        for lineno, rule_name, matched in violations:
            all_violations.append((file_path, lineno, rule_name, matched))

    for file_path, lineno, rule_name, matched in all_violations:
        print(f"{file_path}:{lineno}: [{rule_name}] {matched!r}")

    if all_violations:
        print(
            f"\n{len(all_violations)} antipattern violation(s) found. "
            "Add suppression annotation or fix the violation.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
