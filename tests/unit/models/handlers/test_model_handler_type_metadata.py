# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelHandlerTypeMetadata and related utilities.

Tests verify:
- ModelHandlerTypeMetadata model validation and fields
- get_handler_type_metadata factory function returns correct values for each category
- ProtocolHandlerTypeResolver protocol can be implemented
- Immutability and ONEX pattern compliance

Test Organization:
- TestModelHandlerTypeMetadata: Model field and validation tests
- TestGetHandlerTypeMetadata: Factory function tests
- TestProtocolHandlerTypeResolver: Protocol implementation tests
- TestONEXPatternCompliance: ONEX-specific pattern compliance tests

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- These are pure Pydantic validation tests with no I/O
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.models.handlers import (
    ModelHandlerTypeMetadata,
    get_handler_type_metadata,
)
from omnibase_core.protocols.handlers import ProtocolHandlerTypeResolver

# ---- Test ModelHandlerTypeMetadata Model ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelHandlerTypeMetadata:
    """Tests for ModelHandlerTypeMetadata model class."""

    def test_model_has_all_required_fields(self) -> None:
        """Test that model has all required fields defined."""
        fields = ModelHandlerTypeMetadata.model_fields
        assert "category" in fields
        assert "is_replay_safe" in fields
        assert "requires_secrets" in fields
        assert "is_deterministic" in fields
        assert "allows_caching" in fields
        assert "requires_idempotency_key" in fields

    def test_valid_construction_compute(self) -> None:
        """Test valid construction with COMPUTE category."""
        metadata = ModelHandlerTypeMetadata(
            category=EnumHandlerTypeCategory.COMPUTE,
            is_replay_safe=True,
            requires_secrets=False,
            is_deterministic=True,
            allows_caching=True,
            requires_idempotency_key=False,
        )
        assert metadata.category == EnumHandlerTypeCategory.COMPUTE
        assert metadata.is_replay_safe is True
        assert metadata.requires_secrets is False
        assert metadata.is_deterministic is True
        assert metadata.allows_caching is True
        assert metadata.requires_idempotency_key is False

    def test_valid_construction_effect(self) -> None:
        """Test valid construction with EFFECT category."""
        metadata = ModelHandlerTypeMetadata(
            category=EnumHandlerTypeCategory.EFFECT,
            is_replay_safe=False,
            requires_secrets=True,
            is_deterministic=False,
            allows_caching=False,
            requires_idempotency_key=True,
        )
        assert metadata.category == EnumHandlerTypeCategory.EFFECT
        assert metadata.is_replay_safe is False
        assert metadata.requires_secrets is True
        assert metadata.is_deterministic is False
        assert metadata.allows_caching is False
        assert metadata.requires_idempotency_key is True

    def test_valid_construction_nondeterministic_compute(self) -> None:
        """Test valid construction with NONDETERMINISTIC_COMPUTE category."""
        metadata = ModelHandlerTypeMetadata(
            category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            is_replay_safe=False,
            requires_secrets=False,
            is_deterministic=False,
            allows_caching=True,
            requires_idempotency_key=True,
        )
        assert metadata.category == EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        assert metadata.is_replay_safe is False
        assert metadata.requires_secrets is False
        assert metadata.is_deterministic is False
        assert metadata.allows_caching is True
        assert metadata.requires_idempotency_key is True

    def test_missing_required_field_raises_validation_error(self) -> None:
        """Test that missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerTypeMetadata(
                category=EnumHandlerTypeCategory.COMPUTE,
                # Missing: is_replay_safe, requires_secrets, etc.
            )  # type: ignore[call-arg]
        assert "is_replay_safe" in str(exc_info.value)

    def test_invalid_category_value_raises_error(self) -> None:
        """Test that invalid category value raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerTypeMetadata(
                category="invalid_category",  # type: ignore[arg-type]
                is_replay_safe=True,
                requires_secrets=False,
                is_deterministic=True,
                allows_caching=True,
                requires_idempotency_key=False,
            )

    def test_immutability(self) -> None:
        """Test that model is immutable (frozen)."""
        metadata = ModelHandlerTypeMetadata(
            category=EnumHandlerTypeCategory.COMPUTE,
            is_replay_safe=True,
            requires_secrets=False,
            is_deterministic=True,
            allows_caching=True,
            requires_idempotency_key=False,
        )
        with pytest.raises(ValidationError):
            metadata.is_replay_safe = False  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerTypeMetadata(
                category=EnumHandlerTypeCategory.COMPUTE,
                is_replay_safe=True,
                requires_secrets=False,
                is_deterministic=True,
                allows_caching=True,
                requires_idempotency_key=False,
                unknown_field="value",  # type: ignore[call-arg]
            )
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_category_string_coercion(self) -> None:
        """Test that category string value is coerced to enum."""
        metadata = ModelHandlerTypeMetadata(
            category="compute",  # type: ignore[arg-type]
            is_replay_safe=True,
            requires_secrets=False,
            is_deterministic=True,
            allows_caching=True,
            requires_idempotency_key=False,
        )
        assert metadata.category == EnumHandlerTypeCategory.COMPUTE

    def test_boolean_field_types(self) -> None:
        """Test that boolean fields reject non-coercible values."""
        # Pydantic coerces "true" to True, so we use a non-coercible type
        with pytest.raises(ValidationError):
            ModelHandlerTypeMetadata(
                category=EnumHandlerTypeCategory.COMPUTE,
                is_replay_safe=["not", "a", "bool"],  # type: ignore[arg-type]
                requires_secrets=False,
                is_deterministic=True,
                allows_caching=True,
                requires_idempotency_key=False,
            )


# ---- Test get_handler_type_metadata Factory ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestGetHandlerTypeMetadata:
    """Tests for get_handler_type_metadata factory function."""

    def test_compute_category_returns_correct_metadata(self) -> None:
        """Test COMPUTE category returns correct metadata values."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        assert metadata.category == EnumHandlerTypeCategory.COMPUTE
        assert metadata.is_replay_safe is True
        assert metadata.requires_secrets is False
        assert metadata.is_deterministic is True
        assert metadata.allows_caching is True
        assert metadata.requires_idempotency_key is False

    def test_effect_category_returns_correct_metadata(self) -> None:
        """Test EFFECT category returns correct metadata values."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        assert metadata.category == EnumHandlerTypeCategory.EFFECT
        assert metadata.is_replay_safe is False
        assert metadata.requires_secrets is True
        assert metadata.is_deterministic is False
        assert metadata.allows_caching is False
        assert metadata.requires_idempotency_key is True

    def test_nondeterministic_compute_category_returns_correct_metadata(self) -> None:
        """Test NONDETERMINISTIC_COMPUTE category returns correct metadata values."""
        metadata = get_handler_type_metadata(
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )
        assert metadata.category == EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        assert metadata.is_replay_safe is False
        assert metadata.requires_secrets is False
        assert metadata.is_deterministic is False
        assert metadata.allows_caching is True
        assert metadata.requires_idempotency_key is True

    def test_all_categories_have_metadata(self) -> None:
        """Test that all enum categories have corresponding metadata."""
        for category in EnumHandlerTypeCategory:
            metadata = get_handler_type_metadata(category)
            assert metadata is not None
            assert metadata.category == category

    def test_returns_same_instance_for_same_category(self) -> None:
        """Test that factory returns the same pre-defined instance."""
        metadata1 = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        metadata2 = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        # Should be the exact same object (pre-defined, not newly created)
        assert metadata1 is metadata2

    def test_compute_is_pure_and_deterministic(self) -> None:
        """Test COMPUTE characteristics: pure (no secrets) and deterministic."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        # COMPUTE handlers are pure functions
        assert metadata.is_deterministic is True
        assert metadata.requires_secrets is False
        # Can be safely replayed and cached
        assert metadata.is_replay_safe is True
        assert metadata.allows_caching is True
        # No idempotency key needed (same input = same output)
        assert metadata.requires_idempotency_key is False

    def test_effect_is_impure_with_side_effects(self) -> None:
        """Test EFFECT characteristics: impure (has I/O)."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        # EFFECT handlers interact with external systems
        assert metadata.requires_secrets is True
        assert metadata.is_deterministic is False
        # Cannot safely replay or cache
        assert metadata.is_replay_safe is False
        assert metadata.allows_caching is False
        # Needs idempotency key for replay safety
        assert metadata.requires_idempotency_key is True

    def test_nondeterministic_compute_is_pure_but_varies(self) -> None:
        """Test NONDETERMINISTIC_COMPUTE: pure (no I/O) but output varies."""
        metadata = get_handler_type_metadata(
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )
        # No external I/O
        assert metadata.requires_secrets is False
        # But output varies (e.g., random, time-based)
        assert metadata.is_deterministic is False
        # Cannot safely replay (output differs)
        assert metadata.is_replay_safe is False
        # Can cache with appropriate key (time window, seed, etc.)
        assert metadata.allows_caching is True
        # Needs idempotency key for replay tracking
        assert metadata.requires_idempotency_key is True


# ---- Test ProtocolHandlerTypeResolver Protocol ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolHandlerTypeResolver:
    """Tests for ProtocolHandlerTypeResolver protocol."""

    def test_protocol_can_be_implemented(self) -> None:
        """Test that protocol can be implemented by a mock class."""

        class MockResolver:
            """Mock implementation of ProtocolHandlerTypeResolver."""

            def resolve(self, handler: Any) -> EnumHandlerTypeCategory:
                """Resolve handler type based on handler attributes."""
                if hasattr(handler, "is_effect") and handler.is_effect:
                    return EnumHandlerTypeCategory.EFFECT
                return EnumHandlerTypeCategory.COMPUTE

            def get_metadata(
                self, category: EnumHandlerTypeCategory
            ) -> ModelHandlerTypeMetadata:
                """Get metadata for category."""
                return get_handler_type_metadata(category)

        resolver = MockResolver()

        # Test resolve method
        class EffectHandler:
            is_effect = True

        class ComputeHandler:
            is_effect = False

        assert resolver.resolve(EffectHandler()) == EnumHandlerTypeCategory.EFFECT
        assert resolver.resolve(ComputeHandler()) == EnumHandlerTypeCategory.COMPUTE

        # Test get_metadata method
        metadata = resolver.get_metadata(EnumHandlerTypeCategory.COMPUTE)
        assert metadata.category == EnumHandlerTypeCategory.COMPUTE
        assert metadata.is_replay_safe is True

    def test_protocol_has_required_methods(self) -> None:
        """Test that protocol defines required methods."""
        # Check protocol has resolve and get_metadata methods
        assert hasattr(ProtocolHandlerTypeResolver, "resolve")
        assert hasattr(ProtocolHandlerTypeResolver, "get_metadata")

    def test_protocol_implementation_typing(self) -> None:
        """Test that a properly typed implementation works."""

        class TypedResolver:
            """Fully typed implementation."""

            def resolve(self, handler: Any) -> EnumHandlerTypeCategory:
                return EnumHandlerTypeCategory.COMPUTE

            def get_metadata(
                self, category: EnumHandlerTypeCategory
            ) -> ModelHandlerTypeMetadata:
                return get_handler_type_metadata(category)

        # Create instance and verify it works
        resolver: ProtocolHandlerTypeResolver = TypedResolver()
        result = resolver.resolve(object())
        assert result == EnumHandlerTypeCategory.COMPUTE


# ---- Test ONEX Pattern Compliance ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestONEXPatternCompliance:
    """Tests for ONEX-specific pattern compliance."""

    def test_config_dict_frozen(self) -> None:
        """Test that ModelHandlerTypeMetadata is configured as frozen."""
        assert ModelHandlerTypeMetadata.model_config.get("frozen") is True

    def test_config_dict_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        assert ModelHandlerTypeMetadata.model_config.get("extra") == "forbid"

    def test_model_dump_produces_dict(self) -> None:
        """Test model_dump produces valid dictionary."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        data = metadata.model_dump()
        assert isinstance(data, dict)
        assert data["category"] == EnumHandlerTypeCategory.COMPUTE
        assert data["is_replay_safe"] is True

    def test_model_dump_json_mode(self) -> None:
        """Test model_dump with mode='json' produces serializable types."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        data = metadata.model_dump(mode="json")
        assert isinstance(data, dict)
        # Enum should be serialized as string
        assert data["category"] == "effect"
        assert isinstance(data["is_replay_safe"], bool)

    def test_model_validate_from_dict(self) -> None:
        """Test model can be validated from dictionary."""
        data = {
            "category": "compute",
            "is_replay_safe": True,
            "requires_secrets": False,
            "is_deterministic": True,
            "allows_caching": True,
            "requires_idempotency_key": False,
        }
        metadata = ModelHandlerTypeMetadata.model_validate(data)
        assert metadata.category == EnumHandlerTypeCategory.COMPUTE
        assert metadata.is_replay_safe is True

    def test_roundtrip_serialization(self) -> None:
        """Test model survives round-trip serialization."""
        original = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        data = original.model_dump(mode="json")
        restored = ModelHandlerTypeMetadata.model_validate(data)
        assert restored.category == original.category
        assert restored.is_replay_safe == original.is_replay_safe
        assert restored.requires_secrets == original.requires_secrets
        assert restored.is_deterministic == original.is_deterministic
        assert restored.allows_caching == original.allows_caching
        assert restored.requires_idempotency_key == original.requires_idempotency_key


# ---- Test Decision Matrix Consistency ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestDecisionMatrixConsistency:
    """Tests verifying the decision matrix from EnumHandlerTypeCategory docstring."""

    def test_compute_matrix_row(self) -> None:
        """Test COMPUTE: Pure=Yes, Deterministic=Yes."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        # Pure (no I/O) means: requires_secrets=False, is_deterministic=True
        assert metadata.requires_secrets is False
        assert metadata.is_deterministic is True

    def test_nondeterministic_compute_matrix_row(self) -> None:
        """Test NONDETERMINISTIC_COMPUTE: Pure=Yes, Deterministic=No."""
        metadata = get_handler_type_metadata(
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )
        # Pure (no I/O) means: requires_secrets=False
        assert metadata.requires_secrets is False
        # But not deterministic
        assert metadata.is_deterministic is False

    def test_effect_matrix_row(self) -> None:
        """Test EFFECT: Pure=No (has I/O)."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        # Not pure (has I/O) means: requires_secrets=True
        assert metadata.requires_secrets is True
        # Deterministic is N/A for EFFECT (we use False)
        assert metadata.is_deterministic is False

    def test_replay_safety_correlates_with_determinism(self) -> None:
        """Test replay safety correlates with determinism for pure handlers."""
        for category in EnumHandlerTypeCategory:
            metadata = get_handler_type_metadata(category)
            # For pure handlers (requires_secrets=False), replay safety should match determinism
            if not metadata.requires_secrets:
                # COMPUTE: deterministic=True, replay_safe=True
                # NONDETERMINISTIC_COMPUTE: deterministic=False, replay_safe=False
                if metadata.is_deterministic:
                    assert metadata.is_replay_safe is True
                else:
                    assert metadata.is_replay_safe is False

    def test_caching_allowed_for_non_effect_handlers(self) -> None:
        """Test that non-EFFECT handlers allow caching."""
        compute_meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        nondet_meta = get_handler_type_metadata(
            EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )
        effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)

        assert compute_meta.allows_caching is True
        assert nondet_meta.allows_caching is True
        assert effect_meta.allows_caching is False

    def test_idempotency_key_required_for_non_deterministic(self) -> None:
        """Test idempotency key required for non-deterministic handlers."""
        for category in EnumHandlerTypeCategory:
            metadata = get_handler_type_metadata(category)
            if not metadata.is_deterministic:
                # Non-deterministic handlers need idempotency key
                assert metadata.requires_idempotency_key is True
            else:
                # Deterministic handlers don't need it
                assert metadata.requires_idempotency_key is False


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_equality_of_metadata_instances(self) -> None:
        """Test equality comparison of metadata instances."""
        meta1 = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        meta2 = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        # Same pre-defined instance
        assert meta1 is meta2
        # Also equal by value
        assert meta1 == meta2

    def test_inequality_of_different_categories(self) -> None:
        """Test inequality of metadata for different categories."""
        compute_meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        assert compute_meta != effect_meta

    def test_hash_consistency(self) -> None:
        """Test that frozen model is hashable."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        # Frozen Pydantic models should be hashable
        hash_value = hash(metadata)
        assert isinstance(hash_value, int)

    def test_metadata_in_set(self) -> None:
        """Test metadata can be used in a set."""
        compute_meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        metadata_set = {compute_meta, effect_meta}
        assert len(metadata_set) == 2
        assert compute_meta in metadata_set

    def test_metadata_as_dict_key(self) -> None:
        """Test metadata can be used as dictionary key."""
        compute_meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        lookup = {compute_meta: "compute", effect_meta: "effect"}
        assert lookup[compute_meta] == "compute"
        assert lookup[effect_meta] == "effect"

    def test_repr_contains_useful_info(self) -> None:
        """Test repr contains useful debugging information."""
        metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        repr_str = repr(metadata)
        assert "ModelHandlerTypeMetadata" in repr_str
        assert "COMPUTE" in repr_str or "compute" in repr_str
