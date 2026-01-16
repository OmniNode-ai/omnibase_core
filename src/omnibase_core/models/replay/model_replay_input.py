"""
Replay input model that bundles original inputs with configuration overrides.

This is the integration point for config override injection - overrides attach
to the REPLAY INPUT, not the manifest or handler config directly.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from typing import Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.replay.model_config_override_set import ModelConfigOverrideSet

T_Data = TypeVar("T_Data")


class ModelReplayInput(BaseModel, Generic[T_Data]):
    """
    Input model for replay execution with optional configuration overrides.

    Bundles the original input data with any config overrides to apply during
    replay. The overrides are applied at the START of replay execution, creating
    patched copies of configurations - NEVER mutating originals.

    Key Invariant:
        The original data (in `data` field) is NEVER modified. All overrides
        produce new copies via immutable update patterns.

    Thread Safety:
        Immutable (frozen=True) - safe for concurrent access.

    Example:
        >>> from omnibase_core.models.replay import ModelReplayInput, ModelConfigOverrideSet
        >>> replay_input = ModelReplayInput(
        ...     data=original_envelope,
        ...     config_overrides=ModelConfigOverrideSet(overrides=[
        ...         ModelConfigOverride(path="llm.temperature", value=0.5),
        ...     ]),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    input_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this replay input",
    )
    data: T_Data = Field(
        ...,
        description="The original input data for replay",
    )
    config_overrides: ModelConfigOverrideSet | None = Field(
        default=None,
        description="Optional configuration overrides to apply during replay",
    )

    @property
    def has_overrides(self) -> bool:
        """Check if this input has any config overrides."""
        return (
            self.config_overrides is not None
            and len(self.config_overrides.overrides) > 0
        )

    def with_overrides(
        self, overrides: ModelConfigOverrideSet
    ) -> "ModelReplayInput[T_Data]":
        """Return new input with overrides (immutable update)."""
        return ModelReplayInput(
            input_id=self.input_id,
            data=self.data,
            config_overrides=overrides,
        )


__all__ = ["ModelReplayInput"]
