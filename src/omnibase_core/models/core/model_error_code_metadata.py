from pydantic import BaseModel, ConfigDict


class ModelErrorCodeMetadata(BaseModel):
    """Immutable error code metadata with enhanced information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    number: int
    description: str
    exit_code: int
    category: str
