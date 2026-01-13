"""
Output Transformation Configuration Model.

Output transformation and formatting rules defining transformation logic,
formatting rules, and post-processing configuration for output data.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelOutputTransformationConfig(BaseModel):
    """
    Output transformation and formatting rules.

    Defines transformation logic, formatting rules, and
    post-processing configuration for output data.
    """

    format_type: str = Field(default="standard", description="Output format type")

    precision_control: bool = Field(
        default=True,
        description="Enable precision control for numeric outputs",
    )

    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Output transformation rules",
    )

    validation_enabled: bool = Field(
        default=True,
        description="Enable output validation before return",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
