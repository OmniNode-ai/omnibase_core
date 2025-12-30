"""Requirements models for expressing requirements with graduated strictness.

This module provides ModelRequirementSet for expressing requirements across
four tiers: must (hard requirements), prefer (soft preferences), forbid
(exclusions), and hints (non-binding tie-breakers).

Example:
    Basic usage with all four tiers::

        >>> from omnibase_core.models.requirements import ModelRequirementSet
        >>> reqs = ModelRequirementSet(
        ...     must={"region": "us-east-1", "active": True},
        ...     prefer={"memory_gb": 16, "ssd": True},
        ...     forbid={"deprecated": True},
        ...     hints={"tier": "premium"}
        ... )

    Checking if a provider matches requirements::

        >>> provider = {"region": "us-east-1", "active": True, "memory_gb": 16}
        >>> matches, score, warnings = reqs.matches(provider)
        >>> print(f"Matches: {matches}, Score: {score}")
        Matches: True, Score: 1.0
        >>> # Score is 1.0 because one prefer (memory_gb) matched

    Using sort_key() to sort providers by match quality::

        >>> providers = [
        ...     {"name": "A", "region": "us-east-1", "active": True},
        ...     {"name": "B", "region": "us-east-1", "active": True, "memory_gb": 16},
        ...     {"name": "C", "region": "us-west-2", "active": True},  # wrong region
        ... ]
        >>> sorted_providers = sorted(providers, key=reqs.sort_key)
        >>> [p["name"] for p in sorted_providers]
        ['B', 'A', 'C']
        >>> # B first (matches + highest prefer score), A second, C last (no match)

    Using sort_providers() for batch sorting::

        >>> sorted_list = reqs.sort_providers(providers)
        >>> [p["name"] for p in sorted_list]
        ['B', 'A', 'C']

Comparison Operators:
    ModelRequirementSet supports explicit operators for complex comparisons::

        >>> reqs = ModelRequirementSet(
        ...     must={"latency_ms": {"$lte": 100}},  # latency <= 100
        ...     prefer={"version": {"$gte": 2}},     # version >= 2
        ... )

    Key-name heuristics are also supported::

        >>> reqs = ModelRequirementSet(
        ...     must={"max_latency_ms": 100},  # Automatically uses <=
        ...     prefer={"min_memory_gb": 8},   # Automatically uses >=
        ... )

    Supported operators: $eq, $ne, $lt, $lte, $gt, $gte, $in, $contains
"""

from omnibase_core.models.requirements.model_requirement_set import (
    ModelRequirementSet,
)

__all__ = [
    "ModelRequirementSet",
]
