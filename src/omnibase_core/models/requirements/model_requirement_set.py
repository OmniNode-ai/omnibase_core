"""
Requirement set model for expressing requirements with graduated strictness.

This module provides the ModelRequirementSet class which enables expressing
requirements across four tiers: must (hard requirements), prefer (soft preferences),
forbid (exclusions), and hints (non-binding tie-breakers).
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelRequirementSet",
]


class ModelRequirementSet(BaseModel):
    """Expresses requirements with graduated strictness.

    Four tiers of requirement strictness:
    - must: Hard requirements. Provider MUST satisfy all. Failure = no match.
    - prefer: Soft preferences. Improves score if satisfied. Failure = warning.
    - forbid: Exclusions. Provider MUST NOT have these. Presence = no match.
    - hints: Non-binding hints. May influence tie-breaking. Never causes failure.

    Comparison Semantics:
    - Key-name heuristics: max_* keys use <=, min_* keys use >=, others use ==
    - Operator support: $eq, $ne, $lt, $lte, $gt, $gte, $in, $contains

    Example:
        >>> reqs = ModelRequirementSet(
        ...     must={"region": "us-east-1", "max_latency_ms": 20},
        ...     prefer={"memory_gb": 16},
        ...     forbid={"deprecated": True},
        ...     hints={"tier": "premium"}
        ... )
        >>> provider = {"region": "us-east-1", "latency_ms": 15, "memory_gb": 8}
        >>> matches, score, warnings = reqs.matches(provider)
    """

    must: dict[str, Any] = Field(
        default_factory=dict,
        description="Hard requirements. Provider MUST satisfy all. Failure = no match.",
    )
    prefer: dict[str, Any] = Field(
        default_factory=dict,
        description="Soft preferences. Improves score if satisfied. Failure = warning.",
    )
    forbid: dict[str, Any] = Field(
        default_factory=dict,
        description="Exclusions. Provider MUST NOT have these. Presence = no match.",
    )
    hints: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-binding hints. May influence tie-breaking. Never causes failure.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

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
        warnings: list[str] = []

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
                warnings.append(f"PREFER not satisfied: {key}")

        return (True, score, warnings)

    def sort_key(self, provider: Mapping[str, Any]) -> tuple[float, int, str]:
        """Return sort key for ordering providers.

        Useful for sorting a list of providers by how well they match.
        Use with sorted() with reverse=True for best matches first.

        Args:
            provider: A mapping of provider capabilities/attributes.

        Returns:
            A tuple suitable for sorting:
            - score: Negated so higher scores come first in ascending sort
            - hint_rank: Lower is better (count of unmatched hints)
            - deterministic_fallback: Stable ordering key based on provider id/name
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
        # Use try/except to handle unhashable values in provider dict
        if "id" in provider:
            fallback = str(provider["id"])
        elif "name" in provider:
            fallback = str(provider["name"])
        else:
            try:
                fallback = str(
                    hash(
                        frozenset(provider.items())
                        if isinstance(provider, dict)
                        else id(provider)
                    )
                )
            except TypeError:
                # Fallback for unhashable values (lists, dicts, etc.)
                fallback = str(id(provider))

        # Negate score so higher scores sort first in ascending order
        return (-score, hint_rank, fallback)

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

    def _has_operator(self, requirement: dict[str, Any]) -> bool:
        """Check if a dict requirement contains operator syntax.

        Args:
            requirement: The requirement dict to check.

        Returns:
            True if any key starts with '$'.
        """
        return any(k.startswith("$") for k in requirement)

    def _evaluate_operators(
        self,
        requirement: dict[str, Any],
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
            # Unknown operator - warn instead of silently ignoring
            elif op.startswith("$"):
                warnings.warn(
                    f"Unknown operator '{op}' in requirement - ignoring",
                    UserWarning,
                    stacklevel=2,
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
