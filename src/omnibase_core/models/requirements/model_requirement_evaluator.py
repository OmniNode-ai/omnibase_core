"""
Requirement evaluator model for expressing and evaluating requirements with graduated strictness.

This module provides the ModelRequirementEvaluator class which enables expressing
requirements across four tiers: must (hard requirements), prefer (soft preferences),
forbid (exclusions), and hints (non-binding tie-breakers).

The evaluator includes matching, scoring, and sorting functionality for provider selection.

Note:
    This is distinct from omnibase_core.models.capabilities.ModelRequirementSet which
    is a simpler data model without evaluation logic. Use ModelRequirementEvaluator
    when you need `matches()`, `sort_key()`, and operator support ($eq, $ne, etc.).
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.types.type_json import JsonType

__all__ = [
    "ModelRequirementEvaluator",
]

logger = logging.getLogger(__name__)


class ModelRequirementEvaluator(BaseModel):
    """Evaluates requirements with graduated strictness and provider matching.

    Four tiers of requirement strictness:
    - must: Hard requirements. Provider MUST satisfy all. Failure = no match.
    - prefer: Soft preferences. Improves score if satisfied. Failure = warning.
    - forbid: Exclusions. Provider MUST NOT have these. Presence = no match.
    - hints: Non-binding hints. May influence tie-breaking. Never causes failure.

    Comparison Semantics:
    - Key-name heuristics: max_* keys use <=, min_* keys use >=, others use ==
    - Operator support: $eq, $ne, $lt, $lte, $gt, $gte, $in, $contains

    Thread Safety:
        This class is thread-safe for read operations. The model is frozen
        (immutable after creation), so instances can be safely shared across
        threads. However, the provider Mapping passed to matches() and sort_key()
        should not be modified during method execution.

        For thread safety patterns, see: docs/guides/THREADING.md

    Caching:
        The sort_key() and matches() methods do not cache results internally
        because provider Mappings are mutable and not hashable. For performance
        optimization when sorting many providers:
        1. Use sort_providers() method for efficient batch sorting
        2. Cache results externally if providers are known to be immutable
        3. Convert providers to frozen/hashable forms for caching if needed

    Validation:
        Two levels of validation are available:

        **Automatic (during construction)**:
            The `_validate_no_conflicts()` model validator runs automatically
            when creating an instance. It raises `ValueError` immediately if
            the same key has identical values in both `must` and `forbid`
            (a logical impossibility).

        **Manual (call explicitly)**:
            The `validate_requirements()` method performs additional advisory
            checks and must be called explicitly. It returns a list of warnings
            (does not raise exceptions) for:
            - Non-hashable values that may cause issues with set operations
            - Keys appearing in multiple tiers (e.g., both `prefer` and `hints`)

        Call `validate_requirements()` when you want comprehensive validation
        during development/debugging, or when processing user-provided configs
        where additional warnings are helpful.

        Example:
            >>> reqs = ModelRequirementEvaluator(
            ...     must={"region": "us-east-1"},
            ...     prefer={"region": "us-west-2"},  # Same key in different tier
            ... )
            >>> warnings = reqs.validate_requirements()
            >>> if warnings:
            ...     for w in warnings:
            ...         print(f"Warning: {w}")
            Warning: Key 'region' appears in multiple tiers: ['must', 'prefer']. ...

    Example:
        >>> reqs = ModelRequirementEvaluator(
        ...     must={"region": "us-east-1", "max_latency_ms": 20},
        ...     prefer={"memory_gb": 16},
        ...     forbid={"deprecated": True},
        ...     hints={"tier": "premium"}
        ... )
        >>> provider = {"region": "us-east-1", "latency_ms": 15, "memory_gb": 8}
        >>> matches, score, warnings = reqs.matches(provider)
    """

    must: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Hard requirements. Provider MUST satisfy all. Failure = no match.",
    )
    prefer: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Soft preferences. Improves score if satisfied. Failure = warning.",
    )
    forbid: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Exclusions. Provider MUST NOT have these. Presence = no match.",
    )
    hints: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Non-binding hints. May influence tie-breaking. Never causes failure.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @model_validator(mode="after")
    def _validate_no_conflicts(self) -> ModelRequirementEvaluator:
        """Validate that there are no logical conflicts in requirements.

        Checks for:
        - Same key appearing in both must and forbid with equal values
        - Keys in must that are also in forbid (potential conflict)

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If logical conflicts are detected.
        """
        # Check for direct conflicts: same key in must and forbid with equal values
        for key in self.must:
            if key in self.forbid:
                must_val = self.must[key]
                forbid_val = self.forbid[key]
                # If values are equal, this is a definite conflict
                if must_val == forbid_val:
                    raise ValueError(
                        f"Logical conflict: key '{key}' has same value "
                        f"({must_val!r}) in both 'must' and 'forbid'"
                    )
                # Log warning for same key with different values (potential issue)
                logger.warning(
                    "Key '%s' appears in both 'must' and 'forbid' with different values. "
                    "This may indicate a configuration issue.",
                    key,
                )
        return self

    def validate_requirements(self) -> list[str]:
        """Validate requirements for logical consistency and hashability.

        Performs comprehensive validation including:
        - Checking for logical conflicts (same item in must and forbid)
        - Verifying that values used in set operations are hashable
        - Checking list elements for hashability when used in comparisons

        Returns:
            A list of validation warnings (empty if all valid).
            Critical errors are raised as exceptions during model construction.

        Example:
            >>> reqs = ModelRequirementEvaluator(must={"region": "us-east-1"})
            >>> warnings = reqs.validate_requirements()
            >>> if warnings:
            ...     print("Warnings:", warnings)
        """
        validation_warnings: list[str] = []

        # Check hashability of values that may be used in set operations
        for tier_name, tier_dict in [
            ("must", self.must),
            ("prefer", self.prefer),
            ("forbid", self.forbid),
            ("hints", self.hints),
        ]:
            for key, value in tier_dict.items():
                # Check if value is hashable (needed for some comparisons)
                if not self._is_hashable(value):
                    validation_warnings.append(
                        f"{tier_name}.{key}: Value {value!r} is not hashable. "
                        "This may cause issues with set-based comparisons."
                    )
                # Check list elements for hashability
                if isinstance(value, list):
                    for i, item in enumerate(value):
                        if not self._is_hashable(item):
                            validation_warnings.append(
                                f"{tier_name}.{key}[{i}]: List element {item!r} "
                                "is not hashable. Set operations will use fallback."
                            )

        # Check for keys that appear in multiple tiers (may be intentional but worth noting)
        all_keys = set(self.must.keys()) | set(self.prefer.keys())
        all_keys |= set(self.forbid.keys()) | set(self.hints.keys())

        for key in all_keys:
            tiers_containing = []
            if key in self.must:
                tiers_containing.append("must")
            if key in self.prefer:
                tiers_containing.append("prefer")
            if key in self.forbid:
                tiers_containing.append("forbid")
            if key in self.hints:
                tiers_containing.append("hints")

            if len(tiers_containing) > 1:
                # Skip must+forbid conflict (already checked in validator)
                if tiers_containing != ["must", "forbid"]:
                    validation_warnings.append(
                        f"Key '{key}' appears in multiple tiers: {tiers_containing}. "
                        "This may be intentional but verify the logic."
                    )

        return validation_warnings

    def _is_hashable(self, value: Any) -> bool:
        """Check if a value is hashable.

        Args:
            value: The value to check.

        Returns:
            True if the value is hashable, False otherwise.
        """
        try:
            hash(value)
            return True
        except TypeError:
            return False

    def matches(self, provider: Mapping[str, Any]) -> tuple[bool, float, list[str]]:
        """Check if provider satisfies requirements.

        Resolution order:
        1. Filter by MUST: All must requirements must be satisfied
        2. Filter by FORBID: No forbid requirements can be present
        3. Score by PREFER: Each satisfied preference adds +1.0 to score

        Args:
            provider: A mapping of provider capabilities/attributes.

        Returns:
            A tuple of (matches: bool, score: float, warnings: list[str]).
            - matches: True if all MUST requirements satisfied and no FORBID present
            - score: Sum of +1.0 for each satisfied PREFER constraint
            - warnings: List of unmet PREFER constraints (informational)
        """
        match_warnings: list[str] = []

        # Step 1: Check MUST requirements (all must be satisfied)
        for key, requirement in self.must.items():
            if not self._check_requirement(key, requirement, provider):
                # MUST not satisfied = no match
                return (False, 0.0, [f"MUST requirement not satisfied: {key}"])

        # Step 2: Check FORBID requirements (none can be present/satisfied)
        for key, requirement in self.forbid.items():
            if self._check_forbid(key, requirement, provider):
                # FORBID requirement present = no match
                return (False, 0.0, [f"FORBID requirement violated: {key}"])

        # Step 3: Calculate PREFER score
        score = 0.0
        for key, requirement in self.prefer.items():
            if self._check_requirement(key, requirement, provider):
                score += 1.0
            else:
                match_warnings.append(f"PREFER not satisfied: {key}")

        return (True, score, match_warnings)

    def sort_key(self, provider: Mapping[str, Any]) -> tuple[float, int, str]:
        """Return sort key for ordering providers by match quality.

        This method computes a composite sort key that enables deterministic
        ordering of providers based on how well they match the requirements.
        The key is designed for use with Python's sorted() function.

        Sorting Algorithm:
            The sort key is a 3-tuple ordered by priority:
            1. Score (negated): Higher preference scores sort first
            2. Hint rank: Fewer unmatched hints sort first
            3. Deterministic fallback: Ensures stable ordering for equal scores

        The negation of score allows ascending sort to produce best-matches-first
        ordering. Non-matching providers receive (inf, 999, "") to sort last.

        Performance Note:
            This method calls matches() internally, which evaluates all
            requirements. For sorting many providers, consider using
            sort_providers() which may optimize repeated evaluations.

            Results are NOT cached internally because provider Mappings are
            mutable and not hashable. For performance-critical code, cache
            results externally or ensure providers are converted to hashable
            forms before repeated calls.

        Args:
            provider: A mapping of provider capabilities/attributes.

        Returns:
            A 3-tuple suitable for sorting:
            - Element 0 (float): Negated score so higher scores sort first.
                Non-matching providers return float('inf').
            - Element 1 (int): Hint rank (count of unmatched hints).
                Lower is better. Non-matching providers return 999.
            - Element 2 (str): Deterministic fallback for stable ordering.
                Uses provider 'id', 'name', or hash of provider.

        Example:
            >>> reqs = ModelRequirementEvaluator(prefer={"speed": "fast"})
            >>> providers = [{"name": "A", "speed": "fast"}, {"name": "B"}]
            >>> sorted_providers = sorted(providers, key=reqs.sort_key)
            >>> [p["name"] for p in sorted_providers]
            ['A', 'B']
        """
        matches, score, _ = self.matches(provider)

        # If doesn't match, give worst possible score
        if not matches:
            return (float("inf"), 999, "")

        # Calculate hint rank (lower is better)
        hint_rank = 0
        for key, requirement in self.hints.items():
            if not self._check_requirement(key, requirement, provider):
                hint_rank += 1

        # Deterministic fallback using provider id or name or hash
        fallback = self._compute_deterministic_fallback(provider)

        # Negate score so higher scores sort first in ascending order
        return (-score, hint_rank, fallback)

    def _compute_deterministic_fallback(self, provider: Mapping[str, Any]) -> str:
        """Compute a deterministic fallback string for stable sort ordering.

        Args:
            provider: The provider mapping.

        Returns:
            A string suitable for tie-breaking in sorts.
        """
        if "id" in provider:
            return str(provider["id"])
        if "name" in provider:
            return str(provider["name"])
        # Use try/except to handle unhashable values in provider dict
        try:
            return str(
                hash(
                    frozenset(provider.items())
                    if isinstance(provider, dict)
                    else id(provider)
                )
            )
        except TypeError:
            # Fallback for unhashable values (lists, dicts, etc.)
            return str(id(provider))

    def sort_providers(
        self,
        providers: Sequence[Mapping[str, Any]],
        *,
        reverse: bool = False,
    ) -> list[Mapping[str, Any]]:
        """Sort providers by match quality with optimized batch processing.

        This method provides an efficient way to sort multiple providers,
        potentially with internal caching optimizations for repeated
        requirement evaluations.

        Args:
            providers: Sequence of provider mappings to sort.
            reverse: If True, sort worst matches first (default: False).

        Returns:
            A new list of providers sorted by match quality.
            Best matches appear first unless reverse=True.

        Example:
            >>> reqs = ModelRequirementEvaluator(must={"active": True})
            >>> providers = [
            ...     {"name": "A", "active": False},
            ...     {"name": "B", "active": True},
            ... ]
            >>> sorted_list = reqs.sort_providers(providers)
            >>> [p["name"] for p in sorted_list]
            ['B', 'A']
        """
        # Cache sort keys for efficiency when sorting
        # Using a list of tuples to preserve order and enable caching
        keyed_providers = [(self.sort_key(p), p) for p in providers]
        keyed_providers.sort(key=lambda x: x[0], reverse=reverse)
        return [p for _, p in keyed_providers]

    def _check_requirement(
        self,
        key: str,
        requirement: Any,
        provider: Mapping[str, Any],
    ) -> bool:
        """Check if a single requirement is satisfied by the provider.

        Handles:
        - Explicit operators ($eq, $ne, $lt, $lte, $gt, $gte, $in, $contains)
        - Key-name heuristics (max_* uses <=, min_* uses >=)
        - List matching (any-of semantics)

        Args:
            key: The requirement key name.
            requirement: The requirement value (can include operators).
            provider: The provider mapping to check against.

        Returns:
            True if the requirement is satisfied.
        """
        # Extract the actual key to look up in provider
        # e.g., "max_latency_ms" looks up "latency_ms" or "max_latency_ms"
        lookup_key = self._get_lookup_key(key)
        provider_value = provider.get(lookup_key)

        # If key doesn't exist in provider, also try the original key
        if provider_value is None and lookup_key != key:
            provider_value = provider.get(key)

        # Handle explicit operator syntax
        if isinstance(requirement, dict) and self._has_operator(requirement):
            return self._evaluate_operators(requirement, provider_value)

        # Handle list requirements (any-of semantics)
        if isinstance(requirement, list):
            return self._check_list_requirement(requirement, provider_value)

        # Apply key-name heuristics
        if key.startswith("max_"):
            return self._compare_lte(provider_value, requirement)
        elif key.startswith("min_"):
            return self._compare_gte(provider_value, requirement)
        else:
            return self._compare_eq(provider_value, requirement)

    def _check_forbid(
        self,
        key: str,
        requirement: Any,
        provider: Mapping[str, Any],
    ) -> bool:
        """Check if a forbid requirement is violated.

        A forbid requirement is violated if the provider has the forbidden
        value or matches the forbidden pattern.

        Args:
            key: The forbid key name.
            requirement: The forbidden value/pattern.
            provider: The provider mapping to check against.

        Returns:
            True if the forbid is VIOLATED (provider has forbidden value).
        """
        lookup_key = self._get_lookup_key(key)
        provider_value = provider.get(lookup_key)

        # If key doesn't exist in provider, also try the original key
        if provider_value is None and lookup_key != key:
            provider_value = provider.get(key)

        # If key not present in provider, forbid is not violated
        if key not in provider and lookup_key not in provider:
            return False

        # Handle explicit operator syntax
        if isinstance(requirement, dict) and self._has_operator(requirement):
            return self._evaluate_operators(requirement, provider_value)

        # Handle list requirements
        if isinstance(requirement, list):
            return self._check_list_requirement(requirement, provider_value)

        # For forbid, we check equality - if provider has the forbidden value
        return self._compare_eq(provider_value, requirement)

    def _get_lookup_key(self, key: str) -> str:
        """Get the provider key to look up for a given requirement key.

        For max_* and min_* keys, strips the prefix if that's more likely
        to match the provider's attribute naming.

        Args:
            key: The requirement key.

        Returns:
            The key to look up in the provider.
        """
        if key.startswith("max_"):
            return key[4:]  # Strip "max_" prefix
        elif key.startswith("min_"):
            return key[4:]  # Strip "min_" prefix
        return key

    def _has_operator(self, requirement: dict[str, JsonType]) -> bool:
        """Check if a dict requirement contains operator syntax.

        Args:
            requirement: The requirement dict to check.

        Returns:
            True if any key starts with '$'.
        """
        return any(k.startswith("$") for k in requirement)

    def _evaluate_operators(
        self,
        requirement: dict[str, JsonType],
        provider_value: Any,
    ) -> bool:
        """Evaluate explicit operator expressions.

        Supported operators:
        - $eq: Equal to
        - $ne: Not equal to
        - $lt: Less than
        - $lte: Less than or equal
        - $gt: Greater than
        - $gte: Greater than or equal
        - $in: Value in list
        - $contains: List contains value

        Args:
            requirement: Dict with operator keys and values.
            provider_value: The provider's value to compare.

        Returns:
            True if ALL operators are satisfied.
        """
        for op, expected in requirement.items():
            if op == "$eq":
                if not self._compare_eq(provider_value, expected):
                    return False
            elif op == "$ne":
                if self._compare_eq(provider_value, expected):
                    return False
            elif op == "$lt":
                if not self._compare_lt(provider_value, expected):
                    return False
            elif op == "$lte":
                if not self._compare_lte(provider_value, expected):
                    return False
            elif op == "$gt":
                if not self._compare_gt(provider_value, expected):
                    return False
            elif op == "$gte":
                if not self._compare_gte(provider_value, expected):
                    return False
            elif op == "$in":
                if not self._compare_in(provider_value, expected):
                    return False
            elif op == "$contains":
                if not self._compare_contains(provider_value, expected):
                    return False
            # Unknown operator - log warning and emit deprecation warning
            elif op.startswith("$"):
                logger.warning(
                    "Unknown operator '%s' in requirement - ignoring. "
                    "Supported operators: $eq, $ne, $lt, $lte, $gt, $gte, $in, $contains",
                    op,
                )
                warnings.warn(
                    f"Unknown operator '{op}' in requirement - ignoring",
                    UserWarning,
                    stacklevel=3,
                )
        return True

    def _check_list_requirement(
        self,
        requirement: list[Any],
        provider_value: Any,
    ) -> bool:
        """Check list requirement with any-of semantics.

        A list requirement is satisfied if:
        - provider_value is in requirement list, OR
        - provider_value is a list with non-empty intersection with requirement

        Args:
            requirement: List of acceptable values.
            provider_value: The provider's value.

        Returns:
            True if any-of match succeeds.
        """
        if provider_value is None:
            return False

        # If provider value is a list, check intersection
        if isinstance(provider_value, list):
            try:
                return bool(set(provider_value) & set(requirement))
            except TypeError:
                # Fallback for unhashable elements (dicts, lists, etc.)
                # Use iteration instead of set operations
                logger.debug("Using fallback comparison for unhashable list elements")
                return any(item in requirement for item in provider_value)

        # Otherwise check if provider value is in requirement list
        return provider_value in requirement

    def _compare_eq(self, provider_value: Any, expected: Any) -> bool:
        """Equality comparison with type coercion for numerics.

        Handles None values explicitly and coerces numeric types
        to float for comparison to avoid int/float mismatch issues.

        Args:
            provider_value: The value from the provider to compare.
            expected: The expected value from the requirement.

        Returns:
            True if the values are equal (with numeric coercion if applicable).
        """
        if provider_value is None:
            return expected is None
        try:
            # Try numeric comparison for numeric types
            if isinstance(expected, (int, float)) and isinstance(
                provider_value, (int, float)
            ):
                return float(provider_value) == float(expected)
        except (TypeError, ValueError):
            pass
        return bool(provider_value == expected)

    def _compare_lt(self, provider_value: Any, expected: Any) -> bool:
        """Less than comparison with numeric coercion.

        Converts both values to float for comparison. Returns False
        if either value is None or cannot be converted to float.

        Args:
            provider_value: The value from the provider to compare.
            expected: The expected threshold value.

        Returns:
            True if provider_value < expected (as floats).
        """
        if provider_value is None or expected is None:
            return False
        try:
            return float(provider_value) < float(expected)
        except (TypeError, ValueError):
            return False

    def _compare_lte(self, provider_value: Any, expected: Any) -> bool:
        """Less than or equal comparison with numeric coercion.

        Converts both values to float for comparison. Returns False
        if either value is None or cannot be converted to float.

        Args:
            provider_value: The value from the provider to compare.
            expected: The expected threshold value.

        Returns:
            True if provider_value <= expected (as floats).
        """
        if provider_value is None or expected is None:
            return False
        try:
            return float(provider_value) <= float(expected)
        except (TypeError, ValueError):
            return False

    def _compare_gt(self, provider_value: Any, expected: Any) -> bool:
        """Greater than comparison with numeric coercion.

        Converts both values to float for comparison. Returns False
        if either value is None or cannot be converted to float.

        Args:
            provider_value: The value from the provider to compare.
            expected: The expected threshold value.

        Returns:
            True if provider_value > expected (as floats).
        """
        if provider_value is None or expected is None:
            return False
        try:
            return float(provider_value) > float(expected)
        except (TypeError, ValueError):
            return False

    def _compare_gte(self, provider_value: Any, expected: Any) -> bool:
        """Greater than or equal comparison with numeric coercion.

        Converts both values to float for comparison. Returns False
        if either value is None or cannot be converted to float.

        Args:
            provider_value: The value from the provider to compare.
            expected: The expected threshold value.

        Returns:
            True if provider_value >= expected (as floats).
        """
        if provider_value is None or expected is None:
            return False
        try:
            return float(provider_value) >= float(expected)
        except (TypeError, ValueError):
            return False

    def _compare_in(self, provider_value: Any, expected: Any) -> bool:
        """Check if provider value is in expected list.

        Args:
            provider_value: The provider's value to check.
            expected: Expected to be a list; returns False if not.

        Returns:
            True if provider_value is in expected list.
        """
        if provider_value is None:
            return False
        if not isinstance(expected, list):
            return False
        return bool(provider_value in expected)

    def _compare_contains(self, provider_value: Any, expected: Any) -> bool:
        """Check if provider list contains expected value.

        Tests whether the provider's value (expected to be a list)
        contains the expected item.

        Args:
            provider_value: The provider's value, expected to be a list.
            expected: The value to search for in the provider's list.

        Returns:
            True if provider_value is a list containing expected.
        """
        if provider_value is None:
            return False
        if not isinstance(provider_value, list):
            return False
        return expected in provider_value
