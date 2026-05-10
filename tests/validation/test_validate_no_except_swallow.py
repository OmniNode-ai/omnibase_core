# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validate_no_except_swallow.py (OMN-10817)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from validate_no_except_swallow import ExceptSwallowDetector, scan_python_source


class TestExceptSwallowDetector:
    """Tests for AST-based except-log-no-reraise detection."""

    def _detect(self, code: str) -> list[tuple[int, str]]:
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = ExceptSwallowDetector(source_lines)
        detector.visit(tree)
        return detector.violations

    def test_detects_exception_with_logger_no_reraise(self):
        code = """
try:
    do_something()
except Exception:
    logger.warning("something failed")
"""
        viols = self._detect(code)
        assert len(viols) == 1
        assert "except" in viols[0][1].lower() or viols[0][0] > 0

    def test_detects_except_base_exception_with_log(self):
        code = """
try:
    run()
except BaseException:
    logger.error("base exception caught")
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_logger_info_swallow(self):
        code = """
try:
    work()
except Exception as e:
    logger.info("caught: %s", e)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_logger_debug_swallow(self):
        code = """
try:
    work()
except Exception as e:
    logger.debug("suppressed error: %s", e)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_allows_reraise_after_log(self):
        code = """
try:
    work()
except Exception as e:
    logger.error("failed: %s", e)
    raise
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_reraise_new_exception_after_log(self):
        code = """
try:
    work()
except Exception as e:
    logger.warning("wrapping error")
    raise RuntimeError("wrapped") from e
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_narrow_exception_with_log(self):
        """ValueError is not Exception/BaseException — should not be flagged."""
        code = """
try:
    work()
except ValueError as e:
    logger.warning("value error: %s", e)
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_except_no_logger(self):
        """Swallowing without logging is a different problem — not this validator's scope."""
        code = """
try:
    work()
except Exception:
    pass
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_reraise_ok_annotation(self):
        code = """
try:
    work()
except Exception:  # reraise-ok: intentional suppression for legacy compatibility
    logger.warning("suppressed")
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_detects_multiple_violations(self):
        code = """
def a():
    try:
        x()
    except Exception:
        logger.warning("x failed")

def b():
    try:
        y()
    except BaseException:
        logger.error("y failed")
"""
        viols = self._detect(code)
        assert len(viols) == 2

    def test_no_false_positive_for_non_handler_log(self):
        """Logger call outside except block should not trigger."""
        code = """
logger.info("starting work")
try:
    do_work()
except ValueError:
    pass
"""
        viols = self._detect(code)
        assert len(viols) == 0


class TestScanPythonSource:
    """Integration tests for scan_python_source (file-level)."""

    def test_scan_clean_source(self, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text(
            """
try:
    run()
except Exception as e:
    logger.error("failed")
    raise
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []

    def test_scan_violating_source(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text(
            """
try:
    run()
except Exception as e:
    logger.warning("suppressed: %s", e)
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert len(viols) == 1

    def test_scan_skips_test_files(self, tmp_path: Path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        f = tests_dir / "test_something.py"
        f.write_text(
            """
try:
    run()
except Exception as e:
    logger.warning("ignored in tests")
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []
