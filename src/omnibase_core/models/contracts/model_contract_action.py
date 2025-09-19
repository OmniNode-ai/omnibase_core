"""
Contract action model for node action definitions.

Provides strongly typed action specification for contract content.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractAction(BaseModel):
    """Action definition within a contract."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Action name identifier",
    )
    description: str | None = Field(
        None,
        description="Action description",
    )
    parameters: dict[str, str] | None = Field(
        None,
        description="Action parameters with type specifications",
    )
    return_type: str | None = Field(
        None,
        description="Return type specification",
    )
    category: str | None = Field(
        None,
        description="Action category",
    )
    deprecated: bool = Field(
        default=False,
        description="Whether action is deprecated",
    )
    examples: list[str] | None = Field(
        None,
        description="Usage examples",
    )
