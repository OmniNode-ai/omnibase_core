"""
Complete preview of all config overrides with before/after state.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.replay.model_config_override_field_preview import (
    ModelConfigOverrideFieldPreview,
)

__all__ = ["ModelConfigOverridePreview"]


class ModelConfigOverridePreview(BaseModel):
    """
    Complete preview of all overrides with before/after state.

    Provides patch-like diff visualization for user confirmation before
    applying configuration overrides. Aggregates individual field previews
    and tracks any issues like missing paths or type mismatches.

    Attributes:
        field_previews: Tuple of individual field previews.
        paths_not_found: Paths that don't exist in original config (will be created).
        type_mismatches: Paths where new value type differs from original.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for concurrent reads.

    Example:
        >>> field_preview = ModelConfigOverrideFieldPreview(
        ...     path="retry.max_attempts",
        ...     injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        ...     old_value=3,
        ...     new_value=5,
        ... )
        >>> preview = ModelConfigOverridePreview(
        ...     field_previews=(field_preview,),
        ...     paths_not_found=("new_setting",),
        ...     type_mismatches=(),
        ... )
        >>> print(preview.to_markdown())
        ## Configuration Override Preview
        ...

    .. versionadded:: 0.4.0
    """

    # from_attributes=True: Enables construction from ORM/dataclass instances
    # and ensures pytest-xdist compatibility across worker processes where
    # class identity may differ due to independent imports.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    field_previews: tuple[ModelConfigOverrideFieldPreview, ...] = Field(
        default_factory=tuple,
        description="Individual field previews",
    )
    paths_not_found: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Paths that don't exist in original config (will be created)",
    )
    type_mismatches: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Paths where new value type differs from original",
    )

    def to_markdown(self) -> str:
        """Generate markdown diff table.

        Creates a complete markdown document with:
        - A header section
        - A table showing all field overrides with before/after values
        - Optional sections for new paths and type mismatches

        Returns:
            A complete markdown string suitable for display to users.
        """
        lines = [
            "## Configuration Override Preview",
            "",
            "| Path | Injection Point | Before | After | Status |",
            "|------|-----------------|--------|-------|--------|",
        ]
        for preview in self.field_previews:
            lines.append(preview.to_markdown_row())

        if self.paths_not_found:
            lines.extend(["", "### New Paths (will be created):", ""])
            for path in self.paths_not_found:
                lines.append(f"- `{path}`")

        if self.type_mismatches:
            lines.extend(["", "### Type Mismatches (review required):", ""])
            for path in self.type_mismatches:
                lines.append(f"- `{path}`")

        return "\n".join(lines)
