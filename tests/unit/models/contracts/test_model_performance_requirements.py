# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelPerformanceRequirements.

Tests performance SLA specification including:
- Basic creation and field validation
- Existing fields remain valid (no regressions)
- New timeout fields (OMN-1548): database_query_timeout_ms, external_service_timeout_ms,
  projection_reader_timeout_ms, circuit_breaker_recovery_timeout_s
- Cross-field validation: database_query_timeout_ms <= single_operation_max_ms
- Serialization roundtrip
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)


@pytest.mark.unit
class TestModelPerformanceRequirementsDefaults:
    """Tests for ModelPerformanceRequirements default creation."""

    def test_default_creation_all_none(self) -> None:
        """Test that all fields default to None."""
        req = ModelPerformanceRequirements()
        assert req.single_operation_max_ms is None
        assert req.batch_operation_max_s is None
        assert req.memory_limit_mb is None
        assert req.cpu_limit_percent is None
        assert req.throughput_min_ops_per_second is None
        assert req.database_query_timeout_ms is None
        assert req.external_service_timeout_ms is None
        assert req.projection_reader_timeout_ms is None
        assert req.circuit_breaker_recovery_timeout_s is None

    def test_existing_fields_unaffected(self) -> None:
        """Test that existing fields work as before (no regression)."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=1000,
            batch_operation_max_s=30,
            memory_limit_mb=512,
            cpu_limit_percent=80,
            throughput_min_ops_per_second=100.0,
        )
        assert req.single_operation_max_ms == 1000
        assert req.batch_operation_max_s == 30
        assert req.memory_limit_mb == 512
        assert req.cpu_limit_percent == 80
        assert req.throughput_min_ops_per_second == 100.0

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored (extra='ignore')."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=500,
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert req.single_operation_max_ms == 500


@pytest.mark.unit
class TestDatabaseQueryTimeout:
    """Tests for database_query_timeout_ms field."""

    def test_database_query_timeout_accepts_valid_value(self) -> None:
        """Test that a valid database_query_timeout_ms is accepted."""
        req = ModelPerformanceRequirements(database_query_timeout_ms=500)
        assert req.database_query_timeout_ms == 500

    def test_database_query_timeout_minimum_boundary(self) -> None:
        """Test minimum boundary value (100ms) is accepted."""
        req = ModelPerformanceRequirements(database_query_timeout_ms=100)
        assert req.database_query_timeout_ms == 100

    def test_database_query_timeout_below_minimum_rejected(self) -> None:
        """Test that values below 100ms are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceRequirements(database_query_timeout_ms=99)
        assert "database_query_timeout_ms" in str(exc_info.value)

    def test_database_query_timeout_zero_rejected(self) -> None:
        """Test that zero is rejected."""
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(database_query_timeout_ms=0)

    def test_database_query_timeout_negative_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(database_query_timeout_ms=-500)

    def test_database_query_timeout_none_is_valid(self) -> None:
        """Test that None (absent) is valid for optional field."""
        req = ModelPerformanceRequirements(database_query_timeout_ms=None)
        assert req.database_query_timeout_ms is None


@pytest.mark.unit
class TestExternalServiceTimeout:
    """Tests for external_service_timeout_ms field."""

    def test_external_service_timeout_accepts_valid_value(self) -> None:
        """Test that a valid external_service_timeout_ms is accepted."""
        req = ModelPerformanceRequirements(external_service_timeout_ms=5000)
        assert req.external_service_timeout_ms == 5000

    def test_external_service_timeout_minimum_boundary(self) -> None:
        """Test minimum boundary value (100ms) is accepted."""
        req = ModelPerformanceRequirements(external_service_timeout_ms=100)
        assert req.external_service_timeout_ms == 100

    def test_external_service_timeout_below_minimum_rejected(self) -> None:
        """Test that values below 100ms are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceRequirements(external_service_timeout_ms=50)
        assert "external_service_timeout_ms" in str(exc_info.value)

    def test_external_service_timeout_none_is_valid(self) -> None:
        """Test that None (absent) is valid for optional field."""
        req = ModelPerformanceRequirements(external_service_timeout_ms=None)
        assert req.external_service_timeout_ms is None


@pytest.mark.unit
class TestProjectionReaderTimeout:
    """Tests for projection_reader_timeout_ms field."""

    def test_projection_reader_timeout_accepts_valid_value(self) -> None:
        """Test that a valid projection_reader_timeout_ms is accepted."""
        req = ModelPerformanceRequirements(projection_reader_timeout_ms=2000)
        assert req.projection_reader_timeout_ms == 2000

    def test_projection_reader_timeout_minimum_boundary(self) -> None:
        """Test minimum boundary value (100ms) is accepted."""
        req = ModelPerformanceRequirements(projection_reader_timeout_ms=100)
        assert req.projection_reader_timeout_ms == 100

    def test_projection_reader_timeout_below_minimum_rejected(self) -> None:
        """Test that values below 100ms are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceRequirements(projection_reader_timeout_ms=1)
        assert "projection_reader_timeout_ms" in str(exc_info.value)

    def test_projection_reader_timeout_none_is_valid(self) -> None:
        """Test that None (absent) is valid for optional field."""
        req = ModelPerformanceRequirements(projection_reader_timeout_ms=None)
        assert req.projection_reader_timeout_ms is None


@pytest.mark.unit
class TestCircuitBreakerRecoveryTimeout:
    """Tests for circuit_breaker_recovery_timeout_s field."""

    def test_circuit_breaker_timeout_accepts_valid_value(self) -> None:
        """Test that a valid circuit_breaker_recovery_timeout_s is accepted."""
        req = ModelPerformanceRequirements(circuit_breaker_recovery_timeout_s=60)
        assert req.circuit_breaker_recovery_timeout_s == 60

    def test_circuit_breaker_timeout_minimum_boundary(self) -> None:
        """Test minimum boundary value (1 second) is accepted."""
        req = ModelPerformanceRequirements(circuit_breaker_recovery_timeout_s=1)
        assert req.circuit_breaker_recovery_timeout_s == 1

    def test_circuit_breaker_timeout_below_minimum_rejected(self) -> None:
        """Test that values below 1 second are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceRequirements(circuit_breaker_recovery_timeout_s=0)
        assert "circuit_breaker_recovery_timeout_s" in str(exc_info.value)

    def test_circuit_breaker_timeout_negative_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(circuit_breaker_recovery_timeout_s=-10)

    def test_circuit_breaker_timeout_none_is_valid(self) -> None:
        """Test that None (absent) is valid for optional field."""
        req = ModelPerformanceRequirements(circuit_breaker_recovery_timeout_s=None)
        assert req.circuit_breaker_recovery_timeout_s is None


@pytest.mark.unit
class TestCrossFieldValidation:
    """Tests for cross-field validation: database_query_timeout_ms <= single_operation_max_ms."""

    def test_db_timeout_equal_to_operation_sla_is_valid(self) -> None:
        """Test that database_query_timeout_ms == single_operation_max_ms is valid."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=1000,
            database_query_timeout_ms=1000,
        )
        assert req.database_query_timeout_ms == 1000
        assert req.single_operation_max_ms == 1000

    def test_db_timeout_less_than_operation_sla_is_valid(self) -> None:
        """Test that database_query_timeout_ms < single_operation_max_ms is valid."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=1000,
            database_query_timeout_ms=500,
        )
        assert req.database_query_timeout_ms == 500
        assert req.single_operation_max_ms == 1000

    def test_db_timeout_greater_than_operation_sla_is_rejected(self) -> None:
        """Test that database_query_timeout_ms > single_operation_max_ms is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPerformanceRequirements(
                single_operation_max_ms=1000,
                database_query_timeout_ms=30000,
            )
        error_str = str(exc_info.value)
        assert "database_query_timeout_ms" in error_str
        assert "single_operation_max_ms" in error_str

    def test_db_timeout_set_without_operation_sla_is_valid(self) -> None:
        """Test that database_query_timeout_ms can be set without single_operation_max_ms."""
        req = ModelPerformanceRequirements(database_query_timeout_ms=500)
        assert req.database_query_timeout_ms == 500
        assert req.single_operation_max_ms is None

    def test_operation_sla_set_without_db_timeout_is_valid(self) -> None:
        """Test that single_operation_max_ms can be set without database_query_timeout_ms."""
        req = ModelPerformanceRequirements(single_operation_max_ms=1000)
        assert req.single_operation_max_ms == 1000
        assert req.database_query_timeout_ms is None

    def test_neither_field_set_is_valid(self) -> None:
        """Test that validation passes when neither cross-validated field is set."""
        req = ModelPerformanceRequirements()
        assert req.single_operation_max_ms is None
        assert req.database_query_timeout_ms is None

    def test_external_service_timeout_not_constrained_by_operation_sla(self) -> None:
        """Test that external_service_timeout_ms has no cross-field constraint."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=100,
            external_service_timeout_ms=60000,
        )
        assert req.external_service_timeout_ms == 60000
        assert req.single_operation_max_ms == 100


@pytest.mark.unit
class TestFullTimeoutConfiguration:
    """Tests for creating fully-configured timeout models."""

    def test_all_timeout_fields_set(self) -> None:
        """Test creation with all timeout fields populated."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=5000,
            batch_operation_max_s=30,
            memory_limit_mb=512,
            cpu_limit_percent=80,
            throughput_min_ops_per_second=50.0,
            database_query_timeout_ms=1000,
            external_service_timeout_ms=3000,
            projection_reader_timeout_ms=2000,
            circuit_breaker_recovery_timeout_s=60,
        )
        assert req.single_operation_max_ms == 5000
        assert req.database_query_timeout_ms == 1000
        assert req.external_service_timeout_ms == 3000
        assert req.projection_reader_timeout_ms == 2000
        assert req.circuit_breaker_recovery_timeout_s == 60

    def test_serialization_roundtrip_with_timeout_fields(self) -> None:
        """Test model serialization and deserialization preserves timeout fields."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=2000,
            database_query_timeout_ms=500,
            external_service_timeout_ms=1500,
            projection_reader_timeout_ms=800,
            circuit_breaker_recovery_timeout_s=30,
        )
        dumped = req.model_dump()
        assert dumped["database_query_timeout_ms"] == 500
        assert dumped["external_service_timeout_ms"] == 1500
        assert dumped["projection_reader_timeout_ms"] == 800
        assert dumped["circuit_breaker_recovery_timeout_s"] == 30

        restored = ModelPerformanceRequirements.model_validate(dumped)
        assert restored.database_query_timeout_ms == 500
        assert restored.external_service_timeout_ms == 1500
        assert restored.projection_reader_timeout_ms == 800
        assert restored.circuit_breaker_recovery_timeout_s == 30

    def test_serialization_roundtrip_none_timeout_fields(self) -> None:
        """Test serialization when timeout fields are None."""
        req = ModelPerformanceRequirements(single_operation_max_ms=1000)
        dumped = req.model_dump()
        assert dumped["database_query_timeout_ms"] is None
        assert dumped["external_service_timeout_ms"] is None
        assert dumped["projection_reader_timeout_ms"] is None
        assert dumped["circuit_breaker_recovery_timeout_s"] is None

        restored = ModelPerformanceRequirements.model_validate(dumped)
        assert restored.database_query_timeout_ms is None

    def test_validate_assignment_works_for_timeout_fields(self) -> None:
        """Test that validate_assignment enforces constraints on mutation."""
        req = ModelPerformanceRequirements(
            single_operation_max_ms=1000,
            database_query_timeout_ms=500,
        )
        # Valid assignment
        req.database_query_timeout_ms = 800
        assert req.database_query_timeout_ms == 800

        # Invalid: below minimum
        with pytest.raises(ValidationError):
            req.database_query_timeout_ms = 50

    def test_existing_contracts_remain_valid(self) -> None:
        """Regression test: verify existing contract patterns still work.

        New fields are optional with None defaults; existing contracts that
        don't specify timeout fields remain fully valid.
        """
        req = ModelPerformanceRequirements(single_operation_max_ms=1000)
        assert req.single_operation_max_ms == 1000
        assert req.database_query_timeout_ms is None
        assert req.external_service_timeout_ms is None
        assert req.projection_reader_timeout_ms is None
        assert req.circuit_breaker_recovery_timeout_s is None
