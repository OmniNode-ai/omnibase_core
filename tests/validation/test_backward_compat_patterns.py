#!/usr/bin/env python3
"""
Test cases for backward compatibility pattern detection.

Tests regex patterns to ensure they catch all violations without false negatives.
"""

from __future__ import annotations

# Import the validation script by loading it directly
import importlib.util
import sys
import tempfile
from pathlib import Path

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


class TestExtraAllowPatterns:
    """Test detection of extra='allow' patterns for backward compatibility."""

    def _create_temp_file(self, content: str) -> Path:
        """Create a temporary Python file with given content."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(content)
            return Path(temp_file.name)

    def _validate_content(self, content: str) -> tuple[bool, list[str]]:
        """Validate content and return (success, errors)."""
        detector = BackwardCompatibilityDetector()
        temp_file = self._create_temp_file(content)
        try:
            success = detector.validate_python_file(temp_file)
            return success, detector.errors
        finally:
            temp_file.unlink()

    # --- SHOULD CATCH (False Negative Tests) ---

    def test_extra_allow_same_line_comment_after(self):
        """Should catch: extra='allow' with comment on same line after."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, (
            "Should detect extra='allow' with backward compatibility comment"
        )
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_same_line_comment_before(self):
        """Should catch: comment before extra='allow' on same line."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        # backward compatibility
        extra = 'allow'
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra='allow' with comment on line before"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_comment_line_above(self):
        """Should catch: comment on line above extra='allow'."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    # For backward compatibility with old versions
    class Config:
        extra = 'allow'
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra='allow' with comment above"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_backwards_with_s(self):
        """Should catch: 'backwards compatibility' (with 's')."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # backwards compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect 'backwards' (with s)"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_legacy_support(self):
        """Should catch: 'legacy support' in comment."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # legacy support
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect 'legacy support'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_compat_shorthand(self):
        """Should catch: 'compat' shorthand in comment."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # for compat
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect 'compat' shorthand"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_double_quotes(self):
        """Should catch: extra="allow" with double quotes."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = "allow"  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra with double quotes"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_no_spaces(self):
        """Should catch: extra='allow' with no spaces."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra='allow'  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra='allow' without spaces"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_space_before_value(self):
        """Should catch: extra= 'allow' with space before value."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra= 'allow'  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra= 'allow' with space before value"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_space_after_key(self):
        """Should catch: extra ='allow' with space after key."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra ='allow'  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect extra ='allow' with space after key"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_config_dict(self):
        """Should catch: ConfigDict(extra='allow') with compatibility comment."""
        content = """
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(extra='allow')  # backward compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect ConfigDict with extra='allow'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_config_dict_multiline(self):
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
        success, errors = self._validate_content(content)
        assert not success, "Should detect multiline ConfigDict with extra='allow'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_inline_comment_compat(self):
        """Should catch: inline comment with just 'compat'."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # compat
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect inline 'compat' comment"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_for_compatibility(self):
        """Should catch: 'for compatibility' phrase."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # for compatibility
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect 'for compatibility'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_migration_path(self):
        """Should catch: 'migration path' phrase."""
        content = """
from pydantic import BaseModel

class MyModel(BaseModel):
    class Config:
        extra = 'allow'  # migration path
"""
        success, errors = self._validate_content(content)
        assert not success, "Should detect 'migration path'"
        assert any("extra" in err.lower() for err in errors)

    def test_extra_allow_multiline_docstring(self):
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
        success, errors = self._validate_content(content)
        assert not success, (
            "Should detect compatibility in docstring with extra='allow'"
        )
        # May be caught by docstring check or extra pattern check

    # --- SHOULD NOT CATCH (False Positive Prevention) ---

    def test_extra_allow_legitimate_flexibility(self):
        """Should NOT catch: extra='allow' for legitimate flexibility (no compat mention)."""
        content = """
from pydantic import BaseModel

class DynamicConfig(BaseModel):
    \"\"\"Dynamic configuration that accepts arbitrary fields.\"\"\"
    class Config:
        extra = 'allow'  # Allow dynamic configuration fields
"""
        success, errors = self._validate_content(content)
        assert success, "Should NOT detect extra='allow' without compatibility keywords"

    def test_extra_forbid(self):
        """Should NOT catch: extra='forbid' even with compatibility comment."""
        content = """
from pydantic import BaseModel

class StrictModel(BaseModel):
    class Config:
        extra = 'forbid'  # No backward compatibility
"""
        success, errors = self._validate_content(content)
        assert success, "Should NOT detect extra='forbid'"

    def test_extra_ignore(self):
        """Should NOT catch: extra='ignore' without compatibility mention."""
        content = """
from pydantic import BaseModel

class FlexibleModel(BaseModel):
    class Config:
        extra = 'ignore'  # Ignore unknown fields
"""
        success, errors = self._validate_content(content)
        assert success, "Should NOT detect extra='ignore' without compat keywords"

    def test_no_extra_field(self):
        """Should NOT catch: Config without extra field."""
        content = """
from pydantic import BaseModel

class SimpleModel(BaseModel):
    class Config:
        validate_assignment = True
"""
        success, errors = self._validate_content(content)
        assert success, "Should NOT detect Config without extra field"

    def test_extra_in_unrelated_context(self):
        """Should NOT catch: 'extra' in different context."""
        content = """
def process_data(data: dict) -> dict:
    # Add extra fields for processing
    extra = data.get('allow', False)
    return {'extra': extra}
"""
        success, errors = self._validate_content(content)
        assert success, "Should NOT detect 'extra' in unrelated context"
