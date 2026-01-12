"""
Progress Core Model.

Core progress tracking functionality with percentage, steps, and phase management.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_status_message import EnumStatusMessage
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelProgressCore(BaseModel):
    """
    Core progress tracking with percentage, steps, and phase management.

    Focused on fundamental progress tracking without timing or milestone complexity.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Core progress tracking
    percentage: float = Field(
        default=0.0,
        description="Progress percentage (0.0 to 100.0)",
        ge=0.0,
        le=100.0,
    )

    # Progress details
    current_step: int = Field(
        default=0,
        description="Current step number",
        ge=0,
    )
    total_steps: int = Field(
        default=1,
        description="Total number of steps",
        ge=1,
    )

    # Phase tracking
    current_phase: EnumExecutionPhase = Field(
        default=EnumExecutionPhase.INITIALIZATION,
        description="Current execution phase",
    )
    phase_percentage: float = Field(
        default=0.0,
        description="Progress within current phase",
        ge=0.0,
        le=100.0,
    )

    # Status and description
    status_message: EnumStatusMessage = Field(
        default=EnumStatusMessage.PENDING,
        description="Current progress status",
    )
    detailed_info: str = Field(
        default="",
        description="Detailed progress information",
        max_length=2000,
    )

    @model_validator(mode="after")
    def validate_current_step(self) -> Self:
        """Validate current step doesn't exceed total steps."""
        if self.current_step > self.total_steps:
            msg = "Current step cannot exceed total steps"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        return self

    def model_post_init(self, __context: object) -> None:
        """Post-initialization to update calculated fields."""
        self._update_percentage_from_steps()

    def _update_percentage_from_steps(self) -> None:
        """Update percentage based on steps if available."""
        if self.total_steps > 0:
            calculated_percentage = (self.current_step / self.total_steps) * 100.0
            # Only update if not manually set (i.e., still at default)
            if (
                self.percentage == 0.0
                or abs(self.percentage - calculated_percentage) < 0.1
            ):
                self.percentage = min(100.0, calculated_percentage)

    @property
    def is_completed(self) -> bool:
        """Check if progress is completed (100%)."""
        return self.percentage >= 100.0

    @property
    def is_started(self) -> bool:
        """Check if progress has started (> 0%)."""
        return self.percentage > 0.0

    @property
    def completion_ratio(self) -> float:
        """Get completion ratio (0.0 to 1.0)."""
        return self.percentage / 100.0

    def update_percentage(self, new_percentage: float) -> None:
        """Update progress percentage."""
        self.percentage = max(0.0, min(100.0, new_percentage))

    def update_step(self, new_step: int) -> None:
        """Update current step and recalculate percentage."""
        new_step = min(new_step, self.total_steps)
        self.current_step = max(0, new_step)
        self._update_percentage_from_steps()

    def increment_step(self, steps: int = 1) -> None:
        """Increment current step by specified amount."""
        self.update_step(self.current_step + steps)

    def set_phase(
        self,
        phase: EnumExecutionPhase,
        phase_percentage: float = 0.0,
    ) -> None:
        """Set current execution phase."""
        self.current_phase = phase
        self.phase_percentage = max(0.0, min(100.0, phase_percentage))

    def update_phase_percentage(self, percentage: float) -> None:
        """Update percentage within current phase."""
        self.phase_percentage = max(0.0, min(100.0, percentage))

    def set_status(self, status: EnumStatusMessage, detailed_info: str = "") -> None:
        """Set status and detailed info."""
        self.status_message = status
        if detailed_info:
            self.detailed_info = detailed_info

    def reset(self) -> None:
        """Reset progress core to initial state."""
        self.percentage = 0.0
        self.current_step = 0
        self.phase_percentage = 0.0
        self.current_phase = EnumExecutionPhase.INITIALIZATION
        self.status_message = EnumStatusMessage.PENDING
        self.detailed_info = ""

    @classmethod
    def create_simple(cls, total_steps: int = 1) -> ModelProgressCore:
        """Create simple progress core tracker."""
        return cls(total_steps=total_steps)

    @classmethod
    def create_phased(
        cls,
        phases: list[EnumExecutionPhase],
        total_steps: int = 1,
    ) -> ModelProgressCore:
        """Create progress core with phase tracking."""
        return cls(
            total_steps=total_steps,
            current_phase=phases[0] if phases else EnumExecutionPhase.INITIALIZATION,
        )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelProgressCore"]
