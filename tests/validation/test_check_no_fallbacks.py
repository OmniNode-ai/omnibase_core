# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for check_no_fallbacks.py pre-commit hook.

Verifies that the hook correctly detects and prevents fallback patterns.
"""

import ast
import sys
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from check_no_fallbacks import FallbackDetector, check_file_for_fallbacks


class TestFallbackDetector:
    """Tests for FallbackDetector AST visitor."""

    def test_detects_id_self_fallback(self):
        """Test detection of id(self) in get_id() methods."""
        code = """
class MyModel:
    def get_id(self) -> str:
        for field in ["id", "uuid"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        violation = detector.violations[0]
        assert violation["type"] == "id_self_fallback"
        assert "non-deterministic" in violation["message"]

    def test_detects_validator_field_fallback(self):
        """Test detection of if 'field' in info.data patterns."""
        code = """
from pydantic import field_validator, ValidationInfo

class MyModel:
    @field_validator("max_value")
    @classmethod
    def validate_max(cls, v, info: ValidationInfo) -> int:
        if "base_value" in info.data and v <= info.data["base_value"]:
            raise ValueError("max must be > base")
        return v
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        violation = detector.violations[0]
        assert violation["type"] == "validator_field_fallback"
        assert "model_validator" in violation["message"]

    def test_detects_enum_unknown_fallback(self):
        """Test detection of enum UNKNOWN assignment in except blocks."""
        code = """
from enum import Enum

class MyEnum(Enum):
    VALUE1 = "value1"
    UNKNOWN = "unknown"

def process(value: str):
    try:
        result = MyEnum(value)
    except ValueError:
        result = MyEnum.UNKNOWN
    return result
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        violation = detector.violations[0]
        assert violation["type"] == "enum_fallback"
        assert "UNKNOWN" in violation["message"]

    def test_detects_silent_exception_return(self):
        """Test detection of return in except without logging."""
        code = """
def risky_operation():
    try:
        return dangerous_call()
    except Exception:
        return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        violation = detector.violations[0]
        assert violation["type"] == "silent_exception_return"
        assert "swallows errors" in violation["message"]

    def test_allows_fallback_ok_comment(self):
        """Test that fallback-ok comment allows fallback patterns."""
        code = """
class MyModel:
    def get_id(self) -> str:
        for field in ["id", "uuid"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"  # fallback-ok: legacy compatibility
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        # Should not detect violation due to fallback-ok comment
        assert len(detector.violations) == 0

    def test_allows_exception_with_reraise(self):
        """Test that except with re-raise is allowed."""
        code = """
def safe_operation():
    try:
        return dangerous_call()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        # Should not detect violation because exception is re-raised
        assert len(detector.violations) == 0

    def test_detects_except_log_no_reraise(self):
        """Test that except with logging but no re-raise is a violation (pattern 9)."""
        code = """
def unsafe_operation():
    try:
        return dangerous_call()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "except_log_no_reraise"

    def test_allows_exception_with_logging_and_reraise(self):
        """Test that except with logging AND re-raise is allowed."""
        code = """
def safe_operation():
    try:
        return dangerous_call()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 6: injectable_none_default ---

    def test_detects_injectable_none_default(self):
        """Test detection of injectable param = None in __init__."""
        code = """
class MyHandler:
    def __init__(self, event_bus=None, other_arg="value"):
        self._event_bus = event_bus
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "injectable_none_default"
        assert "event_bus" in detector.violations[0]["message"]

    def test_allows_injectable_none_default_with_suppression(self):
        """Test that fallback-ok suppresses injectable_none_default."""
        code = """
class MyHandler:
    def __init__(self, event_bus=None):  # fallback-ok: test harness only
        self._event_bus = event_bus
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_non_injectable_none_default(self):
        """Test that non-injectable params with None default are not flagged."""
        code = """
class MyHandler:
    def __init__(self, timeout=None, retries=None):
        self.timeout = timeout
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 7: none_guard_publish_skip ---

    def test_detects_none_guard_publish_skip(self):
        """Test detection of 'if self._event_bus is not None: publish(...)' pattern."""
        code = """
class MyHandler:
    def handle(self, event):
        if self._event_bus is not None:
            self._event_bus.publish(event)
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "none_guard_publish_skip"

    def test_allows_none_guard_publish_with_suppression(self):
        """Test that fallback-ok suppresses none_guard_publish_skip."""
        code = """
class MyHandler:
    def handle(self, event):
        if self._event_bus is not None:  # fallback-ok: optional bus in tests
            self._event_bus.publish(event)
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 8: import_error_none_assignment ---

    def test_detects_import_error_none_assignment(self):
        """Test detection of 'except ImportError: x = None' pattern."""
        code = """
try:
    import optional_lib
except ImportError:
    optional_lib = None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "import_error_none_assignment"

    def test_allows_import_error_none_with_suppression(self):
        """Test that fallback-ok suppresses import_error_none_assignment."""
        code = """
try:
    import optional_lib
except ImportError:
    optional_lib = None  # fallback-ok: optional dependency for extra features
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 9: except_log_no_reraise (already tested above, add clean case) ---

    def test_allows_narrow_except_with_log_no_reraise(self):
        """Test that narrow except (not Exception/BaseException) with log is allowed."""
        code = """
def safe_operation():
    try:
        return parse_value()
    except ValueError as e:
        logger.warning(f"Bad value: {e}")
        return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 10: or_chain_degradation ---

    def test_detects_or_chain_degradation(self):
        """Test detection of x or y or z with multiple call nodes."""
        code = """
def get_handler():
    return primary_dispatch() or fallback_dispatch() or default_handler()
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 1
        assert detector.violations[0]["type"] == "or_chain_degradation"

    def test_allows_or_chain_with_suppression(self):
        """Test that fallback-ok suppresses or_chain_degradation."""
        code = """
def get_handler():
    return primary_dispatch() or fallback_dispatch() or default_handler()  # fallback-ok: intentional priority chain
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    def test_allows_short_or_chain(self):
        """Test that 2-value or-chain with calls is not flagged."""
        code = """
def get_value():
    return primary() or fallback()
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        assert len(detector.violations) == 0

    # --- Pattern 11: nested_try_fallback_chain ---

    def test_detects_nested_try_fallback_chain(self):
        """Test detection of try/except inside an except handler body."""
        code = """
def risky():
    try:
        return primary()
    except Exception:
        try:
            return fallback()
        except Exception:
            return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        violations_of_type = [
            v for v in detector.violations if v["type"] == "nested_try_fallback_chain"
        ]
        assert len(violations_of_type) >= 1

    def test_allows_nested_try_with_suppression(self):
        """Test that fallback-ok suppresses nested_try_fallback_chain."""
        code = """
def risky():
    try:
        return primary()
    except Exception:
        try:  # fallback-ok: cleanup must not propagate
            return fallback()
        except Exception:
            return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        violations_of_type = [
            v for v in detector.violations if v["type"] == "nested_try_fallback_chain"
        ]
        assert len(violations_of_type) == 0


class TestCheckFileForFallbacks:
    """Tests for check_file_for_fallbacks function."""

    def test_checks_python_file_with_fallbacks(self, tmp_path: Path):
        """Test checking a Python file containing fallback patterns."""
        code = """
class MyModel:
    def get_id(self) -> str:
        return f"{self.__class__.__name__}_{id(self)}"
"""
        filepath = tmp_path / "test_fallback.py"
        filepath.write_text(code, encoding="utf-8")

        violations = check_file_for_fallbacks(filepath)
        assert len(violations) == 1
        assert violations[0]["type"] == "id_self_fallback"

    def test_handles_syntax_errors_gracefully(self, tmp_path: Path):
        """Test that syntax errors are handled gracefully."""
        code = """
def invalid_syntax(
    # Missing closing paren
"""
        filepath = tmp_path / "test_syntax_error.py"
        filepath.write_text(code, encoding="utf-8")

        violations = check_file_for_fallbacks(filepath)
        # Should return empty list, not crash
        assert violations == []

    def test_returns_empty_for_clean_file(self, tmp_path: Path):
        """Test that clean files return no violations."""
        code = """
class MyModel:
    def get_id(self) -> str:
        if hasattr(self, "uuid") and self.uuid:
            return str(self.uuid)
        raise ValueError("Model must have UUID field")
"""
        filepath = tmp_path / "test_clean.py"
        filepath.write_text(code, encoding="utf-8")

        violations = check_file_for_fallbacks(filepath)
        assert violations == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
