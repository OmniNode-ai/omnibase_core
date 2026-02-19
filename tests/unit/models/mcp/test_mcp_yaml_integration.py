# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for MCP models with YAML contracts.

Tests for loading MCP configuration from YAML-like data structures,
round-trip serialization, and schema generation patterns that mirror
how contract.yaml files define MCP tool configurations.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_mcp_parameter_type import EnumMCPParameterType
from omnibase_core.enums.enum_mcp_tool_type import EnumMCPToolType
from omnibase_core.models.mcp import (
    ModelMCPParameterMapping,
    ModelMCPToolConfig,
    ModelMCPToolDescriptor,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestMCPYAMLIntegration:
    """Integration tests for MCP models with YAML-style data."""

    def test_tool_config_from_yaml_dict(self) -> None:
        """Test loading tool config from YAML-like dict.

        Simulates how a contract.yaml `mcp:` block would be parsed.
        Note: parameter_type uses lowercase JSON Schema types (string, integer, etc.)
        """
        yaml_data = {
            "expose": True,
            "tool_name": "search_documents",
            "description": "Search documents by query",
            "parameter_mappings": [
                {
                    "name": "query",
                    "parameter_type": "string",
                    "required": True,
                    "description": "Search query",
                }
            ],
            "tags": ["search", "documents"],
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.expose is True
        assert config.tool_name == "search_documents"
        assert len(config.parameter_mappings) == 1
        assert config.parameter_mappings[0].name == "query"
        assert (
            config.parameter_mappings[0].parameter_type == EnumMCPParameterType.STRING
        )
        assert config.parameter_mappings[0].required is True

    def test_tool_config_from_yaml_dict_minimal(self) -> None:
        """Test loading tool config with minimal YAML data."""
        yaml_data = {
            "expose": True,
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.expose is True
        assert config.tool_name is None
        assert config.parameter_mappings == []

    def test_tool_config_from_yaml_dict_full(self) -> None:
        """Test loading tool config with full YAML-like configuration.

        Uses lowercase JSON Schema type values (string, integer, etc.)
        """
        yaml_data = {
            "expose": True,
            "tool_name": "advanced_search",
            "description": "Advanced document search with filters",
            "parameter_mappings": [
                {
                    "name": "query",
                    "parameter_type": "string",
                    "required": True,
                    "description": "Search query text",
                    "min_length": 1,
                    "max_length": 1000,
                },
                {
                    "name": "limit",
                    "parameter_type": "integer",
                    "required": False,
                    "default_value": 10,
                    "min_value": 1,
                    "max_value": 100,
                    "description": "Maximum results to return",
                },
                {
                    "name": "format",
                    "parameter_type": "string",
                    "required": False,
                    "default_value": "json",
                    "enum_values": ["json", "xml", "csv"],
                    "description": "Output format",
                },
            ],
            "tags": ["search", "documents", "api"],
            "timeout_seconds": 60,
            "retry_enabled": True,
            "max_retries": 5,
            "requires_confirmation": False,
            "dangerous": False,
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.expose is True
        assert config.tool_name == "advanced_search"
        assert len(config.parameter_mappings) == 3
        assert config.timeout_seconds == 60
        assert config.max_retries == 5

        # Check parameter details
        query_param = config.parameter_mappings[0]
        assert query_param.min_length == 1
        assert query_param.max_length == 1000

        limit_param = config.parameter_mappings[1]
        assert limit_param.default_value == 10
        assert limit_param.min_value == 1
        assert limit_param.max_value == 100

        format_param = config.parameter_mappings[2]
        assert format_param.enum_values == ["json", "xml", "csv"]

    def test_parameter_mapping_roundtrip(self) -> None:
        """Test parameter mapping round-trip serialization."""
        mapping = ModelMCPParameterMapping(
            name="count",
            parameter_type=EnumMCPParameterType.INTEGER,
            required=True,
            min_value=1,
            max_value=100,
            description="Number of items",
        )
        data = mapping.model_dump()
        restored = ModelMCPParameterMapping.model_validate(data)
        assert restored == mapping

    def test_parameter_mapping_roundtrip_all_fields(self) -> None:
        """Test parameter mapping round-trip with all optional fields."""
        mapping = ModelMCPParameterMapping(
            name="email",
            parameter_type=EnumMCPParameterType.STRING,
            description="User email address",
            required=True,
            default_value=None,
            onex_field="input.user.email",
            mcp_param_name="user_email",
            enum_values=None,
            min_value=None,
            max_value=None,
            min_length=5,
            max_length=255,
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            examples=["user@example.com", "admin@company.org"],
        )
        data = mapping.model_dump()
        restored = ModelMCPParameterMapping.model_validate(data)
        assert restored == mapping
        assert restored.pattern == mapping.pattern
        assert restored.examples == mapping.examples

    def test_tool_config_roundtrip(self) -> None:
        """Test tool config round-trip serialization."""
        config = ModelMCPToolConfig(
            expose=True,
            tool_name="test_tool",
            description="A test tool",
            parameter_mappings=[
                ModelMCPParameterMapping(
                    name="param1",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                ),
            ],
            tags=["test", "example"],
            timeout_seconds=45,
        )
        data = config.model_dump()
        restored = ModelMCPToolConfig.model_validate(data)
        assert restored.expose == config.expose
        assert restored.tool_name == config.tool_name
        assert len(restored.parameter_mappings) == 1
        assert restored.parameter_mappings[0].name == "param1"

    def test_tool_descriptor_with_semver(self) -> None:
        """Test tool descriptor with ModelSemVer version."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="A test tool",
            version=ModelSemVer(major=2, minor=1, patch=0),
        )
        assert descriptor.version.major == 2
        assert descriptor.version.minor == 1
        assert descriptor.version.patch == 0

    def test_tool_descriptor_roundtrip(self) -> None:
        """Test tool descriptor round-trip serialization."""
        descriptor = ModelMCPToolDescriptor(
            name="roundtrip_tool",
            description="Test round-trip",
            tool_type=EnumMCPToolType.FUNCTION,
            version=ModelSemVer(major=1, minor=2, patch=3),
            parameters=[
                ModelMCPParameterMapping(
                    name="input",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                ),
            ],
            tags=["test"],
            node_name="NodeTestCompute",
            node_version=ModelSemVer(major=0, minor=1, patch=0),
        )
        data = descriptor.model_dump()
        restored = ModelMCPToolDescriptor.model_validate(data)
        assert restored.name == descriptor.name
        assert restored.version.major == 1
        assert restored.version.minor == 2
        assert restored.version.patch == 3
        assert restored.node_name == "NodeTestCompute"
        assert restored.node_version is not None
        assert restored.node_version.major == 0

    def test_empty_input_schema_preserved(self) -> None:
        """Test that explicitly empty input schema is preserved.

        When a tool has no parameters, an empty dict should be preserved
        rather than generating a schema with empty properties.
        """
        descriptor = ModelMCPToolDescriptor(
            name="no_params_tool",
            description="Tool with no parameters",
            input_schema={},
        )
        schema = descriptor.to_input_schema()
        assert schema == {}

    def test_empty_input_schema_vs_none(self) -> None:
        """Test difference between empty input_schema and None."""
        # With input_schema=None, schema is generated from parameters
        descriptor_none = ModelMCPToolDescriptor(
            name="tool_none_schema",
            description="Tool with None input_schema",
            input_schema=None,
            parameters=[
                ModelMCPParameterMapping(
                    name="param",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                ),
            ],
        )
        schema_none = descriptor_none.to_input_schema()
        assert schema_none["type"] == "object"
        properties = schema_none["properties"]
        assert isinstance(properties, dict)
        assert "param" in properties

        # With input_schema={}, empty dict is preserved
        descriptor_empty = ModelMCPToolDescriptor(
            name="tool_empty_schema",
            description="Tool with empty input_schema",
            input_schema={},
        )
        schema_empty = descriptor_empty.to_input_schema()
        assert schema_empty == {}

    def test_parameter_to_json_schema(self) -> None:
        """Test parameter mapping to JSON Schema conversion."""
        mapping = ModelMCPParameterMapping(
            name="email",
            parameter_type=EnumMCPParameterType.STRING,
            description="User email",
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            required=True,
        )
        schema = mapping.to_json_schema()
        assert schema["type"] == "string"
        assert schema["description"] == "User email"
        assert "pattern" in schema
        assert schema["pattern"] == mapping.pattern

    def test_parameter_to_json_schema_integer_with_constraints(self) -> None:
        """Test integer parameter to JSON Schema with constraints."""
        mapping = ModelMCPParameterMapping(
            name="page",
            parameter_type=EnumMCPParameterType.INTEGER,
            description="Page number",
            required=False,
            default_value=1,
            min_value=1,
            max_value=1000,
        )
        schema = mapping.to_json_schema()
        assert schema["type"] == "integer"
        assert schema["default"] == 1
        assert schema["minimum"] == 1
        assert schema["maximum"] == 1000

    def test_parameter_to_json_schema_array_with_examples(self) -> None:
        """Test array parameter to JSON Schema with examples."""
        mapping = ModelMCPParameterMapping(
            name="tags",
            parameter_type=EnumMCPParameterType.ARRAY,
            description="Filter tags",
            required=False,
            examples=[["python", "api"], ["docs"]],
        )
        schema = mapping.to_json_schema()
        assert schema["type"] == "array"
        assert schema["examples"] == [["python", "api"], ["docs"]]

    def test_generate_tool_descriptor_from_config(self) -> None:
        """Test generating tool descriptor from tool config data."""
        config = ModelMCPToolConfig(
            expose=True,
            tool_name="configured_tool",
            description="Tool from YAML config",
            parameter_mappings=[
                ModelMCPParameterMapping(
                    name="query",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                    description="Search query",
                ),
                ModelMCPParameterMapping(
                    name="limit",
                    parameter_type=EnumMCPParameterType.INTEGER,
                    required=False,
                    default_value=10,
                    min_value=1,
                    max_value=100,
                    description="Max results",
                ),
            ],
            tags=["search", "api"],
            timeout_seconds=45,
        )

        # Create descriptor from config (simulating contract generation)
        descriptor = ModelMCPToolDescriptor(
            name=config.tool_name or "unnamed_tool",
            description=config.description or "",
            parameters=config.parameter_mappings,
            tags=config.tags,
            timeout_seconds=config.timeout_seconds,
        )

        # Verify descriptor
        assert descriptor.name == "configured_tool"
        assert descriptor.description == "Tool from YAML config"
        assert len(descriptor.parameters) == 2
        assert descriptor.tags == ["search", "api"]
        assert descriptor.timeout_seconds == 45

        # Generate input schema
        schema = descriptor.to_input_schema()
        assert schema["type"] == "object"
        properties = schema["properties"]
        assert isinstance(properties, dict)
        assert "query" in properties
        assert "limit" in properties
        assert schema["required"] == ["query"]
        limit_schema = properties["limit"]
        assert isinstance(limit_schema, dict)
        assert limit_schema["default"] == 10
        assert limit_schema["minimum"] == 1
        assert limit_schema["maximum"] == 100

    def test_yaml_style_nested_contract_block(self) -> None:
        """Test loading nested MCP config as in contract.yaml structure.

        Simulates the structure:
        ```yaml
        node:
          name: NodeSearchCompute
          mcp:
            expose: true
            tool_name: search
            ...
        ```
        """
        contract_data = {
            "node": {
                "name": "NodeSearchCompute",
                "version": "1.0.0",
                "mcp": {
                    "expose": True,
                    "tool_name": "search",
                    "description": "Search the index",
                    "parameter_mappings": [
                        {
                            "name": "query",
                            "parameter_type": "string",
                            "required": True,
                        }
                    ],
                },
            }
        }

        # Extract and parse MCP block
        mcp_data = contract_data["node"]["mcp"]
        config = ModelMCPToolConfig.model_validate(mcp_data)

        assert config.expose is True
        assert config.tool_name == "search"
        assert len(config.parameter_mappings) == 1

    def test_all_parameter_types_from_yaml_strings(self) -> None:
        """Test loading all parameter types from YAML string values.

        Uses lowercase JSON Schema type names (string, integer, etc.)
        """
        type_mappings = [
            ("string", EnumMCPParameterType.STRING),
            ("integer", EnumMCPParameterType.INTEGER),
            ("number", EnumMCPParameterType.NUMBER),
            ("boolean", EnumMCPParameterType.BOOLEAN),
            ("array", EnumMCPParameterType.ARRAY),
            ("object", EnumMCPParameterType.OBJECT),
        ]

        for yaml_value, expected_enum in type_mappings:
            yaml_data = {
                "name": f"test_{yaml_value}",
                "parameter_type": yaml_value,
            }
            mapping = ModelMCPParameterMapping.model_validate(yaml_data)
            assert mapping.parameter_type == expected_enum

    def test_mcp_param_name_override_in_schema(self) -> None:
        """Test mcp_param_name override is used in generated schema."""
        config = ModelMCPToolConfig(
            expose=True,
            tool_name="search",
            description="Search tool",
            parameter_mappings=[
                ModelMCPParameterMapping(
                    name="internal_query_field",
                    mcp_param_name="q",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                    description="Search query",
                ),
            ],
        )

        descriptor = ModelMCPToolDescriptor(
            name=config.tool_name or "unnamed",
            description=config.description or "",
            parameters=config.parameter_mappings,
        )

        schema = descriptor.to_input_schema()
        # Should use mcp_param_name "q" not internal name
        properties = schema["properties"]
        assert isinstance(properties, dict)
        assert "q" in properties
        assert "internal_query_field" not in properties
        assert schema["required"] == ["q"]

    def test_dangerous_and_confirmation_flags(self) -> None:
        """Test dangerous and requires_confirmation flags from YAML."""
        yaml_data = {
            "expose": True,
            "tool_name": "delete_all",
            "description": "Delete all records",
            "dangerous": True,
            "requires_confirmation": True,
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.dangerous is True
        assert config.requires_confirmation is True

    def test_tool_descriptor_metadata_from_yaml(self) -> None:
        """Test tool descriptor with metadata dict from YAML."""
        yaml_data = {
            "name": "custom_tool",
            "description": "Tool with metadata",
            "metadata": {
                "author": "test_user",
                "category": "utilities",
                "deprecated": False,
            },
            "tags": ["utility", "helper"],
        }
        descriptor = ModelMCPToolDescriptor.model_validate(yaml_data)
        assert descriptor.metadata["author"] == "test_user"
        assert descriptor.metadata["category"] == "utilities"
        assert descriptor.metadata["deprecated"] is False


@pytest.mark.unit
class TestMCPYAMLEdgeCases:
    """Edge case tests for MCP YAML integration."""

    def test_empty_parameter_mappings_list(self) -> None:
        """Test tool config with explicitly empty parameter mappings."""
        yaml_data = {
            "expose": True,
            "tool_name": "no_params",
            "description": "Tool without parameters",
            "parameter_mappings": [],
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.parameter_mappings == []
        assert config.get_required_parameters() == []
        assert config.get_optional_parameters() == []

    def test_optional_fields_omitted_in_yaml(self) -> None:
        """Test that omitted optional fields get defaults."""
        yaml_data = {
            "expose": True,
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.tool_name is None
        assert config.description is None
        assert config.parameter_mappings == []
        assert config.tags == []
        assert config.timeout_seconds == 30
        assert config.retry_enabled is True
        assert config.max_retries == 3

    def test_parameter_with_only_name(self) -> None:
        """Test parameter mapping with only name specified."""
        yaml_data = {
            "name": "simple_param",
        }
        mapping = ModelMCPParameterMapping.model_validate(yaml_data)
        assert mapping.name == "simple_param"
        assert mapping.parameter_type == EnumMCPParameterType.STRING
        assert mapping.required is True
        assert mapping.description == ""

    def test_unicode_in_yaml_values(self) -> None:
        """Test Unicode characters in YAML string values."""
        yaml_data = {
            "expose": True,
            "tool_name": "search_unicode",
            "description": "Search with Unicode: Japanese",
            "parameter_mappings": [
                {
                    "name": "query",
                    "description": "Japanese text: nihongo",
                },
            ],
        }
        config = ModelMCPToolConfig.model_validate(yaml_data)
        assert config.description is not None
        assert "Japanese" in config.description
        assert "nihongo" in config.parameter_mappings[0].description

    def test_numeric_default_values_preserved(self) -> None:
        """Test that numeric default values are preserved correctly."""
        yaml_data = {
            "name": "score",
            "parameter_type": "number",
            "default_value": 0.5,
            "min_value": 0.0,
            "max_value": 1.0,
        }
        mapping = ModelMCPParameterMapping.model_validate(yaml_data)
        assert mapping.default_value == 0.5
        assert mapping.min_value == 0.0
        assert mapping.max_value == 1.0

        schema = mapping.to_json_schema()
        assert schema["default"] == 0.5
        assert schema["minimum"] == 0.0
        assert schema["maximum"] == 1.0

    def test_boolean_default_value(self) -> None:
        """Test boolean parameter with default value."""
        yaml_data = {
            "name": "include_archived",
            "parameter_type": "boolean",
            "required": False,
            "default_value": False,
            "description": "Include archived items",
        }
        mapping = ModelMCPParameterMapping.model_validate(yaml_data)
        assert mapping.default_value is False

        schema = mapping.to_json_schema()
        assert schema["type"] == "boolean"
        assert schema["default"] is False

    def test_tool_descriptor_version_dict_format(self) -> None:
        """Test version field accepts structured dict format.

        Note: ModelMCPToolDescriptor.version is typed as ModelSemVer,
        and Pydantic can construct it from a dict with major/minor/patch.
        """
        yaml_data = {
            "name": "versioned_tool",
            "description": "Tool with version",
            "version": {"major": 2, "minor": 0, "patch": 0},
        }
        descriptor = ModelMCPToolDescriptor.model_validate(yaml_data)
        # Version should be a ModelSemVer instance
        assert descriptor.version.major == 2
        assert descriptor.version.minor == 0
        assert descriptor.version.patch == 0

    def test_return_schema_preserved(self) -> None:
        """Test return_schema is preserved through serialization."""
        return_schema = {
            "type": "object",
            "properties": {
                "results": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer"},
            },
        }
        descriptor = ModelMCPToolDescriptor(
            name="search",
            description="Search tool",
            return_schema=return_schema,
        )
        assert descriptor.return_schema == return_schema

        # Round-trip
        data = descriptor.model_dump()
        restored = ModelMCPToolDescriptor.model_validate(data)
        assert restored.return_schema == return_schema
