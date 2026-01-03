"""
Unit tests for validate-hardcoded-env-vars.py validator.

Tests hardcoded environment variable detection for:
- UPPER_CASE variable assignments
- Environment variable access patterns
- Constant vs environment variable distinction
- Bypass comment handling
"""

import importlib.util
from pathlib import Path

import pytest

# Load the validator module dynamically (script uses hyphens in filename)
_validator_path = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "validation"
    / "validate-hardcoded-env-vars.py"
)
_spec = importlib.util.spec_from_file_location(
    "validate_hardcoded_env_vars", _validator_path
)
_validator_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator_module)

HardcodedEnvVarValidator = _validator_module.HardcodedEnvVarValidator
PythonEnvVarValidator = _validator_module.PythonEnvVarValidator


@pytest.mark.unit
class TestPythonEnvVarValidator:
    """Test suite for PythonEnvVarValidator AST visitor."""

    def test_detects_hardcoded_database_url(self) -> None:
        """Test detection of hardcoded DATABASE_URL."""
        code = """
DATABASE_URL = "postgresql://localhost/mydb"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].var_name == "DATABASE_URL"

    def test_detects_hardcoded_api_endpoint(self) -> None:
        """Test detection of hardcoded API_ENDPOINT."""
        code = """
API_ENDPOINT = "https://api.example.com"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].var_name == "API_ENDPOINT"

    def test_detects_hardcoded_port(self) -> None:
        """Test detection of hardcoded PORT."""
        code = """
PORT = 8000
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].var_name == "PORT"

    def test_detects_hardcoded_debug(self) -> None:
        """Test detection of hardcoded DEBUG."""
        code = """
DEBUG = True
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1
        assert validator.violations[0].var_name == "DEBUG"

    def test_allows_getenv_usage(self) -> None:
        """Test that os.getenv() usage is allowed."""
        code = """
import os
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", "8000"))
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_environ_get(self) -> None:
        """Test that os.environ.get() is allowed."""
        code = """
import os
API_KEY = os.environ.get("API_KEY")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_environ_subscript(self) -> None:
        """Test that os.environ["KEY"] is allowed."""
        code = """
import os
DATABASE_URL = os.environ["DATABASE_URL"]
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_config_service(self) -> None:
        """Test that config service usage is allowed."""
        code = """
DATABASE_URL = config.get("DATABASE_URL")
PORT = settings.PORT
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_lowercase_constants(self) -> None:
        """Test that lowercase constants are allowed."""
        code = """
default_timeout = 30
max_retries = 3
api_version = "v1"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_mixed_case_variables(self) -> None:
        """Test that mixed case variables are allowed."""
        code = """
DatabaseUrl = "postgresql://localhost/db"
apiEndpoint = "https://api.example.com"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_allows_none_values(self) -> None:
        """Test that None values are allowed (placeholders)."""
        code = """
DATABASE_URL = None
API_KEY = None
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_http_status_constants(self) -> None:
        """Test that HTTP status code constants are ignored."""
        code = """
HTTP_OK = 200
HTTP_NOT_FOUND = 404
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_default_constants(self) -> None:
        """Test that DEFAULT_* constants are ignored."""
        code = """
DEFAULT_TIMEOUT = 30
DEFAULT_PORT = 8000
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_ignores_max_min_constants(self) -> None:
        """Test that MAX_* and MIN_* constants are ignored."""
        code = """
MAX_RETRIES = 5
MIN_LENGTH = 3
MAX_LENGTH = 100
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 0

    def test_detects_kafka_config(self) -> None:
        """Test detection of hardcoded Kafka configuration."""
        code = """
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "my-topic"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2

    def test_detects_redis_url(self) -> None:
        """Test detection of hardcoded Redis URL."""
        code = """
REDIS_URL = "redis://localhost:6379"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1

    def test_detects_aws_config(self) -> None:
        """Test detection of hardcoded AWS configuration."""
        code = """
AWS_REGION = "us-east-1"
AWS_BUCKET = "my-bucket"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2

    def test_detects_cors_origins(self) -> None:
        """Test detection of hardcoded CORS origins."""
        code = """
CORS_ORIGINS = ["http://localhost:3000", "https://example.com"]
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1

    def test_detects_allowed_hosts(self) -> None:
        """Test detection of hardcoded allowed hosts."""
        code = """
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 1

    def test_ignores_enum_members(self) -> None:
        """Test that Enum class members are not flagged."""
        code = """
from enum import Enum

class StatusEnum(Enum):
    PENDING_KEY = "pending"
    ACTIVE_KEY = "active"
    COMPLETED_KEY = "completed"

class ConfigEnum(Enum):
    DATABASE_URL = "db_url_field"
    API_KEY = "api_key_field"
"""
        validator = PythonEnvVarValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        # Enum members should not be flagged as env vars
        assert len(validator.violations) == 0


@pytest.mark.unit
class TestHardcodedEnvVarValidator:
    """Test suite for HardcodedEnvVarValidator."""

    def test_validates_clean_file(self, tmp_path: Path) -> None:
        """Test validation passes for file with proper env var usage."""
        test_file = tmp_path / "test_clean.py"
        test_file.write_text(
            """
import os

DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", "8000"))
""",
            encoding="utf-8",
        )

        validator = HardcodedEnvVarValidator()
        result = validator.validate_python_file(test_file)

        assert result is True
        assert len(validator.violations) == 0

    def test_detects_hardcoded_env_var_in_file(self, tmp_path: Path) -> None:
        """Test validation fails for file with hardcoded env var."""
        test_file = tmp_path / "test_hardcoded.py"
        test_file.write_text(
            """
DATABASE_URL = "postgresql://localhost/mydb"
""",
            encoding="utf-8",
        )

        validator = HardcodedEnvVarValidator()
        result = validator.validate_python_file(test_file)

        assert result is False
        assert len(validator.violations) == 1

    def test_bypass_comment_works(self, tmp_path: Path) -> None:
        """Test that bypass comment allows hardcoded env vars."""
        test_file = tmp_path / "test_bypass.py"
        test_file.write_text(
            """# env-var-ok: constant definition
DATABASE_URL = "postgresql://localhost/mydb"
""",
            encoding="utf-8",
        )

        validator = HardcodedEnvVarValidator()
        result = validator.validate_python_file(test_file)

        assert result is True
        assert len(validator.violations) == 0

    def test_validates_multiple_files(self, tmp_path: Path) -> None:
        """Test validation of multiple files."""
        # Create two temp files
        tmp1_path = tmp_path / "test_file1.py"
        tmp1_path.write_text(
            """
import os

DATABASE_URL = os.getenv("DATABASE_URL")
""",
            encoding="utf-8",
        )

        tmp2_path = tmp_path / "test_file2.py"
        tmp2_path.write_text(
            """
API_KEY = "hardcoded_key"
""",
            encoding="utf-8",
        )

        validator = HardcodedEnvVarValidator()
        result1 = validator.validate_python_file(tmp1_path)
        result2 = validator.validate_python_file(tmp2_path)

        assert result1 is True
        assert result2 is False
        assert len(validator.violations) == 1

    def test_handles_syntax_errors_gracefully(self, tmp_path: Path) -> None:
        """Test that files with syntax errors are skipped."""
        test_file = tmp_path / "test_syntax_error.py"
        test_file.write_text(
            """
def broken_syntax(
    # Missing closing parenthesis
""",
            encoding="utf-8",
        )

        validator = HardcodedEnvVarValidator()
        result = validator.validate_python_file(test_file)

        # Should return True (skip files with syntax errors)
        assert result is True
