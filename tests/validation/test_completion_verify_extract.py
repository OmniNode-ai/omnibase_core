# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from omnibase_core.validation.completion_verify import extract_identifiers


def test_backtick() -> None:
    assert "fooBar" in extract_identifiers("Implement `fooBar` function")


def test_camelcase() -> None:
    assert "validateToken" in extract_identifiers("Refactor validateToken to async")


def test_pascalcase() -> None:
    assert "ModelFoo" in extract_identifiers("Add ModelFoo to the ticket")


def test_dotted_config_key() -> None:
    assert "auth.token.expiry" in extract_identifiers("Set auth.token.expiry to 3600")


def test_quoted_path_excluded_from_identifiers() -> None:
    # paths are extracted separately
    assert "src/foo.py" not in extract_identifiers('Touch "src/foo.py"')


def test_dedup() -> None:
    out = extract_identifiers("`fooBar` and fooBar again")
    assert out.count("fooBar") == 1
