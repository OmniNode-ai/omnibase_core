"""
Tests for Effect IO Configuration Models.

Tests discriminated union behavior, validators, frozen model behavior,
and extra="forbid" configuration for all IO config models.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelHttpIOConfig:
    """Tests for ModelHttpIOConfig model."""

    def test_basic_get_request(self) -> None:
        """Test creating a basic GET request config."""
        config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="GET",
        )
        assert config.handler_type == EnumEffectHandlerType.HTTP
        assert config.method == "GET"
        assert config.url_template == "https://api.example.com/users/${input.user_id}"
        assert config.headers == {}
        assert config.body_template is None
        assert config.query_params == {}
        assert config.timeout_ms == 30000
        assert config.follow_redirects is True
        assert config.verify_ssl is True

    def test_post_request_with_body(self) -> None:
        """Test POST request requires body_template."""
        config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="POST",
            body_template='{"name": "${input.name}"}',
            headers={"Content-Type": "application/json"},
        )
        assert config.method == "POST"
        assert config.body_template == '{"name": "${input.name}"}'
        assert config.headers == {"Content-Type": "application/json"}

    def test_post_without_body_raises_error(self) -> None:
        """Test POST request without body_template raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com/users",
                method="POST",
            )
        assert "body_template is required for POST requests" in str(exc_info.value)

    def test_put_without_body_raises_error(self) -> None:
        """Test PUT request without body_template raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com/users/1",
                method="PUT",
            )
        assert "body_template is required for PUT requests" in str(exc_info.value)

    def test_patch_without_body_raises_error(self) -> None:
        """Test PATCH request without body_template raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com/users/1",
                method="PATCH",
            )
        assert "body_template is required for PATCH requests" in str(exc_info.value)

    def test_delete_without_body_allowed(self) -> None:
        """Test DELETE request doesn't require body_template."""
        config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="DELETE",
        )
        assert config.method == "DELETE"
        assert config.body_template is None

    def test_timeout_bounds(self) -> None:
        """Test timeout_ms bounds validation."""
        # Valid minimum
        config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
            timeout_ms=100,
        )
        assert config.timeout_ms == 100

        # Valid maximum
        config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
            timeout_ms=300000,
        )
        assert config.timeout_ms == 300000

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                timeout_ms=50,
            )
        assert "timeout_ms" in str(exc_info.value)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                timeout_ms=500000,
            )
        assert "timeout_ms" in str(exc_info.value)

    def test_frozen_prevents_modification(self) -> None:
        """Test frozen=True prevents field modification."""
        config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
        )
        with pytest.raises(ValidationError):
            config.method = "POST"  # type: ignore[misc]

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)


class TestModelDbIOConfig:
    """Tests for ModelDbIOConfig model."""

    def test_basic_select_query(self) -> None:
        """Test creating a basic SELECT query config."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
        )
        assert config.handler_type == EnumEffectHandlerType.DB
        assert config.operation == "select"
        assert config.connection_name == "primary_db"
        assert config.query_template == "SELECT * FROM users WHERE id = $1"
        assert config.query_params == ["${input.user_id}"]
        assert config.timeout_ms == 30000
        assert config.fetch_size is None
        assert config.read_only is False

    def test_operation_case_normalization(self) -> None:
        """Test operation is normalized to lowercase."""
        config = ModelDbIOConfig(
            operation="SELECT",  # type: ignore[arg-type]
            connection_name="db",
            query_template="SELECT 1",
            query_params=[],
        )
        assert config.operation == "select"

        config2 = ModelDbIOConfig(
            operation="  UPDATE  ",  # type: ignore[arg-type]
            connection_name="db",
            query_template="UPDATE t SET x = 1",
            query_params=[],
        )
        assert config2.operation == "update"

    def test_sql_injection_prevention_in_raw_queries(self) -> None:
        """Test ${input.*} patterns are blocked in raw queries."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="raw",
                connection_name="db",
                query_template="SELECT * FROM users WHERE name = '${input.name}'",
                query_params=[],
            )
        assert "Raw queries must not contain ${input.*} patterns" in str(exc_info.value)

    def test_sql_injection_pattern_allowed_in_non_raw(self) -> None:
        """Test ${input.*} patterns are allowed in non-raw queries (handled by ORM)."""
        # For non-raw operations, the ORM handles parameterization
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM users WHERE name = ${input.name}",
            query_params=[],
        )
        assert config.operation == "select"

    def test_param_count_matches_placeholders(self) -> None:
        """Test query_params count must match $N placeholders."""
        # Valid: 2 params for $1, $2
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM users WHERE id = $1 AND status = $2",
            query_params=["${input.id}", "${input.status}"],
        )
        assert len(config.query_params) == 2

    def test_param_count_mismatch_too_few(self) -> None:
        """Test error when fewer params than placeholders."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT * FROM users WHERE id = $1 AND status = $2",
                query_params=["${input.id}"],  # Missing second param
            )
        assert "query_params has 1 items" in str(exc_info.value)
        assert "requires 2" in str(exc_info.value)

    def test_param_count_mismatch_too_many(self) -> None:
        """Test error when more params than placeholders."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT * FROM users WHERE id = $1",
                query_params=["${input.id}", "${input.extra}"],  # Extra param
            )
        assert "query_params has 2 items" in str(exc_info.value)
        assert "requires 1" in str(exc_info.value)

    def test_no_placeholders_no_params(self) -> None:
        """Test query with no placeholders requires no params."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT COUNT(*) FROM users",
            query_params=[],
        )
        assert config.query_params == []

    def test_no_placeholders_with_params_error(self) -> None:
        """Test error when params provided but no placeholders."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT COUNT(*) FROM users",
                query_params=["unused"],
            )
        assert "query_params has 1 items" in str(exc_info.value)
        assert "no $N placeholders" in str(exc_info.value)

    def test_frozen_prevents_modification(self) -> None:
        """Test frozen=True prevents field modification."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT 1",
            query_params=[],
        )
        with pytest.raises(ValidationError):
            config.operation = "insert"  # type: ignore[misc]

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT 1",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)


class TestModelKafkaIOConfig:
    """Tests for ModelKafkaIOConfig model."""

    def test_basic_kafka_config(self) -> None:
        """Test creating a basic Kafka config."""
        config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}"}',
        )
        assert config.handler_type == EnumEffectHandlerType.KAFKA
        assert config.topic == "user-events"
        assert config.payload_template == '{"user_id": "${input.user_id}"}'
        assert config.partition_key_template is None
        assert config.headers == {}
        assert config.timeout_ms == 30000
        assert config.acks == "all"
        assert config.compression == "none"

    def test_full_kafka_config(self) -> None:
        """Test Kafka config with all options."""
        config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}"}',
            partition_key_template="${input.user_id}",
            headers={"X-Correlation-ID": "${env.CORRELATION_ID}"},
            timeout_ms=5000,
            acks="1",
            compression="gzip",
        )
        assert config.partition_key_template == "${input.user_id}"
        assert config.headers == {"X-Correlation-ID": "${env.CORRELATION_ID}"}
        assert config.acks == "1"
        assert config.compression == "gzip"

    def test_acks_values(self) -> None:
        """Test valid acks values."""
        for acks_value in ["0", "1", "all"]:
            config = ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks=acks_value,  # type: ignore[arg-type]
            )
            assert config.acks == acks_value

    def test_compression_values(self) -> None:
        """Test valid compression values."""
        for compression_value in ["none", "gzip", "snappy", "lz4", "zstd"]:
            config = ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                compression=compression_value,  # type: ignore[arg-type]
            )
            assert config.compression == compression_value

    def test_frozen_prevents_modification(self) -> None:
        """Test frozen=True prevents field modification."""
        config = ModelKafkaIOConfig(
            topic="test",
            payload_template="{}",
        )
        with pytest.raises(ValidationError):
            config.topic = "other"  # type: ignore[misc]

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)


class TestModelFilesystemIOConfig:
    """Tests for ModelFilesystemIOConfig model."""

    def test_basic_write_config(self) -> None:
        """Test creating a basic write config."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/output/${input.filename}.json",
            operation="write",
        )
        assert config.handler_type == EnumEffectHandlerType.FILESYSTEM
        assert config.file_path_template == "/data/output/${input.filename}.json"
        assert config.operation == "write"
        assert config.timeout_ms == 30000
        assert config.atomic is True
        assert config.create_dirs is True
        assert config.encoding == "utf-8"
        assert config.mode is None

    def test_all_operations(self) -> None:
        """Test all valid operation types."""
        for op in ["read", "write", "delete", "move", "copy"]:
            config = ModelFilesystemIOConfig(
                file_path_template="/path",
                operation=op,  # type: ignore[arg-type]
            )
            assert config.operation == op

    def test_custom_settings(self) -> None:
        """Test custom settings."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/output.txt",
            operation="write",
            atomic=False,
            create_dirs=False,
            encoding="latin-1",
            mode="0644",
        )
        assert config.atomic is False
        assert config.create_dirs is False
        assert config.encoding == "latin-1"
        assert config.mode == "0644"

    def test_frozen_prevents_modification(self) -> None:
        """Test frozen=True prevents field modification."""
        config = ModelFilesystemIOConfig(
            file_path_template="/path",
            operation="read",
        )
        with pytest.raises(ValidationError):
            config.operation = "write"  # type: ignore[misc]

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFilesystemIOConfig(
                file_path_template="/path",
                operation="read",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)


class TestEffectIOConfigUnion:
    """Tests for discriminated union behavior."""

    def test_http_config_discrimination(self) -> None:
        """Test HTTP config is correctly identified via discriminator."""
        data = {
            "handler_type": "http",
            "url_template": "https://api.example.com",
            "method": "GET",
        }
        # Pydantic should automatically select ModelHttpIOConfig
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EffectIOConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, ModelHttpIOConfig)
        assert config.handler_type == EnumEffectHandlerType.HTTP

    def test_db_config_discrimination(self) -> None:
        """Test DB config is correctly identified via discriminator."""
        data = {
            "handler_type": "db",
            "operation": "select",
            "connection_name": "db",
            "query_template": "SELECT 1",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EffectIOConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, ModelDbIOConfig)
        assert config.handler_type == EnumEffectHandlerType.DB

    def test_kafka_config_discrimination(self) -> None:
        """Test Kafka config is correctly identified via discriminator."""
        data = {
            "handler_type": "kafka",
            "topic": "test-topic",
            "payload_template": "{}",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EffectIOConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, ModelKafkaIOConfig)
        assert config.handler_type == EnumEffectHandlerType.KAFKA

    def test_filesystem_config_discrimination(self) -> None:
        """Test Filesystem config is correctly identified via discriminator."""
        data = {
            "handler_type": "filesystem",
            "file_path_template": "/path/to/file",
            "operation": "read",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EffectIOConfig)
        config = adapter.validate_python(data)
        assert isinstance(config, ModelFilesystemIOConfig)
        assert config.handler_type == EnumEffectHandlerType.FILESYSTEM

    def test_invalid_handler_type(self) -> None:
        """Test invalid handler_type raises error."""
        data = {
            "handler_type": "invalid",
            "url_template": "https://api.example.com",
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(EffectIOConfig)
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)
        # Should fail to match any union member
        error_str = str(exc_info.value)
        assert "handler_type" in error_str or "Unable to extract" in error_str

    def test_union_type_is_correct(self) -> None:
        """Test that EffectIOConfig is a proper union type."""
        # Verify it's a Union by checking if we can create instances of each type
        http = ModelHttpIOConfig(
            url_template="https://example.com", method="GET"
        )
        db = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT 1",
        )
        kafka = ModelKafkaIOConfig(topic="test", payload_template="{}")
        fs = ModelFilesystemIOConfig(file_path_template="/path", operation="read")

        # All should be valid EffectIOConfig instances (in type-checking sense)
        configs: list[EffectIOConfig] = [http, db, kafka, fs]
        assert len(configs) == 4


class TestExportedFromSubcontracts:
    """Test that models are properly exported from subcontracts module."""

    def test_imports_from_subcontracts(self) -> None:
        """Test all models can be imported from subcontracts module."""
        from omnibase_core.models.contracts.subcontracts import (
            EffectIOConfig,
            ModelDbIOConfig,
            ModelFilesystemIOConfig,
            ModelHttpIOConfig,
            ModelKafkaIOConfig,
        )

        # Verify they are the same classes
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            EffectIOConfig as DirectEffectIOConfig,
        )
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelDbIOConfig as DirectModelDbIOConfig,
        )
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelFilesystemIOConfig as DirectModelFilesystemIOConfig,
        )
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelHttpIOConfig as DirectModelHttpIOConfig,
        )
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelKafkaIOConfig as DirectModelKafkaIOConfig,
        )

        assert ModelHttpIOConfig is DirectModelHttpIOConfig
        assert ModelDbIOConfig is DirectModelDbIOConfig
        assert ModelKafkaIOConfig is DirectModelKafkaIOConfig
        assert ModelFilesystemIOConfig is DirectModelFilesystemIOConfig
        assert EffectIOConfig is DirectEffectIOConfig
