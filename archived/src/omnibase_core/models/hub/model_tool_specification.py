"""
ONEX-compliant model for tool specifications in generation hub.

Replaces Dict[str, Any] with strongly typed Pydantic model following ONEX standards.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelToolSpecification(BaseModel):
    """
    Tool specification model for generation hub tool discovery and loading.

    Replaces Dict[str, Any] usage with strongly typed ONEX-compliant structure.
    """

    name: str = Field(..., description="Tool name identifier")
    version: ModelSemVer = Field(
        ...,
        description="Tool version following semantic versioning",
    )
    path: str = Field(..., description="Path to tool implementation")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Tool capabilities",
    )
    description: str | None = Field(None, description="Tool description")
    contract_path: str | None = Field(
        None,
        description="Path to tool contract definition",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Tool dependencies",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tool classification tags",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "tool_example_processor",
                "version": {"major": 1, "minor": 0, "patch": 0},
                "path": "/omnibase/tools/processing/tool_example_processor/v1_0_0",
                "capabilities": ["processing", "validation"],
                "description": "Example tool for data processing",
                "contract_path": "/omnibase/tools/processing/tool_example_processor/v1_0_0/node.onex.yaml",
                "dependencies": ["pydantic", "asyncio"],
                "tags": ["processing", "data"],
            },
        }
