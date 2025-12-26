# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelRoutingMetadata.

Tests all ModelRoutingMetadata functionality including:
- Basic instantiation with all fields
- Partial instantiation with optional fields
- Default value verification
- Field validation (load_balance_strategy, weight)
- Frozen behavior (immutability)
- Extra fields forbidden
- JSON serialization/deserialization
- from_attributes behavior
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelRoutingMetadata

# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class RoutingMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelRoutingMetadata."""

    target_region: str | None = None
    preferred_instance: str | None = None
    load_balance_strategy: str = "round_robin"
    sticky_session_id: UUID | None = None
    priority: int = 0
    weight: float = 1.0
    timeout_override_ms: int | None = None
    circuit_breaker_enabled: bool = True


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataInstantiation:
    """Tests for ModelRoutingMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating metadata with all fields populated."""
        session_id = uuid4()
        metadata = ModelRoutingMetadata(
            target_region="us-east-1",
            preferred_instance="instance-abc123",
            load_balance_strategy="weighted",
            sticky_session_id=session_id,
            priority=10,
            weight=2.5,
            timeout_override_ms=5000,
            circuit_breaker_enabled=True,
        )

        assert metadata.target_region == "us-east-1"
        assert metadata.preferred_instance == "instance-abc123"
        assert metadata.load_balance_strategy == "weighted"
        assert metadata.sticky_session_id == session_id
        assert metadata.priority == 10
        assert metadata.weight == 2.5
        assert metadata.timeout_override_ms == 5000
        assert metadata.circuit_breaker_enabled is True

    def test_create_with_partial_fields(self) -> None:
        """Test creating metadata with only some fields."""
        metadata = ModelRoutingMetadata(
            target_region="eu-west-1",
            load_balance_strategy="least_connections",
        )

        assert metadata.target_region == "eu-west-1"
        assert metadata.load_balance_strategy == "least_connections"
        assert metadata.preferred_instance is None
        assert metadata.sticky_session_id is None
        assert metadata.priority == 0  # default
        assert metadata.weight == 1.0  # default

    def test_create_with_no_fields(self) -> None:
        """Test creating metadata with all defaults."""
        metadata = ModelRoutingMetadata()

        assert metadata.target_region is None
        assert metadata.preferred_instance is None
        assert metadata.load_balance_strategy == "round_robin"
        assert metadata.sticky_session_id is None
        assert metadata.priority == 0
        assert metadata.weight == 1.0
        assert metadata.timeout_override_ms is None
        assert metadata.circuit_breaker_enabled is True


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataDefaults:
    """Tests for ModelRoutingMetadata default values."""

    def test_load_balance_strategy_defaults_to_round_robin(self) -> None:
        """Test that load_balance_strategy defaults to 'round_robin'."""
        metadata = ModelRoutingMetadata()
        assert metadata.load_balance_strategy == "round_robin"

    def test_priority_defaults_to_0(self) -> None:
        """Test that priority defaults to 0."""
        metadata = ModelRoutingMetadata()
        assert metadata.priority == 0

    def test_weight_defaults_to_1(self) -> None:
        """Test that weight defaults to 1.0."""
        metadata = ModelRoutingMetadata()
        assert metadata.weight == 1.0

    def test_circuit_breaker_enabled_defaults_to_true(self) -> None:
        """Test that circuit_breaker_enabled defaults to True."""
        metadata = ModelRoutingMetadata()
        assert metadata.circuit_breaker_enabled is True

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        metadata = ModelRoutingMetadata()
        assert metadata.target_region is None
        assert metadata.preferred_instance is None
        assert metadata.sticky_session_id is None
        assert metadata.timeout_override_ms is None


# =============================================================================
# Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataValidation:
    """Tests for ModelRoutingMetadata field validation."""

    def test_load_balance_strategy_accepts_round_robin(self) -> None:
        """Test that load_balance_strategy accepts 'round_robin'."""
        metadata = ModelRoutingMetadata(load_balance_strategy="round_robin")
        assert metadata.load_balance_strategy == "round_robin"

    def test_load_balance_strategy_accepts_least_connections(self) -> None:
        """Test that load_balance_strategy accepts 'least_connections'."""
        metadata = ModelRoutingMetadata(load_balance_strategy="least_connections")
        assert metadata.load_balance_strategy == "least_connections"

    def test_load_balance_strategy_accepts_random(self) -> None:
        """Test that load_balance_strategy accepts 'random'."""
        metadata = ModelRoutingMetadata(load_balance_strategy="random")
        assert metadata.load_balance_strategy == "random"

    def test_load_balance_strategy_accepts_weighted(self) -> None:
        """Test that load_balance_strategy accepts 'weighted'."""
        metadata = ModelRoutingMetadata(load_balance_strategy="weighted")
        assert metadata.load_balance_strategy == "weighted"

    def test_load_balance_strategy_rejects_invalid_value(self) -> None:
        """Test that invalid load_balance_strategy values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(load_balance_strategy="invalid_strategy")
        assert "load_balance_strategy" in str(exc_info.value).lower()

    def test_load_balance_strategy_rejects_empty_string(self) -> None:
        """Test that empty string is rejected for load_balance_strategy."""
        with pytest.raises(ValidationError):
            ModelRoutingMetadata(load_balance_strategy="")

    def test_weight_minimum_is_0(self) -> None:
        """Test that weight minimum is 0.0."""
        metadata = ModelRoutingMetadata(weight=0.0)
        assert metadata.weight == 0.0

    def test_weight_maximum_is_100(self) -> None:
        """Test that weight maximum is 100.0."""
        metadata = ModelRoutingMetadata(weight=100.0)
        assert metadata.weight == 100.0

    def test_weight_rejects_below_0(self) -> None:
        """Test that weight below 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(weight=-0.1)
        assert "weight" in str(exc_info.value).lower()

    def test_weight_rejects_above_100(self) -> None:
        """Test that weight above 100.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(weight=100.1)
        assert "weight" in str(exc_info.value).lower()

    def test_weight_accepts_decimal_values(self) -> None:
        """Test that weight accepts decimal values."""
        metadata = ModelRoutingMetadata(weight=2.5)
        assert metadata.weight == 2.5

    def test_priority_accepts_negative_values(self) -> None:
        """Test that priority accepts negative values (lower priority)."""
        metadata = ModelRoutingMetadata(priority=-10)
        assert metadata.priority == -10

    def test_priority_accepts_positive_values(self) -> None:
        """Test that priority accepts positive values (higher priority)."""
        metadata = ModelRoutingMetadata(priority=100)
        assert metadata.priority == 100

    def test_sticky_session_id_accepts_valid_uuid(self) -> None:
        """Test that sticky_session_id accepts valid UUID."""
        session_id = uuid4()
        metadata = ModelRoutingMetadata(sticky_session_id=session_id)
        assert metadata.sticky_session_id == session_id

    def test_sticky_session_id_accepts_uuid_string(self) -> None:
        """Test that sticky_session_id accepts UUID as string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        metadata = ModelRoutingMetadata(sticky_session_id=uuid_str)  # type: ignore[arg-type]
        assert metadata.sticky_session_id == UUID(uuid_str)

    def test_timeout_override_ms_accepts_positive_value(self) -> None:
        """Test that timeout_override_ms accepts positive values."""
        metadata = ModelRoutingMetadata(timeout_override_ms=5000)
        assert metadata.timeout_override_ms == 5000

    def test_timeout_override_ms_rejects_zero(self) -> None:
        """Test that timeout_override_ms rejects zero (must be positive)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(timeout_override_ms=0)
        assert "timeout_override_ms" in str(exc_info.value).lower()

    def test_timeout_override_ms_rejects_negative(self) -> None:
        """Test that timeout_override_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(timeout_override_ms=-1)
        assert "timeout_override_ms" in str(exc_info.value).lower()


# =============================================================================
# Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataImmutability:
    """Tests for ModelRoutingMetadata immutability (frozen=True)."""

    def test_cannot_modify_target_region(self) -> None:
        """Test that target_region cannot be modified after creation."""
        metadata = ModelRoutingMetadata(target_region="us-east-1")
        with pytest.raises(ValidationError):
            metadata.target_region = "eu-west-1"  # type: ignore[misc]

    def test_cannot_modify_load_balance_strategy(self) -> None:
        """Test that load_balance_strategy cannot be modified after creation."""
        metadata = ModelRoutingMetadata(load_balance_strategy="round_robin")
        with pytest.raises(ValidationError):
            metadata.load_balance_strategy = "weighted"  # type: ignore[misc]

    def test_cannot_modify_weight(self) -> None:
        """Test that weight cannot be modified after creation."""
        metadata = ModelRoutingMetadata(weight=1.0)
        with pytest.raises(ValidationError):
            metadata.weight = 2.0  # type: ignore[misc]

    def test_cannot_modify_circuit_breaker_enabled(self) -> None:
        """Test that circuit_breaker_enabled cannot be modified after creation."""
        metadata = ModelRoutingMetadata(circuit_breaker_enabled=True)
        with pytest.raises(ValidationError):
            metadata.circuit_breaker_enabled = False  # type: ignore[misc]


# =============================================================================
# Extra Fields Forbidden Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataExtraForbid:
    """Tests for ModelRoutingMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRoutingMetadata(
                target_region="us-east-1",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# From Attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataFromAttributes:
    """Tests for ModelRoutingMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelRoutingMetadata from an object with attributes."""
        attrs = RoutingMetadataAttrs(
            target_region="ap-southeast-1",
            load_balance_strategy="weighted",
            weight=3.5,
        )
        metadata = ModelRoutingMetadata.model_validate(attrs)
        assert metadata.target_region == "ap-southeast-1"
        assert metadata.load_balance_strategy == "weighted"
        assert metadata.weight == 3.5

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        session_id = uuid4()
        attrs = RoutingMetadataAttrs(
            target_region="us-west-2",
            preferred_instance="instance-xyz",
            load_balance_strategy="least_connections",
            sticky_session_id=session_id,
            priority=5,
            weight=2.0,
            timeout_override_ms=3000,
            circuit_breaker_enabled=False,
        )
        metadata = ModelRoutingMetadata.model_validate(attrs)
        assert metadata.target_region == "us-west-2"
        assert metadata.preferred_instance == "instance-xyz"
        assert metadata.sticky_session_id == session_id
        assert metadata.circuit_breaker_enabled is False


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataSerialization:
    """Tests for ModelRoutingMetadata serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        session_id = uuid4()
        metadata = ModelRoutingMetadata(
            target_region="us-east-1",
            load_balance_strategy="weighted",
            sticky_session_id=session_id,
            weight=2.5,
        )

        data = metadata.model_dump()
        assert data["target_region"] == "us-east-1"
        assert data["load_balance_strategy"] == "weighted"
        assert data["sticky_session_id"] == session_id
        assert data["weight"] == 2.5

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        metadata = ModelRoutingMetadata(
            target_region="eu-west-1",
            load_balance_strategy="random",
        )

        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)
        assert "eu-west-1" in json_str
        assert "random" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "target_region": "us-west-2",
            "load_balance_strategy": "least_connections",
            "weight": 5.0,
            "circuit_breaker_enabled": False,
        }

        metadata = ModelRoutingMetadata.model_validate(data)
        assert metadata.target_region == "us-west-2"
        assert metadata.load_balance_strategy == "least_connections"
        assert metadata.weight == 5.0
        assert metadata.circuit_breaker_enabled is False

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelRoutingMetadata(
            target_region="ap-northeast-1",
            preferred_instance="instance-roundtrip",
            load_balance_strategy="weighted",
            sticky_session_id=uuid4(),
            priority=15,
            weight=4.5,
            timeout_override_ms=10000,
            circuit_breaker_enabled=True,
        )

        json_str = original.model_dump_json()
        restored = ModelRoutingMetadata.model_validate_json(json_str)

        assert restored == original


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_empty_string_target_region(self) -> None:
        """Test that empty string target_region is accepted."""
        metadata = ModelRoutingMetadata(target_region="")
        assert metadata.target_region == ""

    def test_empty_string_preferred_instance(self) -> None:
        """Test that empty string preferred_instance is accepted."""
        metadata = ModelRoutingMetadata(preferred_instance="")
        assert metadata.preferred_instance == ""

    def test_weight_boundary_values(self) -> None:
        """Test weight at boundary values."""
        # At 0
        meta_zero = ModelRoutingMetadata(weight=0.0)
        assert meta_zero.weight == 0.0

        # At 100
        meta_hundred = ModelRoutingMetadata(weight=100.0)
        assert meta_hundred.weight == 100.0

    def test_model_is_hashable(self) -> None:
        """Test that frozen model is hashable (for use in sets/dicts)."""
        metadata = ModelRoutingMetadata(
            target_region="us-east-1",
            load_balance_strategy="round_robin",
        )
        # Should be hashable (no exception raised)
        hash_value = hash(metadata)
        assert isinstance(hash_value, int)

    def test_equal_metadata_have_same_hash(self) -> None:
        """Test that equal metadata have the same hash."""
        meta1 = ModelRoutingMetadata(
            target_region="eu-west-1",
            load_balance_strategy="weighted",
            weight=2.5,
        )
        meta2 = ModelRoutingMetadata(
            target_region="eu-west-1",
            load_balance_strategy="weighted",
            weight=2.5,
        )

        assert meta1 == meta2
        assert hash(meta1) == hash(meta2)

    def test_different_metadata_are_not_equal(self) -> None:
        """Test that different metadata are not equal."""
        meta1 = ModelRoutingMetadata(load_balance_strategy="round_robin")
        meta2 = ModelRoutingMetadata(load_balance_strategy="weighted")

        assert meta1 != meta2

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update for creating modified copies."""
        original = ModelRoutingMetadata(
            target_region="us-east-1",
            load_balance_strategy="round_robin",
            weight=1.0,
        )

        modified = original.model_copy(
            update={"target_region": "eu-west-1", "weight": 5.0}
        )

        assert modified.target_region == "eu-west-1"
        assert modified.weight == 5.0
        assert modified.load_balance_strategy == "round_robin"  # unchanged
        assert original.target_region == "us-east-1"  # Original unchanged


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelRoutingMetadataIntegration:
    """Integration tests for ModelRoutingMetadata."""

    def test_model_config_is_correct(self) -> None:
        """Verify model configuration is correct."""
        config = ModelRoutingMetadata.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_can_be_used_in_dict(self) -> None:
        """Test that metadata can be stored in dictionary."""
        metadata = ModelRoutingMetadata(
            target_region="us-west-2",
            load_balance_strategy="weighted",
        )
        routing = {"primary": metadata}
        assert routing["primary"].target_region == "us-west-2"
        assert routing["primary"].load_balance_strategy == "weighted"

    def test_can_be_used_in_set(self) -> None:
        """Test that metadata can be stored in set (hashable)."""
        meta1 = ModelRoutingMetadata(target_region="us-east-1")
        meta2 = ModelRoutingMetadata(target_region="eu-west-1")
        meta3 = ModelRoutingMetadata(target_region="us-east-1")  # Same as meta1

        metadata_set = {meta1, meta2, meta3}
        assert len(metadata_set) == 2  # meta1 and meta3 are equal

    def test_valid_load_balance_strategies_constant(self) -> None:
        """Test that all valid strategies from the constant work."""
        # Import the constant
        from omnibase_core.models.context.model_routing_metadata import (
            VALID_LOAD_BALANCE_STRATEGIES,
        )

        for strategy in VALID_LOAD_BALANCE_STRATEGIES:
            metadata = ModelRoutingMetadata(load_balance_strategy=strategy)
            assert metadata.load_balance_strategy == strategy
