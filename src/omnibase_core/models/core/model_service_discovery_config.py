from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Pydantic model configuration for service discovery manager."""

    frozen = True
    extra = "forbid"
    validate_assignment = True
