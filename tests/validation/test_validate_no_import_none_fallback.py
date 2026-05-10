# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validate_no_import_none_fallback.py (OMN-10819)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from validate_no_import_none_fallback import (
    ImportNoneFallbackDetector,
    scan_python_source,
)


class TestImportNoneFallbackDetector:
    """Tests for ImportError-assigned-to-None detection."""

    def _detect(self, code: str) -> list[tuple[int, str]]:
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ImportNoneFallbackDetector(source_lines)
        detector.visit(tree)
        return detector.violations

    def test_detects_basic_import_none_fallback(self):
        code = """
try:
    from foo import Bar
except ImportError:
    Bar = None
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_multi_assignment_none_fallback(self):
        code = """
try:
    from foo import Baz, Qux
except ImportError:
    Baz = None
    Qux = None
"""
        viols = self._detect(code)
        assert len(viols) == 2

    def test_detects_import_error_or_module_not_found(self):
        code = """
try:
    import optional_lib
except (ImportError, ModuleNotFoundError):
    optional_lib = None
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_allows_import_fallback_ok_annotation(self):
        code = """
try:
    from foo import Bar
except ImportError:
    Bar = None  # import-fallback-ok: optional dependency for legacy compat
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_import_error_with_raise(self):
        code = """
try:
    from foo import Bar
except ImportError as e:
    raise RuntimeError("foo is required") from e
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_import_error_with_fallback_class(self):
        """Assigning to a real fallback class (not None) is fine."""
        code = """
try:
    from fast_impl import Parser
except ImportError:
    from slow_impl import Parser
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_import_error_with_false_constant(self):
        """Assigning to False or empty string is a different pattern — not this check."""
        code = """
try:
    import optional
except ImportError:
    optional = False
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_non_import_error_except_none(self):
        """Only ImportError / ModuleNotFoundError trigger the rule."""
        code = """
try:
    result = compute()
except ValueError:
    result = None
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_detects_module_not_found_error_alone(self):
        code = """
try:
    import numpy as np
except ModuleNotFoundError:
    np = None
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_no_false_positive_import_without_except(self):
        code = """
from foo import Bar
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_detects_violation_reports_correct_line(self):
        code = """
try:
    from foo import Bar
except ImportError:
    Bar = None
"""
        viols = self._detect(code)
        assert len(viols) == 1
        lineno, _ = viols[0]
        assert lineno == 5


class TestScanPythonSource:
    def test_scan_violating_source(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text(
            """
try:
    from foo import Bar
except ImportError:
    Bar = None
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert len(viols) == 1

    def test_scan_clean_source(self, tmp_path: Path):
        f = tmp_path / "ok.py"
        f.write_text(
            """
try:
    from foo import Bar
except ImportError as e:
    raise RuntimeError("foo required") from e
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []

    def test_scan_skips_test_files(self, tmp_path: Path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        f = tests_dir / "test_x.py"
        f.write_text(
            """
try:
    from foo import Bar
except ImportError:
    Bar = None
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []
