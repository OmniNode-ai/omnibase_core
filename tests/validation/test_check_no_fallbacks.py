"""
Tests for check_no_fallbacks.py pre-commit hook.

Verifies that the hook correctly detects and prevents fallback patterns.
"""

import ast
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from check_no_fallbacks import (
    FallbackDetector,
    check_file_for_fallbacks,
)


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

    def test_allows_exception_with_logging(self):
        """Test that except with logging and return is allowed."""
        code = """
def safe_operation():
    try:
        return dangerous_call()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return None
"""
        tree = ast.parse(code)
        detector = FallbackDetector("test.py", code.splitlines())
        detector.visit(tree)

        # Should not detect violation because logging is present
        assert len(detector.violations) == 0


class TestCheckFileForFallbacks:
    """Tests for check_file_for_fallbacks function."""

    def test_checks_python_file_with_fallbacks(self):
        """Test checking a Python file containing fallback patterns."""
        code = """
class MyModel:
    def get_id(self) -> str:
        return f"{self.__class__.__name__}_{id(self)}"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            violations = check_file_for_fallbacks(filepath)
            assert len(violations) == 1
            assert violations[0]["type"] == "id_self_fallback"
        finally:
            filepath.unlink()

    def test_handles_syntax_errors_gracefully(self):
        """Test that syntax errors are handled gracefully."""
        code = """
def invalid_syntax(
    # Missing closing paren
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            violations = check_file_for_fallbacks(filepath)
            # Should return empty list, not crash
            assert violations == []
        finally:
            filepath.unlink()

    def test_returns_empty_for_clean_file(self):
        """Test that clean files return no violations."""
        code = """
class MyModel:
    def get_id(self) -> str:
        if hasattr(self, "uuid") and self.uuid:
            return str(self.uuid)
        raise ValueError("Model must have UUID field")
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            violations = check_file_for_fallbacks(filepath)
            assert violations == []
        finally:
            filepath.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
