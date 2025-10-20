"""Docker Resource Limits Model.

Resource limits for Docker services.
"""

from pydantic import BaseModel, Field


class ModelDockerResourceLimits(BaseModel):
    """Resource limits for Docker services."""

    cpus: str | None = Field(
        default=None,
        description="CPU limit (e.g., '0.5', '2')",
    )
    memory: str | None = Field(
        default=None,
        description="Memory limit (e.g., '512M', '2G')",
    )
