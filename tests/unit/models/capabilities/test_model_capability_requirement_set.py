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
from omnibase_core.models.capabilities.model_capability_requirement_set import (
    ModelRequirementSet,
    is_json_primitive,
    is_requirement_dict,
    is_requirement_list,
    is_requirement_value,
)


@pytest.mark.unit
class TestModelRequirementSetJSONSerializability:
    """Tests for JSON-serializability validation.

    These tests verify that the validate_json_serializable model validator
    correctly rejects non-JSON-serializable values at construction time,
    providing helpful error messages with examples.
    """

    def test_valid_primitive_values_accepted(self) -> None:
        """Test that all JSON primitive types are accepted."""
        reqs = ModelRequirementSet(
            must={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
            }
        )
        assert reqs.must["string"] == "value"
        assert reqs.must["int"] == 42
        assert reqs.must["float"] == 3.14
        assert reqs.must["bool"] is True
        assert reqs.must["null"] is None

    def test_valid_nested_structures_accepted(self) -> None:
        """Test that nested JSON-compatible structures are accepted."""
        reqs = ModelRequirementSet(
            must={
                "nested_dict": {"a": 1, "b": {"c": 2}},
                "nested_list": [1, [2, 3], {"d": 4}],
            }
        )
        assert reqs.must["nested_dict"]["b"]["c"] == 2
        assert reqs.must["nested_list"][1] == [2, 3]

    def test_set_rejected_in_must(self) -> None:
        """Test that set values are rejected with helpful error message."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(must={"invalid": {1, 2, 3}})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "must" in error_msg
        assert "JSON-serializable" in error_msg
        assert "set" in error_msg.lower()

    def test_set_rejected_in_prefer(self) -> None:
        """Test that set values are rejected in prefer tier."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(prefer={"invalid": {"a", "b"}})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "prefer" in error_msg
        assert "JSON-serializable" in error_msg

    def test_set_rejected_in_forbid(self) -> None:
        """Test that set values are rejected in forbid tier."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(forbid={"invalid": frozenset([1, 2])})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "forbid" in error_msg
        assert "JSON-serializable" in error_msg

    def test_set_rejected_in_hints(self) -> None:
        """Test that set values are rejected in hints tier."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(hints={"invalid": {1, 2, 3}})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "hints" in error_msg
        assert "JSON-serializable" in error_msg

    def test_lambda_rejected(self) -> None:
        """Test that lambda/function values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(must={"invalid": lambda x: x})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "JSON-serializable" in error_msg

    def test_custom_object_rejected(self) -> None:
        """Test that custom objects without JSON support are rejected."""

        class CustomObject:
            pass

        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(must={"invalid": CustomObject()})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        assert "JSON-serializable" in error_msg

    def test_deeply_nested_set_rejected(self) -> None:
        """Test that sets nested deep in structures are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(
                must={"level1": {"level2": {"level3": {1, 2, 3}}}}  # type: ignore[dict-item]
            )

        error_msg = str(exc_info.value)
        assert "JSON-serializable" in error_msg

    def test_error_message_includes_example(self) -> None:
        """Test that error message includes helpful example of valid value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(must={"invalid": {1, 2, 3}})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        # Should include example of valid format
        assert "Example valid value" in error_msg or "key" in error_msg

    def test_error_message_mentions_allowed_types(self) -> None:
        """Test that error message mentions allowed types."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequirementSet(must={"invalid": {1, 2, 3}})  # type: ignore[dict-item]

        error_msg = str(exc_info.value)
        # Should mention allowed primitives
        assert (
            "str" in error_msg
            or "int" in error_msg
            or "primitives" in error_msg.lower()
        )


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

    This class tests hashability behavior for capability models:

    **Unhashable models** (contain dict fields directly):
    - ModelRequirementSet: Has must/prefer/forbid/hints dict fields

    **Hashable models** (custom __hash__ based on identity fields):
    - ModelCapabilityDependency: Hash based on (capability, alias) only

    Note: ModelCapabilityDependency contains ModelRequirementSet (which has dicts)
    but implements a custom __hash__ using only immutable identity fields
    (capability, alias), making it safely hashable.
    """

    def test_model_requirement_set_not_hashable(self) -> None:
        """Test that ModelRequirementSet with dict fields is NOT hashable.

        Pydantic models with frozen=True are immutable but this does NOT make
        them hashable if they contain dict fields. This is because:
        - Python's hash() requires all nested values to be hashable
        - dict is inherently unhashable (mutable mapping)
        - The frozen=True config only prevents attribute reassignment

        This test verifies all unhashability scenarios:
        - Direct hash() call raises TypeError
        - Cannot be used in sets (sets require hashable elements)
        - Cannot be used as dict keys (keys must be hashable)
        """
        instance = _create_model_requirement_set()

        # Direct hash() call should fail
        with pytest.raises(TypeError, match="unhashable"):
            hash(instance)

        # Cannot add to set (sets use hashing internally)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {instance}

        # Cannot use as dict key (dict keys must be hashable)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {instance: "value"}

    def test_model_capability_dependency_is_hashable(self) -> None:
        """Test that ModelCapabilityDependency IS hashable via custom __hash__.

        ModelCapabilityDependency implements __hash__ based on identity fields
        (capability, alias), enabling:
        - Use in sets for dependency deduplication
        - Use as dict keys for caching resolution results

        The hash is computed from immutable string fields only, making it
        stable and safe despite containing ModelRequirementSet (unhashable).
        """
        instance = _create_model_capability_dependency()

        # Direct hash() call should succeed
        h = hash(instance)
        assert isinstance(h, int)

        # Can add to set
        s = {instance}
        assert len(s) == 1

        # Can use as dict key
        d = {instance: "value"}
        assert d[instance] == "value"

    def test_model_capability_dependency_hash_contract(self) -> None:
        """Test that equal ModelCapabilityDependency objects have equal hashes.

        This verifies the hash contract: equal objects must have equal hashes.
        """
        dep1 = _create_model_capability_dependency()
        dep2 = _create_model_capability_dependency()

        assert dep1 == dep2
        assert hash(dep1) == hash(dep2)


# =============================================================================
# Selection Policy Semantics Tests (Cross-Reference with ModelCapabilityDependency)
# =============================================================================


@pytest.mark.unit
class TestSelectionPolicyWithRequirements:
    """Tests documenting how ModelRequirementSet influences selection policy behavior.

    These tests demonstrate the interaction between RequirementSet constraints
    (must/prefer/forbid/hints) and selection policy semantics. While the selection
    policy is defined on ModelCapabilityDependency, the RequirementSet provides
    the filtering and scoring criteria.

    See ModelCapabilityDependency docstring for policy definitions.
    See also: tests/unit/models/capabilities/test_model_capability_dependency.py
    for additional policy-focused tests.
    """

    def test_auto_if_unique_rejects_multiple_matches(self) -> None:
        """Test that auto_if_unique rejects when multiple providers match requirements.

        Contract: When selection_policy='auto_if_unique', automatic selection
        should FAIL if more than one provider satisfies the 'must' constraints.
        The resolver should return an error or ambiguous status.

        This is a CRITICAL behavior test - auto_if_unique exists to prevent
        accidental resolution when multiple valid options exist.
        """
        # Requirements that multiple providers could satisfy
        requirements = ModelRequirementSet(
            must={"supports_transactions": True},
            prefer={"latency_ms": 10},
        )

        # Simulate multiple providers matching the 'must' constraint
        matching_providers = [
            {"name": "postgres", "supports_transactions": True, "latency_ms": 15},
            {"name": "mysql", "supports_transactions": True, "latency_ms": 20},
            {"name": "mariadb", "supports_transactions": True, "latency_ms": 12},
        ]

        # Filter by must constraints
        def filter_by_must(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> list[dict[str, Any]]:
            return [
                p for p in providers if all(p.get(k) == v for k, v in reqs.must.items())
            ]

        # auto_if_unique resolution logic
        def resolve_auto_if_unique(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> dict[str, Any] | None:
            """Resolve using auto_if_unique policy: only select if exactly one matches."""
            filtered = filter_by_must(providers, reqs)
            if len(filtered) == 1:
                return filtered[0]
            return None  # Reject: zero or multiple matches

        # CRITICAL: With 3 matching providers, auto_if_unique MUST reject
        result = resolve_auto_if_unique(matching_providers, requirements)
        assert result is None, (
            "auto_if_unique MUST reject when multiple providers match 'must' constraints. "
            "This prevents accidental selection when the dependency is ambiguous."
        )

        # Verify 3 providers actually match
        filtered = filter_by_must(matching_providers, requirements)
        assert len(filtered) == 3, "All 3 providers should match 'must' constraints"

    def test_auto_if_unique_accepts_single_match(self) -> None:
        """Test that auto_if_unique accepts when exactly one provider matches.

        Contract: When exactly one provider satisfies 'must' constraints,
        auto_if_unique should automatically select it.
        """
        # Requirements that only one provider satisfies
        requirements = ModelRequirementSet(
            must={"supports_transactions": True, "supports_jsonb": True},
        )

        providers = [
            {"name": "postgres", "supports_transactions": True, "supports_jsonb": True},
            {"name": "mysql", "supports_transactions": True, "supports_jsonb": False},
            {"name": "sqlite", "supports_transactions": False, "supports_jsonb": False},
        ]

        def resolve_auto_if_unique(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> dict[str, Any] | None:
            filtered = [
                p for p in providers if all(p.get(k) == v for k, v in reqs.must.items())
            ]
            if len(filtered) == 1:
                return filtered[0]
            return None

        # With exactly one match, auto_if_unique should select
        result = resolve_auto_if_unique(providers, requirements)
        assert result is not None, "auto_if_unique should select single match"
        assert result["name"] == "postgres"

    def test_best_score_selects_highest_scoring_provider(self) -> None:
        """Test that best_score selects provider with highest preference score.

        Contract: When selection_policy='best_score':
        1. Filter providers by 'must' constraints
        2. Score remaining providers by 'prefer' constraints (each match = +1)
        3. Select provider with highest score
        """
        requirements = ModelRequirementSet(
            must={"distributed": True},
            prefer={"region": "us-east-1", "latency_ms": 10, "encryption": True},
        )

        providers = [
            {
                "name": "redis_west",
                "distributed": True,
                "region": "us-west-2",
                "latency_ms": 20,
                "encryption": True,
            },  # Score: 1 (encryption)
            {
                "name": "redis_east",
                "distributed": True,
                "region": "us-east-1",
                "latency_ms": 15,
                "encryption": True,
            },  # Score: 2 (region, encryption)
            {
                "name": "memcached",
                "distributed": True,
                "region": "us-east-1",
                "latency_ms": 10,
                "encryption": True,
            },  # Score: 3 (region, latency_ms, encryption) - HIGHEST
        ]

        def resolve_best_score(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> dict[str, Any] | None:
            """Resolve using best_score policy: select highest-scoring provider."""
            # Filter by must constraints
            filtered = [
                p for p in providers if all(p.get(k) == v for k, v in reqs.must.items())
            ]
            if not filtered:
                return None

            # Score by prefer constraints
            def score_provider(p: dict[str, Any]) -> float:
                return sum(
                    1.0
                    for key, preferred in reqs.prefer.items()
                    if p.get(key) == preferred
                )

            # Select highest-scoring
            return max(filtered, key=score_provider)

        result = resolve_best_score(providers, requirements)
        assert result is not None, "best_score should select a provider"
        assert result["name"] == "memcached", (
            "best_score MUST select provider with highest preference score. "
            "memcached matches all 3 'prefer' constraints (score=3), "
            "redis_east matches 2, redis_west matches 1."
        )

    def test_best_score_uses_hints_for_tie_breaking(self) -> None:
        """Test that best_score uses hints to break ties between equal scores.

        Contract: When multiple providers have the same 'prefer' score,
        the resolver should use 'hints' as advisory tie-breakers.
        """
        requirements = ModelRequirementSet(
            must={"distributed": True},
            prefer={"region": "us-east-1"},
            hints={"vendor_preference": ["redis", "memcached", "hazelcast"]},
        )

        # Two providers with EQUAL preference scores (both match region)
        providers = [
            {
                "name": "memcached",
                "distributed": True,
                "region": "us-east-1",
            },  # Score: 1
            {"name": "redis", "distributed": True, "region": "us-east-1"},  # Score: 1
        ]

        def resolve_best_score_with_hints(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> dict[str, Any] | None:
            filtered = [
                p for p in providers if all(p.get(k) == v for k, v in reqs.must.items())
            ]
            if not filtered:
                return None

            def score_provider(p: dict[str, Any]) -> float:
                return sum(1.0 for k, v in reqs.prefer.items() if p.get(k) == v)

            max_score = max(score_provider(p) for p in filtered)
            tied = [p for p in filtered if score_provider(p) == max_score]

            if len(tied) == 1:
                return tied[0]

            # Break ties using hints
            vendor_pref = reqs.hints.get("vendor_preference", [])
            if isinstance(vendor_pref, list):
                for preferred in vendor_pref:
                    for p in tied:
                        if p.get("name") == preferred:
                            return p
            return tied[0]

        result = resolve_best_score_with_hints(providers, requirements)
        assert result is not None
        assert result["name"] == "redis", (
            "best_score should use hints to break ties. "
            "Redis is first in vendor_preference list."
        )

    def test_require_explicit_never_auto_selects(self) -> None:
        """Test that require_explicit NEVER auto-selects, regardless of requirements.

        Contract: When selection_policy='require_explicit', the resolver must
        NEVER automatically select a provider, even if:
        - Only one provider matches
        - The provider has a perfect preference score
        - All constraints are satisfied

        This policy exists for security-sensitive dependencies (secrets, credentials).
        """
        requirements = ModelRequirementSet(
            must={"encryption": "aes-256"},
            prefer={"region": "us-east-1"},
        )

        # Perfect single match that would auto-select under other policies
        providers = [
            {
                "name": "hashicorp_vault",
                "encryption": "aes-256",
                "region": "us-east-1",
            },
        ]

        def resolve_require_explicit(
            providers: list[dict[str, Any]],
            reqs: ModelRequirementSet,
            explicit_binding: str | None = None,
        ) -> dict[str, Any] | None:
            """Resolve using require_explicit policy: NEVER auto-select."""
            # CRITICAL: Without explicit binding, ALWAYS return None
            if explicit_binding is None:
                return None

            # Only resolve if explicit binding matches
            filtered = [
                p
                for p in providers
                if p.get("name") == explicit_binding
                and all(p.get(k) == v for k, v in reqs.must.items())
            ]
            return filtered[0] if filtered else None

        # Without explicit binding: MUST return None even with perfect match
        result_without_binding = resolve_require_explicit(providers, requirements)
        assert result_without_binding is None, (
            "require_explicit MUST NOT auto-select, even with perfect single match. "
            "This is critical for security-sensitive dependencies."
        )

        # With explicit binding: should resolve
        result_with_binding = resolve_require_explicit(
            providers, requirements, explicit_binding="hashicorp_vault"
        )
        assert result_with_binding is not None, (
            "require_explicit should resolve when explicit binding is provided"
        )
        assert result_with_binding["name"] == "hashicorp_vault"

    def test_forbid_constraints_exclude_before_policy_applies(self) -> None:
        """Test that 'forbid' constraints exclude providers before policy logic.

        Contract: The 'forbid' tier is applied during filtering (Phase 1),
        before any selection policy (Phase 2). A provider matching ANY forbid
        constraint is excluded regardless of how well it matches 'prefer'.
        """
        requirements = ModelRequirementSet(
            must={"supports_sql": True},
            prefer={"latency_ms": 5},  # Would give high score
            forbid={"deprecated": True},
        )

        providers = [
            {
                "name": "legacy_db",
                "supports_sql": True,
                "latency_ms": 5,  # Perfect prefer match
                "deprecated": True,  # But forbidden!
            },
            {
                "name": "new_db",
                "supports_sql": True,
                "latency_ms": 20,
                "deprecated": False,
            },
        ]

        def filter_providers(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> list[dict[str, Any]]:
            """Filter by must AND forbid constraints."""
            result = []
            for p in providers:
                # Check must constraints
                if not all(p.get(k) == v for k, v in reqs.must.items()):
                    continue
                # Check forbid constraints (any match excludes)
                if any(p.get(k) == v for k, v in reqs.forbid.items()):
                    continue
                result.append(p)
            return result

        filtered = filter_providers(providers, requirements)

        # legacy_db is excluded by forbid, even though it has better prefer score
        assert len(filtered) == 1
        assert filtered[0]["name"] == "new_db", (
            "forbid constraints MUST exclude providers before scoring. "
            "legacy_db has perfect prefer score but is deprecated (forbidden)."
        )


# =============================================================================
# Additional Shallow Merge Behavior Tests (PR Review Request)
# =============================================================================


@pytest.mark.unit
class TestShallowMergeNestedDictBehavior:
    """Additional tests for shallow merge nested dict behavior.

    These tests specifically address the PR review request to document
    the shallow merge warning behavior with nested dictionaries.
    """

    def test_shallow_merge_nested_dict_data_loss_warning(self) -> None:
        """Document that shallow merge causes INTENTIONAL data loss on nested dicts.

        This test explicitly demonstrates the WARNING documented in merge():
        "If your requirements contain nested dicts like {'config': {'a': 1, 'b': 2}},
        merging with {'config': {'a': 10}} will LOSE the 'b' key entirely."

        This behavior is INTENTIONAL for:
        1. Performance: O(n) dict spread vs O(n*m) recursive traversal
        2. Predictability: Flat key-value replacement is easier to reason about
        3. JSON compatibility: Matches JSON Merge Patch (RFC 7396) semantics
        """
        # SETUP: Base config with multiple nested keys
        base = ModelRequirementSet(
            must={"config": {"timeout": 30, "retries": 3, "buffer_size": 1024}}
        )

        # Override only specifies ONE nested key
        override = ModelRequirementSet(must={"config": {"timeout": 60}})

        # MERGE
        merged = base.merge(override)

        # CRITICAL ASSERTION: Nested keys 'retries' and 'buffer_size' are LOST
        config = merged.must.get("config", {})
        assert isinstance(config, dict)
        assert config == {"timeout": 60}, (
            "Shallow merge REPLACES entire nested dict, not deep-merges. "
            "This is documented and intentional."
        )
        assert "retries" not in config, "retries should be LOST (shallow merge)"
        assert "buffer_size" not in config, "buffer_size should be LOST (shallow merge)"

    def test_shallow_merge_explicit_example_a_b_c(self) -> None:
        """Test the exact example: {a: {b: 1}} + {a: {c: 2}} = {a: {c: 2}}.

        This is the canonical example demonstrating shallow vs deep merge:
        - Shallow (what we do): Result is {a: {c: 2}} - 'b' is lost
        - Deep (what we DON'T do): Result would be {a: {b: 1, c: 2}}
        """
        base = ModelRequirementSet(must={"a": {"b": 1}})
        override = ModelRequirementSet(must={"a": {"c": 2}})

        merged = base.merge(override)

        # Shallow merge: entire nested dict replaced
        assert merged.must == {"a": {"c": 2}}

        # NOT deep merge (would be {"a": {"b": 1, "c": 2}})
        nested = merged.must.get("a", {})
        assert isinstance(nested, dict)
        assert "b" not in nested, "Shallow merge: 'b' should NOT be preserved"
        assert nested.get("c") == 2

    def test_shallow_merge_across_all_tiers_consistency(self) -> None:
        """Verify shallow merge is consistent across must/prefer/forbid/hints.

        All four tiers should exhibit identical shallow merge behavior -
        this is not just a 'must' tier quirk.
        """
        base = ModelRequirementSet(
            must={"x": {"a": 1}},
            prefer={"x": {"a": 1}},
            forbid={"x": {"a": 1}},
            hints={"x": {"a": 1}},
        )
        override = ModelRequirementSet(
            must={"x": {"b": 2}},
            prefer={"x": {"b": 2}},
            forbid={"x": {"b": 2}},
            hints={"x": {"b": 2}},
        )

        merged = base.merge(override)

        # ALL tiers should have shallow behavior
        for tier_name in ["must", "prefer", "forbid", "hints"]:
            tier = getattr(merged, tier_name)
            nested = tier.get("x", {})
            assert isinstance(nested, dict)
            assert nested == {"b": 2}, f"{tier_name} tier should have shallow merge"
            assert "a" not in nested, f"{tier_name} tier: 'a' should be lost"

    def test_shallow_merge_deep_nesting_only_top_level_merged(self) -> None:
        """Test that deeply nested structures are entirely replaced.

        Even with 3+ levels of nesting, only the top-level key is merged -
        the entire nested structure is replaced.
        """
        base = ModelRequirementSet(
            must={
                "level1": {
                    "level2": {"level3": {"deep_key": "original", "another": 100}}
                }
            }
        )
        override = ModelRequirementSet(
            must={"level1": {"level2": {"level3": {"deep_key": "override"}}}}
        )

        merged = base.merge(override)

        # Verify entire deep structure is replaced
        level1 = merged.must.get("level1", {})
        assert isinstance(level1, dict)
        level2 = level1.get("level2", {})
        assert isinstance(level2, dict)
        level3 = level2.get("level3", {})
        assert isinstance(level3, dict)

        assert level3 == {"deep_key": "override"}, "Deeply nested dict is replaced"
        assert "another" not in level3, "'another' key should be lost (shallow merge)"


# =============================================================================
# Integration Examples (End-to-End Usage Patterns)
# =============================================================================


@pytest.mark.unit
class TestCapabilityDependencyIntegration:
    """Integration examples demonstrating typical capability dependency usage.

    These tests show end-to-end workflows combining ModelCapabilityDependency
    and ModelRequirementSet for common patterns in ONEX node contracts.
    """

    def test_database_dependency_with_merged_requirements(self) -> None:
        """Example: Database dependency with base and environment-specific requirements.

        Common pattern: Define base requirements in code, merge environment-specific
        requirements from configuration.
        """
        # Base requirements (in handler code)
        base_reqs = ModelRequirementSet(
            must={"supports_transactions": True, "supports_ssl": True},
            prefer={"connection_pool_size": 10},
        )

        # Environment-specific requirements (from config)
        prod_reqs = ModelRequirementSet(
            must={"encryption_at_rest": True},
            prefer={"max_connections": 100, "region": "us-east-1"},
            forbid={"deprecated": True},
        )

        # Merge for production
        merged = base_reqs.merge(prod_reqs)

        # Create the dependency with merged requirements
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=merged,
            selection_policy="auto_if_unique",
        )

        # Verify combined requirements
        assert merged.must == {
            "supports_transactions": True,
            "supports_ssl": True,
            "encryption_at_rest": True,
        }
        assert merged.prefer == {
            "connection_pool_size": 10,
            "max_connections": 100,
            "region": "us-east-1",
        }
        assert merged.forbid == {"deprecated": True}

        # Verify dependency properties
        assert dep.alias == "db"
        assert dep.domain == "database"
        assert dep.capability_type == "relational"
        assert dep.has_requirements is True
        assert dep.requires_explicit_binding is False

    def test_cache_dependency_with_scoring_resolution(self) -> None:
        """Example: Cache dependency using best_score policy with mock resolution.

        Demonstrates how prefer constraints affect provider selection.
        """
        reqs = ModelRequirementSet(
            must={"distributed": True},
            prefer={"in_memory": True, "supports_ttl": True, "region": "us-west-2"},
            hints={"vendor_preference": ["redis", "memcached"]},
        )

        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            requirements=reqs,
            selection_policy="best_score",
            strict=False,  # Allow fallback if some preferences unmet
        )

        # Mock provider catalog
        providers = [
            {
                "name": "redis_west",
                "distributed": True,
                "in_memory": True,
                "supports_ttl": True,
                "region": "us-west-2",
            },
            {
                "name": "redis_east",
                "distributed": True,
                "in_memory": True,
                "supports_ttl": True,
                "region": "us-east-1",
            },
            {
                "name": "memcached",
                "distributed": True,
                "in_memory": True,
                "supports_ttl": False,
                "region": "us-west-2",
            },
        ]

        # Mock scoring function
        def score_provider(p: dict[str, Any]) -> float:
            return sum(1.0 for k, v in dep.requirements.prefer.items() if p.get(k) == v)

        # Score all providers
        scores = [(p["name"], score_provider(p)) for p in providers]

        # redis_west matches all 3 prefer constraints (score=3)
        # memcached matches 2 (in_memory, region) (score=2)
        # redis_east matches 2 (in_memory, supports_ttl) (score=2)
        assert ("redis_west", 3.0) in scores
        assert max(scores, key=lambda x: x[1])[0] == "redis_west"

    def test_secrets_dependency_requires_explicit_binding(self) -> None:
        """Example: Security-sensitive dependency requiring explicit provider binding.

        Demonstrates require_explicit policy for secrets management.
        """
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            requirements=ModelRequirementSet(
                must={"encryption": "aes-256", "audit_logging": True},
            ),
            selection_policy="require_explicit",
        )

        # Verify security properties
        assert dep.requires_explicit_binding is True
        assert dep.selection_policy == "require_explicit"
        assert dep.requirements.must["encryption"] == "aes-256"

        # Mock: Even with single matching provider, require_explicit never auto-selects
        single_provider = [
            {"name": "vault", "encryption": "aes-256", "audit_logging": True}
        ]

        def resolve_require_explicit(
            providers: list[dict[str, Any]], explicit_binding: str | None
        ) -> dict[str, Any] | None:
            if explicit_binding is None:
                return None  # Never auto-select
            return next((p for p in providers if p["name"] == explicit_binding), None)

        # Without explicit binding: returns None (security guarantee)
        assert resolve_require_explicit(single_provider, None) is None

        # With explicit binding: resolves correctly
        result = resolve_require_explicit(single_provider, "vault")
        assert result is not None
        assert result["name"] == "vault"

    def test_vector_store_with_variant_and_hints(self) -> None:
        """Example: Vector store dependency with variant and vendor hints.

        Demonstrates three-part capability name and advisory hints.
        """
        dep = ModelCapabilityDependency(
            alias="vectors",
            capability="storage.vector.embeddings",
            requirements=ModelRequirementSet(
                must={"dimensions": 1536, "supports_metadata": True},
                prefer={"max_vectors": 1000000},
                hints={"engine_preference": ["qdrant", "milvus", "pinecone"]},
            ),
            selection_policy="best_score",
        )

        # Verify capability parsing
        assert dep.domain == "storage"
        assert dep.capability_type == "vector"
        assert dep.variant == "embeddings"

        # Verify hints for tie-breaking
        assert dep.requirements.hints["engine_preference"] == [
            "qdrant",
            "milvus",
            "pinecone",
        ]

    def test_requirement_layering_pattern(self) -> None:
        """Example: Three-layer requirement merging (default -> base -> override).

        Common pattern for configuration layering: default requirements are defined
        in code, base requirements in shared config, and overrides per-environment.
        """
        # Layer 1: Code defaults (most permissive)
        defaults = ModelRequirementSet(
            prefer={"timeout_ms": 5000},
        )

        # Layer 2: Base config (shared across environments)
        base_config = ModelRequirementSet(
            must={"available": True},
            prefer={"timeout_ms": 3000, "retries": 3},
        )

        # Layer 3: Environment override (production)
        prod_override = ModelRequirementSet(
            must={"encryption": True},
            prefer={"timeout_ms": 1000},  # More aggressive timeout
            forbid={"debug_mode": True},
        )

        # Apply layers: defaults -> base -> prod
        layer1 = defaults.merge(base_config)
        final = layer1.merge(prod_override)

        # Verify layered result
        assert final.must == {"available": True, "encryption": True}
        assert final.prefer == {"timeout_ms": 1000, "retries": 3}  # timeout overridden
        assert final.forbid == {"debug_mode": True}

    def test_forbid_filters_before_scoring_integration(self) -> None:
        """Example: Demonstrate that forbid constraints filter before prefer scoring.

        This is a critical integration behavior: a provider with a perfect prefer
        score is excluded if it matches any forbid constraint.
        """
        dep = ModelCapabilityDependency(
            alias="api",
            capability="http.client",
            requirements=ModelRequirementSet(
                must={"supports_https": True},
                prefer={"connection_pooling": True, "retry_logic": True},
                forbid={"uses_deprecated_tls": True},
            ),
            selection_policy="best_score",
        )

        providers = [
            {
                "name": "old_client",
                "supports_https": True,
                "connection_pooling": True,
                "retry_logic": True,  # Perfect prefer score!
                "uses_deprecated_tls": True,  # But forbidden
            },
            {
                "name": "new_client",
                "supports_https": True,
                "connection_pooling": True,
                "retry_logic": False,  # Lower prefer score
                "uses_deprecated_tls": False,
            },
        ]

        # Phase 1: Filter by must AND forbid
        def filter_providers(
            providers: list[dict[str, Any]], reqs: ModelRequirementSet
        ) -> list[dict[str, Any]]:
            result = []
            for p in providers:
                if not all(p.get(k) == v for k, v in reqs.must.items()):
                    continue
                if any(p.get(k) == v for k, v in reqs.forbid.items()):
                    continue  # Excluded by forbid
                result.append(p)
            return result

        filtered = filter_providers(providers, dep.requirements)

        # old_client is excluded despite perfect prefer score
        assert len(filtered) == 1
        assert filtered[0]["name"] == "new_client"


# =============================================================================
# TypeGuard Function Tests
# =============================================================================


@pytest.mark.unit
class TestIsJsonPrimitive:
    """Tests for is_json_primitive TypeGuard function.

    This TypeGuard enables type narrowing for JSON primitive values in resolver code.
    """

    def test_string_is_primitive(self) -> None:
        """Test that strings are recognized as JSON primitives."""
        assert is_json_primitive("hello") is True
        assert is_json_primitive("") is True
        assert is_json_primitive("with spaces") is True

    def test_int_is_primitive(self) -> None:
        """Test that integers are recognized as JSON primitives."""
        assert is_json_primitive(42) is True
        assert is_json_primitive(0) is True
        assert is_json_primitive(-100) is True

    def test_float_is_primitive(self) -> None:
        """Test that floats are recognized as JSON primitives."""
        assert is_json_primitive(3.14) is True
        assert is_json_primitive(0.0) is True
        assert is_json_primitive(-2.5) is True

    def test_bool_is_primitive(self) -> None:
        """Test that booleans are recognized as JSON primitives."""
        assert is_json_primitive(True) is True
        assert is_json_primitive(False) is True

    def test_none_is_primitive(self) -> None:
        """Test that None is recognized as a JSON primitive."""
        assert is_json_primitive(None) is True

    def test_list_is_not_primitive(self) -> None:
        """Test that lists are NOT JSON primitives."""
        assert is_json_primitive([1, 2, 3]) is False
        assert is_json_primitive([]) is False
        assert is_json_primitive(["a", "b"]) is False

    def test_dict_is_not_primitive(self) -> None:
        """Test that dicts are NOT JSON primitives."""
        assert is_json_primitive({"key": "value"}) is False
        assert is_json_primitive({}) is False

    def test_set_is_not_primitive(self) -> None:
        """Test that sets are NOT JSON primitives."""
        assert is_json_primitive({1, 2, 3}) is False

    def test_tuple_is_not_primitive(self) -> None:
        """Test that tuples are NOT JSON primitives."""
        assert is_json_primitive((1, 2, 3)) is False

    def test_custom_object_is_not_primitive(self) -> None:
        """Test that custom objects are NOT JSON primitives."""

        class CustomClass:
            pass

        assert is_json_primitive(CustomClass()) is False

    def test_callable_is_not_primitive(self) -> None:
        """Test that callables are NOT JSON primitives."""
        assert is_json_primitive(lambda x: x) is False
        assert is_json_primitive(len) is False


@pytest.mark.unit
class TestIsRequirementDict:
    """Tests for is_requirement_dict TypeGuard function.

    This TypeGuard enables type narrowing for requirement dictionaries in resolver code.
    """

    def test_empty_dict_is_requirement_dict(self) -> None:
        """Test that empty dict is recognized as requirement dict."""
        assert is_requirement_dict({}) is True

    def test_string_keys_dict_is_requirement_dict(self) -> None:
        """Test that dict with string keys is recognized as requirement dict."""
        assert is_requirement_dict({"key": "value"}) is True
        assert is_requirement_dict({"a": 1, "b": 2}) is True

    def test_nested_dict_is_requirement_dict(self) -> None:
        """Test that nested dicts with string keys are requirement dicts."""
        assert is_requirement_dict({"nested": {"a": 1}}) is True
        assert is_requirement_dict({"deep": {"level1": {"level2": 3}}}) is True

    def test_dict_with_list_values_is_requirement_dict(self) -> None:
        """Test that dicts with list values are requirement dicts."""
        assert is_requirement_dict({"vendors": ["a", "b", "c"]}) is True

    def test_int_keys_dict_is_not_requirement_dict(self) -> None:
        """Test that dict with int keys is NOT a requirement dict."""
        assert is_requirement_dict({1: "value"}) is False
        assert is_requirement_dict({0: "zero", 1: "one"}) is False

    def test_mixed_keys_dict_is_not_requirement_dict(self) -> None:
        """Test that dict with mixed key types is NOT a requirement dict."""
        assert is_requirement_dict({"string": 1, 2: "int_key"}) is False

    def test_list_is_not_requirement_dict(self) -> None:
        """Test that lists are NOT requirement dicts."""
        assert is_requirement_dict([1, 2, 3]) is False
        assert is_requirement_dict([]) is False

    def test_string_is_not_requirement_dict(self) -> None:
        """Test that strings are NOT requirement dicts."""
        assert is_requirement_dict("string") is False

    def test_none_is_not_requirement_dict(self) -> None:
        """Test that None is NOT a requirement dict."""
        assert is_requirement_dict(None) is False

    def test_primitive_is_not_requirement_dict(self) -> None:
        """Test that primitives are NOT requirement dicts."""
        assert is_requirement_dict(42) is False
        assert is_requirement_dict(3.14) is False
        assert is_requirement_dict(True) is False


@pytest.mark.unit
class TestIsRequirementList:
    """Tests for is_requirement_list TypeGuard function.

    This TypeGuard enables type narrowing for requirement lists in resolver code.
    """

    def test_empty_list_is_requirement_list(self) -> None:
        """Test that empty list is recognized as requirement list."""
        assert is_requirement_list([]) is True

    def test_list_of_primitives_is_requirement_list(self) -> None:
        """Test that list of primitives is requirement list."""
        assert is_requirement_list([1, 2, 3]) is True
        assert is_requirement_list(["a", "b", "c"]) is True
        assert is_requirement_list([True, False]) is True

    def test_list_of_dicts_is_requirement_list(self) -> None:
        """Test that list of dicts is requirement list."""
        assert is_requirement_list([{"a": 1}, {"b": 2}]) is True

    def test_nested_list_is_requirement_list(self) -> None:
        """Test that nested list is requirement list."""
        assert is_requirement_list([[1, 2], [3, 4]]) is True

    def test_mixed_list_is_requirement_list(self) -> None:
        """Test that mixed-type list is requirement list."""
        assert is_requirement_list([1, "string", {"key": "value"}]) is True

    def test_dict_is_not_requirement_list(self) -> None:
        """Test that dicts are NOT requirement lists."""
        assert is_requirement_list({"key": "value"}) is False
        assert is_requirement_list({}) is False

    def test_string_is_not_requirement_list(self) -> None:
        """Test that strings are NOT requirement lists (even though iterable)."""
        assert is_requirement_list("string") is False

    def test_tuple_is_not_requirement_list(self) -> None:
        """Test that tuples are NOT requirement lists."""
        assert is_requirement_list((1, 2, 3)) is False

    def test_none_is_not_requirement_list(self) -> None:
        """Test that None is NOT a requirement list."""
        assert is_requirement_list(None) is False

    def test_set_is_not_requirement_list(self) -> None:
        """Test that sets are NOT requirement lists."""
        assert is_requirement_list({1, 2, 3}) is False


@pytest.mark.unit
class TestIsRequirementValue:
    """Tests for is_requirement_value TypeGuard function.

    This TypeGuard enables type narrowing for any valid JsonType value in resolver code.
    """

    def test_string_is_requirement_value(self) -> None:
        """Test that strings are valid requirement values."""
        assert is_requirement_value("hello") is True

    def test_int_is_requirement_value(self) -> None:
        """Test that integers are valid requirement values."""
        assert is_requirement_value(42) is True

    def test_float_is_requirement_value(self) -> None:
        """Test that floats are valid requirement values."""
        assert is_requirement_value(3.14) is True

    def test_bool_is_requirement_value(self) -> None:
        """Test that booleans are valid requirement values."""
        assert is_requirement_value(True) is True
        assert is_requirement_value(False) is True

    def test_none_is_requirement_value(self) -> None:
        """Test that None is a valid requirement value."""
        assert is_requirement_value(None) is True

    def test_list_is_requirement_value(self) -> None:
        """Test that lists are valid requirement values."""
        assert is_requirement_value([1, 2, 3]) is True
        assert is_requirement_value([]) is True
        assert is_requirement_value(["a", "b"]) is True

    def test_dict_with_string_keys_is_requirement_value(self) -> None:
        """Test that dicts with string keys are valid requirement values."""
        assert is_requirement_value({"key": "value"}) is True
        assert is_requirement_value({}) is True

    def test_nested_structures_are_requirement_value(self) -> None:
        """Test that nested structures are valid requirement values."""
        assert is_requirement_value({"nested": {"deep": [1, 2, 3]}}) is True
        assert is_requirement_value([{"a": 1}, [2, 3]]) is True

    def test_dict_with_int_keys_is_not_requirement_value(self) -> None:
        """Test that dict with non-string keys is NOT a valid requirement value."""
        assert is_requirement_value({1: "value"}) is False
        assert is_requirement_value({0: "a", 1: "b"}) is False

    def test_set_is_not_requirement_value(self) -> None:
        """Test that sets are NOT valid requirement values."""
        assert is_requirement_value({1, 2, 3}) is False

    def test_tuple_is_not_requirement_value(self) -> None:
        """Test that tuples are NOT valid requirement values."""
        assert is_requirement_value((1, 2, 3)) is False

    def test_custom_object_is_not_requirement_value(self) -> None:
        """Test that custom objects are NOT valid requirement values."""

        class CustomClass:
            pass

        assert is_requirement_value(CustomClass()) is False

    def test_callable_is_not_requirement_value(self) -> None:
        """Test that callables are NOT valid requirement values."""
        assert is_requirement_value(lambda x: x) is False


@pytest.mark.unit
class TestTypeGuardTypeNarrowing:
    """Tests verifying TypeGuard enables proper type narrowing.

    These tests demonstrate the static analysis benefits of TypeGuards,
    ensuring mypy/pyright recognize narrowed types after the guard.
    """

    def test_is_json_primitive_narrows_in_conditional(self) -> None:
        """Test that is_json_primitive enables type narrowing in conditionals.

        After the guard, mypy should recognize the value as a JSON primitive type.
        """
        value: Any = "test"
        if is_json_primitive(value):
            # After this check, mypy knows value is str | int | float | bool | None
            # We can safely use primitive operations
            result = str(value)  # No type: ignore needed
            assert result == "test"

    def test_is_requirement_dict_narrows_in_conditional(self) -> None:
        """Test that is_requirement_dict enables type narrowing for dict operations.

        After the guard, mypy should recognize dict[str, JsonType].
        """
        value: Any = {"key": "value", "count": 42}
        if is_requirement_dict(value):
            # After this check, mypy knows value is dict[str, JsonType]
            # We can safely use dict operations without type: ignore
            keys = list(value.keys())
            assert "key" in keys
            assert "count" in keys

    def test_is_requirement_list_narrows_in_conditional(self) -> None:
        """Test that is_requirement_list enables type narrowing for list operations.

        After the guard, mypy should recognize list[JsonType].
        """
        value: Any = [1, 2, 3]
        if is_requirement_list(value):
            # After this check, mypy knows value is list[JsonType]
            # We can safely use list operations without type: ignore
            length = len(value)
            assert length == 3

    def test_is_requirement_value_enables_resolver_pattern(self) -> None:
        """Test that is_requirement_value enables the resolver pattern.

        This demonstrates the common pattern in capability resolvers where
        we need to process arbitrary values from requirement dicts.
        """
        data: dict[str, Any] = {
            "primitive": "hello",
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "invalid": {1, 2, 3},  # Set - invalid
        }

        valid_keys: list[str] = []
        invalid_keys: list[str] = []

        for key, value in data.items():
            if is_requirement_value(value):
                valid_keys.append(key)
            else:
                invalid_keys.append(key)

        assert set(valid_keys) == {"primitive", "list", "dict"}
        assert invalid_keys == ["invalid"]

    def test_chained_type_guards_for_nested_processing(self) -> None:
        """Test using multiple TypeGuards for nested structure processing.

        Demonstrates using TypeGuards together to process complex structures
        with full type safety.
        """
        data: Any = {"config": {"timeout": 30, "retries": 3}, "vendors": ["a", "b"]}

        processed: dict[str, str] = {}

        if is_requirement_dict(data):
            for key, value in data.items():
                if is_requirement_dict(value):
                    # Nested dict - could process recursively
                    processed[key] = f"dict with {len(value)} keys"
                elif is_requirement_list(value):
                    processed[key] = f"list with {len(value)} items"
                elif is_json_primitive(value):
                    processed[key] = f"primitive: {value}"

        assert processed["config"] == "dict with 2 keys"
        assert processed["vendors"] == "list with 2 items"

    def test_type_guard_in_list_comprehension(self) -> None:
        """Test TypeGuard works in list comprehension filters.

        This is a common pattern for filtering valid values from mixed data.
        """
        mixed_data: list[Any] = ["a", 1, {1, 2}, {"key": "value"}, lambda x: x]

        # Filter to only valid requirement values
        valid_values = [v for v in mixed_data if is_requirement_value(v)]

        # Should have string, int, and dict (not set or lambda)
        assert len(valid_values) == 3
        assert "a" in valid_values
        assert 1 in valid_values
        assert {"key": "value"} in valid_values
