from pydantic import BaseModel, Field


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    action_name: str = Field(
        ...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        ...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: dict[str, ModelActionConfigValue] = Field(
        default_factory=dict,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
