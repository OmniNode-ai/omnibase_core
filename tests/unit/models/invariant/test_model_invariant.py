"""Tests for ModelInvariant model."""

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import ModelInvariant

# Test UUIDs for consistent testing
TEST_UUID_1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_2 = uuid.UUID("87654321-4321-8765-4321-876543218765")


@pytest.mark.unit
class TestModelInvariantValidation:
    """Test ModelInvariant validation."""

    def test_invariant_requires_name(self) -> None:
        """Name is required field."""
        with pytest.raises(ValidationError):
            ModelInvariant(type=EnumInvariantType.SCHEMA, config={"json_schema": {}})

    def test_invariant_requires_type(self) -> None:
        """Type is required field."""
        with pytest.raises(ValidationError):
            ModelInvariant(name="Test invariant", config={})

    def test_invariant_default_severity_is_warning(self) -> None:
        """Default severity should be warning if not specified."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.SCHEMA,
            config={"json_schema": {}},
        )
        assert inv.severity == EnumSeverity.WARNING

    def test_invariant_default_enabled_is_true(self) -> None:
        """Default enabled should be True."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv.enabled is True

    def test_invariant_generates_uuid_id(self) -> None:
        """ID should be auto-generated UUID."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv.id is not None
        assert isinstance(inv.id, uuid.UUID)

    def test_invariant_accepts_all_types(self) -> None:
        """All 7 invariant types should be valid with proper configs."""
        # Each type requires specific config keys
        type_configs: dict[EnumInvariantType, dict[str, object]] = {
            EnumInvariantType.SCHEMA: {"json_schema": {"type": "object"}},
            EnumInvariantType.FIELD_PRESENCE: {"fields": ["response"]},
            EnumInvariantType.FIELD_VALUE: {"field_path": "status"},
            EnumInvariantType.THRESHOLD: {"metric_name": "accuracy"},
            EnumInvariantType.LATENCY: {"max_ms": 5000},
            EnumInvariantType.COST: {"max_cost": 0.10},
            EnumInvariantType.CUSTOM: {"callable_path": "my_module.validator"},
        }
        for inv_type in EnumInvariantType:
            inv = ModelInvariant(
                name=f"Test {inv_type.value}",
                type=inv_type,
                config=type_configs[inv_type],
            )
            assert inv.type == inv_type


@pytest.mark.unit
class TestModelInvariantSeverityLevels:
    """Test ModelInvariant severity levels."""

    def test_invariant_accepts_all_severity_levels(self) -> None:
        """All severity levels should be valid."""
        for severity in EnumSeverity:
            inv = ModelInvariant(
                name=f"Test {severity.value}",
                type=EnumInvariantType.LATENCY,
                severity=severity,
                config={"max_ms": 5000},
            )
            assert inv.severity == severity

    def test_invariant_critical_severity(self) -> None:
        """Critical severity can be set explicitly."""
        inv = ModelInvariant(
            name="Critical check",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 1000},
        )
        assert inv.severity == EnumSeverity.CRITICAL

    def test_invariant_info_severity(self) -> None:
        """Info severity can be set explicitly."""
        inv = ModelInvariant(
            name="Info check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.INFO,
            config={"metric_name": "latency_p99", "max_value": 2000},
        )
        assert inv.severity == EnumSeverity.INFO


@pytest.mark.unit
class TestModelInvariantOptionalFields:
    """Test ModelInvariant optional fields."""

    def test_invariant_with_description(self) -> None:
        """Invariant can have optional description."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
            description="This invariant checks response latency",
        )
        assert inv.description == "This invariant checks response latency"

    def test_invariant_without_description(self) -> None:
        """Invariant description defaults to None."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv.description is None

    def test_invariant_can_be_disabled(self) -> None:
        """Invariant can be explicitly disabled."""
        inv = ModelInvariant(
            name="Disabled check",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
            enabled=False,
        )
        assert inv.enabled is False

    def test_invariant_with_custom_id(self) -> None:
        """Invariant can accept custom UUID."""
        custom_id = TEST_UUID_1
        inv = ModelInvariant(
            id=custom_id,
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv.id == custom_id


@pytest.mark.unit
class TestModelInvariantTypeSpecificValidation:
    """Test type-specific validation behaviors."""

    def test_latency_invariant_with_valid_config(self) -> None:
        """Latency invariant accepts max_ms config."""
        inv = ModelInvariant(
            name="Latency check",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv.config["max_ms"] == 5000

    def test_cost_invariant_with_valid_config(self) -> None:
        """Cost invariant accepts max_cost and per config."""
        inv = ModelInvariant(
            name="Cost check",
            type=EnumInvariantType.COST,
            config={"max_cost": 0.10, "per": "request"},
        )
        assert inv.config["max_cost"] == 0.10
        assert inv.config["per"] == "request"

    def test_field_presence_invariant_with_valid_config(self) -> None:
        """Field presence invariant accepts fields list config."""
        inv = ModelInvariant(
            name="Field check",
            type=EnumInvariantType.FIELD_PRESENCE,
            config={"fields": ["response", "model", "usage"]},
        )
        assert inv.config["fields"] == ["response", "model", "usage"]

    def test_schema_invariant_with_valid_config(self) -> None:
        """Schema invariant accepts json_schema config."""
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}},
        }
        inv = ModelInvariant(
            name="Schema check",
            type=EnumInvariantType.SCHEMA,
            config={"json_schema": schema},
        )
        assert inv.config["json_schema"] == schema

    def test_threshold_invariant_with_min_value(self) -> None:
        """Threshold invariant accepts min_value config."""
        inv = ModelInvariant(
            name="Threshold check",
            type=EnumInvariantType.THRESHOLD,
            config={"metric_name": "accuracy", "min_value": 0.95},
        )
        assert inv.config["min_value"] == 0.95

    def test_threshold_invariant_with_max_value(self) -> None:
        """Threshold invariant accepts max_value config."""
        inv = ModelInvariant(
            name="Threshold check",
            type=EnumInvariantType.THRESHOLD,
            config={"metric_name": "error_rate", "max_value": 0.05},
        )
        assert inv.config["max_value"] == 0.05

    def test_field_value_invariant_with_valid_config(self) -> None:
        """Field value invariant accepts field_path and expected_value config."""
        inv = ModelInvariant(
            name="Field value check",
            type=EnumInvariantType.FIELD_VALUE,
            config={"field_path": "status", "expected_value": "success"},
        )
        assert inv.config["field_path"] == "status"
        assert inv.config["expected_value"] == "success"

    def test_custom_invariant_with_valid_config(self) -> None:
        """Custom invariant accepts callable_path and kwargs config."""
        inv = ModelInvariant(
            name="Custom check",
            type=EnumInvariantType.CUSTOM,
            config={
                "callable_path": "my_module.custom_validator",
                "kwargs": {"custom_param": "value"},
            },
        )
        assert inv.config["callable_path"] == "my_module.custom_validator"


@pytest.mark.unit
class TestModelInvariantEquality:
    """Test ModelInvariant equality and comparison."""

    def test_invariants_with_same_values_are_equal(self) -> None:
        """Invariants with same values should be equal."""
        inv1 = ModelInvariant(
            id=TEST_UUID_1,
            name="Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 5000},
        )
        inv2 = ModelInvariant(
            id=TEST_UUID_1,
            name="Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 5000},
        )
        assert inv1 == inv2

    def test_invariants_with_different_ids_are_not_equal(self) -> None:
        """Invariants with different IDs should not be equal."""
        inv1 = ModelInvariant(
            id=TEST_UUID_1,
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        inv2 = ModelInvariant(
            id=TEST_UUID_2,
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        assert inv1 != inv2


@pytest.mark.unit
class TestModelInvariantStringRepresentation:
    """Test ModelInvariant string representation."""

    def test_invariant_str_representation(self) -> None:
        """Invariant should have readable string representation."""
        inv = ModelInvariant(
            name="Latency Check",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        str_repr = str(inv)
        assert isinstance(str_repr, str)

    def test_invariant_repr(self) -> None:
        """Invariant should have detailed repr."""
        inv = ModelInvariant(
            name="Latency Check",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )
        repr_str = repr(inv)
        assert "ModelInvariant" in repr_str
        assert "Latency Check" in repr_str
