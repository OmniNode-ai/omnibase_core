"""
Execution Constraints Model for Handler Contracts.

This module defines ModelExecutionConstraints, which declares execution
ordering constraints for handlers. Contracts declare WHAT they need,
not WHERE they run. The resolver computes ordering from profile policy
combined with these constraints.

Core Principle:
    "Contracts declare constraints (not ordering). Ordering is computed by resolver."

Disallowed Constraint Types:
    Contracts may NOT declare:
    - Absolute positions ("I am phase 3")
    - Numeric ordering ("I run at position N")
    - Custom phase names

Example:
    >>> constraints = ModelExecutionConstraints(
    ...     requires_before=["capability:logging", "handler:metrics"],
    ...     requires_after=["capability:auth"],
    ...     can_run_parallel=True,
    ... )
    >>> "capability:logging" in constraints.requires_before
    True

See Also:
    - OMN-1117: Handler Contract Model & YAML Schema
    - ModelHandlerContract: The main handler contract model

.. versionadded:: 0.4.1
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelExecutionConstraints(BaseModel):
    """
    Execution constraints declared by a handler contract.

    Contracts declare WHAT they need, not WHERE they run. The resolver
    computes ordering from profile policy + these constraints.

    Constraint Types:
        - requires_before: This handler must run AFTER these dependencies
        - requires_after: This handler must run BEFORE these dependents
        - must_run: Forces execution even if otherwise skippable (rare)
        - can_run_parallel: Optimization hint for parallel execution
        - nondeterministic_effect: Influences legal phases and replay policy

    Dependency Reference Format:
        Dependencies are specified using prefixed strings:
        - "capability:logging" - Reference by capability
        - "handler:metrics" - Reference by handler ID
        - "tag:audit" - Reference by tag/label

    Disallowed Constraints:
        Contracts may NOT declare:
        - Absolute positions ("I am phase 3")
        - Numeric ordering ("I run at position N")
        - Custom phase names

    Attributes:
        requires_before: List of dependencies that must complete before this handler.
            Uses prefixed references: capability:X, handler:Y, tag:Z
        requires_after: List of dependents that must run after this handler.
            Uses prefixed references: capability:X, handler:Y, tag:Z
        must_run: If True, forces execution even if handler would be skipped.
            Use sparingly - most handlers should be skippable when conditions not met.
        can_run_parallel: Optimization hint indicating handler can run in parallel
            with other handlers that have this flag set.
        nondeterministic_effect: If True, indicates handler has non-deterministic
            side effects. Influences legal execution phases and replay behavior.

    Example:
        >>> # Handler that needs auth before it runs, and logging after
        >>> constraints = ModelExecutionConstraints(
        ...     requires_before=["capability:auth"],
        ...     requires_after=["capability:logging"],
        ...     can_run_parallel=False,  # Must run serially
        ... )

        >>> # Metrics handler that can run in parallel
        >>> metrics_constraints = ModelExecutionConstraints(
        ...     requires_before=["tag:core-execution"],
        ...     can_run_parallel=True,
        ... )

        >>> # Critical handler that must always run
        >>> critical_constraints = ModelExecutionConstraints(
        ...     must_run=True,
        ...     nondeterministic_effect=True,
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    See Also:
        - ModelHandlerContract: Handler contract containing these constraints
        - OMN-1117: Handler Contract Model & YAML Schema
    """

    requires_before: list[str] = Field(
        default_factory=list,
        description=(
            "Dependencies that must complete before this handler. "
            "Format: capability:X, handler:Y, tag:Z"
        ),
    )

    requires_after: list[str] = Field(
        default_factory=list,
        description=(
            "Dependents that must run after this handler. "
            "Format: capability:X, handler:Y, tag:Z"
        ),
    )

    must_run: bool = Field(
        default=False,
        description="Forces execution even if handler would otherwise be skipped (rare)",
    )

    can_run_parallel: bool = Field(
        default=True,
        description="Optimization hint: handler can run in parallel with others",
    )

    nondeterministic_effect: bool = Field(
        default=False,
        description="Handler has non-deterministic side effects (influences replay policy)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    @field_validator("requires_before", "requires_after", mode="after")
    @classmethod
    def validate_dependency_refs(cls, v: list[str]) -> list[str]:
        """
        Validate dependency reference format.

        Valid prefixes: capability:, handler:, tag:

        Note:
            Uses mode="after" because this validator checks semantic content
            (prefix format) of already-typed values, not type coercion.
            Pydantic validates list[str] type first, then this validates format.

        Args:
            v: List of dependency references (guaranteed list[str] by Pydantic).

        Returns:
            Validated list of references.

        Raises:
            ValueError: If reference format is invalid.
        """
        if not v:
            return v

        valid_prefixes = ("capability:", "handler:", "tag:")

        for ref in v:
            if not ref or not ref.strip():
                raise ValueError("Dependency reference cannot be empty")

            if not any(ref.startswith(prefix) for prefix in valid_prefixes):
                raise ValueError(
                    f"Dependency reference '{ref}' must start with one of: "
                    f"{', '.join(valid_prefixes)}"
                )

            # Validate the value after the prefix
            parts = ref.split(":", 1)
            if len(parts) != 2 or not parts[1].strip():
                raise ValueError(
                    f"Dependency reference '{ref}' must have a value after the prefix"
                )

        return v

    def has_ordering_constraints(self) -> bool:
        """
        Check if this constraint set has any ordering requirements.

        Returns:
            True if requires_before or requires_after is non-empty.
        """
        return bool(self.requires_before or self.requires_after)

    def get_all_dependencies(self) -> list[str]:
        """
        Get all dependency references (both before and after).

        Returns:
            Combined list of all dependency references.
        """
        return list(self.requires_before) + list(self.requires_after)


__all__ = [
    "ModelExecutionConstraints",
]
