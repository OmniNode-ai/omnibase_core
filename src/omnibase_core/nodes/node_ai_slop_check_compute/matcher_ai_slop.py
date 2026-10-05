# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure line matching and finding construction, ported from core's script."""

from __future__ import annotations

import re
from typing import Final, Literal

from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

VALIDATOR_ID: Final = "ai-slop"
SUPPRESSION_MARKER: Final = "ai-slop" + "-ok"
CompiledRule = tuple[re.Pattern[str], ModelAislopRule]


def compile_rules(
    rules: list[ModelAislopRule], *, docstrings: bool
) -> dict[str, CompiledRule]:
    """Match the script's flags, enabled filter and duplicate-name behavior."""
    pattern_type = "regex_ast_docstring" if docstrings else "regex_line"
    flags = re.IGNORECASE | re.VERBOSE if docstrings else re.IGNORECASE
    return {
        rule.name: (re.compile(rule.pattern, flags), rule)
        for rule in rules
        if rule.enabled and rule.pattern_type == pattern_type
    }


def make_finding(
    path: str, line: int, rule: str, severity: str, message: str
) -> ModelValidationFinding:
    """Keep script severity as evidence for exact CLI and exit-code parity.

    Script INFO findings are informational PASS findings in the canonical
    vocabulary, so strict mode does not turn them into blocking findings.
    """
    canonical: Literal["FAIL", "WARN", "PASS", "ERROR"] = "PASS"
    if severity == "ERROR":
        canonical = "ERROR" if rule == "syntax_error" else "FAIL"
    elif severity == "WARNING":
        canonical = "WARN"
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity=canonical,
        rule_id=rule,
        location=f"{path}:{line}",
        message=message,
        evidence={"script_severity": severity},
    )


def docstring_message(rule_name: str, doc_line: str) -> str:
    """Reproduce the script's message bytes."""
    stripped = doc_line.strip()
    prefixes = {
        "sycophancy": "Sycophantic opener",
        "rest_docstring": "reST-style docstring marker",
        "boilerplate_docstring": "Boilerplate docstring opener",
        "md_separator": "Markdown-style separator in docstring",
    }
    return f"{prefixes.get(rule_name, 'Violation in docstring')}: {stripped!r}"


def check_lines(
    path: str, source_lines: list[str], rules: dict[str, CompiledRule]
) -> list[ModelValidationFinding]:
    """Preserve the script's quote heuristic and unindented fence handling."""
    is_markdown = path.endswith(".md")
    applicable: dict[str, CompiledRule] = {}
    for name, (pattern, rule) in rules.items():
        md_only = all(g == "*.md" for g in rule.file_globs)
        py_only = all(g == "*.py" for g in rule.file_globs) and not any(
            g == "*.md" for g in rule.file_globs
        )
        if (is_markdown and py_only) or (not is_markdown and md_only):
            continue
        applicable[name] = (pattern, rule)

    findings: list[ModelValidationFinding] = []
    in_triple_quote = False
    triple_char = ""
    in_md_code_fence = False
    for lineno, line in enumerate(source_lines, start=1):
        stripped = line.rstrip()
        if not is_markdown:
            for quote in ('"""', "'''"):
                count = stripped.count(quote)
                if not count:
                    continue
                if not in_triple_quote and count % 2 == 1:
                    in_triple_quote, triple_char = True, quote
                    break
                if quote == triple_char and count % 2 == 1:
                    in_triple_quote, triple_char = False, ""
                    break
            if in_triple_quote:
                continue
        if is_markdown:
            if stripped.startswith(("```", "~~~")):
                in_md_code_fence = not in_md_code_fence
            if in_md_code_fence or stripped.startswith(("```", "~~~")):
                continue
        if SUPPRESSION_MARKER in stripped:
            continue
        for name, (pattern, rule) in applicable.items():
            if name == "step_narration":
                match = re.search(r"#(.+)", stripped)
                if not match or not pattern.search(match.group(0)):
                    continue
                message = f"Step narration comment: {match.group(0).strip()!r}"
            else:
                if not pattern.search(stripped):
                    continue
                message = f"Pattern match ({name}): {stripped!r}"
            findings.append(make_finding(path, lineno, name, rule.severity, message))
    return findings
