# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for omnibase_core.validators.github_token_env_reads (OMN-13292).

Fleet port of omnimarket's check_github_token_env_reads (OMN-12856). Verifies:
(a) Clean source (contract api_key_ref resolution) produces zero violations.
(b) Each raw GitHub-token env-read form is detected (positive corpus).
(c) Suppression tokens silence a violation.
(d) Test files / excluded paths are skipped.
(e) main() exits 1 on violations (enforce) and 0 on a clean tree.
(f) Port-equivalence: the omnimarket origin's documented corpus yields the
    same verdict (1 violation per snippet) here.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omnibase_core.validators import github_token_env_reads as gate

# Each snippet is a single raw GitHub-token env read → exactly one violation.
_VIOLATION_SNIPPETS: list[str] = [
    'import os\ntoken = os.environ["GH_PAT"]\n',
    'import os\ntoken = os.environ.get("GH_PAT", "")\n',
    'import os\ntoken = os.getenv("GH_PAT")\n',
    'import os\ntoken = os.environ["GITHUB_TOKEN"]\n',
    'import os\ntoken = os.environ.get("GITHUB_TOKEN")\n',
    'import os\ntoken = os.getenv("GITHUB_TOKEN")\n',
    'import os\ntoken = os.environ["GH_TOKEN"]\n',
    'import os\ntoken = os.getenv("GH_TOKEN")\n',
]

_CLEAN_SOURCE = textwrap.dedent(
    """
    from pathlib import Path

    def get_token(resolver, contract_path: Path) -> str:
        # Secret resolved at the effect boundary from a contract api_key_ref.
        ref = contract_secret_ref(contract_path, "GITHUB_TOKEN")
        secret = resolver.resolve_api_key(ref)
        return secret.get_secret_value()

    # An unrelated env read of a non-token name is fine.
    import os
    region = os.environ.get("AWS_REGION", "us-east-1")
    """
)


@pytest.mark.unit
def test_clean_source_returns_empty() -> None:
    assert gate.scan_source(_CLEAN_SOURCE, "handler.py") == []


@pytest.mark.unit
@pytest.mark.parametrize("snippet", _VIOLATION_SNIPPETS)
def test_detects_each_raw_env_read(snippet: str) -> None:
    violations = gate.scan_source(snippet, "bad.py")
    assert len(violations) == 1, f"snippet {snippet!r} -> {violations}"
    assert "raw GitHub-token env read" in violations[0]


@pytest.mark.unit
@pytest.mark.parametrize(
    "token",
    ["# github-token-env-ok: boundary resolver", "# ONEX_EXCLUDE: runtime secret read"],
)
def test_suppression_token_silences_violation(token: str) -> None:
    snippet = f'import os\ntoken = os.environ["GITHUB_TOKEN"]  {token}\n'
    assert gate.scan_source(snippet, "boundary.py") == []


@pytest.mark.unit
def test_suppression_on_multiline_call() -> None:
    snippet = (
        "import os\n"
        "token = os.environ.get(  # github-token-env-ok: boundary\n"
        '    "GITHUB_TOKEN",\n'
        '    "",\n'
        ")\n"
    )
    assert gate.scan_source(snippet, "boundary.py") == []


@pytest.mark.unit
def test_non_token_env_name_is_legal() -> None:
    snippet = 'import os\nx = os.environ["SOME_OTHER_TOKEN"]\ny = os.getenv("HOME")\n'
    assert gate.scan_source(snippet, "ok.py") == []


@pytest.mark.unit
def test_syntax_error_source_is_skipped() -> None:
    assert gate.scan_source("def (:\n", "broken.py") == []


@pytest.mark.unit
def test_scan_tree_excludes_tests(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "good.py").write_text("x = 1\n", encoding="utf-8")
    (src / "bad.py").write_text(
        'import os\ntoken = os.environ["GH_PAT"]\n', encoding="utf-8"
    )
    tests_dir = src / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_thing.py").write_text(
        'import os\ntoken = os.environ["GH_PAT"]\n', encoding="utf-8"
    )
    violations = gate.scan_tree(tmp_path)
    assert len(violations) == 1
    assert "bad.py" in violations[0]
    assert "test_thing.py" not in violations[0]


@pytest.mark.unit
def test_main_exits_1_on_violation_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('import os\ntoken = os.environ["GITHUB_TOKEN"]\n', encoding="utf-8")
    assert gate.main([str(bad)]) == 1


@pytest.mark.unit
def test_main_exits_0_on_clean_file(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text("x = 1\n", encoding="utf-8")
    assert gate.main([str(good)]) == 0


@pytest.mark.unit
def test_main_no_files_is_noop() -> None:
    assert gate.main([]) == 0


@pytest.mark.unit
def test_main_all_mode_scans_tree(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "bad.py").write_text(
        'import os\ntoken = os.getenv("GH_TOKEN")\n', encoding="utf-8"
    )
    assert gate.main(["--all", "--repo-root", str(tmp_path)]) == 1
