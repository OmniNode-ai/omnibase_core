"""
Unit tests for GeometricConflictClassifier.

Tests cover:
- Classification thresholds (IDENTICAL, ORTHOGONAL, LOW_CONFLICT, CONFLICTING, OPPOSITE, AMBIGUOUS)
- Determinism invariant (D4): same inputs always produce same output
- Similarity computation (dicts, strings, lists, primitives, mixed types)
- Contradiction detection (booleans, semantic pairs, recursive dict contradictions)
- Orthogonality detection (non-overlapping dict changes)
- Resolution recommendation (advisory only, ValueError for OPPOSITE/AMBIGUOUS)
- Edge cases (empty dicts, single-char strings, deeply nested values)

Related: OMN-1854, PR #502
"""

from typing import Any

import pytest

from omnibase_core.enums.enum_merge_conflict_type import EnumMergeConflictType
from omnibase_core.merge.geometric_conflict_classifier import (
    GeometricConflictClassifier,
)
from omnibase_core.models.merge.model_geometric_conflict_details import (
    ModelGeometricConflictDetails,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def classifier() -> GeometricConflictClassifier:
    return GeometricConflictClassifier()


# ------------------------------------------------------------------
# classify() tests
# ------------------------------------------------------------------


class TestClassifyIdentical:
    """Tests for IDENTICAL classification (similarity >= 0.99)."""

    def test_identical_dicts(self, classifier: GeometricConflictClassifier) -> None:
        result = classifier.classify(
            base_value={"key": "value"},
            values=[("agent-1", {"key": "value"}), ("agent-2", {"key": "value"})],
        )
        assert result.conflict_type == EnumMergeConflictType.IDENTICAL
        assert result.similarity_score >= 0.99

    def test_identical_strings(self, classifier: GeometricConflictClassifier) -> None:
        result = classifier.classify(
            base_value="hello",
            values=[("agent-1", "hello"), ("agent-2", "hello")],
        )
        assert result.conflict_type == EnumMergeConflictType.IDENTICAL

    def test_identical_nested_dicts(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        value = {"a": {"b": 1, "c": [1, 2, 3]}, "d": "text"}
        result = classifier.classify(
            base_value=value,
            values=[("agent-1", value), ("agent-2", value)],
        )
        assert result.conflict_type == EnumMergeConflictType.IDENTICAL

    def test_identical_three_agents(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value=42,
            values=[("a1", 42), ("a2", 42), ("a3", 42)],
        )
        assert result.conflict_type == EnumMergeConflictType.IDENTICAL


class TestClassifyOpposite:
    """Tests for OPPOSITE classification (contradictory values)."""

    def test_boolean_contradiction(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"approve": None},
            values=[("agent-1", {"approve": True}), ("agent-2", {"approve": False})],
        )
        assert result.conflict_type == EnumMergeConflictType.OPPOSITE

    def test_semantic_contradiction_enable_disable(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"mode": ""},
            values=[("agent-1", {"mode": "enable"}), ("agent-2", {"mode": "disable"})],
        )
        assert result.conflict_type == EnumMergeConflictType.OPPOSITE

    def test_semantic_contradiction_yes_no(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"answer": ""},
            values=[("agent-1", {"answer": "yes"}), ("agent-2", {"answer": "no"})],
        )
        assert result.conflict_type == EnumMergeConflictType.OPPOSITE

    def test_nested_boolean_contradiction(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"config": {"enabled": None}},
            values=[
                ("agent-1", {"config": {"enabled": True}}),
                ("agent-2", {"config": {"enabled": False}}),
            ],
        )
        assert result.conflict_type == EnumMergeConflictType.OPPOSITE


class TestClassifyOrthogonal:
    """Tests for ORTHOGONAL classification (non-overlapping changes)."""

    def test_different_keys_modified(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        base = {"name": "original", "age": 0, "city": "none"}
        result = classifier.classify(
            base_value=base,
            values=[
                ("agent-1", {"name": "alice", "age": 0, "city": "none"}),
                ("agent-2", {"name": "original", "age": 30, "city": "none"}),
            ],
        )
        assert result.conflict_type == EnumMergeConflictType.ORTHOGONAL

    def test_three_agents_orthogonal(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        base = {"a": 0, "b": 0, "c": 0, "d": "shared", "e": "shared"}
        result = classifier.classify(
            base_value=base,
            values=[
                ("agent-1", {"a": 1, "b": 0, "c": 0, "d": "shared", "e": "shared"}),
                ("agent-2", {"a": 0, "b": 2, "c": 0, "d": "shared", "e": "shared"}),
                ("agent-3", {"a": 0, "b": 0, "c": 3, "d": "shared", "e": "shared"}),
            ],
        )
        assert result.conflict_type == EnumMergeConflictType.ORTHOGONAL


class TestClassifyLowConflict:
    """Tests for LOW_CONFLICT classification (similar but overlapping)."""

    def test_same_key_similar_values(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        base = {"description": "original text", "status": "active", "count": 10}
        result = classifier.classify(
            base_value=base,
            values=[
                (
                    "agent-1",
                    {
                        "description": "original text updated",
                        "status": "active",
                        "count": 10,
                    },
                ),
                (
                    "agent-2",
                    {
                        "description": "original text modified",
                        "status": "active",
                        "count": 10,
                    },
                ),
            ],
        )
        # Both modify same key (description) so not orthogonal,
        # but high similarity -> LOW_CONFLICT
        assert result.conflict_type == EnumMergeConflictType.LOW_CONFLICT


class TestClassifyConflicting:
    """Tests for CONFLICTING classification (moderate similarity)."""

    def test_partial_overlap(self, classifier: GeometricConflictClassifier) -> None:
        """Same keys, majority of values match, one differs -> CONFLICTING (0.5-0.85)."""
        result = classifier.classify(
            base_value={"a": 1, "b": 2, "c": 3, "d": 4},
            values=[
                ("agent-1", {"a": 1, "b": 2, "c": 3, "d": 40}),
                ("agent-2", {"a": 1, "b": 2, "c": 3, "d": 400}),
            ],
        )
        assert result.conflict_type == EnumMergeConflictType.CONFLICTING


class TestClassifyAmbiguous:
    """Tests for AMBIGUOUS classification (unclear relationship)."""

    def test_different_types_no_contradiction(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value="original",
            values=[("agent-1", "completely different text"), ("agent-2", 42)],
        )
        assert result.conflict_type == EnumMergeConflictType.AMBIGUOUS


# ------------------------------------------------------------------
# Determinism (D4) tests
# ------------------------------------------------------------------


class TestDeterminism:
    """Invariant D4: same inputs always produce same output."""

    def test_classify_deterministic_10_runs(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        results: list[EnumMergeConflictType] = []
        for _ in range(10):
            result = classifier.classify(
                base_value={"key": "original"},
                values=[
                    ("agent-1", {"key": "modified-a"}),
                    ("agent-2", {"key": "modified-b"}),
                ],
            )
            results.append(result.conflict_type)
        assert len(set(results)) == 1, f"Non-deterministic: {results}"

    def test_classify_deterministic_complex(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Complex nested input should still be deterministic."""
        base = {"config": {"level": 1, "tags": ["a", "b"]}, "name": "test"}
        vals: list[tuple[str, Any]] = [
            ("a1", {"config": {"level": 2, "tags": ["a", "c"]}, "name": "test"}),
            ("a2", {"config": {"level": 3, "tags": ["b", "d"]}, "name": "modified"}),
        ]
        results = [classifier.classify(base, vals).conflict_type for _ in range(10)]
        assert len(set(results)) == 1

    def test_similarity_deterministic(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        scores = [
            classifier.compute_similarity(
                {"a": 1, "b": "hello"}, {"a": 2, "b": "world"}
            )
            for _ in range(10)
        ]
        assert len(set(scores)) == 1


# ------------------------------------------------------------------
# compute_similarity() tests
# ------------------------------------------------------------------


class TestComputeSimilarity:
    """Tests for the similarity computation engine."""

    def test_identical_values_score_1(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity({"a": 1}, {"a": 1}) == 1.0
        assert classifier.compute_similarity("hello", "hello") == 1.0
        assert classifier.compute_similarity([1, 2, 3], [1, 2, 3]) == 1.0
        assert classifier.compute_similarity(42, 42) == 1.0
        assert classifier.compute_similarity(None, None) == 1.0

    def test_different_types_score_0(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity("hello", 42) == 0.0
        assert classifier.compute_similarity({"a": 1}, [1, 2]) == 0.0

    def test_dict_partial_overlap(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        score = classifier.compute_similarity({"a": 1, "b": 2}, {"a": 1, "c": 3})
        # key_sim = 1/3, value_sim for 'a' = 1.0 -> combined
        assert 0.0 < score < 1.0

    def test_empty_dicts_identical(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity({}, {}) == 1.0

    def test_string_similarity_high(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        score = classifier.compute_similarity("hello world", "hello worlds")
        assert score > 0.8

    def test_string_similarity_low(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        score = classifier.compute_similarity("abc", "xyz")
        assert score < 0.3

    def test_list_identical_elements(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity([1, 2, 3], [1, 2, 3]) == 1.0

    def test_list_partial_overlap(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        score = classifier.compute_similarity([1, 2, 3], [2, 3, 4])
        assert 0.3 < score < 0.8

    def test_list_no_overlap(self, classifier: GeometricConflictClassifier) -> None:
        score = classifier.compute_similarity([1, 2], [3, 4])
        assert score == 0.0

    def test_empty_lists_identical(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity([], []) == 1.0

    def test_empty_vs_nonempty_list(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity([], [1, 2]) == 0.0

    def test_bool_same(self, classifier: GeometricConflictClassifier) -> None:
        assert classifier.compute_similarity(True, True) == 1.0

    def test_bool_different(self, classifier: GeometricConflictClassifier) -> None:
        assert classifier.compute_similarity(True, False) == 0.0

    def test_nested_dict_similarity(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Recursive dict comparison should work for nested structures."""
        a = {"config": {"level": 1, "enabled": True}}
        b = {"config": {"level": 1, "enabled": False}}
        score = classifier.compute_similarity(a, b)
        assert 0.0 < score < 1.0

    def test_single_char_strings(self, classifier: GeometricConflictClassifier) -> None:
        """Single character strings have no bigrams - should handle gracefully."""
        score = classifier.compute_similarity("a", "b")
        assert score == 0.0


# ------------------------------------------------------------------
# recommend_resolution() tests
# ------------------------------------------------------------------


class TestRecommendResolution:
    """Tests for advisory resolution recommendations."""

    def test_identical_returns_first_value(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.IDENTICAL,
            similarity_score=1.0,
            confidence=1.0,
            explanation="Identical",
        )
        value, explanation = classifier.recommend_resolution(
            details, [("agent-1", {"key": "value"}), ("agent-2", {"key": "value"})]
        )
        assert value == {"key": "value"}
        assert "identical" in explanation.lower()

    def test_orthogonal_merges_dicts(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.ORTHOGONAL,
            similarity_score=0.9,
            confidence=0.9,
            explanation="Orthogonal",
        )
        value, explanation = classifier.recommend_resolution(
            details,
            [("agent-1", {"a": 1}), ("agent-2", {"b": 2})],
        )
        assert value == {"a": 1, "b": 2}
        assert "merged" in explanation.lower()

    def test_low_conflict_picks_first(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.LOW_CONFLICT,
            similarity_score=0.88,
            confidence=0.85,
            explanation="Low conflict",
        )
        value, _ = classifier.recommend_resolution(
            details,
            [("agent-1", {"key": "a"}), ("agent-2", {"key": "b"})],
        )
        assert value == {"key": "a"}

    def test_conflicting_picks_first_advisory(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.CONFLICTING,
            similarity_score=0.55,
            confidence=0.6,
            explanation="Conflicting",
        )
        _, explanation = classifier.recommend_resolution(
            details,
            [("agent-1", {"key": "a"}), ("agent-2", {"key": "b"})],
        )
        assert "advisory" in explanation.lower()

    def test_opposite_raises_valueerror(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            similarity_score=0.1,
            confidence=0.8,
            explanation="Opposite",
        )
        with pytest.raises(ValueError, match="Human approval required"):
            classifier.recommend_resolution(
                details,
                [("agent-1", {"approve": True}), ("agent-2", {"approve": False})],
            )

    def test_ambiguous_raises_valueerror(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.AMBIGUOUS,
            similarity_score=0.3,
            confidence=0.4,
            explanation="Ambiguous",
        )
        with pytest.raises(ValueError, match="Human approval required"):
            classifier.recommend_resolution(
                details,
                [("agent-1", "text"), ("agent-2", 42)],
            )


# ------------------------------------------------------------------
# Edge cases and validation
# ------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and input validation."""

    def test_classify_single_value_raises(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            classifier.classify(
                base_value={"key": "value"},
                values=[("agent-1", {"key": "value"})],
            )

    def test_classify_empty_values_raises(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            classifier.classify(base_value={}, values=[])

    def test_result_is_frozen(self, classifier: GeometricConflictClassifier) -> None:
        result = classifier.classify(
            base_value={"key": "value"},
            values=[("agent-1", {"key": "value"}), ("agent-2", {"key": "value"})],
        )
        with pytest.raises(Exception):
            result.conflict_type = EnumMergeConflictType.AMBIGUOUS  # type: ignore[misc]

    def test_affected_fields_populated_for_dict_changes(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"name": "original", "age": 0},
            values=[
                ("agent-1", {"name": "alice", "age": 0}),
                ("agent-2", {"name": "original", "age": 30}),
            ],
        )
        assert "name" in result.affected_fields
        assert "age" in result.affected_fields

    def test_affected_fields_sorted(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"z": 0, "a": 0, "m": 0},
            values=[
                ("agent-1", {"z": 1, "a": 1, "m": 0}),
                ("agent-2", {"z": 0, "a": 0, "m": 1}),
            ],
        )
        assert result.affected_fields == sorted(result.affected_fields)

    def test_confidence_between_0_and_1(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"key": "value"},
            values=[("agent-1", {"key": "a"}), ("agent-2", {"key": "b"})],
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_similarity_score_between_0_and_1(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"key": "value"},
            values=[("agent-1", {"key": "a"}), ("agent-2", {"key": "b"})],
        )
        assert 0.0 <= result.similarity_score <= 1.0

    def test_structural_similarity_populated_for_dicts(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"a": 1},
            values=[("agent-1", {"a": 2}), ("agent-2", {"a": 3})],
        )
        assert result.structural_similarity is not None

    def test_structural_similarity_none_for_non_dicts(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value="hello",
            values=[("agent-1", "hello"), ("agent-2", "hello")],
        )
        assert result.structural_similarity is None

    def test_explanation_not_empty(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        result = classifier.classify(
            base_value={"key": "value"},
            values=[("agent-1", {"key": "value"}), ("agent-2", {"key": "value"})],
        )
        assert len(result.explanation) > 0

    def test_none_values_handled(self, classifier: GeometricConflictClassifier) -> None:
        """None values should not crash the classifier."""
        result = classifier.classify(
            base_value=None,
            values=[("agent-1", None), ("agent-2", None)],
        )
        assert result.conflict_type == EnumMergeConflictType.IDENTICAL


class TestDeepNesting:
    """Regression tests for deeply nested dict similarity convergence."""

    def test_deeply_nested_different_leaves_not_identical(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Deeply nested dicts with different leaf values must NOT be IDENTICAL."""

        def nest(value: object, depth: int) -> dict[str, object]:
            result: dict[str, object] = {"leaf": value}
            for _ in range(depth):
                result = {"nested": result}
            return result

        a = nest(1, 15)
        b = nest(999, 15)
        score = classifier.compute_similarity(a, b)
        assert score < 0.99, f"Deeply nested dicts converged to {score}"

    def test_deeply_nested_classify_not_identical(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """classify() should not report IDENTICAL for deeply nested differing dicts."""

        def nest(value: object, depth: int) -> dict[str, object]:
            result: dict[str, object] = {"leaf": value}
            for _ in range(depth):
                result = {"nested": result}
            return result

        base = nest("original", 10)
        result = classifier.classify(
            base_value=base,
            values=[
                ("agent-1", nest("changed-a", 10)),
                ("agent-2", nest("changed-b", 10)),
            ],
        )
        assert result.conflict_type != EnumMergeConflictType.IDENTICAL


class TestMultisetListSimilarity:
    """Tests verifying Counter-based multiset Jaccard for list similarity."""

    def test_duplicate_counts_affect_similarity(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Lists with same elements but different counts should NOT score 1.0."""
        score = classifier.compute_similarity([1, 1, 1, 2], [1, 2, 2, 2])
        assert score < 1.0, (
            f"Multiset Jaccard should distinguish duplicates, got {score}"
        )

    def test_identical_duplicates_score_1(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity([1, 1, 2, 2], [1, 1, 2, 2]) == 1.0


class TestOrthogonalNonDict:
    """Tests for recommend_resolution ORTHOGONAL with non-dict values."""

    def test_orthogonal_non_dict_picks_first(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.ORTHOGONAL,
            similarity_score=0.9,
            confidence=0.9,
            explanation="Orthogonal non-dict",
        )
        value, explanation = classifier.recommend_resolution(
            details,
            [("agent-1", "text-a"), ("agent-2", "text-b")],
        )
        assert value == "text-a"
        assert "non-dict" in explanation.lower()

    def test_orthogonal_overlapping_keys_raises(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """ORTHOGONAL merge with overlapping dict keys should raise ValueError."""
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.ORTHOGONAL,
            similarity_score=0.9,
            confidence=0.9,
            explanation="Orthogonal",
        )
        with pytest.raises(ValueError, match="disjoint keys"):
            classifier.recommend_resolution(
                details,
                [("agent-1", {"shared": "first"}), ("agent-2", {"shared": "second"})],
            )

    def test_orthogonal_overlap_names_both_agents(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Overlap error message should name both agents involved."""
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.ORTHOGONAL,
            similarity_score=0.9,
            confidence=0.9,
            explanation="Orthogonal",
        )
        with pytest.raises(ValueError, match=r"agent-1.*agent-3|agent-3.*agent-1"):
            classifier.recommend_resolution(
                details,
                [
                    ("agent-1", {"shared": "first", "a": 1}),
                    ("agent-2", {"b": 2}),
                    ("agent-3", {"shared": "third", "c": 3}),
                ],
            )


class TestMixedTypeAgents:
    """Tests for >2 agents with mixed value types."""

    def test_three_agents_mixed_types(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Three agents with mixed types should classify without crashing."""
        result = classifier.classify(
            base_value="original",
            values=[("a1", "modified"), ("a2", 42), ("a3", {"key": "value"})],
        )
        assert result.conflict_type is not None
        assert 0.0 <= result.similarity_score <= 1.0


class TestMixedDictAndNonDict:
    """Tests for mixed dict/non-dict values across agents."""

    def test_classify_mixed_dict_and_non_dict_values(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """One agent returns a dict, another returns a string for the same field."""
        result = classifier.classify(
            base_value={"key": "original"},
            values=[
                ("agent-1", {"key": "updated"}),
                ("agent-2", "just a string"),
            ],
        )
        # Different types should not be IDENTICAL or ORTHOGONAL
        assert result.conflict_type not in {
            EnumMergeConflictType.IDENTICAL,
            EnumMergeConflictType.ORTHOGONAL,
        }
        assert 0.0 <= result.similarity_score <= 1.0


class TestConflictingAutoResolvable:
    """Tests that CONFLICTING classification is NOT auto-resolvable."""

    def test_conflicting_not_auto_resolvable(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """CONFLICTING classification must have auto_resolvable=False."""
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.CONFLICTING,
            similarity_score=0.55,
            confidence=0.6,
            explanation="Partial overlap",
        )
        assert details.is_auto_resolvable() is False
        assert details.requires_human_approval() is False


class TestNumericProximitySimilarity:
    """Tests for numeric proximity in compute_similarity()."""

    def test_close_numbers_higher_than_distant(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Close numbers should score higher than distant numbers."""
        close_score = classifier.compute_similarity(100, 101)
        distant_score = classifier.compute_similarity(100, 999999)
        assert close_score > distant_score

    def test_identical_numbers_score_1(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        assert classifier.compute_similarity(42, 42) == 1.0
        assert classifier.compute_similarity(0.5, 0.5) == 1.0

    def test_both_zero_score_1(self, classifier: GeometricConflictClassifier) -> None:
        assert classifier.compute_similarity(0, 0) == 1.0
        assert classifier.compute_similarity(0.0, 0.0) == 1.0

    def test_numeric_proximity_range(
        self, classifier: GeometricConflictClassifier
    ) -> None:
        """Numeric similarity should be in [0.0, 1.0]."""
        score = classifier.compute_similarity(1, 1000)
        assert 0.0 <= score <= 1.0

    def test_float_proximity(self, classifier: GeometricConflictClassifier) -> None:
        score = classifier.compute_similarity(1.0, 1.1)
        assert score > 0.8


class TestModuleExports:
    """Test that module exports are correct."""

    def test_classifier_importable_from_merge(self) -> None:
        from omnibase_core.merge import GeometricConflictClassifier as Cls

        assert Cls is GeometricConflictClassifier
