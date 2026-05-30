# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the gitignore-baseline validator (OMN-12452).

These tests exercise the validator logic directly (not via subprocess) so they
run fast and stay isolated from the CI environment's .gitignore state.

Each test creates a minimal temp-dir tree, writes .gitignore / pyproject.toml
as needed, and calls validate() directly with an explicit spec_path pointing at
the canonical architecture-handshakes/gitignore-baseline.yaml.

Coverage:
  - python repo missing the python managed block → finding
  - js-only repo (no pyproject.toml) with only the universal block → clean
  - both blocks present verbatim → clean
  - universal block with patterns in wrong order → finding
  - file-level suppression marker honored → clean
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.gitignore_baseline import validate

# ---------------------------------------------------------------------------
# Locate the canonical spec (installed next to the repo root in the worktree)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SPEC_PATH = _REPO_ROOT / "architecture-handshakes" / "gitignore-baseline.yaml"


@pytest.fixture(autouse=True, scope="module")
def _spec_exists() -> None:
    """Guard: skip the entire module if the spec file is absent."""
    assert _SPEC_PATH.exists(), (
        f"gitignore-baseline.yaml not found at {_SPEC_PATH}. "
        "Run from the omnibase_core repo root after OMN-12451 is merged."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Build block strings from explicit line lists so the closing triple-quote
# never appears at the end of a .gitignore content line (which confuses some
# formatters). The trailing newline is omitted; callers add it when needed.
_UNIVERSAL_LINES = [
    "# === onex-managed: universal ===",
    ".env",
    ".env.*",
    "!.env.example",
    ".DS_Store",
    "*.log",
    ".idea/",
    ".vscode/",
    "test-results/",
    "playwright-report/",
    "# === end onex-managed: universal ===",
]
_UNIVERSAL_BLOCK = "\n".join(_UNIVERSAL_LINES)

_PYTHON_LINES = [
    "# === onex-managed: python ===",
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    ".venv/",
    "venv/",
    "env/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "htmlcov/",
    "dist/",
    "build/",
    "*.egg-info/",
    "# === end onex-managed: python ===",
]
_PYTHON_BLOCK = "\n".join(_PYTHON_LINES)


def _write_gitignore(tmp_path: Path, content: str) -> None:
    (tmp_path / ".gitignore").write_text(content, encoding="utf-8")


def _write_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'test'\n", encoding="utf-8"
    )


def _write_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}\n', encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_python_repo_missing_python_block_fails(tmp_path: Path) -> None:
    """A repo with pyproject.toml that lacks the python managed block → finding."""
    _write_pyproject(tmp_path)
    _write_gitignore(tmp_path, _UNIVERSAL_BLOCK + "\n")

    findings = validate(tmp_path, _SPEC_PATH)

    assert len(findings) == 1, f"expected 1 finding, got {findings}"
    assert "python" in findings[0], f"finding should mention 'python': {findings[0]}"


@pytest.mark.unit
def test_js_repo_with_universal_block_passes(tmp_path: Path) -> None:
    """A JS-only repo (no pyproject.toml) with the universal block → clean."""
    _write_package_json(tmp_path)
    _write_gitignore(tmp_path, _UNIVERSAL_BLOCK + "\n")

    findings = validate(tmp_path, _SPEC_PATH)

    assert findings == [], f"expected no findings, got {findings}"


@pytest.mark.unit
def test_verbatim_match_passes(tmp_path: Path) -> None:
    """A Python repo with both blocks present verbatim → clean."""
    _write_pyproject(tmp_path)
    _write_gitignore(
        tmp_path,
        _UNIVERSAL_BLOCK + "\n\n" + _PYTHON_BLOCK + "\n",
    )

    findings = validate(tmp_path, _SPEC_PATH)

    assert findings == [], f"expected no findings, got {findings}"


@pytest.mark.unit
def test_altered_pattern_order_fails(tmp_path: Path) -> None:
    """Universal block with two patterns swapped → finding (order matters)."""
    _write_pyproject(tmp_path)
    # Swap .DS_Store and *.log relative to the canonical order
    altered_universal = """\
# === onex-managed: universal ===
.env
.env.*
!.env.example
*.log
.DS_Store
.idea/
.vscode/
test-results/
playwright-report/
# === end onex-managed: universal ==="""
    _write_gitignore(
        tmp_path,
        altered_universal + "\n\n" + _PYTHON_BLOCK + "\n",
    )

    findings = validate(tmp_path, _SPEC_PATH)

    # At least the universal block should be flagged
    assert any("universal" in f for f in findings), (
        f"expected a finding for 'universal' reordering, got {findings}"
    )


@pytest.mark.unit
def test_suppression_marker_honored(tmp_path: Path) -> None:
    """File-level suppression marker suppresses all findings."""
    _write_pyproject(tmp_path)
    # .gitignore is completely empty except for the suppression marker
    _write_gitignore(tmp_path, "# gitignore-ok: intentionally minimal for tests\n")

    findings = validate(tmp_path, _SPEC_PATH)

    assert findings == [], f"suppression marker should silence findings, got {findings}"


@pytest.mark.unit
def test_missing_gitignore_produces_finding(tmp_path: Path) -> None:
    """Repo without a .gitignore at all → finding."""
    _write_pyproject(tmp_path)
    # no .gitignore written

    findings = validate(tmp_path, _SPEC_PATH)

    assert len(findings) == 1, (
        f"expected 1 finding for missing .gitignore, got {findings}"
    )
    assert ".gitignore" in findings[0]


@pytest.mark.unit
def test_both_blocks_missing_produces_two_findings(tmp_path: Path) -> None:
    """Python repo with empty .gitignore → one finding per block."""
    _write_pyproject(tmp_path)
    _write_gitignore(tmp_path, "# just some comment\n")

    findings = validate(tmp_path, _SPEC_PATH)

    assert len(findings) == 2, (
        f"expected 2 findings (universal + python), got {findings}"
    )
    block_names = {
        f.split("block ")[1].split("'")[1] for f in findings if "block " in f
    }
    assert block_names == {"universal", "python"}


@pytest.mark.unit
def test_no_pyproject_skips_python_block(tmp_path: Path) -> None:
    """Repo with no pyproject.toml only needs the universal block."""
    # No pyproject.toml, no package.json — plain repo
    _write_gitignore(tmp_path, _UNIVERSAL_BLOCK + "\n")

    findings = validate(tmp_path, _SPEC_PATH)

    assert findings == [], f"expected no findings for non-python repo, got {findings}"
