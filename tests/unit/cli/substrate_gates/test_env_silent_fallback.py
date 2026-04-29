# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for substrate_gates.env_silent_fallback — Gate 3."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.cli.substrate_gates.env_silent_fallback import EnvSilentFallbackGate


@pytest.fixture
def gate() -> EnvSilentFallbackGate:
    return EnvSilentFallbackGate()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixture-based: violation file → violations, clean file → empty
# ---------------------------------------------------------------------------


class TestFixtureFiles:
    def test_violation_file_produces_violations(
        self, gate: EnvSilentFallbackGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "env_violation.py"])
        assert len(violations) == 3, f"expected 3 violations, got {violations}"

    def test_clean_file_produces_no_violations(
        self, gate: EnvSilentFallbackGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "env_clean.py"])
        assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# Inline: each banned form detected individually
# ---------------------------------------------------------------------------


class TestVariant1EnvironGetWithDefault:
    def test_detects_environ_get_with_positional_default(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "v1.py"
        f.write_text('import os\nHOST = os.environ.get("HOST", "localhost")\n')
        violations = gate.run([f])
        assert len(violations) == 1
        assert "os.environ.get" in violations[0].message

    def test_detects_environ_get_with_keyword_default(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "v1kw.py"
        f.write_text('import os\nHOST = os.environ.get("HOST", default="localhost")\n')
        violations = gate.run([f])
        assert len(violations) == 1

    def test_allows_environ_get_no_default(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text('import os\nHOST = os.environ.get("HOST")\n')
        assert gate.run([f]) == []


class TestVariant2GetenvWithDefault:
    def test_detects_getenv_with_positional_default(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "v2.py"
        f.write_text('import os\nPORT = os.getenv("PORT", "8080")\n')
        violations = gate.run([f])
        assert len(violations) == 1
        assert "os.getenv" in violations[0].message

    def test_allows_getenv_no_default(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text('import os\nPORT = os.getenv("PORT")\n')
        assert gate.run([f]) == []


class TestVariant3BoolOpOr:
    def test_detects_environ_get_or_constant(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "v3.py"
        f.write_text('import os\nTIMEOUT = os.environ.get("TIMEOUT") or "30"\n')
        violations = gate.run([f])
        assert len(violations) == 1
        assert (
            "or" in violations[0].message.lower() or "BoolOp" in violations[0].message
        )

    def test_no_double_report_for_bool_or(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        """BoolOp Or case must not also trigger Variant 1 for the inner call."""
        f = tmp_path / "v3_no_dup.py"
        f.write_text('import os\nX = os.environ.get("X") or "default"\n')
        violations = gate.run([f])
        assert len(violations) == 1, f"expected exactly 1, got {violations}"


# ---------------------------------------------------------------------------
# Allow annotation suppression
# ---------------------------------------------------------------------------


class TestAllowAnnotation:
    def test_substrate_allow_suppresses_environ_get(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "suppressed.py"
        f.write_text(
            "import os\n"
            'DB = os.environ.get("DB", "sqlite://")  # substrate-allow: bootstrap-fallback\n'
        )
        assert gate.run([f]) == []

    def test_substrate_allow_suppresses_getenv(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "suppressed2.py"
        f.write_text(
            "import os\n"
            'DB = os.getenv("DB", "sqlite://")  # substrate-allow: bootstrap-fallback\n'
        )
        assert gate.run([f]) == []

    def test_substrate_allow_suppresses_bool_or(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "suppressed3.py"
        f.write_text(
            "import os\n"
            'X = os.environ.get("X") or "default"  # substrate-allow: bootstrap-fallback\n'
        )
        assert gate.run([f]) == []


# ---------------------------------------------------------------------------
# Allowed patterns — must never fire
# ---------------------------------------------------------------------------


class TestAllowedPatterns:
    def test_environ_key_access_allowed(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text('import os\nHOST = os.environ["HOST"]\n')
        assert gate.run([f]) == []

    def test_empty_file_allowed(
        self, gate: EnvSilentFallbackGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        assert gate.run([f]) == []

    def test_empty_paths_list(self, gate: EnvSilentFallbackGate) -> None:
        assert gate.run([]) == []
