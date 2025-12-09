"""
Tests for Effect supporting models.

Comprehensive tests for Effect subcontract supporting models:
- ModelEffectRetryPolicy
- ModelEffectCircuitBreaker
- ModelEffectTransactionConfig
- ModelEffectObservability
- ModelEffectResponseHandling
- IDEMPOTENCY_DEFAULTS constant

Implements: OMN-524, OMN-525
"""

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from omnibase_core.constants.constants_effect_idempotency import IDEMPOTENCY_DEFAULTS
from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
    ModelEffectCircuitBreaker,
)
from omnibase_core.models.contracts.subcontracts.model_effect_observability import (
    ModelEffectObservability,
)
from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
    ModelEffectResponseHandling,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_transaction_config import (
    ModelEffectTransactionConfig,
)

# =============================================================================
# ModelEffectRetryPolicy Tests
# =============================================================================


class TestModelEffectRetryPolicyDefaults:
    """Test ModelEffectRetryPolicy default values."""

    def test_default_values_are_correct(self) -> None:
        """Test that default values match specification."""
        policy = ModelEffectRetryPolicy()
        assert policy.enabled is True
        assert policy.max_retries == 3
        assert policy.backoff_strategy == "exponential"
        assert policy.base_delay_ms == 1000
        assert policy.max_delay_ms == 30000
        assert policy.jitter_factor == 0.1
        assert policy.retryable_status_codes == [429, 500, 502, 503, 504]
        assert policy.retryable_errors == ["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED"]

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen (immutable)."""
        policy = ModelEffectRetryPolicy()
        with pytest.raises(ValidationError):
            policy.enabled = False  # type: ignore[misc]


class TestModelEffectRetryPolicyCustomConfiguration:
    """Test ModelEffectRetryPolicy with custom configurations."""

    def test_valid_custom_configuration(self) -> None:
        """Test creating with valid custom values."""
        policy = ModelEffectRetryPolicy(
            enabled=False,
            max_retries=5,
            backoff_strategy="fixed",
            base_delay_ms=500,
            max_delay_ms=10000,
            jitter_factor=0.2,
            retryable_status_codes=[500, 503],
            retryable_errors=["ECONNRESET"],
        )
        assert policy.enabled is False
        assert policy.max_retries == 5
        assert policy.backoff_strategy == "fixed"
        assert policy.base_delay_ms == 500
        assert policy.max_delay_ms == 10000
        assert policy.jitter_factor == 0.2
        assert policy.retryable_status_codes == [500, 503]
        assert policy.retryable_errors == ["ECONNRESET"]

    def test_all_backoff_strategies(self) -> None:
        """Test all valid backoff strategies."""
        for strategy in ["fixed", "exponential", "linear"]:
            policy = ModelEffectRetryPolicy(backoff_strategy=strategy)  # type: ignore[arg-type]
            assert policy.backoff_strategy == strategy

    def test_invalid_backoff_strategy(self) -> None:
        """Test that invalid backoff strategy is rejected."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(backoff_strategy="invalid")  # type: ignore[arg-type]


class TestModelEffectRetryPolicyConstraints:
    """Test ModelEffectRetryPolicy field constraints."""

    def test_max_retries_minimum(self) -> None:
        """Test max_retries minimum constraint (0)."""
        policy = ModelEffectRetryPolicy(max_retries=0)
        assert policy.max_retries == 0

    def test_max_retries_maximum(self) -> None:
        """Test max_retries maximum constraint (10)."""
        policy = ModelEffectRetryPolicy(max_retries=10)
        assert policy.max_retries == 10

    def test_max_retries_below_minimum(self) -> None:
        """Test max_retries below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(max_retries=-1)

    def test_max_retries_above_maximum(self) -> None:
        """Test max_retries above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(max_retries=11)

    def test_base_delay_ms_minimum(self) -> None:
        """Test base_delay_ms minimum constraint (100)."""
        policy = ModelEffectRetryPolicy(base_delay_ms=100)
        assert policy.base_delay_ms == 100

    def test_base_delay_ms_maximum(self) -> None:
        """Test base_delay_ms maximum constraint (60000)."""
        policy = ModelEffectRetryPolicy(base_delay_ms=60000)
        assert policy.base_delay_ms == 60000

    def test_base_delay_ms_below_minimum(self) -> None:
        """Test base_delay_ms below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(base_delay_ms=99)

    def test_base_delay_ms_above_maximum(self) -> None:
        """Test base_delay_ms above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(base_delay_ms=60001)

    def test_max_delay_ms_minimum(self) -> None:
        """Test max_delay_ms minimum constraint (1000)."""
        policy = ModelEffectRetryPolicy(max_delay_ms=1000)
        assert policy.max_delay_ms == 1000

    def test_max_delay_ms_maximum(self) -> None:
        """Test max_delay_ms maximum constraint (300000)."""
        policy = ModelEffectRetryPolicy(max_delay_ms=300000)
        assert policy.max_delay_ms == 300000

    def test_max_delay_ms_below_minimum(self) -> None:
        """Test max_delay_ms below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(max_delay_ms=999)

    def test_max_delay_ms_above_maximum(self) -> None:
        """Test max_delay_ms above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(max_delay_ms=300001)

    def test_jitter_factor_minimum(self) -> None:
        """Test jitter_factor minimum constraint (0.0)."""
        policy = ModelEffectRetryPolicy(jitter_factor=0.0)
        assert policy.jitter_factor == 0.0

    def test_jitter_factor_maximum(self) -> None:
        """Test jitter_factor maximum constraint (0.5)."""
        policy = ModelEffectRetryPolicy(jitter_factor=0.5)
        assert policy.jitter_factor == 0.5

    def test_jitter_factor_below_minimum(self) -> None:
        """Test jitter_factor below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(jitter_factor=-0.1)

    def test_jitter_factor_above_maximum(self) -> None:
        """Test jitter_factor above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectRetryPolicy(jitter_factor=0.6)


class TestModelEffectRetryPolicySerialization:
    """Test ModelEffectRetryPolicy serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump produces correct dictionary."""
        policy = ModelEffectRetryPolicy()
        data = policy.model_dump()
        assert isinstance(data, dict)
        assert data["enabled"] is True
        assert data["max_retries"] == 3
        assert data["backoff_strategy"] == "exponential"

    def test_model_dump_json(self) -> None:
        """Test model_dump_json produces valid JSON."""
        policy = ModelEffectRetryPolicy()
        json_str = policy.model_dump_json()
        assert isinstance(json_str, str)
        assert "exponential" in json_str

    def test_roundtrip_serialization(self) -> None:
        """Test serialization roundtrip."""
        original = ModelEffectRetryPolicy(
            max_retries=5, backoff_strategy="linear", jitter_factor=0.25
        )
        data = original.model_dump()
        restored = ModelEffectRetryPolicy.model_validate(data)
        assert restored.max_retries == original.max_retries
        assert restored.backoff_strategy == original.backoff_strategy
        assert restored.jitter_factor == original.jitter_factor


# =============================================================================
# ModelEffectCircuitBreaker Tests
# =============================================================================


class TestModelEffectCircuitBreakerDefaults:
    """Test ModelEffectCircuitBreaker default values."""

    def test_default_values_are_correct(self) -> None:
        """Test that default values match specification."""
        cb = ModelEffectCircuitBreaker()
        assert cb.enabled is False
        assert cb.failure_threshold == 5
        assert cb.success_threshold == 2
        assert cb.timeout_ms == 60000
        assert cb.half_open_requests == 3

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen (immutable)."""
        cb = ModelEffectCircuitBreaker()
        with pytest.raises(ValidationError):
            cb.enabled = True  # type: ignore[misc]


class TestModelEffectCircuitBreakerCustomConfiguration:
    """Test ModelEffectCircuitBreaker with custom configurations."""

    def test_valid_custom_configuration(self) -> None:
        """Test creating with valid custom values."""
        cb = ModelEffectCircuitBreaker(
            enabled=True,
            failure_threshold=3,
            success_threshold=1,
            timeout_ms=30000,
            half_open_requests=1,
        )
        assert cb.enabled is True
        assert cb.failure_threshold == 3
        assert cb.success_threshold == 1
        assert cb.timeout_ms == 30000
        assert cb.half_open_requests == 1


class TestModelEffectCircuitBreakerConstraints:
    """Test ModelEffectCircuitBreaker field constraints."""

    def test_failure_threshold_minimum(self) -> None:
        """Test failure_threshold minimum constraint (1)."""
        cb = ModelEffectCircuitBreaker(failure_threshold=1)
        assert cb.failure_threshold == 1

    def test_failure_threshold_maximum(self) -> None:
        """Test failure_threshold maximum constraint (100)."""
        cb = ModelEffectCircuitBreaker(failure_threshold=100)
        assert cb.failure_threshold == 100

    def test_failure_threshold_below_minimum(self) -> None:
        """Test failure_threshold below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(failure_threshold=0)

    def test_failure_threshold_above_maximum(self) -> None:
        """Test failure_threshold above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(failure_threshold=101)

    def test_success_threshold_minimum(self) -> None:
        """Test success_threshold minimum constraint (1)."""
        cb = ModelEffectCircuitBreaker(success_threshold=1)
        assert cb.success_threshold == 1

    def test_success_threshold_maximum(self) -> None:
        """Test success_threshold maximum constraint (10)."""
        cb = ModelEffectCircuitBreaker(success_threshold=10)
        assert cb.success_threshold == 10

    def test_success_threshold_below_minimum(self) -> None:
        """Test success_threshold below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(success_threshold=0)

    def test_success_threshold_above_maximum(self) -> None:
        """Test success_threshold above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(success_threshold=11)

    def test_timeout_ms_minimum(self) -> None:
        """Test timeout_ms minimum constraint (1000)."""
        cb = ModelEffectCircuitBreaker(timeout_ms=1000)
        assert cb.timeout_ms == 1000

    def test_timeout_ms_maximum(self) -> None:
        """Test timeout_ms maximum constraint (600000)."""
        cb = ModelEffectCircuitBreaker(timeout_ms=600000)
        assert cb.timeout_ms == 600000

    def test_timeout_ms_below_minimum(self) -> None:
        """Test timeout_ms below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(timeout_ms=999)

    def test_timeout_ms_above_maximum(self) -> None:
        """Test timeout_ms above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(timeout_ms=600001)

    def test_half_open_requests_minimum(self) -> None:
        """Test half_open_requests minimum constraint (1)."""
        cb = ModelEffectCircuitBreaker(half_open_requests=1)
        assert cb.half_open_requests == 1

    def test_half_open_requests_maximum(self) -> None:
        """Test half_open_requests maximum constraint (10)."""
        cb = ModelEffectCircuitBreaker(half_open_requests=10)
        assert cb.half_open_requests == 10

    def test_half_open_requests_below_minimum(self) -> None:
        """Test half_open_requests below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(half_open_requests=0)

    def test_half_open_requests_above_maximum(self) -> None:
        """Test half_open_requests above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectCircuitBreaker(half_open_requests=11)


class TestModelEffectCircuitBreakerSerialization:
    """Test ModelEffectCircuitBreaker serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump produces correct dictionary."""
        cb = ModelEffectCircuitBreaker()
        data = cb.model_dump()
        assert isinstance(data, dict)
        assert data["enabled"] is False
        assert data["failure_threshold"] == 5

    def test_roundtrip_serialization(self) -> None:
        """Test serialization roundtrip."""
        original = ModelEffectCircuitBreaker(
            enabled=True, failure_threshold=10, timeout_ms=90000
        )
        data = original.model_dump()
        restored = ModelEffectCircuitBreaker.model_validate(data)
        assert restored.enabled == original.enabled
        assert restored.failure_threshold == original.failure_threshold
        assert restored.timeout_ms == original.timeout_ms


# =============================================================================
# ModelEffectTransactionConfig Tests
# =============================================================================


class TestModelEffectTransactionConfigDefaults:
    """Test ModelEffectTransactionConfig default values."""

    def test_default_values_are_correct(self) -> None:
        """Test that default values match specification."""
        config = ModelEffectTransactionConfig()
        assert config.enabled is False
        assert config.isolation_level == "read_committed"
        assert config.rollback_on_error is True
        assert config.timeout_ms == 30000

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen (immutable)."""
        config = ModelEffectTransactionConfig()
        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]


class TestModelEffectTransactionConfigIsolationLevels:
    """Test ModelEffectTransactionConfig isolation level validation."""

    def test_read_uncommitted(self) -> None:
        """Test read_uncommitted isolation level."""
        config = ModelEffectTransactionConfig(isolation_level="read_uncommitted")
        assert config.isolation_level == "read_uncommitted"

    def test_read_committed(self) -> None:
        """Test read_committed isolation level."""
        config = ModelEffectTransactionConfig(isolation_level="read_committed")
        assert config.isolation_level == "read_committed"

    def test_repeatable_read(self) -> None:
        """Test repeatable_read isolation level."""
        config = ModelEffectTransactionConfig(isolation_level="repeatable_read")
        assert config.isolation_level == "repeatable_read"

    def test_serializable(self) -> None:
        """Test serializable isolation level."""
        config = ModelEffectTransactionConfig(isolation_level="serializable")
        assert config.isolation_level == "serializable"

    def test_invalid_isolation_level(self) -> None:
        """Test that invalid isolation level is rejected."""
        with pytest.raises(ValidationError):
            ModelEffectTransactionConfig(isolation_level="invalid")  # type: ignore[arg-type]


class TestModelEffectTransactionConfigConstraints:
    """Test ModelEffectTransactionConfig field constraints."""

    def test_timeout_ms_minimum(self) -> None:
        """Test timeout_ms minimum constraint (1000)."""
        config = ModelEffectTransactionConfig(timeout_ms=1000)
        assert config.timeout_ms == 1000

    def test_timeout_ms_maximum(self) -> None:
        """Test timeout_ms maximum constraint (300000)."""
        config = ModelEffectTransactionConfig(timeout_ms=300000)
        assert config.timeout_ms == 300000

    def test_timeout_ms_below_minimum(self) -> None:
        """Test timeout_ms below minimum fails."""
        with pytest.raises(ValidationError):
            ModelEffectTransactionConfig(timeout_ms=999)

    def test_timeout_ms_above_maximum(self) -> None:
        """Test timeout_ms above maximum fails."""
        with pytest.raises(ValidationError):
            ModelEffectTransactionConfig(timeout_ms=300001)


class TestModelEffectTransactionConfigSerialization:
    """Test ModelEffectTransactionConfig serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump produces correct dictionary."""
        config = ModelEffectTransactionConfig()
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["enabled"] is False
        assert data["isolation_level"] == "read_committed"

    def test_roundtrip_serialization(self) -> None:
        """Test serialization roundtrip."""
        original = ModelEffectTransactionConfig(
            enabled=True, isolation_level="serializable", timeout_ms=60000
        )
        data = original.model_dump()
        restored = ModelEffectTransactionConfig.model_validate(data)
        assert restored.enabled == original.enabled
        assert restored.isolation_level == original.isolation_level
        assert restored.timeout_ms == original.timeout_ms


# =============================================================================
# ModelEffectObservability Tests
# =============================================================================


class TestModelEffectObservabilityDefaults:
    """Test ModelEffectObservability default values."""

    def test_default_values_are_correct(self) -> None:
        """Test that default values match specification."""
        obs = ModelEffectObservability()
        assert obs.log_request is True
        assert obs.log_response is False
        assert obs.emit_metrics is True
        assert obs.trace_propagation is True

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen (immutable)."""
        obs = ModelEffectObservability()
        with pytest.raises(ValidationError):
            obs.log_request = False  # type: ignore[misc]


class TestModelEffectObservabilityCustomConfiguration:
    """Test ModelEffectObservability with custom configurations."""

    def test_all_enabled(self) -> None:
        """Test enabling all observability settings."""
        obs = ModelEffectObservability(
            log_request=True,
            log_response=True,
            emit_metrics=True,
            trace_propagation=True,
        )
        assert obs.log_request is True
        assert obs.log_response is True
        assert obs.emit_metrics is True
        assert obs.trace_propagation is True

    def test_all_disabled(self) -> None:
        """Test disabling all observability settings."""
        obs = ModelEffectObservability(
            log_request=False,
            log_response=False,
            emit_metrics=False,
            trace_propagation=False,
        )
        assert obs.log_request is False
        assert obs.log_response is False
        assert obs.emit_metrics is False
        assert obs.trace_propagation is False

    def test_security_conscious_configuration(self) -> None:
        """Test security-conscious configuration (log_response=False)."""
        obs = ModelEffectObservability(log_request=True, log_response=False)
        assert obs.log_request is True
        assert obs.log_response is False


class TestModelEffectObservabilitySerialization:
    """Test ModelEffectObservability serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump produces correct dictionary."""
        obs = ModelEffectObservability()
        data = obs.model_dump()
        assert isinstance(data, dict)
        assert data["log_request"] is True
        assert data["log_response"] is False

    def test_roundtrip_serialization(self) -> None:
        """Test serialization roundtrip."""
        original = ModelEffectObservability(
            log_request=False, log_response=True, emit_metrics=False
        )
        data = original.model_dump()
        restored = ModelEffectObservability.model_validate(data)
        assert restored.log_request == original.log_request
        assert restored.log_response == original.log_response
        assert restored.emit_metrics == original.emit_metrics


# =============================================================================
# ModelEffectResponseHandling Tests
# =============================================================================


class TestModelEffectResponseHandlingDefaults:
    """Test ModelEffectResponseHandling default values."""

    def test_default_success_codes(self) -> None:
        """Test default success_codes [200, 201, 202, 204]."""
        handling = ModelEffectResponseHandling()
        assert handling.success_codes == [200, 201, 202, 204]

    def test_default_extract_fields(self) -> None:
        """Test default extract_fields is empty dict."""
        handling = ModelEffectResponseHandling()
        assert handling.extract_fields == {}

    def test_default_fail_on_empty(self) -> None:
        """Test default fail_on_empty is False."""
        handling = ModelEffectResponseHandling()
        assert handling.fail_on_empty is False

    def test_default_extraction_engine(self) -> None:
        """Test default extraction_engine is jsonpath."""
        handling = ModelEffectResponseHandling()
        assert handling.extraction_engine == "jsonpath"

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen (immutable)."""
        handling = ModelEffectResponseHandling()
        with pytest.raises(ValidationError):
            handling.fail_on_empty = True  # type: ignore[misc]


class TestModelEffectResponseHandlingCustomConfiguration:
    """Test ModelEffectResponseHandling with custom configurations."""

    def test_valid_extract_fields(self) -> None:
        """Test valid extract_fields configuration."""
        handling = ModelEffectResponseHandling(
            extract_fields={
                "user_id": "$.data.id",
                "email": "$.data.email",
            }
        )
        assert handling.extract_fields["user_id"] == "$.data.id"
        assert handling.extract_fields["email"] == "$.data.email"

    def test_custom_success_codes(self) -> None:
        """Test custom success_codes."""
        handling = ModelEffectResponseHandling(success_codes=[200, 201])
        assert handling.success_codes == [200, 201]

    def test_fail_on_empty_enabled(self) -> None:
        """Test fail_on_empty enabled."""
        handling = ModelEffectResponseHandling(fail_on_empty=True)
        assert handling.fail_on_empty is True


class TestModelEffectResponseHandlingExtractionEngine:
    """Test ModelEffectResponseHandling extraction_engine options."""

    def test_jsonpath_engine(self) -> None:
        """Test jsonpath extraction engine."""
        handling = ModelEffectResponseHandling(extraction_engine="jsonpath")
        assert handling.extraction_engine == "jsonpath"

    def test_dotpath_engine(self) -> None:
        """Test dotpath extraction engine."""
        handling = ModelEffectResponseHandling(extraction_engine="dotpath")
        assert handling.extraction_engine == "dotpath"

    def test_invalid_extraction_engine(self) -> None:
        """Test that invalid extraction engine is rejected."""
        with pytest.raises(ValidationError):
            ModelEffectResponseHandling(extraction_engine="invalid")  # type: ignore[arg-type]


class TestModelEffectResponseHandlingSerialization:
    """Test ModelEffectResponseHandling serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump produces correct dictionary."""
        handling = ModelEffectResponseHandling()
        data = handling.model_dump()
        assert isinstance(data, dict)
        assert data["success_codes"] == [200, 201, 202, 204]
        assert data["extraction_engine"] == "jsonpath"

    def test_roundtrip_serialization(self) -> None:
        """Test serialization roundtrip."""
        original = ModelEffectResponseHandling(
            success_codes=[200],
            extract_fields={"id": "$.id"},
            extraction_engine="dotpath",
        )
        data = original.model_dump()
        restored = ModelEffectResponseHandling.model_validate(data)
        assert restored.success_codes == original.success_codes
        assert restored.extract_fields == original.extract_fields
        assert restored.extraction_engine == original.extraction_engine


# =============================================================================
# IDEMPOTENCY_DEFAULTS Constant Tests
# =============================================================================


class TestIdempotencyDefaultsHttpMethods:
    """Test IDEMPOTENCY_DEFAULTS for HTTP methods."""

    def test_http_key_exists(self) -> None:
        """Test http key exists in IDEMPOTENCY_DEFAULTS."""
        assert "http" in IDEMPOTENCY_DEFAULTS

    def test_get_is_idempotent(self) -> None:
        """Test GET is idempotent."""
        assert IDEMPOTENCY_DEFAULTS["http"]["GET"] is True

    def test_head_is_idempotent(self) -> None:
        """Test HEAD is idempotent."""
        assert IDEMPOTENCY_DEFAULTS["http"]["HEAD"] is True

    def test_options_is_idempotent(self) -> None:
        """Test OPTIONS is idempotent."""
        assert IDEMPOTENCY_DEFAULTS["http"]["OPTIONS"] is True

    def test_put_is_idempotent(self) -> None:
        """Test PUT is idempotent (per RFC 7231)."""
        assert IDEMPOTENCY_DEFAULTS["http"]["PUT"] is True

    def test_delete_is_idempotent(self) -> None:
        """Test DELETE is idempotent (per RFC 7231)."""
        assert IDEMPOTENCY_DEFAULTS["http"]["DELETE"] is True

    def test_post_is_not_idempotent(self) -> None:
        """Test POST is NOT idempotent."""
        assert IDEMPOTENCY_DEFAULTS["http"]["POST"] is False

    def test_patch_is_not_idempotent(self) -> None:
        """Test PATCH is NOT idempotent."""
        assert IDEMPOTENCY_DEFAULTS["http"]["PATCH"] is False

    def test_all_http_methods_present(self) -> None:
        """Test all expected HTTP methods are present."""
        expected_methods = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "POST", "PATCH"}
        assert set(IDEMPOTENCY_DEFAULTS["http"].keys()) == expected_methods


class TestIdempotencyDefaultsDbOperations:
    """Test IDEMPOTENCY_DEFAULTS for database operations."""

    def test_db_key_exists(self) -> None:
        """Test db key exists in IDEMPOTENCY_DEFAULTS."""
        assert "db" in IDEMPOTENCY_DEFAULTS

    def test_select_is_idempotent(self) -> None:
        """Test SELECT is idempotent."""
        assert IDEMPOTENCY_DEFAULTS["db"]["SELECT"] is True

    def test_insert_is_not_idempotent(self) -> None:
        """Test INSERT is NOT idempotent (may create duplicates)."""
        assert IDEMPOTENCY_DEFAULTS["db"]["INSERT"] is False

    def test_update_is_idempotent(self) -> None:
        """Test UPDATE is idempotent (same update = same result)."""
        assert IDEMPOTENCY_DEFAULTS["db"]["UPDATE"] is True

    def test_delete_is_idempotent(self) -> None:
        """Test DELETE is idempotent (deleting deleted = no-op)."""
        assert IDEMPOTENCY_DEFAULTS["db"]["DELETE"] is True

    def test_upsert_is_idempotent(self) -> None:
        """Test UPSERT is idempotent by design."""
        assert IDEMPOTENCY_DEFAULTS["db"]["UPSERT"] is True

    def test_all_db_operations_present(self) -> None:
        """Test all expected DB operations are present."""
        expected_ops = {"SELECT", "INSERT", "UPDATE", "DELETE", "UPSERT"}
        assert set(IDEMPOTENCY_DEFAULTS["db"].keys()) == expected_ops


class TestIdempotencyDefaultsKafkaOperations:
    """Test IDEMPOTENCY_DEFAULTS for Kafka operations."""

    def test_kafka_key_exists(self) -> None:
        """Test kafka key exists in IDEMPOTENCY_DEFAULTS."""
        assert "kafka" in IDEMPOTENCY_DEFAULTS

    def test_produce_is_not_idempotent(self) -> None:
        """Test produce is NOT idempotent (unless using idempotent producer)."""
        assert IDEMPOTENCY_DEFAULTS["kafka"]["produce"] is False

    def test_all_kafka_operations_present(self) -> None:
        """Test all expected Kafka operations are present."""
        expected_ops = {"produce"}
        assert set(IDEMPOTENCY_DEFAULTS["kafka"].keys()) == expected_ops


class TestIdempotencyDefaultsFilesystemOperations:
    """Test IDEMPOTENCY_DEFAULTS for filesystem operations."""

    def test_filesystem_key_exists(self) -> None:
        """Test filesystem key exists in IDEMPOTENCY_DEFAULTS."""
        assert "filesystem" in IDEMPOTENCY_DEFAULTS

    def test_read_is_idempotent(self) -> None:
        """Test read is idempotent."""
        assert IDEMPOTENCY_DEFAULTS["filesystem"]["read"] is True

    def test_write_is_not_idempotent(self) -> None:
        """Test write is NOT idempotent (overwrites may corrupt data)."""
        assert IDEMPOTENCY_DEFAULTS["filesystem"]["write"] is False

    def test_delete_is_idempotent(self) -> None:
        """Test delete is idempotent (deleting deleted = no-op)."""
        assert IDEMPOTENCY_DEFAULTS["filesystem"]["delete"] is True

    def test_move_is_not_idempotent(self) -> None:
        """Test move is NOT idempotent (source may not exist after first move)."""
        assert IDEMPOTENCY_DEFAULTS["filesystem"]["move"] is False

    def test_copy_is_not_idempotent(self) -> None:
        """Test copy is NOT idempotent (dest may exist after first attempt)."""
        assert IDEMPOTENCY_DEFAULTS["filesystem"]["copy"] is False

    def test_all_filesystem_operations_present(self) -> None:
        """Test all expected filesystem operations are present."""
        expected_ops = {"read", "write", "delete", "move", "copy"}
        assert set(IDEMPOTENCY_DEFAULTS["filesystem"].keys()) == expected_ops


class TestIdempotencyDefaultsStructure:
    """Test overall structure of IDEMPOTENCY_DEFAULTS."""

    def test_all_handler_types_present(self) -> None:
        """Test all expected handler types are present."""
        expected_types = {"http", "db", "kafka", "filesystem"}
        assert set(IDEMPOTENCY_DEFAULTS.keys()) == expected_types

    def test_all_values_are_booleans(self) -> None:
        """Test all idempotency values are booleans."""
        for handler_type, operations in IDEMPOTENCY_DEFAULTS.items():
            for operation, is_idempotent in operations.items():
                assert isinstance(is_idempotent, bool), (
                    f"{handler_type}.{operation} is not bool"
                )

    def test_dictionary_is_properly_typed(self) -> None:
        """Test IDEMPOTENCY_DEFAULTS is immutable MappingProxyType."""
        # Outer structure is MappingProxyType (immutable)
        assert isinstance(IDEMPOTENCY_DEFAULTS, MappingProxyType)
        for handler_type, operations in IDEMPOTENCY_DEFAULTS.items():
            assert isinstance(handler_type, str)
            # Inner structures are also MappingProxyType (deeply immutable)
            assert isinstance(operations, MappingProxyType)
            for operation, is_idempotent in operations.items():
                assert isinstance(operation, str)
                assert isinstance(is_idempotent, bool)


# =============================================================================
# Extra Fields Rejection Tests (all models use extra="forbid")
# =============================================================================


class TestExtraFieldsRejection:
    """Test that all models reject extra fields (extra='forbid')."""

    def test_retry_policy_rejects_extra_fields(self) -> None:
        """Test ModelEffectRetryPolicy rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRetryPolicy.model_validate({"unknown_field": "value"})
        assert "extra" in str(exc_info.value).lower()

    def test_circuit_breaker_rejects_extra_fields(self) -> None:
        """Test ModelEffectCircuitBreaker rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectCircuitBreaker.model_validate({"unknown_field": "value"})
        assert "extra" in str(exc_info.value).lower()

    def test_transaction_config_rejects_extra_fields(self) -> None:
        """Test ModelEffectTransactionConfig rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectTransactionConfig.model_validate({"unknown_field": "value"})
        assert "extra" in str(exc_info.value).lower()

    def test_observability_rejects_extra_fields(self) -> None:
        """Test ModelEffectObservability rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectObservability.model_validate({"unknown_field": "value"})
        assert "extra" in str(exc_info.value).lower()

    def test_response_handling_rejects_extra_fields(self) -> None:
        """Test ModelEffectResponseHandling rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectResponseHandling.model_validate({"unknown_field": "value"})
        assert "extra" in str(exc_info.value).lower()
