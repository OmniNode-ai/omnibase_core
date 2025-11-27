from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"\nDependencies model for node introspection.\n"
from pydantic import BaseModel


class ModelDependencies(BaseModel):
    """Model for node dependencies specification."""

    runtime: list[str] = Field(
        default_factory=list, description="Required runtime dependencies"
    )
    optional: list[str] = Field(
        default_factory=list, description="Optional dependencies"
    )
    python_version: ModelSemVer = Field(
        default=..., description="Required Python version"
    )
    external_tools: list[str] = Field(
        default_factory=list, description="Required external tools"
    )
