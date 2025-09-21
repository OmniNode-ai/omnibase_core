"""
Progress Model.

Specialized model for tracking and managing progress with validation and utilities.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_execution_phase import EnumExecutionPhase
from ...enums.enum_status_message import EnumStatusMessage
from .model_metrics_data import ModelMetricsData


class ModelProgress(BaseModel):
    """
    Progress tracking model.

    Provides comprehensive progress tracking with percentage validation,
    phase management, and timing utilities.
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
    total_steps: int | None = Field(
        default=None,
        description="Total number of steps",
        ge=1,
    )

    # Phase tracking
    current_phase: EnumExecutionPhase | None = Field(
        default=None,
        description="Current execution phase",
    )
    phase_percentage: float = Field(
        default=0.0,
        description="Progress within current phase",
        ge=0.0,
        le=100.0,
    )

    # Status and description
    status_message: EnumStatusMessage | None = Field(
        default=None,
        description="Current progress status",
    )
    detailed_info: str | None = Field(
        default=None,
        description="Detailed progress information",
        max_length=2000,
    )

    # Timing information
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Progress tracking start time",
    )
    last_update_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last progress update time",
    )
    estimated_completion_time: datetime | None = Field(
        default=None,
        description="Estimated completion time",
    )

    # Progress milestones
    milestones: dict[str, float] = Field(
        default_factory=dict,
        description="Named progress milestones (name -> percentage)",
    )
    completed_milestones: list[str] = Field(
        default_factory=list,
        description="List of completed milestone names",
    )

    # Metadata
    custom_metrics: ModelMetricsData = Field(
        default_factory=lambda: ModelMetricsData(collection_name="progress_metrics"),
        description="Custom progress metrics with clean typing",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Progress tracking tags",
    )

    @field_validator("current_step")
    @classmethod
    def validate_current_step(cls, v: int, info: Any) -> int:
        """Validate current step doesn't exceed total steps."""
        if "total_steps" in info.data and info.data["total_steps"] is not None:
            total = info.data["total_steps"]
            if v > total:
                msg = "Current step cannot exceed total steps"
                raise ValueError(msg)
        return v

    @field_validator("milestones")
    @classmethod
    def validate_milestones(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate milestone percentages are valid."""
        for name, percentage in v.items():
            if not 0.0 <= percentage <= 100.0:
                msg = f"Milestone '{name}' percentage must be between 0.0 and 100.0"
                raise ValueError(msg)
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to update calculated fields."""
        self._update_percentage_from_steps()
        self._check_milestones()

    def _update_percentage_from_steps(self) -> None:
        """Update percentage based on steps if available."""
        if self.total_steps is not None and self.total_steps > 0:
            calculated_percentage = (self.current_step / self.total_steps) * 100.0
            # Only update if not manually set (i.e., still at default)
            if (
                self.percentage == 0.0
                or abs(self.percentage - calculated_percentage) < 0.1
            ):
                self.percentage = min(100.0, calculated_percentage)

    def _check_milestones(self) -> None:
        """Check and update completed milestones."""
        for name, milestone_percentage in self.milestones.items():
            if (
                self.percentage >= milestone_percentage
                and name not in self.completed_milestones
            ):
                self.completed_milestones.append(name)

    @property
    def is_completed(self) -> bool:
        """Check if progress is completed (100%)."""
        return self.percentage >= 100.0

    @property
    def is_started(self) -> bool:
        """Check if progress has started (> 0%)."""
        return self.percentage > 0.0

    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since start."""
        return datetime.now(UTC) - self.start_time

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.elapsed_time.total_seconds()

    @property
    def elapsed_minutes(self) -> float:
        """Get elapsed time in minutes."""
        return self.elapsed_seconds / 60.0

    @property
    def estimated_total_duration(self) -> timedelta | None:
        """Estimate total duration based on current progress."""
        if self.percentage <= 0.0:
            return None

        elapsed = self.elapsed_time
        estimated_total_seconds = (elapsed.total_seconds() / self.percentage) * 100.0
        return timedelta(seconds=estimated_total_seconds)

    @property
    def estimated_remaining_duration(self) -> timedelta | None:
        """Estimate remaining duration."""
        if self.is_completed:
            return timedelta(0)

        total_duration = self.estimated_total_duration
        if total_duration is None:
            return None

        return total_duration - self.elapsed_time

    @property
    def completion_rate_per_minute(self) -> float:
        """Get completion rate as percentage per minute."""
        if self.elapsed_minutes <= 0.0:
            return 0.0
        return self.percentage / self.elapsed_minutes

    def update_percentage(self, new_percentage: float) -> None:
        """Update progress percentage."""
        self.percentage = max(0.0, min(100.0, new_percentage))
        self.last_update_time = datetime.now(UTC)
        self._check_milestones()
        self._update_estimated_completion()

    def update_step(self, new_step: int) -> None:
        """Update current step and recalculate percentage."""
        if self.total_steps is not None:
            new_step = min(new_step, self.total_steps)
        self.current_step = max(0, new_step)
        self.last_update_time = datetime.now(UTC)
        self._update_percentage_from_steps()
        self._check_milestones()
        self._update_estimated_completion()

    def increment_step(self, steps: int = 1) -> None:
        """Increment current step by specified amount."""
        self.update_step(self.current_step + steps)

    def set_phase(
        self, phase: EnumExecutionPhase, phase_percentage: float = 0.0
    ) -> None:
        """Set current execution phase."""
        self.current_phase = phase
        self.phase_percentage = max(0.0, min(100.0, phase_percentage))
        self.last_update_time = datetime.now(UTC)

    def update_phase_percentage(self, percentage: float) -> None:
        """Update percentage within current phase."""
        self.phase_percentage = max(0.0, min(100.0, percentage))
        self.last_update_time = datetime.now(UTC)

    def set_status(
        self, status: EnumStatusMessage, detailed_info: str | None = None
    ) -> None:
        """Set status and optional detailed info."""
        self.status_message = status
        if detailed_info is not None:
            self.detailed_info = detailed_info
        self.last_update_time = datetime.now(UTC)

    def add_milestone(self, name: str, percentage: float) -> None:
        """Add a progress milestone."""
        if not 0.0 <= percentage <= 100.0:
            msg = "Milestone percentage must be between 0.0 and 100.0"
            raise ValueError(msg)
        self.milestones[name] = percentage
        self._check_milestones()

    def remove_milestone(self, name: str) -> bool:
        """Remove a milestone. Returns True if milestone existed."""
        removed = name in self.milestones
        self.milestones.pop(name, None)
        if name in self.completed_milestones:
            self.completed_milestones.remove(name)
        return removed

    def get_next_milestone(self) -> tuple[str, float] | None:
        """Get the next uncompleted milestone."""
        uncompleted = {
            name: percentage
            for name, percentage in self.milestones.items()
            if name not in self.completed_milestones and percentage > self.percentage
        }
        if not uncompleted:
            return None

        next_name = min(uncompleted, key=lambda name: uncompleted[name])
        return (next_name, uncompleted[next_name])

    def add_custom_metric(self, key: str, value: str | int | float | bool) -> None:
        """Add custom progress metric with proper typing."""
        self.custom_metrics.add_metric(key, value)
        self.last_update_time = datetime.now(UTC)

    def add_tag(self, tag: str) -> None:
        """Add a progress tag."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a progress tag. Returns True if tag existed."""
        try:
            self.tags.remove(tag)
            return True
        except ValueError:
            return False

    def _update_estimated_completion(self) -> None:
        """Update estimated completion time based on current progress."""
        remaining = self.estimated_remaining_duration
        if remaining is not None:
            self.estimated_completion_time = datetime.now(UTC) + remaining

    def reset(self) -> None:
        """Reset progress to initial state."""
        self.percentage = 0.0
        self.current_step = 0
        self.phase_percentage = 0.0
        self.current_phase = None
        self.status_message = None
        self.detailed_info = None
        self.start_time = datetime.now(UTC)
        self.last_update_time = self.start_time
        self.estimated_completion_time = None
        self.completed_milestones.clear()
        self.custom_metrics.clear_all_metrics()

    def get_summary(self) -> dict[str, str | int | bool | float | None]:
        """Get progress summary."""
        return {
            "percentage": self.percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "phase_percentage": self.phase_percentage,
            "status_message": self.status_message,
            "is_completed": self.is_completed,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_remaining_seconds": (
                self.estimated_remaining_duration.total_seconds()
                if self.estimated_remaining_duration
                else None
            ),
            "completed_milestones": len(self.completed_milestones),
            "total_milestones": len(self.milestones),
            "completion_rate_per_minute": self.completion_rate_per_minute,
        }

    @classmethod
    def create_simple(cls, total_steps: int | None = None) -> ModelProgress:
        """Create simple progress tracker."""
        return cls(total_steps=total_steps)

    @classmethod
    def create_with_milestones(
        cls,
        milestones: dict[str, float],
        total_steps: int | None = None,
    ) -> ModelProgress:
        """Create progress tracker with predefined milestones."""
        return cls(
            total_steps=total_steps,
            milestones=milestones,
        )

    @classmethod
    def create_phased(
        cls,
        phases: list[EnumExecutionPhase],
        total_steps: int | None = None,
    ) -> ModelProgress:
        """Create progress tracker with phase milestones."""
        milestones = {}
        phase_increment = 100.0 / len(phases)

        for i, phase in enumerate(phases):
            milestone_percentage = (i + 1) * phase_increment
            milestones[f"phase_{phase.value}"] = milestone_percentage

        return cls(
            total_steps=total_steps,
            milestones=milestones,
        )


# Export for use
__all__ = ["ModelProgress"]
