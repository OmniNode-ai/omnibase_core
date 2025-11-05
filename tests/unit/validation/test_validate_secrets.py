"""
Unit tests for validate-secrets.py validator.

Tests secret detection for:
- Hardcoded API keys, passwords, tokens
- Environment variable usage validation
- Bypass comment handling
- Various secret pattern detection
"""

import tempfile
from pathlib import Path

import pytest

# Import the validator classes
import sys
import importlib.util

# Load the validator module dynamically (script uses hyphens in filename)
_validator_path = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "validation"
    / "validate-secrets.py"
)
_spec = importlib.util.spec_from_file_location("validate_secrets", _validator_path)
_validator_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator_module)

PythonSecretValidator = _validator_module.PythonSecretValidator
SecretValidator = _validator_module.SecretValidator


class TestPythonSecretValidator:
    """Test suite for PythonSecretValidator AST visitor."""

    def test_detects_hardcoded_api_key(self) -> None:
        """Test detection of hardcoded API key."""
        code = """
api_key = "sk-1234567890abcdef"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].secret_name == "api_key"
        assert validator.violations[0].violation_type == "hardcoded_secret"

    def test_detects_hardcoded_password(self) -> None:
        """Test detection of hardcoded password."""
        code = """
password = "super_secret_123"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].secret_name == "password"

    def test_detects_hardcoded_token(self) -> None:
        """Test detection of hardcoded token."""
        code = """
auth_token = "Bearer abc123xyz"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].secret_name == "auth_token"

    def test_allows_env_var_access_getenv(self) -> None:
        """Test that os.getenv() usage is allowed."""
        code = """
import os
api_key = os.getenv("API_KEY")
password = os.getenv("PASSWORD", "default")
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_env_var_access_environ(self) -> None:
        """Test that os.environ access is allowed."""
        code = """
import os
api_key = os.environ.get("API_KEY")
password = os.environ["PASSWORD"]
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_config_service(self) -> None:
        """Test that config service usage is allowed."""
        code = """
config = container.get_service("ProtocolConfig")
api_key = config.get("api_key")
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_empty_strings(self) -> None:
        """Test that empty strings are ignored."""
        code = """
api_key = ""
password = ""
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_placeholder_values(self) -> None:
        """Test that placeholder values are ignored."""
        code = """
api_key = "YOUR_KEY_HERE"
password = "CHANGEME"
secret = "TODO"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_short_values(self) -> None:
        """Test that very short values (<3 chars) are ignored."""
        code = """
api_key = "ab"
password = "x"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_exception_patterns(self) -> None:
        """Test that exception patterns are ignored."""
        code = """
password_field = "user_password"
password_validator = SomeValidator()
token_type = "Bearer"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_detects_aws_credentials(self) -> None:
        """Test detection of AWS credentials."""
        code = """
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2

    def test_detects_database_url(self) -> None:
        """Test detection of hardcoded database URL."""
        code = """
database_url = "postgresql://user:pass@localhost/db"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].secret_name == "database_url"

    def test_detects_client_secret(self) -> None:
        """Test detection of OAuth client secret."""
        code = """
client_secret = "abc123xyz789"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1

    def test_detects_keyword_arguments(self) -> None:
        """Test detection in keyword arguments."""
        code = """
def connect_to_api():
    client = APIClient(api_key="hardcoded_key_123")
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1


class TestSecretValidator:
    """Test suite for SecretValidator."""

    def test_validates_clean_file(self) -> None:
        """Test validation passes for file with no secrets."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(
                """
import os

api_key = os.getenv("API_KEY")
password = os.getenv("PASSWORD")
"""
            )
            tmp_path = Path(tmp.name)

        try:
            validator = SecretValidator()
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            result = validator.validate_python_file(tmp_path, lines)

            assert result is True
            assert len(validator.violations) == 0
        finally:
            tmp_path.unlink()

    def test_detects_hardcoded_secret_in_file(self) -> None:
        """Test validation fails for file with hardcoded secret."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(
                """
api_key = "sk-1234567890abcdef"
"""
            )
            tmp_path = Path(tmp.name)

        try:
            validator = SecretValidator()
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            result = validator.validate_python_file(tmp_path, lines)

            assert result is False
            assert len(validator.violations) == 1
        finally:
            tmp_path.unlink()

    def test_bypass_comment_works(self) -> None:
        """Test that bypass comment allows hardcoded secrets."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(
                """# secret-ok: test fixture
api_key = "sk-1234567890abcdef"
"""
            )
            tmp_path = Path(tmp.name)

        try:
            validator = SecretValidator()
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            result = validator.validate_python_file(tmp_path, lines)

            assert result is True
            assert len(validator.violations) == 0
        finally:
            tmp_path.unlink()

    def test_handles_empty_file_gracefully(self) -> None:
        """Test that empty Python files are handled gracefully."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write("")
            tmp_path = Path(tmp.name)

        try:
            validator = SecretValidator()
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            result = validator.validate_python_file(tmp_path, lines)

            # Should return True (empty files are valid)
            assert result is True
            assert len(validator.violations) == 0
        finally:
            tmp_path.unlink()

    def test_handles_syntax_errors_gracefully(self) -> None:
        """Test that files with syntax errors are skipped."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(
                """
def broken_syntax(
    # Missing closing parenthesis
"""
            )
            tmp_path = Path(tmp.name)

        try:
            validator = SecretValidator()
            with open(tmp_path, encoding="utf-8") as f:
                lines = f.readlines()
            result = validator.validate_python_file(tmp_path, lines)

            # Should return True (skip files with syntax errors)
            assert result is True
        finally:
            tmp_path.unlink()
