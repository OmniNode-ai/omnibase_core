# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelRequirementSet."""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet


@pytest.mark.unit
class TestModelRequirementSetInstantiation:
    """Tests for ModelRequirementSet instantiation."""

    def test_default_instantiation_creates_empty_requirements(self) -> None:
        """Test that default instantiation creates empty dicts."""
        reqs = ModelRequirementSet()
        assert reqs.must == {}
        assert reqs.prefer == {}
        assert reqs.forbid == {}
        assert reqs.hints == {}

    def test_instantiation_with_must_only(self) -> None:
        """Test creating requirements with only must constraints."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.must == {"key": "value"}
        assert reqs.prefer == {}
        assert reqs.forbid == {}
        assert reqs.hints == {}

    def test_instantiation_with_all_tiers(self) -> None:
        """Test creating requirements with all constraint tiers."""
        reqs = ModelRequirementSet(
            must={"required": True},
            prefer={"fast": True},
            forbid={"deprecated": True},
            hints={"vendor": ["a", "b"]},
        )
        assert reqs.must == {"required": True}
        assert reqs.prefer == {"fast": True}
        assert reqs.forbid == {"deprecated": True}
        assert reqs.hints == {"vendor": ["a", "b"]}

    def test_instantiation_with_complex_values(self) -> None:
        """Test creating requirements with complex nested values."""
        reqs = ModelRequirementSet(
            must={"features": ["tx", "encryption"], "version": {"min": 14}},
            prefer={"latency": {"max_ms": 20, "p99_ms": 50}},
        )
        assert reqs.must["features"] == ["tx", "encryption"]
        assert reqs.must["version"]["min"] == 14
        assert reqs.prefer["latency"]["max_ms"] == 20


@pytest.mark.unit
class TestModelRequirementSetProperties:
    """Tests for ModelRequirementSet properties."""

    def test_is_empty_true_for_default(self) -> None:
        """Test is_empty returns True for default requirements."""
        assert ModelRequirementSet().is_empty is True

    def test_is_empty_false_with_must(self) -> None:
        """Test is_empty returns False when must is populated."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_prefer(self) -> None:
        """Test is_empty returns False when prefer is populated."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_forbid(self) -> None:
        """Test is_empty returns False when forbid is populated."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_hints(self) -> None:
        """Test is_empty returns False when hints is populated."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        assert reqs.is_empty is False

    def test_has_hard_constraints_false_for_empty(self) -> None:
        """Test has_hard_constraints returns False when empty."""
        assert ModelRequirementSet().has_hard_constraints is False

    def test_has_hard_constraints_true_with_must(self) -> None:
        """Test has_hard_constraints returns True with must."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.has_hard_constraints is True

    def test_has_hard_constraints_true_with_forbid(self) -> None:
        """Test has_hard_constraints returns True with forbid."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        assert reqs.has_hard_constraints is True

    def test_has_hard_constraints_false_with_only_soft(self) -> None:
        """Test has_hard_constraints returns False with only prefer/hints."""
        reqs = ModelRequirementSet(prefer={"a": 1}, hints={"b": 2})
        assert reqs.has_hard_constraints is False

    def test_has_soft_constraints_false_for_empty(self) -> None:
        """Test has_soft_constraints returns False when empty."""
        assert ModelRequirementSet().has_soft_constraints is False

    def test_has_soft_constraints_true_with_prefer(self) -> None:
        """Test has_soft_constraints returns True with prefer."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        assert reqs.has_soft_constraints is True

    def test_has_soft_constraints_true_with_hints(self) -> None:
        """Test has_soft_constraints returns True with hints."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        assert reqs.has_soft_constraints is True

    def test_has_soft_constraints_false_with_only_hard(self) -> None:
        """Test has_soft_constraints returns False with only must/forbid."""
        reqs = ModelRequirementSet(must={"a": 1}, forbid={"b": 2})
        assert reqs.has_soft_constraints is False


@pytest.mark.unit
class TestModelRequirementSetMerge:
    """Tests for ModelRequirementSet.merge() method."""

    def test_merge_empty_with_empty(self) -> None:
        """Test merging two empty requirement sets."""
        a = ModelRequirementSet()
        b = ModelRequirementSet()
        merged = a.merge(b)
        assert merged.is_empty

    def test_merge_adds_new_keys(self) -> None:
        """Test merge adds keys from other."""
        a = ModelRequirementSet(must={"a": 1})
        b = ModelRequirementSet(must={"b": 2})
        merged = a.merge(b)
        assert merged.must == {"a": 1, "b": 2}

    def test_merge_other_takes_precedence(self) -> None:
        """Test merge uses other's values for conflicts."""
        a = ModelRequirementSet(must={"key": "original"})
        b = ModelRequirementSet(must={"key": "override"})
        merged = a.merge(b)
        assert merged.must == {"key": "override"}

    def test_merge_all_tiers(self) -> None:
        """Test merge works across all tiers."""
        a = ModelRequirementSet(
            must={"a": 1},
            prefer={"b": 2},
            forbid={"c": 3},
            hints={"d": 4},
        )
        b = ModelRequirementSet(
            must={"e": 5},
            prefer={"f": 6},
            forbid={"g": 7},
            hints={"h": 8},
        )
        merged = a.merge(b)
        assert merged.must == {"a": 1, "e": 5}
        assert merged.prefer == {"b": 2, "f": 6}
        assert merged.forbid == {"c": 3, "g": 7}
        assert merged.hints == {"d": 4, "h": 8}

    def test_merge_returns_new_instance(self) -> None:
        """Test merge returns new instance, doesn't modify originals."""
        a = ModelRequirementSet(must={"key": "a"})
        b = ModelRequirementSet(must={"key": "b"})
        merged = a.merge(b)
        assert a.must == {"key": "a"}  # Original unchanged
        assert b.must == {"key": "b"}  # Original unchanged
        assert merged.must == {"key": "b"}

    def test_merge_shallow_replaces_nested_dicts(self) -> None:
        """Test that merge performs SHALLOW merge - nested dicts are replaced entirely.

        This test codifies the documented warning in merge() that nested dictionaries
        are NOT recursively merged. The entire nested dict is replaced by other's value.
        """
        base = ModelRequirementSet(
            must={"config": {"timeout": 30, "retries": 3, "host": "localhost"}}
        )
        override = ModelRequirementSet(
            must={"config": {"timeout": 60}}  # Only has timeout, missing retries/host
        )
        merged = base.merge(override)

        # IMPORTANT: This demonstrates shallow merge - "retries" and "host" are LOST
        # because the entire "config" dict is replaced, not recursively merged
        assert merged.must == {"config": {"timeout": 60}}
        config = merged.must.get("config", {})
        assert isinstance(config, dict)
        assert "retries" not in config
        assert "host" not in config

    def test_merge_shallow_exact_example(self) -> None:
        """Test shallow merge with exact example: {a: {b: 1}} + {a: {c: 2}} = {a: {c: 2}}.

        This explicitly tests the documented warning that nested dicts are replaced,
        not deep-merged. This is the canonical example from the PR review.
        """
        # Base has nested dict with key 'b'
        base = ModelRequirementSet(must={"a": {"b": 1}})
        # Override has nested dict with DIFFERENT key 'c'
        override = ModelRequirementSet(must={"a": {"c": 2}})

        merged = base.merge(override)

        # Shallow merge: entire nested dict is REPLACED
        # Result is {a: {c: 2}}, NOT {a: {b: 1, c: 2}}
        assert merged.must == {"a": {"c": 2}}

        # Explicitly verify 'b' is NOT present (shallow, not deep merge)
        nested = merged.must.get("a", {})
        assert isinstance(nested, dict)
        assert "b" not in nested, (
            "Shallow merge should replace nested dict, not merge keys"
        )
        assert nested.get("c") == 2

    def test_merge_shallow_lists_are_replaced_not_concatenated(self) -> None:
        """Test that list values are replaced, not concatenated.

        The merge warning also applies to lists - they are replaced entirely,
        not merged or concatenated.
        """
        base = ModelRequirementSet(hints={"vendors": ["postgres", "mysql"]})
        override = ModelRequirementSet(hints={"vendors": ["redis"]})

        merged = base.merge(override)

        # List is REPLACED, not concatenated
        assert merged.hints == {"vendors": ["redis"]}
        # Verify postgres and mysql are gone
        vendors = merged.hints.get("vendors", [])
        assert isinstance(vendors, list)
        assert "postgres" not in vendors
        assert "mysql" not in vendors
        assert len(vendors) == 1

    def test_merge_shallow_prefer_tier_nested_dicts(self) -> None:
        """Test shallow merge on prefer tier with nested dicts.

        Ensures shallow merge behavior is consistent across all tiers (must,
        prefer, forbid, hints). The prefer tier may contain complex scoring
        criteria that should be fully replaced, not deep-merged.
        """
        base = ModelRequirementSet(
            prefer={
                "latency_config": {"p50_ms": 10, "p99_ms": 50, "timeout_ms": 100},
                "region": "us-east-1",
            }
        )
        override = ModelRequirementSet(
            prefer={
                "latency_config": {
                    "p50_ms": 5
                },  # Only p50_ms, missing p99_ms/timeout_ms
            }
        )

        merged = base.merge(override)

        # Shallow merge: "latency_config" is entirely replaced
        assert merged.prefer["latency_config"] == {"p50_ms": 5}

        # p99_ms and timeout_ms are LOST (shallow, not deep merge)
        config = merged.prefer.get("latency_config", {})
        assert isinstance(config, dict)
        assert "p99_ms" not in config
        assert "timeout_ms" not in config

        # region is preserved (different key, not overridden)
        assert merged.prefer.get("region") == "us-east-1"

    def test_merge_shallow_forbid_tier_nested_dicts(self) -> None:
        """Test shallow merge on forbid tier with nested dicts.

        Ensures shallow merge behavior is consistent across the forbid tier.
        Forbid constraints might use nested dicts for complex exclusion rules.
        """
        base = ModelRequirementSet(
            forbid={
                "network_policy": {"public_internet": True, "cross_region": True},
            }
        )
        override = ModelRequirementSet(
            forbid={
                "network_policy": {"cross_az": True},  # Different nested key
            }
        )

        merged = base.merge(override)

        # Shallow merge: entire "network_policy" dict is replaced
        assert merged.forbid["network_policy"] == {"cross_az": True}

        # public_internet and cross_region are LOST
        policy = merged.forbid.get("network_policy", {})
        assert isinstance(policy, dict)
        assert "public_internet" not in policy
        assert "cross_region" not in policy

    def test_merge_shallow_all_tiers_comprehensive(self) -> None:
        """Comprehensive test of shallow merge across all four tiers.

        This test verifies that shallow merge behavior is consistent and
        intentional across must, prefer, forbid, and hints tiers.
        Documents the behavior as intentional rather than a bug.
        """
        base = ModelRequirementSet(
            must={"config": {"a": 1, "b": 2}},
            prefer={"scoring": {"weight": 0.5, "threshold": 0.8}},
            forbid={"exclusions": {"x": True, "y": True}},
            hints={"advice": {"primary": "postgres", "fallback": "mysql"}},
        )
        override = ModelRequirementSet(
            must={"config": {"c": 3}},
            prefer={"scoring": {"weight": 0.9}},
            forbid={"exclusions": {"z": True}},
            hints={"advice": {"tertiary": "sqlite"}},
        )

        merged = base.merge(override)

        # All tiers should have shallow merge behavior
        # must: {a, b} replaced by {c}
        assert merged.must == {"config": {"c": 3}}
        must_config = merged.must.get("config", {})
        assert isinstance(must_config, dict)
        assert "a" not in must_config
        assert "b" not in must_config

        # prefer: {weight, threshold} replaced by {weight}
        assert merged.prefer == {"scoring": {"weight": 0.9}}
        prefer_scoring = merged.prefer.get("scoring", {})
        assert isinstance(prefer_scoring, dict)
        assert "threshold" not in prefer_scoring

        # forbid: {x, y} replaced by {z}
        assert merged.forbid == {"exclusions": {"z": True}}
        forbid_exclusions = merged.forbid.get("exclusions", {})
        assert isinstance(forbid_exclusions, dict)
        assert "x" not in forbid_exclusions
        assert "y" not in forbid_exclusions

        # hints: {primary, fallback} replaced by {tertiary}
        assert merged.hints == {"advice": {"tertiary": "sqlite"}}
        hints_advice = merged.hints.get("advice", {})
        assert isinstance(hints_advice, dict)
        assert "primary" not in hints_advice
        assert "fallback" not in hints_advice


@pytest.mark.unit
class TestModelRequirementSetImmutability:
    """Tests for ModelRequirementSet frozen immutability."""

    def test_frozen_immutability_must(self) -> None:
        """Test that must cannot be reassigned."""
        reqs = ModelRequirementSet(must={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.must = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_prefer(self) -> None:
        """Test that prefer cannot be reassigned."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.prefer = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_forbid(self) -> None:
        """Test that forbid cannot be reassigned."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.forbid = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_hints(self) -> None:
        """Test that hints cannot be reassigned."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.hints = {"new": "dict"}  # type: ignore[misc]


@pytest.mark.unit
class TestModelRequirementSetExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelRequirementSet(
                must={"key": "value"},
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelRequirementSetRepr:
    """Tests for ModelRequirementSet string representation."""

    def test_repr_empty(self) -> None:
        """Test repr for empty requirements."""
        reqs = ModelRequirementSet()
        assert repr(reqs) == "ModelRequirementSet()"

    def test_repr_with_must_only(self) -> None:
        """Test repr with only must."""
        reqs = ModelRequirementSet(must={"key": "value"})
        repr_str = repr(reqs)
        assert "ModelRequirementSet" in repr_str
        assert "must=" in repr_str
        assert "prefer=" not in repr_str

    def test_repr_with_all_tiers(self) -> None:
        """Test repr with all tiers."""
        reqs = ModelRequirementSet(
            must={"a": 1},
            prefer={"b": 2},
            forbid={"c": 3},
            hints={"d": 4},
        )
        repr_str = repr(reqs)
        assert "must=" in repr_str
        assert "prefer=" in repr_str
        assert "forbid=" in repr_str
        assert "hints=" in repr_str


@pytest.mark.unit
class TestModelRequirementSetEquality:
    """Tests for ModelRequirementSet equality.

    Note: Hashability tests have been consolidated into
    TestCapabilityModelsHashability at the end of this file for
    cross-model parametrized testing.
    """

    def test_equality_same_requirements(self) -> None:
        """Test equality for identical requirements."""
        reqs1 = ModelRequirementSet(must={"a": 1}, prefer={"b": 2})
        reqs2 = ModelRequirementSet(must={"a": 1}, prefer={"b": 2})
        assert reqs1 == reqs2

    def test_inequality_different_requirements(self) -> None:
        """Test inequality for different requirements."""
        reqs1 = ModelRequirementSet(must={"a": 1})
        reqs2 = ModelRequirementSet(must={"a": 2})
        assert reqs1 != reqs2


# =============================================================================
# Consolidated Hashability Tests (Cross-Model Parametrized)
# =============================================================================


def _create_model_requirement_set() -> ModelRequirementSet:
    """Factory for ModelRequirementSet test instance."""
    return ModelRequirementSet(must={"key": "value"})


def _create_model_capability_dependency() -> ModelCapabilityDependency:
    """Factory for ModelCapabilityDependency test instance."""
    return ModelCapabilityDependency(alias="db", capability="database.relational")


@pytest.mark.unit
class TestCapabilityModelsHashability:
    """Consolidated tests for hashability behavior across capability models.

    This class uses pytest.mark.parametrize to test hashability behavior
    consistently across all capability models that contain dict fields.
    Models with dict[str, Any] fields are frozen (immutable) but NOT hashable
    because dicts are mutable and thus unhashable.

    This consolidation:
    - Reduces code duplication across model-specific test files
    - Ensures consistent testing of this critical behavior
    - Makes it easy to add new models to the test suite

    Note: Individual model test files may retain their own hashability tests
    for backwards compatibility, but this parametrized test is the canonical
    source for cross-model hashability verification.
    """

    @pytest.mark.parametrize(
        ("model_factory", "model_name"),
        [
            pytest.param(
                _create_model_requirement_set,
                "ModelRequirementSet",
                id="ModelRequirementSet",
            ),
            pytest.param(
                _create_model_capability_dependency,
                "ModelCapabilityDependency",
                id="ModelCapabilityDependency",
            ),
        ],
    )
    def test_models_with_dict_fields_are_not_hashable(
        self,
        model_factory: Any,
        model_name: str,
    ) -> None:
        """Test that capability models with dict fields are NOT hashable.

        Pydantic models with frozen=True are immutable but this does NOT make
        them hashable if they contain dict fields. This is because:
        - Python's hash() requires all nested values to be hashable
        - dict is inherently unhashable (mutable mapping)
        - The frozen=True config only prevents attribute reassignment

        This test verifies all unhashability scenarios:
        - Direct hash() call raises TypeError
        - Cannot be used in sets (sets require hashable elements)
        - Cannot be used as dict keys (keys must be hashable)

        Args:
            model_factory: Callable that creates a test instance of the model.
            model_name: Name of the model for error messages.
        """
        instance = model_factory()

        # Direct hash() call should fail
        with pytest.raises(TypeError, match="unhashable"):
            hash(instance)

        # Cannot add to set (sets use hashing internally)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {instance}

        # Cannot use as dict key (dict keys must be hashable)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {instance: "value"}
