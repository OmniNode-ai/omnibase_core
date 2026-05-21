#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX AI-Slop Pattern Checker v2.0

Pre-commit hook and CI gate that detects AI-generated boilerplate ("slop") in
Python and Markdown files.  Rule patterns are loaded from the bundled default
YAML (omnibase_core/contracts/aislop_default_rules.yaml) and can be overridden
per-repo via .onex/aislop-rules.yaml (OMN-11132).

Rule set v1.0 (locked 2026-03-02, OMN-3191) — unchanged defaults:
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
  v2.0 (2026-05-17, OMN-11132): rules loaded from YAML; --config flag added.
    Backwards-compatible: default behavior identical to v1.0.
  v1.0 (2026-03-02): step_narration scoped to Markdown files only; code fences skipped.
    Rationale: 48h post-rollout audit (OMN-3191) found "# Step N:" in Python code
    triggers 110+ false positives in omniintelligence and omniclaude alone.
    Python numbered steps ("# Step 1: Fetch session snapshot") are legitimate
    multi-step function documentation. Only Markdown step headings are LLM slop.
    Code fence tracking added: lines inside ```...``` blocks in .md files are skipped
    so that quoted Python examples in documentation are not flagged.
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
    python scripts/validation/check_ai_slop.py --config /path/to/repo/root [files...]

Linear tickets: OMN-2971 (original), OMN-3191 (v1.0 tuning), OMN-11132 (configurable)
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
# Rule loader — builds compiled regexes from the configured rule set
# ---------------------------------------------------------------------------


def _build_docstring_regexes(
    repo_root: Path | None,
) -> dict[str, tuple[re.Pattern[str], str]]:
    """Return {rule_name: (compiled_pattern, severity)} for AST-docstring rules.

    Falls back to hardcoded patterns if the rule loader is unavailable (e.g.
    when running the script before omnibase_core is installed).
    """
    try:
        from omnibase_core.validation.aislop_rule_loader import resolve_rules

        ruleset = resolve_rules(repo_root or Path.cwd())
        result: dict[str, tuple[re.Pattern[str], str]] = {}
        for rule in ruleset.rules:
            if rule.pattern_type == "regex_ast_docstring" and rule.enabled:
                result[rule.name] = (
                    re.compile(rule.pattern, re.IGNORECASE | re.VERBOSE),
                    rule.severity,
                )
        return result
    except Exception:
        # Fallback: hardcoded v1.0 patterns (identical to original defaults)
        return {
            CHECK_SYCOPHANCY: (
                re.compile(
                    r"^\s*(Excellent|Great|Sure|Certainly|Absolutely|Of course|Happy to|"
                    r"I would be|Gladly|Wonderful|Perfect|Fantastic|Awesome)[!,. ]",
                    re.IGNORECASE,
                ),
                SEVERITY_ERROR,
            ),
            CHECK_REST_DOCSTRING: (
                re.compile(r"^\s*:(param|type|returns?|rtype|raises?|var|ivar|cvar)\b"),
                SEVERITY_ERROR,
            ),
            CHECK_BOILERPLATE_DOCSTRING: (
                re.compile(
                    r"^\s*This\s+(module|class|function|method|file|script|node|handler|service)"
                    r"\s+(provides?|implements?|contains?|is responsible for|handles?|manages?|offers?)",
                    re.IGNORECASE,
                ),
                SEVERITY_WARNING,
            ),
            CHECK_MD_SEPARATOR: (
                re.compile(r"={4,}"),
                SEVERITY_WARNING,
            ),
        }


def _build_line_regexes(
    repo_root: Path | None,
) -> dict[str, tuple[re.Pattern[str], str, list[str]]]:
    """Return {rule_name: (compiled_pattern, severity, file_globs)} for line rules."""
    try:
        from omnibase_core.validation.aislop_rule_loader import resolve_rules

        ruleset = resolve_rules(repo_root or Path.cwd())
        result: dict[str, tuple[re.Pattern[str], str, list[str]]] = {}
        for rule in ruleset.rules:
            if rule.pattern_type == "regex_line" and rule.enabled:
                result[rule.name] = (
                    re.compile(rule.pattern, re.IGNORECASE),
                    rule.severity,
                    rule.file_globs,
                )
        return result
    except Exception:
        return {
            CHECK_STEP_NARRATION: (
                re.compile(r"#\s*Step\s+\d+\s*[:\-]", re.IGNORECASE),
                SEVERITY_WARNING,
                ["*.md"],
            ),
        }


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

    def __init__(
        self,
        filename: str,
        source_lines: list[str],
        docstring_rules: dict[str, tuple[re.Pattern[str], str]] | None = None,
    ) -> None:
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[SlopViolation] = []
        # Accepts externally-resolved rules or falls back to defaults
        self._rules = docstring_rules or _build_docstring_regexes(None)

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

        doc_lines = docstring.splitlines()
        for offset, doc_line in enumerate(doc_lines):
            actual_lineno = docstring_lineno + offset
            for rule_name, (pattern, severity) in self._rules.items():
                match_fn = (
                    pattern.match if rule_name != CHECK_MD_SEPARATOR else pattern.search
                )
                if match_fn(doc_line):
                    self.violations.append(
                        SlopViolation(
                            filename=self.filename,
                            line=actual_lineno,
                            check=rule_name,
                            severity=severity,
                            message=_format_docstring_message(rule_name, doc_line),
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


def _format_docstring_message(rule_name: str, doc_line: str) -> str:
    stripped = doc_line.strip()
    if rule_name == CHECK_SYCOPHANCY:
        return f"Sycophantic opener: {stripped!r}"
    if rule_name == CHECK_REST_DOCSTRING:
        return f"reST-style docstring marker: {stripped!r}"
    if rule_name == CHECK_BOILERPLATE_DOCSTRING:
        return f"Boilerplate docstring opener: {stripped!r}"
    if rule_name == CHECK_MD_SEPARATOR:
        return f"Markdown-style separator in docstring: {stripped!r}"
    return f"Violation in docstring: {stripped!r}"


# ---------------------------------------------------------------------------
# Line-based checks (non-docstring patterns)
# ---------------------------------------------------------------------------


LineRule = tuple[str, re.Pattern[str], str]


def _applicable_line_rules(
    line_rules: dict[str, tuple[re.Pattern[str], str, list[str]]],
    *,
    is_markdown: bool,
) -> list[LineRule]:
    applicable: list[LineRule] = []
    for rule_name, (pattern, severity, globs) in line_rules.items():
        md_only = all(g == "*.md" for g in globs)
        py_only = all(g == "*.py" for g in globs) and not any(
            g == "*.md" for g in globs
        )
        if is_markdown and py_only:
            continue
        if not is_markdown and md_only:
            continue
        applicable.append((rule_name, pattern, severity))
    return applicable


def _toggle_triple_quote_state(
    stripped: str, *, in_triple_quote: bool, triple_char: str
) -> tuple[bool, str]:
    for quote in ('"""', "'''"):
        count = stripped.count(quote)
        if not count:
            continue
        if not in_triple_quote and count % 2 == 1:
            return True, quote
        if quote == triple_char and count % 2 == 1:
            return False, ""
    return in_triple_quote, triple_char


def _build_line_violation(
    *,
    filename: str,
    lineno: int,
    rule_name: str,
    severity: str,
    message: str,
    source_line: str,
) -> SlopViolation:
    return SlopViolation(
        filename=filename,
        line=lineno,
        check=rule_name,
        severity=severity,
        message=message,
        source_line=source_line,
    )


def _check_line_rules(
    *,
    filename: str,
    lineno: int,
    stripped: str,
    applicable: list[LineRule],
) -> list[SlopViolation]:
    if SUPPRESSION_MARKER in stripped:
        return []

    violations: list[SlopViolation] = []
    for rule_name, pattern, severity in applicable:
        if rule_name == CHECK_STEP_NARRATION:
            comment_match = re.search(r"#(.+)", stripped)
            if comment_match and pattern.search(comment_match.group(0)):
                comment_text = comment_match.group(0)
                violations.append(
                    _build_line_violation(
                        filename=filename,
                        lineno=lineno,
                        rule_name=rule_name,
                        severity=severity,
                        message=f"Step narration comment: {comment_text.strip()!r}",
                        source_line=stripped,
                    )
                )
            continue

        if pattern.search(stripped):
            violations.append(
                _build_line_violation(
                    filename=filename,
                    lineno=lineno,
                    rule_name=rule_name,
                    severity=severity,
                    message=f"Pattern match ({rule_name}): {stripped!r}",
                    source_line=stripped,
                )
            )
    return violations


def _check_lines(
    filename: str,
    source_lines: list[str],
    line_rules: dict[str, tuple[re.Pattern[str], str, list[str]]] | None = None,
) -> list[SlopViolation]:
    """
    Line-based regex checks for patterns that don't require AST analysis.
    Only applies outside of docstrings (we use a simple heuristic: skip
    lines inside triple-quoted strings by tracking quote depth).

    step_narration is only checked in Markdown files (.md), not Python files.
    In Python code, '# Step N:' is a legitimate ordered-step comment pattern
    (e.g., documenting multi-step functions). In Markdown, it is LLM boilerplate.

    For Markdown files, lines inside fenced code blocks (``` ... ```) are skipped
    so that quoted Python examples with '# Step N:' comments are not flagged.
    """
    if line_rules is None:
        line_rules = _build_line_regexes(None)

    violations: list[SlopViolation] = []
    is_markdown = filename.endswith(".md")

    applicable = _applicable_line_rules(line_rules, is_markdown=is_markdown)

    in_triple_quote = False
    triple_char = ""
    in_md_code_fence = False

    for lineno, line in enumerate(source_lines, start=1):
        stripped = line.rstrip()

        # Toggle triple-quote tracking for Python files (simple heuristic)
        if not is_markdown:
            in_triple_quote, triple_char = _toggle_triple_quote_state(
                stripped,
                in_triple_quote=in_triple_quote,
                triple_char=triple_char,
            )
            if in_triple_quote:
                continue

        # For Markdown: track fenced code blocks (``` or ~~~) to skip their content.
        if is_markdown:
            if stripped.startswith(("```", "~~~")):
                in_md_code_fence = not in_md_code_fence
            if in_md_code_fence or stripped.startswith(("```", "~~~")):
                continue

        violations.extend(
            _check_line_rules(
                filename=filename,
                lineno=lineno,
                stripped=stripped,
                applicable=applicable,
            )
        )

    return violations


# ---------------------------------------------------------------------------
# File-level checker
# ---------------------------------------------------------------------------


def check_file(
    filepath: str | Path,
    repo_root: Path | None = None,
) -> list[SlopViolation]:
    """Check a single Python or Markdown file for AI-slop patterns."""
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

    source_lines = source.splitlines()
    line_rules = _build_line_regexes(repo_root)

    if path.suffix == ".py":
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

        docstring_rules = _build_docstring_regexes(repo_root)
        visitor = _DocstringVisitor(
            filename=str(filepath),
            source_lines=source_lines,
            docstring_rules=docstring_rules,
        )
        visitor.visit(tree)
        violations.extend(visitor.violations)

    violations.extend(_check_lines(str(filepath), source_lines, line_rules))
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
    parser.add_argument(
        "--config",
        metavar="REPO_ROOT",
        default=None,
        help="Repo root containing .onex/aislop-rules.yaml for per-repo overrides.",
    )

    args = parser.parse_args(argv)
    repo_root = Path(args.config) if args.config else None

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
        if filepath.suffix in (".py", ".md"):
            all_violations.extend(check_file(filepath, repo_root=repo_root))

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
