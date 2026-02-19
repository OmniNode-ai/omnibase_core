# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for validate-secrets.py validator.

Tests secret detection for:
- Hardcoded API keys, passwords, tokens
- Environment variable usage validation
- Bypass comment handling
- Various secret pattern detection

SECURITY NOTE:
This test file intentionally contains realistic-looking secrets (JWT tokens, API keys,
passwords, connection strings) as test fixtures. These are NOT real credentials - they
are synthetic test data used to verify that the secret validator correctly detects
secret patterns. The test tokens are either:
1. Publicly known test tokens from documentation (e.g., jwt.io example tokens)
2. Synthetic patterns that match secret formats but contain no actual secrets
3. Invalid signatures that cannot be used for authentication

Do NOT replace these with obviously fake values - the validator needs realistic
patterns to test its detection capabilities.
"""

import importlib.util

# Import the validator classes
from pathlib import Path

import pytest

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


@pytest.mark.unit
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

    # ===== API Key Detection Tests =====

    def test_detects_openai_api_key(self) -> None:
        """Test detection of OpenAI API key format."""
        code = """
OPENAI_API_KEY = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
openai_api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect OpenAI API key patterns"

    def test_detects_aws_access_key_akia_format(self) -> None:
        """Test detection of AWS AKIA format access keys."""
        code = """
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
aws_access_key = "AKIAJKLMNOPQRSTUVWXY"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect AWS AKIA format keys"

    def test_detects_generic_api_keys(self) -> None:
        """Test detection of generic API key patterns."""
        code = """
api_key = "api_key_1234567890abcdef"
API_KEY = "live_key_abcdefghijklmnop"
client_api_key = "prod-api-key-xyz123"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, "Should detect generic API key patterns"

    def test_detects_service_specific_keys(self) -> None:
        """Test detection of service-specific API keys."""
        # Using generic secret-like variable names with fake values
        code = """
STRIPE_API_KEY = "NOT_REAL_sk_test_1234567890abcdefghij"
GITHUB_API_TOKEN = "NOT_REAL_ghp_1234567890abcdefghij"
SENDGRID_API_SECRET = "NOT_REAL_SG_1234567890abcdefghij"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, "Should detect service-specific API keys"

    # ===== Password Detection Tests =====

    def test_detects_hardcoded_password_variations(self) -> None:
        """Test detection of various hardcoded password formats."""
        code = """
password = "actual_password_123"
PASSWORD = "MySecureP@ssw0rd!"
user_password = "p@ssw0rd123"
admin_password = "AdminPassword2024!"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 4, "Should detect various password formats"

    def test_detects_password_hash_values(self) -> None:
        """Test detection of hardcoded password hashes."""
        code = """
hashed_password = "5f4dcc3b5aa765d61d8327deb882cf99"
stored_password = "$2b$12$KIXxLVJHLf8EuyBJh6EK5eQ7kO6Q0X9Z1Y2W3V4U5T6R7S8O9P0"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect hardcoded password hashes"

    def test_detects_auth_password_in_config(self) -> None:
        """Test detection of passwords in configuration objects."""
        code = """
auth_password = "SuperSecret123!"
db_password = "database_password_xyz"
smtp_password = "smtp_p@ssw0rd"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, "Should detect passwords in configs"

    # ===== Token Detection Tests =====

    def test_detects_bearer_tokens(self) -> None:
        """Test detection of Bearer token patterns."""
        code = """
bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
authorization_token = "Bearer abc123xyz789def456"
auth_bearer_token = "Bearer token_1234567890abcdef"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, "Should detect Bearer token patterns"

    def test_detects_access_and_refresh_tokens(self) -> None:
        """Test detection of access and refresh tokens."""
        code = """
access_token = "at_1234567890abcdefghijklmnop"
refresh_token = "rt_0987654321fedcbazyxwvutsrq"
oauth_access_token = "ya29.a0AfH6SMBx..."
oauth_refresh_token = "1//0gK8..."
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 4, "Should detect access/refresh tokens"

    def test_detects_jwt_tokens(self) -> None:
        """Test detection of JWT tokens."""
        code = """
jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
auth_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect JWT tokens"

    # ===== Connection String Detection Tests =====

    def test_detects_postgresql_connection_strings(self) -> None:
        """Test detection of PostgreSQL connection strings with credentials."""
        code = """
DATABASE_URL = "postgresql://user:secretpass@localhost:5432/mydb"
postgres_database_url = "postgresql://admin:P@ssw0rd123@192.168.1.100:5432/production"
pg_connection_string = "postgres://dbuser:dbpass123@db.example.com/appdb"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, (
            "Should detect PostgreSQL connection strings"
        )

    def test_detects_redis_connection_strings(self) -> None:
        """Test detection of Redis connection strings with passwords."""
        code = """
redis_database_url = "redis://:my_redis_password@localhost:6379/0"
redis_connection_string = "redis://user:pass123@redis.example.com:6379/1"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect Redis connection strings"

    def test_detects_mongodb_connection_strings(self) -> None:
        """Test detection of MongoDB connection strings with credentials."""
        code = """
mongo_database_url = "mongodb://admin:mongopass123@localhost:27017/mydb"
mongodb_url = "mongodb+srv://user:password@cluster.mongodb.net/database"
mongo_connection_string = "mongodb://dbuser:dbpass@mongo.example.com:27017/prod"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        # Note: MongoDB connection strings will be detected because they contain
        # secret-like patterns (connection_string, database_url, etc.)
        assert len(validator.violations) == 3, (
            "Should detect MongoDB connection strings"
        )

    def test_detects_mysql_connection_strings(self) -> None:
        """Test detection of MySQL connection strings."""
        code = """
mysql_dsn = "mysql://root:mysqlpass@localhost:3306/mydb"
DATABASE_URL = "mysql+pymysql://user:password@db.example.com/database"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect MySQL connection strings"

    # ===== Private Key Detection Tests =====

    def test_detects_rsa_private_keys(self) -> None:
        """Test detection of RSA private key blocks."""
        code = '''
private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyz
-----END RSA PRIVATE KEY-----"""
rsa_key = "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA..."
'''
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect RSA private keys"

    def test_detects_ssh_private_keys(self) -> None:
        """Test detection of SSH private keys."""
        code = '''
ssh_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAAAdzc2gtcn
-----END OPENSSH PRIVATE KEY-----"""
SSH_PRIVATE_KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\\nb3BlbnNzaC1rZXktdjE..."
'''
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect SSH private keys"

    def test_detects_certificate_private_keys(self) -> None:
        """Test detection of certificate private keys."""
        code = '''
cert_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
-----END PRIVATE KEY-----"""
certificate_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG..."
tls_key = "-----BEGIN EC PRIVATE KEY-----\\nMHcCAQEEIIGN..."
'''
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 3, "Should detect certificate private keys"

    # ===== OAuth and Client Secret Detection Tests =====

    def test_detects_oauth_client_secrets(self) -> None:
        """Test detection of OAuth client secrets."""
        code = """
OAUTH_CLIENT_SECRET = "oauth_secret_1234567890abcdef"
client_secret = "cs_live_abcdefghijklmnopqrstuvwxyz123"
app_secret = "appsecret_1234567890abcdef"
consumer_secret = "consumer_secret_xyz789abc123"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 4, "Should detect OAuth client secrets"

    # ===== Encryption and Signing Key Detection Tests =====

    def test_detects_encryption_keys(self) -> None:
        """Test detection of hardcoded encryption keys."""
        code = """
encryption_key = "0123456789abcdef0123456789abcdef"
ENCRYPTION_KEY = "aes256_key_1234567890abcdefghijklmnop"
signing_key = "hmac_signing_key_xyz123abc456"
SECRET_KEY = "django-insecure-1234567890abcdefghijklmnopqrstuvwxyz"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 4, "Should detect encryption/signing keys"

    # ===== AWS Session Token Detection =====

    def test_detects_aws_session_tokens(self) -> None:
        """Test detection of AWS session tokens."""
        code = """
AWS_SESSION_TOKEN = "FwoGZXIvYXdzEBIaDH1234567890abcdefghij=="
aws_session_token = "AQoDYXdzEJr1234567890abcdefghijklmnop"
"""
        validator = PythonSecretValidator("test.py")
        import ast

        tree = ast.parse(code)
        validator.visit(tree)

        assert len(validator.violations) == 2, "Should detect AWS session tokens"


@pytest.mark.unit
class TestSecretValidator:
    """Test suite for SecretValidator."""

    def test_validates_clean_file(self, tmp_path: Path) -> None:
        """Test validation passes for file with no secrets."""
        test_file = tmp_path / "test_clean.py"
        test_file.write_text(
            """
import os

api_key = os.getenv("API_KEY")
password = os.getenv("PASSWORD")
""",
            encoding="utf-8",
        )

        validator = SecretValidator()
        with open(test_file, encoding="utf-8") as f:
            lines = f.readlines()
        result = validator.validate_python_file(test_file, lines)

        assert result is True
        assert len(validator.violations) == 0

    def test_detects_hardcoded_secret_in_file(self, tmp_path: Path) -> None:
        """Test validation fails for file with hardcoded secret."""
        test_file = tmp_path / "test_secret.py"
        test_file.write_text(
            """
api_key = "sk-1234567890abcdef"
""",
            encoding="utf-8",
        )

        validator = SecretValidator()
        with open(test_file, encoding="utf-8") as f:
            lines = f.readlines()
        result = validator.validate_python_file(test_file, lines)

        assert result is False
        assert len(validator.violations) == 1

    def test_bypass_comment_works(self, tmp_path: Path) -> None:
        """Test that bypass comment allows hardcoded secrets."""
        test_file = tmp_path / "test_bypass.py"
        test_file.write_text(
            """# secret-ok: test fixture
api_key = "sk-1234567890abcdef"
""",
            encoding="utf-8",
        )

        validator = SecretValidator()
        with open(test_file, encoding="utf-8") as f:
            lines = f.readlines()
        result = validator.validate_python_file(test_file, lines)

        assert result is True
        assert len(validator.violations) == 0

    def test_handles_empty_file_gracefully(self, tmp_path: Path) -> None:
        """Test that empty Python files are handled gracefully."""
        test_file = tmp_path / "test_empty.py"
        test_file.write_text("", encoding="utf-8")

        validator = SecretValidator()
        with open(test_file, encoding="utf-8") as f:
            lines = f.readlines()
        result = validator.validate_python_file(test_file, lines)

        # Should return True (empty files are valid)
        assert result is True
        assert len(validator.violations) == 0

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

        validator = SecretValidator()
        with open(test_file, encoding="utf-8") as f:
            lines = f.readlines()
        result = validator.validate_python_file(test_file, lines)

        # Should return True (skip files with syntax errors)
        assert result is True
