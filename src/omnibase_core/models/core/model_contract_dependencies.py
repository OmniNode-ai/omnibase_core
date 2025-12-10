#!/usr/bin/env python3
"""
Contract Dependencies Model.

Model representing the dependencies section of a contract.
"""

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_contract_dependency import ModelContractDependency


class ModelContractDependencies(BaseModel):
    """Model representing the dependencies section of a contract."""

    model_config = ConfigDict(extra="ignore")

    dependencies: list[ModelContractDependency] = Field(
        default_factory=list,
        description="List of contract dependencies",
    )

    def __iter__(self) -> Iterator[ModelContractDependency]:  # type: ignore[override]
        """Allow iteration over dependencies."""
        return iter(self.dependencies)

    def __len__(self) -> int:
        """Return number of dependencies."""
        return len(self.dependencies)
