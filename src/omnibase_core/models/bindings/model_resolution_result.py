"""
Resolution Result Model for Capability Dependency Resolution.

Captures the complete result of resolving all capability dependencies for a
handler contract, including:
    - Resolved bindings (alias -> provider mapping)
    - Success/failure status
    - Audit information (candidates, scores, rejection reasons)
    - Performance metrics

Core Principle:
    "Resolution is transparent. Every decision is auditable."

The resolution result provides complete visibility into the resolver's
decision-making process, enabling:
    - Debugging resolution failures
    - Understanding why specific providers were selected
    - Auditing security-sensitive binding decisions
    - Performance optimization of resolution

Example Usage:
    >>> from datetime import datetime, timezone
    >>> from omnibase_core.models.bindings import ModelResolutionResult, ModelBinding
    >>>
    >>> # Successful resolution
    >>> result = ModelResolutionResult(
    ...     bindings={
    ...         "db": ModelBinding(
    ...             dependency_alias="db",
    ...             capability="database.relational",
    ...             provider_id="550e8400-e29b-41d4-a716-446655440000",
    ...             adapter="omnibase_infra.adapters.PostgresAdapter",
    ...             connection_ref="secrets://postgres/primary",
    ...             requirements_hash="sha256:abc123",
    ...             resolution_profile="production",
    ...             resolved_at=datetime.now(timezone.utc),
    ...         ),
    ...     },
    ...     success=True,
    ...     candidates_by_alias={"db": ["provider-1", "provider-2"]},
    ...     scores_by_alias={"db": {"provider-1": 0.95, "provider-2": 0.7}},
    ... )
    >>>
    >>> result.is_successful
    True
    >>> result.binding_count
    1

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.bindings.model_binding import ModelBinding
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelResolutionResult(BaseModel):
    """Complete resolution result with bindings and audit information.

    Captures the outcome of resolving all capability dependencies declared
    in a handler contract. Includes both the resolved bindings and detailed
    audit information about the resolution process.

    Attributes:
        bindings: Mapping of alias to resolved binding. Each entry represents
            a successfully resolved capability dependency.
        success: Whether all dependencies were successfully resolved.
            False if any dependency failed to resolve.
        candidates_by_alias: Provider IDs that were considered for each alias
            before filtering and selection. Useful for debugging.
        scores_by_alias: Scores assigned to each candidate provider during
            resolution. Keys are aliases, values are dicts of provider_id -> score.
        rejection_reasons: Reasons why providers were rejected for each alias.
            Keys are aliases, values are dicts of provider_id -> reason string.
        resolved_at: Timestamp when resolution completed.
        resolution_duration_ms: How long the resolution process took in milliseconds.
        resolution_profile: Optional identifier for the resolution profile used.
            Profiles can define default bindings or constraints.
        errors: List of error messages encountered during resolution.
            Empty for successful resolutions.

    Examples:
        Successful resolution with full audit info:

        >>> from datetime import datetime, timezone
        >>> result = ModelResolutionResult(
        ...     bindings={
        ...         "db": ModelBinding(
        ...             dependency_alias="db",
        ...             capability="database.relational",
        ...             provider_id="550e8400-e29b-41d4-a716-446655440000",
        ...             adapter="omnibase_infra.adapters.PostgresAdapter",
        ...             connection_ref="secrets://postgres/primary",
        ...             requirements_hash="sha256:abc123",
        ...             resolution_profile="production",
        ...             resolved_at=datetime.now(timezone.utc),
        ...             candidates_considered=2,
        ...         ),
        ...     },
        ...     success=True,
        ...     candidates_by_alias={
        ...         "db": ["pg-primary", "pg-replica"],
        ...     },
        ...     scores_by_alias={
        ...         "db": {"pg-primary": 0.95, "pg-replica": 0.7},
        ...     },
        ...     resolution_duration_ms=12.5,
        ... )
        >>>
        >>> result.is_successful
        True
        >>> result.binding_count
        1

        Failed resolution with error:

        >>> failed_result = ModelResolutionResult(
        ...     bindings={},
        ...     success=False,
        ...     errors=["No provider found for capability 'secrets.vault'"],
        ...     rejection_reasons={
        ...         "secrets": {"vault-1": "health check failed"},
        ...     },
        ... )
        >>>
        >>> failed_result.is_successful
        False
        >>> failed_result.has_errors
        True

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. See ModelProviderDescriptor for detailed
        explanation of this pattern.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Core resolution result
    bindings: dict[str, ModelBinding] = Field(
        default_factory=dict,
        description="Mapping of alias to resolved binding",
    )

    success: bool = Field(
        default=False,
        description="Whether all dependencies were successfully resolved",
    )

    # Audit information - candidates considered
    candidates_by_alias: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Provider IDs considered for each alias before filtering",
    )

    # Audit information - scoring details
    scores_by_alias: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Scores assigned to each candidate (alias -> {provider_id: score})",
    )

    # Audit information - rejection reasons
    rejection_reasons: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Why providers were rejected (alias -> {provider_id: reason})",
    )

    # Timing and metadata
    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when resolution completed",
    )

    resolution_duration_ms: float = Field(
        default=0.0,
        description="How long the resolution process took in milliseconds",
        ge=0.0,
    )

    resolution_profile: str | None = Field(
        default=None,
        description="Identifier for the resolution profile used",
    )

    # Error tracking
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages encountered during resolution",
    )

    @field_validator("errors", mode="before")
    @classmethod
    def validate_errors(cls, v: Any) -> list[str]:
        """Validate and filter error messages.

        Strips whitespace from each error message and removes empty strings.
        Ensures consistency with other string list validators in the codebase.

        Note:
            Uses ``Any`` type hint because ``mode="before"`` receives raw input
            before Pydantic type coercion. The input could be any type.

        Args:
            v: Raw input value (expected to be a list of strings).

        Returns:
            List of non-empty error messages with whitespace stripped.

        Raises:
            ModelOnexError: If input is not a list or contains non-string items.
        """
        if v is None:
            return []

        if not isinstance(v, list):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"errors must be a list, got {type(v).__name__}",
                context={"value": v, "type": type(v).__name__},
            )

        validated: list[str] = []
        for error in v:
            if not isinstance(error, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"error must be a string, got {type(error).__name__}",
                    context={"error": error, "error_type": type(error).__name__},
                )
            stripped = error.strip()
            if stripped:  # Only include non-empty errors
                validated.append(stripped)

        return validated

    @property
    def is_successful(self) -> bool:
        """Check if resolution was successful.

        This is a convenience property that mirrors the success field.

        Returns:
            True if all dependencies were resolved successfully.
        """
        return self.success

    @property
    def binding_count(self) -> int:
        """Get the number of resolved bindings.

        Returns:
            Count of successfully resolved bindings.
        """
        return len(self.bindings)

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred during resolution.

        Returns:
            True if the errors list is non-empty.
        """
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Get the number of errors encountered.

        Returns:
            Count of error messages.
        """
        return len(self.errors)

    @property
    def aliases(self) -> list[str]:
        """Get list of all resolved aliases.

        Returns:
            Sorted list of alias names with successful bindings.
        """
        return sorted(self.bindings.keys())

    @property
    def total_candidates_considered(self) -> int:
        """Get total number of candidates considered across all aliases.

        Returns:
            Sum of candidates considered for all dependencies.
        """
        return sum(len(candidates) for candidates in self.candidates_by_alias.values())

    @property
    def total_rejections(self) -> int:
        """Get total number of provider rejections across all aliases.

        Returns:
            Sum of rejections for all dependencies.
        """
        return sum(len(reasons) for reasons in self.rejection_reasons.values())

    @property
    def average_binding_score(self) -> float:
        """Calculate average score across all resolved bindings.

        Uses the scores from scores_by_alias for each resolved binding's
        provider_id. If score information is not available, returns 0.0.

        Returns:
            Average score of all resolved bindings, or 0.0 if no bindings
            or no score information available.
        """
        if not self.bindings or not self.scores_by_alias:
            return 0.0

        total_score = 0.0
        count = 0
        for alias, binding in self.bindings.items():
            alias_scores = self.scores_by_alias.get(alias, {})
            # Try to get score for the bound provider
            if binding.resolved_provider in alias_scores:
                total_score += alias_scores[binding.resolved_provider]
                count += 1

        return total_score / count if count > 0 else 0.0

    def get_binding(self, alias: str) -> ModelBinding | None:
        """Get the binding for a specific alias.

        Args:
            alias: The dependency alias to look up.

        Returns:
            The ModelBinding if found, None otherwise.
        """
        return self.bindings.get(alias)

    def get_candidates(self, alias: str) -> list[str]:
        """Get candidates that were considered for an alias.

        Args:
            alias: The dependency alias to look up.

        Returns:
            List of provider IDs that were candidates, empty if alias not found.
        """
        return self.candidates_by_alias.get(alias, [])

    def get_rejection_reason(self, alias: str, provider_id_str: str) -> str | None:
        """Get the rejection reason for a specific provider.

        Args:
            alias: The dependency alias.
            provider_id_str: The provider ID string that was rejected.

        Returns:
            Rejection reason string if found, None otherwise.
        """
        reasons = self.rejection_reasons.get(alias, {})
        return reasons.get(provider_id_str)

    def __repr__(self) -> str:
        """Return concise representation for debugging.

        Returns:
            String showing success status and binding count.
        """
        status = "success" if self.success else "failed"
        return (
            f"ModelResolutionResult("
            f"status={status}, "
            f"bindings={len(self.bindings)}, "
            f"errors={len(self.errors)})"
        )

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            Summary string with status and counts.
        """
        status = "SUCCESS" if self.success else "FAILED"
        parts = [f"Resolution {status}"]
        if self.bindings:
            parts.append(f"{len(self.bindings)} binding(s)")
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.resolution_duration_ms > 0:
            parts.append(f"{self.resolution_duration_ms:.2f}ms")
        return " | ".join(parts)


__all__ = ["ModelResolutionResult"]
