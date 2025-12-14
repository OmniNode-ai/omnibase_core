from pydantic import BaseModel, ConfigDict


class ModelConfig(BaseModel):
    """Pydantic model configuration for service discovery manager."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
