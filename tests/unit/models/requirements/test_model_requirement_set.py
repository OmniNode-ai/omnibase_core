"""Comprehensive tests for ModelRequirementSet.

Tests cover:
1. Basic matching with must requirements (pass/fail cases)
2. Forbid requirements blocking matches
3. Prefer scoring (+1.0 per satisfied)
4. Warning emission for unmet prefer constraints
5. Key-name heuristics (max_*, min_*)
6. Explicit operator support ($eq, $ne, $lt, $lte, $gt, $gte, $in, $contains)
7. List value matching (any-of semantics)
8. Hints-based sorting/tie-breaking
9. Empty requirement set behavior
10. Frozen/immutable behavior
11. Edge cases (missing keys, None values, type mismatches)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.requirements import ModelRequirementSet


@pytest.mark.unit
class TestBasicMustRequirements:
    """Tests for basic MUST requirement matching."""

    def test_must_single_requirement_pass(self) -> None:
        """Single MUST requirement that passes."""
        reqs = ModelRequirementSet(must={"region": "us-east-1"})
        provider = {"region": "us-east-1"}

        matches, score, warnings = reqs.matches(provider)

        assert matches is True
        assert score == 0.0  # No PREFER constraints
        assert warnings == []

    def test_must_single_requirement_fail(self) -> None:
        """Single MUST requirement that fails."""
        reqs = ModelRequirementSet(must={"region": "us-east-1"})
        provider = {"region": "us-west-2"}

        matches, score, warnings = reqs.matches(provider)

        assert matches is False
        assert score == 0.0
        assert "MUST requirement not satisfied: region" in warnings[0]

    def test_must_multiple_requirements_all_pass(self) -> None:
        """Multiple MUST requirements that all pass."""
        reqs = ModelRequirementSet(
            must={"region": "us-east-1", "tier": "premium", "version": 2}
        )
        provider = {"region": "us-east-1", "tier": "premium", "version": 2}

        matches, _score, warnings = reqs.matches(provider)

        assert matches is True
        assert warnings == []

    def test_must_multiple_requirements_one_fails(self) -> None:
        """Multiple MUST requirements where one fails."""
        reqs = ModelRequirementSet(must={"region": "us-east-1", "tier": "premium"})
        provider = {"region": "us-east-1", "tier": "basic"}

        matches, _score, warnings = reqs.matches(provider)

        assert matches is False
        assert "tier" in warnings[0]

    def test_must_requirement_missing_key(self) -> None:
        """MUST requirement where key is missing from provider."""
        reqs = ModelRequirementSet(must={"required_feature": True})
        provider = {"other_feature": True}

        matches, _score, _warnings = reqs.matches(provider)

        assert matches is False


@pytest.mark.unit
class TestForbidRequirements:
    """Tests for FORBID requirement blocking."""

    def test_forbid_not_present_passes(self) -> None:
        """FORBID requirement passes when key not present."""
        reqs = ModelRequirementSet(forbid={"deprecated": True})
        provider = {"active": True}

        matches, _score, _warnings = reqs.matches(provider)

        assert matches is True

    def test_forbid_present_and_matching_fails(self) -> None:
        """FORBID requirement fails when key present with forbidden value."""
        reqs = ModelRequirementSet(forbid={"deprecated": True})
        provider = {"deprecated": True}

        matches, _score, warnings = reqs.matches(provider)

        assert matches is False
        assert "FORBID requirement violated: deprecated" in warnings[0]

    def test_forbid_present_but_different_value_passes(self) -> None:
        """FORBID requirement passes when key present but value differs."""
        reqs = ModelRequirementSet(forbid={"deprecated": True})
        provider = {"deprecated": False}

        matches, _score, _warnings = reqs.matches(provider)

        assert matches is True

    def test_forbid_multiple_requirements(self) -> None:
        """Multiple FORBID requirements - any violation fails."""
        reqs = ModelRequirementSet(forbid={"deprecated": True, "legacy": True})
        provider = {"deprecated": False, "legacy": True}

        matches, _score, warnings = reqs.matches(provider)

        assert matches is False
        assert "FORBID" in warnings[0]


@pytest.mark.unit
class TestPreferScoring:
    """Tests for PREFER scoring (+1.0 per satisfied)."""

    def test_prefer_single_satisfied(self) -> None:
        """Single PREFER constraint satisfied adds +1.0."""
        reqs = ModelRequirementSet(prefer={"memory_gb": 16})
        provider = {"memory_gb": 16}

        matches, score, warnings = reqs.matches(provider)

        assert matches is True
        assert score == 1.0
        assert warnings == []

    def test_prefer_multiple_all_satisfied(self) -> None:
        """Multiple PREFER constraints all satisfied."""
        reqs = ModelRequirementSet(
            prefer={"memory_gb": 16, "cpu_cores": 8, "ssd": True}
        )
        provider = {"memory_gb": 16, "cpu_cores": 8, "ssd": True}

        matches, score, warnings = reqs.matches(provider)

        assert matches is True
        assert score == 3.0
        assert warnings == []

    def test_prefer_partial_satisfied(self) -> None:
        """Some PREFER constraints satisfied, some not."""
        reqs = ModelRequirementSet(
            prefer={"memory_gb": 16, "cpu_cores": 8, "ssd": True}
        )
        provider = {"memory_gb": 16, "cpu_cores": 4, "ssd": True}

        matches, score, warnings = reqs.matches(provider)

        assert matches is True
        assert score == 2.0
        assert len(warnings) == 1
        assert "PREFER not satisfied: cpu_cores" in warnings[0]

    def test_prefer_none_satisfied(self) -> None:
        """No PREFER constraints satisfied - still matches."""
        reqs = ModelRequirementSet(prefer={"memory_gb": 16, "cpu_cores": 8})
        provider = {"memory_gb": 8, "cpu_cores": 4}

        matches, score, warnings = reqs.matches(provider)

        assert matches is True
        assert score == 0.0
        assert len(warnings) == 2

    def test_prefer_does_not_affect_match(self) -> None:
        """PREFER failures don't cause match failure."""
        reqs = ModelRequirementSet(
            must={"region": "us-east-1"},
            prefer={"memory_gb": 32},  # Won't be satisfied
        )
        provider = {"region": "us-east-1", "memory_gb": 8}

        matches, score, _warnings = reqs.matches(provider)

        assert matches is True  # MUST is satisfied
        assert score == 0.0  # PREFER not satisfied


@pytest.mark.unit
class TestKeyNameHeuristics:
    """Tests for key-name heuristics (max_*, min_*)."""

    def test_max_prefix_uses_lte(self) -> None:
        """max_* keys use <= comparison."""
        reqs = ModelRequirementSet(must={"max_latency_ms": 20})

        # latency_ms is looked up for max_latency_ms requirement
        provider_pass = {"latency_ms": 15}
        provider_exact = {"latency_ms": 20}
        provider_fail = {"latency_ms": 25}

        assert reqs.matches(provider_pass)[0] is True
        assert reqs.matches(provider_exact)[0] is True
        assert reqs.matches(provider_fail)[0] is False

    def test_min_prefix_uses_gte(self) -> None:
        """min_* keys use >= comparison."""
        reqs = ModelRequirementSet(must={"min_memory_gb": 16})

        provider_pass = {"memory_gb": 32}
        provider_exact = {"memory_gb": 16}
        provider_fail = {"memory_gb": 8}

        assert reqs.matches(provider_pass)[0] is True
        assert reqs.matches(provider_exact)[0] is True
        assert reqs.matches(provider_fail)[0] is False

    def test_max_prefix_with_full_key_in_provider(self) -> None:
        """max_* also matches if provider has the full key name."""
        reqs = ModelRequirementSet(must={"max_latency_ms": 20})
        provider = {"max_latency_ms": 15}  # Full key name in provider

        matches, _, _ = reqs.matches(provider)
        assert matches is True

    def test_min_prefix_with_full_key_in_provider(self) -> None:
        """min_* also matches if provider has the full key name."""
        reqs = ModelRequirementSet(must={"min_uptime": 99.9})
        provider = {"min_uptime": 99.95}  # Full key name in provider

        matches, _, _ = reqs.matches(provider)
        assert matches is True

    def test_regular_key_uses_equality(self) -> None:
        """Keys without max_/min_ prefix use equality."""
        reqs = ModelRequirementSet(must={"version": 2})

        provider_pass = {"version": 2}
        provider_fail = {"version": 3}

        assert reqs.matches(provider_pass)[0] is True
        assert reqs.matches(provider_fail)[0] is False


@pytest.mark.unit
class TestExplicitOperators:
    """Tests for explicit operator support."""

    def test_eq_operator(self) -> None:
        """$eq operator for equality."""
        reqs = ModelRequirementSet(must={"version": {"$eq": 2}})

        assert reqs.matches({"version": 2})[0] is True
        assert reqs.matches({"version": 3})[0] is False

    def test_ne_operator(self) -> None:
        """$ne operator for not equal."""
        reqs = ModelRequirementSet(must={"status": {"$ne": "deprecated"}})

        assert reqs.matches({"status": "active"})[0] is True
        assert reqs.matches({"status": "deprecated"})[0] is False

    def test_lt_operator(self) -> None:
        """$lt operator for less than."""
        reqs = ModelRequirementSet(must={"latency_ms": {"$lt": 20}})

        assert reqs.matches({"latency_ms": 15})[0] is True
        assert reqs.matches({"latency_ms": 20})[0] is False
        assert reqs.matches({"latency_ms": 25})[0] is False

    def test_lte_operator(self) -> None:
        """$lte operator for less than or equal."""
        reqs = ModelRequirementSet(must={"latency_ms": {"$lte": 20}})

        assert reqs.matches({"latency_ms": 15})[0] is True
        assert reqs.matches({"latency_ms": 20})[0] is True
        assert reqs.matches({"latency_ms": 25})[0] is False

    def test_gt_operator(self) -> None:
        """$gt operator for greater than."""
        reqs = ModelRequirementSet(must={"memory_gb": {"$gt": 8}})

        assert reqs.matches({"memory_gb": 16})[0] is True
        assert reqs.matches({"memory_gb": 8})[0] is False
        assert reqs.matches({"memory_gb": 4})[0] is False

    def test_gte_operator(self) -> None:
        """$gte operator for greater than or equal."""
        reqs = ModelRequirementSet(must={"memory_gb": {"$gte": 8}})

        assert reqs.matches({"memory_gb": 16})[0] is True
        assert reqs.matches({"memory_gb": 8})[0] is True
        assert reqs.matches({"memory_gb": 4})[0] is False

    def test_in_operator(self) -> None:
        """$in operator for value in list."""
        reqs = ModelRequirementSet(must={"region": {"$in": ["us-east-1", "us-west-2"]}})

        assert reqs.matches({"region": "us-east-1"})[0] is True
        assert reqs.matches({"region": "us-west-2"})[0] is True
        assert reqs.matches({"region": "eu-west-1"})[0] is False

    def test_contains_operator(self) -> None:
        """$contains operator for list contains value."""
        reqs = ModelRequirementSet(must={"features": {"$contains": "gpu"}})

        assert reqs.matches({"features": ["gpu", "ssd", "nvme"]})[0] is True
        assert reqs.matches({"features": ["ssd", "nvme"]})[0] is False

    def test_multiple_operators_combined(self) -> None:
        """Multiple operators in same requirement (all must pass)."""
        reqs = ModelRequirementSet(must={"latency_ms": {"$gte": 5, "$lte": 20}})

        assert reqs.matches({"latency_ms": 10})[0] is True
        assert reqs.matches({"latency_ms": 5})[0] is True
        assert reqs.matches({"latency_ms": 20})[0] is True
        assert reqs.matches({"latency_ms": 4})[0] is False
        assert reqs.matches({"latency_ms": 21})[0] is False

    def test_explicit_lte_overrides_max_heuristic(self) -> None:
        """Explicit $lte in max_* key uses operator, not heuristic."""
        # This tests that operator syntax is respected even with max_* keys
        reqs = ModelRequirementSet(must={"max_latency_ms": {"$lte": 20}})
        provider = {"latency_ms": 15}

        assert reqs.matches(provider)[0] is True


@pytest.mark.unit
class TestListValueMatching:
    """Tests for list value matching (any-of semantics)."""

    def test_list_requirement_single_value_match(self) -> None:
        """Provider single value in requirement list."""
        reqs = ModelRequirementSet(
            must={"region": ["us-east-1", "us-west-2", "eu-west-1"]}
        )

        assert reqs.matches({"region": "us-east-1"})[0] is True
        assert reqs.matches({"region": "ap-south-1"})[0] is False

    def test_list_requirement_list_intersection(self) -> None:
        """Provider list intersects with requirement list."""
        reqs = ModelRequirementSet(must={"zones": ["zone-a", "zone-b", "zone-c"]})

        # Has intersection
        assert reqs.matches({"zones": ["zone-a", "zone-d"]})[0] is True
        # No intersection
        assert reqs.matches({"zones": ["zone-x", "zone-y"]})[0] is False

    def test_list_requirement_empty_intersection(self) -> None:
        """Provider list with no intersection fails."""
        reqs = ModelRequirementSet(must={"features": ["gpu", "tpu"]})
        provider = {"features": ["cpu", "fpga"]}

        assert reqs.matches(provider)[0] is False

    def test_list_requirement_in_prefer_matching(self) -> None:
        """List matching in PREFER adds score when satisfied."""
        reqs = ModelRequirementSet(prefer={"regions": ["us-east-1", "us-west-2"]})

        matches, score, _ = reqs.matches({"regions": ["us-east-1"]})

        assert matches is True
        assert score == 1.0

    def test_list_requirement_in_prefer_non_matching(self) -> None:
        """List matching in PREFER gives zero score when not satisfied."""
        reqs = ModelRequirementSet(prefer={"regions": ["us-east-1", "us-west-2"]})

        matches, score, _ = reqs.matches({"regions": ["ap-south-1"]})

        assert matches is True
        assert score == 0.0


@pytest.mark.unit
class TestHintsAndSorting:
    """Tests for hints-based sorting and tie-breaking."""

    def test_sort_key_higher_score_first(self) -> None:
        """sort_key puts higher scores first (negative score)."""
        reqs = ModelRequirementSet(prefer={"memory_gb": 16, "cpu_cores": 8})

        provider_high = {"id": "p1", "memory_gb": 16, "cpu_cores": 8}
        provider_low = {"id": "p2", "memory_gb": 8, "cpu_cores": 4}

        key_high = reqs.sort_key(provider_high)
        key_low = reqs.sort_key(provider_low)

        # Higher score = more negative first element
        assert key_high[0] < key_low[0]

    def test_sort_key_hints_break_ties(self) -> None:
        """Hints break ties when scores are equal."""
        reqs = ModelRequirementSet(
            prefer={"memory_gb": 16}, hints={"tier": "premium", "ssd": True}
        )

        # Same PREFER score, but different hint satisfaction
        provider_good_hints = {
            "id": "p1",
            "memory_gb": 16,
            "tier": "premium",
            "ssd": True,
        }
        provider_bad_hints = {
            "id": "p2",
            "memory_gb": 16,
            "tier": "basic",
            "ssd": False,
        }

        key_good = reqs.sort_key(provider_good_hints)
        key_bad = reqs.sort_key(provider_bad_hints)

        # Same score (negative)
        assert key_good[0] == key_bad[0]
        # But better hint rank (lower)
        assert key_good[1] < key_bad[1]

    def test_sort_key_deterministic_fallback(self) -> None:
        """Deterministic fallback uses provider id."""
        reqs = ModelRequirementSet()

        provider1 = {"id": "alpha", "memory_gb": 16}
        provider2 = {"id": "beta", "memory_gb": 16}

        key1 = reqs.sort_key(provider1)
        key2 = reqs.sort_key(provider2)

        assert key1[2] == "alpha"
        assert key2[2] == "beta"

    def test_sort_key_non_matching_providers(self) -> None:
        """Non-matching providers get worst sort key."""
        reqs = ModelRequirementSet(must={"region": "us-east-1"})

        provider_match = {"id": "p1", "region": "us-east-1"}
        provider_no_match = {"id": "p2", "region": "eu-west-1"}

        key_match = reqs.sort_key(provider_match)
        key_no_match = reqs.sort_key(provider_no_match)

        # Non-matching gets infinity score
        assert key_no_match[0] == float("inf")
        assert key_match[0] < key_no_match[0]

    def test_sorting_providers_list(self) -> None:
        """Sort a list of providers by match quality."""
        reqs = ModelRequirementSet(
            must={"active": True},
            prefer={"memory_gb": 16, "cpu_cores": 8},
            hints={"tier": "premium"},
        )

        providers = [
            {
                "id": "worst",
                "active": True,
                "memory_gb": 4,
                "cpu_cores": 2,
                "tier": "basic",
            },
            {
                "id": "best",
                "active": True,
                "memory_gb": 16,
                "cpu_cores": 8,
                "tier": "premium",
            },
            {
                "id": "middle",
                "active": True,
                "memory_gb": 16,
                "cpu_cores": 4,
                "tier": "basic",
            },
            {
                "id": "no_match",
                "active": False,
                "memory_gb": 32,
                "cpu_cores": 16,
                "tier": "premium",
            },
        ]

        sorted_providers = sorted(providers, key=reqs.sort_key)

        assert sorted_providers[0]["id"] == "best"
        assert sorted_providers[1]["id"] == "middle"
        assert sorted_providers[2]["id"] == "worst"
        assert sorted_providers[3]["id"] == "no_match"


@pytest.mark.unit
class TestEmptyRequirementSet:
    """Tests for empty requirement set behavior."""

    def test_empty_set_matches_any_provider(self) -> None:
        """Empty requirement set matches any provider."""
        reqs = ModelRequirementSet()

        assert reqs.matches({})[0] is True
        assert reqs.matches({"any": "thing"})[0] is True
        assert reqs.matches({"complex": {"nested": "data"}})[0] is True

    def test_empty_set_zero_score(self) -> None:
        """Empty requirement set has zero score."""
        reqs = ModelRequirementSet()

        _, score, warnings = reqs.matches({"anything": "here"})

        assert score == 0.0
        assert warnings == []

    def test_empty_set_sort_key(self) -> None:
        """Empty set sort_key works correctly."""
        reqs = ModelRequirementSet()

        provider = {"id": "test"}
        key = reqs.sort_key(provider)

        assert key[0] == 0.0  # Negated zero score
        assert key[1] == 0  # No unmatched hints


@pytest.mark.unit
class TestFrozenImmutability:
    """Tests for frozen/immutable behavior."""

    def test_model_is_frozen(self) -> None:
        """Model is frozen and cannot be mutated."""
        reqs = ModelRequirementSet(must={"region": "us-east-1"})

        with pytest.raises(ValidationError):
            reqs.must = {"different": "value"}  # type: ignore[misc]

    def test_model_rejects_extra_fields(self) -> None:
        """Model rejects extra fields."""
        with pytest.raises(ValidationError):
            ModelRequirementSet(
                must={"region": "us-east-1"},
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_not_hashable_due_to_dict_fields(self) -> None:
        """Frozen model with dict fields is not hashable (Python limitation).

        Note: Pydantic frozen models containing mutable types like dict
        cannot be hashed. This is expected Python behavior.
        """
        reqs = ModelRequirementSet(must={"region": "us-east-1"})

        # Dict fields make the model unhashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(reqs)

    def test_empty_model_equality(self) -> None:
        """Empty models with same defaults are equal."""
        reqs1 = ModelRequirementSet()
        reqs2 = ModelRequirementSet()

        assert reqs1 == reqs2

    def test_model_equality_same_content(self) -> None:
        """Models with same content are equal."""
        reqs1 = ModelRequirementSet(must={"region": "us-east-1"})
        reqs2 = ModelRequirementSet(must={"region": "us-east-1"})

        assert reqs1 == reqs2

    def test_model_inequality_different_content(self) -> None:
        """Models with different content are not equal."""
        reqs1 = ModelRequirementSet(must={"region": "us-east-1"})
        reqs2 = ModelRequirementSet(must={"region": "us-west-2"})

        assert reqs1 != reqs2


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases."""

    def test_none_value_in_provider(self) -> None:
        """Handle None values in provider."""
        reqs = ModelRequirementSet(must={"optional_field": None})

        assert reqs.matches({"optional_field": None})[0] is True
        assert reqs.matches({"optional_field": "something"})[0] is False

    def test_none_value_comparison_operators(self) -> None:
        """Comparison operators with None values return False."""
        reqs = ModelRequirementSet(must={"value": {"$gt": 10}})

        assert reqs.matches({"value": None})[0] is False
        assert reqs.matches({})[0] is False

    def test_type_mismatch_numeric_coercion(self) -> None:
        """Numeric types are coerced for comparison."""
        reqs = ModelRequirementSet(must={"value": 10})

        assert reqs.matches({"value": 10})[0] is True
        assert reqs.matches({"value": 10.0})[0] is True

    def test_type_mismatch_string_vs_int(self) -> None:
        """String vs int comparison works with equality."""
        reqs = ModelRequirementSet(must={"version": "2"})

        assert reqs.matches({"version": "2"})[0] is True
        assert reqs.matches({"version": 2})[0] is False

    def test_nested_dict_equality(self) -> None:
        """Nested dict equality comparison."""
        reqs = ModelRequirementSet(must={"config": {"nested": {"deep": True}}})

        assert reqs.matches({"config": {"nested": {"deep": True}}})[0] is True
        assert reqs.matches({"config": {"nested": {"deep": False}}})[0] is False

    def test_boolean_values(self) -> None:
        """Boolean value matching."""
        reqs = ModelRequirementSet(must={"enabled": True})

        assert reqs.matches({"enabled": True})[0] is True
        assert reqs.matches({"enabled": False})[0] is False
        # 1 and True are equal in Python, but this model uses equality
        assert reqs.matches({"enabled": 1})[0] is True

    def test_float_comparison_precision(self) -> None:
        """Float comparison with precision."""
        reqs = ModelRequirementSet(must={"max_latency": 0.001})

        assert reqs.matches({"latency": 0.0009})[0] is True
        assert reqs.matches({"latency": 0.001})[0] is True
        assert reqs.matches({"latency": 0.002})[0] is False

    def test_empty_list_in_requirement(self) -> None:
        """Empty list requirement (nothing matches)."""
        reqs = ModelRequirementSet(must={"regions": []})

        # Nothing can match an empty list
        assert reqs.matches({"regions": "us-east-1"})[0] is False
        assert reqs.matches({"regions": []})[0] is False

    def test_operator_with_non_numeric_value(self) -> None:
        """Numeric operators with non-numeric values return False."""
        reqs = ModelRequirementSet(must={"value": {"$gt": 10}})

        assert reqs.matches({"value": "not_a_number"})[0] is False

    def test_contains_operator_on_non_list(self) -> None:
        """$contains on non-list provider value returns False."""
        reqs = ModelRequirementSet(must={"tags": {"$contains": "important"}})

        assert reqs.matches({"tags": "not_a_list"})[0] is False

    def test_in_operator_on_non_list_expected(self) -> None:
        """$in with non-list expected value returns False."""
        reqs = ModelRequirementSet(must={"value": {"$in": "not_a_list"}})

        assert reqs.matches({"value": "something"})[0] is False


@pytest.mark.unit
class TestCombinedTiers:
    """Tests for combined tier functionality."""

    def _create_full_tier_requirements(self) -> ModelRequirementSet:
        """Helper to create requirements with all four tiers."""
        return ModelRequirementSet(
            must={"region": "us-east-1", "active": True},
            prefer={"memory_gb": 16, "cpu_cores": 8},
            forbid={"deprecated": True, "legacy": True},
            hints={"tier": "premium", "ssd": True},
        )

    def test_all_tiers_perfect_provider(self) -> None:
        """Perfect provider satisfies all tiers with full score."""
        reqs = self._create_full_tier_requirements()
        perfect = {
            "region": "us-east-1",
            "active": True,
            "memory_gb": 16,
            "cpu_cores": 8,
            "deprecated": False,
            "tier": "premium",
            "ssd": True,
        }

        matches, score, warnings = reqs.matches(perfect)

        assert matches is True
        assert score == 2.0  # Both PREFER satisfied
        assert warnings == []

    def test_all_tiers_good_provider(self) -> None:
        """Good provider matches MUST but only partial PREFER score."""
        reqs = self._create_full_tier_requirements()
        good = {
            "region": "us-east-1",
            "active": True,
            "memory_gb": 8,  # Less than preferred
            "cpu_cores": 8,
            "tier": "basic",  # Not preferred hint
        }

        matches, score, warnings = reqs.matches(good)

        assert matches is True
        assert score == 1.0  # One PREFER satisfied
        assert len(warnings) == 1

    def test_all_tiers_fails_must(self) -> None:
        """Provider failing MUST requirement does not match."""
        reqs = self._create_full_tier_requirements()
        fails_must = {
            "region": "eu-west-1",  # Wrong region
            "active": True,
            "memory_gb": 32,
            "cpu_cores": 16,
        }

        matches, _score, _warnings = reqs.matches(fails_must)

        assert matches is False

    def test_all_tiers_fails_forbid(self) -> None:
        """Provider violating FORBID requirement does not match."""
        reqs = self._create_full_tier_requirements()
        fails_forbid = {
            "region": "us-east-1",
            "active": True,
            "deprecated": True,  # Forbidden!
        }

        matches, _score, warnings = reqs.matches(fails_forbid)

        assert matches is False
        assert "FORBID" in warnings[0]

    def test_resolution_order_must_before_forbid(self) -> None:
        """MUST is checked before FORBID."""
        reqs = ModelRequirementSet(
            must={"region": "us-east-1"}, forbid={"deprecated": True}
        )

        # Fails both MUST and FORBID - MUST failure reported
        provider = {"region": "eu-west-1", "deprecated": True}
        matches, _score, warnings = reqs.matches(provider)

        assert matches is False
        assert "MUST" in warnings[0]

    def test_resolution_order_forbid_before_prefer(self) -> None:
        """FORBID is checked before PREFER scoring."""
        reqs = ModelRequirementSet(
            forbid={"deprecated": True}, prefer={"memory_gb": 16}
        )

        # Fails FORBID but would satisfy PREFER
        provider = {"deprecated": True, "memory_gb": 16}
        matches, score, _warnings = reqs.matches(provider)

        assert matches is False
        assert score == 0.0  # No scoring on failed match
