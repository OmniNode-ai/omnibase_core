#!/usr/bin/env python3
"""
Test cases for backward compatibility pattern detection.

Tests regex patterns to ensure they catch all violations without false negatives.
"""

from __future__ import annotations

# Import the validation script by loading it directly
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "validation"
    / "validate-no-backward-compatibility.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_no_backward_compatibility", SCRIPT_PATH
)
if spec and spec.loader:
    validate_module = importlib.util.module_from_spec(spec)
    sys.modules["validate_no_backward_compatibility"] = validate_module
    spec.loader.exec_module(validate_module)
    BackwardCompatibilityDetector = validate_module.BackwardCompatibilityDetector
else:
    raise ImportError(f"Could not load validation script from {SCRIPT_PATH}")


@pytest.fixture
def temp_py_file(tmp_path: Path):
    """Factory fixture to create temporary Python files."""

    def _create(content: str) -> Path:
        file_path = tmp_path / "test_file.py"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create


class TestExtraAllowPatterns:
    """Test detection of extra='allow' patterns for backward compatibility."""

    def _validate_content(self, content: str, temp_py_file) -> tuple[bool, list[str]]:
        """Validate content and return (success, errors)."""
        detector = BackwardCompatibilityDetector()
        temp_file = temp_py_file(content)
        success = detector.validate_python_file(temp_file)
        return success, detector.errors

    # --- SHOULD CATCH (False Negative Tests) ---

    def test_extra_allow_same_line_comment_after(self, temp_py_file):
        """Should catch: extra='allow' with comment on same line after."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, (
            "Should detect extra='allow' with backward compatibility comment"
        )
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_same_line_comment_before(self, temp_py_file):
        """Should catch: comment before extra='allow' on same line."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        # backward compatibility
        extra = 'allow'
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra='allow' with comment on line before"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_comment_line_above(self, temp_py_file):
        """Should catch: comment on line above extra='allow'."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    # For backward compatibility with old versions
    class Config:
        extra = 'allow'
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra='allow' with comment above"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_backwards_with_s(self, temp_py_file):
        """Should catch: 'backwards compatibility' (with 's')."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # backwards compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect 'backwards' (with s)"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_legacy_support(self, temp_py_file):
        """Should catch: 'legacy support' in comment."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # legacy support
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect 'legacy support'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_compat_shorthand(self, temp_py_file):
        """Should catch: 'compat' shorthand in comment."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # for compat
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect 'compat' shorthand"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_double_quotes(self, temp_py_file):
        """Should catch: extra="allow" with double quotes."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = "allow"  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra with double quotes"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_no_spaces(self, temp_py_file):
        """Should catch: extra='allow' with no spaces."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra='allow'  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra='allow' without spaces"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_space_before_value(self, temp_py_file):
        """Should catch: extra= 'allow' with space before value."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra= 'allow'  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra= 'allow' with space before value"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_space_after_key(self, temp_py_file):
        """Should catch: extra ='allow' with space after key."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra ='allow'  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect extra ='allow' with space after key"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_config_dict(self, temp_py_file):
        """Should catch: ConfigDict(extra='allow') with compatibility comment."""
        content = """
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(extra='allow')  # backward compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect ConfigDict with extra='allow'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_config_dict_multiline(self, temp_py_file):
        """Should catch: ConfigDict with extra='allow' on separate line."""
        content = """
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    # Backward compatibility with old API
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True
    )
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect multiline ConfigDict with extra='allow'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_inline_comment_compat(self, temp_py_file):
        """Should catch: inline comment with just 'compat'."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # compat
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect inline 'compat' comment"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_for_compatibility(self, temp_py_file):
        """Should catch: 'for compatibility' phrase."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # for compatibility
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect 'for compatibility'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_migration_path(self, temp_py_file):
        """Should catch: 'migration path' phrase."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # migration path
"""
        success, errors = self._validate_content(content, temp_py_file)
        assert not success, "Should detect 'migration path'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_multiline_docstring(self, temp_py_file):
        """Should catch: compatibility mention in class docstring."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    \"\"\"Model with backward compatibility.

    Uses extra='allow' for backward compatibility.
    \"\"\"
    class Config:
        extra = 'allow'
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert not success, (
            "Should detect compatibility in docstring with extra='allow'"
        )
        # May be caught by docstring check or extra pattern check

    # --- SHOULD NOT CATCH (False Positive Prevention) ---

    def test_extra_allow_legitimate_flexibility(self, temp_py_file):
        """Should NOT catch: extra='allow' for legitimate flexibility (no compat mention)."""
        content = """
from pydantic import BaseModel

class DynamicConfig(BaseModel):
    \"\"\"Dynamic configuration that accepts arbitrary fields.\"\"\"
    class Config:
        extra = 'allow'  # Allow dynamic configuration fields
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert success, "Should NOT detect extra='allow' without compatibility keywords"

    def test_extra_forbid(self, temp_py_file):
        """Should NOT catch: extra='forbid' even with compatibility comment."""
        content = """
from pydantic import BaseModel

class StrictModel(BaseModel):
    class Config:
        extra = 'forbid'  # No backward compatibility
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert success, "Should NOT detect extra='forbid'"

    def test_extra_ignore(self, temp_py_file):
        """Should NOT catch: extra='ignore' without compatibility mention."""
        content = """
from pydantic import BaseModel

class FlexibleModel(BaseModel):
    class Config:
        extra = 'ignore'  # Ignore unknown fields
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert success, "Should NOT detect extra='ignore' without compat keywords"

    def test_no_extra_field(self, temp_py_file):
        """Should NOT catch: Config without extra field."""
        content = """
from pydantic import BaseModel

class SimpleModel(BaseModel):
    class Config:
        validate_assignment = True
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert success, "Should NOT detect Config without extra field"

    def test_extra_in_unrelated_context(self, temp_py_file):
        """Should NOT catch: 'extra' in different context."""
        content = """
def process_data(data: dict) -> dict:
    # Add extra fields for processing
    extra = data.get('allow', False)
    return {'extra': extra}
"""
        success, _ = self._validate_content(content, temp_py_file)
        assert success, "Should NOT detect 'extra' in unrelated context"
