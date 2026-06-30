# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the canonical no-new-os-environ validator (OMN-13566).

TDD test file written before the implementation. The validator must:

1. Block os.environ[KEY], os.environ.get(KEY), and os.getenv(KEY) calls
   outside the keep allowlist in source files.
2. Pass reads of keys listed in KEEP_ALLOWLIST.
3. Respect ``# env-read-ok: <reason>`` inline suppression.
4. Skip test files and scripts/ directories.
5. Parse multiline strings correctly (no false positives inside docstrings).
6. Exit 0 / 1 via main() for CLI use.
7. Contain a deliberate red-test corpus (used as DoD proof in CI).

Red-test corpus (DoD item: "a new env read in any repo fails CI"):
  The test ``test_deliberate_violation_corpus`` plants two known-bad snippets
  and asserts that validate_file() flags both.  If the validator ever stops
  flagging them, this test fails — proving the gate is live.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from omnibase_core.validators.no_new_os_environ import (
    KEEP_ALLOWLIST,
    validate_file,
    validate_paths,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, source: str) -> Path:
    p = tmp_path / name
    p.write_text(source, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Basic violation detection
# ---------------------------------------------------------------------------


def test_flags_os_environ_subscript(tmp_path: Path) -> None:
    """os.environ[KEY] outside allowlist → violation."""
    src = _write(
        tmp_path,
        "bad.py",
        'import os\nVAL = os.environ["MY_SECRET_KEY"]\n',
    )
    findings = validate_file(src)
    assert len(findings) == 1
    assert findings[0].var_name == "MY_SECRET_KEY"
    assert findings[0].line == 2


def test_flags_os_environ_get(tmp_path: Path) -> None:
    """os.environ.get(KEY) outside allowlist → violation."""
    src = _write(
        tmp_path,
        "bad2.py",
        'import os\nVAL = os.environ.get("UNLISTED_TOKEN")\n',
    )
    findings = validate_file(src)
    assert len(findings) == 1
    assert findings[0].var_name == "UNLISTED_TOKEN"


def test_flags_os_getenv(tmp_path: Path) -> None:
    """os.getenv(KEY) outside allowlist → violation."""
    src = _write(
        tmp_path,
        "bad3.py",
        'import os\nVAL = os.getenv("MYSTERY_PARAM")\n',
    )
    findings = validate_file(src)
    assert len(findings) == 1
    assert findings[0].var_name == "MYSTERY_PARAM"


# ---------------------------------------------------------------------------
# Allowlist pass-through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keep_var",
    sorted(KEEP_ALLOWLIST)[:10],  # spot-check 10 entries
)
def test_allows_keep_allowlist_vars(tmp_path: Path, keep_var: str) -> None:
    """Reads of vars in KEEP_ALLOWLIST must not produce findings."""
    src = _write(
        tmp_path,
        "ok.py",
        f'import os\nVAL = os.environ["{keep_var}"]\n',
    )
    assert validate_file(src) == []


def test_allows_omni_home(tmp_path: Path) -> None:
    src = _write(tmp_path, "ok2.py", 'import os\nroot = os.environ["OMNI_HOME"]\n')
    assert validate_file(src) == []


def test_allows_ci_var(tmp_path: Path) -> None:
    src = _write(tmp_path, "ok3.py", 'import os\nciv = os.getenv("CI")\n')
    assert validate_file(src) == []


# ---------------------------------------------------------------------------
# Inline suppression
# ---------------------------------------------------------------------------


def test_inline_suppression_skips_line(tmp_path: Path) -> None:
    """Lines annotated with # env-read-ok are skipped."""
    src = _write(
        tmp_path,
        "suppressed.py",
        'import os\nVAL = os.environ["MY_CUSTOM_KEY"]  # env-read-ok: bootstrap boundary\n',
    )
    assert validate_file(src) == []


def test_inline_suppression_required_reason(tmp_path: Path) -> None:
    """Bare # env-read-ok (no reason) is still accepted as suppression."""
    src = _write(
        tmp_path,
        "suppressed2.py",
        'import os\nVAL = os.environ["MY_CUSTOM_KEY"]  # env-read-ok\n',
    )
    assert validate_file(src) == []


# ---------------------------------------------------------------------------
# Skip rules
# ---------------------------------------------------------------------------


def test_skips_test_files(tmp_path: Path) -> None:
    """Files inside a tests/ directory are skipped entirely."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    src = tests_dir / "test_something.py"
    src.write_text('import os\nos.environ["UNLISTED"]\n', encoding="utf-8")
    assert validate_file(src) == []


def test_skips_scripts_dir(tmp_path: Path) -> None:
    """Files inside a scripts/ directory are skipped entirely."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    src = scripts_dir / "bootstrap.py"
    src.write_text('import os\nos.environ["UNLISTED"]\n', encoding="utf-8")
    assert validate_file(src) == []


def test_skips_non_python_file(tmp_path: Path) -> None:
    """Non-.py files are skipped."""
    src = _write(tmp_path, "config.yaml", 'key: "os.environ[THING]"\n')
    assert validate_file(src) == []


# ---------------------------------------------------------------------------
# Multiline string false-positive guard
# ---------------------------------------------------------------------------


def test_no_false_positive_in_docstring(tmp_path: Path) -> None:
    """env reads in docstrings / multiline strings must not fire."""
    src = _write(
        tmp_path,
        "docs.py",
        '''\
def foo():
    """
    Example::

        val = os.environ["SOME_KEY"]
    """
    pass
''',
    )
    assert validate_file(src) == []


def test_no_false_positive_in_triple_quoted_string(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "tqs.py",
        '''\
TEMPLATE = """
os.getenv("SHOULD_BE_IGNORED")
"""
''',
    )
    assert validate_file(src) == []


# ---------------------------------------------------------------------------
# validate_paths — multi-file aggregation
# ---------------------------------------------------------------------------


def test_validate_paths_aggregates(tmp_path: Path) -> None:
    """validate_paths returns findings from all supplied paths."""
    f1 = _write(tmp_path, "a.py", 'import os\nos.environ["AAA"]\n')
    f2 = _write(tmp_path, "b.py", 'import os\nos.getenv("BBB")\n')
    findings = validate_paths([f1, f2])
    var_names = {f.var_name for f in findings}
    assert "AAA" in var_names
    assert "BBB" in var_names


def test_validate_paths_returns_empty_on_clean_files(tmp_path: Path) -> None:
    f1 = _write(tmp_path, "clean.py", "x = 1\n")
    assert validate_paths([f1]) == []


# ---------------------------------------------------------------------------
# CLI (main) exit codes
# ---------------------------------------------------------------------------


def test_main_exits_0_on_no_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() returns 0 when no files have violations."""
    clean = _write(tmp_path, "clean.py", "x = 1\n")
    monkeypatch.setattr(sys, "argv", ["validator", str(clean)])
    from omnibase_core.validators.no_new_os_environ import main

    assert main() == 0


def test_main_exits_1_on_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() returns 1 when at least one violation is found."""
    bad = _write(tmp_path, "bad.py", 'import os\nos.environ["FORBIDDEN_KEY"]\n')
    monkeypatch.setattr(sys, "argv", ["validator", str(bad)])
    from omnibase_core.validators.no_new_os_environ import main

    assert main() == 1


# ---------------------------------------------------------------------------
# DELIBERATE RED-TEST CORPUS (DoD proof OMN-13566)
# ---------------------------------------------------------------------------
# These two snippets are planted violations — each must produce exactly one
# finding.  If the validator is ever regressed to the point of not catching
# them, this test fails, proving the CI gate would have let the violation in.


_CORPUS_VIOLATION_A = """\
import os

SECRET = os.environ["ONEX_NEW_VIOLATION_CORPUS_A"]
"""

_CORPUS_VIOLATION_B = """\
import os

SECRET = os.getenv("ONEX_NEW_VIOLATION_CORPUS_B")
"""


def test_deliberate_violation_corpus(tmp_path: Path) -> None:
    """Red-test corpus: two known-bad snippets must each produce exactly one finding."""
    va = _write(tmp_path, "corpus_a.py", _CORPUS_VIOLATION_A)
    vb = _write(tmp_path, "corpus_b.py", _CORPUS_VIOLATION_B)

    findings_a = validate_file(va)
    findings_b = validate_file(vb)

    assert len(findings_a) == 1, (
        f"Corpus-A violation not flagged — gate is broken! findings={findings_a}"
    )
    assert findings_a[0].var_name == "ONEX_NEW_VIOLATION_CORPUS_A"

    assert len(findings_b) == 1, (
        f"Corpus-B violation not flagged — gate is broken! findings={findings_b}"
    )
    assert findings_b[0].var_name == "ONEX_NEW_VIOLATION_CORPUS_B"
