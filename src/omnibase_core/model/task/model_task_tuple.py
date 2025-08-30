"""Model for task routing tuple data."""

from typing import Union

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_optional_string import ModelOptionalString


class ModelTaskTuple(BaseModel):
    """
    Strongly-typed model for task routing data.

    Replaces Tuple[str, str, Optional[str]] to comply with ONEX
    standards requiring specific typed models instead of generic types.
    """

    task_role: str = Field(..., description="Required agent role for the task")

    prompt: str = Field(..., description="Task prompt to execute")

    system_prompt: ModelOptionalString = Field(
        default_factory=ModelOptionalString,
        description="Optional system prompt for context",
    )

    def to_tuple(self) -> tuple:
        """Convert to tuple representation for backward compatibility."""
        return (self.task_role, self.prompt, self.system_prompt.get())

    @classmethod
    def from_tuple(cls, data: tuple) -> "ModelTaskTuple":
        """Create from tuple representation."""
        if len(data) >= 3:
            return cls(
                task_role=data[0],
                prompt=data[1],
                system_prompt=ModelOptionalString(value=data[2]),
            )
        elif len(data) == 2:
            return cls(
                task_role=data[0], prompt=data[1], system_prompt=ModelOptionalString()
            )
        else:
            raise ValueError("Tuple must have at least 2 elements")

    def get_task_role(self) -> str:
        """Get the task role."""
        return self.task_role

    def get_prompt(self) -> str:
        """Get the task prompt."""
        return self.prompt

    def get_system_prompt(self) -> Union[str, None]:
        """Get the optional system prompt."""
        return self.system_prompt.get()

    def has_system_prompt(self) -> bool:
        """Check if system prompt is provided."""
        return self.system_prompt.has_value()
