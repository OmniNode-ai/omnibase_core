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

Type Safety:
    Requirement values are constrained to JSON-compatible types via
    ``JsonType`` (imported from ``omnibase_core.types.type_json``).
    This prevents arbitrary Python objects from being stored as
    requirement values, ensuring serialization safety and consistent
    resolver behavior.

Runtime Validation:
    Beyond static type hints, ``ModelRequirementSet`` enforces JSON-serializability
    at runtime via the ``validate_json_serializable`` model validator. This catches
    non-serializable objects that slip past type checkers (e.g., sets, datetime,
    custom classes). If validation fails, a clear error message is raised with
    examples of valid values.

.. versionadded:: 0.4.0
"""

import json
from typing import Any, TypeGuard

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.types.type_json import JsonType

# =============================================================================
# TypeGuard Functions for Runtime Type Narrowing
# =============================================================================
#
# These TypeGuard functions enable better type inference in resolver code by
# providing runtime type checks that narrow types for static analysis tools.
#
# Usage in resolvers:
#     if is_requirement_dict(data):
#         # Type narrowed: data is dict[str, JsonType]
#         for key, val in data.items():
#             process_requirement(key, val)
#
# Benefits:
#     - Better IDE autocompletion and type hints
#     - Mypy recognizes narrowed types after the guard
#     - Eliminates need for cast() or type: ignore comments
#     - Runtime validation with type-safe static analysis
#


def is_json_primitive(value: Any) -> TypeGuard[str | int | float | bool | None]:
    """Type guard for JSON primitive values.

    Enables type narrowing for scalar JSON values that are valid
    JsonType leaves (non-container types).

    Args:
        value: Any value to check.

    Returns:
        True if value is a JSON primitive (str, int, float, bool, or None),
        False otherwise.

    Examples:
        >>> is_json_primitive("hello")
        True
        >>> is_json_primitive(42)
        True
        >>> is_json_primitive(3.14)
        True
        >>> is_json_primitive(True)
        True
        >>> is_json_primitive(None)
        True
        >>> is_json_primitive([1, 2, 3])
        False
        >>> is_json_primitive({"key": "value"})
        False

    Note:
        This explicitly checks for bool before int because in Python,
        ``isinstance(True, int)`` returns True (bool is a subclass of int).
    """
    # Check None first (common case)
    if value is None:
        return True
    # Check bool before int (bool is subclass of int in Python)
    if isinstance(value, bool):
        return True
    # Check remaining primitives
    return isinstance(value, (str, int, float))


def is_requirement_dict(value: Any) -> TypeGuard[dict[str, JsonType]]:
    """Type guard for requirement dictionaries.

    Enables type narrowing in resolver code for better IDE support
    and static type checking. Validates that the value is a dict
    with string keys (values are not deeply validated for performance).

    Args:
        value: Any value to check.

    Returns:
        True if value is a dict with all string keys, False otherwise.

    Examples:
        >>> is_requirement_dict({"key": "value", "count": 42})
        True
        >>> is_requirement_dict({"nested": {"a": 1}})
        True
        >>> is_requirement_dict({})
        True
        >>> is_requirement_dict({1: "value"})  # Non-string key
        False
        >>> is_requirement_dict("not a dict")
        False
        >>> is_requirement_dict([1, 2, 3])
        False

    Note:
        This performs a shallow check - it validates that all keys are strings
        but does not recursively validate that all values are valid
        JsonType values. For full validation, use ``ModelRequirementSet``
        which performs JSON serializability checks.
    """
    if not isinstance(value, dict):
        return False
    return all(isinstance(k, str) for k in value)


def is_requirement_list(value: Any) -> TypeGuard[list[JsonType]]:
    """Type guard for requirement lists.

    Enables type narrowing for list values that are valid JsonType
    containers. Validates that the value is a list (values are not deeply
    validated for performance).

    Args:
        value: Any value to check.

    Returns:
        True if value is a list, False otherwise.

    Examples:
        >>> is_requirement_list([1, 2, 3])
        True
        >>> is_requirement_list(["a", "b", "c"])
        True
        >>> is_requirement_list([{"nested": True}])
        True
        >>> is_requirement_list([])
        True
        >>> is_requirement_list("not a list")
        False
        >>> is_requirement_list({"key": "value"})
        False

    Note:
        This performs a shallow check - it validates that the value is a list
        but does not recursively validate that all elements are valid
        JsonType values. For full validation, use ``ModelRequirementSet``
        which performs JSON serializability checks.
    """
    return isinstance(value, list)


def is_requirement_value(value: Any) -> TypeGuard[JsonType]:
    """Type guard for any valid JsonType value.

    Enables type narrowing for values that conform to the JsonType
    recursive type alias. Performs a shallow check for the top-level type.

    Args:
        value: Any value to check.

    Returns:
        True if value is a valid JsonType (primitive, list, or
        dict with string keys), False otherwise.

    Examples:
        >>> is_requirement_value("string")
        True
        >>> is_requirement_value(42)
        True
        >>> is_requirement_value(None)
        True
        >>> is_requirement_value([1, 2, 3])
        True
        >>> is_requirement_value({"key": "value"})
        True
        >>> is_requirement_value({1: "value"})  # Non-string key
        False
        >>> is_requirement_value({1, 2, 3})  # Set is not JSON-serializable
        False
        >>> is_requirement_value(lambda x: x)  # Function is not allowed
        False

    Note:
        This performs a shallow validation - for deeply nested structures,
        it validates only the top-level type. Use ``ModelRequirementSet``
        for full JSON serializability validation at construction time.
    """
    # Check primitives
    if is_json_primitive(value):
        return True
    # Check list (shallow)
    if isinstance(value, list):
        return True
    # Check dict with string keys (shallow)
    if isinstance(value, dict):
        return all(isinstance(k, str) for k in value)
    return False


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

    must: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Hard constraints that must be satisfied for a provider to match",
    )

    prefer: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Soft preferences that affect provider scoring",
    )

    forbid: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Hard exclusion constraints that disqualify providers",
    )

    hints: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Advisory information for tie-breaking between equal providers",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_json_serializable(cls, data: Any) -> Any:
        """Validate that all requirement values are JSON-serializable.

        This validator ensures that values stored in must/prefer/forbid/hints
        can be serialized to JSON, preventing runtime errors during serialization
        and ensuring consistent behavior across resolvers.

        This is a runtime enforcement of the ``JsonType`` type constraint,
        since Pydantic's type checking alone cannot catch all non-JSON-serializable
        objects (e.g., custom classes, datetime objects, lambdas).

        Args:
            data: Raw input data (dict or model instance).

        Returns:
            Validated data unchanged if all values are JSON-serializable.

        Raises:
            ValueError: If any requirement dict contains non-JSON-serializable values,
                with a helpful error message showing the problematic field and value.

        Examples:
            Valid (all JSON-serializable)::

                ModelRequirementSet(must={"key": "value", "nested": {"a": 1}})

            Invalid (contains non-serializable object)::

                # Raises ValueError: Requirements in 'must' are not JSON-serializable:
                # Object of type 'set' is not JSON serializable.
                # Ensure values are primitives (str, int, float, bool, None)
                # or JSON-compatible containers (list, dict).
                ModelRequirementSet(must={"invalid": {1, 2, 3}})  # set is not JSON
        """
        if not isinstance(data, dict):
            # Let Pydantic handle non-dict inputs (e.g., model instances)
            return data

        requirement_fields = ["must", "prefer", "forbid", "hints"]
        for field_name in requirement_fields:
            if field_name not in data:
                continue
            field_value = data[field_name]
            if field_value is None:
                continue
            try:
                json.dumps(field_value)
            except (TypeError, ValueError) as e:
                # error-ok: Pydantic model_validator requires ValueError
                raise ValueError(
                    f"Requirements in '{field_name}' are not JSON-serializable: {e}. "
                    f"Ensure values are primitives (str, int, float, bool, None) "
                    f"or JSON-compatible containers (list, dict). "
                    f"Example valid value: {{'key': 'value', 'count': 42, 'nested': {{'a': 1}}}}"
                ) from e
        return data

    @property
    def is_empty(self) -> bool:
        """
        Check if this requirement set has no constraints.

        Returns:
            True if all constraint tiers are empty, False otherwise.

        Validation Invariants:
            This property assumes all constraint dicts are valid (enforced by
            ``validate_json_serializable``). Empty dicts evaluate to False in
            boolean context, so this check is safe even if validation was
            somehow bypassed - it would just return True for empty dicts.

        Examples:
            >>> ModelRequirementSet().is_empty
            True
            >>> ModelRequirementSet(must={"key": "value"}).is_empty
            False
        """
        # Implementation Note: Uses Python's truthiness for dicts
        # Empty dict {} is falsy, non-empty dict {"k": "v"} is truthy
        return not (self.must or self.prefer or self.forbid or self.hints)

    @property
    def has_hard_constraints(self) -> bool:
        """
        Check if this requirement set has hard constraints (must or forbid).

        Hard constraints are filter criteria that exclude providers entirely:
        - ``must``: Provider MUST match all specified attributes
        - ``forbid``: Provider MUST NOT match any specified attributes

        Returns:
            True if must or forbid are non-empty, False otherwise.

        Validation Invariants:
            This property assumes all constraint values are JSON-serializable
            (enforced by ``validate_json_serializable``). The bool() conversion
            is safe for any dict - empty returns False, non-empty returns True.

        Examples:
            >>> ModelRequirementSet(prefer={"fast": True}).has_hard_constraints
            False
            >>> ModelRequirementSet(must={"required": True}).has_hard_constraints
            True
        """
        # Implementation Note: Hard constraints affect provider FILTERING (Phase 1)
        # They determine which providers are even considered, before scoring.
        return bool(self.must or self.forbid)

    @property
    def has_soft_constraints(self) -> bool:
        """
        Check if this requirement set has soft constraints (prefer or hints).

        Soft constraints affect provider SCORING but don't exclude providers:
        - ``prefer``: Matching attributes increase provider score
        - ``hints``: Advisory tie-breakers when scores are equal

        Returns:
            True if prefer or hints are non-empty, False otherwise.

        Validation Invariants:
            This property assumes all constraint values are JSON-serializable
            (enforced by ``validate_json_serializable``). The bool() conversion
            is safe for any dict - empty returns False, non-empty returns True.

        Examples:
            >>> ModelRequirementSet(must={"required": True}).has_soft_constraints
            False
            >>> ModelRequirementSet(prefer={"fast": True}).has_soft_constraints
            True
        """
        # Implementation Note: Soft constraints affect provider SCORING (Phase 2)
        # They influence ranking among providers that passed hard constraint filtering.
        return bool(self.prefer or self.hints)

    def merge(self, other: "ModelRequirementSet") -> "ModelRequirementSet":
        """
        Merge another requirement set into this one.

        Creates a new requirement set combining constraints from both.
        For conflicts (same key in both), the other's values take precedence.

        .. important:: TL;DR - Nested Dicts Are REPLACED, Not Merged

            If your requirements contain nested dicts like ``{"config": {"a": 1, "b": 2}}``,
            merging with ``{"config": {"a": 10}}`` will **lose** the ``"b"`` key entirely.
            See the "Shallow merge behavior" example below.

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
        # Implementation Note: Shallow merge is intentional
        #
        # Why shallow merge (dict spread) instead of deep merge (recursive update)?
        # 1. Performance: O(n) dict spread vs O(n*m) recursive traversal
        # 2. Predictability: Flat key-value replacement is easier to reason about
        # 3. Simplicity: No edge cases with mixed types (list vs dict vs scalar)
        # 4. Explicit override: When you override a nested config, you intend to
        #    replace it entirely rather than partially patch it
        # 5. JSON compatibility: Matches how JSON Merge Patch (RFC 7396) works
        #
        # If deep merge is needed, callers should pre-process their requirements
        # before calling merge(), or use a utility like `dict_deep_update()`.
        return ModelRequirementSet(
            must={**self.must, **other.must},
            prefer={**self.prefer, **other.prefer},
            forbid={**self.forbid, **other.forbid},
            hints={**self.hints, **other.hints},
        )

    @allow_dict_any(
        reason="Provider capabilities are dynamic key-value pairs from external systems"
    )
    def matches(
        self,
        provider: dict[str, Any],
    ) -> tuple[bool, float, list[str]]:
        """
        Check if a provider satisfies this requirement set.

        Evaluates the provider against all constraint tiers and returns
        a match result with score and warnings.

        Matching Logic:
            1. **must constraints**: All must be satisfied. If any ``must``
               constraint is not met, the provider is rejected (matches=False).
            2. **forbid constraints**: None should match. If any ``forbid``
               constraint matches, the provider is rejected (matches=False).
            3. **prefer constraints**: Affect the score. Each satisfied preference
               adds to the score. Unmet preferences generate warnings.
            4. **hints**: Currently advisory only, do not affect scoring.

        Scoring:
            - Base score is 1.0 for a matching provider
            - Each satisfied ``prefer`` constraint adds 0.1 to the score
            - Each unsatisfied ``prefer`` constraint generates a warning

        Note on Scoring Design:
            This scoring scheme (1.0 base + 0.1 per preference) differs
            intentionally from ``ServiceCapabilityResolver._score_providers()``
            which uses (0.0 base + 1.0 per preference). The difference exists
            because they serve different purposes:

            - ``matches()`` is a **boolean check with quality score** where
              1.0 base represents "valid match" and 0.1 increments provide
              fine-grained quality differentiation within the valid range.
            - ``_score_providers()`` is a **relative ranking function** for
              already-filtered providers where only relative scores matter
              for sorting, not absolute values.

        Args:
            provider: Provider capability mapping to check. Keys are attribute
                names, values are the provider's capability values.

        Returns:
            Tuple of (matches, score, warnings):
                - matches: True if provider satisfies all must/forbid constraints
                - score: Float score (1.0 base + 0.1 per satisfied preference)
                - warnings: List of warning messages for unmet preferences

        Examples:
            >>> reqs = ModelRequirementSet(
            ...     must={"engine": "postgres"},
            ...     prefer={"version": 14},
            ...     forbid={"deprecated": True},
            ... )
            >>> # Provider matches all constraints
            >>> reqs.matches({"engine": "postgres", "version": 14})
            (True, 1.1, [])
            >>> # Provider missing must constraint
            >>> reqs.matches({"engine": "mysql"})
            (False, 0.0, [])
            >>> # Provider has forbidden attribute
            >>> reqs.matches({"engine": "postgres", "deprecated": True})
            (False, 0.0, [])
        """
        warnings: list[str] = []

        # Check must constraints - all must be satisfied
        for key, required_value in self.must.items():
            if key not in provider:
                return (False, 0.0, [])
            if provider[key] != required_value:
                return (False, 0.0, [])

        # Check forbid constraints - none should match
        for key, forbidden_value in self.forbid.items():
            if key in provider and provider[key] == forbidden_value:
                return (False, 0.0, [])

        # Calculate score based on prefer matches
        score = 1.0  # Base score for matching provider
        for key, preferred_value in self.prefer.items():
            if key in provider and provider[key] == preferred_value:
                score += 0.1  # Bonus for matching preference
            else:
                warnings.append(
                    f"Preference not met: {key}={preferred_value!r} "
                    f"(provider has {provider.get(key, '<missing>')!r})"
                )

        return (True, score, warnings)

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


__all__ = [
    "ModelRequirementSet",
    # TypeGuard functions for runtime type narrowing
    "is_json_primitive",
    "is_requirement_dict",
    "is_requirement_list",
    "is_requirement_value",
]
