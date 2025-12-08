"""
Tests for Effect IO Configuration Models.

Tests discriminated union behavior, validators, frozen model behavior,
and extra="forbid" configuration for all IO config models.
"""

import warnings

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


@pytest.mark.unit
@pytest.mark.timeout(60)
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
        """Test timeout_ms bounds validation.

        Timeout bounds: 1000ms (1 second) minimum for realistic production I/O,
        600000ms (10 minutes) maximum timeout.
        """
        # Valid minimum (1000ms = 1 second)
        config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
            timeout_ms=1000,
        )
        assert config.timeout_ms == 1000

        # Valid maximum (600000ms = 10 minutes)
        config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
            timeout_ms=600000,
        )
        assert config.timeout_ms == 600000

        # Below minimum (999ms < 1000ms)
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                timeout_ms=999,
            )
        assert "timeout_ms" in str(exc_info.value)

        # Above maximum (600001ms > 600000ms)
        with pytest.raises(ValidationError) as exc_info:
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                timeout_ms=600001,
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

    def test_verify_ssl_false_emits_security_warning(self) -> None:
        """Test that verify_ssl=False emits a SecurityWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                verify_ssl=False,
            )
            assert config.verify_ssl is False
            # Check that a SecurityWarning was emitted
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "verify_ssl=False disables SSL certificate validation" in str(
                w[0].message
            )
            assert "insecure for production use" in str(w[0].message)

    def test_verify_ssl_true_no_warning(self) -> None:
        """Test that verify_ssl=True (default) does not emit a warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
                verify_ssl=True,
            )
            assert config.verify_ssl is True
            # No warnings should be emitted
            security_warnings = [
                warning for warning in w if issubclass(warning.category, UserWarning)
            ]
            assert len(security_warnings) == 0


@pytest.mark.unit
@pytest.mark.timeout(60)
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

    def test_sequential_placeholders_valid(self) -> None:
        """Test that sequential placeholders $1, $2, $3 are valid."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM users WHERE id = $1 AND status = $2 AND role = $3",
            query_params=["${input.id}", "${input.status}", "${input.role}"],
        )
        assert len(config.query_params) == 3

    def test_non_sequential_placeholders_error_missing_middle(self) -> None:
        """Test error when placeholders skip numbers (e.g., $1, $3 missing $2)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT * FROM users WHERE id = $1 AND role = $3",
                query_params=["${input.id}", "${input.status}", "${input.role}"],
            )
        assert "Placeholders must be sequential" in str(exc_info.value)
        assert "$2" in str(exc_info.value)

    def test_non_sequential_placeholders_error_missing_first(self) -> None:
        """Test error when placeholders start from $2 (missing $1)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT * FROM users WHERE status = $2",
                query_params=["${input.id}", "${input.status}"],
            )
        assert "Placeholders must be sequential" in str(exc_info.value)
        assert "$1" in str(exc_info.value)

    def test_non_sequential_placeholders_error_large_gap(self) -> None:
        """Test error when placeholders have large gap (e.g., $1, $5)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT * FROM users WHERE id = $1 AND role = $5",
                query_params=["a", "b", "c", "d", "e"],
            )
        assert "Placeholders must be sequential" in str(exc_info.value)
        # Should mention missing $2, $3, $4
        error_str = str(exc_info.value)
        assert "$2" in error_str or "2" in error_str

    def test_duplicate_placeholders_valid(self) -> None:
        """Test that using same placeholder multiple times is valid."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM users WHERE id = $1 OR backup_id = $1",
            query_params=["${input.id}"],
        )
        assert len(config.query_params) == 1

    def test_read_only_with_select_valid(self) -> None:
        """Test read_only=True is valid with select operation."""
        config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM users",
            query_params=[],
            read_only=True,
        )
        assert config.read_only is True
        assert config.operation == "select"

    def test_read_only_with_insert_error(self) -> None:
        """Test read_only=True raises error with insert operation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="insert",
                connection_name="db",
                query_template="INSERT INTO users (name) VALUES ($1)",
                query_params=["${input.name}"],
                read_only=True,
            )
        assert "read_only=True only allows 'select' operation" in str(exc_info.value)
        assert "'insert'" in str(exc_info.value)

    def test_read_only_with_update_error(self) -> None:
        """Test read_only=True raises error with update operation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="update",
                connection_name="db",
                query_template="UPDATE users SET name = $1 WHERE id = $2",
                query_params=["${input.name}", "${input.id}"],
                read_only=True,
            )
        assert "read_only=True only allows 'select' operation" in str(exc_info.value)
        assert "'update'" in str(exc_info.value)

    def test_read_only_with_delete_error(self) -> None:
        """Test read_only=True raises error with delete operation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="delete",
                connection_name="db",
                query_template="DELETE FROM users WHERE id = $1",
                query_params=["${input.id}"],
                read_only=True,
            )
        assert "read_only=True only allows 'select' operation" in str(exc_info.value)
        assert "'delete'" in str(exc_info.value)

    def test_read_only_with_upsert_error(self) -> None:
        """Test read_only=True raises error with upsert operation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="upsert",
                connection_name="db",
                query_template="INSERT INTO users (id, name) VALUES ($1, $2) ON CONFLICT DO UPDATE",
                query_params=["${input.id}", "${input.name}"],
                read_only=True,
            )
        assert "read_only=True only allows 'select' operation" in str(exc_info.value)
        assert "'upsert'" in str(exc_info.value)

    def test_read_only_with_raw_error(self) -> None:
        """Test read_only=True raises error with raw operation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDbIOConfig(
                operation="raw",
                connection_name="db",
                query_template="TRUNCATE TABLE users",
                query_params=[],
                read_only=True,
            )
        assert "read_only=True only allows 'select' operation" in str(exc_info.value)
        assert "'raw'" in str(exc_info.value)

    def test_read_only_false_allows_all_operations(self) -> None:
        """Test read_only=False (default) allows all operations."""
        for operation in ["select", "insert", "update", "delete", "upsert"]:
            config = ModelDbIOConfig(
                operation=operation,  # type: ignore[arg-type]
                connection_name="db",
                query_template="SELECT 1"
                if operation == "select"
                else "UPDATE t SET x = 1",
                query_params=[],
                read_only=False,
            )
            assert config.read_only is False
            assert config.operation == operation


@pytest.mark.unit
@pytest.mark.timeout(60)
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
        # Test acks=1 and acks=all (no opt-in required)
        for acks_value in ["1", "all"]:
            config = ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks=acks_value,  # type: ignore[arg-type]
            )
            assert config.acks == acks_value

        # Test acks=0 requires explicit opt-in
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            config = ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="0",
                acks_zero_acknowledged=True,
            )
            assert config.acks == "0"
            assert config.acks_zero_acknowledged is True

    def test_acks_zero_requires_opt_in(self) -> None:
        """Test that acks=0 requires explicit opt-in via acks_zero_acknowledged."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="0",  # No acks_zero_acknowledged=True
            )
        assert "acks_zero_acknowledged" in str(exc_info.value)
        assert "explicit opt-in" in str(exc_info.value)

    def test_acks_zero_emits_warning(self) -> None:
        """Test that acks=0 emits a warning even with opt-in."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="0",
                acks_zero_acknowledged=True,
            )
            # Check that warning was emitted
            assert len(w) == 1
            assert "no delivery guarantees" in str(w[0].message)
            assert issubclass(w[0].category, UserWarning)

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

    def test_acks_zero_with_acknowledged_true_valid(self) -> None:
        """Test acks='0' with acks_zero_acknowledged=True is valid."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            config = ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="0",
                acks_zero_acknowledged=True,
            )
            assert config.acks == "0"
            assert config.acks_zero_acknowledged is True

    def test_acks_zero_with_acknowledged_false_valid(self) -> None:
        """Test acks='0' with acks_zero_acknowledged=False raises error (opt-in required)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="0",
                acks_zero_acknowledged=False,
            )
        assert "acks_zero_acknowledged" in str(exc_info.value)
        assert "explicit opt-in" in str(exc_info.value)

    def test_acks_one_with_acknowledged_true_invalid(self) -> None:
        """Test acks='1' with acks_zero_acknowledged=True is invalid."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="1",
                acks_zero_acknowledged=True,
            )
        assert "acks_zero_acknowledged=True is only valid when acks='0'" in str(
            exc_info.value
        )
        assert "acks='1'" in str(exc_info.value)

    def test_acks_all_with_acknowledged_true_invalid(self) -> None:
        """Test acks='all' with acks_zero_acknowledged=True is invalid."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
                acks="all",
                acks_zero_acknowledged=True,
            )
        assert "acks_zero_acknowledged=True is only valid when acks='0'" in str(
            exc_info.value
        )
        assert "acks='all'" in str(exc_info.value)

    def test_acks_one_with_acknowledged_false_valid(self) -> None:
        """Test acks='1' with acks_zero_acknowledged=False is valid (default case)."""
        config = ModelKafkaIOConfig(
            topic="test",
            payload_template="{}",
            acks="1",
            acks_zero_acknowledged=False,
        )
        assert config.acks == "1"
        assert config.acks_zero_acknowledged is False

    def test_acks_all_with_acknowledged_false_valid(self) -> None:
        """Test acks='all' with acks_zero_acknowledged=False is valid (default case)."""
        config = ModelKafkaIOConfig(
            topic="test",
            payload_template="{}",
            acks="all",
            acks_zero_acknowledged=False,
        )
        assert config.acks == "all"
        assert config.acks_zero_acknowledged is False


@pytest.mark.unit
@pytest.mark.timeout(60)
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
            # atomic=False for non-write operations (atomic=True only valid for write)
            # destination_path_template required for move/copy operations
            config = ModelFilesystemIOConfig(
                file_path_template="/path",
                operation=op,  # type: ignore[arg-type]
                atomic=(op == "write"),  # Only write supports atomic=True
                destination_path_template="/dest" if op in ("move", "copy") else None,
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
            atomic=False,  # atomic=True only valid for write operations
        )
        with pytest.raises(ValidationError):
            config.operation = "write"  # type: ignore[misc]

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFilesystemIOConfig(
                file_path_template="/path",
                operation="read",
                atomic=False,  # atomic=True only valid for write operations
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)

    def test_atomic_true_only_valid_for_write(self) -> None:
        """Test atomic=True raises error for non-write operations."""
        non_write_ops = ["read", "delete", "move", "copy"]
        for op in non_write_ops:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelFilesystemIOConfig(
                    file_path_template="/path",
                    operation=op,  # type: ignore[arg-type]
                    atomic=True,
                )
            assert (
                f"atomic=True is only valid for 'write' operations, not '{op}'"
                in str(exc_info.value)
            )

    def test_atomic_true_allowed_for_write(self) -> None:
        """Test atomic=True is allowed for write operations."""
        config = ModelFilesystemIOConfig(
            file_path_template="/path",
            operation="write",
            atomic=True,
        )
        assert config.atomic is True
        assert config.operation == "write"

    def test_atomic_false_allowed_for_all_operations(self) -> None:
        """Test atomic=False is allowed for all operations."""
        for op in ["read", "write", "delete", "move", "copy"]:
            config = ModelFilesystemIOConfig(
                file_path_template="/path",
                operation=op,  # type: ignore[arg-type]
                atomic=False,
                destination_path_template="/dest" if op in ("move", "copy") else None,
            )
            assert config.atomic is False
            assert config.operation == op

    def test_read_without_destination_valid(self) -> None:
        """Test read operation without destination_path_template is valid."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/input.json",
            operation="read",
            atomic=False,
        )
        assert config.operation == "read"
        assert config.destination_path_template is None

    def test_write_without_destination_valid(self) -> None:
        """Test write operation without destination_path_template is valid."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/output.json",
            operation="write",
            atomic=True,
        )
        assert config.operation == "write"
        assert config.destination_path_template is None

    def test_delete_without_destination_valid(self) -> None:
        """Test delete operation without destination_path_template is valid."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/to_delete.json",
            operation="delete",
            atomic=False,
        )
        assert config.operation == "delete"
        assert config.destination_path_template is None

    def test_move_without_destination_invalid(self) -> None:
        """Test move operation without destination_path_template raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFilesystemIOConfig(
                file_path_template="/data/source.json",
                operation="move",
                atomic=False,
            )
        assert "destination_path_template is required for 'move' operations" in str(
            exc_info.value
        )

    def test_copy_without_destination_invalid(self) -> None:
        """Test copy operation without destination_path_template raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFilesystemIOConfig(
                file_path_template="/data/source.json",
                operation="copy",
                atomic=False,
            )
        assert "destination_path_template is required for 'copy' operations" in str(
            exc_info.value
        )

    def test_move_with_destination_valid(self) -> None:
        """Test move operation with destination_path_template is valid."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/inbox/${input.filename}",
            destination_path_template="/data/archive/${input.date}/${input.filename}",
            operation="move",
            atomic=False,
            create_dirs=True,
        )
        assert config.operation == "move"
        assert config.file_path_template == "/data/inbox/${input.filename}"
        assert (
            config.destination_path_template
            == "/data/archive/${input.date}/${input.filename}"
        )

    def test_copy_with_destination_valid(self) -> None:
        """Test copy operation with destination_path_template is valid."""
        config = ModelFilesystemIOConfig(
            file_path_template="/data/source/${input.filename}",
            destination_path_template="/data/backup/${input.filename}",
            operation="copy",
            atomic=False,
            create_dirs=True,
        )
        assert config.operation == "copy"
        assert config.file_path_template == "/data/source/${input.filename}"
        assert config.destination_path_template == "/data/backup/${input.filename}"


@pytest.mark.unit
@pytest.mark.timeout(60)
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
            "atomic": False,  # atomic=True only valid for write operations
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
        http = ModelHttpIOConfig(url_template="https://example.com", method="GET")
        db = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT 1",
        )
        kafka = ModelKafkaIOConfig(topic="test", payload_template="{}")
        fs = ModelFilesystemIOConfig(
            file_path_template="/path",
            operation="read",
            atomic=False,  # atomic=True only valid for write operations
        )

        # All should be valid EffectIOConfig instances (in type-checking sense)
        configs: list[EffectIOConfig] = [http, db, kafka, fs]
        assert len(configs) == 4


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestEffectIOConfigDiscriminatedUnionIntegration:
    """
    Integration tests for EffectIOConfig discriminated union behavior.

    These tests verify that Pydantic correctly discriminates between
    ModelHttpIOConfig, ModelDbIOConfig, ModelKafkaIOConfig, and
    ModelFilesystemIOConfig based on the handler_type field.
    """

    def test_http_config_discriminated_from_dict(self) -> None:
        """Test HTTP config is correctly discriminated from dict data."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "http",
            "url_template": "https://api.example.com/users",
            "method": "GET",
        }
        config = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(config, ModelHttpIOConfig)
        assert config.handler_type == EnumEffectHandlerType.HTTP
        assert config.url_template == "https://api.example.com/users"
        assert config.method == "GET"

    def test_db_config_discriminated_from_dict(self) -> None:
        """Test DB config is correctly discriminated from dict data."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "db",
            "operation": "select",
            "connection_name": "primary_db",
            "query_template": "SELECT * FROM users WHERE id = $1",
            "query_params": ["user_123"],
        }
        config = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(config, ModelDbIOConfig)
        assert config.handler_type == EnumEffectHandlerType.DB
        assert config.operation == "select"
        assert config.connection_name == "primary_db"

    def test_kafka_config_discriminated_from_dict(self) -> None:
        """Test Kafka config is correctly discriminated from dict data."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "kafka",
            "topic": "user-events",
            "payload_template": '{"user_id": "${input.user_id}"}',
        }
        config = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(config, ModelKafkaIOConfig)
        assert config.handler_type == EnumEffectHandlerType.KAFKA
        assert config.topic == "user-events"

    def test_filesystem_config_discriminated_from_dict(self) -> None:
        """Test Filesystem config is correctly discriminated from dict data."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "filesystem",
            "file_path_template": "/data/output/${input.filename}.json",
            "operation": "write",
        }
        config = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(config, ModelFilesystemIOConfig)
        assert config.handler_type == EnumEffectHandlerType.FILESYSTEM
        assert config.operation == "write"

    def test_invalid_handler_type_rejected(self) -> None:
        """Test invalid handler_type values are rejected."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "invalid_type",
            "url_template": "https://api.example.com",
            "method": "GET",
        }
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(EffectIOConfig).validate_python(data)
        # Pydantic should report that no union member matched
        error_str = str(exc_info.value)
        assert "handler_type" in error_str or "Unable to extract" in error_str

    def test_uppercase_handler_type_rejected(self) -> None:
        """Test uppercase handler_type values are rejected (case-sensitive enum)."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": "HTTP",  # Should be lowercase "http"
            "url_template": "https://api.example.com",
            "method": "GET",
        }
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(EffectIOConfig).validate_python(data)
        error_str = str(exc_info.value)
        assert "handler_type" in error_str or "Unable to extract" in error_str

    def test_missing_handler_type_rejected(self) -> None:
        """Test missing handler_type field is rejected."""
        from pydantic import TypeAdapter

        data = {
            "url_template": "https://api.example.com",
            "method": "GET",
        }
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(EffectIOConfig).validate_python(data)
        # Should fail because discriminator field is missing
        error_str = str(exc_info.value)
        assert "handler_type" in error_str or "Unable to extract" in error_str

    def test_round_trip_http_serialization(self) -> None:
        """Test HTTP config round-trip serialization/deserialization."""
        from pydantic import TypeAdapter

        original = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="POST",
            body_template='{"name": "${input.name}"}',
            headers={"Content-Type": "application/json"},
            timeout_ms=5000,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["handler_type"] == "http"
        assert data["url_template"] == "https://api.example.com/users/${input.user_id}"

        # Deserialize back via union type adapter
        restored = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(restored, ModelHttpIOConfig)
        assert restored.handler_type == original.handler_type
        assert restored.url_template == original.url_template
        assert restored.method == original.method
        assert restored.body_template == original.body_template

    def test_round_trip_db_serialization(self) -> None:
        """Test DB config round-trip serialization/deserialization."""
        from pydantic import TypeAdapter

        original = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
            read_only=True,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["handler_type"] == "db"

        # Deserialize back via union type adapter
        restored = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(restored, ModelDbIOConfig)
        assert restored.operation == original.operation
        assert restored.query_params == original.query_params

    def test_round_trip_kafka_serialization(self) -> None:
        """Test Kafka config round-trip serialization/deserialization."""
        from pydantic import TypeAdapter

        original = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}"}',
            partition_key_template="${input.user_id}",
            acks="all",
            compression="gzip",
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["handler_type"] == "kafka"

        # Deserialize back via union type adapter
        restored = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(restored, ModelKafkaIOConfig)
        assert restored.topic == original.topic
        assert restored.acks == original.acks
        assert restored.compression == original.compression

    def test_round_trip_filesystem_serialization(self) -> None:
        """Test Filesystem config round-trip serialization/deserialization."""
        from pydantic import TypeAdapter

        original = ModelFilesystemIOConfig(
            file_path_template="/data/output/${input.date}/${input.filename}.json",
            operation="write",
            atomic=True,
            create_dirs=True,
            encoding="utf-8",
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["handler_type"] == "filesystem"

        # Deserialize back via union type adapter
        restored = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(restored, ModelFilesystemIOConfig)
        assert restored.file_path_template == original.file_path_template
        assert restored.operation == original.operation

    def test_json_round_trip_all_types(self) -> None:
        """Test JSON serialization round-trip for all config types."""
        from pydantic import TypeAdapter

        configs = [
            ModelHttpIOConfig(
                url_template="https://api.example.com",
                method="GET",
            ),
            ModelDbIOConfig(
                operation="select",
                connection_name="db",
                query_template="SELECT 1",
            ),
            ModelKafkaIOConfig(
                topic="test",
                payload_template="{}",
            ),
            ModelFilesystemIOConfig(
                file_path_template="/path/to/file",
                operation="read",
                atomic=False,  # atomic=True is only valid for write operations
            ),
        ]

        adapter = TypeAdapter(EffectIOConfig)

        for original in configs:
            # Serialize to JSON string
            json_str = original.model_dump_json()

            # Deserialize from JSON
            restored = adapter.validate_json(json_str)

            # Verify type is preserved
            assert type(restored) is type(original)
            assert restored.handler_type == original.handler_type

    def test_enum_handler_type_directly(self) -> None:
        """Test using enum value directly in data dict."""
        from pydantic import TypeAdapter

        data = {
            "handler_type": EnumEffectHandlerType.HTTP,
            "url_template": "https://api.example.com",
            "method": "GET",
        }
        config = TypeAdapter(EffectIOConfig).validate_python(data)
        assert isinstance(config, ModelHttpIOConfig)
        assert config.handler_type == EnumEffectHandlerType.HTTP

    def test_mismatched_fields_for_handler_type_rejected(self) -> None:
        """Test that providing fields from wrong config type causes validation error."""
        from pydantic import TypeAdapter

        # HTTP handler_type but with DB-specific fields
        data = {
            "handler_type": "http",
            "operation": "select",  # DB-specific field
            "connection_name": "db",  # DB-specific field
            "query_template": "SELECT 1",  # DB-specific field
        }
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(EffectIOConfig).validate_python(data)
        # Should fail because required HTTP fields are missing
        error_str = str(exc_info.value)
        assert "url_template" in error_str or "method" in error_str

    def test_all_handler_types_have_distinct_discriminator(self) -> None:
        """Test that all handler types produce distinct discriminator values."""
        configs = [
            ModelHttpIOConfig(url_template="https://example.com", method="GET"),
            ModelDbIOConfig(
                operation="select", connection_name="db", query_template="SELECT 1"
            ),
            ModelKafkaIOConfig(topic="test", payload_template="{}"),
            ModelFilesystemIOConfig(
                file_path_template="/path",
                operation="read",
                atomic=False,  # atomic=True is only valid for write operations
            ),
        ]

        handler_types = [config.handler_type for config in configs]
        serialized_types = [config.model_dump()["handler_type"] for config in configs]

        # All handler types should be unique
        assert len(set(handler_types)) == 4
        assert len(set(serialized_types)) == 4

        # Serialized values should be lowercase strings
        assert set(serialized_types) == {"http", "db", "kafka", "filesystem"}


@pytest.mark.unit
@pytest.mark.timeout(60)
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
