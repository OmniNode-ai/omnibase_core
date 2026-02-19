# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for MixinEffectExecution.

Tests the effect execution mixin for contract-driven I/O operations.
This module provides comprehensive coverage for:
- Handler protocol resolution
- Operation extraction from effect_subcontract
- Filesystem content resolution
- Retry logic (correct counting)
- Circuit breaker management
- Template variable resolution with depth limits
- Idempotency handling
- Transaction management
- Rollback failure handling

VERSION: 1.0.0 - Aligned with MixinEffectExecution v1.0.0
"""

import importlib.util
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit

from omnibase_core.enums import EnumEffectType, EnumTransactionState
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_resolved_context import (
    ModelResolvedDbContext,
    ModelResolvedFilesystemContext,
    ModelResolvedHttpContext,
    ModelResolvedKafkaContext,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class MockContainer:
    """Mock container for dependency injection."""

    def __init__(self) -> None:
        """Initialize mock container."""
        self._services: dict[str, Any] = {}

    def register_service(self, name: str, service: Any) -> None:
        """Register a mock service."""
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        if name not in self._services:
            raise KeyError(f"Service not found: {name}")
        return self._services[name]


@pytest.mark.unit
class TestNode(MixinEffectExecution):
    """Test node class using effect execution mixin."""

    def __init__(self, container: MockContainer | None = None) -> None:
        """Initialize test node with mock container."""
        self.node_id: UUID = uuid4()
        self.container: MockContainer = container or MockContainer()
        super().__init__()
        # Initialize _circuit_breakers as required by MixinEffectExecution.
        # In production, NodeEffect initializes this; for tests, we do it here.
        self._circuit_breakers: dict[UUID, ModelCircuitBreaker] = {}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_container() -> MockContainer:
    """Create mock container fixture."""
    return MockContainer()


@pytest.fixture
def test_node(mock_container: MockContainer) -> TestNode:
    """Create test node fixture."""
    return TestNode(container=mock_container)


@pytest.fixture
def basic_http_input() -> ModelEffectInput:
    """Create basic HTTP effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.API_CALL,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "http",
                        "url_template": "https://api.example.com/users/123",
                        "method": "GET",
                    },
                    "operation_timeout_ms": 5000,
                }
            ]
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


@pytest.fixture
def http_input_with_templates() -> ModelEffectInput:
    """Create HTTP effect input with template placeholders."""
    return ModelEffectInput(
        effect_type=EnumEffectType.API_CALL,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "http",
                        "url_template": "https://api.example.com/users/${input.user_id}",
                        "method": "POST",
                        "headers": {"Authorization": "Bearer ${env.API_TOKEN}"},
                        "body_template": '{"name": "${input.name}"}',
                    },
                    "operation_timeout_ms": 5000,
                }
            ],
            "user_id": "456",
            "name": "Test User",
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


@pytest.fixture
def db_input() -> ModelEffectInput:
    """Create database effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.DATABASE_OPERATION,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "db",
                        "operation": "select",
                        "connection_name": "primary_db",
                        "query_template": "SELECT * FROM users WHERE id = $1",
                        "query_params": ["${input.user_id}"],
                    },
                    "operation_timeout_ms": 30000,
                }
            ],
            "user_id": "123",
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


@pytest.fixture
def kafka_input() -> ModelEffectInput:
    """Create Kafka effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.EVENT_EMISSION,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "kafka",
                        "topic": "user-events",
                        "payload_template": '{"user_id": "${input.user_id}"}',
                        "partition_key_template": "${input.user_id}",
                    },
                    "operation_timeout_ms": 10000,
                }
            ],
            "user_id": "789",
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


@pytest.fixture
def filesystem_write_input() -> ModelEffectInput:
    """Create filesystem write effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.FILE_OPERATION,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "filesystem",
                        "file_path_template": "/data/output/${input.filename}.json",
                        "operation": "write",
                        "atomic": True,
                        "create_dirs": True,
                    },
                    "operation_timeout_ms": 5000,
                }
            ],
            "filename": "test_output",
            "file_content": '{"data": "test"}',
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


@pytest.fixture
def filesystem_read_input() -> ModelEffectInput:
    """Create filesystem read effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.FILE_OPERATION,
        operation_data={
            "operations": [
                {
                    "io_config": {
                        "handler_type": "filesystem",
                        "file_path_template": "/data/input/${input.filename}.json",
                        "operation": "read",
                        "atomic": False,
                    },
                    "operation_timeout_ms": 5000,
                }
            ],
            "filename": "test_input",
        },
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


# =============================================================================
# TEST CLASSES
# =============================================================================


@pytest.mark.unit
class TestMixinEffectExecutionInit:
    """Test MixinEffectExecution initialization."""

    def test_mixin_init_creates_circuit_breakers_dict(
        self, mock_container: MockContainer
    ) -> None:
        """Test that mixin initialization creates empty circuit breakers dict."""
        node = TestNode(container=mock_container)
        assert hasattr(node, "_circuit_breakers")
        assert isinstance(node._circuit_breakers, dict)
        assert len(node._circuit_breakers) == 0

    def test_mixin_init_preserves_node_id(self, mock_container: MockContainer) -> None:
        """Test that mixin initialization preserves node_id from mixing class."""
        node = TestNode(container=mock_container)
        assert hasattr(node, "node_id")
        assert isinstance(node.node_id, UUID)

    def test_mixin_init_preserves_container(
        self, mock_container: MockContainer
    ) -> None:
        """Test that mixin initialization preserves container from mixing class."""
        node = TestNode(container=mock_container)
        assert hasattr(node, "container")
        assert node.container is mock_container


@pytest.mark.unit
class TestParseIOConfig:
    """Test _parse_io_config method for all handler types."""

    def test_parse_http_config(self, test_node: TestNode) -> None:
        """Test parsing HTTP IO config."""
        from omnibase_core.models.operations import ModelEffectOperationConfig

        operation_config = ModelEffectOperationConfig.from_dict(
            {
                "io_config": {
                    "handler_type": "http",
                    "url_template": "https://api.example.com/test",
                    "method": "GET",
                }
            }
        )
        result = test_node._parse_io_config(operation_config)
        assert isinstance(result, ModelHttpIOConfig)
        assert result.url_template == "https://api.example.com/test"
        assert result.method == "GET"

    def test_parse_db_config(self, test_node: TestNode) -> None:
        """Test parsing DB IO config."""
        from omnibase_core.models.operations import ModelEffectOperationConfig

        operation_config = ModelEffectOperationConfig.from_dict(
            {
                "io_config": {
                    "handler_type": "db",
                    "operation": "select",
                    "connection_name": "primary",
                    "query_template": "SELECT * FROM users",
                }
            }
        )
        result = test_node._parse_io_config(operation_config)
        assert isinstance(result, ModelDbIOConfig)
        assert result.operation == "select"
        assert result.connection_name == "primary"

    def test_parse_kafka_config(self, test_node: TestNode) -> None:
        """Test parsing Kafka IO config."""
        from omnibase_core.models.operations import ModelEffectOperationConfig

        operation_config = ModelEffectOperationConfig.from_dict(
            {
                "io_config": {
                    "handler_type": "kafka",
                    "topic": "test-topic",
                    "payload_template": '{"test": "data"}',
                }
            }
        )
        result = test_node._parse_io_config(operation_config)
        assert isinstance(result, ModelKafkaIOConfig)
        assert result.topic == "test-topic"

    def test_parse_filesystem_config(self, test_node: TestNode) -> None:
        """Test parsing Filesystem IO config."""
        from omnibase_core.models.operations import ModelEffectOperationConfig

        operation_config = ModelEffectOperationConfig.from_dict(
            {
                "io_config": {
                    "handler_type": "filesystem",
                    "file_path_template": "/data/test.txt",
                    "operation": "read",
                    "atomic": False,
                }
            }
        )
        result = test_node._parse_io_config(operation_config)
        assert isinstance(result, ModelFilesystemIOConfig)
        assert result.operation == "read"

    def test_parse_missing_io_config_raises_error(self, test_node: TestNode) -> None:
        """Test that missing io_config raises validation error.

        NOTE: With typed ModelEffectOperationConfig, validation happens
        at model creation time, not in _parse_io_config. This is actually
        better - earlier validation catches errors sooner.
        """
        from pydantic import ValidationError

        from omnibase_core.models.operations import ModelEffectOperationConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectOperationConfig.from_dict({})
        errors = exc_info.value.errors()
        assert any("io_config" in error.get("msg", "") for error in errors)

    def test_parse_unknown_handler_type_raises_error(self, test_node: TestNode) -> None:
        """Test that unknown handler type raises ValidationError during parsing.

        Since io_config uses a discriminated union, unknown handler types are
        rejected at model validation time (before reaching _parse_io_config).
        """
        from pydantic import ValidationError

        from omnibase_core.models.operations import ModelEffectOperationConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectOperationConfig.from_dict(
                {"io_config": {"handler_type": "unknown"}}
            )
        errors = exc_info.value.errors()
        assert any(error["type"] == "union_tag_invalid" for error in errors)


@pytest.mark.unit
class TestResolveIOContext:
    """Test _resolve_io_context template resolution."""

    def test_resolve_http_context_no_templates(self, test_node: TestNode) -> None:
        """Test resolving HTTP context without templates."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedHttpContext)
        assert result.url == "https://api.example.com/users"
        assert result.method == "GET"

    def test_resolve_http_context_with_input_templates(
        self, test_node: TestNode
    ) -> None:
        """Test resolving HTTP context with input.* templates."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"user_id": "123"},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedHttpContext)
        assert result.url == "https://api.example.com/users/123"

    def test_resolve_http_context_with_env_templates(self, test_node: TestNode) -> None:
        """Test resolving HTTP context with env.* templates."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"Authorization": "Bearer ${env.TEST_TOKEN}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        with patch.dict(os.environ, {"TEST_TOKEN": "secret_token_value"}):
            result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedHttpContext)
        assert result.headers["Authorization"] == "Bearer secret_token_value"

    def test_resolve_http_context_missing_env_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that missing env variable raises ModelOnexError."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"Authorization": "Bearer ${env.NONEXISTENT_VAR}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        # Ensure the env var does not exist
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._resolve_io_context(io_config, input_data)
            assert "Environment variable not found" in str(exc_info.value)

    def test_resolve_http_context_with_body_template(self, test_node: TestNode) -> None:
        """Test resolving HTTP context with body template."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="POST",
            body_template='{"name": "${input.name}", "email": "${input.email}"}',
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"name": "John Doe", "email": "john@example.com"},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedHttpContext)
        assert result.body == '{"name": "John Doe", "email": "john@example.com"}'

    def test_resolve_db_context(self, test_node: TestNode) -> None:
        """Test resolving DB context with template parameters."""
        io_config = ModelDbIOConfig(
            operation="select",
            connection_name="primary",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data={"user_id": "123"},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedDbContext)
        assert result.query == "SELECT * FROM users WHERE id = $1"
        # Params should be coerced to int
        assert result.params == [123]

    def test_resolve_kafka_context(self, test_node: TestNode) -> None:
        """Test resolving Kafka context with template placeholders."""
        io_config = ModelKafkaIOConfig(
            topic="${input.topic_name}",
            payload_template='{"user_id": "${input.user_id}"}',
            partition_key_template="${input.user_id}",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.EVENT_EMISSION,
            operation_data={"topic_name": "events", "user_id": "789"},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedKafkaContext)
        assert result.topic == "events"
        assert result.payload == '{"user_id": "789"}'
        assert result.partition_key == "789"

    def test_resolve_filesystem_context_write_with_content(
        self, test_node: TestNode
    ) -> None:
        """Test resolving filesystem context for write with content."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/${input.filename}.json",
            operation="write",
            atomic=True,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"filename": "output", "file_content": '{"data": "test"}'},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.file_path == "/data/output.json"
        assert result.content == '{"data": "test"}'
        assert result.operation == "write"

    def test_resolve_filesystem_context_read_no_content(
        self, test_node: TestNode
    ) -> None:
        """Test resolving filesystem context for read (no content needed)."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/${input.filename}.json",
            operation="read",
            atomic=False,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"filename": "input"},
        )
        result = test_node._resolve_io_context(io_config, input_data)
        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.file_path == "/data/input.json"
        assert result.content is None

    def test_resolve_unknown_template_prefix_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that unknown template prefix raises ModelOnexError."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/${unknown.value}",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )
        with pytest.raises(ModelOnexError) as exc_info:
            test_node._resolve_io_context(io_config, input_data)
        assert "Unknown template prefix" in str(exc_info.value)


@pytest.mark.unit
class TestExtractField:
    """Test _extract_field dotpath extraction."""

    def test_extract_simple_field(self, test_node: TestNode) -> None:
        """Test extracting simple field."""
        data = {"user_id": "123", "name": "Test"}
        assert test_node._extract_field(data, "user_id") == "123"
        assert test_node._extract_field(data, "name") == "Test"

    def test_extract_nested_field(self, test_node: TestNode) -> None:
        """Test extracting nested field."""
        data = {"user": {"profile": {"name": "John", "age": 30}}}
        assert test_node._extract_field(data, "user.profile.name") == "John"
        assert test_node._extract_field(data, "user.profile.age") == 30

    def test_extract_missing_field_returns_none(self, test_node: TestNode) -> None:
        """Test that missing field returns None."""
        data = {"user_id": "123"}
        assert test_node._extract_field(data, "nonexistent") is None
        assert test_node._extract_field(data, "user.profile") is None

    def test_extract_from_non_dict_returns_none(self, test_node: TestNode) -> None:
        """Test that extracting from non-dict returns None."""
        data = {"value": "string"}
        assert test_node._extract_field(data, "value.nested") is None

    def test_extract_field_with_underscore_names(self, test_node: TestNode) -> None:
        """Test extracting fields with underscore names (snake_case)."""
        data = {"user_info": {"first_name": "John", "last_name": "Doe"}}
        assert test_node._extract_field(data, "user_info.first_name") == "John"
        assert test_node._extract_field(data, "user_info.last_name") == "Doe"

    def test_extract_field_with_numeric_names(self, test_node: TestNode) -> None:
        """Test extracting fields with numeric names."""
        data = {"item0": {"sub1": "value"}}
        assert test_node._extract_field(data, "item0.sub1") == "value"

    def test_extract_field_rejects_unsafe_characters(self, test_node: TestNode) -> None:
        """Test that _extract_field rejects paths with unsafe characters.

        Security hardening: Prevents injection attacks via malicious field paths
        like __import__, eval(), etc.
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        unsafe_paths = [
            "eval()",  # Parentheses not allowed
            "foo;bar",  # Semicolon not allowed
            "path/../etc",  # Path traversal via ../
            "a[0]",  # Brackets not allowed
            "${var}",  # Template syntax not allowed
            "foo bar",  # Spaces not allowed
            "foo\nbar",  # Newlines not allowed
            "foo\tbar",  # Tabs not allowed
            "foo|bar",  # Pipe not allowed
            "foo&bar",  # Ampersand not allowed
            "foo>bar",  # Greater than not allowed
            "foo<bar",  # Less than not allowed
            'foo"bar',  # Quotes not allowed
            "foo'bar",  # Single quotes not allowed
            "foo`bar",  # Backticks not allowed
            "foo!bar",  # Exclamation not allowed
            "foo@bar",  # At symbol not allowed
            "foo#bar",  # Hash not allowed
            "foo%bar",  # Percent not allowed
            "foo^bar",  # Caret not allowed
            "foo*bar",  # Asterisk not allowed
            "foo+bar",  # Plus not allowed
            "foo=bar",  # Equals not allowed
            "foo~bar",  # Tilde not allowed
            "foo\\bar",  # Backslash not allowed
            "foo/bar",  # Forward slash not allowed
            "foo:bar",  # Colon not allowed
            "foo?bar",  # Question mark not allowed
            "foo,bar",  # Comma not allowed
        ]
        data = {"foo": {"bar": "value"}}

        for unsafe_path in unsafe_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, unsafe_path)
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Invalid field path characters" in str(exc_info.value)
            # Context is stored in model.context["context"] for additional keys
            # (source code uses context={...} kwarg which nests under "context" key)
            inner_context = exc_info.value.model.context.get(
                "context", exc_info.value.model.context
            )
            assert "allowed_pattern" in inner_context

    def test_extract_field_accepts_safe_paths(self, test_node: TestNode) -> None:
        """Test that _extract_field accepts valid safe paths."""
        data = {
            "user_id": "123",
            "UserName": "John",
            "item0": {"sub_field": "value"},
            "a": {"b": {"c": "deep"}},
            # Note: "__init__" is now on the deny-list (see TestDeniedBuiltins)
            "my_field": "test",
            "_private": "allowed",  # Single underscore prefixes are allowed
            "__custom__": "value",  # Custom dunder not in deny-list - allowed by pattern
        }

        # These should all work without raising
        assert test_node._extract_field(data, "user_id") == "123"
        assert test_node._extract_field(data, "UserName") == "John"
        assert test_node._extract_field(data, "item0.sub_field") == "value"
        assert test_node._extract_field(data, "a.b.c") == "deep"
        assert test_node._extract_field(data, "my_field") == "test"
        assert test_node._extract_field(data, "_private") == "allowed"
        assert test_node._extract_field(data, "__custom__") == "value"

    def test_extract_field_rejects_empty_path(self, test_node: TestNode) -> None:
        """Test that _extract_field rejects empty paths."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        data = {"foo": "bar"}

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_field(data, "")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_extract_field_error_includes_operation_id(
        self, test_node: TestNode
    ) -> None:
        """Test that error context includes operation_id when provided."""
        from uuid import uuid4

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        data = {"foo": "bar"}
        op_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_field(data, "eval()", operation_id=op_id)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # Context is stored in model.context for additional (non-standard) keys
        assert exc_info.value.model.context["operation_id"] == str(op_id)
        assert exc_info.value.model.context["field_path"] == "eval()"
        assert exc_info.value.model.context["allowed_pattern"] == "[a-zA-Z0-9_.]"


@pytest.mark.unit
class TestDeniedBuiltins:
    """Test denied Python built-ins validation for template injection protection.

    These tests verify the defense-in-depth security mechanism that blocks
    access to Python built-ins and special attributes via field paths, even
    when those paths pass the character pattern validation (SAFE_FIELD_PATTERN).

    The DENIED_BUILTINS set blocks dangerous identifiers like:
    - Code execution: import, __import__, eval, exec, compile
    - Introspection: globals, locals, vars, dir
    - Attribute manipulation: getattr, setattr, delattr, hasattr
    - Special attributes: __class__, __bases__, __builtins__, etc.
    """

    def test_denied_code_execution_builtins(self, test_node: TestNode) -> None:
        """Test that code execution built-ins are denied."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Code execution functions that could enable arbitrary code execution
        denied_paths = [
            "import",
            "__import__",
            "eval",
            "exec",
            "compile",
        ]
        data = {"foo": "bar"}

        for path in denied_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
            assert "denied" in exc_info.value.message.lower()
            assert path in exc_info.value.model.context.get("denied_builtin", "")

    def test_denied_introspection_builtins(self, test_node: TestNode) -> None:
        """Test that introspection built-ins are denied."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Introspection functions that could leak sensitive information
        denied_paths = [
            "globals",
            "locals",
            "vars",
            "dir",
        ]
        data = {"foo": "bar"}

        for path in denied_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
            assert "denied" in exc_info.value.message.lower()

    def test_denied_attribute_manipulation_builtins(self, test_node: TestNode) -> None:
        """Test that attribute manipulation built-ins are denied."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Attribute manipulation functions that could modify objects
        denied_paths = [
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
        ]
        data = {"foo": "bar"}

        for path in denied_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
            assert "denied" in exc_info.value.message.lower()

    def test_denied_special_attributes(self, test_node: TestNode) -> None:
        """Test that Python special attributes (dunder) are denied."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Special attributes used in prototype pollution / class manipulation attacks
        denied_paths = [
            "__builtins__",
            "__class__",
            "__bases__",
            "__mro__",
            "__subclasses__",
            "__dict__",
            "__globals__",
            "__code__",
            "__init__",
            "__call__",
            "__getattr__",
            "__setattr__",
        ]
        data = {"foo": "bar"}

        for path in denied_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
            assert "denied" in exc_info.value.message.lower()

    def test_denied_builtins_in_nested_path(self, test_node: TestNode) -> None:
        """Test that denied built-ins are caught in nested paths."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Attacks often try to access special attributes through nested paths
        nested_attack_paths = [
            "user.__class__",
            "data.__class__.name",
            "config.eval",
            "obj.__bases__",
            "item.__subclasses__",
            "user.profile.__dict__",
            "request.__globals__",
            "module.__import__",
            "nested.path.to.__builtins__",
        ]
        data = {"user": {"profile": {"name": "test"}}}

        for path in nested_attack_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION

    def test_denied_other_dangerous_builtins(self, test_node: TestNode) -> None:
        """Test that other potentially dangerous built-ins are denied."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Additional dangerous builtins for defense in depth
        denied_paths = [
            "open",
            "input",
            "breakpoint",
            "exit",
            "quit",
        ]
        data = {"foo": "bar"}

        for path in denied_paths:
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_field(data, path)
            assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION

    def test_legitimate_field_names_still_work(self, test_node: TestNode) -> None:
        """Test that legitimate field names with underscores still work."""
        data = {
            "user_id": "123",
            "first_name": "John",
            "_private_field": "private",
            "__custom_dunder__": "custom",  # Not in deny-list
            "evaluator": "allowed",  # Contains 'eval' but not exact match
            "compiler_version": "1.0",  # Contains 'compile' but not exact match
            "global_config": "config",  # Contains 'global' but not exact match
            "nested": {
                "importer_id": "imp123",  # Contains 'import' but not exact match
                "classname": "MyClass",  # Contains 'class' but not exact match
            },
        }

        # These should all work - they contain denied words as substrings but
        # are not exact matches to denied built-in names
        assert test_node._extract_field(data, "user_id") == "123"
        assert test_node._extract_field(data, "first_name") == "John"
        assert test_node._extract_field(data, "_private_field") == "private"
        assert test_node._extract_field(data, "__custom_dunder__") == "custom"
        assert test_node._extract_field(data, "evaluator") == "allowed"
        assert test_node._extract_field(data, "compiler_version") == "1.0"
        assert test_node._extract_field(data, "global_config") == "config"
        assert test_node._extract_field(data, "nested.importer_id") == "imp123"
        assert test_node._extract_field(data, "nested.classname") == "MyClass"

    def test_denied_builtin_error_includes_context(self, test_node: TestNode) -> None:
        """Test that denied builtin error includes helpful context."""
        from uuid import uuid4

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        data = {"foo": "bar"}
        op_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_field(data, "user.__class__", operation_id=op_id)

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        context = exc_info.value.model.context
        assert context["operation_id"] == str(op_id)
        assert context["field_path"] == "user.__class__"
        assert context["denied_builtin"] == "__class__"

    def test_case_sensitivity_of_denied_builtins(self, test_node: TestNode) -> None:
        """Test that denied built-in check is case-sensitive (Python is case-sensitive)."""
        data = {
            "Eval": "uppercase_allowed",  # Not the same as 'eval'
            "IMPORT": "uppercase_allowed",  # Not the same as 'import'
            "Globals": "uppercase_allowed",  # Not the same as 'globals'
        }

        # These should work because Python identifiers are case-sensitive
        # and our deny-list uses exact lowercase matches
        assert test_node._extract_field(data, "Eval") == "uppercase_allowed"
        assert test_node._extract_field(data, "IMPORT") == "uppercase_allowed"
        assert test_node._extract_field(data, "Globals") == "uppercase_allowed"

    def test_pattern_validation_runs_before_denylist(self, test_node: TestNode) -> None:
        """Test that character pattern validation runs before deny-list check.

        This ensures we fail fast on invalid characters before checking the deny-list.
        Both checks are important for defense-in-depth, but the pattern check
        catches more obvious attacks immediately.
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        data = {"foo": "bar"}

        # eval() has parentheses - pattern should reject first
        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_field(data, "eval()")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # Should mention pattern, not deny-list
        assert "Invalid field path characters" in exc_info.value.message

    def test_extract_field_returns_dict_values(self, test_node: TestNode) -> None:
        """Test that dict values are returned as-is (type validation allows dicts)."""
        nested_dict = {"key": "value", "nested": {"inner": 123}}
        data = {"config": nested_dict}

        result = test_node._extract_field(data, "config")
        assert result == nested_dict
        assert isinstance(result, dict)

    def test_extract_field_returns_list_values(self, test_node: TestNode) -> None:
        """Test that list values are returned as-is (type validation allows lists)."""
        items = [1, 2, {"key": "value"}]
        data = {"items": items}

        result = test_node._extract_field(data, "items")
        assert result == items
        assert isinstance(result, list)

    def test_extract_field_returns_none_for_callable(self, test_node: TestNode) -> None:
        """Test that callable values return None (type safety validation).

        Security hardening: Prevents accidentally exposing callable objects
        which could be exploited for code execution.
        """

        def my_function() -> str:
            return "dangerous"

        data = {"callback": my_function}

        # Callable should be filtered out by type validation
        result = test_node._extract_field(data, "callback")
        assert result is None

    def test_extract_field_returns_none_for_custom_object(
        self, test_node: TestNode
    ) -> None:
        """Test that custom objects return None (type safety validation).

        Security hardening: Prevents leaking arbitrary object references
        which could expose internal state or methods.
        """

        class CustomClass:
            def __init__(self) -> None:
                self.secret = "internal_data"

        data = {"obj": CustomClass()}

        # Custom object should be filtered out by type validation
        result = test_node._extract_field(data, "obj")
        assert result is None

    def test_extract_field_returns_primitives_correctly(
        self, test_node: TestNode
    ) -> None:
        """Test that all primitive types are returned correctly."""
        data = {
            "string_val": "hello",
            "int_val": 42,
            "float_val": 3.14,
            "bool_true": True,
            "bool_false": False,
        }

        assert test_node._extract_field(data, "string_val") == "hello"
        assert test_node._extract_field(data, "int_val") == 42
        assert test_node._extract_field(data, "float_val") == 3.14
        assert test_node._extract_field(data, "bool_true") is True
        assert test_node._extract_field(data, "bool_false") is False


@pytest.mark.unit
class TestCoerceParamValue:
    """Test _coerce_param_value type coercion."""

    def test_coerce_bool_true(self, test_node: TestNode) -> None:
        """Test coercing true/True to bool."""
        assert test_node._coerce_param_value("true") is True
        assert test_node._coerce_param_value("True") is True
        assert test_node._coerce_param_value("TRUE") is True

    def test_coerce_bool_false(self, test_node: TestNode) -> None:
        """Test coercing false/False to bool."""
        assert test_node._coerce_param_value("false") is False
        assert test_node._coerce_param_value("False") is False
        assert test_node._coerce_param_value("FALSE") is False

    def test_coerce_none(self, test_node: TestNode) -> None:
        """Test coercing none/null to None."""
        assert test_node._coerce_param_value("none") is None
        assert test_node._coerce_param_value("None") is None
        assert test_node._coerce_param_value("null") is None

    def test_coerce_int(self, test_node: TestNode) -> None:
        """Test coercing integer strings."""
        assert test_node._coerce_param_value("123") == 123
        assert test_node._coerce_param_value("-456") == -456
        assert test_node._coerce_param_value("0") == 0

    def test_coerce_float(self, test_node: TestNode) -> None:
        """Test coercing float strings."""
        assert test_node._coerce_param_value("3.14") == 3.14
        assert test_node._coerce_param_value("-2.5") == -2.5
        assert test_node._coerce_param_value("0.0") == 0.0

    def test_coerce_string_passthrough(self, test_node: TestNode) -> None:
        """Test that non-coercible strings pass through."""
        assert test_node._coerce_param_value("hello") == "hello"
        assert test_node._coerce_param_value("test@example.com") == "test@example.com"


@pytest.mark.unit
class TestCircuitBreaker:
    """Test circuit breaker management methods."""

    def test_check_circuit_breaker_initializes_new(self, test_node: TestNode) -> None:
        """Test that checking non-existent circuit breaker initializes it."""
        operation_id = uuid4()
        assert operation_id not in test_node._circuit_breakers

        result = test_node._check_circuit_breaker(operation_id)

        assert result is True  # New circuit breaker should allow requests
        assert operation_id in test_node._circuit_breakers
        assert isinstance(
            test_node._circuit_breakers[operation_id], ModelCircuitBreaker
        )

    def test_check_circuit_breaker_closed_allows_requests(
        self, test_node: TestNode
    ) -> None:
        """Test that closed circuit breaker allows requests."""
        operation_id = uuid4()
        cb = ModelCircuitBreaker.create_resilient()
        cb.state = EnumCircuitBreakerState.CLOSED
        test_node._circuit_breakers[operation_id] = cb

        result = test_node._check_circuit_breaker(operation_id)

        assert result is True

    def test_check_circuit_breaker_open_denies_requests(
        self, test_node: TestNode
    ) -> None:
        """Test that open circuit breaker denies requests.

        Note: Circuit breaker has timeout-based transition from open to half-open.
        We set last_state_change to now to ensure we're testing the "still open" case.
        """
        from datetime import UTC, datetime

        operation_id = uuid4()
        cb = ModelCircuitBreaker.create_resilient()
        cb.state = EnumCircuitBreakerState.OPEN
        cb.failure_count = cb.failure_threshold + 1
        cb.total_requests = cb.minimum_request_threshold + 1
        # Set last_state_change to now so it doesn't transition to half-open
        cb.last_state_change = datetime.now(UTC)
        test_node._circuit_breakers[operation_id] = cb

        result = test_node._check_circuit_breaker(operation_id)

        assert result is False

    def test_record_circuit_breaker_success(self, test_node: TestNode) -> None:
        """Test recording success in circuit breaker."""
        operation_id = uuid4()
        cb = ModelCircuitBreaker.create_resilient()
        initial_total = cb.total_requests
        test_node._circuit_breakers[operation_id] = cb

        test_node._record_circuit_breaker_result(operation_id, success=True)

        assert cb.total_requests == initial_total + 1

    def test_record_circuit_breaker_failure(self, test_node: TestNode) -> None:
        """Test recording failure in circuit breaker."""
        operation_id = uuid4()
        cb = ModelCircuitBreaker.create_resilient()
        initial_failures = cb.failure_count
        test_node._circuit_breakers[operation_id] = cb

        test_node._record_circuit_breaker_result(operation_id, success=False)

        assert cb.failure_count == initial_failures + 1

    def test_record_creates_circuit_breaker_if_missing(
        self, test_node: TestNode
    ) -> None:
        """Test that recording creates circuit breaker if not present."""
        operation_id = uuid4()
        assert operation_id not in test_node._circuit_breakers

        test_node._record_circuit_breaker_result(operation_id, success=True)

        assert operation_id in test_node._circuit_breakers


@pytest.mark.unit
class TestExecuteEffect:
    """Test execute_effect main entry point."""

    @pytest.mark.asyncio
    async def test_execute_effect_no_operations_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that missing operations raises ModelOnexError."""
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},  # No operations
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        assert "No operations defined" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_effect_empty_operations_list_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that empty operations list raises ModelOnexError."""
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"operations": []},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        assert "No operations defined" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_effect_successful_http(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test successful HTTP effect execution."""
        # Register mock HTTP handler
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"status": "success", "data": "test"}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        "operation_timeout_ms": 5000,
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=False,
        )

        result = await test_node.execute_effect(input_data)

        assert isinstance(result, ModelEffectOutput)
        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.result == {"status": "success", "data": "test"}
        assert result.retry_count == 0
        mock_handler.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_effect_handler_not_registered_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that missing handler registration raises ModelOnexError."""
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        "operation_timeout_ms": 5000,
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        assert "Effect handler not registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_effect_handler_failure_rolls_back(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that handler failure causes rollback state."""
        # Register mock handler that raises exception
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = RuntimeError("Handler error")
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        "operation_timeout_ms": 5000,
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=False,
        )

        with pytest.raises(ModelOnexError):
            await test_node.execute_effect(input_data)


@pytest.mark.unit
class TestExecuteWithRetry:
    """Test _execute_with_retry retry logic."""

    @pytest.mark.asyncio
    async def test_retry_count_zero_on_first_success(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that retry_count is 0 when operation succeeds on first try."""
        # Register mock handler
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"success": True}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=True,
            max_retries=3,
        )

        result = await test_node.execute_effect(input_data)

        assert result.retry_count == 0
        assert mock_handler.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_count_increments_on_failures(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that retry_count correctly counts failed attempts."""
        # Register mock handler that fails twice then succeeds
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = [
            RuntimeError("First failure"),
            RuntimeError("Second failure"),
            {"success": True},
        ]
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=1,  # Fast retries for testing
        )

        result = await test_node.execute_effect(input_data)

        # retry_count should be 2 (two failures before success)
        assert result.retry_count == 2
        assert mock_handler.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_respects_max_retries(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that retries stop at max_retries."""
        # Register mock handler that always fails
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = RuntimeError("Always fails")
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=True,
            max_retries=2,
            retry_delay_ms=1,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        # Should have attempted 1 initial + 2 retries = 3 total
        assert mock_handler.execute.call_count == 3
        # The error is wrapped in "Handler execution failed" for handler-raised exceptions
        assert "Always fails" in str(
            exc_info.value
        ) or "Handler execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_disabled_no_retries(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that retry_enabled=False disables retries."""
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = RuntimeError("Failure")
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=False,
            max_retries=5,  # Should be ignored
        )

        with pytest.raises(ModelOnexError):
            await test_node.execute_effect(input_data)

        # Only one attempt
        assert mock_handler.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_open_fails_fast(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that open circuit breaker causes fast failure."""
        # Set up circuit breaker in open state
        operation_id = uuid4()

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_id=operation_id,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=True,
            max_retries=3,
            circuit_breaker_enabled=True,
        )

        # Initialize circuit breaker in open state
        cb = ModelCircuitBreaker.create_resilient()
        cb.state = EnumCircuitBreakerState.OPEN
        test_node._circuit_breakers[operation_id] = cb

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        assert "Circuit breaker is open" in str(exc_info.value)


@pytest.mark.unit
class TestExtractResponseFields:
    """Test _extract_response_fields method."""

    def test_extract_with_dotpath_engine(self, test_node: TestNode) -> None:
        """Test field extraction with dotpath engine."""
        response = {"data": {"user": {"id": 123, "name": "John"}}}
        response_handling = {
            "extraction_engine": "dotpath",
            "extract_fields": {
                "user_id": "$.data.user.id",
                "user_name": "$.data.user.name",
            },
        }

        result = test_node._extract_response_fields(response, response_handling)

        assert result["user_id"] == 123
        assert result["user_name"] == "John"

    def test_extract_missing_field_returns_none(self, test_node: TestNode) -> None:
        """Test that missing field returns None."""
        response = {"data": {"user": {"id": 123}}}
        response_handling = {
            "extraction_engine": "dotpath",
            "extract_fields": {"user_email": "$.data.user.email"},
        }

        result = test_node._extract_response_fields(response, response_handling)

        assert result["user_email"] is None

    def test_extract_fail_on_empty_raises_error(self, test_node: TestNode) -> None:
        """Test that fail_on_empty=True raises error for missing values."""
        response = {"data": {"user": {"id": 123}}}
        response_handling = {
            "extraction_engine": "dotpath",
            "extract_fields": {"user_email": "$.data.user.email"},
            "fail_on_empty": True,
        }

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_response_fields(response, response_handling)

        assert "No value found" in str(exc_info.value)

    def test_extract_empty_fields_returns_empty_dict(self, test_node: TestNode) -> None:
        """Test that empty extract_fields returns empty dict."""
        response = {"data": "value"}
        response_handling: dict[str, Any] = {"extraction_engine": "dotpath"}

        result = test_node._extract_response_fields(response, response_handling)

        assert result == {}

    def test_extract_unknown_engine_raises_error(self, test_node: TestNode) -> None:
        """Test that unknown extraction engine raises error."""
        response = {"data": "value"}
        response_handling = {
            "extraction_engine": "unknown_engine",
            "extract_fields": {"key": "$.data"},
        }

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_response_fields(response, response_handling)

        assert "Unknown extraction engine" in str(exc_info.value)

    def test_extract_non_primitive_raises_error(self, test_node: TestNode) -> None:
        """Test that extracting non-primitive value raises error."""
        response = {"data": {"nested": {"complex": "value"}}}
        response_handling = {
            "extraction_engine": "dotpath",
            "extract_fields": {"nested_obj": "$.data.nested"},
        }

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._extract_response_fields(response, response_handling)

        assert "must be primitive" in str(exc_info.value)

    def test_extract_with_jsonpath_engine(self, test_node: TestNode) -> None:
        """Test jsonpath engine behavior based on jsonpath-ng availability.

        This test handles both scenarios:
        - If jsonpath-ng is installed: extraction should succeed
        - If jsonpath-ng is NOT installed: should raise dependency error

        The test dynamically detects whether the library is available and
        validates the appropriate behavior.
        """
        # Check if jsonpath-ng is available
        jsonpath_available = importlib.util.find_spec("jsonpath_ng") is not None

        response = {"data": {"user": {"id": 123}}}
        response_handling = {
            "extraction_engine": "jsonpath",  # Uses jsonpath which requires jsonpath-ng
            "extract_fields": {"user_id": "$.data.user.id"},
        }

        if jsonpath_available:
            # jsonpath-ng IS installed - extraction should succeed
            result = test_node._extract_response_fields(response, response_handling)
            assert result["user_id"] == 123
        else:
            # jsonpath-ng is NOT installed - should raise dependency error
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_response_fields(response, response_handling)

            # Either dependency not available or some parsing error
            error_str = str(exc_info.value)
            assert (
                "jsonpath-ng" in error_str
                or "DEPENDENCY_UNAVAILABLE" in error_str
                or "Field extraction failed" in error_str
            )

    def test_extract_default_engine_is_jsonpath(self, test_node: TestNode) -> None:
        """Test that default extraction engine is jsonpath.

        This test handles both scenarios:
        - If jsonpath-ng is installed: extraction should succeed with default engine
        - If jsonpath-ng is NOT installed: should raise dependency error

        The test dynamically detects whether the library is available and
        validates the appropriate behavior.
        """
        # Check if jsonpath-ng is available
        jsonpath_available = importlib.util.find_spec("jsonpath_ng") is not None

        response = {"data": "value"}
        # No extraction_engine specified - should default to jsonpath
        response_handling: dict[str, Any] = {
            "extract_fields": {"key": "$.data"},
        }

        if jsonpath_available:
            # jsonpath-ng IS installed - default engine should work
            result = test_node._extract_response_fields(response, response_handling)
            assert result["key"] == "value"
        else:
            # jsonpath-ng is NOT installed - should fail with dependency error
            with pytest.raises(ModelOnexError) as exc_info:
                test_node._extract_response_fields(response, response_handling)

            error_str = str(exc_info.value)
            assert (
                "jsonpath-ng" in error_str
                or "DEPENDENCY_UNAVAILABLE" in error_str
                or "Field extraction failed" in error_str
            )


@pytest.mark.unit
class TestExecuteOperation:
    """Test _execute_operation handler dispatch."""

    @pytest.mark.asyncio
    async def test_execute_operation_http_handler(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test dispatching to HTTP handler."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"response": "data"}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        context = ModelResolvedHttpContext(
            url="https://api.example.com/test",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        result = await test_node._execute_operation(context, input_data)

        assert result == {"response": "data"}
        mock_handler.execute.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_operation_db_handler(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test dispatching to DB handler."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = [{"id": 1}, {"id": 2}]
        mock_container.register_service("ProtocolEffectHandler_DB", mock_handler)

        context = ModelResolvedDbContext(
            operation="select",
            connection_name="primary",
            query="SELECT * FROM users",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data={},
        )

        result = await test_node._execute_operation(context, input_data)

        assert result == [{"id": 1}, {"id": 2}]

    @pytest.mark.asyncio
    async def test_execute_operation_handler_exception_wraps_error(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that handler exceptions are wrapped in ModelOnexError."""
        mock_handler = AsyncMock()
        mock_handler.execute.side_effect = ValueError("Handler internal error")
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        context = ModelResolvedHttpContext(
            url="https://api.example.com/test",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node._execute_operation(context, input_data)

        assert "Handler execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_operation_converts_non_standard_result_to_string(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that non-standard result types are converted to string."""

        class CustomResult:
            def __str__(self) -> str:
                return "custom_result_string"

        mock_handler = AsyncMock()
        mock_handler.execute.return_value = CustomResult()
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        context = ModelResolvedHttpContext(
            url="https://api.example.com/test",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        result = await test_node._execute_operation(context, input_data)

        assert result == "custom_result_string"


@pytest.mark.unit
class TestDefaultOperationTimeout:
    """Test default operation timeout behavior."""

    @pytest.mark.asyncio
    async def test_default_timeout_when_not_specified(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that default timeout is used when not specified."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"success": True}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        # No operation_timeout_ms specified
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=False,
        )

        # Should not raise - default timeout is used
        result = await test_node.execute_effect(input_data)
        assert result.transaction_state == EnumTransactionState.COMMITTED

    @pytest.mark.asyncio
    async def test_explicit_null_timeout_uses_default(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that explicit null timeout falls back to default."""
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"success": True}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        "operation_timeout_ms": None,  # Explicit null
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=False,
        )

        result = await test_node.execute_effect(input_data)
        assert result.transaction_state == EnumTransactionState.COMMITTED


@pytest.mark.unit
class TestSecretResolution:
    """Test secret.* template resolution."""

    def test_resolve_secret_template(self, test_node: TestNode) -> None:
        """Test resolving secret.* templates via secret service."""
        # Register mock secret service
        mock_secret_service = MagicMock()
        mock_secret_service.get_secret.return_value = "super_secret_value"
        test_node.container.register_service(
            "ProtocolSecretService", mock_secret_service
        )

        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"X-API-Key": "${secret.API_KEY}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedHttpContext)
        assert result.headers["X-API-Key"] == "super_secret_value"
        mock_secret_service.get_secret.assert_called_once_with("API_KEY")

    def test_resolve_secret_not_found_raises_error(self, test_node: TestNode) -> None:
        """Test that missing secret raises error."""
        # Register mock secret service that returns None
        mock_secret_service = MagicMock()
        mock_secret_service.get_secret.return_value = None
        test_node.container.register_service(
            "ProtocolSecretService", mock_secret_service
        )

        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"X-API-Key": "${secret.NONEXISTENT}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._resolve_io_context(io_config, input_data)

        # The error wraps "Secret not found" in "Failed to resolve secret"
        assert "Failed to resolve secret" in str(
            exc_info.value
        ) or "Secret not found" in str(exc_info.value)

    def test_resolve_secret_service_error_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that secret service error is wrapped."""
        # Register mock secret service that raises exception
        mock_secret_service = MagicMock()
        mock_secret_service.get_secret.side_effect = RuntimeError("Service error")
        test_node.container.register_service(
            "ProtocolSecretService", mock_secret_service
        )

        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"X-API-Key": "${secret.API_KEY}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._resolve_io_context(io_config, input_data)

        assert "Failed to resolve secret" in str(exc_info.value)

    def test_resolve_secret_service_missing_method_raises_error(
        self, test_node: TestNode
    ) -> None:
        """Test that secret service without get_secret method raises error.

        This tests the hasattr check that validates the secret service
        implements the required get_secret method.
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Register mock secret service WITHOUT get_secret method
        mock_secret_service = MagicMock(spec=[])  # Empty spec = no methods
        test_node.container.register_service(
            "ProtocolSecretService", mock_secret_service
        )

        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/test",
            method="GET",
            headers={"X-API-Key": "${secret.API_KEY}"},
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            test_node._resolve_io_context(io_config, input_data)

        # Check error wrapping - either inner or outer message
        error_str = str(exc_info.value)
        assert (
            "does not implement get_secret method" in error_str
            or "Failed to resolve secret" in error_str
        )
        # Verify error code if accessible
        if hasattr(exc_info.value, "error_code"):
            # Could be UNSUPPORTED_OPERATION or wrapped error
            assert exc_info.value.error_code in (
                EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                EnumCoreErrorCode.CONFIGURATION_ERROR,
            )


@pytest.mark.unit
class TestFilesystemContentResolution:
    """Test filesystem content extraction and resolution."""

    def test_write_with_file_content_key(self, test_node: TestNode) -> None:
        """Test that write operation uses file_content key."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/output.json",
            operation="write",
            atomic=True,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"file_content": '{"key": "value"}'},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.content == '{"key": "value"}'

    def test_write_with_content_key_fallback(self, test_node: TestNode) -> None:
        """Test that write operation falls back to content key."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/output.json",
            operation="write",
            atomic=True,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"content": '{"fallback": "content"}'},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.content == '{"fallback": "content"}'

    def test_write_with_template_in_content(self, test_node: TestNode) -> None:
        """Test that templates in content are resolved for write."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/output.json",
            operation="write",
            atomic=True,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={
                "file_content": '{"user_id": "${input.user_id}"}',
                "user_id": "123",
            },
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.content == '{"user_id": "123"}'

    def test_read_operation_no_content(self, test_node: TestNode) -> None:
        """Test that read operation has no content."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/input.json",
            operation="read",
            atomic=False,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"file_content": "should_be_ignored"},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.content is None

    def test_delete_operation_no_content(self, test_node: TestNode) -> None:
        """Test that delete operation has no content."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/to_delete.json",
            operation="delete",
            atomic=False,
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedFilesystemContext)
        assert result.content is None


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.unit
class TestMixinEffectExecutionIntegration:
    """Integration-style tests for MixinEffectExecution.

    These tests verify the full execution path including handler dispatch,
    retry logic, and circuit breaker behavior working together.

    Markers:
        @pytest.mark.integration: Indicates this tests multi-component interactions
            (handler dispatch + retry logic + circuit breaker) even though external
            services are mocked. This marker makes the integration testing intent clear.
        @pytest.mark.slow: Indicates these tests may take longer due to retry delays
            and multi-step execution flows.

    Note:
        These tests use mocked dependencies (no real external services) but exercise
        integration patterns between components. The module-level pytestmark =
        pytest.mark.unit still applies for test discovery purposes.
    """

    @pytest.mark.asyncio
    async def test_full_http_flow_with_retry_and_success(
        self, mock_container: MockContainer
    ) -> None:
        """Test complete HTTP flow: failure, retry, success."""
        node = TestNode(container=mock_container)

        # Handler fails twice, then succeeds
        mock_handler = AsyncMock()
        call_count = 0

        async def mock_execute(context: ModelResolvedHttpContext) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Attempt {call_count} failed")
            return {"status": "success", "attempt": call_count}

        mock_handler.execute = mock_execute
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=1,
            circuit_breaker_enabled=False,
        )

        result = await node.execute_effect(input_data)

        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.retry_count == 2  # Two failures before success
        assert result.result["status"] == "success"
        assert result.result["attempt"] == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success_and_failure(
        self, mock_container: MockContainer
    ) -> None:
        """Test that circuit breaker properly tracks success/failure."""
        node = TestNode(container=mock_container)

        # Handler succeeds
        mock_handler = AsyncMock()
        mock_handler.execute.return_value = {"status": "ok"}
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        operation_id = uuid4()
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_id=operation_id,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=False,
            circuit_breaker_enabled=True,
        )

        result = await node.execute_effect(input_data)

        assert result.transaction_state == EnumTransactionState.COMMITTED
        # Circuit breaker should have been created and recorded success
        assert operation_id in node._circuit_breakers
        cb = node._circuit_breakers[operation_id]
        assert cb.total_requests >= 1


@pytest.mark.slow
@pytest.mark.unit
class TestTimeoutBehavior:
    """Test timeout behavior in effect execution.

    Markers:
        @pytest.mark.slow: Timeout tests involve asyncio.sleep() delays to simulate
            timing behavior, which may cause these tests to run longer than typical
            unit tests.

    Timeout Behavior Note:
        The operation_timeout_ms is checked at the START of each retry attempt,
        not during handler execution. This means:
        - First attempt: timeout check at t=0ms usually passes
        - Handler executes (may take longer than timeout)
        - If handler fails and retry is enabled, timeout checked before next attempt
        - Timeout triggers if elapsed >= operation_timeout_ms at retry loop start

        This design is intentional - it guards against cumulative retry time
        exceeding limits, not individual operation duration. Handler-level
        timeouts should be set via io_config.timeout_ms for per-operation limits.

    Determinism:
        Tests use fixed delays (e.g., 50ms) greater than fixed timeouts (e.g., 30ms)
        to ensure deterministic behavior. The margin is sufficient to avoid CI flakiness
        from scheduling jitter.
    """

    @pytest.mark.asyncio
    async def test_operation_timeout_exceeded_on_retry(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that operation timeout triggers on retry attempt.

        This test exercises the timeout path in _execute_with_retry() at line 1006:
            if elapsed_ms >= operation_timeout_ms:
                raise ModelOnexError(..., error_code=EnumCoreErrorCode.TIMEOUT_EXCEEDED)

        The timeout check occurs at the START of each retry attempt. To properly
        exercise this path, we need:
        1. First attempt to fail (to trigger a retry)
        2. Enough time to elapse that the second attempt hits timeout

        Test Flow:
            t=0ms:   First attempt starts, timeout check passes (0 < 30)
            t=50ms:  Handler fails after 50ms delay
            t=50ms:  Retry triggered, but timeout check at loop start finds
                     elapsed_ms (50) >= operation_timeout_ms (30)
            t=50ms:  TIMEOUT_EXCEEDED raised before second attempt begins

        This test uses a handler that fails with a delay, ensuring the timeout
        check on the retry attempt finds elapsed_ms >= operation_timeout_ms.
        """
        import asyncio

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        # Handler that fails after a delay (simulating slow network failure)
        async def slow_failing_handler(context: Any) -> dict[str, Any]:
            await asyncio.sleep(0.05)  # 50ms
            raise ValueError("Simulated failure after delay")

        mock_handler = AsyncMock()
        mock_handler.execute = slow_failing_handler
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                        # 30ms timeout - first attempt takes 50ms, so retry check fails
                        "operation_timeout_ms": 30,
                    }
                ]
            },
            retry_enabled=True,
            max_retries=3,  # Enable retries so timeout is checked on retry
            retry_delay_ms=1,  # Minimal delay
            circuit_breaker_enabled=False,
        )

        # Should raise timeout error when attempting retry after first failure
        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        # Verify it's actually a timeout error, not the handler's ValueError
        assert exc_info.value.error_code == EnumCoreErrorCode.TIMEOUT_EXCEEDED
        assert "timeout" in exc_info.value.message.lower()


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_input_template_returns_empty_string(
        self, test_node: TestNode
    ) -> None:
        """Test that missing input field returns empty string in template."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.nonexistent}",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},  # No fields
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedHttpContext)
        # Missing input fields resolve to empty string
        assert result.url == "https://api.example.com/users/"

    def test_multiple_templates_in_single_string(self, test_node: TestNode) -> None:
        """Test resolving multiple templates in single string."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/${input.version}/users/${input.user_id}",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"version": "v2", "user_id": "123"},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedHttpContext)
        assert result.url == "https://api.example.com/v2/users/123"

    def test_nested_input_path_resolution(self, test_node: TestNode) -> None:
        """Test resolving deeply nested input paths."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user.profile.id}",
            method="GET",
        )
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"user": {"profile": {"id": "nested_123"}}},
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert isinstance(result, ModelResolvedHttpContext)
        assert result.url == "https://api.example.com/users/nested_123"

    @pytest.mark.asyncio
    async def test_model_onex_error_passthrough(
        self, test_node: TestNode, mock_container: MockContainer
    ) -> None:
        """Test that ModelOnexError from handler is passed through unchanged."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        mock_handler = AsyncMock()
        original_error = ModelOnexError(
            message="Original handler error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
        mock_handler.execute.side_effect = original_error
        mock_container.register_service("ProtocolEffectHandler_HTTP", mock_handler)

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "operations": [
                    {
                        "io_config": {
                            "handler_type": "http",
                            "url_template": "https://api.example.com/test",
                            "method": "GET",
                        },
                    }
                ]
            },
            retry_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.execute_effect(input_data)

        # The original ModelOnexError should be passed through unchanged
        # Verify the original error message is preserved
        assert "Original handler error" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
class TestMixinEffectExecutionThreadSafety:
    """Thread safety tests for MixinEffectExecution.

    These tests verify that the mixin properly handles concurrent access
    to shared state like circuit breakers.

    See docs/guides/THREADING.md for complete thread safety guidance.
    """

    def test_circuit_breakers_dict_is_instance_specific(self) -> None:
        """Test that each instance gets its own circuit breakers dictionary.

        This is critical for thread safety - each node instance should have
        its own circuit breakers to avoid cross-thread contamination.
        """
        container1 = MockContainer()
        container2 = MockContainer()

        node1 = TestNode(container=container1)
        node2 = TestNode(container=container2)

        # Each node should have its own circuit breakers dict
        assert node1._circuit_breakers is not node2._circuit_breakers

        # Adding to one should not affect the other
        from uuid import uuid4

        operation_id = uuid4()
        node1._check_circuit_breaker(operation_id)

        assert operation_id in node1._circuit_breakers
        assert operation_id not in node2._circuit_breakers

    def test_thread_local_node_instances_recommended_pattern(self) -> None:
        """Demonstrate the recommended thread-local pattern for safe concurrent usage.

        This test validates the pattern documented in docs/guides/THREADING.md:
        each thread should create its own node instance to avoid race conditions.
        """
        import threading

        container = MockContainer()
        thread_local = threading.local()

        def get_thread_local_node() -> TestNode:
            """Get or create thread-local TestNode instance."""
            if not hasattr(thread_local, "effect_node"):
                thread_local.effect_node = TestNode(container=container)
            return thread_local.effect_node

        # Track instances created by each thread
        instances: list[TestNode] = []
        lock = threading.Lock()

        def worker() -> None:
            """Each thread gets its own node instance."""
            node = get_thread_local_node()
            with lock:
                instances.append(node)

        # Launch multiple threads
        threads = []
        num_threads = 3
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have gotten a unique instance
        instance_ids = [id(inst) for inst in instances]
        assert len(instance_ids) == num_threads
        assert len(set(instance_ids)) == num_threads, (
            "Each thread should have a unique node instance for thread safety"
        )

    def test_circuit_breaker_state_isolation(self) -> None:
        """Test that circuit breaker state is isolated per operation_id.

        This ensures that different operations don't interfere with each other's
        circuit breaker state, which is important for concurrent usage.
        """
        container = MockContainer()
        node = TestNode(container=container)

        from uuid import uuid4

        # Create two different operation IDs
        op_id_1 = uuid4()
        op_id_2 = uuid4()

        # Initialize circuit breakers for both
        node._check_circuit_breaker(op_id_1)
        node._check_circuit_breaker(op_id_2)

        # Record failures for one operation
        for _ in range(3):
            node._record_circuit_breaker_result(op_id_1, success=False)

        # Other operation should be unaffected
        cb1 = node._circuit_breakers[op_id_1]
        cb2 = node._circuit_breakers[op_id_2]

        assert cb1.failure_count == 3
        assert cb2.failure_count == 0


@pytest.mark.unit
class TestEffectContractYamlParsing:
    """Tests for YAML effect contract parsing.

    These tests verify that the example YAML contracts in examples/contracts/effect/
    parse correctly and can be used to configure effect operations.

    Tests validate:
    - YAML syntax correctness
    - IO configuration parsing for all handler types (HTTP, DB, Kafka, Filesystem)
    - Retry policy configuration
    - Circuit breaker configuration
    - Response handling configuration
    - Template variable syntax
    """

    @staticmethod
    def _get_examples_dir() -> str:
        """Get path to examples/contracts/effect directory."""
        from pathlib import Path

        # Navigate from tests/unit/mixins to project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        return str(project_root / "examples" / "contracts" / "effect")

    def test_http_api_call_contract_parses_correctly(self) -> None:
        """Test that http_api_call.yaml parses with valid effect_operations."""
        from pathlib import Path

        import yaml

        contract_path = Path(self._get_examples_dir()) / "http_api_call.yaml"
        if not contract_path.exists():
            pytest.skip(f"Example contract not found: {contract_path}")

        with open(contract_path) as f:
            contract_data = yaml.safe_load(f)

        # Verify structure
        assert "effect_operations" in contract_data, "Missing effect_operations section"
        effect_ops = contract_data["effect_operations"]

        # Verify version
        assert "version" in effect_ops, "Missing version in effect_operations"

        # Verify operations array
        assert "operations" in effect_ops, "Missing operations array"
        assert len(effect_ops["operations"]) > 0, "Operations array should not be empty"

        # Verify first operation has required fields
        first_op = effect_ops["operations"][0]
        assert "operation_name" in first_op, "Missing operation_name"
        assert "io_config" in first_op, "Missing io_config"
        assert first_op["io_config"]["handler_type"] == "http", (
            "Handler type should be http"
        )

    def test_filesystem_operations_contract_parses_correctly(self) -> None:
        """Test that filesystem_operations.yaml parses with valid effect_operations."""
        from pathlib import Path

        import yaml

        contract_path = Path(self._get_examples_dir()) / "filesystem_operations.yaml"
        if not contract_path.exists():
            pytest.skip(f"Example contract not found: {contract_path}")

        with open(contract_path) as f:
            contract_data = yaml.safe_load(f)

        # Verify structure
        assert "effect_operations" in contract_data, "Missing effect_operations section"
        effect_ops = contract_data["effect_operations"]

        # Verify operations array
        assert "operations" in effect_ops, "Missing operations array"
        assert len(effect_ops["operations"]) > 0, "Operations array should not be empty"

        # Verify filesystem operations have correct handler type
        for op in effect_ops["operations"]:
            assert op["io_config"]["handler_type"] == "filesystem", (
                f"Handler type should be filesystem for operation: {op.get('operation_name')}"
            )

    def test_db_query_contract_parses_correctly(self) -> None:
        """Test that db_query.yaml parses with valid effect_operations."""
        from pathlib import Path

        import yaml

        contract_path = Path(self._get_examples_dir()) / "db_query.yaml"
        if not contract_path.exists():
            pytest.skip(f"Example contract not found: {contract_path}")

        with open(contract_path) as f:
            contract_data = yaml.safe_load(f)

        # Verify structure
        assert "effect_operations" in contract_data, "Missing effect_operations section"
        effect_ops = contract_data["effect_operations"]

        # Verify operations exist
        assert "operations" in effect_ops, "Missing operations array"
        assert len(effect_ops["operations"]) > 0, "Operations array should not be empty"

        # Verify DB operations have correct handler type
        for op in effect_ops["operations"]:
            assert op["io_config"]["handler_type"] == "db", (
                f"Handler type should be db for operation: {op.get('operation_name')}"
            )

    def test_kafka_produce_contract_parses_correctly(self) -> None:
        """Test that kafka_produce.yaml parses with valid effect_operations."""
        from pathlib import Path

        import yaml

        contract_path = Path(self._get_examples_dir()) / "kafka_produce.yaml"
        if not contract_path.exists():
            pytest.skip(f"Example contract not found: {contract_path}")

        with open(contract_path) as f:
            contract_data = yaml.safe_load(f)

        # Verify structure
        assert "effect_operations" in contract_data, "Missing effect_operations section"
        effect_ops = contract_data["effect_operations"]

        # Verify operations exist
        assert "operations" in effect_ops, "Missing operations array"
        assert len(effect_ops["operations"]) > 0, "Operations array should not be empty"

        # Verify Kafka operations have correct handler type
        for op in effect_ops["operations"]:
            assert op["io_config"]["handler_type"] == "kafka", (
                f"Handler type should be kafka for operation: {op.get('operation_name')}"
            )

    def test_resilient_effect_contract_parses_correctly(self) -> None:
        """Test that resilient_effect.yaml parses with retry and circuit breaker config."""
        from pathlib import Path

        import yaml

        contract_path = Path(self._get_examples_dir()) / "resilient_effect.yaml"
        if not contract_path.exists():
            pytest.skip(f"Example contract not found: {contract_path}")

        with open(contract_path) as f:
            contract_data = yaml.safe_load(f)

        # Verify structure
        assert "effect_operations" in contract_data, "Missing effect_operations section"
        effect_ops = contract_data["effect_operations"]

        # Verify operations exist
        assert "operations" in effect_ops, "Missing operations array"

        # Check for resilience configuration (retry_policy or circuit_breaker)
        has_resilience_config = False
        for op in effect_ops["operations"]:
            if "retry_policy" in op or "circuit_breaker" in op:
                has_resilience_config = True
                break

        # Also check for default policies at the effect_operations level
        if (
            "default_retry_policy" in effect_ops
            or "default_circuit_breaker" in effect_ops
        ):
            has_resilience_config = True

        assert has_resilience_config, (
            "Resilient effect contract should have retry_policy or circuit_breaker configuration"
        )

    def test_all_example_contracts_parse_without_error(self) -> None:
        """Test that all example YAML contracts parse without YAML syntax errors."""
        from pathlib import Path

        import yaml

        examples_dir = Path(self._get_examples_dir())
        if not examples_dir.exists():
            pytest.skip(f"Examples directory not found: {examples_dir}")

        yaml_files = list(examples_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No YAML files found in examples/contracts/effect/"

        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                try:
                    data = yaml.safe_load(f)
                    assert data is not None, f"Empty YAML file: {yaml_file.name}"
                except yaml.YAMLError as e:
                    pytest.fail(f"YAML parsing error in {yaml_file.name}: {e}")

    def test_io_config_extraction_from_yaml_operation(
        self, test_node: TestNode
    ) -> None:
        """Test that _parse_io_config correctly parses YAML-style operation configs."""
        from omnibase_core.models.operations import ModelEffectOperationConfig

        # Simulate a YAML operation config structure
        yaml_operation = {
            "operation_name": "test_http_call",
            "io_config": {
                "handler_type": "http",
                "url_template": "https://api.example.com/v1/users/${input.user_id}",
                "method": "GET",
                "headers": {
                    "Authorization": "Bearer ${secret.API_TOKEN}",
                    "Content-Type": "application/json",
                },
                "timeout_ms": 5000,
            },
            "retry_policy": {
                "max_retries": 3,
                "backoff_strategy": "exponential",
                "base_delay_ms": 100,
            },
        }

        # Convert dict to typed model (as the mixin now expects)
        operation_config = ModelEffectOperationConfig.from_dict(yaml_operation)

        # Test that io_config parses correctly
        io_config = test_node._parse_io_config(operation_config)

        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelHttpIOConfig,
        )

        assert isinstance(io_config, ModelHttpIOConfig)
        assert (
            io_config.url_template
            == "https://api.example.com/v1/users/${input.user_id}"
        )
        assert io_config.method == "GET"
        assert io_config.headers["Content-Type"] == "application/json"

    def test_template_variables_in_yaml_configs(self, test_node: TestNode) -> None:
        """Test that template variables in YAML configs resolve correctly."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/${input.version}/users/${input.user_id}",
            method="GET",
            headers={"X-Request-ID": "${input.request_id}"},
        )

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "version": "v2",
                "user_id": "12345",
                "request_id": "req-abc-123",
            },
        )

        result = test_node._resolve_io_context(io_config, input_data)

        assert result.url == "https://api.example.com/v2/users/12345"
        assert result.headers["X-Request-ID"] == "req-abc-123"
