# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Requirement Set Model for Capability Matching.

Provides a structured way to declare requirements for capability matching,
with four tiers of constraints:

- **must**: Hard constraints that must be satisfied (filter)
- **prefer**: Soft preferences for scoring (affect ranking)
- **forbid**: Hard exclusion constraints (filter)
- **hints**: Advisory information for tie-breaking (lowest priority)

Example Usage:
    >>> from omnibase_core.models.capabilities import ModelRequirementSet
    >>>
    >>> # Database with strong constraints
    >>> db_requirements = ModelRequirementSet(
    ...     must={"supports_transactions": True, "encryption_in_transit": True},
    ...     prefer={"max_latency_ms": 20, "region": "us-east-1"},
    ...     forbid={"scope": "public_internet"},
    ...     hints={"vendor_preference": ["postgres", "mysql"]}
    ... )
    >>>
    >>> # Minimal requirements
    >>> minimal = ModelRequirementSet(must={"available": True})

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelRequirementSet(BaseModel):
    """
    Structured requirement set for capability matching.

    Requirements are organized into four tiers that control how providers
    are filtered and ranked during capability resolution:

    1. **must** - Hard constraints that MUST be satisfied
       - Providers not meeting these are excluded entirely
       - Example: ``{"supports_transactions": True}``

    2. **forbid** - Hard exclusion constraints
       - Providers matching these are excluded entirely
       - Example: ``{"scope": "public_internet"}``

    3. **prefer** - Soft preferences for scoring
       - Affect provider ranking but don't exclude
       - When ``strict=True`` (on dependency), unmet preferences fail
       - When ``strict=False``, unmet preferences generate warnings
       - Example: ``{"max_latency_ms": 20, "region": "us-east-1"}``

    4. **hints** - Advisory information for tie-breaking
       - Used only when multiple providers have equal scores
       - Lowest priority, purely advisory
       - Example: ``{"vendor_preference": ["postgres", "mysql"]}``

    Attributes:
        must: Hard constraints that must be satisfied. Keys are attribute
            names, values are required values. All must match for a
            provider to be considered.
        prefer: Soft preferences for scoring. Keys are attribute names,
            values are preferred values. Matching preferences increase
            provider score.
        forbid: Hard exclusion constraints. Keys are attribute names,
            values that exclude a provider. Any match excludes the provider.
        hints: Advisory information for tie-breaking. Keys are attribute
            names, values are hints for resolution. Only used when
            providers are otherwise equal.

    Examples:
        Create a requirement set for a database:

        >>> reqs = ModelRequirementSet(
        ...     must={"engine": "postgres", "version_major": 14},
        ...     prefer={"max_latency_ms": 20},
        ...     forbid={"deprecated": True},
        ... )

        Empty requirement set (matches any provider):

        >>> empty = ModelRequirementSet()
        >>> empty.must
        {}

        Check if requirements are empty:

        >>> empty.is_empty
        True
        >>> reqs.is_empty
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    must: dict[str, Any] = Field(
        default_factory=dict,
        description="Hard constraints that must be satisfied for a provider to match",
    )

    prefer: dict[str, Any] = Field(
        default_factory=dict,
        description="Soft preferences that affect provider scoring",
    )

    forbid: dict[str, Any] = Field(
        default_factory=dict,
        description="Hard exclusion constraints that disqualify providers",
    )

    hints: dict[str, Any] = Field(
        default_factory=dict,
        description="Advisory information for tie-breaking between equal providers",
    )

    @property
    def is_empty(self) -> bool:
        """
        Check if this requirement set has no constraints.

        Returns:
            True if all constraint tiers are empty, False otherwise.

        Examples:
            >>> ModelRequirementSet().is_empty
            True
            >>> ModelRequirementSet(must={"key": "value"}).is_empty
            False
        """
        return not (self.must or self.prefer or self.forbid or self.hints)

    @property
    def has_hard_constraints(self) -> bool:
        """
        Check if this requirement set has hard constraints (must or forbid).

        Returns:
            True if must or forbid are non-empty, False otherwise.

        Examples:
            >>> ModelRequirementSet(prefer={"fast": True}).has_hard_constraints
            False
            >>> ModelRequirementSet(must={"required": True}).has_hard_constraints
            True
        """
        return bool(self.must or self.forbid)

    @property
    def has_soft_constraints(self) -> bool:
        """
        Check if this requirement set has soft constraints (prefer or hints).

        Returns:
            True if prefer or hints are non-empty, False otherwise.

        Examples:
            >>> ModelRequirementSet(must={"required": True}).has_soft_constraints
            False
            >>> ModelRequirementSet(prefer={"fast": True}).has_soft_constraints
            True
        """
        return bool(self.prefer or self.hints)

    def merge(self, other: "ModelRequirementSet") -> "ModelRequirementSet":
        """
        Merge another requirement set into this one.

        Creates a new requirement set combining constraints from both.
        For conflicts (same key in both), the other's values take precedence.

        .. warning:: Shallow Merge Semantics

            This method performs a **SHALLOW merge** for each constraint tier
            (must, prefer, forbid, hints). This means:

            - Top-level keys from ``other`` override keys from ``self``
            - Nested dictionaries are **NOT** recursively merged; they are
              replaced entirely
            - Lists and other complex values are replaced, not concatenated

            If you need deep merge behavior (recursive merging of nested dicts),
            you must implement it separately before calling merge, or use a
            utility like ``copy.deepcopy`` combined with recursive dict update.

        Args:
            other: Another requirement set to merge.

        Returns:
            New ModelRequirementSet with merged constraints.

        Examples:
            Basic merge with override:

            >>> base = ModelRequirementSet(must={"a": 1}, prefer={"b": 2})
            >>> override = ModelRequirementSet(must={"a": 10, "c": 3})
            >>> merged = base.merge(override)
            >>> merged.must
            {'a': 10, 'c': 3}
            >>> merged.prefer
            {'b': 2}

            Shallow merge behavior with nested dicts (values replaced, not merged):

            >>> base = ModelRequirementSet(
            ...     must={"config": {"timeout": 30, "retries": 3}}
            ... )
            >>> override = ModelRequirementSet(
            ...     must={"config": {"timeout": 60}}  # Only has timeout
            ... )
            >>> merged = base.merge(override)
            >>> # Note: "retries" is lost because the entire nested dict is replaced
            >>> merged.must
            {'config': {'timeout': 60}}
        """
        return ModelRequirementSet(
            must={**self.must, **other.must},
            prefer={**self.prefer, **other.prefer},
            forbid={**self.forbid, **other.forbid},
            hints={**self.hints, **other.hints},
        )

    def __repr__(self) -> str:
        """
        Return detailed representation for debugging.

        Only includes non-empty constraint tiers for readability.

        Returns:
            String representation showing non-empty constraints.
        """
        parts = []
        if self.must:
            parts.append(f"must={self.must!r}")
        if self.prefer:
            parts.append(f"prefer={self.prefer!r}")
        if self.forbid:
            parts.append(f"forbid={self.forbid!r}")
        if self.hints:
            parts.append(f"hints={self.hints!r}")
        return f"ModelRequirementSet({', '.join(parts)})"


__all__ = ["ModelRequirementSet"]
