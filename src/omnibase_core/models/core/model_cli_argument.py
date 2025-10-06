from pydantic import Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

"""
CLI argument model for command specification.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_schema_value import ModelSchemaValue


class ModelCLIArgument(BaseModel):
    """Model for CLI argument specification."""

    name: str = Field(..., description="Argument name (e.g., 'files', '--author')")
    type: str = Field(..., description="Argument type (e.g., 'str', 'bool', 'int')")
    required: bool = Field(..., description="Whether argument is required")
    description: str = Field(..., description="Human-readable argument description")
    default: ModelSchemaValue | None = Field(
        default=None,
        description="Default value if optional",
    )
    choices: list[str] | None = Field(
        default=None, description="Valid choices for argument"
    )
