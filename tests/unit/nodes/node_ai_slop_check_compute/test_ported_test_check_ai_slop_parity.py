# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Port the loader versus hardcoded-rule parity gate onto the AI-slop node."""

from __future__ import annotations

import ast
import re as _re
import textwrap
from pathlib import Path

import pytest

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)
from omnibase_core.nodes.node_ai_slop_check_compute.handler import (
    NodeAiSlopCheckCompute,
)
from omnibase_core.nodes.node_ai_slop_check_compute.rules_ai_slop import (
    resolve_script_rules,
)

pytestmark = pytest.mark.unit


def _check_source(
    path: Path, *, repo_root: Path
) -> tuple[ModelValidationFindingEmbed, ...]:
    report = NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[
                ModelSourceFile(path=str(path), source=path.read_text(encoding="utf-8"))
            ],
            rules=resolve_script_rules(repo_root, docstrings=True)
            + resolve_script_rules(repo_root, docstrings=False),
            fallback_docstring_rules=resolve_script_rules(Path.cwd(), docstrings=True),
        )
    )
    return report.findings


# Retain the original inline hardcoded oracle independently of node matchers.
_OLD_SYCOPHANCY_RE = _re.compile(
    r"^\s*(Excellent|Great|Sure|Certainly|Absolutely|Of course|Happy to|"
    r"I would be|Gladly|Wonderful|Perfect|Fantastic|Awesome)[!,. ]",
    _re.IGNORECASE,
)
_OLD_REST_RE = _re.compile(r"^\s*:(param|type|returns?|rtype|raises?|var|ivar|cvar)\b")
_OLD_BOILERPLATE_RE = _re.compile(
    r"^\s*This\s+(module|class|function|method|file|script|node|handler|service)"
    r"\s+(provides?|implements?|contains?|is responsible for|handles?|manages?|offers?)",
    _re.IGNORECASE,
)
_OLD_STEP_NARRATION_RE = _re.compile(r"#\s*Step\s+\d+\s*[:\-]", _re.IGNORECASE)
_OLD_MD_SEPARATOR_RE = _re.compile(r"={4,}")

_OLD_SUPPRESSION = "ai-slop" + "-ok"


def _old_check_docstring_violations(
    source: str, filename: str
) -> set[tuple[int, str, str]]:
    """Run original v1.0 docstring checks; returns {(lineno, check, severity)}."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return set()

    source_lines = source.splitlines()
    violations: set[tuple[int, str, str]] = set()

    def _has_suppression(def_lineno: int, docstring_lineno: int) -> bool:
        n = len(source_lines)

        def _chk(ln: int) -> bool:
            return 1 <= ln <= n and _OLD_SUPPRESSION in source_lines[ln - 1]

        return _chk(def_lineno) or _chk(docstring_lineno) or _chk(def_lineno - 1)

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        if not node.body:
            continue
        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr) or not isinstance(
            first_stmt.value, ast.Constant
        ):
            continue
        if not isinstance(first_stmt.value.value, str):
            continue
        docstring_lineno = first_stmt.value.lineno
        def_lineno = 1 if isinstance(node, ast.Module) else node.lineno
        if _has_suppression(def_lineno, docstring_lineno):
            continue
        for offset, doc_line in enumerate(docstring.splitlines()):
            ln = docstring_lineno + offset
            if _OLD_SYCOPHANCY_RE.match(doc_line):
                violations.add((ln, "sycophancy", "ERROR"))
            if _OLD_REST_RE.match(doc_line):
                violations.add((ln, "rest_docstring", "ERROR"))
            if _OLD_BOILERPLATE_RE.match(doc_line):
                violations.add((ln, "boilerplate_docstring", "WARNING"))
            if _OLD_MD_SEPARATOR_RE.search(doc_line):
                violations.add((ln, "md_separator", "WARNING"))
    return violations


def _old_check_line_violations(source: str, filename: str) -> set[tuple[int, str, str]]:
    """Run original v1.0 line-based checks; returns {(lineno, check, severity)}."""
    violations: set[tuple[int, str, str]] = set()
    is_markdown = filename.endswith(".md")
    lines = source.splitlines()
    in_triple_quote = False
    triple_char = ""
    in_md_code_fence = False

    for lineno, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if not is_markdown:
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
        if is_markdown:
            if stripped.startswith(("```", "~~~")):
                in_md_code_fence = not in_md_code_fence
            if in_md_code_fence or stripped.startswith(("```", "~~~")):
                continue
            comment_match = _re.search(r"#(.+)", stripped)
            if comment_match:
                comment_text = comment_match.group(0)
                if _OLD_STEP_NARRATION_RE.search(comment_text):
                    if _OLD_SUPPRESSION not in stripped:
                        violations.add((lineno, "step_narration", "WARNING"))
    return violations


# Fixture corpus

FIXTURE_PY = textwrap.dedent("""\
    def good_function():
        \"\"\"Normal docstring — no slop.\"\"\"
        pass


    def sycophantic_fn():
        \"\"\"Excellent function that does stuff.\"\"\"
        pass


    def rest_style():
        \"\"\"Do something.

        :param x: the input
        :returns: the output
        \"\"\"
        pass


    def boilerplate_fn():
        \"\"\"This function provides a way to do stuff.\"\"\"
        pass


    class BadClass:
        \"\"\"
        ============================
        This class implements stuff.
        \"\"\"
        pass


    def suppressed():  # {suppression}: intentional test
        \"\"\"Excellent — this should NOT be flagged.\"\"\"
        pass
""")

FIXTURE_PY = FIXTURE_PY.replace("{suppression}", _OLD_SUPPRESSION)

FIXTURE_MD = textwrap.dedent("""\
    # Normal heading

    Some prose.

    ## Step 1: Do the thing

    More prose.

    ```python
    # Step 2: This is inside a code block and should not be flagged
    ```

    ## Step 3: Another step
""")


def test_parity_python_docstring_rules(tmp_path: Path) -> None:
    """New loader-backed path produces identical findings to v1.0 on .py fixture."""
    fixture = tmp_path / "fixture.py"
    fixture.write_text(FIXTURE_PY, encoding="utf-8")

    # Old path
    old_violations = _old_check_docstring_violations(
        FIXTURE_PY, str(fixture)
    ) | _old_check_line_violations(FIXTURE_PY, str(fixture))

    # New path (no repo config → uses defaults, which match v1.0)
    new_raw = _check_source(fixture, repo_root=tmp_path)
    # Filter to the same rules the old code handled: docstring + line-based originals
    original_rules = {
        "sycophancy",
        "rest_docstring",
        "boilerplate_docstring",
        "md_separator",
        "step_narration",
    }
    new_violations = {
        (
            int((v.location or "").rsplit(":", 1)[1]),
            v.rule_id,
            str(v.evidence["script_severity"]),
        )
        for v in new_raw
        if v.rule_id in original_rules
    }

    assert new_violations == old_violations, (
        f"Parity failure on Python fixture.\n"
        f"Old only: {old_violations - new_violations}\n"
        f"New only: {new_violations - old_violations}"
    )


def test_parity_markdown_step_narration(tmp_path: Path) -> None:
    """New loader-backed path produces identical step_narration findings on .md fixture."""
    fixture = tmp_path / "fixture.md"
    fixture.write_text(FIXTURE_MD, encoding="utf-8")

    old_violations = _old_check_line_violations(FIXTURE_MD, str(fixture))

    new_raw = _check_source(fixture, repo_root=tmp_path)
    new_violations = {
        (
            int((v.location or "").rsplit(":", 1)[1]),
            v.rule_id,
            str(v.evidence["script_severity"]),
        )
        for v in new_raw
        if v.rule_id == "step_narration"
    }

    assert new_violations == old_violations, (
        f"Parity failure on Markdown fixture.\n"
        f"Old only: {old_violations - new_violations}\n"
        f"New only: {new_violations - old_violations}"
    )


def test_suppression_still_works(tmp_path: Path) -> None:
    """Suppressed sycophancy must not appear in new output."""
    fixture = tmp_path / "suppressed.py"
    fixture.write_text(FIXTURE_PY, encoding="utf-8")
    violations = _check_source(fixture, repo_root=tmp_path)
    # The suppressed() function must not produce any sycophancy finding
    flagged_lines = {
        int((v.location or "").rsplit(":", 1)[1])
        for v in violations
        if v.rule_id == "sycophancy"
    }
    # Line 37 is the suppressed function's docstring — must not appear
    # We check that no violations reference "suppressed" context (line 37)
    source_lines = FIXTURE_PY.splitlines()
    for line_no in flagged_lines:
        line_content = source_lines[line_no - 1] if line_no <= len(source_lines) else ""
        assert "NOT be flagged" not in line_content, (
            f"Suppressed sycophancy was incorrectly flagged at line {line_no}"
        )


def test_override_disables_rule_parity(tmp_path: Path) -> None:
    """With sycophancy disabled via per-repo config, no sycophancy violations appear."""
    import textwrap as tw

    onex_dir = tmp_path / ".onex"
    onex_dir.mkdir()
    (onex_dir / "aislop-rules.yaml").write_text(
        tw.dedent("""\
            overrides:
              - name: sycophancy
                enabled: false
        """)
    )
    fixture = tmp_path / "fixture.py"
    fixture.write_text(FIXTURE_PY, encoding="utf-8")
    violations = _check_source(fixture, repo_root=tmp_path)
    assert not any(v.rule_id == "sycophancy" for v in violations), (
        "sycophancy rule should be disabled by per-repo config"
    )
