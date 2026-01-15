"""
Progress Milestones Model.

Milestone management and tracking for progress monitoring.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelProgressMilestones(BaseModel):
    """
    Progress milestone management with validation and tracking.

    Focused on milestone creation, validation, and completion tracking.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Progress milestones
    milestones: dict[str, float] = Field(
        default_factory=dict,
        description="Named progress milestones (name -> percentage)",
    )
    completed_milestones: list[str] = Field(
        default_factory=list,
        description="List of completed milestone names",
    )

    @field_validator("milestones")
    @classmethod
    def validate_milestones(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate milestone percentages are valid."""
        for name, percentage in v.items():
            if not 0.0 <= percentage <= 100.0:
                msg = f"Milestone '{name}' percentage must be between 0.0 and 100.0"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
        return v

    def check_milestones(self, current_percentage: float) -> list[str]:
        """Check and update completed milestones. Returns newly completed milestones."""
        newly_completed = []
        for name, milestone_percentage in self.milestones.items():
            if (
                current_percentage >= milestone_percentage
                and name not in self.completed_milestones
            ):
                self.completed_milestones.append(name)
                newly_completed.append(name)
        return newly_completed

    def add_milestone(self, name: str, percentage: float) -> None:
        """Add a progress milestone."""
        if not 0.0 <= percentage <= 100.0:
            msg = "Milestone percentage must be between 0.0 and 100.0"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        self.milestones[name] = percentage

    def remove_milestone(self, name: str) -> bool:
        """Remove a milestone. Returns True if milestone existed."""
        removed = name in self.milestones
        self.milestones.pop(name, None)
        if name in self.completed_milestones:
            self.completed_milestones.remove(name)
        return removed

    def get_next_milestone(self, current_percentage: float) -> tuple[str, float] | None:
        """Get the next uncompleted milestone."""
        uncompleted = {
            name: percentage
            for name, percentage in self.milestones.items()
            if name not in self.completed_milestones and percentage > current_percentage
        }
        if not uncompleted:
            return None

        next_name = min(uncompleted, key=lambda name: uncompleted[name])
        return (next_name, uncompleted[next_name])

    def get_completed_count(self) -> int:
        """Get count of completed milestones."""
        return len(self.completed_milestones)

    def get_total_count(self) -> int:
        """Get total count of milestones."""
        return len(self.milestones)

    def get_completion_ratio(self) -> float:
        """Get milestone completion ratio (0.0 to 1.0)."""
        if not self.milestones:
            return 1.0
        return len(self.completed_milestones) / len(self.milestones)

    def is_milestone_completed(self, name: str) -> bool:
        """Check if a specific milestone is completed."""
        return name in self.completed_milestones

    def get_milestone_percentage(self, name: str) -> float | None:
        """Get percentage for a specific milestone."""
        return self.milestones.get(name)

    def get_uncompleted_milestones(self, current_percentage: float) -> dict[str, float]:
        """Get all uncompleted milestones."""
        return {
            name: percentage
            for name, percentage in self.milestones.items()
            if name not in self.completed_milestones
        }

    def get_upcoming_milestones(
        self,
        current_percentage: float,
        limit: int = 3,
    ) -> list[tuple[str, float]]:
        """Get upcoming milestones sorted by percentage."""
        uncompleted = self.get_uncompleted_milestones(current_percentage)
        upcoming = [
            (name, percentage)
            for name, percentage in uncompleted.items()
            if percentage > current_percentage
        ]
        upcoming.sort(key=lambda x: x[1])  # Sort by percentage
        return upcoming[:limit]

    def reset(self) -> None:
        """Reset milestone completion status."""
        self.completed_milestones.clear()

    def clear_all_milestones(self) -> None:
        """Clear all milestones and completion status."""
        self.milestones.clear()
        self.completed_milestones.clear()

    @classmethod
    def create_with_milestones(
        cls,
        milestones: dict[str, float],
    ) -> ModelProgressMilestones:
        """Create milestone tracker with predefined milestones."""
        return cls(milestones=milestones)

    @classmethod
    def create_phased_milestones(
        cls,
        phases: list[EnumExecutionPhase],
    ) -> ModelProgressMilestones:
        """Create milestone tracker with phase-based milestones."""
        if not phases:
            return cls(milestones={})
        milestones = {}
        phase_increment = 100.0 / len(phases)

        for i, phase in enumerate(phases):
            milestone_percentage = (i + 1) * phase_increment
            milestones[f"phase_{phase.value}"] = milestone_percentage

        return cls(milestones=milestones)

    @classmethod
    def create_percentage_milestones(
        cls,
        increments: list[float],
    ) -> ModelProgressMilestones:
        """Create milestone tracker with percentage-based milestones."""
        milestones = {}
        for percentage in increments:
            if 0.0 <= percentage <= 100.0:
                milestones[f"{percentage}%"] = percentage

        return cls(milestones=milestones)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelProgressMilestones"]
