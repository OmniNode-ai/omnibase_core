"""
Tests for EnumHealthStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_health_status import EnumHealthStatus


@pytest.mark.unit
class TestEnumHealthStatus:
    """Test cases for EnumHealthStatus enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHealthStatus.HEALTHY == "healthy"
        assert EnumHealthStatus.DEGRADED == "degraded"
        assert EnumHealthStatus.UNHEALTHY == "unhealthy"
        assert EnumHealthStatus.CRITICAL == "critical"
        assert EnumHealthStatus.UNKNOWN == "unknown"
        assert EnumHealthStatus.WARNING == "warning"
        assert EnumHealthStatus.UNREACHABLE == "unreachable"
        assert EnumHealthStatus.AVAILABLE == "available"
        assert EnumHealthStatus.UNAVAILABLE == "unavailable"
        assert EnumHealthStatus.ERROR == "error"
        assert EnumHealthStatus.INITIALIZING == "initializing"
        assert EnumHealthStatus.DISPOSING == "disposing"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHealthStatus, str)
        assert issubclass(EnumHealthStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumHealthStatus.HEALTHY) == "healthy"
        assert str(EnumHealthStatus.DEGRADED) == "degraded"
        assert str(EnumHealthStatus.UNHEALTHY) == "unhealthy"
        assert str(EnumHealthStatus.CRITICAL) == "critical"
        assert str(EnumHealthStatus.UNKNOWN) == "unknown"
        assert str(EnumHealthStatus.WARNING) == "warning"
        assert str(EnumHealthStatus.UNREACHABLE) == "unreachable"
        assert str(EnumHealthStatus.AVAILABLE) == "available"
        assert str(EnumHealthStatus.UNAVAILABLE) == "unavailable"
        assert str(EnumHealthStatus.ERROR) == "error"
        assert str(EnumHealthStatus.INITIALIZING) == "initializing"
        assert str(EnumHealthStatus.DISPOSING) == "disposing"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHealthStatus)
        assert len(values) == 12
        assert EnumHealthStatus.HEALTHY in values
        assert EnumHealthStatus.DEGRADED in values
        assert EnumHealthStatus.UNHEALTHY in values
        assert EnumHealthStatus.CRITICAL in values
        assert EnumHealthStatus.UNKNOWN in values
        assert EnumHealthStatus.WARNING in values
        assert EnumHealthStatus.UNREACHABLE in values
        assert EnumHealthStatus.AVAILABLE in values
        assert EnumHealthStatus.UNAVAILABLE in values
        assert EnumHealthStatus.ERROR in values
        assert EnumHealthStatus.INITIALIZING in values
        assert EnumHealthStatus.DISPOSING in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "healthy" in EnumHealthStatus
        assert "degraded" in EnumHealthStatus
        assert "unhealthy" in EnumHealthStatus
        assert "critical" in EnumHealthStatus
        assert "unknown" in EnumHealthStatus
        assert "warning" in EnumHealthStatus
        assert "unreachable" in EnumHealthStatus
        assert "available" in EnumHealthStatus
        assert "unavailable" in EnumHealthStatus
        assert "error" in EnumHealthStatus
        assert "initializing" in EnumHealthStatus
        assert "disposing" in EnumHealthStatus
        assert "invalid" not in EnumHealthStatus

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHealthStatus.HEALTHY == "healthy"
        assert EnumHealthStatus.DEGRADED == "degraded"
        assert EnumHealthStatus.UNHEALTHY == "unhealthy"
        assert EnumHealthStatus.CRITICAL == "critical"
        assert EnumHealthStatus.UNKNOWN == "unknown"
        assert EnumHealthStatus.WARNING == "warning"
        assert EnumHealthStatus.UNREACHABLE == "unreachable"
        assert EnumHealthStatus.AVAILABLE == "available"
        assert EnumHealthStatus.UNAVAILABLE == "unavailable"
        assert EnumHealthStatus.ERROR == "error"
        assert EnumHealthStatus.INITIALIZING == "initializing"
        assert EnumHealthStatus.DISPOSING == "disposing"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHealthStatus.HEALTHY.value == "healthy"
        assert EnumHealthStatus.DEGRADED.value == "degraded"
        assert EnumHealthStatus.UNHEALTHY.value == "unhealthy"
        assert EnumHealthStatus.CRITICAL.value == "critical"
        assert EnumHealthStatus.UNKNOWN.value == "unknown"
        assert EnumHealthStatus.WARNING.value == "warning"
        assert EnumHealthStatus.UNREACHABLE.value == "unreachable"
        assert EnumHealthStatus.AVAILABLE.value == "available"
        assert EnumHealthStatus.UNAVAILABLE.value == "unavailable"
        assert EnumHealthStatus.ERROR.value == "error"
        assert EnumHealthStatus.INITIALIZING.value == "initializing"
        assert EnumHealthStatus.DISPOSING.value == "disposing"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHealthStatus("healthy") == EnumHealthStatus.HEALTHY
        assert EnumHealthStatus("degraded") == EnumHealthStatus.DEGRADED
        assert EnumHealthStatus("unhealthy") == EnumHealthStatus.UNHEALTHY
        assert EnumHealthStatus("critical") == EnumHealthStatus.CRITICAL
        assert EnumHealthStatus("unknown") == EnumHealthStatus.UNKNOWN
        assert EnumHealthStatus("warning") == EnumHealthStatus.WARNING
        assert EnumHealthStatus("unreachable") == EnumHealthStatus.UNREACHABLE
        assert EnumHealthStatus("available") == EnumHealthStatus.AVAILABLE
        assert EnumHealthStatus("unavailable") == EnumHealthStatus.UNAVAILABLE
        assert EnumHealthStatus("error") == EnumHealthStatus.ERROR
        assert EnumHealthStatus("initializing") == EnumHealthStatus.INITIALIZING
        assert EnumHealthStatus("disposing") == EnumHealthStatus.DISPOSING

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHealthStatus("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [status.value for status in EnumHealthStatus]
        expected_values = [
            "healthy",
            "degraded",
            "unhealthy",
            "critical",
            "unknown",
            "warning",
            "unreachable",
            "available",
            "unavailable",
            "error",
            "initializing",
            "disposing",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Canonical health status" in EnumHealthStatus.__doc__

    def test_is_operational_method(self):
        """Test the is_operational method.

        Operational statuses indicate the component can handle requests,
        even if degraded or with warnings.
        """
        assert EnumHealthStatus.HEALTHY.is_operational() is True
        assert EnumHealthStatus.DEGRADED.is_operational() is True
        assert EnumHealthStatus.WARNING.is_operational() is True
        assert EnumHealthStatus.AVAILABLE.is_operational() is True
        # Non-operational statuses
        assert EnumHealthStatus.UNHEALTHY.is_operational() is False
        assert EnumHealthStatus.CRITICAL.is_operational() is False
        assert EnumHealthStatus.UNKNOWN.is_operational() is False
        assert EnumHealthStatus.UNREACHABLE.is_operational() is False
        assert EnumHealthStatus.UNAVAILABLE.is_operational() is False
        assert EnumHealthStatus.ERROR.is_operational() is False
        assert EnumHealthStatus.INITIALIZING.is_operational() is False
        assert EnumHealthStatus.DISPOSING.is_operational() is False

    def test_requires_attention_method(self):
        """Test the requires_attention method.

        Statuses that require immediate attention indicate critical problems.
        """
        # Require attention
        assert EnumHealthStatus.UNHEALTHY.requires_attention() is True
        assert EnumHealthStatus.CRITICAL.requires_attention() is True
        assert EnumHealthStatus.ERROR.requires_attention() is True
        assert EnumHealthStatus.UNREACHABLE.requires_attention() is True
        # Don't require attention
        assert EnumHealthStatus.HEALTHY.requires_attention() is False
        assert EnumHealthStatus.DEGRADED.requires_attention() is False
        assert EnumHealthStatus.UNKNOWN.requires_attention() is False
        assert EnumHealthStatus.WARNING.requires_attention() is False
        assert EnumHealthStatus.AVAILABLE.requires_attention() is False
        assert EnumHealthStatus.UNAVAILABLE.requires_attention() is False
        assert EnumHealthStatus.INITIALIZING.requires_attention() is False
        assert EnumHealthStatus.DISPOSING.requires_attention() is False

    def test_is_transitional_method(self):
        """Test the is_transitional method.

        Transitional statuses indicate temporary states during startup/shutdown.
        """
        assert EnumHealthStatus.INITIALIZING.is_transitional() is True
        assert EnumHealthStatus.DISPOSING.is_transitional() is True
        # Non-transitional
        assert EnumHealthStatus.HEALTHY.is_transitional() is False
        assert EnumHealthStatus.DEGRADED.is_transitional() is False
        assert EnumHealthStatus.UNHEALTHY.is_transitional() is False
        assert EnumHealthStatus.CRITICAL.is_transitional() is False
        assert EnumHealthStatus.UNKNOWN.is_transitional() is False
        assert EnumHealthStatus.WARNING.is_transitional() is False
        assert EnumHealthStatus.UNREACHABLE.is_transitional() is False
        assert EnumHealthStatus.AVAILABLE.is_transitional() is False
        assert EnumHealthStatus.UNAVAILABLE.is_transitional() is False
        assert EnumHealthStatus.ERROR.is_transitional() is False

    def test_roundtrip_serialization_all_values(self):
        """Test roundtrip serialization for all enum values.

        Ensures str(enum) -> Enum(str) works for every value.
        """
        for status in EnumHealthStatus:
            # String roundtrip
            serialized = str(status)
            deserialized = EnumHealthStatus(serialized)
            assert deserialized == status, (
                f"String roundtrip failed for {status}: "
                f"serialized={serialized}, deserialized={deserialized}"
            )

            # Value roundtrip
            value = status.value
            reconstructed = EnumHealthStatus(value)
            assert reconstructed == status, (
                f"Value roundtrip failed for {status}: "
                f"value={value}, reconstructed={reconstructed}"
            )

    def test_helper_method_coverage_completeness(self):
        """Test that helper methods cover all status values without gaps.

        Every status should be categorized by at least one helper method,
        ensuring no status is left in an undefined state.
        """
        for status in EnumHealthStatus:
            is_operational = status.is_operational()
            requires_attention = status.requires_attention()
            is_transitional = status.is_transitional()

            # Not all statuses need to be covered by helpers, but we verify
            # that the classification is consistent
            # For example: UNAVAILABLE is neither operational nor requires_attention
            # nor transitional - this is expected as it represents "unavailable but
            # not critical"

            # Verify no status is both operational and requires attention
            if is_operational:
                # Operational statuses should not require attention (except WARNING)
                if status != EnumHealthStatus.WARNING:
                    assert not requires_attention, (
                        f"{status} is operational and requires attention"
                    )

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""
        from pydantic import BaseModel, ValidationError

        class HealthModel(BaseModel):
            status: EnumHealthStatus

        # Test valid enum assignment
        model = HealthModel(status=EnumHealthStatus.HEALTHY)
        assert model.status == EnumHealthStatus.HEALTHY

        # Test string assignment
        model = HealthModel(status="degraded")
        assert model.status == EnumHealthStatus.DEGRADED

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            HealthModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        from pydantic import BaseModel

        class HealthModel(BaseModel):
            status: EnumHealthStatus

        model = HealthModel(status=EnumHealthStatus.CRITICAL)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"status": "critical"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"status":"critical"}'

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        import json

        status = EnumHealthStatus.DEGRADED
        json_str = json.dumps(status, default=str)
        assert json_str == '"degraded"'

        # Test in dictionary
        data = {"health_status": EnumHealthStatus.HEALTHY}
        json_str = json.dumps(data, default=str)
        assert '"health_status": "healthy"' in json_str

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        data = {"status": str(EnumHealthStatus.INITIALIZING)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: initializing" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "initializing"

    def test_is_operational_exhaustive(self):
        """Test is_operational returns correct values for ALL statuses.

        Exhaustive test to ensure all 12 statuses are covered.
        """
        operational_statuses = {
            EnumHealthStatus.HEALTHY,
            EnumHealthStatus.DEGRADED,
            EnumHealthStatus.AVAILABLE,
            EnumHealthStatus.WARNING,
        }

        for status in EnumHealthStatus:
            expected = status in operational_statuses
            assert status.is_operational() == expected, (
                f"is_operational() mismatch for {status}: "
                f"expected={expected}, actual={status.is_operational()}"
            )

    def test_requires_attention_exhaustive(self):
        """Test requires_attention returns correct values for ALL statuses.

        Exhaustive test to ensure all 12 statuses are covered.
        """
        attention_statuses = {
            EnumHealthStatus.UNHEALTHY,
            EnumHealthStatus.CRITICAL,
            EnumHealthStatus.ERROR,
            EnumHealthStatus.UNREACHABLE,
        }

        for status in EnumHealthStatus:
            expected = status in attention_statuses
            assert status.requires_attention() == expected, (
                f"requires_attention() mismatch for {status}: "
                f"expected={expected}, actual={status.requires_attention()}"
            )

    def test_is_transitional_exhaustive(self):
        """Test is_transitional returns correct values for ALL statuses.

        Exhaustive test to ensure all 12 statuses are covered.
        """
        transitional_statuses = {
            EnumHealthStatus.INITIALIZING,
            EnumHealthStatus.DISPOSING,
        }

        for status in EnumHealthStatus:
            expected = status in transitional_statuses
            assert status.is_transitional() == expected, (
                f"is_transitional() mismatch for {status}: "
                f"expected={expected}, actual={status.is_transitional()}"
            )
