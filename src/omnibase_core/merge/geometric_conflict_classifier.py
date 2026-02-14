"""
Geometric Conflict Classifier for Parallel Agent Output Analysis.

Deterministic classifier that analyzes parallel agent outputs and classifies
conflicts using geometric similarity metrics. All classification is based on
pairwise value comparison with configurable thresholds.

Invariant D4:
    classify() is DETERMINISTIC: same inputs always produce same output.
    recommend_resolution() is ADVISORY ONLY: never authoritative.

See Also:
    - OMN-1854: GeometricConflictClassifier implementation
    - OMN-1853: ModelGeometricConflictDetails
    - OMN-1852: EnumMergeConflictType geometric types

.. versionadded:: 0.16.1
    Added as part of geometric conflict analysis (OMN-1854)
"""

from __future__ import annotations

import json
from collections import Counter

from omnibase_core.enums.enum_merge_conflict_type import EnumMergeConflictType
from omnibase_core.models.merge.model_geometric_conflict_details import (
    HUMAN_APPROVAL_REQUIRED_TYPES,
    ModelGeometricConflictDetails,
)

# Semantic contradiction pairs for _are_contradictory detection.
# Typed as frozenset[frozenset[object]] because pairs mix booleans and strings;
# a Union-based generic would add complexity without safety benefit here.
_CONTRADICTORY_PAIRS: frozenset[frozenset[object]] = frozenset(
    {
        frozenset({True, False}),
        frozenset({"enable", "disable"}),
        frozenset({"allow", "deny"}),
        frozenset({"yes", "no"}),
        frozenset({"on", "off"}),
        frozenset({"true", "false"}),
        frozenset({"accept", "reject"}),
        frozenset({"approve", "deny"}),
        frozenset({"approve", "reject"}),
        frozenset({"include", "exclude"}),
    }
)


class GeometricConflictClassifier:
    """Classify conflicts between parallel agent outputs using geometric analysis.

    All classification is deterministic: identical inputs always produce
    identical outputs (Invariant D4). No randomness, no ordering sensitivity.

    Class-level thresholds (override via subclass):
        IDENTICAL_THRESHOLD (0.99): Values are effectively the same.
        HIGH_SIMILARITY_THRESHOLD (0.85): Values are very similar.
        CONFLICTING_THRESHOLD (0.50): Partial overlap, needs resolution.

    .. versionadded:: 0.16.1
        Added as part of geometric conflict analysis (OMN-1854)
    """

    IDENTICAL_THRESHOLD: float = 0.99
    HIGH_SIMILARITY_THRESHOLD: float = 0.85
    CONFLICTING_THRESHOLD: float = 0.50

    def classify(
        self,
        base_value: object,
        values: list[tuple[str, object]],
    ) -> ModelGeometricConflictDetails:
        """Classify conflict between parallel agent outputs.

        DETERMINISTIC: Same inputs always produce same classification (D4).

        Args:
            base_value: The original value before agent modifications.
            values: List of (agent_name, value) pairs from parallel agents.
                Must contain at least 2 entries.

        Returns:
            ModelGeometricConflictDetails with classification and metrics.

        Raises:
            ValueError: If fewer than 2 agent values are provided.
        """
        if len(values) < 2:
            raise ValueError(  # error-ok: standard input validation at method boundary
                f"classify() requires at least 2 agent values, got {len(values)}"
            )

        # Compute all pairwise similarities (deterministic order)
        pairwise: list[float] = []
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                sim = self.compute_similarity(values[i][1], values[j][1])
                pairwise.append(sim)

        avg_similarity = sum(pairwise) / len(pairwise)

        # Multi-axis analysis
        structural = self._compute_structural_similarity(values)
        semantic = self._compute_semantic_similarity(values)

        # Affected fields
        affected_fields = self._compute_affected_fields(base_value, values)

        # Classify based on semantic signals and thresholds (cascading).
        #
        # Priority order:
        # 1. OPPOSITE: contradiction dominates - checked first so high-similarity
        #    dicts with a contradictory field are never silently classified IDENTICAL
        # 2. IDENTICAL: near-perfect match (only if no contradictions)
        # 3. ORTHOGONAL: structural non-overlap is independent of value similarity
        # 4. LOW_CONFLICT / CONFLICTING / AMBIGUOUS: threshold-based fallbacks
        contradictory = self._are_contradictory(values)
        orthogonal = self._are_orthogonal(base_value, values)

        if contradictory:
            conflict_type = EnumMergeConflictType.OPPOSITE
            explanation = (
                f"Agents produced contradictory conclusions "
                f"(similarity={avg_similarity:.3f})"
            )
        elif avg_similarity >= self.IDENTICAL_THRESHOLD:
            conflict_type = EnumMergeConflictType.IDENTICAL
            explanation = (
                f"All {len(values)} agents produced effectively identical output "
                f"(similarity={avg_similarity:.3f})"
            )
        elif orthogonal:
            conflict_type = EnumMergeConflictType.ORTHOGONAL
            explanation = (
                f"Agents modified non-overlapping aspects "
                f"(similarity={avg_similarity:.3f})"
            )
        elif avg_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            conflict_type = EnumMergeConflictType.LOW_CONFLICT
            explanation = (
                f"Minor differences between agent outputs "
                f"(similarity={avg_similarity:.3f})"
            )
        elif avg_similarity >= self.CONFLICTING_THRESHOLD:
            conflict_type = EnumMergeConflictType.CONFLICTING
            explanation = (
                f"Partial overlap between agent outputs requires resolution "
                f"(similarity={avg_similarity:.3f})"
            )
        else:
            conflict_type = EnumMergeConflictType.AMBIGUOUS
            explanation = (
                f"Cannot determine clear relationship between agent outputs "
                f"(similarity={avg_similarity:.3f})"
            )

        confidence = self._compute_confidence(pairwise, conflict_type)

        return ModelGeometricConflictDetails(
            conflict_type=conflict_type,
            similarity_score=avg_similarity,
            confidence=confidence,
            structural_similarity=structural,
            semantic_similarity=semantic,
            explanation=explanation,
            affected_fields=affected_fields,
        )

    def compute_similarity(self, value_a: object, value_b: object) -> float:
        """Compute similarity score between two values.

        Returns a float in [0.0, 1.0] where 1.0 means identical.

        Handles dicts (recursive key+value comparison), strings (Dice bigram
        coefficient), lists (Jaccard index via JSON serialization), and
        primitives (exact match).
        """
        norm_a = self._normalize(value_a)
        norm_b = self._normalize(value_b)

        if norm_a == norm_b:
            return 1.0

        if isinstance(norm_a, dict) and isinstance(norm_b, dict):
            return self._dict_similarity(norm_a, norm_b)

        # Numeric proximity: close numbers score higher than distant numbers.
        # Check before string branch; bool is excluded (subclass of int).
        if (
            isinstance(norm_a, (int, float))
            and isinstance(norm_b, (int, float))
            and not isinstance(norm_a, bool)
            and not isinstance(norm_b, bool)
        ):
            if norm_a == 0 and norm_b == 0:
                return 1.0
            return 1.0 - min(
                abs(norm_a - norm_b) / max(abs(norm_a), abs(norm_b), 1), 1.0
            )

        if isinstance(norm_a, str) and isinstance(norm_b, str):
            return self._string_similarity(norm_a, norm_b)

        if isinstance(norm_a, list) and isinstance(norm_b, list):
            return self._list_similarity(norm_a, norm_b)

        # Different types or non-comparable primitives
        if type(norm_a) is not type(norm_b):
            return 0.0

        return 0.0

    def recommend_resolution(
        self,
        details: ModelGeometricConflictDetails,
        values: list[tuple[str, object]],
    ) -> tuple[object, str]:
        """Recommend a resolution for the conflict.

        ADVISORY ONLY (GI-3). Raises ValueError for OPPOSITE/AMBIGUOUS conflicts
        that require human approval.

        Args:
            details: Classification result from classify().
            values: Original (agent_name, value) pairs.

        Returns:
            Tuple of (resolved_value, explanation_string).

        Raises:
            ValueError: For OPPOSITE or AMBIGUOUS conflicts (human approval required).
        """
        if details.conflict_type in HUMAN_APPROVAL_REQUIRED_TYPES:
            raise ValueError(  # error-ok: GI-3 contract enforcement at API boundary
                f"Cannot recommend resolution for {details.conflict_type.value} "
                f"conflicts. Human approval required (GI-3)."
            )

        if details.conflict_type == EnumMergeConflictType.IDENTICAL:
            return values[0][1], "All agents produced identical output"

        if details.conflict_type == EnumMergeConflictType.ORTHOGONAL:
            # Merge non-overlapping dict changes (guard: keys must be disjoint)
            if all(isinstance(v, dict) for _, v in values):
                # Pre-compute all pairwise overlaps so the error message names
                # both agents involved, not just the one accumulated last.
                agent_keys: list[tuple[str, set[str]]] = [
                    (name, set(v.keys()))  # type: ignore[attr-defined]
                    for name, v in values
                ]
                for i in range(len(agent_keys)):
                    for j in range(i + 1, len(agent_keys)):
                        overlap = agent_keys[i][1] & agent_keys[j][1]
                        if overlap:
                            raise ValueError(  # error-ok: API boundary guard against data loss
                                f"ORTHOGONAL merge requires disjoint keys, but "
                                f"agents '{agent_keys[i][0]}' and '{agent_keys[j][0]}' "
                                f"overlap on: {sorted(overlap)}"
                            )
                merged: dict[str, object] = {}
                for _, value in values:
                    merged.update(value)  # type: ignore[call-overload]
                return merged, "Merged non-overlapping changes from all agents"
            return (
                values[0][1],
                f"Selected output from {values[0][0]} (non-dict orthogonal)",
            )

        if details.conflict_type == EnumMergeConflictType.LOW_CONFLICT:
            return (
                values[0][1],
                f"Selected output from {values[0][0]} (highest priority, advisory)",
            )

        if details.conflict_type == EnumMergeConflictType.CONFLICTING:
            return (
                values[0][1],
                f"Selected output from {values[0][0]} (advisory, conflicts exist)",
            )

        raise ValueError(  # error-ok: defensive unreachable guard
            f"Unexpected conflict type: {details.conflict_type}"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _are_orthogonal(
        self,
        base_value: object,
        values: list[tuple[str, object]],
    ) -> bool:
        """Check if agent changes are non-overlapping (different keys modified)."""
        if not isinstance(base_value, dict):
            return False

        changed_key_sets: list[set[str]] = []
        for _, value in values:
            if not isinstance(value, dict):
                return False
            all_keys = set(base_value.keys()) | set(value.keys())
            changed = {k for k in all_keys if base_value.get(k) != value.get(k)}
            changed_key_sets.append(changed)

        # If all agents made zero changes, that is IDENTICAL, not orthogonal.
        # Empty sets are trivially disjoint, so without this guard the
        # pairwise check below would incorrectly return True.
        if all(len(cs) == 0 for cs in changed_key_sets):
            return False

        # All pairs must have disjoint change sets
        for i in range(len(changed_key_sets)):
            for j in range(i + 1, len(changed_key_sets)):
                if changed_key_sets[i] & changed_key_sets[j]:
                    return False

        return True

    def _are_contradictory(self, values: list[tuple[str, object]]) -> bool:
        """Check for boolean or semantic contradictions between agent outputs."""
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                if self._values_contradict(values[i][1], values[j][1]):
                    return True
        return False

    def _values_contradict(self, a: object, b: object) -> bool:
        """Check if two values form a known contradiction."""
        # Direct boolean contradiction
        if isinstance(a, bool) and isinstance(b, bool) and a is not b:
            return True

        # String semantic contradiction
        if isinstance(a, str) and isinstance(b, str):
            pair = frozenset({a.lower().strip(), b.lower().strip()})
            if pair in _CONTRADICTORY_PAIRS:
                return True

        # Dict value contradictions (check common keys recursively).
        # Ratio-based: for small dicts (<=2 common keys) any contradiction
        # suffices; for larger dicts, >50% of common keys must contradict
        # to avoid false positives where one field out of many differs.
        if isinstance(a, dict) and isinstance(b, dict):
            common_keys = sorted(set(a.keys()) & set(b.keys()))
            if not common_keys:
                return False
            contradictions = sum(
                1 for k in common_keys if self._values_contradict(a[k], b[k])
            )
            if contradictions == 0:
                return False
            if len(common_keys) <= 2:
                return True
            return contradictions / len(common_keys) > 0.5

        return False

    def _normalize(self, value: object) -> object:
        """Normalize a value for deterministic comparison.

        Sorts dict keys recursively. Preserves list ordering.
        """
        if isinstance(value, dict):
            return {k: self._normalize(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [self._normalize(v) for v in value]
        return value

    def _dict_similarity(
        self, dict_a: dict[str, object], dict_b: dict[str, object]
    ) -> float:
        """Compute similarity between two dicts using key overlap + value comparison.

        When all keys match (key_similarity=1.0), returns pure value similarity
        to prevent convergence to 1.0 for deeply nested dicts with differing leaves.
        """
        all_keys = set(dict_a.keys()) | set(dict_b.keys())
        if not all_keys:
            return 1.0

        common_keys = set(dict_a.keys()) & set(dict_b.keys())

        # Key overlap (Jaccard)
        key_similarity = len(common_keys) / len(all_keys)

        # Value similarity for common keys
        if common_keys:
            value_sims = [
                self.compute_similarity(dict_a[k], dict_b[k])
                for k in sorted(common_keys)
            ]
            value_similarity = sum(value_sims) / len(value_sims)
        else:
            value_similarity = 0.0

        # When keys are identical, structural info is trivial - use value similarity
        # directly to prevent convergence to 1.0 for deeply nested dicts.
        if key_similarity == 1.0:
            return value_similarity

        # Mixed: weight structure (key overlap) and content equally
        return 0.5 * key_similarity + 0.5 * value_similarity

    def _string_similarity(self, str_a: str, str_b: str) -> float:
        """Compute string similarity using multiset Dice coefficient on character bigrams.

        Uses Counter-based comparison so repeated bigrams affect the score
        (consistent with _list_similarity multiset approach).
        """
        if str_a == str_b:
            return 1.0
        if not str_a or not str_b:
            return 0.0

        bigrams_a = Counter(str_a[i : i + 2] for i in range(len(str_a) - 1))
        bigrams_b = Counter(str_b[i : i + 2] for i in range(len(str_b) - 1))

        if not bigrams_a and not bigrams_b:
            # Single-char strings that differ
            return 0.0

        # Multiset Dice: 2 * sum(min counts) / (total_a + total_b)
        intersection_size = sum(
            min(bigrams_a[k], bigrams_b.get(k, 0)) for k in bigrams_a
        )
        return (
            2 * intersection_size / (sum(bigrams_a.values()) + sum(bigrams_b.values()))
        )

    def _list_similarity(self, list_a: list[object], list_b: list[object]) -> float:
        """Compute list similarity using multiset Jaccard index on serialized elements.

        Uses Counter-based comparison so duplicate counts affect similarity
        (e.g. [1,1,2] vs [1,2,2] are not identical).
        """
        if not list_a and not list_b:
            return 1.0
        if not list_a or not list_b:
            return 0.0

        # Serialize elements for multiset comparison
        counter_a = Counter(self._to_json_str(x) for x in list_a)
        counter_b = Counter(self._to_json_str(x) for x in list_b)

        # Multiset Jaccard: sum(min counts) / sum(max counts)
        all_keys = set(counter_a.keys()) | set(counter_b.keys())
        intersection_size = sum(
            min(counter_a.get(k, 0), counter_b.get(k, 0)) for k in all_keys
        )
        union_size = sum(
            max(counter_a.get(k, 0), counter_b.get(k, 0)) for k in all_keys
        )

        if union_size == 0:
            return 1.0

        return intersection_size / union_size

    def _to_json_str(self, value: object) -> str:
        """Deterministic JSON serialization for set-based comparison."""
        return json.dumps(self._normalize(value), sort_keys=True, default=str)

    def _compute_structural_similarity(
        self,
        values: list[tuple[str, object]],
    ) -> float | None:
        """Compute structural similarity (key/type overlap) across agent outputs."""
        dicts = [v for _, v in values if isinstance(v, dict)]
        if len(dicts) < 2:
            return None

        similarities: list[float] = []
        for i in range(len(dicts)):
            for j in range(i + 1, len(dicts)):
                keys_a = set(dicts[i].keys())
                keys_b = set(dicts[j].keys())
                union = keys_a | keys_b
                if not union:
                    similarities.append(1.0)
                else:
                    similarities.append(len(keys_a & keys_b) / len(union))

        return sum(similarities) / len(similarities) if similarities else None

    def _compute_semantic_similarity(
        self,
        values: list[tuple[str, object]],
    ) -> float | None:
        """Compute semantic similarity (value content) across agent outputs."""
        dicts = [v for _, v in values if isinstance(v, dict)]
        if len(dicts) < 2:
            return None

        similarities: list[float] = []
        for i in range(len(dicts)):
            for j in range(i + 1, len(dicts)):
                common = sorted(set(dicts[i].keys()) & set(dicts[j].keys()))
                if not common:
                    similarities.append(0.0)
                    continue
                value_sims = [
                    self.compute_similarity(dicts[i][k], dicts[j][k]) for k in common
                ]
                similarities.append(sum(value_sims) / len(value_sims))

        return sum(similarities) / len(similarities) if similarities else None

    def _compute_affected_fields(
        self,
        base_value: object,
        values: list[tuple[str, object]],
    ) -> list[str]:
        """Compute sorted list of fields that differ from the base value."""
        if not isinstance(base_value, dict):
            return []

        affected: set[str] = set()
        for _, value in values:
            if isinstance(value, dict):
                all_keys = set(base_value.keys()) | set(value.keys())
                for key in all_keys:
                    if base_value.get(key) != value.get(key):
                        affected.add(key)

        return sorted(affected)

    def _compute_confidence(
        self,
        similarities: list[float],
        conflict_type: EnumMergeConflictType,
    ) -> float:
        """Compute confidence score based on similarity distribution and classification.

        High confidence when similarities agree (low spread) and the classification
        falls clearly within its threshold band.
        """
        if not similarities:
            return 1.0

        spread = max(similarities) - min(similarities) if len(similarities) > 1 else 0.0
        base_confidence = 1.0 - spread

        # Scale by how clearly the classification fits its threshold band
        confidence_scale = {
            EnumMergeConflictType.IDENTICAL: 1.0,
            EnumMergeConflictType.ORTHOGONAL: 0.90,
            EnumMergeConflictType.LOW_CONFLICT: 0.85,
            EnumMergeConflictType.CONFLICTING: 0.70,
            EnumMergeConflictType.OPPOSITE: 0.85,
            EnumMergeConflictType.AMBIGUOUS: 0.50,
        }
        scale = confidence_scale.get(conflict_type, 0.5)

        return max(0.0, min(1.0, base_confidence * scale))


__all__ = [
    "GeometricConflictClassifier",
]
