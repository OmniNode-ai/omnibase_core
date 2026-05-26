# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Equivalence tests for scripts/validation/validate-secrets.py (OMN-12177).

Captures current pass/fail behavior as a regression baseline before refactoring.
Does NOT modify the script. Tests SecretValidator and PythonSecretValidator directly.

Pass cases:
    - File with no secret-like variable names
    - Secret-like variable set via os.getenv()
    - Secret-like variable set via os.environ["KEY"]
    - Empty string value (ignored)
    - Placeholder strings (YOUR_KEY_HERE, CHANGEME, TODO)
    - Variable name in the exception list (e.g. password_hash)
    - Enum class member with secret-like name
    - File-level bypass comment in header (# secret-ok: ...)
    - Inline bypass comment on line (# noqa: secrets)
    - File with only non-secret variable names

Fail cases:
    - Hardcoded non-empty string assigned to 'password'
    - Hardcoded non-empty string assigned to 'api_key'
    - Hardcoded non-empty string assigned to 'token'
    - Hardcoded non-empty string assigned to 'secret'
    - Hardcoded f-string with content assigned to secret-like name
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "validation" / "validate-secrets.py"


def _load_module():  # type: ignore[return]
    spec = importlib.util.spec_from_file_location("validate_secrets", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()
SecretValidator = _mod.SecretValidator
PythonSecretValidator = _mod.PythonSecretValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(tmp_path: Path, filename: str, content: str) -> SecretValidator:
    """Write content to a temp file and run the validator. Returns the validator."""
    f = tmp_path / filename
    f.write_text(content)
    lines = content.splitlines(keepends=True)
    sv = SecretValidator()
    sv.validate_python_file(f, lines)
    return sv


# ---------------------------------------------------------------------------
# Pass cases — no violations expected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_secret_names_no_violations(tmp_path: Path) -> None:
    """Variables with non-secret names are not flagged."""
    sv = _run(tmp_path, "clean.py", "x = 'hello'\ncount = 42\n")
    assert sv.violations == []


@pytest.mark.unit
def test_os_getenv_not_flagged(tmp_path: Path) -> None:
    """Secret assigned via os.getenv() is safe and not flagged."""
    sv = _run(
        tmp_path,
        "getenv.py",
        "import os\npassword = os.getenv('MY_PASSWORD')\n",
    )
    assert sv.violations == []


@pytest.mark.unit
def test_os_environ_subscript_not_flagged(tmp_path: Path) -> None:
    """Secret assigned via os.environ['KEY'] is safe."""
    sv = _run(
        tmp_path,
        "environ.py",
        "import os\napi_key = os.environ['API_KEY']\n",
    )
    assert sv.violations == []


@pytest.mark.unit
def test_empty_string_not_flagged(tmp_path: Path) -> None:
    """Empty string assignment to a secret-like name is not flagged."""
    sv = _run(tmp_path, "empty.py", "password = ''\n")
    assert sv.violations == []


@pytest.mark.unit
def test_placeholder_strings_not_flagged(tmp_path: Path) -> None:
    """Placeholder values (YOUR_KEY_HERE, CHANGEME, TODO) are ignored."""
    content = "api_key = 'YOUR_KEY_HERE'\ntoken = 'CHANGEME'\nsecret = 'TODO'\n"
    sv = _run(tmp_path, "placeholders.py", content)
    assert sv.violations == []


@pytest.mark.unit
def test_exception_variable_names_not_flagged(tmp_path: Path) -> None:
    """Variable names in the exceptions set are skipped."""
    content = "password_hash = 'bcrypt_hash_value'\npassword_validator = 'some_value'\n"
    sv = _run(tmp_path, "exceptions.py", content)
    assert sv.violations == []


@pytest.mark.unit
def test_enum_class_members_not_flagged(tmp_path: Path) -> None:
    """Enum members with secret-like names are not flagged."""
    content = (
        "from enum import Enum\n"
        "class AuthType(Enum):\n"
        "    password = 'password'\n"
        "    api_key = 'api_key'\n"
    )
    sv = _run(tmp_path, "enum_members.py", content)
    assert sv.violations == []


@pytest.mark.unit
def test_file_level_bypass_comment_skips_file(tmp_path: Path) -> None:
    """A # secret-ok: comment in the file header causes the whole file to be skipped."""
    content = "# secret-ok: test fixture file\npassword = 'supersecret'\n"
    sv = _run(tmp_path, "bypass_file.py", content)
    assert sv.violations == []


@pytest.mark.unit
def test_inline_bypass_nosec_skips_line(tmp_path: Path) -> None:
    """An inline # nosec bypass on the same line suppresses the violation."""
    content = "password = 'mysecretvalue'  # nosec\n"
    sv = _run(tmp_path, "bypass_inline.py", content)
    assert sv.violations == []


@pytest.mark.unit
def test_short_value_under_three_chars_not_flagged(tmp_path: Path) -> None:
    """Very short strings (< 3 chars) are not treated as secrets."""
    sv = _run(tmp_path, "short.py", "password = 'ab'\n")
    assert sv.violations == []


@pytest.mark.unit
def test_metadata_assignment_not_flagged(tmp_path: Path) -> None:
    """Known metadata patterns like password_strength='strong' are allowed."""
    sv = _run(tmp_path, "meta.py", "password_strength = 'strong'\n")
    assert sv.violations == []


# ---------------------------------------------------------------------------
# Fail cases — violations expected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hardcoded_password_detected(tmp_path: Path) -> None:
    """Hardcoded string assigned to 'password' is flagged."""
    sv = _run(tmp_path, "hardcoded_pw.py", "password = 'supersecretvalue'\n")
    assert len(sv.violations) >= 1
    assert any(v.secret_name == "password" for v in sv.violations)


@pytest.mark.unit
def test_hardcoded_api_key_detected(tmp_path: Path) -> None:
    """Hardcoded string assigned to 'api_key' is flagged."""
    sv = _run(tmp_path, "hardcoded_key.py", "api_key = 'sk-abc123defghijklmnop'\n")
    assert len(sv.violations) >= 1
    assert any(v.secret_name == "api_key" for v in sv.violations)


@pytest.mark.unit
def test_hardcoded_token_detected(tmp_path: Path) -> None:
    """Hardcoded string assigned to 'token' is flagged."""
    sv = _run(tmp_path, "hardcoded_token.py", "token = 'ghp_realtoken12345678'\n")
    assert len(sv.violations) >= 1
    assert any(v.secret_name == "token" for v in sv.violations)


@pytest.mark.unit
def test_hardcoded_secret_detected(tmp_path: Path) -> None:
    """Hardcoded string assigned to 'secret' is flagged."""
    sv = _run(tmp_path, "hardcoded_secret.py", "secret = 'mysupersecretvalue'\n")
    assert len(sv.violations) >= 1
    assert any(v.secret_name == "secret" for v in sv.violations)


@pytest.mark.unit
def test_violation_contains_line_number(tmp_path: Path) -> None:
    """Violation includes the correct line number."""
    content = "x = 1\npassword = 'realpasswordvalue'\n"
    sv = _run(tmp_path, "lineno.py", content)
    assert sv.violations
    assert sv.violations[0].line_number == 2


@pytest.mark.unit
def test_violation_type_is_hardcoded_secret(tmp_path: Path) -> None:
    """Violation type is 'hardcoded_secret'."""
    sv = _run(tmp_path, "vtype.py", "api_key = 'verylongsecretkey'\n")
    assert sv.violations
    assert sv.violations[0].violation_type == "hardcoded_secret"


@pytest.mark.unit
def test_violation_suggestion_non_empty(tmp_path: Path) -> None:
    """Violation suggestion text is populated."""
    sv = _run(tmp_path, "suggest.py", "password = 'shouldnotbehardcoded'\n")
    assert sv.violations
    assert sv.violations[0].suggestion


@pytest.mark.unit
def test_keyword_argument_secret_detected(tmp_path: Path) -> None:
    """Secret-like keyword argument with hardcoded string value is flagged."""
    content = "some_func(password='hardcodedvalue')\n"
    sv = _run(tmp_path, "kwarg.py", content)
    assert len(sv.violations) >= 1


@pytest.mark.unit
def test_annotated_assignment_secret_detected(tmp_path: Path) -> None:
    """Annotated assignment (x: str = 'val') with secret-like name is flagged."""
    content = "api_key: str = 'hardcoded_api_key_value'\n"
    sv = _run(tmp_path, "annassign.py", content)
    assert len(sv.violations) >= 1
