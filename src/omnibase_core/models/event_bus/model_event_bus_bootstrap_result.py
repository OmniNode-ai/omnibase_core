from pydantic import BaseModel, Field


class ModelEventBusBootstrapResult(BaseModel):
    """
    Result model for event bus bootstrap operations (canonical, ONEX-compatible).
    """

    status: str = Field(
        default=..., description="Bootstrap status, e.g. 'ok' or 'error'."
    )
    message: str = Field(
        default=...,
        description="Human-readable message about the bootstrap result.",
    )
    # Add more fields as needed (e.g., error_code, details)
