"""Unit tests for MCP models.

Comprehensive tests for Model Context Protocol models including:
- ModelMCPParameterMapping: Parameter mapping with JSON schema generation
- ModelMCPToolConfig: Tool configuration with parameter filtering
- ModelMCPToolDescriptor: Tool descriptor with schema generation
- ModelMCPInvocationRequest: Request envelope with argument access
- ModelMCPInvocationResponse: Response with factory methods and __bool__ override
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_mcp_parameter_type import EnumMCPParameterType
from omnibase_core.enums.enum_mcp_tool_type import EnumMCPToolType
from omnibase_core.models.mcp import (
    ModelMCPInvocationRequest,
    ModelMCPInvocationResponse,
    ModelMCPParameterMapping,
    ModelMCPToolConfig,
    ModelMCPToolDescriptor,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelMCPParameterMapping:
    """Tests for ModelMCPParameterMapping model."""

    def test_creation_with_required_field(self):
        """Test creation with only the required name field."""
        mapping = ModelMCPParameterMapping(name="query")

        assert mapping.name == "query"
        assert mapping.parameter_type == EnumMCPParameterType.STRING
        assert mapping.description == ""
        assert mapping.required is True
        assert mapping.default_value is None
        assert mapping.onex_field is None
        assert mapping.mcp_param_name is None
        assert mapping.enum_values is None
        assert mapping.min_value is None
        assert mapping.max_value is None
        assert mapping.min_length is None
        assert mapping.max_length is None
        assert mapping.pattern is None
        assert mapping.examples is None

    def test_creation_with_all_fields(self):
        """Test creation with all optional fields populated."""
        mapping = ModelMCPParameterMapping(
            name="limit",
            parameter_type=EnumMCPParameterType.INTEGER,
            description="Maximum number of results",
            required=False,
            default_value=10,
            onex_field="input.pagination.limit",
            mcp_param_name="max_results",
            enum_values=None,
            min_value=1,
            max_value=100,
            min_length=None,
            max_length=None,
            pattern=None,
            examples=[5, 10, 25, 50],
        )

        assert mapping.name == "limit"
        assert mapping.parameter_type == EnumMCPParameterType.INTEGER
        assert mapping.description == "Maximum number of results"
        assert mapping.required is False
        assert mapping.default_value == 10
        assert mapping.onex_field == "input.pagination.limit"
        assert mapping.mcp_param_name == "max_results"
        assert mapping.min_value == 1
        assert mapping.max_value == 100
        assert mapping.examples == [5, 10, 25, 50]

    def test_creation_with_string_constraints(self):
        """Test creation with string-specific constraints."""
        mapping = ModelMCPParameterMapping(
            name="email",
            parameter_type=EnumMCPParameterType.STRING,
            description="User email address",
            min_length=5,
            max_length=255,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )

        assert mapping.min_length == 5
        assert mapping.max_length == 255
        assert mapping.pattern == r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def test_creation_with_enum_values(self):
        """Test creation with enum values for validation."""
        mapping = ModelMCPParameterMapping(
            name="status",
            parameter_type=EnumMCPParameterType.STRING,
            description="Filter by status",
            enum_values=["pending", "active", "completed", "cancelled"],
        )

        assert mapping.enum_values == ["pending", "active", "completed", "cancelled"]

    def test_get_effective_name_without_override(self):
        """Test get_effective_name returns name when mcp_param_name is None."""
        mapping = ModelMCPParameterMapping(name="search_query")

        assert mapping.get_effective_name() == "search_query"

    def test_get_effective_name_with_override(self):
        """Test get_effective_name returns mcp_param_name when set."""
        mapping = ModelMCPParameterMapping(
            name="internal_query",
            mcp_param_name="query",
        )

        assert mapping.get_effective_name() == "query"

    def test_to_json_schema_basic(self):
        """Test to_json_schema with basic string parameter."""
        mapping = ModelMCPParameterMapping(
            name="query",
            parameter_type=EnumMCPParameterType.STRING,
            description="Search query string",
        )

        schema = mapping.to_json_schema()

        assert schema == {
            "type": "string",
            "description": "Search query string",
        }

    def test_to_json_schema_with_default(self):
        """Test to_json_schema includes default value."""
        mapping = ModelMCPParameterMapping(
            name="limit",
            parameter_type=EnumMCPParameterType.INTEGER,
            description="Result limit",
            default_value=10,
        )

        schema = mapping.to_json_schema()

        assert schema["default"] == 10

    def test_to_json_schema_with_enum(self):
        """Test to_json_schema includes enum values."""
        mapping = ModelMCPParameterMapping(
            name="format",
            parameter_type=EnumMCPParameterType.STRING,
            description="Output format",
            enum_values=["json", "xml", "csv"],
        )

        schema = mapping.to_json_schema()

        assert schema["enum"] == ["json", "xml", "csv"]

    def test_to_json_schema_with_numeric_constraints(self):
        """Test to_json_schema includes numeric constraints."""
        mapping = ModelMCPParameterMapping(
            name="page",
            parameter_type=EnumMCPParameterType.INTEGER,
            description="Page number",
            min_value=1,
            max_value=1000,
        )

        schema = mapping.to_json_schema()

        assert schema["minimum"] == 1
        assert schema["maximum"] == 1000

    def test_to_json_schema_with_string_constraints(self):
        """Test to_json_schema includes string constraints."""
        mapping = ModelMCPParameterMapping(
            name="username",
            parameter_type=EnumMCPParameterType.STRING,
            description="Username",
            min_length=3,
            max_length=32,
            pattern=r"^[a-zA-Z0-9_]+$",
        )

        schema = mapping.to_json_schema()

        assert schema["minLength"] == 3
        assert schema["maxLength"] == 32
        assert schema["pattern"] == r"^[a-zA-Z0-9_]+$"

    def test_to_json_schema_with_examples(self):
        """Test to_json_schema includes examples."""
        mapping = ModelMCPParameterMapping(
            name="tags",
            parameter_type=EnumMCPParameterType.ARRAY,
            description="Tags for filtering",
            examples=[["python", "api"], ["documentation"]],
        )

        schema = mapping.to_json_schema()

        assert schema["examples"] == [["python", "api"], ["documentation"]]

    def test_to_json_schema_full(self):
        """Test to_json_schema with all optional fields."""
        mapping = ModelMCPParameterMapping(
            name="score",
            parameter_type=EnumMCPParameterType.NUMBER,
            description="Score value",
            default_value=0.5,
            min_value=0.0,
            max_value=1.0,
            examples=[0.0, 0.5, 1.0],
        )

        schema = mapping.to_json_schema()

        assert schema == {
            "type": "number",
            "description": "Score value",
            "default": 0.5,
            "minimum": 0.0,
            "maximum": 1.0,
            "examples": [0.0, 0.5, 1.0],
        }

    def test_frozen_behavior(self):
        """Test that the model is immutable (frozen)."""
        mapping = ModelMCPParameterMapping(name="query")

        with pytest.raises(ValidationError):
            mapping.name = "new_name"

    def test_all_parameter_types(self):
        """Test creation with each EnumMCPParameterType value."""
        for param_type in EnumMCPParameterType:
            mapping = ModelMCPParameterMapping(
                name=f"test_{param_type.value}",
                parameter_type=param_type,
            )
            assert mapping.parameter_type == param_type
            schema = mapping.to_json_schema()
            assert schema["type"] == param_type.value


@pytest.mark.unit
class TestModelMCPToolConfig:
    """Tests for ModelMCPToolConfig model."""

    def test_creation_with_defaults(self):
        """Test creation with default values."""
        config = ModelMCPToolConfig()

        assert config.expose is False
        assert config.tool_name is None
        assert config.description is None
        assert config.parameter_mappings == []
        assert config.tags == []
        assert config.timeout_seconds == 30
        assert config.retry_enabled is True
        assert config.max_retries == 3
        assert config.requires_confirmation is False
        assert config.dangerous is False

    def test_creation_with_expose_true(self):
        """Test creation with expose enabled."""
        config = ModelMCPToolConfig(expose=True)

        assert config.expose is True
        assert config.is_enabled() is True

    def test_creation_with_expose_false(self):
        """Test creation with expose disabled."""
        config = ModelMCPToolConfig(expose=False)

        assert config.expose is False
        assert config.is_enabled() is False

    def test_creation_with_full_config(self):
        """Test creation with all fields populated."""
        params = [
            ModelMCPParameterMapping(name="query", required=True),
            ModelMCPParameterMapping(name="limit", required=False, default_value=10),
        ]

        config = ModelMCPToolConfig(
            expose=True,
            tool_name="search_documents",
            description="Search documents by query",
            parameter_mappings=params,
            tags=["search", "documents"],
            timeout_seconds=60,
            retry_enabled=True,
            max_retries=5,
            requires_confirmation=True,
            dangerous=True,
        )

        assert config.expose is True
        assert config.tool_name == "search_documents"
        assert config.description == "Search documents by query"
        assert len(config.parameter_mappings) == 2
        assert config.tags == ["search", "documents"]
        assert config.timeout_seconds == 60
        assert config.retry_enabled is True
        assert config.max_retries == 5
        assert config.requires_confirmation is True
        assert config.dangerous is True

    def test_is_enabled_method(self):
        """Test is_enabled returns expose value."""
        enabled_config = ModelMCPToolConfig(expose=True)
        disabled_config = ModelMCPToolConfig(expose=False)

        assert enabled_config.is_enabled() is True
        assert disabled_config.is_enabled() is False

    def test_get_required_parameters_empty(self):
        """Test get_required_parameters with no parameters."""
        config = ModelMCPToolConfig()

        assert config.get_required_parameters() == []

    def test_get_required_parameters_all_required(self):
        """Test get_required_parameters when all are required."""
        params = [
            ModelMCPParameterMapping(name="query", required=True),
            ModelMCPParameterMapping(name="filter", required=True),
        ]
        config = ModelMCPToolConfig(parameter_mappings=params)

        required = config.get_required_parameters()

        assert len(required) == 2
        assert all(p.required for p in required)

    def test_get_required_parameters_mixed(self):
        """Test get_required_parameters with mixed required/optional."""
        params = [
            ModelMCPParameterMapping(name="query", required=True),
            ModelMCPParameterMapping(name="limit", required=False),
            ModelMCPParameterMapping(name="offset", required=False),
            ModelMCPParameterMapping(name="filter", required=True),
        ]
        config = ModelMCPToolConfig(parameter_mappings=params)

        required = config.get_required_parameters()

        assert len(required) == 2
        assert {p.name for p in required} == {"query", "filter"}

    def test_get_optional_parameters_empty(self):
        """Test get_optional_parameters with no parameters."""
        config = ModelMCPToolConfig()

        assert config.get_optional_parameters() == []

    def test_get_optional_parameters_all_optional(self):
        """Test get_optional_parameters when all are optional."""
        params = [
            ModelMCPParameterMapping(name="limit", required=False),
            ModelMCPParameterMapping(name="offset", required=False),
        ]
        config = ModelMCPToolConfig(parameter_mappings=params)

        optional = config.get_optional_parameters()

        assert len(optional) == 2
        assert all(not p.required for p in optional)

    def test_get_optional_parameters_mixed(self):
        """Test get_optional_parameters with mixed required/optional."""
        params = [
            ModelMCPParameterMapping(name="query", required=True),
            ModelMCPParameterMapping(name="limit", required=False),
            ModelMCPParameterMapping(name="offset", required=False),
        ]
        config = ModelMCPToolConfig(parameter_mappings=params)

        optional = config.get_optional_parameters()

        assert len(optional) == 2
        assert {p.name for p in optional} == {"limit", "offset"}

    def test_timeout_seconds_constraints(self):
        """Test timeout_seconds validation constraints."""
        # Valid range
        config = ModelMCPToolConfig(timeout_seconds=1)
        assert config.timeout_seconds == 1

        config = ModelMCPToolConfig(timeout_seconds=600)
        assert config.timeout_seconds == 600

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPToolConfig(timeout_seconds=0)

        # Above maximum
        with pytest.raises(ValidationError):
            ModelMCPToolConfig(timeout_seconds=601)

    def test_max_retries_constraints(self):
        """Test max_retries validation constraints."""
        # Valid range
        config = ModelMCPToolConfig(max_retries=0)
        assert config.max_retries == 0

        config = ModelMCPToolConfig(max_retries=10)
        assert config.max_retries == 10

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPToolConfig(max_retries=-1)

        # Above maximum
        with pytest.raises(ValidationError):
            ModelMCPToolConfig(max_retries=11)

    def test_frozen_behavior(self):
        """Test that the model is immutable (frozen)."""
        config = ModelMCPToolConfig(expose=True)

        with pytest.raises(ValidationError):
            config.expose = False


@pytest.mark.unit
class TestModelMCPToolDescriptor:
    """Tests for ModelMCPToolDescriptor model."""

    def test_creation_with_required_fields(self):
        """Test creation with only required fields."""
        descriptor = ModelMCPToolDescriptor(
            name="search_tool",
            description="A tool for searching",
        )

        assert descriptor.name == "search_tool"
        assert descriptor.description == "A tool for searching"
        assert descriptor.tool_type == EnumMCPToolType.FUNCTION
        assert descriptor.version == "1.0.0"
        assert descriptor.parameters == []
        assert descriptor.return_schema is None
        assert descriptor.input_schema is None
        assert descriptor.timeout_seconds == 30
        assert descriptor.retry_count == 3
        assert descriptor.requires_auth is False
        assert descriptor.tags == []
        assert descriptor.metadata == {}
        assert descriptor.node_name is None
        assert descriptor.node_version is None
        assert descriptor.dangerous is False
        assert descriptor.requires_confirmation is False

    def test_creation_with_all_fields(self):
        """Test creation with all fields populated."""
        params = [
            ModelMCPParameterMapping(name="query", required=True),
            ModelMCPParameterMapping(name="limit", required=False),
        ]
        semver = ModelSemVer(major=2, minor=1, patch=0)

        descriptor = ModelMCPToolDescriptor(
            name="advanced_search",
            tool_type=EnumMCPToolType.FUNCTION,
            description="Advanced search tool",
            version="2.1.0",
            parameters=params,
            return_schema={"type": "array", "items": {"type": "object"}},
            input_schema=None,  # Will be generated
            timeout_seconds=120,
            retry_count=5,
            requires_auth=True,
            tags=["search", "advanced", "api"],
            metadata={"author": "test", "category": "search"},
            node_name="NodeSearchCompute",
            node_version=semver,
            dangerous=True,
            requires_confirmation=True,
        )

        assert descriptor.name == "advanced_search"
        assert descriptor.tool_type == EnumMCPToolType.FUNCTION
        assert descriptor.version == "2.1.0"
        assert len(descriptor.parameters) == 2
        assert descriptor.return_schema == {
            "type": "array",
            "items": {"type": "object"},
        }
        assert descriptor.timeout_seconds == 120
        assert descriptor.retry_count == 5
        assert descriptor.requires_auth is True
        assert descriptor.tags == ["search", "advanced", "api"]
        assert descriptor.metadata == {"author": "test", "category": "search"}
        assert descriptor.node_name == "NodeSearchCompute"
        assert descriptor.node_version == semver
        assert descriptor.dangerous is True
        assert descriptor.requires_confirmation is True

    def test_get_required_parameters_empty(self):
        """Test get_required_parameters with no parameters."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
        )

        assert descriptor.get_required_parameters() == []

    def test_get_required_parameters_mixed(self):
        """Test get_required_parameters with mixed parameters."""
        params = [
            ModelMCPParameterMapping(name="required_1", required=True),
            ModelMCPParameterMapping(name="optional_1", required=False),
            ModelMCPParameterMapping(name="required_2", required=True),
        ]
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            parameters=params,
        )

        required = descriptor.get_required_parameters()

        assert len(required) == 2
        assert {p.name for p in required} == {"required_1", "required_2"}

    def test_get_optional_parameters_mixed(self):
        """Test get_optional_parameters with mixed parameters."""
        params = [
            ModelMCPParameterMapping(name="required_1", required=True),
            ModelMCPParameterMapping(name="optional_1", required=False),
            ModelMCPParameterMapping(name="optional_2", required=False),
        ]
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            parameters=params,
        )

        optional = descriptor.get_optional_parameters()

        assert len(optional) == 2
        assert {p.name for p in optional} == {"optional_1", "optional_2"}

    def test_to_input_schema_returns_existing(self):
        """Test to_input_schema returns input_schema if already set."""
        existing_schema = {
            "type": "object",
            "properties": {"custom": {"type": "string"}},
            "required": ["custom"],
        }
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            input_schema=existing_schema,
        )

        schema = descriptor.to_input_schema()

        assert schema == existing_schema

    def test_to_input_schema_generates_from_parameters(self):
        """Test to_input_schema generates schema from parameters."""
        params = [
            ModelMCPParameterMapping(
                name="query",
                parameter_type=EnumMCPParameterType.STRING,
                description="Search query",
                required=True,
            ),
            ModelMCPParameterMapping(
                name="limit",
                parameter_type=EnumMCPParameterType.INTEGER,
                description="Result limit",
                required=False,
                default_value=10,
            ),
        ]
        descriptor = ModelMCPToolDescriptor(
            name="search_tool",
            description="Search tool",
            parameters=params,
        )

        schema = descriptor.to_input_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["query"]["description"] == "Search query"
        assert schema["properties"]["limit"]["type"] == "integer"
        assert schema["properties"]["limit"]["default"] == 10
        assert schema["required"] == ["query"]

    def test_to_input_schema_no_required_parameters(self):
        """Test to_input_schema with no required parameters."""
        params = [
            ModelMCPParameterMapping(name="limit", required=False),
            ModelMCPParameterMapping(name="offset", required=False),
        ]
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            parameters=params,
        )

        schema = descriptor.to_input_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" not in schema  # No required params

    def test_to_input_schema_uses_effective_name(self):
        """Test to_input_schema uses mcp_param_name when set."""
        params = [
            ModelMCPParameterMapping(
                name="internal_query",
                mcp_param_name="q",
                required=True,
            ),
        ]
        descriptor = ModelMCPToolDescriptor(
            name="search_tool",
            description="Search tool",
            parameters=params,
        )

        schema = descriptor.to_input_schema()

        assert "q" in schema["properties"]
        assert "internal_query" not in schema["properties"]
        assert schema["required"] == ["q"]

    def test_has_tag_exact_match(self):
        """Test has_tag with exact case match."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            tags=["Search", "API", "Documents"],
        )

        assert descriptor.has_tag("Search") is True
        assert descriptor.has_tag("API") is True
        assert descriptor.has_tag("Documents") is True

    def test_has_tag_case_insensitive(self):
        """Test has_tag is case-insensitive."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            tags=["Search", "API", "Documents"],
        )

        assert descriptor.has_tag("search") is True
        assert descriptor.has_tag("SEARCH") is True
        assert descriptor.has_tag("api") is True
        assert descriptor.has_tag("documents") is True

    def test_has_tag_not_found(self):
        """Test has_tag returns False for missing tags."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            tags=["Search", "API"],
        )

        assert descriptor.has_tag("missing") is False
        assert descriptor.has_tag("other") is False

    def test_has_tag_empty_tags(self):
        """Test has_tag with empty tags list."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
        )

        assert descriptor.has_tag("any") is False

    def test_is_from_onex_node_true(self):
        """Test is_from_onex_node returns True when node_name is set."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
            node_name="NodeSearchCompute",
        )

        assert descriptor.is_from_onex_node() is True

    def test_is_from_onex_node_false(self):
        """Test is_from_onex_node returns False when node_name is None."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
        )

        assert descriptor.is_from_onex_node() is False

    def test_all_tool_types(self):
        """Test creation with each EnumMCPToolType value."""
        for tool_type in EnumMCPToolType:
            descriptor = ModelMCPToolDescriptor(
                name=f"test_{tool_type.value}",
                description=f"Tool of type {tool_type.value}",
                tool_type=tool_type,
            )
            assert descriptor.tool_type == tool_type

    def test_frozen_behavior(self):
        """Test that the model is immutable (frozen)."""
        descriptor = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test tool",
        )

        with pytest.raises(ValidationError):
            descriptor.name = "new_name"

    def test_timeout_seconds_constraints(self):
        """Test timeout_seconds validation constraints."""
        # Valid range
        descriptor = ModelMCPToolDescriptor(
            name="test",
            description="test",
            timeout_seconds=1,
        )
        assert descriptor.timeout_seconds == 1

        descriptor = ModelMCPToolDescriptor(
            name="test",
            description="test",
            timeout_seconds=600,
        )
        assert descriptor.timeout_seconds == 600

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPToolDescriptor(
                name="test",
                description="test",
                timeout_seconds=0,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ModelMCPToolDescriptor(
                name="test",
                description="test",
                timeout_seconds=601,
            )

    def test_retry_count_constraints(self):
        """Test retry_count validation constraints."""
        # Valid range
        descriptor = ModelMCPToolDescriptor(
            name="test",
            description="test",
            retry_count=0,
        )
        assert descriptor.retry_count == 0

        descriptor = ModelMCPToolDescriptor(
            name="test",
            description="test",
            retry_count=10,
        )
        assert descriptor.retry_count == 10

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPToolDescriptor(
                name="test",
                description="test",
                retry_count=-1,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ModelMCPToolDescriptor(
                name="test",
                description="test",
                retry_count=11,
            )


@pytest.mark.unit
class TestModelMCPInvocationRequest:
    """Tests for ModelMCPInvocationRequest model."""

    def test_creation_with_required_field(self):
        """Test creation with only required tool_name."""
        request = ModelMCPInvocationRequest(tool_name="search_tool")

        assert request.tool_name == "search_tool"
        assert request.arguments == {}
        assert request.correlation_id is None
        assert request.request_id is None
        assert request.timeout_ms is None
        assert request.metadata == {}

    def test_creation_with_all_fields(self):
        """Test creation with all fields populated."""
        correlation_id = uuid4()
        request_id = uuid4()

        request = ModelMCPInvocationRequest(
            tool_name="advanced_search",
            arguments={"query": "test", "limit": 10},
            correlation_id=correlation_id,
            request_id=request_id,
            timeout_ms=5000,
            metadata={"source": "api", "user_id": "123"},
        )

        assert request.tool_name == "advanced_search"
        assert request.arguments == {"query": "test", "limit": 10}
        assert request.correlation_id == correlation_id
        assert request.request_id == request_id
        assert request.timeout_ms == 5000
        assert request.metadata == {"source": "api", "user_id": "123"}

    def test_has_correlation_id_true(self):
        """Test has_correlation_id returns True when correlation_id is set."""
        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            correlation_id=uuid4(),
        )

        assert request.has_correlation_id() is True

    def test_has_correlation_id_false(self):
        """Test has_correlation_id returns False when correlation_id is None."""
        request = ModelMCPInvocationRequest(tool_name="test_tool")

        assert request.has_correlation_id() is False

    def test_get_argument_existing_key(self):
        """Test get_argument returns value for existing key."""
        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            arguments={"query": "test value", "limit": 50},
        )

        assert request.get_argument("query") == "test value"
        assert request.get_argument("limit") == 50

    def test_get_argument_missing_key_no_default(self):
        """Test get_argument returns None for missing key without default."""
        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            arguments={"query": "test"},
        )

        assert request.get_argument("missing") is None

    def test_get_argument_missing_key_with_default(self):
        """Test get_argument returns default for missing key."""
        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            arguments={"query": "test"},
        )

        assert request.get_argument("limit", 10) == 10
        assert request.get_argument("offset", "default_value") == "default_value"

    def test_get_argument_none_value(self):
        """Test get_argument returns None when value is explicitly None."""
        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            arguments={"nullable_field": None},
        )

        # Returns None because the value is actually None
        assert request.get_argument("nullable_field") is None
        # But won't use default because key exists
        assert request.get_argument("nullable_field", "default") is None

    def test_timeout_ms_constraints(self):
        """Test timeout_ms validation constraints."""
        # Valid values
        request = ModelMCPInvocationRequest(tool_name="test", timeout_ms=0)
        assert request.timeout_ms == 0

        request = ModelMCPInvocationRequest(tool_name="test", timeout_ms=60000)
        assert request.timeout_ms == 60000

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPInvocationRequest(tool_name="test", timeout_ms=-1)

    def test_frozen_behavior(self):
        """Test that the model is immutable (frozen)."""
        request = ModelMCPInvocationRequest(tool_name="test_tool")

        with pytest.raises(ValidationError):
            request.tool_name = "new_name"

    def test_uuid_fields(self):
        """Test that UUID fields accept valid UUIDs."""
        correlation_id = UUID("12345678-1234-5678-1234-567812345678")
        request_id = UUID("87654321-4321-8765-4321-876543218765")

        request = ModelMCPInvocationRequest(
            tool_name="test_tool",
            correlation_id=correlation_id,
            request_id=request_id,
        )

        assert request.correlation_id == correlation_id
        assert request.request_id == request_id

    def test_complex_arguments(self):
        """Test with complex nested arguments."""
        request = ModelMCPInvocationRequest(
            tool_name="complex_tool",
            arguments={
                "filters": {
                    "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
                    "tags": ["important", "urgent"],
                },
                "options": {"include_archived": False, "max_depth": 5},
            },
        )

        assert request.get_argument("filters")["date_range"]["start"] == "2024-01-01"
        assert request.get_argument("options")["max_depth"] == 5


@pytest.mark.unit
class TestModelMCPInvocationResponse:
    """Tests for ModelMCPInvocationResponse model."""

    def test_success_response_factory_string(self):
        """Test success_response factory with string content."""
        response = ModelMCPInvocationResponse.success_response(
            content="Operation completed successfully",
        )

        assert response.success is True
        assert response.content == "Operation completed successfully"
        assert response.is_error is False
        assert response.error_message is None
        assert response.error_code is None
        assert response.correlation_id is None
        assert response.request_id is None
        assert response.execution_time_ms is None
        assert response.metadata == {}

    def test_success_response_factory_dict(self):
        """Test success_response factory with dict content."""
        content = {"results": [{"id": 1}, {"id": 2}], "total": 2}
        response = ModelMCPInvocationResponse.success_response(content=content)

        assert response.success is True
        assert response.content == content
        assert response.is_error is False

    def test_success_response_factory_list(self):
        """Test success_response factory with list content."""
        content = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = ModelMCPInvocationResponse.success_response(content=content)

        assert response.success is True
        assert response.content == content
        assert response.is_error is False

    def test_success_response_factory_with_all_options(self):
        """Test success_response factory with all optional parameters."""
        correlation_id = uuid4()
        request_id = uuid4()

        response = ModelMCPInvocationResponse.success_response(
            content={"result": "value"},
            correlation_id=correlation_id,
            request_id=request_id,
            execution_time_ms=123.456,
            metadata={"source": "test", "version": "1.0"},
        )

        assert response.success is True
        assert response.content == {"result": "value"}
        assert response.is_error is False
        assert response.correlation_id == correlation_id
        assert response.request_id == request_id
        assert response.execution_time_ms == 123.456
        assert response.metadata == {"source": "test", "version": "1.0"}

    def test_error_response_factory_basic(self):
        """Test error_response factory with basic error."""
        response = ModelMCPInvocationResponse.error_response(
            error_message="Something went wrong",
        )

        assert response.success is False
        assert response.content == "Something went wrong"
        assert response.is_error is True
        assert response.error_message == "Something went wrong"
        assert response.error_code is None

    def test_error_response_factory_with_code(self):
        """Test error_response factory with error code."""
        response = ModelMCPInvocationResponse.error_response(
            error_message="Invalid input provided",
            error_code="VALIDATION_ERROR",
        )

        assert response.success is False
        assert response.is_error is True
        assert response.error_message == "Invalid input provided"
        assert response.error_code == "VALIDATION_ERROR"

    def test_error_response_factory_with_all_options(self):
        """Test error_response factory with all optional parameters."""
        correlation_id = uuid4()
        request_id = uuid4()

        response = ModelMCPInvocationResponse.error_response(
            error_message="Tool execution failed",
            error_code="EXECUTION_ERROR",
            correlation_id=correlation_id,
            request_id=request_id,
            execution_time_ms=50.5,
            metadata={"attempt": 3, "retryable": False},
        )

        assert response.success is False
        assert response.is_error is True
        assert response.error_message == "Tool execution failed"
        assert response.error_code == "EXECUTION_ERROR"
        assert response.correlation_id == correlation_id
        assert response.request_id == request_id
        assert response.execution_time_ms == 50.5
        assert response.metadata == {"attempt": 3, "retryable": False}

    def test_bool_success_response(self):
        """Test __bool__ returns True for successful response."""
        response = ModelMCPInvocationResponse.success_response(content="ok")

        assert bool(response) is True
        assert response  # Should be truthy

    def test_bool_error_response(self):
        """Test __bool__ returns False for error response."""
        response = ModelMCPInvocationResponse.error_response(
            error_message="error",
        )

        assert bool(response) is False
        assert not response  # Should be falsy

    def test_bool_override_with_success_false(self):
        """Verify __bool__ returns False when success=False.

        This test explicitly validates the non-standard __bool__ override
        documented in ModelMCPInvocationResponse. Unlike standard Pydantic
        models where bool(model) always returns True, this model returns
        False when success is False.
        """
        response = ModelMCPInvocationResponse.error_response("Failed")
        assert response.success is False
        assert bool(response) is False  # Explicit bool() check

    def test_bool_success_but_is_error(self):
        """Test __bool__ returns False when success=True but is_error=True."""
        # Edge case: manually constructed inconsistent state
        response = ModelMCPInvocationResponse(
            success=True,
            content="content",
            is_error=True,
        )

        assert bool(response) is False

    def test_bool_not_success_not_error(self):
        """Test __bool__ returns False when success=False even if is_error=False."""
        response = ModelMCPInvocationResponse(
            success=False,
            content="content",
            is_error=False,
        )

        assert bool(response) is False

    def test_direct_creation_success(self):
        """Test direct creation of successful response."""
        response = ModelMCPInvocationResponse(
            success=True,
            content="Result data",
            is_error=False,
        )

        assert response.success is True
        assert response.content == "Result data"
        assert response.is_error is False
        assert bool(response) is True

    def test_direct_creation_error(self):
        """Test direct creation of error response."""
        response = ModelMCPInvocationResponse(
            success=False,
            content="Error details",
            is_error=True,
            error_message="Full error message",
            error_code="ERR_001",
        )

        assert response.success is False
        assert response.content == "Error details"
        assert response.is_error is True
        assert response.error_message == "Full error message"
        assert response.error_code == "ERR_001"
        assert bool(response) is False

    def test_frozen_behavior(self):
        """Test that the model is immutable (frozen)."""
        response = ModelMCPInvocationResponse.success_response(content="test")

        with pytest.raises(ValidationError):
            response.success = False

    def test_execution_time_ms_constraints(self):
        """Test execution_time_ms validation constraints."""
        # Valid values
        response = ModelMCPInvocationResponse.success_response(
            content="test",
            execution_time_ms=0.0,
        )
        assert response.execution_time_ms == 0.0

        response = ModelMCPInvocationResponse.success_response(
            content="test",
            execution_time_ms=0.001,  # Sub-millisecond precision
        )
        assert response.execution_time_ms == 0.001

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMCPInvocationResponse(
                success=True,
                content="test",
                execution_time_ms=-1.0,
            )

    def test_content_types(self):
        """Test all supported content types."""
        # String content
        str_response = ModelMCPInvocationResponse.success_response(content="string")
        assert isinstance(str_response.content, str)

        # Dict content
        dict_response = ModelMCPInvocationResponse.success_response(
            content={"key": "value"},
        )
        assert isinstance(dict_response.content, dict)

        # List content
        list_response = ModelMCPInvocationResponse.success_response(
            content=[1, 2, 3],
        )
        assert isinstance(list_response.content, list)

    def test_use_in_conditional(self):
        """Test using response in conditional statements."""
        success = ModelMCPInvocationResponse.success_response(content="ok")
        error = ModelMCPInvocationResponse.error_response(error_message="fail")

        # Test in if statement
        if success:
            result = "success branch"
        else:
            result = "error branch"
        assert result == "success branch"

        if error:
            result = "success branch"
        else:
            result = "error branch"
        assert result == "error branch"

        # Test with ternary
        assert ("ok" if success else "fail") == "ok"
        assert ("ok" if error else "fail") == "fail"


@pytest.mark.unit
class TestModelMCPEdgeCases:
    """Test edge cases and integration scenarios for MCP models."""

    def test_parameter_mapping_serialization_roundtrip(self):
        """Test parameter mapping serializes and deserializes correctly."""
        original = ModelMCPParameterMapping(
            name="test",
            parameter_type=EnumMCPParameterType.INTEGER,
            description="Test parameter",
            required=True,
            default_value=42,
            min_value=0,
            max_value=100,
        )

        json_data = original.model_dump()
        restored = ModelMCPParameterMapping.model_validate(json_data)

        assert restored.name == original.name
        assert restored.parameter_type == original.parameter_type
        assert restored.description == original.description
        assert restored.required == original.required
        assert restored.default_value == original.default_value
        assert restored.min_value == original.min_value
        assert restored.max_value == original.max_value

    def test_tool_config_serialization_roundtrip(self):
        """Test tool config serializes and deserializes correctly."""
        original = ModelMCPToolConfig(
            expose=True,
            tool_name="test_tool",
            description="A test tool",
            parameter_mappings=[
                ModelMCPParameterMapping(name="param1", required=True),
            ],
            tags=["test"],
            timeout_seconds=60,
        )

        json_data = original.model_dump()
        restored = ModelMCPToolConfig.model_validate(json_data)

        assert restored.expose == original.expose
        assert restored.tool_name == original.tool_name
        assert len(restored.parameter_mappings) == 1
        assert restored.parameter_mappings[0].name == "param1"

    def test_tool_descriptor_serialization_roundtrip(self):
        """Test tool descriptor serializes and deserializes correctly."""
        semver = ModelSemVer(major=1, minor=2, patch=3)
        original = ModelMCPToolDescriptor(
            name="test_tool",
            description="Test description",
            version="1.2.3",
            node_name="TestNode",
            node_version=semver,
            parameters=[
                ModelMCPParameterMapping(name="p1", required=True),
            ],
            tags=["tag1", "tag2"],
        )

        json_data = original.model_dump()
        restored = ModelMCPToolDescriptor.model_validate(json_data)

        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.node_name == original.node_name
        assert restored.node_version.major == 1
        assert restored.node_version.minor == 2
        assert restored.node_version.patch == 3
        assert len(restored.tags) == 2

    def test_invocation_request_serialization_roundtrip(self):
        """Test invocation request serializes and deserializes correctly."""
        correlation_id = uuid4()
        original = ModelMCPInvocationRequest(
            tool_name="test",
            arguments={"key": "value"},
            correlation_id=correlation_id,
            timeout_ms=1000,
        )

        json_data = original.model_dump()
        restored = ModelMCPInvocationRequest.model_validate(json_data)

        assert restored.tool_name == original.tool_name
        assert restored.arguments == original.arguments
        assert restored.correlation_id == correlation_id
        assert restored.timeout_ms == 1000

    def test_invocation_response_serialization_roundtrip(self):
        """Test invocation response serializes and deserializes correctly."""
        original = ModelMCPInvocationResponse.success_response(
            content={"data": [1, 2, 3]},
            execution_time_ms=42.5,
        )

        json_data = original.model_dump()
        restored = ModelMCPInvocationResponse.model_validate(json_data)

        assert restored.success == original.success
        assert restored.content == original.content
        assert restored.execution_time_ms == original.execution_time_ms
        assert bool(restored) is True

    def test_empty_arguments_handling(self):
        """Test handling of empty arguments in request."""
        request = ModelMCPInvocationRequest(
            tool_name="no_args_tool",
            arguments={},
        )

        assert request.arguments == {}
        assert request.get_argument("any_key") is None
        assert request.get_argument("any_key", "default") == "default"

    def test_empty_metadata_handling(self):
        """Test handling of empty metadata in request and response."""
        request = ModelMCPInvocationRequest(tool_name="test")
        response = ModelMCPInvocationResponse.success_response(content="ok")

        assert request.metadata == {}
        assert response.metadata == {}

    def test_descriptor_from_config(self):
        """Test creating descriptor from config-like data."""
        config = ModelMCPToolConfig(
            expose=True,
            tool_name="configured_tool",
            description="Tool from config",
            parameter_mappings=[
                ModelMCPParameterMapping(
                    name="query",
                    parameter_type=EnumMCPParameterType.STRING,
                    required=True,
                    description="Search query",
                ),
            ],
            tags=["search", "api"],
            timeout_seconds=45,
        )

        # Create descriptor using config values
        descriptor = ModelMCPToolDescriptor(
            name=config.tool_name or "default_name",
            description=config.description or "",
            parameters=config.parameter_mappings,
            tags=config.tags,
            timeout_seconds=config.timeout_seconds,
        )

        assert descriptor.name == "configured_tool"
        assert descriptor.description == "Tool from config"
        assert len(descriptor.parameters) == 1
        assert descriptor.tags == ["search", "api"]
        assert descriptor.timeout_seconds == 45

        # Generate schema
        schema = descriptor.to_input_schema()
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["required"] == ["query"]
