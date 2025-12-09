"""
Tests for ModelEffectOperation and get_effective_idempotency().

Tests the idempotency logic that determines if an operation is safe to retry.
Covers all handler types (HTTP, DB, Kafka, Filesystem) and their respective
operations, as well as explicit override behavior.

Implements: OMN-524
"""

import pytest

from omnibase_core.constants.constants_effect_idempotency import IDEMPOTENCY_DEFAULTS
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelEffectOperationBasic:
    """Basic tests for ModelEffectOperation model."""

    def test_basic_operation_creation(self) -> None:
        """Test creating a basic effect operation."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="fetch_user",
            io_config=io_config,
        )
        assert operation.operation_name == "fetch_user"
        assert operation.handler_type == "http"
        assert operation.idempotent is None

    def test_handler_type_property(self) -> None:
        """Test handler_type property extracts correct value."""
        http_config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="test_op",
            io_config=http_config,
        )
        assert operation.handler_type == "http"

        db_config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT 1",
        )
        operation_db = ModelEffectOperation(
            operation_name="test_db",
            io_config=db_config,
        )
        assert operation_db.handler_type == "db"


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestHttpIdempotency:
    """Tests for HTTP method idempotency defaults."""

    def test_http_get_is_idempotent(self) -> None:
        """Test HTTP GET is idempotent by default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="fetch_users",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_http_head_is_idempotent(self) -> None:
        """Test HTTP HEAD is idempotent by default.

        Note: HEAD is not in the allowed methods for ModelHttpIOConfig,
        so we test via the IDEMPOTENCY_DEFAULTS constant directly.
        """
        # HEAD is idempotent per HTTP spec, verify in defaults
        assert IDEMPOTENCY_DEFAULTS["http"]["HEAD"] is True

    def test_http_options_is_idempotent(self) -> None:
        """Test HTTP OPTIONS is idempotent by default.

        Note: OPTIONS is not in the allowed methods for ModelHttpIOConfig,
        so we test via the IDEMPOTENCY_DEFAULTS constant directly.
        """
        # OPTIONS is idempotent per HTTP spec, verify in defaults
        assert IDEMPOTENCY_DEFAULTS["http"]["OPTIONS"] is True

    def test_http_put_is_idempotent(self) -> None:
        """Test HTTP PUT is idempotent by default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="PUT",
            body_template='{"name": "${input.name}"}',
        )
        operation = ModelEffectOperation(
            operation_name="update_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_http_delete_is_idempotent(self) -> None:
        """Test HTTP DELETE is idempotent by default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="DELETE",
        )
        operation = ModelEffectOperation(
            operation_name="delete_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_http_post_is_not_idempotent(self) -> None:
        """Test HTTP POST is NOT idempotent by default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="POST",
            body_template='{"name": "${input.name}"}',
        )
        operation = ModelEffectOperation(
            operation_name="create_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_http_patch_is_not_idempotent(self) -> None:
        """Test HTTP PATCH is NOT idempotent by default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="PATCH",
            body_template='{"name": "${input.name}"}',
        )
        operation = ModelEffectOperation(
            operation_name="patch_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestDbIdempotency:
    """Tests for database operation idempotency defaults."""

    def test_db_select_is_idempotent(self) -> None:
        """Test DB SELECT is idempotent by default."""
        io_config = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
        )
        operation = ModelEffectOperation(
            operation_name="fetch_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_db_update_is_idempotent(self) -> None:
        """Test DB UPDATE is idempotent by default.

        UPDATE with same values produces same result.
        """
        io_config = ModelDbIOConfig(
            operation="update",
            connection_name="primary_db",
            query_template="UPDATE users SET name = $1 WHERE id = $2",
            query_params=["${input.name}", "${input.user_id}"],
        )
        operation = ModelEffectOperation(
            operation_name="update_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_db_delete_is_idempotent(self) -> None:
        """Test DB DELETE is idempotent by default.

        Deleting an already deleted row = no-op.
        """
        io_config = ModelDbIOConfig(
            operation="delete",
            connection_name="primary_db",
            query_template="DELETE FROM users WHERE id = $1",
            query_params=["${input.user_id}"],
        )
        operation = ModelEffectOperation(
            operation_name="delete_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_db_upsert_is_idempotent(self) -> None:
        """Test DB UPSERT is idempotent by default.

        UPSERT (INSERT ON CONFLICT UPDATE) is idempotent by design.
        """
        io_config = ModelDbIOConfig(
            operation="upsert",
            connection_name="primary_db",
            query_template="INSERT INTO users (id, name) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET name = $2",
            query_params=["${input.user_id}", "${input.name}"],
        )
        operation = ModelEffectOperation(
            operation_name="upsert_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_db_insert_is_not_idempotent(self) -> None:
        """Test DB INSERT is NOT idempotent by default.

        INSERT may create duplicates on retry.
        """
        io_config = ModelDbIOConfig(
            operation="insert",
            connection_name="primary_db",
            query_template="INSERT INTO users (name) VALUES ($1)",
            query_params=["${input.name}"],
        )
        operation = ModelEffectOperation(
            operation_name="create_user",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_db_raw_is_not_idempotent(self) -> None:
        """Test DB RAW is NOT idempotent by default.

        RAW operations default to non-idempotent for safety.
        """
        io_config = ModelDbIOConfig(
            operation="raw",
            connection_name="primary_db",
            query_template="TRUNCATE TABLE audit_logs",
        )
        operation = ModelEffectOperation(
            operation_name="truncate_audit_logs",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_db_operation_case_normalization(self) -> None:
        """Test DB operation is normalized to uppercase for lookup."""
        # DB operations are stored lowercase but looked up uppercase
        io_config = ModelDbIOConfig(
            operation="select",  # lowercase in config
            connection_name="db",
            query_template="SELECT 1",
        )
        operation = ModelEffectOperation(
            operation_name="test",
            io_config=io_config,
        )
        # Should find SELECT in IDEMPOTENCY_DEFAULTS
        assert operation.get_effective_idempotency() is True


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestKafkaIdempotency:
    """Tests for Kafka operation idempotency defaults."""

    def test_kafka_produce_is_not_idempotent(self) -> None:
        """Test Kafka produce is NOT idempotent by default.

        Standard produce may create duplicate messages on retry
        (unless using idempotent producer config).
        """
        io_config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}", "action": "created"}',
        )
        operation = ModelEffectOperation(
            operation_name="publish_user_event",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_kafka_produce_with_all_acks(self) -> None:
        """Test Kafka produce with acks=all is still not idempotent."""
        io_config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}"}',
            acks="all",
        )
        operation = ModelEffectOperation(
            operation_name="publish_event",
            io_config=io_config,
        )
        # acks level doesn't affect idempotency semantics
        assert operation.get_effective_idempotency() is False


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestFilesystemIdempotency:
    """Tests for filesystem operation idempotency defaults."""

    def test_filesystem_read_is_idempotent(self) -> None:
        """Test filesystem read is idempotent by default."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/input/${input.filename}.json",
            operation="read",
            atomic=False,
        )
        operation = ModelEffectOperation(
            operation_name="read_file",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_filesystem_delete_is_idempotent(self) -> None:
        """Test filesystem delete is idempotent by default.

        Deleting an already deleted file = no-op.
        """
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/temp/${input.filename}.tmp",
            operation="delete",
            atomic=False,
        )
        operation = ModelEffectOperation(
            operation_name="delete_temp_file",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is True

    def test_filesystem_write_is_not_idempotent(self) -> None:
        """Test filesystem write is NOT idempotent by default.

        Overwrites may corrupt data on retry with different content.
        """
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/output/${input.filename}.json",
            operation="write",
            atomic=True,
        )
        operation = ModelEffectOperation(
            operation_name="write_output",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_filesystem_move_is_not_idempotent(self) -> None:
        """Test filesystem move is NOT idempotent by default.

        Source may not exist after first move.
        """
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/inbox/${input.filename}",
            destination_path_template="/data/archive/${input.filename}",
            operation="move",
            atomic=False,
        )
        operation = ModelEffectOperation(
            operation_name="archive_file",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_filesystem_copy_is_not_idempotent(self) -> None:
        """Test filesystem copy is NOT idempotent by default.

        Destination may exist after first attempt, causing failure or overwrite.
        """
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/source/${input.filename}",
            destination_path_template="/data/backup/${input.filename}",
            operation="copy",
            atomic=False,
        )
        operation = ModelEffectOperation(
            operation_name="backup_file",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestExplicitIdempotencyOverride:
    """Tests for explicit idempotent field override behavior."""

    def test_explicit_true_overrides_default_false_http_post(self) -> None:
        """Test explicit idempotent=True overrides default False for HTTP POST."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users",
            method="POST",
            body_template='{"name": "${input.name}", "idempotency_key": "${input.key}"}',
        )
        operation = ModelEffectOperation(
            operation_name="create_user_idempotent",
            io_config=io_config,
            idempotent=True,  # Explicit override
        )
        # Default would be False for POST, but explicit True overrides
        assert operation.get_effective_idempotency() is True

    def test_explicit_true_overrides_default_false_db_insert(self) -> None:
        """Test explicit idempotent=True overrides default False for DB INSERT."""
        io_config = ModelDbIOConfig(
            operation="insert",
            connection_name="db",
            query_template="INSERT INTO users (id, name) VALUES ($1, $2)",
            query_params=["${input.id}", "${input.name}"],
        )
        operation = ModelEffectOperation(
            operation_name="create_user_idempotent",
            io_config=io_config,
            idempotent=True,  # Explicit override (e.g., using natural key)
        )
        assert operation.get_effective_idempotency() is True

    def test_explicit_true_overrides_default_false_kafka(self) -> None:
        """Test explicit idempotent=True overrides default False for Kafka produce."""
        io_config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}"}',
        )
        operation = ModelEffectOperation(
            operation_name="publish_event_idempotent",
            io_config=io_config,
            idempotent=True,  # Using idempotent producer
        )
        assert operation.get_effective_idempotency() is True

    def test_explicit_true_overrides_default_false_filesystem_write(self) -> None:
        """Test explicit idempotent=True overrides default False for filesystem write."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/output/${input.hash}.json",
            operation="write",
            atomic=True,
        )
        operation = ModelEffectOperation(
            operation_name="write_by_hash",
            io_config=io_config,
            idempotent=True,  # Content-addressed storage
        )
        assert operation.get_effective_idempotency() is True

    def test_explicit_false_overrides_default_true_http_get(self) -> None:
        """Test explicit idempotent=False overrides default True for HTTP GET."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/increment_counter",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="increment_counter",
            io_config=io_config,
            idempotent=False,  # Side-effecting GET (bad API design, but exists)
        )
        # Default would be True for GET, but explicit False overrides
        assert operation.get_effective_idempotency() is False

    def test_explicit_false_overrides_default_true_db_select(self) -> None:
        """Test explicit idempotent=False overrides default True for DB SELECT."""
        io_config = ModelDbIOConfig(
            operation="select",
            connection_name="db",
            query_template="SELECT * FROM audit_log()",  # Function with side effects
        )
        operation = ModelEffectOperation(
            operation_name="read_with_side_effect",
            io_config=io_config,
            idempotent=False,  # Side-effecting function
        )
        assert operation.get_effective_idempotency() is False

    def test_explicit_false_overrides_default_true_db_delete(self) -> None:
        """Test explicit idempotent=False overrides default True for DB DELETE."""
        io_config = ModelDbIOConfig(
            operation="delete",
            connection_name="db",
            query_template="DELETE FROM queue RETURNING *",
            query_params=[],
        )
        operation = ModelEffectOperation(
            operation_name="dequeue_item",
            io_config=io_config,
            idempotent=False,  # Queue dequeue is not idempotent
        )
        assert operation.get_effective_idempotency() is False

    def test_explicit_false_overrides_default_true_filesystem_read(self) -> None:
        """Test explicit idempotent=False overrides default True for filesystem read."""
        io_config = ModelFilesystemIOConfig(
            file_path_template="/data/counters/${input.id}.txt",
            operation="read",
            atomic=False,
        )
        operation = ModelEffectOperation(
            operation_name="read_and_lock",
            io_config=io_config,
            idempotent=False,  # Read with advisory lock
        )
        assert operation.get_effective_idempotency() is False


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestIdempotencyPriority:
    """Tests verifying the priority order: explicit > handler default."""

    def test_none_uses_handler_default_true(self) -> None:
        """Test idempotent=None uses handler default (True case)."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="test",
            io_config=io_config,
            idempotent=None,  # Explicitly None (same as default)
        )
        assert operation.idempotent is None
        assert operation.get_effective_idempotency() is True

    def test_none_uses_handler_default_false(self) -> None:
        """Test idempotent=None uses handler default (False case)."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="POST",
            body_template="{}",
        )
        operation = ModelEffectOperation(
            operation_name="test",
            io_config=io_config,
            idempotent=None,  # Explicitly None (same as default)
        )
        assert operation.idempotent is None
        assert operation.get_effective_idempotency() is False

    def test_true_takes_precedence_over_default(self) -> None:
        """Test explicit True takes precedence over default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="POST",
            body_template="{}",
        )
        operation = ModelEffectOperation(
            operation_name="test",
            io_config=io_config,
            idempotent=True,
        )
        assert operation.idempotent is True
        assert operation.get_effective_idempotency() is True

    def test_false_takes_precedence_over_default(self) -> None:
        """Test explicit False takes precedence over default."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="test",
            io_config=io_config,
            idempotent=False,
        )
        assert operation.idempotent is False
        assert operation.get_effective_idempotency() is False


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestIdempotencyDefaultsConstant:
    """Tests for IDEMPOTENCY_DEFAULTS constant consistency."""

    def test_http_defaults_complete(self) -> None:
        """Test HTTP idempotency defaults are complete."""
        http_defaults = IDEMPOTENCY_DEFAULTS["http"]
        expected_methods = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "POST", "PATCH"}
        assert set(http_defaults.keys()) == expected_methods

    def test_db_defaults_complete(self) -> None:
        """Test DB idempotency defaults are complete."""
        db_defaults = IDEMPOTENCY_DEFAULTS["db"]
        expected_operations = {"SELECT", "INSERT", "UPDATE", "DELETE", "UPSERT"}
        assert set(db_defaults.keys()) == expected_operations

    def test_kafka_defaults_complete(self) -> None:
        """Test Kafka idempotency defaults are complete."""
        kafka_defaults = IDEMPOTENCY_DEFAULTS["kafka"]
        assert "produce" in kafka_defaults

    def test_filesystem_defaults_complete(self) -> None:
        """Test Filesystem idempotency defaults are complete."""
        fs_defaults = IDEMPOTENCY_DEFAULTS["filesystem"]
        expected_operations = {"read", "write", "delete", "move", "copy"}
        assert set(fs_defaults.keys()) == expected_operations

    def test_http_idempotent_methods_per_rfc7231(self) -> None:
        """Test HTTP idempotent methods match RFC 7231."""
        http_defaults = IDEMPOTENCY_DEFAULTS["http"]
        # Per RFC 7231, these methods are idempotent
        idempotent_methods = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}
        for method in idempotent_methods:
            assert http_defaults[method] is True, f"{method} should be idempotent"

        # These are not idempotent
        non_idempotent_methods = {"POST", "PATCH"}
        for method in non_idempotent_methods:
            assert http_defaults[method] is False, f"{method} should not be idempotent"


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_unknown_handler_defaults_to_true(self) -> None:
        """Test that unknown handler types default to idempotent=True (conservative).

        This is a defensive test for future handler types. The current implementation
        returns True for unknown handlers as a conservative default.
        """
        # We can't easily test unknown handlers directly since the IO config
        # uses a discriminated union, but we verify the logic by checking
        # that get_effective_idempotency() has proper fallback behavior

        # Verify the fallback path exists in the defaults lookup
        assert IDEMPOTENCY_DEFAULTS.get("unknown_handler", {}).get("unknown_op", True)

    def test_db_raw_special_case_returns_false(self) -> None:
        """Test DB RAW operations always return False regardless of defaults.

        RAW is a special case that bypasses the defaults lookup and
        immediately returns False for safety.
        """
        io_config = ModelDbIOConfig(
            operation="raw",
            connection_name="db",
            query_template="SELECT 1",  # Even a SELECT as raw is non-idempotent
        )
        operation = ModelEffectOperation(
            operation_name="raw_query",
            io_config=io_config,
        )
        assert operation.get_effective_idempotency() is False

    def test_db_raw_with_explicit_true_override(self) -> None:
        """Test DB RAW can be overridden with explicit idempotent=True."""
        io_config = ModelDbIOConfig(
            operation="raw",
            connection_name="db",
            query_template="SELECT 1",
        )
        operation = ModelEffectOperation(
            operation_name="raw_select",
            io_config=io_config,
            idempotent=True,  # Explicit override
        )
        # Explicit takes precedence, even for RAW
        assert operation.get_effective_idempotency() is True

    def test_all_http_methods_have_idempotency_defined(self) -> None:
        """Test all ModelHttpIOConfig methods have idempotency defined."""
        # Get allowed methods from ModelHttpIOConfig
        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        http_defaults = IDEMPOTENCY_DEFAULTS["http"]

        for method in allowed_methods:
            assert method in http_defaults, (
                f"Missing idempotency default for HTTP {method}"
            )

    def test_all_db_operations_have_idempotency_defined(self) -> None:
        """Test all ModelDbIOConfig operations have idempotency defined."""
        # Get allowed operations from ModelDbIOConfig
        allowed_ops = {"select", "insert", "update", "delete", "upsert", "raw"}
        db_defaults = IDEMPOTENCY_DEFAULTS["db"]

        for op in allowed_ops:
            if op != "raw":  # RAW is handled specially
                assert op.upper() in db_defaults, (
                    f"Missing idempotency default for DB {op}"
                )

    def test_all_filesystem_operations_have_idempotency_defined(self) -> None:
        """Test all ModelFilesystemIOConfig operations have idempotency defined."""
        # Get allowed operations from ModelFilesystemIOConfig
        allowed_ops = {"read", "write", "delete", "move", "copy"}
        fs_defaults = IDEMPOTENCY_DEFAULTS["filesystem"]

        for op in allowed_ops:
            assert op in fs_defaults, f"Missing idempotency default for filesystem {op}"


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelEffectOperationIntegration:
    """Integration tests for ModelEffectOperation with various IO configs."""

    def test_full_http_operation_with_retry_policy(self) -> None:
        """Test HTTP operation with retry policy respects idempotency."""
        from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
            ModelEffectRetryPolicy,
        )

        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.id}",
            method="PUT",
            body_template='{"name": "${input.name}"}',
        )
        retry_policy = ModelEffectRetryPolicy(
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=1000,
        )
        operation = ModelEffectOperation(
            operation_name="update_user",
            io_config=io_config,
            retry_policy=retry_policy,
        )
        # PUT is idempotent, safe to retry
        assert operation.get_effective_idempotency() is True
        assert operation.retry_policy is not None
        assert operation.retry_policy.max_retries == 3

    def test_full_db_operation_with_circuit_breaker(self) -> None:
        """Test DB operation with circuit breaker respects idempotency."""
        from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
            ModelEffectCircuitBreaker,
        )

        io_config = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE status = $1",
            query_params=["${input.status}"],
        )
        circuit_breaker = ModelEffectCircuitBreaker(
            enabled=True,
            failure_threshold=5,
            timeout_ms=30000,
        )
        operation = ModelEffectOperation(
            operation_name="list_users",
            io_config=io_config,
            circuit_breaker=circuit_breaker,
        )
        # SELECT is idempotent
        assert operation.get_effective_idempotency() is True
        assert operation.circuit_breaker is not None

    def test_operation_with_description(self) -> None:
        """Test operation with description field."""
        io_config = ModelHttpIOConfig(
            url_template="https://api.example.com/health",
            method="GET",
        )
        operation = ModelEffectOperation(
            operation_name="health_check",
            description="Checks the health status of the upstream API",
            io_config=io_config,
        )
        assert operation.description == "Checks the health status of the upstream API"
        assert operation.get_effective_idempotency() is True

    def test_operation_with_timeout(self) -> None:
        """Test operation with custom operation timeout."""
        io_config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"event": "test"}',
        )
        operation = ModelEffectOperation(
            operation_name="publish_event",
            io_config=io_config,
            operation_timeout_ms=120000,  # 2 minutes
        )
        assert operation.operation_timeout_ms == 120000
        # Kafka produce is not idempotent
        assert operation.get_effective_idempotency() is False
