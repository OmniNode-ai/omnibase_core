"""
Diff Configuration Model.

Provides configuration options for contract diffing operations,
including field exclusions, identity keys for list element matching,
and normalization settings.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class ModelDiffConfiguration(BaseModel):
    """
    Configuration for contract diff operations.

    Controls how contract diffs are computed, including which fields
    to exclude from comparison, how to identify list elements for
    change tracking, and whether to include unchanged fields in results.

    Attributes:
        exclude_fields: Set of field paths to exclude from diff comparison.
            These are typically volatile fields like correlation_id or timestamps.
        identity_keys: Mapping of list field paths to their identity key field.
            Used to track additions, removals, and modifications of list elements
            by identity rather than position.
        include_unchanged: If True, include UNCHANGED fields in diff results.
            Defaults to False for more concise output.
        normalize_before_diff: If True, normalize contract values before diffing.
            Normalization includes sorting keys and canonicalizing values.

    Example:
        >>> config = ModelDiffConfiguration(
        ...     exclude_fields=frozenset({"computed_at", "fingerprint"}),
        ...     identity_keys={"transitions": "name", "states": "state_id"},
        ...     include_unchanged=False,
        ... )
        >>> config.should_exclude("computed_at")
        True
        >>> config.get_identity_key("transitions")
        'name'
    """

    DEFAULT_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "correlation_id",
            "execution_id",
            "computed_at",
            "fingerprint",
        }
    )
    """Default fields to exclude from diff comparison (volatile/computed fields)."""

    DEFAULT_IDENTITY_KEYS: ClassVar[dict[str, str]] = {
        "transitions": "name",
        "states": "name",
        "steps": "step_id",
        "actions": "name",
        "events": "event_type",
        "handlers": "handler_id",
        "dependencies": "name",
    }
    """Default identity keys for common list fields in contracts."""

    exclude_fields: frozenset[str] = Field(
        default_factory=lambda: ModelDiffConfiguration.DEFAULT_EXCLUDE_FIELDS,
        description=(
            "Field paths to exclude from diff comparison. "
            "Typically volatile fields like correlation_id, execution_id, etc."
        ),
    )

    identity_keys: dict[str, str] = Field(
        default_factory=lambda: dict(ModelDiffConfiguration.DEFAULT_IDENTITY_KEYS),
        description=(
            "Mapping of list field paths to their identity key field. "
            "Used to match list elements by identity rather than position."
        ),
    )

    include_unchanged: bool = Field(
        default=False,
        description="Whether to include UNCHANGED fields in diff results.",
    )

    normalize_before_diff: bool = Field(
        default=True,
        description=(
            "Whether to normalize contract values before computing diff. "
            "Normalization includes sorting keys and canonicalizing values."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    def get_identity_key(self, field_path: str) -> str | None:
        """
        Get the identity key for a list field path.

        The identity key is used to match elements between lists during
        diff computation. Elements with the same identity key value are
        considered the same logical element, allowing detection of
        modifications vs additions/removals.

        Args:
            field_path: The dot-separated path to the list field.
                Can be a full path (e.g., "meta.transitions") or just
                the final component (e.g., "transitions").

        Returns:
            The identity key field name if configured, None otherwise.

        Example:
            >>> config = ModelDiffConfiguration()
            >>> config.get_identity_key("transitions")
            'name'
            >>> config.get_identity_key("meta.transitions")
            'name'
            >>> config.get_identity_key("unknown_field")
            None
        """
        # Check for exact match first
        if field_path in self.identity_keys:
            return self.identity_keys[field_path]

        # Check for final path component match
        final_component = field_path.rsplit(".", maxsplit=1)[-1]
        return self.identity_keys.get(final_component)

    def should_exclude(self, field_path: str) -> bool:
        """
        Check if a field path should be excluded from diff comparison.

        Args:
            field_path: The dot-separated path to the field.
                Can be a full path (e.g., "meta.computed_at") or just
                the field name (e.g., "computed_at").

        Returns:
            True if the field should be excluded, False otherwise.

        Example:
            >>> config = ModelDiffConfiguration()
            >>> config.should_exclude("computed_at")
            True
            >>> config.should_exclude("meta.computed_at")
            True
            >>> config.should_exclude("name")
            False
        """
        # Check for exact match
        if field_path in self.exclude_fields:
            return True

        # Check for final path component match
        final_component = field_path.rsplit(".", maxsplit=1)[-1]
        return final_component in self.exclude_fields


__all__ = ["ModelDiffConfiguration"]
