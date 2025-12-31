"""
Unit tests for json_types module.

Tests the type aliases defined in omnibase_core.types.json_types to verify:
1. All type aliases are importable
2. Type aliases can be used in type annotations
3. Runtime behavior verification with valid values
4. Documentation examples work correctly
"""

from typing import get_args, get_origin

import pytest

from omnibase_core.types.json_types import (
    JsonPrimitive,
    JsonType,
    PrimitiveContainer,
    PrimitiveValue,
    ToolParameterValue,
)


@pytest.mark.unit
class TestJsonPrimitive:
    """Tests for JsonPrimitive type alias."""

    def test_import(self) -> None:
        """Test that JsonPrimitive can be imported."""
        assert JsonPrimitive is not None

    def test_type_is_union(self) -> None:
        """Test that JsonPrimitive is a union type."""
        # PEP 604 unions have UnionType origin
        origin = get_origin(JsonPrimitive)
        # For PEP 604 syntax, origin is types.UnionType
        assert origin is not None

    def test_type_includes_str(self) -> None:
        """Test that JsonPrimitive includes str."""
        args = get_args(JsonPrimitive)
        assert str in args

    def test_type_includes_int(self) -> None:
        """Test that JsonPrimitive includes int."""
        args = get_args(JsonPrimitive)
        assert int in args

    def test_type_includes_float(self) -> None:
        """Test that JsonPrimitive includes float."""
        args = get_args(JsonPrimitive)
        assert float in args

    def test_type_includes_bool(self) -> None:
        """Test that JsonPrimitive includes bool."""
        args = get_args(JsonPrimitive)
        assert bool in args

    def test_type_includes_none(self) -> None:
        """Test that JsonPrimitive includes None."""
        args = get_args(JsonPrimitive)
        assert type(None) in args

    def test_type_annotation_with_str(self) -> None:
        """Test using JsonPrimitive with str value."""
        value: JsonPrimitive = "hello"
        assert value == "hello"
        assert isinstance(value, str)

    def test_type_annotation_with_int(self) -> None:
        """Test using JsonPrimitive with int value."""
        value: JsonPrimitive = 42
        assert value == 42
        assert isinstance(value, int)

    def test_type_annotation_with_float(self) -> None:
        """Test using JsonPrimitive with float value."""
        value: JsonPrimitive = 3.14
        assert value == 3.14
        assert isinstance(value, float)

    def test_type_annotation_with_bool(self) -> None:
        """Test using JsonPrimitive with bool value."""
        value: JsonPrimitive = True
        assert value is True
        assert isinstance(value, bool)

    def test_type_annotation_with_none(self) -> None:
        """Test using JsonPrimitive with None value."""
        value: JsonPrimitive = None
        assert value is None

    def test_docstring_example_str(self) -> None:
        """Test docstring example: value: JsonPrimitive = 'hello'."""
        value: JsonPrimitive = "hello"
        assert value == "hello"

    def test_docstring_example_int(self) -> None:
        """Test docstring example: value: JsonPrimitive = 42."""
        value: JsonPrimitive = 42
        assert value == 42

    def test_docstring_example_none(self) -> None:
        """Test docstring example: value: JsonPrimitive = None."""
        value: JsonPrimitive = None
        assert value is None

    def test_edge_case_empty_string(self) -> None:
        """Test JsonPrimitive with empty string."""
        value: JsonPrimitive = ""
        assert value == ""

    def test_edge_case_zero(self) -> None:
        """Test JsonPrimitive with zero."""
        value: JsonPrimitive = 0
        assert value == 0

    def test_edge_case_negative_int(self) -> None:
        """Test JsonPrimitive with negative integer."""
        value: JsonPrimitive = -42
        assert value == -42

    def test_edge_case_negative_float(self) -> None:
        """Test JsonPrimitive with negative float."""
        value: JsonPrimitive = -3.14
        assert value == -3.14

    def test_edge_case_false(self) -> None:
        """Test JsonPrimitive with False."""
        value: JsonPrimitive = False
        assert value is False


@pytest.mark.unit
class TestPrimitiveValue:
    """Tests for PrimitiveValue type alias (non-nullable)."""

    def test_import(self) -> None:
        """Test that PrimitiveValue can be imported."""
        assert PrimitiveValue is not None

    def test_type_is_union(self) -> None:
        """Test that PrimitiveValue is a union type."""
        origin = get_origin(PrimitiveValue)
        assert origin is not None

    def test_type_includes_str(self) -> None:
        """Test that PrimitiveValue includes str."""
        args = get_args(PrimitiveValue)
        assert str in args

    def test_type_includes_int(self) -> None:
        """Test that PrimitiveValue includes int."""
        args = get_args(PrimitiveValue)
        assert int in args

    def test_type_includes_float(self) -> None:
        """Test that PrimitiveValue includes float."""
        args = get_args(PrimitiveValue)
        assert float in args

    def test_type_includes_bool(self) -> None:
        """Test that PrimitiveValue includes bool."""
        args = get_args(PrimitiveValue)
        assert bool in args

    def test_type_excludes_none(self) -> None:
        """Test that PrimitiveValue excludes None (non-nullable)."""
        args = get_args(PrimitiveValue)
        assert type(None) not in args

    def test_type_annotation_with_str(self) -> None:
        """Test using PrimitiveValue with str value."""
        value: PrimitiveValue = "hello"
        assert value == "hello"

    def test_type_annotation_with_int(self) -> None:
        """Test using PrimitiveValue with int value."""
        value: PrimitiveValue = 42
        assert value == 42

    def test_type_annotation_with_float(self) -> None:
        """Test using PrimitiveValue with float value."""
        value: PrimitiveValue = 3.14
        assert value == 3.14

    def test_type_annotation_with_bool(self) -> None:
        """Test using PrimitiveValue with bool value."""
        value: PrimitiveValue = True
        assert value is True

    def test_docstring_example_str(self) -> None:
        """Test docstring example: value: PrimitiveValue = 'hello'."""
        value: PrimitiveValue = "hello"
        assert value == "hello"

    def test_is_subset_of_json_primitive(self) -> None:
        """Test that PrimitiveValue is JsonPrimitive minus None."""
        primitive_args = set(get_args(PrimitiveValue))
        json_primitive_args = set(get_args(JsonPrimitive))
        # PrimitiveValue should be JsonPrimitive without None
        assert primitive_args == json_primitive_args - {type(None)}


@pytest.mark.unit
class TestJsonType:
    """Tests for JsonType recursive type alias.

    Note (v0.4.0): JsonType uses PEP 695 type alias syntax for proper
    recursive type handling with Pydantic 2.x. Tests that relied on
    get_args() have been replaced with functional tests that verify
    runtime behavior.
    """

    def test_import(self) -> None:
        """Test that JsonType can be imported."""
        assert JsonType is not None

    def test_accepts_str(self) -> None:
        """Test that JsonType accepts str values at runtime."""
        value: JsonType = "hello"
        assert isinstance(value, str)

    def test_accepts_int(self) -> None:
        """Test that JsonType accepts int values at runtime."""
        value: JsonType = 42
        assert isinstance(value, int)

    def test_accepts_float(self) -> None:
        """Test that JsonType accepts float values at runtime."""
        value: JsonType = 3.14
        assert isinstance(value, float)

    def test_accepts_bool(self) -> None:
        """Test that JsonType accepts bool values at runtime."""
        value: JsonType = True
        assert isinstance(value, bool)

    def test_accepts_none(self) -> None:
        """Test that JsonType accepts None values at runtime."""
        value: JsonType = None
        assert value is None

    def test_type_annotation_with_primitive(self) -> None:
        """Test using JsonType with primitive value."""
        value: JsonType = "hello"
        assert value == "hello"

    def test_type_annotation_with_dict(self) -> None:
        """Test using JsonType with dict value."""
        value: JsonType = {"key": "value"}
        assert value == {"key": "value"}

    def test_type_annotation_with_list(self) -> None:
        """Test using JsonType with list value."""
        value: JsonType = [1, 2, 3]
        assert value == [1, 2, 3]

    def test_docstring_example_nested_config(self) -> None:
        """Test docstring example: deeply nested config structure."""
        config: JsonType = {
            "database": {
                "hosts": ["host1", "host2"],
                "settings": {"timeout": 30, "retry": True},
            }
        }
        # Access nested structure with runtime assertions
        assert isinstance(config, dict)
        database = config["database"]
        assert isinstance(database, dict)
        assert database["hosts"] == ["host1", "host2"]
        settings = database["settings"]
        assert isinstance(settings, dict)
        assert settings["timeout"] == 30
        assert settings["retry"] is True

    def test_recursive_definition(self) -> None:
        """Test that JsonType supports recursive structures."""
        # This should work with the recursive type definition
        value: JsonType = {
            "nested": {"more_nested": {"array": [{"deep": True}, "string", 123]}}
        }
        assert isinstance(value, dict)

    def test_empty_containers(self) -> None:
        """Test JsonType with empty containers."""
        empty_dict: JsonType = {}
        empty_list: JsonType = []
        assert empty_dict == {}
        assert empty_list == []


@pytest.mark.unit
class TestPrimitiveContainer:
    """Tests for PrimitiveContainer type alias."""

    def test_import(self) -> None:
        """Test that PrimitiveContainer can be imported."""
        assert PrimitiveContainer is not None

    def test_type_is_union(self) -> None:
        """Test that PrimitiveContainer is a union type."""
        origin = get_origin(PrimitiveContainer)
        assert origin is not None

    def test_type_annotation_with_str(self) -> None:
        """Test using PrimitiveContainer with str value."""
        value: PrimitiveContainer = "hello"
        assert value == "hello"

    def test_type_annotation_with_int(self) -> None:
        """Test using PrimitiveContainer with int value."""
        value: PrimitiveContainer = 42
        assert value == 42

    def test_type_annotation_with_float(self) -> None:
        """Test using PrimitiveContainer with float value."""
        value: PrimitiveContainer = 3.14
        assert value == 3.14

    def test_type_annotation_with_bool(self) -> None:
        """Test using PrimitiveContainer with bool value."""
        value: PrimitiveContainer = True
        assert value is True

    def test_type_annotation_with_list(self) -> None:
        """Test using PrimitiveContainer with list of primitives."""
        value: PrimitiveContainer = ["prod", "critical"]
        assert value == ["prod", "critical"]

    def test_type_annotation_with_dict(self) -> None:
        """Test using PrimitiveContainer with dict of primitives."""
        value: PrimitiveContainer = {"timeout": 30, "enabled": True}
        assert value == {"timeout": 30, "enabled": True}

    def test_docstring_example_dict(self) -> None:
        """Test docstring example: settings: PrimitiveContainer = {'timeout': 30, 'enabled': True}."""
        settings: PrimitiveContainer = {"timeout": 30, "enabled": True}
        assert settings == {"timeout": 30, "enabled": True}

    def test_docstring_example_list(self) -> None:
        """Test docstring example: tags: PrimitiveContainer = ['prod', 'critical']."""
        tags: PrimitiveContainer = ["prod", "critical"]
        assert tags == ["prod", "critical"]

    def test_docstring_example_scalar(self) -> None:
        """Test docstring example: count: PrimitiveContainer = 42."""
        count: PrimitiveContainer = 42
        assert count == 42

    def test_list_with_mixed_primitives(self) -> None:
        """Test PrimitiveContainer with list containing mixed primitive types."""
        value: PrimitiveContainer = [1, "two", 3.0, True]
        assert isinstance(value, list)
        assert len(value) == 4

    def test_dict_with_mixed_primitive_values(self) -> None:
        """Test PrimitiveContainer with dict containing mixed primitive values."""
        value: PrimitiveContainer = {
            "count": 10,
            "name": "test",
            "ratio": 0.5,
            "active": False,
        }
        assert isinstance(value, dict)
        assert value["count"] == 10
        assert value["name"] == "test"

    def test_none_not_in_type(self) -> None:
        """Test that PrimitiveContainer does not include None (via PrimitiveValue)."""
        args = get_args(PrimitiveContainer)
        # Direct None should not be in args (None is not a PrimitiveValue)
        assert type(None) not in args


@pytest.mark.unit
class TestToolParameterValue:
    """Tests for ToolParameterValue type alias."""

    def test_import(self) -> None:
        """Test that ToolParameterValue can be imported."""
        assert ToolParameterValue is not None

    def test_type_is_union(self) -> None:
        """Test that ToolParameterValue is a union type."""
        origin = get_origin(ToolParameterValue)
        assert origin is not None

    def test_type_includes_str(self) -> None:
        """Test that ToolParameterValue includes str."""
        args = get_args(ToolParameterValue)
        assert str in args

    def test_type_includes_int(self) -> None:
        """Test that ToolParameterValue includes int."""
        args = get_args(ToolParameterValue)
        assert int in args

    def test_type_includes_float(self) -> None:
        """Test that ToolParameterValue includes float."""
        args = get_args(ToolParameterValue)
        assert float in args

    def test_type_includes_bool(self) -> None:
        """Test that ToolParameterValue includes bool."""
        args = get_args(ToolParameterValue)
        assert bool in args

    def test_type_excludes_none(self) -> None:
        """Test that ToolParameterValue excludes None (parameters should be explicit)."""
        args = get_args(ToolParameterValue)
        assert type(None) not in args

    def test_type_includes_list_str(self) -> None:
        """Test that ToolParameterValue includes list[str]."""
        args = get_args(ToolParameterValue)
        list_types = [arg for arg in args if get_origin(arg) is list]
        assert len(list_types) == 1
        # Verify it's list[str]
        list_type = list_types[0]
        list_args = get_args(list_type)
        assert str in list_args

    def test_type_includes_dict_str_str(self) -> None:
        """Test that ToolParameterValue includes dict[str, str]."""
        args = get_args(ToolParameterValue)
        dict_types = [arg for arg in args if get_origin(arg) is dict]
        assert len(dict_types) == 1
        # Verify it's dict[str, str]
        dict_type = dict_types[0]
        dict_args = get_args(dict_type)
        assert dict_args == (str, str)

    def test_type_annotation_with_str(self) -> None:
        """Test using ToolParameterValue with str value."""
        value: ToolParameterValue = "https://example.com"
        assert value == "https://example.com"

    def test_type_annotation_with_int(self) -> None:
        """Test using ToolParameterValue with int value."""
        value: ToolParameterValue = 30
        assert value == 30

    def test_type_annotation_with_float(self) -> None:
        """Test using ToolParameterValue with float value."""
        value: ToolParameterValue = 3.14
        assert value == 3.14

    def test_type_annotation_with_bool(self) -> None:
        """Test using ToolParameterValue with bool value."""
        value: ToolParameterValue = True
        assert value is True

    def test_type_annotation_with_list_str(self) -> None:
        """Test using ToolParameterValue with list[str] value."""
        value: ToolParameterValue = ["api", "external"]
        assert value == ["api", "external"]

    def test_type_annotation_with_dict_str_str(self) -> None:
        """Test using ToolParameterValue with dict[str, str] value."""
        value: ToolParameterValue = {"Authorization": "Bearer token"}
        assert value == {"Authorization": "Bearer token"}

    def test_docstring_example_full_params(self) -> None:
        """Test docstring example: full params dict."""
        params: dict[str, ToolParameterValue] = {
            "url": "https://example.com",
            "timeout": 30,
            "headers": {"Authorization": "Bearer token"},
            "tags": ["api", "external"],
        }
        assert params["url"] == "https://example.com"
        assert params["timeout"] == 30
        assert params["headers"] == {"Authorization": "Bearer token"}
        assert params["tags"] == ["api", "external"]

    def test_mcp_tool_parameters_use_case(self) -> None:
        """Test ToolParameterValue in MCP tool context."""
        # Simulate MCP tool parameters
        tool_params: dict[str, ToolParameterValue] = {
            "query": "search term",
            "limit": 100,
            "include_drafts": False,
            "filters": ["active", "published"],
            "options": {"format": "json", "lang": "en"},
        }
        assert tool_params["query"] == "search term"
        assert tool_params["limit"] == 100
        assert tool_params["include_drafts"] is False
        assert tool_params["filters"] == ["active", "published"]
        options = tool_params["options"]
        assert isinstance(options, dict)
        assert options["format"] == "json"

    def test_cli_argument_use_case(self) -> None:
        """Test ToolParameterValue in CLI argument context."""
        cli_args: dict[str, ToolParameterValue] = {
            "input_file": "/path/to/input.txt",
            "verbose": True,
            "count": 5,
            "extra_args": ["--force", "--no-cache"],
        }
        assert cli_args["input_file"] == "/path/to/input.txt"
        assert cli_args["verbose"] is True


@pytest.mark.unit
class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_exist(self) -> None:
        """Test that all items in __all__ are exported."""
        from omnibase_core.types import json_types

        expected_exports = [
            "JsonPrimitive",
            "JsonType",
            "PrimitiveValue",
            "PrimitiveContainer",
            "ToolParameterValue",
        ]

        for export in expected_exports:
            assert hasattr(json_types, export), f"Missing export: {export}"

    def test_all_list_contents(self) -> None:
        """Test that __all__ contains expected type aliases."""
        from omnibase_core.types import json_types

        expected_exports = {
            "JsonPrimitive",
            "JsonType",
            "PrimitiveValue",
            "PrimitiveContainer",
            "ToolParameterValue",
        }

        assert set(json_types.__all__) == expected_exports


@pytest.mark.unit
class TestTypeRelationships:
    """Tests for relationships between type aliases.

    Note (v0.4.0): JsonType uses PEP 695 type alias syntax, which has different
    runtime introspection behavior.
    """

    def test_primitive_value_subset_of_json_primitive(self) -> None:
        """Test that PrimitiveValue is JsonPrimitive without None."""
        prim_value_args = set(get_args(PrimitiveValue))
        json_prim_args = set(get_args(JsonPrimitive))

        # PrimitiveValue should be JsonPrimitive minus None
        expected = json_prim_args - {type(None)}
        assert prim_value_args == expected

    def test_tool_parameter_does_not_include_none(self) -> None:
        """Test that ToolParameterValue does not include None."""
        tool_args = set(get_args(ToolParameterValue))

        # ToolParameterValue should not have None (it's for explicit parameters)
        assert type(None) not in tool_args

    def test_json_primitive_components(self) -> None:
        """Test that JsonPrimitive contains expected primitive types."""
        primitive_args = set(get_args(JsonPrimitive))

        # Verify expected components
        assert str in primitive_args
        assert int in primitive_args
        assert float in primitive_args
        assert bool in primitive_args
        assert type(None) in primitive_args


@pytest.mark.unit
class TestUsageInFunctionSignatures:
    """Tests for using type aliases in function signatures."""

    def test_function_with_json_type_param(self) -> None:
        """Test function that accepts JsonType parameter."""

        def process_json(data: JsonType) -> str:
            if data is None:
                return "null"
            return str(type(data).__name__)

        assert process_json("test") == "str"
        assert process_json(42) == "int"
        assert process_json([1, 2, 3]) == "list"
        assert process_json({"key": "value"}) == "dict"
        assert process_json(None) == "null"

    def test_function_with_json_type_return(self) -> None:
        """Test function that returns JsonType."""

        def create_config() -> JsonType:
            return {"database": {"host": "localhost", "port": 5432}}

        config = create_config()
        assert isinstance(config, dict)
        database = config["database"]
        assert isinstance(database, dict)
        assert database["host"] == "localhost"

    def test_function_with_tool_params(self) -> None:
        """Test function that uses ToolParameterValue dict."""

        def execute_tool(params: dict[str, ToolParameterValue]) -> bool:
            return "url" in params

        result = execute_tool({"url": "https://example.com", "timeout": 30})
        assert result is True

    def test_function_with_primitive_container_return(self) -> None:
        """Test function that returns PrimitiveContainer."""

        def get_config_value(key: str) -> PrimitiveContainer:
            configs: dict[str, PrimitiveContainer] = {
                "count": 10,
                "tags": ["prod", "api"],
                "settings": {"debug": True, "verbose": False},
            }
            return configs.get(key, "default")

        assert get_config_value("count") == 10
        assert get_config_value("tags") == ["prod", "api"]
        assert get_config_value("unknown") == "default"


@pytest.mark.unit
class TestDocstringExamplesFromModule:
    """Tests that verify all docstring examples from the module work correctly."""

    def test_module_usage_example_function_signature(self) -> None:
        """Test module docstring example: function signature usage."""

        def process_json(data: JsonType) -> JsonType:
            # Simple pass-through for testing
            if isinstance(data, dict):
                # Cast to JsonType since dict[str, Any] is compatible
                result: JsonType = {}
                for k, v in data.items():
                    result[k] = v
                return result
            return {"result": data}

        result = process_json({"input": "test"})
        assert result == {"input": "test"}

    def test_module_usage_example_config_dict(self) -> None:
        """Test module docstring example: config dict usage."""
        config: dict[str, JsonType] = {"key": "value", "count": 42}
        assert config["key"] == "value"
        assert config["count"] == 42

    def test_module_usage_example_tool_params(self) -> None:
        """Test module docstring example: tool params usage."""
        params: dict[str, ToolParameterValue] = {"name": "test", "tags": ["a", "b"]}
        assert params["name"] == "test"
        assert params["tags"] == ["a", "b"]
