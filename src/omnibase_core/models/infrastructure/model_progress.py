"""
Progress Model (Composed).

Composed model that combines focused progress tracking components.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_status_message import EnumStatusMessage
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_metrics_data import ModelMetricsData
from omnibase_core.types.type_serializable_value import SerializedDict

from .progress.model_progress_core import ModelProgressCore
from .progress.model_progress_metrics import ModelProgressMetrics
from .progress.model_progress_milestones import ModelProgressMilestones
from .progress.model_progress_timing import ModelProgressTiming


class ModelProgress(BaseModel):
    """
    Composed progress tracking model using focused components.

    Provides comprehensive progress tracking with percentage validation,
    phase management, timing utilities, milestone tracking, and custom metrics.

    Uses composition pattern with focused components for maintainability.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Composed components
    core: ModelProgressCore = Field(
        default_factory=ModelProgressCore,
        description="Core progress tracking (percentage, steps, phases, status)",
    )
    timing: ModelProgressTiming = Field(
        default_factory=ModelProgressTiming,
        description="Timing and duration calculations",
    )
    milestones: ModelProgressMilestones = Field(
        default_factory=ModelProgressMilestones,
        description="Milestone management and tracking",
    )
    metrics: ModelProgressMetrics = Field(
        default_factory=ModelProgressMetrics,
        description="Custom metrics and tagging",
    )

    def model_post_init(self, __context: object) -> None:
        """Post-initialization to sync components."""
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    def _sync_timing_with_core(self) -> None:
        """Sync timing estimates with core progress."""
        self.timing.update_time_estimates(self.core.percentage)

    def _sync_milestones_with_core(self) -> None:
        """Sync milestone completion with core progress."""
        self.milestones.check_milestones(self.core.percentage)

    def _sync_metrics_with_core(self) -> None:
        """Sync standard metrics with core progress."""
        self.metrics.update_standard_metrics(
            percentage=self.core.percentage,
            current_step=self.core.current_step,
            total_steps=self.core.total_steps,
            is_completed=self.core.is_completed,
            elapsed_seconds=self.timing.elapsed_seconds,
        )

    # Properties for direct access
    @property
    def percentage(self) -> float:
        return self.core.percentage

    @percentage.setter
    def percentage(self, value: float) -> None:
        self.core.update_percentage(value)
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    @property
    def current_step(self) -> int:
        return self.core.current_step

    @current_step.setter
    def current_step(self, value: int) -> None:
        self.core.update_step(value)
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    @property
    def total_steps(self) -> int:
        return self.core.total_steps

    @total_steps.setter
    def total_steps(self, value: int) -> None:
        self.core.total_steps = value
        self.core._update_percentage_from_steps()
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    @property
    def current_phase(self) -> EnumExecutionPhase:
        return self.core.current_phase

    @property
    def phase_percentage(self) -> float:
        return self.core.phase_percentage

    @property
    def status_message(self) -> EnumStatusMessage:
        return self.core.status_message

    @property
    def detailed_info(self) -> str:
        return self.core.detailed_info

    @property
    def start_time(self) -> datetime:
        return self.timing.start_time

    @property
    def last_update_time(self) -> datetime:
        return self.timing.last_update_time

    @property
    def estimated_completion_time(self) -> datetime | None:
        return self.timing.estimated_completion_time

    @property
    def is_completed(self) -> bool:
        return self.core.is_completed

    @property
    def is_started(self) -> bool:
        return self.core.is_started

    @property
    def elapsed_time(self) -> timedelta:
        return self.timing.elapsed_time

    @property
    def elapsed_seconds(self) -> float:
        return self.timing.elapsed_seconds

    @property
    def elapsed_minutes(self) -> float:
        return self.timing.elapsed_minutes

    @property
    def estimated_total_duration(self) -> timedelta | None:
        if self.timing.estimated_total_duration:
            return self.timing.estimated_total_duration.to_timedelta()
        return None

    @property
    def estimated_remaining_duration(self) -> timedelta | None:
        if self.timing.estimated_remaining_duration:
            return self.timing.estimated_remaining_duration.to_timedelta()
        return None

    @property
    def completion_rate_per_minute(self) -> float:
        return self.timing.get_completion_rate_per_minute(self.core.percentage)

    @property
    def custom_metrics(self) -> ModelMetricsData:
        return self.metrics.custom_metrics

    @property
    def tags(self) -> list[str]:
        return self.metrics.tags

    # Update methods
    def update_percentage(self, new_percentage: float) -> None:
        self.core.update_percentage(new_percentage)
        self.timing.update_timestamp()
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    def update_step(self, new_step: int) -> None:
        self.core.update_step(new_step)
        self.timing.update_timestamp()
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    def increment_step(self, steps: int = 1) -> None:
        self.core.increment_step(steps)
        self.timing.update_timestamp()
        self._sync_timing_with_core()
        self._sync_milestones_with_core()

    def set_phase(
        self,
        phase: EnumExecutionPhase,
        phase_percentage: float = 0.0,
    ) -> None:
        self.core.set_phase(phase, phase_percentage)
        self.timing.update_timestamp()

    def update_phase_percentage(self, percentage: float) -> None:
        self.core.update_phase_percentage(percentage)
        self.timing.update_timestamp()

    def set_status(self, status: EnumStatusMessage, detailed_info: str = "") -> None:
        self.core.set_status(status, detailed_info)
        self.timing.update_timestamp()

    def add_milestone(self, name: str, percentage: float) -> None:
        self.milestones.add_milestone(name, percentage)
        self._sync_milestones_with_core()

    def remove_milestone(self, name: str) -> bool:
        return self.milestones.remove_milestone(name)

    def get_next_milestone(self) -> tuple[str, float] | None:
        return self.milestones.get_next_milestone(self.core.percentage)

    def add_custom_metric(self, key: str, value: ModelFlexibleValue) -> None:
        self.metrics.add_custom_metric(key, value)

    def add_tag(self, tag: str) -> None:
        self.metrics.add_tag(tag)

    def remove_tag(self, tag: str) -> bool:
        return self.metrics.remove_tag(tag)

    def reset(self) -> None:
        self.core.reset()
        self.timing.reset()
        self.milestones.reset()
        self.metrics.reset()

    def get_time_remaining_formatted(self) -> str:
        return self.timing.get_time_remaining_formatted()

    def get_elapsed_formatted(self) -> str:
        return self.timing.get_elapsed_formatted()

    def get_estimated_total_formatted(self) -> str:
        return self.timing.get_estimated_total_formatted()

    def get_summary(self) -> dict[str, ModelFlexibleValue]:
        # Sync all components
        self._sync_timing_with_core()
        self._sync_milestones_with_core()
        self._sync_metrics_with_core()

        # Get comprehensive summary
        summary = {
            "percentage": ModelFlexibleValue.from_float(self.core.percentage),
            "current_step": ModelFlexibleValue.from_integer(self.core.current_step),
            "total_steps": ModelFlexibleValue.from_integer(self.core.total_steps),
            "current_phase": ModelFlexibleValue.from_string(
                self.core.current_phase.value,
            ),
            "phase_percentage": ModelFlexibleValue.from_float(
                self.core.phase_percentage,
            ),
            "status_message": ModelFlexibleValue.from_string(
                str(self.core.status_message),
            ),
            "is_completed": ModelFlexibleValue.from_boolean(self.core.is_completed),
            "elapsed_seconds": ModelFlexibleValue.from_float(
                self.timing.elapsed_seconds,
            ),
            "estimated_remaining_seconds": ModelFlexibleValue.from_float(
                (
                    self.timing.estimated_remaining_duration.to_seconds()
                    if self.timing.estimated_remaining_duration
                    else 0.0
                ),
            ),
            "completed_milestones": ModelFlexibleValue.from_integer(
                self.milestones.get_completed_count(),
            ),
            "total_milestones": ModelFlexibleValue.from_integer(
                self.milestones.get_total_count(),
            ),
            "completion_rate_per_minute": ModelFlexibleValue.from_float(
                self.timing.get_completion_rate_per_minute(self.core.percentage),
            ),
            "elapsed_formatted": ModelFlexibleValue.from_string(
                self.timing.get_elapsed_formatted(),
            ),
            "remaining_formatted": ModelFlexibleValue.from_string(
                self.timing.get_time_remaining_formatted(),
            ),
            "total_formatted": ModelFlexibleValue.from_string(
                self.timing.get_estimated_total_formatted(),
            ),
        }

        # Add custom metrics
        summary.update(self.metrics.get_metrics_summary())

        return summary

    @classmethod
    def create_simple(cls, total_steps: int | None = None) -> ModelProgress:
        """Create simple progress tracker."""
        core = ModelProgressCore.create_simple(total_steps or 1)
        return cls(core=core)

    @classmethod
    def create_with_milestones(
        cls,
        milestones: dict[str, float],
        total_steps: int | None = None,
    ) -> ModelProgress:
        """Create progress tracker with predefined milestones."""
        core = ModelProgressCore.create_simple(total_steps or 1)
        milestone_component = ModelProgressMilestones.create_with_milestones(milestones)
        return cls(core=core, milestones=milestone_component)

    @classmethod
    def create_phased(
        cls,
        phases: list[EnumExecutionPhase],
        total_steps: int | None = None,
    ) -> ModelProgress:
        """Create progress tracker with phase milestones."""
        core = ModelProgressCore.create_phased(phases, total_steps or 1)
        milestone_component = ModelProgressMilestones.create_phased_milestones(phases)
        return cls(core=core, milestones=milestone_component)

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


# NOTE: model_rebuild() not needed - Pydantic v2 handles forward references automatically
# ModelMetadataValue is imported at runtime, Pydantic will resolve references lazily

# Export for use
__all__ = ["ModelProgress"]
