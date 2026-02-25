#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceSchemaArgumentParser — OMN-2553.

Covers:
    - full schema parse: all property types generate correct flags
    - required field enforcement via argparse
    - type coercion: string, integer, number, boolean, array, enum
    - help text generation: description, required markers, defaults
    - --json flag is always present
    - determinism: same schema produces same parser (sorted flags)
    - error cases: non-object schema, missing properties, unsupported type
    - array type: nargs="+" with correct item type
    - boolean type: BooleanOptionalAction (--flag / --no-flag)
    - enum type: choices restricted to enum values
"""

from __future__ import annotations

import argparse

import pytest

from omnibase_core.errors.error_schema_argument_parser import SchemaParseError
from omnibase_core.services.cli.service_schema_argument_parser import (
    ServiceSchemaArgumentParser,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

COMMAND_ID = "com.omninode.test.run"
DISPLAY_NAME = "Test Run"
DESCRIPTION = "Run a test command."

FULL_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "description": "Max results.",
            "default": 10,
        },
        "verbose": {
            "type": "boolean",
            "description": "Enable verbose output.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Filter tags.",
        },
        "mode": {
            "type": "string",
            "enum": ["fast", "slow"],
            "description": "Execution mode.",
        },
        "name": {
            "type": "string",
            "description": "Target name.",
        },
        "score": {
            "type": "number",
            "description": "Threshold score.",
            "default": 0.5,
        },
    },
    "required": ["mode", "name"],
}


def _make_parser(
    schema: dict[str, object] = FULL_SCHEMA,
    *,
    command_id: str = COMMAND_ID,
    display_name: str = DISPLAY_NAME,
    description: str = DESCRIPTION,
    permissions: list[str] | None = None,
    risk: str = "low",
    examples: list[str] | None = None,
) -> argparse.ArgumentParser:
    return ServiceSchemaArgumentParser.from_schema(
        command_id=command_id,
        display_name=display_name,
        description=description,
        args_schema=schema,
        permissions=permissions,
        risk=risk,
        examples=examples,
    )


# ---------------------------------------------------------------------------
# Tests: basic construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parser_created_successfully() -> None:
    """from_schema returns an ArgumentParser without error for a valid schema."""
    parser = _make_parser()
    assert isinstance(parser, argparse.ArgumentParser)


@pytest.mark.unit
def test_json_flag_always_present() -> None:
    """--json flag is always added regardless of schema contents."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--json"])
    assert namespace.json is True


@pytest.mark.unit
def test_json_flag_defaults_false() -> None:
    """--json flag defaults to False when not supplied."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x"])
    assert namespace.json is False


@pytest.mark.unit
def test_empty_schema_only_json_flag() -> None:
    """A schema with no properties produces a parser with only --json."""
    schema: dict[str, object] = {"type": "object", "properties": {}}
    parser = _make_parser(schema)
    namespace = parser.parse_args([])
    assert namespace.json is False


# ---------------------------------------------------------------------------
# Tests: type coercion
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_integer_type_coerced() -> None:
    """Integer property is coerced to int."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--limit", "42"])
    assert namespace.limit == 42
    assert isinstance(namespace.limit, int)


@pytest.mark.unit
def test_integer_default_used() -> None:
    """Integer default from schema is applied when flag is omitted."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x"])
    assert namespace.limit == 10


@pytest.mark.unit
def test_number_type_coerced() -> None:
    """Number property is coerced to float."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--score", "0.75"])
    assert namespace.score == pytest.approx(0.75)
    assert isinstance(namespace.score, float)


@pytest.mark.unit
def test_string_type() -> None:
    """String property stays as str."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "my-target"])
    assert namespace.name == "my-target"
    assert isinstance(namespace.name, str)


@pytest.mark.unit
def test_boolean_true() -> None:
    """Boolean property: --verbose sets to True."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--verbose"])
    assert namespace.verbose is True


@pytest.mark.unit
def test_boolean_false() -> None:
    """Boolean property: --no-verbose sets to False."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--no-verbose"])
    assert namespace.verbose is False


@pytest.mark.unit
def test_array_type_single_value() -> None:
    """Array property accepts a single value."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "x", "--tags", "foo"])
    assert namespace.tags == ["foo"]


@pytest.mark.unit
def test_array_type_multiple_values() -> None:
    """Array property accepts multiple values (nargs=+)."""
    parser = _make_parser()
    namespace = parser.parse_args(
        ["--mode", "fast", "--name", "x", "--tags", "foo", "bar", "baz"]
    )
    assert namespace.tags == ["foo", "bar", "baz"]


@pytest.mark.unit
def test_enum_valid_choice() -> None:
    """Enum property accepts a valid choice."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "slow", "--name", "x"])
    assert namespace.mode == "slow"


@pytest.mark.unit
def test_enum_invalid_choice_raises() -> None:
    """Enum property rejects values not in the enum."""
    parser = _make_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--mode", "invalid", "--name", "x"])


# ---------------------------------------------------------------------------
# Tests: required fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_required_field_missing_raises() -> None:
    """argparse raises SystemExit when a required flag is not provided."""
    parser = _make_parser()
    # Both --mode and --name are required; omitting both should error.
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.unit
def test_required_field_present_succeeds() -> None:
    """Providing all required fields parses successfully."""
    parser = _make_parser()
    namespace = parser.parse_args(["--mode", "fast", "--name", "target"])
    assert namespace.mode == "fast"
    assert namespace.name == "target"


# ---------------------------------------------------------------------------
# Tests: determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parser_determinism_same_schema() -> None:
    """Two calls with the same schema produce parsers with identical flag sets."""
    parser_a = _make_parser()
    parser_b = _make_parser()

    flags_a = sorted(a.option_strings for a in parser_a._actions)
    flags_b = sorted(a.option_strings for a in parser_b._actions)
    assert flags_a == flags_b


@pytest.mark.unit
def test_parser_flags_sorted_alphabetically() -> None:
    """Schema properties are added as flags in sorted order."""
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "zebra": {"type": "string", "description": "Z flag."},
            "alpha": {"type": "string", "description": "A flag."},
            "middle": {"type": "string", "description": "M flag."},
        },
    }
    parser = _make_parser(schema)
    flag_names = [a.dest for a in parser._actions if a.dest not in ("help", "json")]
    assert flag_names == ["alpha", "middle", "zebra"]


# ---------------------------------------------------------------------------
# Tests: error cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_non_object_schema_raises() -> None:
    """Schema with type != 'object' raises SchemaParseError."""
    schema: dict[str, object] = {"type": "array", "items": {"type": "string"}}
    with pytest.raises(SchemaParseError, match="type='object'"):
        _make_parser(schema)


@pytest.mark.unit
def test_non_dict_schema_raises() -> None:
    """Non-dict schema raises SchemaParseError."""
    with pytest.raises(SchemaParseError):
        ServiceSchemaArgumentParser.from_schema(
            command_id=COMMAND_ID,
            display_name=DISPLAY_NAME,
            description=DESCRIPTION,
            args_schema="not-a-dict",  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_unsupported_property_type_raises() -> None:
    """Unsupported property type raises SchemaParseError."""
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "bad": {"type": "object", "description": "Nested object."},
        },
    }
    with pytest.raises(SchemaParseError, match="Unsupported property type"):
        _make_parser(schema)


@pytest.mark.unit
def test_non_dict_properties_raises() -> None:
    """Non-dict 'properties' field raises SchemaParseError."""
    schema: dict[str, object] = {"type": "object", "properties": ["not", "a", "dict"]}
    with pytest.raises(SchemaParseError, match="properties"):
        _make_parser(schema)


@pytest.mark.unit
def test_non_dict_property_schema_raises() -> None:
    """A property whose schema is not a dict raises SchemaParseError."""
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "bad": "not-a-dict",
        },
    }
    with pytest.raises(SchemaParseError, match="must be a dict"):
        _make_parser(schema)


# ---------------------------------------------------------------------------
# Tests: help text / epilog
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_permissions_in_epilog() -> None:
    """Permissions appear in the parser epilog."""
    parser = _make_parser(permissions=["memory.read", "memory.write"])
    assert parser.epilog is not None
    assert "memory.read" in parser.epilog
    assert "memory.write" in parser.epilog


@pytest.mark.unit
def test_risk_in_epilog() -> None:
    """Risk level appears in the parser epilog."""
    parser = _make_parser(risk="critical")
    assert parser.epilog is not None
    assert "critical" in parser.epilog


@pytest.mark.unit
def test_examples_in_epilog() -> None:
    """Examples appear in the parser epilog."""
    parser = _make_parser(
        schema={"type": "object", "properties": {}},
        examples=["onex test run --mode fast"],
    )
    assert parser.epilog is not None
    assert "onex test run --mode fast" in parser.epilog
