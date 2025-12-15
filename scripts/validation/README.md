# ONEX Security Validators

This directory contains security validators that enforce best practices for secret management and environment variable configuration in the ONEX framework.

---

## Table of Contents

1. [Overview](#overview)
2. [Validators](#validators)
   - [Secret Validator](#secret-validator)
   - [Environment Variable Validator](#environment-variable-validator)
3. [Usage](#usage)
4. [Bypass Mechanisms](#bypass-mechanisms)
5. [Detection Details](#detection-details)
6. [Configuration](#configuration)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Security validators prevent common anti-patterns that can lead to security vulnerabilities:

- **Hardcoded Secrets**: API keys, passwords, tokens, and credentials should never be committed to source code
- **Hardcoded Configuration**: Environment-specific values (URLs, ports, etc.) should be loaded from environment variables

Both validators use **AST (Abstract Syntax Tree) parsing** for reliable, context-aware detection that minimizes false positives.

### Why These Matter

❌ **WRONG** (Security Risk):
```python
# Secrets exposed in source code
api_key = "sk-1234567890abcdef"
database_url = "postgresql://user:password@localhost/db"
PORT = 8000  # Hardcoded instead of configurable
```

✅ **CORRECT** (Secure Pattern):
```python
import os

# Load secrets from environment
api_key = os.getenv("API_KEY")
database_url = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", "8000"))
```

---

## Validators

### Secret Validator

**File**: `validate-secrets.py`

**Purpose**: Detects hardcoded secrets (passwords, API keys, tokens) in Python source code.

**What It Detects**:
- API keys (`api_key`, `API_KEY`, `apikey`)
- Passwords (`password`, `PASSWORD`, `pwd`)
- Tokens (`token`, `auth_token`, `access_token`, `refresh_token`, `bearer`)
- AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Connection strings (`connection_string`, `database_url`, `dsn`)
- OAuth secrets (`client_secret`, `consumer_secret`, `app_secret`)
- SSH/RSA keys (`ssh_key`, `rsa_key`, `private_key`)
- Encryption keys (`encryption_key`, `signing_key`)
- Certificates (`certificate`, `cert_key`, `tls_key`)

**How It Works**:
1. Parses Python files using AST (Abstract Syntax Tree)
2. Identifies assignments matching secret patterns
3. Checks if values are hardcoded strings (not from `os.getenv()` or config services)
4. Skips legitimate patterns (enum members, metadata, test placeholders)
5. Reports violations with line numbers and suggestions

**Legitimate Patterns Allowed**:
- Environment variable access: `api_key = os.getenv("API_KEY")`
- Config service injection: `config = container.get_service("ProtocolConfig")`
- Enum class members: `class AuthType(Enum): API_KEY = "api_key"`
- Metadata fields: `password_strength = "weak"`
- Empty strings: `password = ""`
- Placeholders: `password = "YOUR_KEY_HERE"`

---

### Environment Variable Validator

**File**: `validate-hardcoded-env-vars.py`

**Purpose**: Detects hardcoded environment variables instead of loading them from the environment.

**What It Detects**:

Environment variables identified by:
1. **UPPER_CASE naming convention** (e.g., `DATABASE_URL`, `PORT`)
2. **Common prefixes**: `DATABASE_`, `API_`, `AWS_`, `KAFKA_`, `REDIS_`, etc.
3. **Common suffixes**: `_URL`, `_KEY`, `_TOKEN`, `_PORT`, `_HOST`, `_ENDPOINT`, etc.
4. **Exact matches**: `DEBUG`, `PORT`, `HOST`, `LOG_LEVEL`, etc.

**How It Works**:
1. Parses Python files using AST
2. Identifies UPPER_CASE variable assignments
3. Checks against heuristics (prefixes, suffixes, exact matches)
4. Verifies values are hardcoded (not from `os.getenv()`, `os.environ`, or config services)
5. Skips legitimate constants (HTTP status codes, MAX/MIN values, etc.)
6. Reports violations with suggested fixes

**Legitimate Patterns Allowed**:
- Environment access: `DATABASE_URL = os.getenv("DATABASE_URL")`
- With defaults: `PORT = int(os.getenv("PORT", "8000"))`
- Boolean parsing: `DEBUG = os.getenv("DEBUG", "false").lower() == "true"`
- Config services: `DATABASE_URL = config.get("DATABASE_URL")`
- Enum members: `class Config(Enum): DATABASE_URL = "db_url_field"`
- HTTP constants: `HTTP_OK = 200`
- Default constants: `DEFAULT_TIMEOUT = 30`
- Lowercase variables: `default_timeout = 30` (not flagged as env var)

---

## Usage

### Manual Execution

Run validators manually on specific files or directories:

```bash
# Validate secrets in a directory
poetry run python scripts/validation/validate-secrets.py src/

# Validate a specific file
poetry run python scripts/validation/validate-secrets.py src/mymodule/myfile.py

# Validate environment variables
poetry run python scripts/validation/validate-hardcoded-env-vars.py src/

# Multiple files
poetry run python scripts/validation/validate-secrets.py file1.py file2.py file3.py
```

**Exit Codes**:
- `0`: Validation passed (no violations found)
- `1`: Validation failed (violations detected) or error occurred

### Pre-commit Integration

**Automatic validation on every commit** (recommended):

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Hooks run automatically on git commit
git commit -m "Add new feature"

# Run hooks manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run validate-secrets --all-files
pre-commit run validate-hardcoded-env-vars --all-files
```

**Pre-commit Configuration** (`.pre-commit-config.yaml`):

```yaml
# Security: Secret Detection
- id: validate-secrets
  name: ONEX Secret Detection
  entry: poetry run python scripts/validation/validate-secrets.py
  language: system
  pass_filenames: true
  files: ^src/.*\.py$
  exclude: ^(tests/|archived/|archive/|scripts/validation/).*\.py$
  stages: [pre-commit]

# Security: Hardcoded Environment Variable Prevention
- id: validate-hardcoded-env-vars
  name: ONEX Hardcoded Environment Variable Prevention
  entry: poetry run python scripts/validation/validate-hardcoded-env-vars.py
  language: system
  pass_filenames: true
  files: ^src/.*\.py$
  exclude: ^(tests/|archived/|archive/|scripts/validation/).*\.py$
  stages: [pre-commit]
```

**What Files Are Validated**:
- ✅ Production code: `src/**/*.py`
- ❌ Tests: `tests/**/*.py` (excluded)
- ❌ Archived code: `archived/**/*.py` (excluded)
- ❌ Validator scripts: `scripts/validation/**/*.py` (excluded)

---

## Bypass Mechanisms

### When to Use Bypass Comments

Use bypass comments **only for legitimate use cases**:
- **Test fixtures**: Test data requiring hardcoded values
- **Examples/documentation**: Code snippets demonstrating patterns
- **Constants**: Business logic constants that look like secrets but aren't
- **Legacy code**: Temporary bypass during migration (document reason)

⚠️ **WARNING**: Never bypass real secrets! Always use environment variables for actual credentials.

### Secret Validator Bypass

**Supported patterns**:
```python
# File-level bypass (top of file, within first 10 lines)
# secret-ok: test fixture with mock credentials

api_key = "test_key_123"


# Inline bypass (same line as assignment)
password = "test_password"  # noqa: secrets
token = "mock_token"  # secret-ok: test data


# Alternative bypass patterns
auth = "Bearer test"  # password-ok: test fixture
key = "abc123"  # hardcoded-ok: example code
secret = "demo"  # nosec - demonstration only
```

**All bypass patterns**:
- `# secret-ok:` - Generic secret bypass
- `# password-ok:` - Password-specific bypass
- `# hardcoded-ok:` - Hardcoded value bypass
- `# nosec` - Standard security scanner bypass
- `# noqa: secrets` - Standard linter bypass

### Environment Variable Validator Bypass

**Supported pattern**:
```python
# File-level bypass (within first 500 characters)
# env-var-ok: constant definition

DATABASE_URL = "postgresql://localhost/test_db"
API_ENDPOINT = "https://api.test.example.com"
```

**Use cases**:
- Test constants that mimic env var naming
- Business constants in UPPER_CASE (consider lowercase instead)
- Configuration defaults before migration

---

## Detection Details

### How Secret Detection Works

1. **AST Parsing**: Analyzes Python syntax tree (more reliable than regex)
2. **Pattern Matching**: Checks variable names against secret patterns
3. **Context Detection**:
   - **Enum classes**: Skips enum members (e.g., `class Auth(Enum): API_KEY = "api_key"`)
   - **Metadata patterns**: Recognizes business logic (e.g., `password_strength = "weak"`)
   - **Exception list**: Ignores variable names like `password_field`, `token_type`
4. **Value Analysis**:
   - Flags hardcoded strings: `password = "secret123"`
   - Allows env access: `password = os.getenv("PASSWORD")`
   - Ignores placeholders: `password = "YOUR_KEY_HERE"`
   - Skips short values: `key = "ab"` (< 3 chars)

### How Environment Variable Detection Works

1. **AST Parsing**: Analyzes variable assignments
2. **Naming Convention**: Identifies UPPER_CASE variables matching pattern `^[A-Z][A-Z0-9_]*$`
3. **Heuristics** (precise to avoid false positives):
   - **Exact matches**: `DEBUG`, `PORT`, `HOST`, `LOG_LEVEL`, etc.
   - **Prefixes**: `DATABASE_`, `API_`, `AWS_`, `KAFKA_`, `REDIS_`, etc.
   - **Suffixes**: `_URL`, `_KEY`, `_TOKEN`, `_PORT`, `_HOST`, `_ENDPOINT`, etc.
4. **Context Detection**:
   - **Enum classes**: Skips enum members
   - **Exception list**: Ignores constants like `HTTP_OK`, `DEFAULT_TIMEOUT`, `MAX_RETRIES`
5. **Value Analysis**:
   - Flags hardcoded values: `PORT = 8000`
   - Allows env access: `PORT = int(os.getenv("PORT", "8000"))`
   - Allows None: `DATABASE_URL = None` (placeholder)

### Edge Cases Handled

Both validators handle:
- **Enum class members**: Not flagged as secrets/env vars
- **Syntax errors**: Skipped gracefully (other tools catch these)
- **Empty files**: Ignored
- **Large files**: Protected against DoS (10MB limit)
- **Encoding issues**: Unicode handling with graceful fallback
- **Keyword arguments**: Detected in function calls
- **Annotated assignments**: Type-hinted assignments checked

---

## Configuration

### Pre-commit Configuration

Edit `.pre-commit-config.yaml` to customize:

```yaml
# Exclude additional paths
- id: validate-secrets
  exclude: ^(tests/|archived/|mylegacy/).*\.py$

# Change file pattern
- id: validate-hardcoded-env-vars
  files: ^(src/|lib/).*\.py$
```

### Validator Configuration

Edit validator scripts to customize:

**`validate-secrets.py`**:
```python
# Add custom secret patterns (line 60-99)
self.secret_patterns = [
    r".*my_custom_secret.*",
    # ...
]

# Add custom exceptions (line 102-136)
self.exceptions = {
    "my_field_name",
    # ...
}

# Add custom bypass patterns (line 159-165)
self.bypass_patterns = [
    "my-bypass:",
    # ...
]
```

**`validate-hardcoded-env-vars.py`**:
```python
# Add custom prefixes (line 62-85)
self.env_var_prefixes = [
    "MYAPP_",
    # ...
]

# Add custom suffixes (line 88-105)
self.env_var_suffixes = [
    "_CONFIG",
    # ...
]

# Add custom exceptions (line 135-180)
self.exceptions = {
    "MY_CONSTANT",
    # ...
}
```

---

## Examples

### Secret Validator Examples

#### ❌ Bad: Hardcoded Secrets

```python
# FAILS validation
api_key = "sk-1234567890abcdef"
password = "super_secret_password"
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
database_url = "postgresql://user:pass@localhost/db"
client_secret = "oauth_secret_123"

def connect():
    return APIClient(api_key="hardcoded_key")  # Also caught!
```

**Error Output**:
```
❌ Secret Validation FAILED
================================================================================
Found 6 hardcoded secrets in 1 files:

📁 src/mymodule/config.py
  🔐 Line 2:0 - Secret 'api_key' is hardcoded
      💡 Use environment variable or secure configuration instead.
         Example: os.getenv('API_KEY') or container.get_service('ProtocolConfig')
  🔐 Line 3:0 - Secret 'password' is hardcoded
      💡 Use environment variable or secure configuration instead.
         Example: os.getenv('PASSWORD') or container.get_service('ProtocolConfig')
  ...

🔧 How to fix:
   1. Move secrets to .env file:
      Example: API_KEY=your_secret_key
   2. Load from environment in code:
      Example: api_key = os.getenv('API_KEY')
   3. Or use dependency injection:
      Example: config = container.get_service('ProtocolConfig')
   4. For test fixtures, add bypass comment:
      Example: # secret-ok: test fixture
   5. Or use inline bypass:
      Example: password = 'test'  # noqa: secrets
```

#### ✅ Good: Environment Variables

```python
import os
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# PASSES validation - load from environment
api_key = os.getenv("API_KEY")
password = os.getenv("PASSWORD")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")

# With defaults
database_url = os.getenv("DATABASE_URL", "postgresql://localhost/dev")

# Using os.environ
api_key = os.environ.get("API_KEY")
token = os.environ["AUTH_TOKEN"]

# Using dependency injection
def __init__(self, container: ModelONEXContainer):
    config = container.get_service("ProtocolConfig")
    self.api_key = config.get("api_key")
```

#### ✅ Good: Test Fixtures with Bypass

```python
# Test file with bypass comment
# secret-ok: test fixture with mock credentials

import pytest

@pytest.fixture
def mock_credentials():
    """Mock credentials for testing."""
    return {
        "api_key": "test_key_123",  # noqa: secrets
        "password": "test_password",  # secret-ok: test data
    }
```

---

### Environment Variable Validator Examples

#### ❌ Bad: Hardcoded Environment Variables

```python
# FAILS validation
DATABASE_URL = "postgresql://localhost/mydb"
API_ENDPOINT = "https://api.example.com"
PORT = 8000
DEBUG = True
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
AWS_REGION = "us-east-1"
REDIS_URL = "redis://localhost:6379"
CORS_ORIGINS = ["http://localhost:3000"]
```

**Error Output**:
```
❌ Hardcoded Environment Variable Validation FAILED
================================================================================
Found 8 hardcoded environment variables in 1 files:

📁 src/mymodule/settings.py
  ⚠️  Line 2:0 - 'DATABASE_URL' is hardcoded to "postgresql://localhost/mydb"
      💡 Use environment variable instead.
         Example: DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://localhost/mydb")
  ⚠️  Line 3:0 - 'API_ENDPOINT' is hardcoded to "https://api.example.com"
      💡 Use environment variable instead.
         Example: API_ENDPOINT = os.getenv('API_ENDPOINT', "https://api.example.com")
  ...

🔧 How to fix:
   1. Use os.getenv() for environment variables:
      Example: DATABASE_URL = os.getenv("DATABASE_URL")
   2. Provide default values when appropriate:
      Example: PORT = int(os.getenv("PORT", "8000"))
   3. For booleans, parse string values:
      Example: DEBUG = os.getenv("DEBUG", "false").lower() == "true"
   4. For constants, use lowercase names:
      Example: default_timeout = 30  # Not DEFAULT_TIMEOUT = 30
   5. Add bypass comment if intentional:
      Example: # env-var-ok: constant definition
```

#### ✅ Good: Load from Environment

```python
import os

# PASSES validation - load from environment
DATABASE_URL = os.getenv("DATABASE_URL")
API_ENDPOINT = os.getenv("API_ENDPOINT")

# With defaults
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "localhost")
WORKERS = int(os.getenv("WORKERS", "4"))

# Boolean parsing
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Using os.environ
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
AWS_REGION = os.environ["AWS_REGION"]

# List from comma-separated string
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [origin.strip() for origin in cors_origins_str.split(",")]
```

#### ✅ Good: Legitimate Constants

```python
# PASSES validation - lowercase constants (not env vars)
default_timeout = 30
max_retries = 5
api_version = "v1"

# PASSES validation - HTTP status codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500

# PASSES validation - None placeholders
DATABASE_URL = None  # Set at runtime
API_KEY = None  # Injected via container
```

#### ✅ Good: Enum Members (Not Flagged)

```python
from enum import Enum

# PASSES validation - enum members are not env vars
class ConfigKey(Enum):
    """Configuration key names."""
    DATABASE_URL = "database_url"
    API_KEY = "api_key"
    PORT = "port"

class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

---

## Troubleshooting

### False Positives

**Issue**: Validator flags legitimate code.

**Solutions**:

1. **Check if pattern is correct**:
   ```python
   # If this is legitimately a constant (not env var), use lowercase
   default_port = 8000  # ✅ Not flagged
   DEFAULT_PORT = 8000  # ❌ Flagged as env var
   ```

2. **Use bypass comment** (if truly necessary):
   ```python
   # env-var-ok: business constant
   MAX_UPLOAD_SIZE = 10485760  # 10MB
   ```

3. **Update validator exceptions**:
   Edit `scripts/validation/validate-hardcoded-env-vars.py`:
   ```python
   self.exceptions = {
       "YOUR_CONSTANT_NAME",
       # ...
   }
   ```

4. **Report false positive**:
   If pattern is commonly misdetected, report it to improve validator heuristics.

### Bypass Not Working

**Issue**: Bypass comment not recognized.

**Check**:

1. **Secret validator**: Bypass must be within first 10 lines (file-level) or same line (inline)
   ```python
   # ✅ Correct - within first 10 lines
   # secret-ok: test fixture

   api_key = "test"

   # ✅ Correct - inline
   password = "test"  # noqa: secrets
   ```

2. **Env var validator**: Bypass must be within first 500 characters
   ```python
   # ✅ Correct - near top of file
   # env-var-ok: constants

   DATABASE_URL = "postgresql://test"
   ```

3. **Exact pattern matching**: Use exact bypass strings (case-sensitive)
   ```python
   # ❌ Wrong
   # secret-OK: test
   # Secret-ok: test

   # ✅ Correct
   # secret-ok: test
   # noqa: secrets
   ```

### Validator Errors

**Issue**: Validator crashes or errors.

**Common causes**:

1. **Syntax errors in Python file**: Validators skip files with syntax errors gracefully
   - Fix syntax errors first
   - Check with: `poetry run python -m py_compile yourfile.py`

2. **File encoding issues**: Validators expect UTF-8
   - Check file encoding: `file -i yourfile.py`
   - Convert if needed: `iconv -f ISO-8859-1 -t UTF-8 yourfile.py > fixed.py`

3. **Large files**: Files > 10MB are skipped (DoS protection)
   - Split large files into modules

4. **Permission errors**: Ensure files are readable
   - Check permissions: `ls -la yourfile.py`

### Pre-commit Issues

**Issue**: Hooks not running.

**Solutions**:

1. **Install hooks**:
   ```bash
   pre-commit install
   ```

2. **Update hooks**:
   ```bash
   pre-commit autoupdate
   pre-commit install --install-hooks
   ```

3. **Check hook configuration**:
   ```bash
   pre-commit run --all-files --verbose
   ```

4. **Force hook execution**:
   ```bash
   SKIP= git commit -m "message"  # Don't skip
   ```

### Performance Issues

**Issue**: Validators are slow.

**Tips**:

1. **Check file count**: Validators process each file
   ```bash
   find src -name "*.py" | wc -l
   ```

2. **Exclude unnecessary paths** in `.pre-commit-config.yaml`:
   ```yaml
   exclude: ^(tests/|archived/|vendor/).*\.py$
   ```

3. **Run hooks in parallel**: Pre-commit runs hooks concurrently by default

4. **Skip for WIP commits** (use sparingly):
   ```bash
   git commit --no-verify -m "WIP: work in progress"
   ```

---

## Additional Resources

### Related Documentation

- **ONEX Error Handling**: `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`
- **Security Best Practices**: See project security documentation
- **Environment Configuration**: `~/.claude/CLAUDE.md` (shared infrastructure)
- **Pre-commit Configuration**: `.pre-commit-config.yaml`

### Validator Source Code

- **Secret Validator**: `scripts/validation/validate-secrets.py`
- **Env Var Validator**: `scripts/validation/validate-hardcoded-env-vars.py`
- **Test Suite**: `tests/unit/validation/`

### Testing the Validators

Run validator tests:
```bash
# Test secret validator
poetry run pytest tests/unit/validation/test_validate_secrets.py -v

# Test env var validator
poetry run pytest tests/unit/validation/test_validate_hardcoded_env_vars.py -v

# All validation tests
poetry run pytest tests/unit/validation/ -v
```

---

## Quick Reference

### Commands

```bash
# Manual validation
poetry run python scripts/validation/validate-secrets.py src/
poetry run python scripts/validation/validate-hardcoded-env-vars.py src/

# Pre-commit
pre-commit install
pre-commit run --all-files
pre-commit run validate-secrets --all-files
pre-commit run validate-hardcoded-env-vars --all-files

# Testing
poetry run pytest tests/unit/validation/ -v
```

### Bypass Comments

```python
# Secret validator (file-level, top of file)
# secret-ok: reason
# noqa: secrets
# nosec

# Secret validator (inline)
api_key = "test"  # noqa: secrets

# Environment variable validator (file-level)
# env-var-ok: reason
```

### Common Patterns

```python
# ✅ Load secrets from environment
api_key = os.getenv("API_KEY")
password = os.getenv("PASSWORD")

# ✅ Load config with defaults
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ✅ Dependency injection
config = container.get_service("ProtocolConfig")

# ✅ Use lowercase for constants
default_timeout = 30  # Not DEFAULT_TIMEOUT
```

---

**Last Updated**: 2025-12-13
**Project**: omnibase_core v0.4.0
**ONEX Framework**: Security Best Practices
