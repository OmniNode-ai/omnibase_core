# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""ModelChangeProposal for representing proposed system changes (OMN-1196).

This module provides a typed model for capturing proposed system changes
including model swaps, configuration changes, and endpoint changes. It is
designed for use in the DEMO feature set for evaluating changes before
they are applied.

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or
    async tasks.

See Also:
    - ModelEffectOperationConfig: Related configuration model pattern
    - ModelAction: Similar factory method and validation patterns

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1196 change proposal feature.
"""

from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_change_type import EnumChangeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["EnumChangeType", "ModelChangeProposal"]


class ModelChangeProposal(BaseModel):
    """
    Represents a proposed system change for evaluation.

    This model captures what we want to change, why, and the before/after
    state for comparison. Used in the DEMO feature set for evaluating
    model swaps, config changes, and endpoint changes.

    The model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access. Unknown fields are rejected (extra='forbid')
    to ensure strict schema compliance.

    Attributes:
        change_type: Type of change being proposed (discriminator field).
        change_id: Unique identifier for this proposal (auto-generated UUID).
        description: Human-readable description of the change.
        before_config: Current configuration state.
        after_config: Proposed configuration state.
        rationale: Why this change is proposed.
        created_at: When the proposal was created (auto-generated).
        proposed_by: Optional identifier of who proposed the change.
        estimated_impact: Optional description of expected improvement.
        rollback_plan: Optional description of how to revert if needed.
        correlation_id: Optional correlation ID for tracking related operations.
        tags: Optional list of tags for categorization.
        is_breaking_change: Whether this change is a breaking change (default False).

    Example:
        >>> proposal = ModelChangeProposal.create(
        ...     change_type="model_swap",
        ...     description="Replace GPT-4 with Claude-3.5",
        ...     before_config={"model": "gpt-4", "provider": "openai"},
        ...     after_config={"model": "claude-3-5-sonnet", "provider": "anthropic"},
        ...     rationale="50% cost reduction with comparable quality",
        ... )
        >>> proposal.change_type
        'model_swap'
        >>> proposal.get_changed_keys()
        {'model', 'provider'}

    To modify a frozen instance, use model_copy():
        >>> modified = proposal.model_copy(update={"rationale": "Updated rationale"})

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )

    # Discriminator field FIRST per codebase pattern
    change_type: EnumChangeType = Field(
        ...,
        description="Type of change being proposed",
    )

    change_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this proposal",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the change",
    )

    before_config: dict[str, object] = Field(
        ...,
        description="Current configuration state",
    )

    after_config: dict[str, object] = Field(
        ...,
        description="Proposed configuration state",
    )

    rationale: str = Field(
        ...,
        min_length=1,
        description="Why this change is proposed",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the proposal was created (UTC)",
    )

    proposed_by: str | None = Field(
        default=None,
        description="Who proposed this change",
    )

    estimated_impact: str | None = Field(
        default=None,
        description="Expected improvement from this change",
    )

    rollback_plan: str | None = Field(
        default=None,
        description="How to revert if needed",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking related operations",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing this change proposal",
    )

    is_breaking_change: bool = Field(
        default=False,
        description="Whether this change is a breaking change",
    )

    @field_validator("description", "rationale", mode="after")
    @classmethod
    def _validate_not_whitespace_only(cls, v: str) -> str:
        """Validate that description and rationale are not whitespace-only."""
        if not v.strip():
            raise ValueError("cannot be whitespace-only")
        return v

    @field_validator("before_config", "after_config", mode="after")
    @classmethod
    def _validate_config_not_empty(cls, v: dict[str, object]) -> dict[str, object]:
        """Validate that before_config and after_config are not empty."""
        if not v:
            raise ValueError("cannot be empty")
        return v

    @model_validator(mode="after")
    def _validate_configs_differ(self) -> Self:
        """
        Validate before_config and after_config are not identical.

        A change proposal must represent an actual change. If the before
        and after configurations are identical, there is nothing to propose.

        Returns:
            Self: The validated model instance

        Raises:
            ModelOnexError: If before_config and after_config are identical
        """
        if self.before_config == self.after_config:
            raise ModelOnexError(
                message="before_config and after_config cannot be identical",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                change_type=self.change_type,
                change_id=str(self.change_id),
            )
        return self

    @classmethod
    def create(
        cls,
        change_type: EnumChangeType | str,
        description: str,
        before_config: dict[str, object],
        after_config: dict[str, object],
        rationale: str,
        *,
        change_id: UUID | None = None,
        proposed_by: str | None = None,
        estimated_impact: str | None = None,
        rollback_plan: str | None = None,
        correlation_id: UUID | None = None,
        tags: list[str] | None = None,
        is_breaking_change: bool = False,
    ) -> "ModelChangeProposal":
        """
        Factory method for creating a change proposal.

        This is the preferred way to create ModelChangeProposal instances
        as it provides a clear, documented API with keyword-only optional
        arguments.

        Args:
            change_type: Type of change (model_swap, config_change, endpoint_change).
                Can be an EnumChangeType enum value or its string value.
            description: Human-readable description
            before_config: Current configuration state
            after_config: Proposed configuration state
            rationale: Why this change is proposed
            change_id: Optional - explicit ID for this proposal
            proposed_by: Optional - who proposed the change
            estimated_impact: Optional - expected improvement
            rollback_plan: Optional - how to revert
            correlation_id: Optional - for tracking related operations
            tags: Optional - list of tags for categorization
            is_breaking_change: Optional - whether this is a breaking change

        Returns:
            A new ModelChangeProposal instance.

        Raises:
            ModelOnexError: If before_config and after_config are identical

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="endpoint_change",
            ...     description="Switch to faster API endpoint",
            ...     before_config={"url": "https://api.old.com/v1"},
            ...     after_config={"url": "https://api.new.com/v2"},
            ...     rationale="New endpoint has 2x lower latency",
            ...     proposed_by="system-optimizer",
            ...     estimated_impact="50% latency reduction",
            ... )
        """
        # Convert string to enum if needed
        if isinstance(change_type, str):
            change_type = EnumChangeType(change_type)

        # Build with explicit arguments to satisfy mypy strict mode
        if change_id is not None:
            return cls(
                change_type=change_type,
                change_id=change_id,
                description=description,
                before_config=before_config,
                after_config=after_config,
                rationale=rationale,
                proposed_by=proposed_by,
                estimated_impact=estimated_impact,
                rollback_plan=rollback_plan,
                correlation_id=correlation_id,
                tags=tags if tags is not None else [],
                is_breaking_change=is_breaking_change,
            )
        return cls(
            change_type=change_type,
            description=description,
            before_config=before_config,
            after_config=after_config,
            rationale=rationale,
            proposed_by=proposed_by,
            estimated_impact=estimated_impact,
            rollback_plan=rollback_plan,
            correlation_id=correlation_id,
            tags=tags if tags is not None else [],
            is_breaking_change=is_breaking_change,
        )

    def get_changed_keys(self) -> set[str]:
        """
        Get the set of keys that differ between before_config and after_config.

        This method identifies:
        - Keys where values differ between before and after
        - Keys that exist only in before_config (removed)
        - Keys that exist only in after_config (added)

        Returns:
            Set of keys where values differ or keys that exist in only one config.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="config_change",
            ...     description="Update settings",
            ...     before_config={"a": 1, "b": 2, "c": 3},
            ...     after_config={"a": 1, "b": 5, "d": 4},
            ...     rationale="Optimize performance",
            ... )
            >>> sorted(proposal.get_changed_keys())
            ['b', 'c', 'd']
        """
        before_keys = set(self.before_config.keys())
        after_keys = set(self.after_config.keys())

        # Keys that exist in only one config
        added_keys = after_keys - before_keys
        removed_keys = before_keys - after_keys

        # Keys that exist in both but have different values
        common_keys = before_keys & after_keys
        modified_keys = {
            key
            for key in common_keys
            if self.before_config[key] != self.after_config[key]
        }

        return added_keys | removed_keys | modified_keys

    def get_diff_summary(self) -> str:
        """
        Get a human-readable summary of the configuration differences.

        This method produces a formatted string showing:
        - Added keys (in after_config but not in before_config)
        - Removed keys (in before_config but not in after_config)
        - Modified keys (value changed between before and after)

        Returns:
            Formatted string showing before/after values for changed keys.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="model_swap",
            ...     description="Upgrade model",
            ...     before_config={"model": "v1", "temp": 0.5},
            ...     after_config={"model": "v2", "temp": 0.7, "top_p": 0.9},
            ...     rationale="Better accuracy",
            ... )
            >>> print(proposal.get_diff_summary())  # doctest: +NORMALIZE_WHITESPACE
            Configuration Changes:
              [+] top_p: 0.9 (added)
              [~] model: 'v1' -> 'v2'
              [~] temp: 0.5 -> 0.7
        """
        before_keys = set(self.before_config.keys())
        after_keys = set(self.after_config.keys())

        added_keys = sorted(after_keys - before_keys)
        removed_keys = sorted(before_keys - after_keys)
        common_keys = before_keys & after_keys
        modified_keys = sorted(
            key
            for key in common_keys
            if self.before_config[key] != self.after_config[key]
        )

        lines: list[str] = ["Configuration Changes:"]

        for key in added_keys:
            lines.append(f"  [+] {key}: {self.after_config[key]!r} (added)")

        for key in removed_keys:
            lines.append(f"  [-] {key}: {self.before_config[key]!r} (removed)")

        for key in modified_keys:
            before_val = self.before_config[key]
            after_val = self.after_config[key]
            lines.append(f"  [~] {key}: {before_val!r} -> {after_val!r}")

        if len(lines) == 1:
            lines.append("  (no changes detected)")

        return "\n".join(lines)

    def get_model_names(self) -> dict[str, str | None] | None:
        """
        Extract old and new model names for MODEL_SWAP change type.

        This method is specifically for MODEL_SWAP proposals to extract
        the model names from the before/after configurations.

        Returns:
            Dictionary with "old_model" and "new_model" keys if change_type
            is MODEL_SWAP, None otherwise.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="model_swap",
            ...     description="Upgrade model",
            ...     before_config={"model_name": "gpt-4"},
            ...     after_config={"model_name": "gpt-4-turbo"},
            ...     rationale="Better performance",
            ... )
            >>> proposal.get_model_names()
            {'old_model': 'gpt-4', 'new_model': 'gpt-4-turbo'}
        """
        if self.change_type != EnumChangeType.MODEL_SWAP:
            return None

        old_model = self.before_config.get("model_name")
        new_model = self.after_config.get("model_name")

        return {
            "old_model": str(old_model) if old_model is not None else None,
            "new_model": str(new_model) if new_model is not None else None,
        }

    @classmethod
    def create_model_swap(
        cls,
        old_model: str,
        new_model: str,
        description: str,
        rationale: str,
        before_config: dict[str, object],
        after_config: dict[str, object],
        *,
        change_id: UUID | None = None,
        proposed_by: str | None = None,
        estimated_impact: str | None = None,
        rollback_plan: str | None = None,
        correlation_id: UUID | None = None,
        tags: list[str] | None = None,
        is_breaking_change: bool = False,
    ) -> "ModelChangeProposal":
        """
        Factory method specifically for creating model swap proposals.

        This is a convenience method that creates a ModelChangeProposal with
        change_type set to MODEL_SWAP and stores the old/new model names
        in the configuration.

        Args:
            old_model: Name of the model being replaced
            new_model: Name of the replacement model
            description: Human-readable description
            rationale: Why this change is proposed
            before_config: Current configuration state
            after_config: Proposed configuration state
            change_id: Optional - explicit ID for this proposal
            proposed_by: Optional - who proposed the change
            estimated_impact: Optional - expected improvement
            rollback_plan: Optional - how to revert
            correlation_id: Optional - for tracking related operations
            tags: Optional - list of tags for categorization
            is_breaking_change: Optional - whether this is a breaking change

        Returns:
            A new ModelChangeProposal instance with MODEL_SWAP type.

        Example:
            >>> proposal = ModelChangeProposal.create_model_swap(
            ...     old_model="gpt-4",
            ...     new_model="gpt-4-turbo",
            ...     description="Upgrade to GPT-4 Turbo",
            ...     rationale="Better performance at lower cost",
            ...     before_config={"model_name": "gpt-4", "temperature": 0.7},
            ...     after_config={"model_name": "gpt-4-turbo", "temperature": 0.5},
            ... )
        """
        # Ensure model_name is in configs for get_model_names() to work
        # (but don't override if already present)
        final_before = dict(before_config)
        final_after = dict(after_config)

        if "model_name" not in final_before:
            final_before["model_name"] = old_model
        if "model_name" not in final_after:
            final_after["model_name"] = new_model

        return cls.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description=description,
            rationale=rationale,
            before_config=final_before,
            after_config=final_after,
            change_id=change_id,
            proposed_by=proposed_by,
            estimated_impact=estimated_impact,
            rollback_plan=rollback_plan,
            correlation_id=correlation_id,
            tags=tags,
            is_breaking_change=is_breaking_change,
        )
