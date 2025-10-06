from pydantic import BaseModel, Field


class ModelGroupServiceEndpoint(BaseModel):
    """HTTP endpoint definition for group services."""

    path: str = Field(description="HTTP endpoint path")
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE)")
    description: str = Field(description="Endpoint purpose and functionality")
    delegation_target: str | None = Field(
        default=None,
        description="Tool to delegate requests to",
    )
    authentication_required: bool = Field(
        default=True,
        description="Whether authentication is required",
    )
