from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .model_action_config_parameter import ModelActionConfigParameter


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    action_name: str = Field(
        default=...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        default=...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: list[ModelActionConfigParameter] = Field(
        default_factory=list,
        description="Strongly-typed configuration parameters for the action",
    )

    execution_order: int = Field(
        default=1,
        description="Order of execution relative to other actions",
        ge=1,
    )

    is_critical: bool = Field(
        default=False,
        description="Whether action failure should abort transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Action to execute if rollback is needed",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for action execution",
        ge=1,
    )

    @model_validator(mode="after")
    def validate_unique_action_config(self) -> ModelFSMTransitionAction:
        """Ensure action_config parameter names are unique."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for param in self.action_config:
            if param.parameter_name in seen:
                duplicates.add(param.parameter_name)
            seen.add(param.parameter_name)
        if duplicates:
            raise ValueError(
                f"Duplicate parameter names in action_config: {sorted(duplicates)}"
            )
        return self

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
