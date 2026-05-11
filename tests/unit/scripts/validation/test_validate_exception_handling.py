#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validate-exception-handling.py — exit-code enforcement (OMN-10836)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "validate_exception_handling",
    SCRIPTS_DIR / "validate-exception-handling.py",
)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot find validate-exception-handling.py at {SCRIPTS_DIR}")
_mod = importlib.util.module_from_spec(spec)
sys.modules["validate_exception_handling"] = _mod
# NOTE(OMN-10836): spec.loader is validated as non-None two lines above.
spec.loader.exec_module(_mod)  # type: ignore[union-attr]

ExceptionHandlingValidator = _mod.ExceptionHandlingValidator
main = _mod.main

pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


@pytest.mark.unit
class TestExceptionHandlingValidatorExitCode:
    """Verify that main() exits non-zero on violations without --strict."""

    def test_bare_except_exits_nonzero_by_default(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("try:\n    pass\nexcept:\n    pass\n")
        with patch.object(sys, "argv", ["validate-exception-handling.py", str(f)]):
            result = main()
        assert result == 1

    def test_clean_file_exits_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("def foo() -> None:\n    pass\n")
        with patch.object(sys, "argv", ["validate-exception-handling.py", str(f)]):
            result = main()
        assert result == 0

    def test_fallback_ok_suppresses_bare_except(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.py"
        f.write_text("try:\n    pass\nexcept:  # fallback-ok: intentional\n    pass\n")
        with patch.object(sys, "argv", ["validate-exception-handling.py", str(f)]):
            result = main()
        assert result == 0

    def test_base_exception_exits_nonzero_by_default(self, tmp_path: Path) -> None:
        f = tmp_path / "base.py"
        f.write_text("try:\n    pass\nexcept BaseException:\n    pass\n")
        with patch.object(sys, "argv", ["validate-exception-handling.py", str(f)]):
            result = main()
        assert result == 1

    def test_non_python_file_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("except:\n    pass\n")
        with patch.object(sys, "argv", ["validate-exception-handling.py", str(f)]):
            result = main()
        assert result == 0


@pytest.mark.unit
class TestExceptionHandlingValidatorLogic:
    """Unit tests for the validator's detection logic."""

    def test_bare_except_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "bare.py"
        f.write_text("try:\n    pass\nexcept:\n    pass\n")
        v = ExceptionHandlingValidator()
        assert not v.validate_file(f)
        assert len(v.errors) == 1
        assert "Bare except:" in v.errors[0][2]

    def test_base_exception_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "base.py"
        f.write_text("try:\n    pass\nexcept BaseException:\n    pass\n")
        v = ExceptionHandlingValidator()
        assert not v.validate_file(f)
        assert len(v.errors) == 1

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("try:\n    pass\nexcept ValueError:\n    raise\n")
        v = ExceptionHandlingValidator()
        assert v.validate_file(f)
        assert v.errors == []
