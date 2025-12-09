"""
Tests for ModelEffectSubcontract validators.

Tests the 4 critical validators in ModelEffectSubcontract:
1. validate_transaction_scope - Transaction only for DB-only operations with same connection
2. validate_idempotency_retry_interaction - Cannot retry non-idempotent operations
3. validate_select_retry_in_transaction - Cannot retry SELECT in repeatable_read/serializable transactions
4. validate_no_raw_in_transaction - No raw DB operations in transactions

Implements: OMN-524, OMN-525
"""

import pytest

from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelDbIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_effect_transaction_config import (
    ModelEffectTransactionConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Helper factories for creating test objects
# =============================================================================


def make_db_operation(
    name: str,
    connection_name: str = "primary_db",
    operation: str = "select",
    query_template: str = "SELECT 1",
    query_params: list[str] | None = None,
    idempotent: bool | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectOperation:
    """Create a DB operation for testing."""
    return ModelEffectOperation(
        operation_name=name,
        io_config=ModelDbIOConfig(
            operation=operation,  # type: ignore[arg-type]
            connection_name=connection_name,
            query_template=query_template,
            query_params=query_params or [],
        ),
        idempotent=idempotent,
        retry_policy=retry_policy,
    )


def make_http_operation(
    name: str,
    method: str = "GET",
    url_template: str = "https://api.example.com",
    body_template: str | None = None,
    idempotent: bool | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectOperation:
    """Create an HTTP operation for testing."""
    return ModelEffectOperation(
        operation_name=name,
        io_config=ModelHttpIOConfig(
            url_template=url_template,
            method=method,  # type: ignore[arg-type]
            body_template=body_template,
        ),
        idempotent=idempotent,
        retry_policy=retry_policy,
    )


def make_kafka_operation(
    name: str,
    topic: str = "test-topic",
    payload_template: str = "{}",
    idempotent: bool | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectOperation:
    """Create a Kafka operation for testing."""
    return ModelEffectOperation(
        operation_name=name,
        io_config=ModelKafkaIOConfig(
            topic=topic,
            payload_template=payload_template,
        ),
        idempotent=idempotent,
        retry_policy=retry_policy,
    )


def make_subcontract(
    operations: list[ModelEffectOperation],
    transaction_enabled: bool = False,
    isolation_level: str = "read_committed",
    retry_enabled: bool = True,
    max_retries: int = 3,
) -> ModelEffectSubcontract:
    """Create a subcontract for testing."""
    return ModelEffectSubcontract(
        subcontract_name="test_subcontract",
        operations=operations,
        transaction=ModelEffectTransactionConfig(
            enabled=transaction_enabled,
            isolation_level=isolation_level,  # type: ignore[arg-type]
        ),
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=retry_enabled,
            max_retries=max_retries,
        ),
    )


# =============================================================================
# Test validate_transaction_scope
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestValidateTransactionScope:
    """Tests for validate_transaction_scope validator.

    RULE: Transactions only make sense when:
    1. All operations are DB operations
    2. All operations use the same connection_name
    """

    def test_db_only_same_connection_transaction_passes(self) -> None:
        """Valid: DB-only operations with same connection and transaction enabled."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
            make_db_operation(
                "update_user", "primary_db", "update", "UPDATE users SET x = 1"
            ),
            make_db_operation(
                "insert_audit",
                "primary_db",
                "insert",
                "INSERT INTO audit VALUES ($1)",
                ["${input.msg}"],
                idempotent=True,  # Mark as idempotent to pass retry validation
            ),
        ]

        # Should not raise - all DB operations with same connection
        # Retry is disabled to avoid idempotency validation issues
        subcontract = make_subcontract(
            operations, transaction_enabled=True, retry_enabled=False
        )
        assert subcontract.transaction.enabled is True
        assert len(subcontract.operations) == 3

    def test_transaction_disabled_no_validation(self) -> None:
        """Valid: Transaction disabled bypasses all transaction validation."""
        # Mix HTTP and DB - this would fail if transaction was enabled
        operations = [
            make_http_operation("fetch_data"),
            make_db_operation(
                "store_data",
                "primary_db",
                "insert",
                "INSERT INTO t VALUES ($1)",
                ["${input.v}"],
                idempotent=True,  # Mark as idempotent to pass retry validation
            ),
        ]

        # Should not raise - transaction disabled means no validation
        # Retry disabled to avoid idempotency validation issues
        subcontract = make_subcontract(
            operations, transaction_enabled=False, retry_enabled=False
        )
        assert subcontract.transaction.enabled is False

    def test_mixed_http_db_operations_with_transaction_raises(self) -> None:
        """Invalid: Mixed HTTP+DB operations with transaction enabled."""
        operations = [
            make_http_operation("fetch_user"),
            make_db_operation(
                "store_user",
                "primary_db",
                "insert",
                "INSERT INTO users VALUES ($1)",
                ["${input.id}"],
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, transaction_enabled=True)

        error_msg = str(exc_info.value)
        assert "Transaction enabled but found non-DB operations" in error_msg
        assert "fetch_user" in error_msg
        assert "Transactions only supported for DB handler type" in error_msg

    def test_mixed_kafka_db_operations_with_transaction_raises(self) -> None:
        """Invalid: Mixed Kafka+DB operations with transaction enabled."""
        operations = [
            make_db_operation("select_data", "primary_db", "select"),
            make_kafka_operation("publish_event"),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, transaction_enabled=True)

        error_msg = str(exc_info.value)
        assert "Transaction enabled but found non-DB operations" in error_msg
        assert "publish_event" in error_msg

    def test_db_operations_different_connections_with_transaction_raises(self) -> None:
        """Invalid: DB operations with different connections + transaction enabled."""
        operations = [
            make_db_operation("select_from_primary", "primary_db", "select"),
            make_db_operation("select_from_replica", "replica_db", "select"),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, transaction_enabled=True)

        error_msg = str(exc_info.value)
        assert "different connections" in error_msg
        assert "primary_db" in error_msg or "replica_db" in error_msg
        assert (
            "All DB operations in a transaction must use the same connection"
            in error_msg
        )

    def test_three_different_connections_with_transaction_raises(self) -> None:
        """Invalid: Three DB operations with three different connections."""
        operations = [
            make_db_operation("op1", "conn1", "select"),
            make_db_operation("op2", "conn2", "select"),
            make_db_operation("op3", "conn3", "select"),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, transaction_enabled=True)

        error_msg = str(exc_info.value)
        assert "different connections" in error_msg

    def test_single_db_operation_with_transaction_passes(self) -> None:
        """Valid: Single DB operation with transaction enabled."""
        operations = [
            make_db_operation("single_op", "primary_db", "update", "UPDATE t SET x = 1")
        ]

        subcontract = make_subcontract(operations, transaction_enabled=True)
        assert subcontract.transaction.enabled is True
        assert len(subcontract.operations) == 1


# =============================================================================
# Test validate_idempotency_retry_interaction
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestValidateIdempotencyRetryInteraction:
    """Tests for validate_idempotency_retry_interaction validator.

    RULE: Cannot retry non-idempotent operations.
    """

    def test_idempotent_operation_with_retry_enabled_passes(self) -> None:
        """Valid: Idempotent operation (GET) with retry enabled."""
        operations = [
            make_http_operation("fetch_user", method="GET", idempotent=True),
        ]

        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=3)
        assert len(subcontract.operations) == 1

    def test_select_with_retry_enabled_passes(self) -> None:
        """Valid: SELECT (idempotent by default) with retry enabled."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        # SELECT is idempotent by default (IDEMPOTENCY_DEFAULTS)
        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=3)
        assert len(subcontract.operations) == 1

    def test_non_idempotent_operation_with_retry_disabled_passes(self) -> None:
        """Valid: Non-idempotent operation (POST) with retry disabled."""
        operations = [
            make_http_operation(
                "create_user",
                method="POST",
                body_template='{"name": "test"}',
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ]

        # Explicitly disable retry at operation level
        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=3)
        assert len(subcontract.operations) == 1

    def test_non_idempotent_post_with_retry_enabled_raises(self) -> None:
        """Invalid: Non-idempotent operation (POST) with retry enabled."""
        operations = [
            make_http_operation(
                "create_user",
                method="POST",
                body_template='{"name": "test"}',
                # No explicit idempotent override, so defaults to False for POST
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, retry_enabled=True, max_retries=3)

        error_msg = str(exc_info.value)
        assert "create_user" in error_msg
        assert "not idempotent" in error_msg
        assert "retry enabled" in error_msg

    def test_non_idempotent_insert_with_retry_enabled_raises(self) -> None:
        """Invalid: Non-idempotent operation (INSERT) with retry enabled."""
        operations = [
            make_db_operation(
                "insert_user",
                "primary_db",
                "insert",
                "INSERT INTO users (name) VALUES ($1)",
                ["${input.name}"],
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, retry_enabled=True, max_retries=3)

        error_msg = str(exc_info.value)
        assert "insert_user" in error_msg
        assert "not idempotent" in error_msg

    def test_kafka_produce_with_retry_enabled_raises(self) -> None:
        """Invalid: Kafka produce (non-idempotent by default) with retry enabled."""
        operations = [make_kafka_operation("publish_event")]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, retry_enabled=True, max_retries=3)

        error_msg = str(exc_info.value)
        assert "publish_event" in error_msg
        assert "not idempotent" in error_msg

    def test_explicit_idempotent_true_overrides_default(self) -> None:
        """Valid: Explicit idempotent=true overrides non-idempotent default."""
        operations = [
            make_http_operation(
                "create_user_idempotent",
                method="POST",
                body_template='{"name": "test"}',
                idempotent=True,  # Explicit override
            ),
        ]

        # Should pass because idempotent=True explicitly set
        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=3)
        assert len(subcontract.operations) == 1

    def test_zero_max_retries_passes(self) -> None:
        """Valid: Non-idempotent with retry enabled but max_retries=0."""
        operations = [
            make_http_operation(
                "create_user",
                method="POST",
                body_template='{"name": "test"}',
            ),
        ]

        # max_retries=0 means no actual retries happen
        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=0)
        assert len(subcontract.operations) == 1

    def test_operation_level_retry_overrides_default(self) -> None:
        """Valid: Operation-level retry disabled overrides default retry policy."""
        operations = [
            make_http_operation(
                "create_user",
                method="POST",
                body_template='{"name": "test"}',
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ]

        # Default is retry enabled, but operation overrides
        subcontract = make_subcontract(operations, retry_enabled=True, max_retries=3)
        assert len(subcontract.operations) == 1

    def test_multiple_operations_one_non_idempotent_with_retry_raises(self) -> None:
        """Invalid: Multiple operations where one non-idempotent has retry enabled."""
        operations = [
            make_http_operation("fetch_user", method="GET"),  # Idempotent
            make_http_operation(
                "create_user",
                method="POST",
                body_template='{"name": "test"}',
            ),  # Non-idempotent
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(operations, retry_enabled=True, max_retries=3)

        error_msg = str(exc_info.value)
        assert "create_user" in error_msg


# =============================================================================
# Test validate_select_retry_in_transaction
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestValidateSelectRetryInTransaction:
    """Tests for validate_select_retry_in_transaction validator.

    RULE: Cannot retry SELECT operations inside repeatable_read or serializable
    transactions. This violates snapshot semantics.
    """

    def test_select_with_retry_in_read_committed_passes(self) -> None:
        """Valid: SELECT with retry in read_committed transaction."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        # read_committed: safe to retry - each query sees fresh data
        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="read_committed",
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.enabled is True
        assert subcontract.transaction.isolation_level == "read_committed"

    def test_select_with_retry_in_read_uncommitted_passes(self) -> None:
        """Valid: SELECT with retry in read_uncommitted transaction."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="read_uncommitted",
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.isolation_level == "read_uncommitted"

    def test_select_without_retry_in_repeatable_read_passes(self) -> None:
        """Valid: SELECT without retry in repeatable_read transaction."""
        operations = [
            make_db_operation(
                "select_users",
                "primary_db",
                "select",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="repeatable_read",
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.isolation_level == "repeatable_read"

    def test_select_without_retry_in_serializable_passes(self) -> None:
        """Valid: SELECT without retry in serializable transaction."""
        operations = [
            make_db_operation(
                "select_users",
                "primary_db",
                "select",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="serializable",
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.isolation_level == "serializable"

    def test_select_with_retry_in_repeatable_read_raises(self) -> None:
        """Invalid: SELECT with retry in repeatable_read transaction."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(
                operations,
                transaction_enabled=True,
                isolation_level="repeatable_read",
                retry_enabled=True,
                max_retries=3,
            )

        error_msg = str(exc_info.value)
        assert "select_users" in error_msg
        assert "SELECT with retry enabled" in error_msg
        assert "repeatable_read" in error_msg
        assert "violates snapshot semantics" in error_msg

    def test_select_with_retry_in_serializable_raises(self) -> None:
        """Invalid: SELECT with retry in serializable transaction."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(
                operations,
                transaction_enabled=True,
                isolation_level="serializable",
                retry_enabled=True,
                max_retries=3,
            )

        error_msg = str(exc_info.value)
        assert "select_users" in error_msg
        assert "serializable" in error_msg

    def test_update_with_retry_in_serializable_passes(self) -> None:
        """Valid: UPDATE (not SELECT) with retry in serializable transaction."""
        operations = [
            make_db_operation(
                "update_user",
                "primary_db",
                "update",
                "UPDATE users SET x = 1",
                idempotent=True,  # UPDATE is idempotent by default
            ),
        ]

        # UPDATE is not SELECT, so not affected by this rule
        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="serializable",
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.isolation_level == "serializable"

    def test_select_no_transaction_with_retry_passes(self) -> None:
        """Valid: SELECT with retry when transaction is disabled."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
        ]

        # No transaction = no snapshot semantics to worry about
        subcontract = make_subcontract(
            operations,
            transaction_enabled=False,
            isolation_level="serializable",  # Doesn't matter since tx disabled
            retry_enabled=True,
            max_retries=3,
        )
        assert subcontract.transaction.enabled is False

    def test_multiple_selects_one_with_retry_in_repeatable_read_raises(self) -> None:
        """Invalid: Multiple SELECTs where one has retry in repeatable_read."""
        operations = [
            make_db_operation(
                "select_safe",
                "primary_db",
                "select",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
            make_db_operation(
                "select_unsafe",
                "primary_db",
                "select",
                # Uses default retry policy (enabled)
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(
                operations,
                transaction_enabled=True,
                isolation_level="repeatable_read",
                retry_enabled=True,
                max_retries=3,
            )

        error_msg = str(exc_info.value)
        assert "select_unsafe" in error_msg


# =============================================================================
# Test validate_no_raw_in_transaction
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestValidateNoRawInTransaction:
    """Tests for validate_no_raw_in_transaction validator.

    RULE: Raw DB operations are not allowed inside transactions.
    """

    def test_non_raw_operations_in_transaction_passes(self) -> None:
        """Valid: Non-raw DB operations in transaction."""
        operations = [
            make_db_operation("select_users", "primary_db", "select"),
            make_db_operation(
                "update_user", "primary_db", "update", "UPDATE users SET x = 1"
            ),
            make_db_operation(
                "insert_audit",
                "primary_db",
                "insert",
                "INSERT INTO audit VALUES ($1)",
                ["${input.msg}"],
                idempotent=True,  # Mark as idempotent to pass retry validation
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            retry_enabled=False,  # Disable retry to avoid idempotency issues
        )
        assert subcontract.transaction.enabled is True

    def test_raw_operation_without_transaction_passes(self) -> None:
        """Valid: Raw DB operation when transaction is disabled."""
        operations = [
            make_db_operation(
                "run_procedure",
                "primary_db",
                "raw",
                "CALL my_stored_procedure($1)",
                ["${input.param}"],
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=False,
            retry_enabled=False,  # Raw operations are non-idempotent
        )
        assert subcontract.transaction.enabled is False

    def test_raw_operation_in_transaction_raises(self) -> None:
        """Invalid: Raw DB operation in transaction."""
        operations = [
            make_db_operation(
                "run_procedure",
                "primary_db",
                "raw",
                "CALL my_stored_procedure($1)",
                ["${input.param}"],
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(
                operations,
                transaction_enabled=True,
                retry_enabled=False,  # Disable retry since raw is non-idempotent
            )

        error_msg = str(exc_info.value)
        assert "Raw DB operations not allowed inside transactions" in error_msg
        assert "run_procedure" in error_msg
        assert (
            "stored procedures" in error_msg or "multi-statement batches" in error_msg
        )

    def test_multiple_operations_one_raw_in_transaction_raises(self) -> None:
        """Invalid: Multiple operations where one is raw in transaction."""
        operations = [
            make_db_operation(
                "select_data",
                "primary_db",
                "select",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
            make_db_operation(
                "update_data",
                "primary_db",
                "update",
                "UPDATE t SET x = 1",
            ),
            make_db_operation(
                "run_cleanup",
                "primary_db",
                "raw",
                "TRUNCATE TABLE temp_data",
            ),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            make_subcontract(
                operations,
                transaction_enabled=True,
                retry_enabled=False,
            )

        error_msg = str(exc_info.value)
        assert "run_cleanup" in error_msg

    def test_delete_in_transaction_passes(self) -> None:
        """Valid: DELETE (not raw) in transaction."""
        operations = [
            make_db_operation(
                "delete_user",
                "primary_db",
                "delete",
                "DELETE FROM users WHERE id = $1",
                ["${input.id}"],
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            retry_enabled=False,
        )
        assert subcontract.transaction.enabled is True

    def test_upsert_in_transaction_passes(self) -> None:
        """Valid: UPSERT (not raw) in transaction."""
        operations = [
            make_db_operation(
                "upsert_user",
                "primary_db",
                "upsert",
                "INSERT INTO users (id, name) VALUES ($1, $2) ON CONFLICT DO UPDATE",
                ["${input.id}", "${input.name}"],
            ),
        ]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            retry_enabled=False,
        )
        assert subcontract.transaction.enabled is True


# =============================================================================
# Test validator interactions and edge cases
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestValidatorInteractions:
    """Tests for interactions between multiple validators."""

    def test_all_validators_pass_valid_subcontract(self) -> None:
        """Valid: All validators pass for a well-formed subcontract."""
        operations = [
            make_db_operation(
                "select_users",
                "primary_db",
                "select",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
            make_db_operation(
                "update_user",
                "primary_db",
                "update",
                "UPDATE users SET x = 1",
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ]

        # All validators should pass:
        # - Transaction scope: all DB, same connection
        # - Idempotency: retry disabled
        # - Select retry: retry disabled
        # - No raw: no raw operations
        subcontract = make_subcontract(
            operations,
            transaction_enabled=True,
            isolation_level="serializable",
            retry_enabled=False,
        )
        assert subcontract.transaction.enabled is True
        assert len(subcontract.operations) == 2

    def test_minimal_valid_subcontract(self) -> None:
        """Valid: Minimal subcontract with single operation."""
        operations = [make_http_operation("fetch_data", method="GET")]

        subcontract = make_subcontract(
            operations,
            transaction_enabled=False,
            retry_enabled=True,
            max_retries=3,
        )
        assert len(subcontract.operations) == 1

    def test_frozen_model_behavior(self) -> None:
        """Test that ModelEffectSubcontract is frozen (immutable)."""
        operations = [make_http_operation("fetch_data", method="GET")]
        subcontract = make_subcontract(operations)

        # Attempting to modify should raise
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            subcontract.subcontract_name = "new_name"  # type: ignore[misc]

    def test_default_retry_policy_values(self) -> None:
        """Test default retry policy is applied correctly."""
        operations = [make_http_operation("fetch_data", method="GET")]

        subcontract = make_subcontract(operations)

        # Check default retry policy
        assert subcontract.default_retry_policy.enabled is True
        assert subcontract.default_retry_policy.max_retries == 3

    def test_execution_mode_default(self) -> None:
        """Test default execution mode is sequential_abort."""
        operations = [make_http_operation("fetch_data", method="GET")]

        subcontract = make_subcontract(operations)
        assert subcontract.execution_mode == "sequential_abort"

    def test_operations_list_limits(self) -> None:
        """Test operations list has valid bounds (1-50)."""
        from pydantic import ValidationError

        # Test empty operations list (should fail)
        with pytest.raises(ValidationError):
            ModelEffectSubcontract(
                subcontract_name="test",
                operations=[],  # Empty list
            )

    def test_http_operation_idempotency_defaults(self) -> None:
        """Test HTTP operations use correct idempotency defaults."""
        # GET is idempotent by default
        get_op = make_http_operation("get_users", method="GET")
        assert get_op.get_effective_idempotency() is True

        # POST is non-idempotent by default
        post_op = make_http_operation("create_user", method="POST", body_template="{}")
        assert post_op.get_effective_idempotency() is False

        # PUT is idempotent by HTTP spec
        put_op = make_http_operation("update_user", method="PUT", body_template="{}")
        assert put_op.get_effective_idempotency() is True

        # DELETE is idempotent by HTTP spec
        delete_op = make_http_operation("delete_user", method="DELETE")
        assert delete_op.get_effective_idempotency() is True

    def test_db_operation_idempotency_defaults(self) -> None:
        """Test DB operations use correct idempotency defaults."""
        # SELECT is idempotent
        select_op = make_db_operation("select", "db", "select")
        assert select_op.get_effective_idempotency() is True

        # INSERT is non-idempotent
        insert_op = make_db_operation(
            "insert", "db", "insert", "INSERT INTO t VALUES ($1)", ["v"]
        )
        assert insert_op.get_effective_idempotency() is False

        # UPDATE is idempotent
        update_op = make_db_operation("update", "db", "update", "UPDATE t SET x = 1")
        assert update_op.get_effective_idempotency() is True

        # DELETE is idempotent
        delete_op = make_db_operation(
            "delete", "db", "delete", "DELETE FROM t WHERE id = $1", ["1"]
        )
        assert delete_op.get_effective_idempotency() is True

        # UPSERT is idempotent
        upsert_op = make_db_operation(
            "upsert", "db", "upsert", "INSERT ... ON CONFLICT DO UPDATE"
        )
        assert upsert_op.get_effective_idempotency() is True

        # RAW is non-idempotent (conservative default)
        raw_op = make_db_operation("raw", "db", "raw", "CALL procedure()")
        assert raw_op.get_effective_idempotency() is False

    def test_explicit_idempotency_overrides_default(self) -> None:
        """Test explicit idempotent field overrides default."""
        # POST marked as idempotent
        post_idempotent = make_http_operation(
            "create_idempotent",
            method="POST",
            body_template="{}",
            idempotent=True,
        )
        assert post_idempotent.get_effective_idempotency() is True

        # GET marked as non-idempotent (unusual but allowed)
        get_non_idempotent = make_http_operation(
            "get_with_side_effect",
            method="GET",
            idempotent=False,
        )
        assert get_non_idempotent.get_effective_idempotency() is False


# =============================================================================
# Test imports and exports
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelEffectSubcontractExports:
    """Test that ModelEffectSubcontract is properly exported."""

    def test_import_from_subcontracts_module(self) -> None:
        """Test import from subcontracts module."""
        from omnibase_core.models.contracts.subcontracts import (
            ModelEffectSubcontract,
        )

        assert ModelEffectSubcontract is not None

    def test_import_direct(self) -> None:
        """Test direct import from module."""
        from omnibase_core.models.contracts.subcontracts import (
            ModelEffectSubcontract as ModuleImport,
        )
        from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
            ModelEffectSubcontract as DirectImport,
        )

        assert DirectImport is ModuleImport
