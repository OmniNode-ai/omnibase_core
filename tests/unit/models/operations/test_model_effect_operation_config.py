# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEffectOperationConfig model.

Validates the effect operation runtime configuration model including:
- IO configuration handling (typed models and dicts)
- Factory methods (from_dict, from_effect_operation)
- Helper methods (get_io_config_as_dict, get_response_handling_as_dict, get_typed_io_config)
- Optional field handling
- Immutability (frozen model)
- Validation behavior
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
    ModelEffectCircuitBreaker,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
    ModelEffectResponseHandling,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.operations.model_effect_operation_config import (
    ModelEffectOperationConfig,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def http_io_config() -> ModelHttpIOConfig:
    """Create a minimal HTTP IO config for testing."""
    return ModelHttpIOConfig(
        handler_type=EnumEffectHandlerType.HTTP,
        url_template="https://api.example.com/users/${input.user_id}",
        method="GET",
    )


@pytest.fixture
def http_io_config_dict() -> dict:
    """Create a dict-based HTTP IO config for testing."""
    return {
        "handler_type": "http",
        "url_template": "https://api.example.com/users/123",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body_template": '{"name": "${input.name}"}',
    }


@pytest.fixture
def db_io_config() -> ModelDbIOConfig:
    """Create a minimal DB IO config for testing."""
    return ModelDbIOConfig(
        handler_type=EnumEffectHandlerType.DB,
        operation="select",
        connection_name="primary_db",
        query_template="SELECT * FROM users WHERE id = $1",
        query_params=["${input.user_id}"],
    )


@pytest.fixture
def db_io_config_dict() -> dict:
    """Create a dict-based DB IO config for testing."""
    return {
        "handler_type": "db",
        "operation": "select",
        "connection_name": "test_db",
        "query_template": "SELECT * FROM orders WHERE user_id = $1",
        "query_params": ["${input.user_id}"],
    }


@pytest.fixture
def kafka_io_config() -> ModelKafkaIOConfig:
    """Create a minimal Kafka IO config for testing."""
    return ModelKafkaIOConfig(
        handler_type=EnumEffectHandlerType.KAFKA,
        topic="user-events",
        payload_template='{"user_id": "${input.user_id}", "action": "created"}',
    )


@pytest.fixture
def kafka_io_config_dict() -> dict:
    """Create a dict-based Kafka IO config for testing."""
    return {
        "handler_type": "kafka",
        "topic": "order-events",
        "payload_template": '{"order_id": "${input.order_id}"}',
        "partition_key_template": "${input.order_id}",
    }


@pytest.fixture
def filesystem_io_config() -> ModelFilesystemIOConfig:
    """Create a minimal Filesystem IO config for testing."""
    return ModelFilesystemIOConfig(
        handler_type=EnumEffectHandlerType.FILESYSTEM,
        file_path_template="/data/output/${input.filename}.json",
        operation="write",
    )


@pytest.fixture
def filesystem_io_config_dict() -> dict:
    """Create a dict-based Filesystem IO config for testing.

    Note: atomic=False is required for 'read' operations since
    atomic=True is the default and only valid for 'write' operations.
    """
    return {
        "handler_type": "filesystem",
        "file_path_template": "/data/archive/${input.date}/${input.file}.txt",
        "operation": "read",
        "atomic": False,  # Required: atomic=True (default) is only valid for 'write'
    }


@pytest.fixture
def response_handling() -> ModelEffectResponseHandling:
    """Create a response handling config for testing."""
    return ModelEffectResponseHandling(
        success_codes=[200, 201],
        extract_fields={"user_id": "$.data.id", "email": "$.data.email"},
        fail_on_empty=True,
    )


@pytest.fixture
def retry_policy() -> ModelEffectRetryPolicy:
    """Create a retry policy for testing."""
    return ModelEffectRetryPolicy(
        enabled=True,
        max_retries=3,
        backoff_strategy="exponential",
        base_delay_ms=1000,
    )


@pytest.fixture
def circuit_breaker() -> ModelEffectCircuitBreaker:
    """Create a circuit breaker config for testing."""
    return ModelEffectCircuitBreaker(
        enabled=True,
        failure_threshold=5,
        success_threshold=2,
        timeout_ms=60000,
    )


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigBasic:
    """Test basic instantiation of ModelEffectOperationConfig."""

    def test_minimal_http_config(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test creating config with minimal HTTP io_config."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        assert config.io_config == http_io_config
        assert config.operation_name == "unknown"  # Default value
        assert config.description is None
        assert config.operation_timeout_ms is None
        assert config.response_handling is None
        assert config.retry_policy is None
        assert config.circuit_breaker is None
        assert config.correlation_id is None
        assert config.idempotent is None

    def test_minimal_db_config(self, db_io_config: ModelDbIOConfig) -> None:
        """Test creating config with minimal DB io_config."""
        config = ModelEffectOperationConfig(io_config=db_io_config)

        assert config.io_config == db_io_config
        assert config.io_config.handler_type == EnumEffectHandlerType.DB

    def test_minimal_kafka_config(self, kafka_io_config: ModelKafkaIOConfig) -> None:
        """Test creating config with minimal Kafka io_config."""
        config = ModelEffectOperationConfig(io_config=kafka_io_config)

        assert config.io_config == kafka_io_config
        assert config.io_config.handler_type == EnumEffectHandlerType.KAFKA

    def test_minimal_filesystem_config(
        self, filesystem_io_config: ModelFilesystemIOConfig
    ) -> None:
        """Test creating config with minimal Filesystem io_config."""
        config = ModelEffectOperationConfig(io_config=filesystem_io_config)

        assert config.io_config == filesystem_io_config
        assert config.io_config.handler_type == EnumEffectHandlerType.FILESYSTEM

    def test_full_config_with_all_fields(
        self,
        http_io_config: ModelHttpIOConfig,
        response_handling: ModelEffectResponseHandling,
        retry_policy: ModelEffectRetryPolicy,
        circuit_breaker: ModelEffectCircuitBreaker,
    ) -> None:
        """Test creating config with all optional fields populated."""
        correlation_id = uuid4()

        config = ModelEffectOperationConfig(
            io_config=http_io_config,
            operation_name="fetch_user_profile",
            description="Fetches user profile data from the API",
            operation_timeout_ms=5000,
            response_handling=response_handling,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            correlation_id=correlation_id,
            idempotent=True,
        )

        assert config.io_config == http_io_config
        assert config.operation_name == "fetch_user_profile"
        assert config.description == "Fetches user profile data from the API"
        assert config.operation_timeout_ms == 5000
        assert config.response_handling == response_handling
        assert config.retry_policy == retry_policy
        assert config.circuit_breaker == circuit_breaker
        assert config.correlation_id == correlation_id
        assert config.idempotent is True


# =============================================================================
# Dict-Based IO Config Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigDictIOConfig:
    """Test io_config handling when provided as a dict.

    Note: Pydantic validates valid dicts into typed models when they match
    a known handler_type. The dict[str, Any] in the union type is primarily
    for forward compatibility or cases where validation into typed models
    is not possible.
    """

    def test_http_io_config_as_dict(self, http_io_config_dict: dict) -> None:
        """Test creating config with HTTP io_config as dict.

        When a valid HTTP dict is provided, Pydantic validates it into
        ModelHttpIOConfig.
        """
        config = ModelEffectOperationConfig(io_config=http_io_config_dict)

        # Dict is validated into typed model
        assert isinstance(config.io_config, ModelHttpIOConfig)
        assert config.io_config.handler_type == EnumEffectHandlerType.HTTP
        assert config.io_config.method == "POST"

    def test_db_io_config_as_dict(self, db_io_config_dict: dict) -> None:
        """Test creating config with DB io_config as dict."""
        config = ModelEffectOperationConfig(io_config=db_io_config_dict)

        # Dict is validated into typed model
        assert isinstance(config.io_config, ModelDbIOConfig)
        assert config.io_config.handler_type == EnumEffectHandlerType.DB
        assert config.io_config.operation == "select"

    def test_kafka_io_config_as_dict(self, kafka_io_config_dict: dict) -> None:
        """Test creating config with Kafka io_config as dict."""
        config = ModelEffectOperationConfig(io_config=kafka_io_config_dict)

        # Dict is validated into typed model
        assert isinstance(config.io_config, ModelKafkaIOConfig)
        assert config.io_config.handler_type == EnumEffectHandlerType.KAFKA
        assert config.io_config.topic == "order-events"

    def test_filesystem_io_config_as_dict(
        self, filesystem_io_config_dict: dict
    ) -> None:
        """Test creating config with Filesystem io_config as dict."""
        config = ModelEffectOperationConfig(io_config=filesystem_io_config_dict)

        # Dict is validated into typed model
        assert isinstance(config.io_config, ModelFilesystemIOConfig)
        assert config.io_config.handler_type == EnumEffectHandlerType.FILESYSTEM
        assert config.io_config.operation == "read"

    def test_unknown_handler_type_raises_validation_error(self) -> None:
        """Test that unknown handler types raise ValidationError at parse time.

        With the discriminated union, unknown handler types are rejected during
        model validation, not kept as dicts.
        """
        unknown_dict = {
            "handler_type": "custom_unknown",
            "some_field": "value",
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectOperationConfig(io_config=unknown_dict)

        errors = exc_info.value.errors()
        assert any(error["type"] == "union_tag_invalid" for error in errors)


# =============================================================================
# get_io_config_as_dict() Method Tests
# =============================================================================


@pytest.mark.unit
class TestGetIOConfigAsDict:
    """Test the get_io_config_as_dict() method."""

    def test_typed_http_config_to_dict(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test converting typed HTTP io_config to dict."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        result = config.get_io_config_as_dict()

        assert isinstance(result, dict)
        assert result["handler_type"] == EnumEffectHandlerType.HTTP
        assert result["url_template"] == http_io_config.url_template
        assert result["method"] == "GET"

    def test_typed_db_config_to_dict(self, db_io_config: ModelDbIOConfig) -> None:
        """Test converting typed DB io_config to dict."""
        config = ModelEffectOperationConfig(io_config=db_io_config)

        result = config.get_io_config_as_dict()

        assert isinstance(result, dict)
        assert result["handler_type"] == EnumEffectHandlerType.DB
        assert result["operation"] == "select"

    def test_typed_kafka_config_to_dict(
        self, kafka_io_config: ModelKafkaIOConfig
    ) -> None:
        """Test converting typed Kafka io_config to dict."""
        config = ModelEffectOperationConfig(io_config=kafka_io_config)

        result = config.get_io_config_as_dict()

        assert isinstance(result, dict)
        assert result["handler_type"] == EnumEffectHandlerType.KAFKA
        assert result["topic"] == "user-events"

    def test_typed_filesystem_config_to_dict(
        self, filesystem_io_config: ModelFilesystemIOConfig
    ) -> None:
        """Test converting typed Filesystem io_config to dict."""
        config = ModelEffectOperationConfig(io_config=filesystem_io_config)

        result = config.get_io_config_as_dict()

        assert isinstance(result, dict)
        assert result["handler_type"] == EnumEffectHandlerType.FILESYSTEM
        assert result["operation"] == "write"

    def test_dict_config_returns_model_dump(self, http_io_config_dict: dict) -> None:
        """Test that dict io_config (validated to model) returns model_dump.

        When a valid dict is provided, Pydantic validates it into a typed model.
        get_io_config_as_dict() then returns the model_dump() of that typed model,
        which includes default values.
        """
        config = ModelEffectOperationConfig(io_config=http_io_config_dict)

        result = config.get_io_config_as_dict()

        # Result contains original values plus defaults
        assert result["handler_type"] == EnumEffectHandlerType.HTTP
        assert result["method"] == "POST"
        assert result["url_template"] == http_io_config_dict["url_template"]
        # Default values are included
        assert "timeout_ms" in result

    def test_typed_config_serializes_to_dict(self) -> None:
        """Test that typed io_config serializes correctly via get_io_config_as_dict().

        Since io_config is now always a typed model (discriminated union),
        get_io_config_as_dict() serializes it via model_dump().
        """
        config = ModelEffectOperationConfig(
            io_config={
                "handler_type": "http",
                "url_template": "https://example.com",
                "method": "GET",
            }
        )

        result = config.get_io_config_as_dict()

        assert result["handler_type"] == "http"
        assert result["url_template"] == "https://example.com"
        assert result["method"] == "GET"


# =============================================================================
# get_response_handling_as_dict() Method Tests
# =============================================================================


@pytest.mark.unit
class TestGetResponseHandlingAsDict:
    """Test the get_response_handling_as_dict() method."""

    def test_none_response_handling_returns_empty_dict(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that None response_handling returns empty dict."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        result = config.get_response_handling_as_dict()

        assert result == {}

    def test_typed_response_handling_to_dict(
        self,
        http_io_config: ModelHttpIOConfig,
        response_handling: ModelEffectResponseHandling,
    ) -> None:
        """Test converting typed response_handling to dict."""
        config = ModelEffectOperationConfig(
            io_config=http_io_config, response_handling=response_handling
        )

        result = config.get_response_handling_as_dict()

        assert isinstance(result, dict)
        assert result["success_codes"] == [200, 201]
        assert result["extract_fields"] == {
            "user_id": "$.data.id",
            "email": "$.data.email",
        }
        assert result["fail_on_empty"] is True

    def test_dict_response_handling_returns_validated_dict(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that dict response_handling is validated and returns model dump.

        When a valid dict is provided for response_handling, Pydantic validates it
        into ModelEffectResponseHandling. get_response_handling_as_dict() then
        returns the model_dump(), which includes default values.
        """
        response_dict = {
            "success_codes": [200],
            "extract_fields": {"id": "$.id"},
            "fail_on_empty": False,
        }

        config = ModelEffectOperationConfig(
            io_config=http_io_config, response_handling=response_dict
        )

        result = config.get_response_handling_as_dict()

        # Original values are preserved
        assert result["success_codes"] == [200]
        assert result["extract_fields"] == {"id": "$.id"}
        assert result["fail_on_empty"] is False
        # Default values are included (e.g., extraction_engine)
        assert "extraction_engine" in result


# =============================================================================
# get_typed_io_config() Method Tests
# =============================================================================


@pytest.mark.unit
class TestGetTypedIOConfig:
    """Test the get_typed_io_config() method."""

    def test_already_typed_http_config(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test get_typed_io_config with already typed HTTP config."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        result = config.get_typed_io_config()

        assert result is http_io_config
        assert isinstance(result, ModelHttpIOConfig)

    def test_already_typed_db_config(self, db_io_config: ModelDbIOConfig) -> None:
        """Test get_typed_io_config with already typed DB config."""
        config = ModelEffectOperationConfig(io_config=db_io_config)

        result = config.get_typed_io_config()

        assert result is db_io_config
        assert isinstance(result, ModelDbIOConfig)

    def test_already_typed_kafka_config(
        self, kafka_io_config: ModelKafkaIOConfig
    ) -> None:
        """Test get_typed_io_config with already typed Kafka config."""
        config = ModelEffectOperationConfig(io_config=kafka_io_config)

        result = config.get_typed_io_config()

        assert result is kafka_io_config
        assert isinstance(result, ModelKafkaIOConfig)

    def test_already_typed_filesystem_config(
        self, filesystem_io_config: ModelFilesystemIOConfig
    ) -> None:
        """Test get_typed_io_config with already typed Filesystem config."""
        config = ModelEffectOperationConfig(io_config=filesystem_io_config)

        result = config.get_typed_io_config()

        assert result is filesystem_io_config
        assert isinstance(result, ModelFilesystemIOConfig)

    def test_dict_to_typed_http_config(self, http_io_config_dict: dict) -> None:
        """Test converting dict to typed HTTP config."""
        config = ModelEffectOperationConfig(io_config=http_io_config_dict)

        result = config.get_typed_io_config()

        assert isinstance(result, ModelHttpIOConfig)
        assert result.handler_type == EnumEffectHandlerType.HTTP
        assert result.method == "POST"

    def test_dict_to_typed_db_config(self, db_io_config_dict: dict) -> None:
        """Test converting dict to typed DB config."""
        config = ModelEffectOperationConfig(io_config=db_io_config_dict)

        result = config.get_typed_io_config()

        assert isinstance(result, ModelDbIOConfig)
        assert result.handler_type == EnumEffectHandlerType.DB
        assert result.operation == "select"

    def test_dict_to_typed_kafka_config(self, kafka_io_config_dict: dict) -> None:
        """Test converting dict to typed Kafka config."""
        config = ModelEffectOperationConfig(io_config=kafka_io_config_dict)

        result = config.get_typed_io_config()

        assert isinstance(result, ModelKafkaIOConfig)
        assert result.handler_type == EnumEffectHandlerType.KAFKA
        assert result.topic == "order-events"

    def test_dict_to_typed_filesystem_config(
        self, filesystem_io_config_dict: dict
    ) -> None:
        """Test converting dict to typed Filesystem config."""
        config = ModelEffectOperationConfig(io_config=filesystem_io_config_dict)

        result = config.get_typed_io_config()

        assert isinstance(result, ModelFilesystemIOConfig)
        assert result.handler_type == EnumEffectHandlerType.FILESYSTEM
        assert result.operation == "read"

    def test_unknown_handler_type_raises_validation_error(self) -> None:
        """Test that unknown handler_type raises ValidationError at parse time.

        With the discriminated union, unknown handler types are rejected during
        model validation, before get_typed_io_config() is called.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectOperationConfig(
                io_config={"handler_type": "unknown", "some_field": "value"}
            )

        errors = exc_info.value.errors()
        assert any(error["type"] == "union_tag_invalid" for error in errors)

    def test_dict_without_handler_type_raises_validation_error(self) -> None:
        """Test that dict without handler_type raises ValidationError.

        The discriminated union requires handler_type to select the correct model.
        Without it, validation fails.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectOperationConfig(
                io_config={"url_template": "https://example.com", "method": "GET"}
            )

        errors = exc_info.value.errors()
        assert any(error["type"] == "union_tag_not_found" for error in errors)

    def test_get_typed_io_config_returns_io_config(self) -> None:
        """Test that get_typed_io_config returns the already-typed io_config.

        Since io_config is now always typed via discriminated union,
        get_typed_io_config simply returns it.
        """
        config = ModelEffectOperationConfig(
            io_config={
                "handler_type": "http",
                "url_template": "https://example.com",
                "method": "GET",
            }
        )

        typed = config.get_typed_io_config()
        assert typed is config.io_config


# =============================================================================
# from_dict() Factory Method Tests
# =============================================================================


@pytest.mark.unit
class TestFromDictFactory:
    """Test the from_dict() factory method."""

    def test_from_dict_minimal(self, http_io_config_dict: dict) -> None:
        """Test from_dict with minimal data.

        The io_config dict is validated into a typed model (ModelHttpIOConfig).
        """
        data = {"io_config": http_io_config_dict}

        config = ModelEffectOperationConfig.from_dict(data)

        assert isinstance(config, ModelEffectOperationConfig)
        # io_config is validated into typed model, not kept as dict
        assert isinstance(config.io_config, ModelHttpIOConfig)
        assert config.io_config.method == "POST"
        assert config.io_config.url_template == http_io_config_dict["url_template"]

    def test_from_dict_with_all_fields(
        self, http_io_config_dict: dict, retry_policy: ModelEffectRetryPolicy
    ) -> None:
        """Test from_dict with all fields."""
        correlation_id = str(uuid4())

        data = {
            "io_config": http_io_config_dict,
            "operation_name": "api_call",
            "description": "Makes an API call",
            "operation_timeout_ms": 10000,
            "response_handling": {
                "success_codes": [200],
                "extract_fields": {"id": "$.id"},
            },
            "retry_policy": {
                "enabled": True,
                "max_retries": 5,
            },
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 10,
            },
            "correlation_id": correlation_id,
            "idempotent": True,
        }

        config = ModelEffectOperationConfig.from_dict(data)

        assert config.operation_name == "api_call"
        assert config.description == "Makes an API call"
        assert config.operation_timeout_ms == 10000
        assert config.correlation_id == correlation_id
        assert config.idempotent is True

    def test_from_dict_missing_io_config_raises_error(self) -> None:
        """Test that from_dict raises ValueError when io_config is missing."""
        with pytest.raises(ValueError, match="io_config is required"):
            ModelEffectOperationConfig.from_dict({"operation_name": "test"})


# =============================================================================
# from_effect_operation() Factory Method Tests
# =============================================================================


@pytest.mark.unit
class TestFromEffectOperationFactory:
    """Test the from_effect_operation() factory method."""

    def test_from_effect_operation_minimal(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test from_effect_operation with minimal ModelEffectOperation."""
        operation = ModelEffectOperation(
            operation_name="fetch_user",
            io_config=http_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert isinstance(config, ModelEffectOperationConfig)
        assert config.io_config == http_io_config
        assert config.operation_name == "fetch_user"

    def test_from_effect_operation_with_all_fields(
        self,
        http_io_config: ModelHttpIOConfig,
        response_handling: ModelEffectResponseHandling,
        retry_policy: ModelEffectRetryPolicy,
        circuit_breaker: ModelEffectCircuitBreaker,
    ) -> None:
        """Test from_effect_operation with all fields populated."""
        operation = ModelEffectOperation(
            operation_name="create_order",
            description="Creates a new order in the system",
            io_config=http_io_config,
            response_handling=response_handling,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            idempotent=False,
            operation_timeout_ms=15000,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert config.operation_name == "create_order"
        assert config.description == "Creates a new order in the system"
        assert config.io_config == http_io_config
        assert config.response_handling == response_handling
        assert config.retry_policy == retry_policy
        assert config.circuit_breaker == circuit_breaker
        assert config.idempotent is False
        assert config.operation_timeout_ms == 15000
        # correlation_id is copied from operation
        assert config.correlation_id == operation.correlation_id

    def test_from_effect_operation_preserves_correlation_id(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that correlation_id is preserved from the operation."""
        operation = ModelEffectOperation(
            operation_name="test_op",
            io_config=http_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert config.correlation_id == operation.correlation_id
        assert isinstance(config.correlation_id, UUID)

    # =========================================================================
    # Edge Case Tests for from_effect_operation
    # =========================================================================

    def test_from_effect_operation_with_db_io_config(
        self, db_io_config: ModelDbIOConfig
    ) -> None:
        """Test from_effect_operation with DB io_config."""
        operation = ModelEffectOperation(
            operation_name="query_users",
            io_config=db_io_config,
            description="Query users from database",
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert isinstance(config, ModelEffectOperationConfig)
        assert config.io_config == db_io_config
        assert isinstance(config.io_config, ModelDbIOConfig)
        assert config.operation_name == "query_users"
        assert config.description == "Query users from database"

    def test_from_effect_operation_with_kafka_io_config(
        self, kafka_io_config: ModelKafkaIOConfig
    ) -> None:
        """Test from_effect_operation with Kafka io_config."""
        operation = ModelEffectOperation(
            operation_name="publish_event",
            io_config=kafka_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert isinstance(config, ModelEffectOperationConfig)
        assert config.io_config == kafka_io_config
        assert isinstance(config.io_config, ModelKafkaIOConfig)
        assert config.operation_name == "publish_event"

    def test_from_effect_operation_with_filesystem_io_config(
        self, filesystem_io_config: ModelFilesystemIOConfig
    ) -> None:
        """Test from_effect_operation with Filesystem io_config."""
        operation = ModelEffectOperation(
            operation_name="write_file",
            io_config=filesystem_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert isinstance(config, ModelEffectOperationConfig)
        assert config.io_config == filesystem_io_config
        assert isinstance(config.io_config, ModelFilesystemIOConfig)
        assert config.operation_name == "write_file"

    def test_from_effect_operation_preserves_none_optional_fields(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that None values for optional fields are preserved correctly.

        ModelEffectOperation has defaults for some fields (e.g., response_handling
        has default_factory). Verify the conversion preserves these correctly.
        """
        operation = ModelEffectOperation(
            operation_name="minimal_op",
            io_config=http_io_config,
            # retry_policy, circuit_breaker, operation_timeout_ms are None by default
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        # Optional fields that default to None should be None
        assert config.retry_policy is None
        assert config.circuit_breaker is None
        assert config.operation_timeout_ms is None
        # idempotent defaults to None in ModelEffectOperation
        assert config.idempotent is None

    def test_from_effect_operation_with_explicit_none_idempotent(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test from_effect_operation with explicitly set idempotent=None.

        When idempotent is explicitly None, it should be preserved as None
        in the resulting config, not converted to a boolean.
        """
        operation = ModelEffectOperation(
            operation_name="explicit_none_test",
            io_config=http_io_config,
            idempotent=None,  # Explicit None
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert config.idempotent is None

    def test_from_effect_operation_with_idempotent_true(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test from_effect_operation with idempotent=True."""
        operation = ModelEffectOperation(
            operation_name="idempotent_op",
            io_config=http_io_config,
            idempotent=True,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert config.idempotent is True

    def test_from_effect_operation_with_idempotent_false(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test from_effect_operation with idempotent=False."""
        operation = ModelEffectOperation(
            operation_name="non_idempotent_op",
            io_config=http_io_config,
            idempotent=False,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        assert config.idempotent is False

    def test_from_effect_operation_preserves_default_response_handling(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that default response_handling from ModelEffectOperation is preserved.

        ModelEffectOperation has `response_handling: ModelEffectResponseHandling =
        Field(default_factory=ModelEffectResponseHandling)`. This means when no
        response_handling is provided, a default instance is created.
        """
        operation = ModelEffectOperation(
            operation_name="default_response_test",
            io_config=http_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        # response_handling should be the default ModelEffectResponseHandling
        assert config.response_handling is not None
        assert isinstance(config.response_handling, ModelEffectResponseHandling)
        # Default ModelEffectResponseHandling has default success codes
        assert config.response_handling.success_codes == [200, 201, 202, 204]

    def test_from_effect_operation_typed_io_config_accessible(
        self, db_io_config: ModelDbIOConfig
    ) -> None:
        """Test that get_typed_io_config works on config created from operation."""
        operation = ModelEffectOperation(
            operation_name="typed_access_test",
            io_config=db_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        # Should be able to get typed io_config
        typed = config.get_typed_io_config()
        assert isinstance(typed, ModelDbIOConfig)
        assert typed.handler_type == db_io_config.handler_type
        assert typed.operation == db_io_config.operation

    def test_from_effect_operation_get_io_config_as_dict(
        self, kafka_io_config: ModelKafkaIOConfig
    ) -> None:
        """Test that get_io_config_as_dict works on config created from operation."""
        operation = ModelEffectOperation(
            operation_name="dict_access_test",
            io_config=kafka_io_config,
        )

        config = ModelEffectOperationConfig.from_effect_operation(operation)

        # Should be able to get io_config as dict
        io_dict = config.get_io_config_as_dict()
        assert isinstance(io_dict, dict)
        assert io_dict["topic"] == kafka_io_config.topic
        assert io_dict["payload_template"] == kafka_io_config.payload_template


# =============================================================================
# Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigValidation:
    """Test validation behavior of ModelEffectOperationConfig."""

    def test_missing_io_config_raises_error(self) -> None:
        """Test that missing io_config raises ValueError."""
        with pytest.raises(ValueError, match="io_config is required"):
            ModelEffectOperationConfig(operation_name="test")

    def test_io_config_none_raises_error(self) -> None:
        """Test that io_config=None raises ValueError."""
        with pytest.raises(ValueError, match="io_config is required"):
            ModelEffectOperationConfig(io_config=None)

    def test_operation_name_min_length(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that operation_name must have at least 1 character."""
        with pytest.raises(ValidationError):
            ModelEffectOperationConfig(io_config=http_io_config, operation_name="")

    def test_operation_timeout_ms_minimum(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that operation_timeout_ms must be at least 1."""
        with pytest.raises(ValidationError):
            ModelEffectOperationConfig(io_config=http_io_config, operation_timeout_ms=0)

    def test_operation_timeout_ms_negative(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that negative operation_timeout_ms is rejected."""
        with pytest.raises(ValidationError):
            ModelEffectOperationConfig(
                io_config=http_io_config, operation_timeout_ms=-100
            )

    def test_valid_operation_timeout_ms(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test valid operation_timeout_ms values."""
        config = ModelEffectOperationConfig(
            io_config=http_io_config, operation_timeout_ms=1
        )
        assert config.operation_timeout_ms == 1

        config2 = ModelEffectOperationConfig(
            io_config=http_io_config, operation_timeout_ms=300000
        )
        assert config2.operation_timeout_ms == 300000

    def test_correlation_id_as_uuid(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that correlation_id accepts UUID objects."""
        correlation_id = uuid4()

        config = ModelEffectOperationConfig(
            io_config=http_io_config, correlation_id=correlation_id
        )

        assert config.correlation_id == correlation_id

    def test_correlation_id_as_string(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that correlation_id accepts string UUIDs."""
        correlation_id_str = str(uuid4())

        config = ModelEffectOperationConfig(
            io_config=http_io_config, correlation_id=correlation_id_str
        )

        assert config.correlation_id == correlation_id_str


# =============================================================================
# Immutability (Frozen Model) Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigImmutability:
    """Test that the model is immutable (frozen=True)."""

    def test_cannot_modify_io_config(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that io_config cannot be modified after creation."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        with pytest.raises(ValidationError):
            config.io_config = ModelHttpIOConfig(
                handler_type=EnumEffectHandlerType.HTTP,
                url_template="https://other.com",
                method="GET",  # Use GET to avoid body_template validation
            )

    def test_cannot_modify_operation_name(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test that operation_name cannot be modified after creation."""
        config = ModelEffectOperationConfig(
            io_config=http_io_config, operation_name="original"
        )

        with pytest.raises(ValidationError):
            config.operation_name = "modified"

    def test_cannot_modify_idempotent(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that idempotent cannot be modified after creation."""
        config = ModelEffectOperationConfig(io_config=http_io_config, idempotent=True)

        with pytest.raises(ValidationError):
            config.idempotent = False

    def test_cannot_add_new_field(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that new fields cannot be added (model is frozen)."""
        config = ModelEffectOperationConfig(io_config=http_io_config)

        with pytest.raises(ValidationError):
            config.new_field = "value"


# =============================================================================
# Extra Fields (extra="forbid") Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigExtraFields:
    """Test that extra fields are forbidden for strict validation."""

    def test_extra_fields_rejected(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test that extra fields are rejected at creation time."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelEffectOperationConfig(
                io_config=http_io_config,
                future_field="some_value",  # type: ignore[call-arg]
                another_new_field=123,  # type: ignore[call-arg]
            )


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigSerialization:
    """Test serialization and deserialization."""

    def test_model_dump_with_typed_io_config(
        self, http_io_config: ModelHttpIOConfig
    ) -> None:
        """Test model_dump with typed io_config."""
        config = ModelEffectOperationConfig(
            io_config=http_io_config,
            operation_name="test_op",
        )

        dumped = config.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["operation_name"] == "test_op"
        assert dumped["io_config"]["handler_type"] == EnumEffectHandlerType.HTTP
        assert dumped["io_config"]["method"] == "GET"

    def test_model_dump_json(self, http_io_config: ModelHttpIOConfig) -> None:
        """Test model_dump_json produces valid JSON."""
        config = ModelEffectOperationConfig(
            io_config=http_io_config,
            operation_name="json_test",
            operation_timeout_ms=5000,
        )

        json_str = config.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "5000" in json_str

    def test_round_trip_serialization(
        self,
        http_io_config: ModelHttpIOConfig,
        response_handling: ModelEffectResponseHandling,
        retry_policy: ModelEffectRetryPolicy,
    ) -> None:
        """Test full round-trip serialization."""
        original = ModelEffectOperationConfig(
            io_config=http_io_config,
            operation_name="round_trip_test",
            description="Testing round-trip serialization",
            operation_timeout_ms=8000,
            response_handling=response_handling,
            retry_policy=retry_policy,
            idempotent=True,
        )

        # Serialize to dict
        dumped = original.model_dump()

        # Deserialize back
        restored = ModelEffectOperationConfig.model_validate(dumped)

        assert restored.operation_name == original.operation_name
        assert restored.description == original.description
        assert restored.operation_timeout_ms == original.operation_timeout_ms
        assert restored.idempotent == original.idempotent


# =============================================================================
# Integration-Style Tests
# =============================================================================


@pytest.mark.unit
class TestModelEffectOperationConfigIntegration:
    """Test real-world usage patterns."""

    def test_http_api_call_pattern(self) -> None:
        """Test typical HTTP API call configuration."""
        config = ModelEffectOperationConfig(
            io_config=ModelHttpIOConfig(
                handler_type=EnumEffectHandlerType.HTTP,
                url_template="https://api.example.com/v1/users/${input.user_id}",
                method="GET",
                headers={
                    "Authorization": "Bearer ${env.API_TOKEN}",
                    "Accept": "application/json",
                },
                timeout_ms=5000,
            ),
            operation_name="get_user_by_id",
            description="Fetches user details from the user service",
            operation_timeout_ms=10000,
            response_handling=ModelEffectResponseHandling(
                success_codes=[200],
                extract_fields={
                    "user_id": "$.data.id",
                    "username": "$.data.username",
                    "email": "$.data.email",
                },
                fail_on_empty=True,
            ),
            retry_policy=ModelEffectRetryPolicy(
                enabled=True,
                max_retries=3,
                backoff_strategy="exponential",
                base_delay_ms=1000,
            ),
            idempotent=True,
        )

        assert config.operation_name == "get_user_by_id"
        assert config.idempotent is True

        # Verify we can get typed config
        typed_io = config.get_typed_io_config()
        assert isinstance(typed_io, ModelHttpIOConfig)
        assert typed_io.method == "GET"

    def test_database_query_pattern(self) -> None:
        """Test typical database query configuration."""
        config = ModelEffectOperationConfig(
            io_config=ModelDbIOConfig(
                handler_type=EnumEffectHandlerType.DB,
                operation="select",
                connection_name="primary_db",
                query_template="SELECT id, name, email FROM users WHERE id = $1",
                query_params=["${input.user_id}"],
                timeout_ms=3000,
                read_only=True,
            ),
            operation_name="select_user",
            idempotent=True,
        )

        typed_io = config.get_typed_io_config()
        assert isinstance(typed_io, ModelDbIOConfig)
        assert typed_io.read_only is True

    def test_kafka_event_publish_pattern(self) -> None:
        """Test typical Kafka event publishing configuration."""
        config = ModelEffectOperationConfig(
            io_config=ModelKafkaIOConfig(
                handler_type=EnumEffectHandlerType.KAFKA,
                topic="user-events",
                payload_template='{"event_type": "user_created", "user_id": "${input.user_id}", "timestamp": "${input.timestamp}"}',
                partition_key_template="${input.user_id}",
                acks="all",
            ),
            operation_name="publish_user_created_event",
            idempotent=False,
        )

        typed_io = config.get_typed_io_config()
        assert isinstance(typed_io, ModelKafkaIOConfig)
        assert typed_io.acks == "all"

    def test_file_write_pattern(self) -> None:
        """Test typical file write configuration."""
        config = ModelEffectOperationConfig(
            io_config=ModelFilesystemIOConfig(
                handler_type=EnumEffectHandlerType.FILESYSTEM,
                file_path_template="/data/output/${input.date}/${input.report_id}.json",
                operation="write",
                atomic=True,
                create_dirs=True,
            ),
            operation_name="write_report",
            idempotent=True,
        )

        typed_io = config.get_typed_io_config()
        assert isinstance(typed_io, ModelFilesystemIOConfig)
        assert typed_io.atomic is True
        assert typed_io.create_dirs is True
