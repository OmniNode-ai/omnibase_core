"""
Model for contract dependency representation in ONEX Phase 0 pattern.

This model supports dependency injection configuration in contracts.

Author: ONEX Framework Team
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelContractDependency(BaseModel):
    """Model representing a single dependency in a contract."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Dependency service name")
    type: str = Field(..., description="Dependency type (utility, protocol, service)")
    class_name: Optional[str] = Field(
        None, alias="class", description="Class name for the dependency"
    )
    module: Optional[str] = Field(None, description="Module path for the dependency")
    description: Optional[str] = Field(None, description="Dependency description")


class ModelContractDependencies(BaseModel):
    """Model representing the dependencies section of a contract."""

    model_config = ConfigDict(extra="ignore")

    dependencies: List[ModelContractDependency] = Field(
        default_factory=list, description="List of contract dependencies"
    )

    def __iter__(self):
        """Allow iteration over dependencies."""
        return iter(self.dependencies)

    def __len__(self):
        """Return number of dependencies."""
        return len(self.dependencies)
