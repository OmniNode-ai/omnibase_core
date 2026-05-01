# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import hashlib

import pytest

from omnibase_core.analysis.symbol_extractor import extract_symbols

SIMPLE_FUNCTION = """\
def foo(x: int) -> int:
    return x + 1
"""

CLASS_WITH_METHODS = """\
class MyClass:
    def __init__(self, x: int) -> None:
        self.x = x

    def method(self) -> int:
        return self.x
"""

NESTED_FUNCTION = """\
def outer(x: int) -> int:
    def inner(y: int) -> int:
        return y
    return inner(x)
"""

MULTI_SYMBOL = """\
def alpha():
    pass

class Beta:
    def gamma(self):
        pass

def delta(x, y):
    return x + y
"""

DECORATED_SYMBOLS = """\
@route("/items")
def list_items():
    return []

@dataclass
class Item:
    @property
    def name(self):
        return "item"
"""


@pytest.mark.unit
def test_simple_function_extracted():
    result = extract_symbols(SIMPLE_FUNCTION)
    assert "foo" in result
    sym = result["foo"]
    assert sym["kind"] == "function"
    assert sym["start_line"] == 1
    assert sym["end_line"] == 2


@pytest.mark.unit
def test_signature_whitespace_collapsed():
    result = extract_symbols(SIMPLE_FUNCTION)
    sig = result["foo"]["signature"]
    assert sig == "def foo(x: int) -> int:"
    assert "  " not in sig


@pytest.mark.unit
def test_body_hash_is_sha256_hex():
    result = extract_symbols(SIMPLE_FUNCTION)
    body_hash = result["foo"]["body_hash"]
    assert len(body_hash) == 64
    assert all(c in "0123456789abcdef" for c in body_hash)


@pytest.mark.unit
def test_body_hash_deterministic():
    r1 = extract_symbols(SIMPLE_FUNCTION)
    r2 = extract_symbols(SIMPLE_FUNCTION)
    assert r1["foo"]["body_hash"] == r2["foo"]["body_hash"]


@pytest.mark.unit
def test_body_hash_changes_with_body():
    modified = "def foo(x: int) -> int:\n    return x + 2\n"
    r1 = extract_symbols(SIMPLE_FUNCTION)
    r2 = extract_symbols(modified)
    assert r1["foo"]["body_hash"] != r2["foo"]["body_hash"]


@pytest.mark.unit
def test_one_line_function_body_not_in_signature():
    r1 = extract_symbols("def foo(x): return x\n")
    r2 = extract_symbols("def foo(x): return x * 2\n")
    assert r1["foo"]["signature"] == "def foo(x):"
    assert r2["foo"]["signature"] == "def foo(x):"
    assert r1["foo"]["body_hash"] != r2["foo"]["body_hash"]


@pytest.mark.unit
def test_class_extracted():
    result = extract_symbols(CLASS_WITH_METHODS)
    assert "MyClass" in result
    sym = result["MyClass"]
    assert sym["kind"] == "class"
    assert sym["start_line"] == 1


@pytest.mark.unit
def test_method_extracted():
    result = extract_symbols(CLASS_WITH_METHODS)
    assert "MyClass.method" in result
    sym = result["MyClass.method"]
    assert sym["kind"] == "method"


@pytest.mark.unit
def test_init_method_extracted():
    result = extract_symbols(CLASS_WITH_METHODS)
    assert "MyClass.__init__" in result


@pytest.mark.unit
def test_nested_function_not_extracted_as_top_level():
    result = extract_symbols(NESTED_FUNCTION)
    assert "outer" in result
    assert "inner" not in result


@pytest.mark.unit
def test_multi_symbol_all_extracted():
    result = extract_symbols(MULTI_SYMBOL)
    assert "alpha" in result
    assert "Beta" in result
    assert "Beta.gamma" in result
    assert "delta" in result


@pytest.mark.unit
def test_decorated_symbols_extracted():
    result = extract_symbols(DECORATED_SYMBOLS)
    assert "list_items" in result
    assert "Item" in result
    assert "Item.name" in result
    assert result["list_items"]["kind"] == "function"
    assert result["Item"]["kind"] == "class"
    assert result["Item.name"]["kind"] == "method"


@pytest.mark.unit
def test_kind_values_valid():
    result = extract_symbols(MULTI_SYMBOL)
    valid_kinds = {"function", "class", "method"}
    for sym in result.values():
        assert sym["kind"] in valid_kinds


@pytest.mark.unit
def test_line_numbers_are_one_indexed():
    result = extract_symbols(SIMPLE_FUNCTION)
    assert result["foo"]["start_line"] >= 1
    assert result["foo"]["end_line"] >= result["foo"]["start_line"]


@pytest.mark.unit
def test_empty_source_returns_empty():
    assert extract_symbols("") == {}


@pytest.mark.unit
def test_body_hash_value_correct():
    result = extract_symbols(SIMPLE_FUNCTION)
    body_source = "    return x + 1\n"
    expected = hashlib.sha256(body_source.encode()).hexdigest()
    assert result["foo"]["body_hash"] == expected
