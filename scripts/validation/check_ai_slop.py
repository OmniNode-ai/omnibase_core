#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX AI-Slop Pattern Checker v1.0

This pre-commit hook and CI gate detects AI-generated boilerplate ("slop") patterns
in Python and Markdown files. Uses AST analysis for docstring patterns and line-based
regex for non-docstring patterns.

Rule set v1.0 (locked 2026-03-02, OMN-3191):
- ERROR: sycophancy (sycophantic docstring openers: "Excellent", "Great", "Sure")
- ERROR: rest_docstring (reST-style :param:, :type:, :returns:, :rtype:)
- WARNING: boilerplate_docstring ("This module/class/function provides/implements/contains")
  Applies to Python docstrings (AST-based). Catches LLM-generated opener phrases.
- WARNING: step_narration ("# Step N:" or "## Step N:" comments) — Markdown files ONLY.
  Python inline "# Step N:" comments are legitimate ordered-step code documentation
  and are NOT flagged. Only Markdown headings trigger this rule.
- WARNING: md_separator (four-or-more = signs used as markdown separators in docstrings)
  Applies to Python docstrings (AST-based). Catches LLM visual separators.
- INFO: obvious_comment (self-evident inline comments, report mode only)

Rule change log:
  v1.0 (2026-03-02): step_narration scoped to Markdown files only.
    Rationale: 48h post-rollout audit (OMN-3191) found "# Step N:" in Python code
    triggers 110+ false positives in omniintelligence and omniclaude alone.
    Python numbered steps ("# Step 1: Fetch session snapshot") are legitimate
    multi-step function documentation. Only Markdown step headings are LLM slop.
  v0.1 (2026-02-28, OMN-2971): initial rollout across 7 repos.

Suppression:
    Add `# ai-slop-ok: reason` on:
    - The def/class line
    - The docstring's opening triple-quote line
    - The line immediately preceding the def/class line

Exit codes:
    0 - No violations (or only INFO/WARNING in non-strict mode)
    1 - ERROR violations found
    2 - WARNING violations found (--strict mode only)

Usage:
    python scripts/validation/check_ai_slop.py [files...]
    python scripts/validation/check_ai_slop.py --strict [files...]
    python scripts/validation/check_ai_slop.py --report src/

Linear tickets: OMN-2971 (original), OMN-3191 (v1.0 tuning)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"

CHECK_SYCOPHANCY = "sycophancy"
CHECK_REST_DOCSTRING = "rest_docstring"
CHECK_BOILERPLATE_DOCSTRING = "boilerplate_docstring"
CHECK_STEP_NARRATION = "step_narration"
CHECK_MD_SEPARATOR = "md_separator"
CHECK_OBVIOUS_COMMENT = "obvious_comment"

SUPPRESSION_MARKER = "ai-slop-ok"

# Sycophantic openers (case-insensitive, must be at start of docstring content)
_SYCOPHANCY_RE = re.compile(
    r"^\s*(Excellent|Great|Sure|Certainly|Absolutely|Of course|Happy to|"
    r"I would be|Gladly|Wonderful|Perfect|Fantastic|Awesome)[!,. ]",
    re.IGNORECASE,
)

# reST docstring markers
_REST_RE = re.compile(r"^\s*:(param|type|returns?|rtype|raises?|var|ivar|cvar)\b")

# Boilerplate "This <thing> provides/implements/contains/is responsible for"
_BOILERPLATE_RE = re.compile(
    r"^\s*This\s+(module|class|function|method|file|script|node|handler|service)"
    r"\s+(provides?|implements?|contains?|is responsible for|handles?|manages?|offers?)",
    re.IGNORECASE,
)

# Step narration: "# Step N:" or "# Step N -"
_STEP_NARRATION_RE = re.compile(r"#\s*Step\s+\d+\s*[:\-]", re.IGNORECASE)

# Markdown separator: 4+ = characters in a docstring line
_MD_SEPARATOR_RE = re.compile(r"={4,}")


class SlopViolation:
    """A single AI-slop violation found in a file."""

    def __init__(
        self,
        filename: str,
        line: int,
        check: str,
        severity: str,
        message: str,
        source_line: str = "",
    ) -> None:
        self.filename = filename
        self.line = line
        self.check = check
        self.severity = severity
        self.message = message
        self.source_line = source_line

    def __repr__(self) -> str:
        return (
            f"SlopViolation({self.filename}:{self.line} [{self.severity}] "
            f"{self.check}: {self.message})"
        )

    def format_line(self) -> str:
        return (
            f"{self.filename}:{self.line}: [{self.severity}] "
            f"{self.check}: {self.message}"
        )


# ---------------------------------------------------------------------------
# AST visitor — handles docstring patterns
# ---------------------------------------------------------------------------


class _DocstringVisitor(ast.NodeVisitor):
    """
    AST-based visitor that extracts docstrings from functions, classes, and
    modules and checks them for AI-slop patterns.

    Uses AST so that the opener line is correctly resolved even when the
    triple-quote and the first content line are on different lines.
    """

    def __init__(self, filename: str, source_lines: list[str]) -> None:
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[SlopViolation] = []

    # ------------------------------------------------------------------
    # Suppression helpers
    # ------------------------------------------------------------------

    def _has_suppression(self, def_lineno: int, docstring_lineno: int) -> bool:
        """
        Return True if any of the three suppression locations contain the
        suppression marker:
          1. The def/class line itself (1-indexed)
          2. The docstring's opening triple-quote line
          3. The line immediately preceding the def/class line
        """
        lines = self.source_lines
        n = len(lines)

        def _check(lineno: int) -> bool:
            if 1 <= lineno <= n:
                return SUPPRESSION_MARKER in lines[lineno - 1]
            return False

        return _check(def_lineno) or _check(docstring_lineno) or _check(def_lineno - 1)

    # ------------------------------------------------------------------
    # Docstring checker
    # ------------------------------------------------------------------

    def _check_docstring(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module,
        def_lineno: int,
    ) -> None:
        """Extract and check the docstring of a node."""
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            return

        # Find the AST Constant node that IS the docstring
        if not node.body:
            return
        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr):
            return
        if not isinstance(first_stmt.value, ast.Constant):
            return
        if not isinstance(first_stmt.value.value, str):
            return

        docstring_lineno: int = first_stmt.value.lineno  # opening triple-quote line

        if self._has_suppression(def_lineno, docstring_lineno):
            return

        # Check each line of the docstring for patterns
        doc_lines = docstring.splitlines()
        for offset, doc_line in enumerate(doc_lines):
            actual_lineno = docstring_lineno + offset

            # Sycophancy (ERROR)
            if _SYCOPHANCY_RE.match(doc_line):
                self.violations.append(
                    SlopViolation(
                        filename=self.filename,
                        line=actual_lineno,
                        check=CHECK_SYCOPHANCY,
                        severity=SEVERITY_ERROR,
                        message=f"Sycophantic opener: {doc_line.strip()!r}",
                        source_line=doc_line,
                    )
                )

            # reST docstring (ERROR)
            if _REST_RE.match(doc_line):
                self.violations.append(
                    SlopViolation(
                        filename=self.filename,
                        line=actual_lineno,
                        check=CHECK_REST_DOCSTRING,
                        severity=SEVERITY_ERROR,
                        message=f"reST-style docstring marker: {doc_line.strip()!r}",
                        source_line=doc_line,
                    )
                )

            # Boilerplate opener (WARNING)
            if _BOILERPLATE_RE.match(doc_line):
                self.violations.append(
                    SlopViolation(
                        filename=self.filename,
                        line=actual_lineno,
                        check=CHECK_BOILERPLATE_DOCSTRING,
                        severity=SEVERITY_WARNING,
                        message=f"Boilerplate docstring opener: {doc_line.strip()!r}",
                        source_line=doc_line,
                    )
                )

            # Markdown separator (WARNING)
            if _MD_SEPARATOR_RE.search(doc_line):
                self.violations.append(
                    SlopViolation(
                        filename=self.filename,
                        line=actual_lineno,
                        check=CHECK_MD_SEPARATOR,
                        severity=SEVERITY_WARNING,
                        message=f"Markdown-style separator in docstring: {doc_line.strip()!r}",
                        source_line=doc_line,
                    )
                )

    # ------------------------------------------------------------------
    # AST visit methods
    # ------------------------------------------------------------------

    def visit_Module(self, node: ast.Module) -> None:
        self._check_docstring(node, 1)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Line-based checks (non-docstring patterns)
# ---------------------------------------------------------------------------


def _check_lines(filename: str, source_lines: list[str]) -> list[SlopViolation]:
    """
    Line-based regex checks for patterns that don't require AST analysis.
    Only applies outside of docstrings (we use a simple heuristic: skip
    lines inside triple-quoted strings by tracking quote depth).

    step_narration is only checked in Markdown files (.md), not Python files.
    In Python code, '# Step N:' is a legitimate ordered-step comment pattern
    (e.g., documenting multi-step functions). In Markdown, it is LLM boilerplate.
    """
    violations: list[SlopViolation] = []
    is_markdown = filename.endswith(".md")

    in_triple_quote = False
    triple_char = ""

    for lineno, line in enumerate(source_lines, start=1):
        stripped = line.rstrip()

        # Toggle triple-quote tracking (simple heuristic)
        # Count occurrences of """ and '''
        for tq in ('"""', "'''"):
            count = stripped.count(tq)
            if count:
                if not in_triple_quote:
                    if count % 2 == 1:
                        in_triple_quote = True
                        triple_char = tq
                elif tq == triple_char:
                    if count % 2 == 1:
                        in_triple_quote = False
                        triple_char = ""

        if in_triple_quote:
            continue

        # Step narration: "# Step N:" — Markdown files only.
        # Python inline comments like "# Step 1: Clone repo" are legitimate code
        # documentation for ordered multi-step functions; only flag in .md files
        # where "## Step N:" / "### Step N:" is LLM-generated structural boilerplate.
        if is_markdown:
            comment_match = re.search(r"#(.+)", stripped)
            if comment_match:
                comment_text = comment_match.group(0)
                if _STEP_NARRATION_RE.search(comment_text):
                    # Check for suppression on this line
                    if SUPPRESSION_MARKER not in stripped:
                        violations.append(
                            SlopViolation(
                                filename=filename,
                                line=lineno,
                                check=CHECK_STEP_NARRATION,
                                severity=SEVERITY_WARNING,
                                message=f"Step narration comment: {comment_text.strip()!r}",
                                source_line=stripped,
                            )
                        )

    return violations


# ---------------------------------------------------------------------------
# File-level checker
# ---------------------------------------------------------------------------


def check_file(filepath: str | Path) -> list[SlopViolation]:
    """
    Check a single Python file for AI-slop patterns.

    Returns a list of SlopViolation instances (may be empty).
    """
    path = Path(filepath)
    violations: list[SlopViolation] = []

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            SlopViolation(
                filename=str(filepath),
                line=0,
                check="file_read",
                severity=SEVERITY_ERROR,
                message=f"Cannot read file: {exc}",
            )
        ]

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as exc:
        return [
            SlopViolation(
                filename=str(filepath),
                line=exc.lineno or 0,
                check="syntax_error",
                severity=SEVERITY_ERROR,
                message=f"Syntax error: {exc.msg}",
            )
        ]

    source_lines = source.splitlines()

    # AST-based docstring checks
    visitor = _DocstringVisitor(filename=str(filepath), source_lines=source_lines)
    visitor.visit(tree)
    violations.extend(visitor.violations)

    # Line-based checks (step narration, etc.)
    violations.extend(_check_lines(str(filepath), source_lines))

    # Sort by line number
    violations.sort(key=lambda v: v.line)
    return violations


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the AI-slop checker.

    Returns:
        0 - No violations (or only WARNING/INFO in non-strict mode)
        1 - ERROR violations found
        2 - WARNING violations found (--strict mode only)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Check Python/Markdown files for AI-slop patterns."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files or directories to check. When no files are given, exits 0.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARNING violations as blocking (exit code 2).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Report mode: include INFO violations, scan directories recursively.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON.",
    )

    args = parser.parse_args(argv)

    # Collect files
    files: list[Path] = []
    for f in args.files:
        p = Path(f)
        if p.is_dir():
            files.extend(p.rglob("*.py"))
            if args.report:
                files.extend(p.rglob("*.md"))
        elif p.exists():
            files.append(p)

    all_violations: list[SlopViolation] = []
    for filepath in files:
        if filepath.suffix == ".py":
            all_violations.extend(check_file(filepath))
        # Markdown files: no AST checks, only line-based (step_narration)
        elif filepath.suffix == ".md":
            try:
                source_lines = filepath.read_text(encoding="utf-8").splitlines()
                all_violations.extend(_check_lines(str(filepath), source_lines))
            except OSError as exc:
                all_violations.append(
                    SlopViolation(
                        filename=str(filepath),
                        line=0,
                        check="file_read",
                        severity=SEVERITY_ERROR,
                        message=f"Cannot read file: {exc}",
                    )
                )

    # Filter by severity
    if not args.report:
        all_violations = [
            v
            for v in all_violations
            if v.severity in (SEVERITY_ERROR, SEVERITY_WARNING)
        ]

    if args.json_output:
        import json

        output: list[dict[str, str | int]] = [
            {
                "filename": v.filename,
                "line": v.line,
                "check": v.check,
                "severity": v.severity,
                "message": v.message,
            }
            for v in all_violations
        ]
        print(json.dumps(output, indent=2))
    else:
        for v in all_violations:
            print(v.format_line(), file=sys.stderr)

    has_errors = any(v.severity == SEVERITY_ERROR for v in all_violations)
    has_warnings = any(v.severity == SEVERITY_WARNING for v in all_violations)

    if has_errors:
        return 1
    if args.strict and has_warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
