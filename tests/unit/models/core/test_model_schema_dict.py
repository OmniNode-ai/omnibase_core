# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSchemaDict.

Covers construction (direct field names, aliases, and nesting), the
``to_dict`` serialization path (which emits canonical JSON-Schema alias keys),
and the ``from_dict`` deserialization path.

KNOWN LIMITATION (pinned, not endorsed)
---------------------------------------
``ModelSchemaDict`` declares no ``model_config`` and therefore inherits
Pydantic's defaults: ``populate_by_name`` is *off*, so a field that carries an
alias can only be populated *by its alias* at validation time. ``from_dict``
builds its kwargs using the Python *field names* (e.g. ``schema_uri``,
``min_length``, ``all_of``) rather than the aliases (``$schema``, ``minLength``,
``allOf``). As a result every aliased field is silently dropped when routed
through ``from_dict`` (extra keys default to ``ignore``). These tests assert the
*actual* observed behavior so the round-trip gap is documented rather than
hidden; see the ``TestModelSchemaDictFromDictAliasDrop`` group. The ``to_dict``
tests construct models by alias (which works) so serialization is covered fully.
"""

import pytest

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_schema_dict import ModelSchemaDict


@pytest.mark.unit
class TestModelSchemaDictConstruction:
    """Construction via field names, aliases, and nesting."""

    def test_empty_construction_all_none(self) -> None:
        m = ModelSchemaDict()
        assert m.type is None
        assert m.schema_uri is None
        assert m.items is None
        assert m.properties is None
        # default_factory dict, not None
        assert m.additional_fields == {}

    def test_non_aliased_fields(self) -> None:
        m = ModelSchemaDict(
            type="string",
            title="Title",
            description="A description",
            enum=["a", "b"],
            pattern="^x$",
            minimum=1,
            maximum=10,
            required=["a"],
            nullable=True,
        )
        assert m.type == "string"
        assert m.title == "Title"
        assert m.description == "A description"
        assert m.enum == ["a", "b"]
        assert m.pattern == "^x$"
        assert m.minimum == 1
        assert m.maximum == 10
        assert m.required == ["a"]
        assert m.nullable is True

    def test_aliased_fields_populate_by_alias(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$ref": "#/definitions/Foo",
                "minLength": 2,
                "maxLength": 9,
                "multipleOf": 3,
                "minItems": 1,
                "maxItems": 5,
                "uniqueItems": True,
                "minProperties": 1,
                "maxProperties": 4,
                "additionalProperties": False,
            }
        )
        assert m.schema_uri == "http://json-schema.org/draft-07/schema#"
        assert m.ref == "#/definitions/Foo"
        assert m.min_length == 2
        assert m.max_length == 9
        assert m.multiple_of == 3
        assert m.min_items == 1
        assert m.max_items == 5
        assert m.unique_items is True
        assert m.min_properties == 1
        assert m.max_properties == 4
        assert m.additional_properties is False

    def test_aliased_field_name_is_ignored_without_populate_by_name(self) -> None:
        # Field name (not alias) is treated as an extra key and dropped.
        m = ModelSchemaDict(min_length=7)  # type: ignore[call-arg]
        assert m.min_length is None

    def test_nested_items_and_properties(self) -> None:
        m = ModelSchemaDict(
            type="object",
            items=ModelSchemaDict(type="integer"),
            properties={"p": ModelSchemaDict(type="string")},
        )
        assert m.items is not None
        assert m.items.type == "integer"
        assert m.properties is not None
        assert m.properties["p"].type == "string"


@pytest.mark.unit
class TestModelSchemaDictToDict:
    """``to_dict`` emits canonical JSON-Schema alias keys."""

    def test_empty_to_dict_is_empty(self) -> None:
        assert ModelSchemaDict().to_dict() == {}

    def test_core_fields_use_alias_keys(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "type": "string",
                "$schema": "http://x",
                "title": "T",
                "description": "D",
                "$ref": "#/d/F",
            }
        )
        assert m.to_dict() == {
            "type": "string",
            "$schema": "http://x",
            "title": "T",
            "description": "D",
            "$ref": "#/d/F",
        }

    def test_string_and_numeric_constraints(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "enum": ["a"],
                "pattern": "^a$",
                "minLength": 1,
                "maxLength": 3,
                "minimum": 0,
                "maximum": 9,
                "multipleOf": 2,
            }
        )
        assert m.to_dict() == {
            "enum": ["a"],
            "pattern": "^a$",
            "minLength": 1,
            "maxLength": 3,
            "minimum": 0,
            "maximum": 9,
            "multipleOf": 2,
        }

    def test_array_constraints_recurse_items(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "type": "array",
                "items": ModelSchemaDict(type="integer"),
                "minItems": 1,
                "maxItems": 5,
                "uniqueItems": True,
            }
        )
        assert m.to_dict() == {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "maxItems": 5,
            "uniqueItems": True,
        }

    def test_object_constraints_bool_additional_properties(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "type": "object",
                "properties": {"p": ModelSchemaDict(type="string")},
                "required": ["p"],
                "additionalProperties": True,
                "minProperties": 1,
                "maxProperties": 4,
            }
        )
        assert m.to_dict() == {
            "type": "object",
            "properties": {"p": {"type": "string"}},
            "required": ["p"],
            "additionalProperties": True,
            "minProperties": 1,
            "maxProperties": 4,
        }

    def test_additional_properties_as_schema_recurses(self) -> None:
        m = ModelSchemaDict.model_validate(
            {"additionalProperties": ModelSchemaDict(type="number")}
        )
        assert m.to_dict() == {"additionalProperties": {"type": "number"}}

    def test_nullable_default_and_examples(self) -> None:
        m = ModelSchemaDict(
            nullable=True,
            default=ModelSchemaValue.from_value(5),
            examples=[
                ModelSchemaValue.from_value("x"),
                ModelSchemaValue.from_value(True),
            ],
        )
        assert m.to_dict() == {
            "nullable": True,
            "default": 5,
            "examples": ["x", True],
        }

    def test_composition_fields_recurse(self) -> None:
        m = ModelSchemaDict.model_validate(
            {
                "definitions": {"D": ModelSchemaDict(type="null")},
                "allOf": [ModelSchemaDict(type="string")],
                "anyOf": [ModelSchemaDict(type="integer")],
                "oneOf": [ModelSchemaDict(type="boolean")],
            }
        )
        assert m.to_dict() == {
            "definitions": {"D": {"type": "null"}},
            "allOf": [{"type": "string"}],
            "anyOf": [{"type": "integer"}],
            "oneOf": [{"type": "boolean"}],
        }

    def test_additional_fields_merged(self) -> None:
        m = ModelSchemaDict(
            type="string",
            additional_fields={"format": ModelSchemaValue.from_value("email")},
        )
        assert m.to_dict() == {"type": "string", "format": "email"}

    def test_additional_fields_do_not_override_core_keys(self) -> None:
        # to_dict only writes an additional field when the key is absent.
        m = ModelSchemaDict(
            type="string",
            additional_fields={"type": ModelSchemaValue.from_value("OVERRIDE")},
        )
        assert m.to_dict() == {"type": "string"}


@pytest.mark.unit
class TestModelSchemaDictFromDict:
    """``from_dict`` for the non-aliased fields it can actually populate."""

    def test_non_aliased_scalar_fields(self) -> None:
        m = ModelSchemaDict.from_dict(
            {
                "type": "string",
                "title": "T",
                "description": "D",
                "enum": ["a", "b"],
                "pattern": "^a$",
                "minimum": 1,
                "maximum": 9,
                "required": ["a"],
                "nullable": True,
            }
        )
        assert m.type == "string"
        assert m.title == "T"
        assert m.description == "D"
        assert m.enum == ["a", "b"]
        assert m.pattern == "^a$"
        assert m.minimum == 1
        assert m.maximum == 9
        assert m.required == ["a"]
        assert m.nullable is True

    def test_nested_items(self) -> None:
        m = ModelSchemaDict.from_dict({"items": {"type": "integer"}})
        assert m.items is not None
        assert m.items.type == "integer"

    def test_nested_properties(self) -> None:
        m = ModelSchemaDict.from_dict(
            {"properties": {"p": {"type": "string"}, "q": {"type": "number"}}}
        )
        assert m.properties is not None
        assert m.properties["p"].type == "string"
        assert m.properties["q"].type == "number"

    def test_nested_definitions(self) -> None:
        m = ModelSchemaDict.from_dict({"definitions": {"D": {"type": "null"}}})
        assert m.definitions is not None
        assert m.definitions["D"].type == "null"

    def test_default_wrapped_as_schema_value(self) -> None:
        m = ModelSchemaDict.from_dict({"default": 42})
        assert isinstance(m.default, ModelSchemaValue)
        assert m.default.to_value() == 42

    def test_examples_wrapped_as_schema_values(self) -> None:
        m = ModelSchemaDict.from_dict({"examples": ["x", 1, True]})
        assert m.examples is not None
        assert [e.to_value() for e in m.examples] == ["x", 1, True]

    def test_unknown_field_goes_to_additional_fields(self) -> None:
        m = ModelSchemaDict.from_dict({"format": "email", "customFlag": True})
        assert set(m.additional_fields) == {"format", "customFlag"}
        assert m.additional_fields["format"].to_value() == "email"
        assert m.additional_fields["customFlag"].to_value() is True

    def test_from_dict_accepts_mapping_and_returns_instance(self) -> None:
        m = ModelSchemaDict.from_dict({})
        assert isinstance(m, ModelSchemaDict)
        assert m.to_dict() == {}


@pytest.mark.unit
class TestModelSchemaDictFromDictAliasDrop:
    """Pin the known ``from_dict`` alias-drop limitation.

    ``from_dict`` keys its kwargs by field name, but the model only accepts
    these fields by alias (no ``populate_by_name``), so every aliased field is
    silently dropped. This is a documented gap, not endorsed behavior.
    """

    def test_scalar_aliased_fields_are_dropped(self) -> None:
        m = ModelSchemaDict.from_dict(
            {
                "$schema": "http://x",
                "$ref": "#/d/F",
                "minLength": 2,
                "maxLength": 9,
                "multipleOf": 3,
                "minItems": 1,
                "maxItems": 5,
                "uniqueItems": True,
                "minProperties": 1,
                "maxProperties": 4,
            }
        )
        assert m.schema_uri is None
        assert m.ref is None
        assert m.min_length is None
        assert m.max_length is None
        assert m.multiple_of is None
        assert m.min_items is None
        assert m.max_items is None
        assert m.unique_items is None
        assert m.min_properties is None
        assert m.max_properties is None

    def test_additional_properties_dropped(self) -> None:
        assert (
            ModelSchemaDict.from_dict(
                {"additionalProperties": False}
            ).additional_properties
            is None
        )
        assert (
            ModelSchemaDict.from_dict(
                {"additionalProperties": {"type": "string"}}
            ).additional_properties
            is None
        )

    def test_composition_fields_dropped(self) -> None:
        m = ModelSchemaDict.from_dict(
            {
                "allOf": [{"type": "string"}],
                "anyOf": [{"type": "integer"}],
                "oneOf": [{"type": "boolean"}],
            }
        )
        assert m.all_of is None
        assert m.any_of is None
        assert m.one_of is None


@pytest.mark.unit
class TestModelSchemaDictRoundTrip:
    """Round-trip over the fields that survive both directions."""

    def test_non_aliased_round_trip_is_stable(self) -> None:
        source = {
            "type": "object",
            "title": "T",
            "description": "D",
            "properties": {"p": {"type": "string"}},
            "required": ["p"],
            "items": {"type": "integer"},
            "definitions": {"D": {"type": "null"}},
            "nullable": True,
        }
        once = ModelSchemaDict.from_dict(source).to_dict()
        twice = ModelSchemaDict.from_dict(once).to_dict()
        assert once == source
        assert twice == source
