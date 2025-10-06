"""
Model for contract dependency representation in ONEX Phase 0 pattern.

This model supports dependency injection configuration in contracts.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractDependency(BaseModel):
    """Model representing a single dependency in a contract."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Dependency service name")
    type: str = Field(..., description="Dependency type (utility, protocol, service)")
    class_name: str | None = Field(
        None,
        alias="class",
        description="Class name for the dependency",
    )
    module: str | None = Field(None, description="Module path for the dependency")
    description: str | None = Field(None, description="Dependency description")
