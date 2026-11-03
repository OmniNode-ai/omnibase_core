# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One first-party dependency a repository's manifest declares (OMN-22360)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    DependencyTable,
)

__all__ = ["ModelDependencyPinEdge"]


class ModelDependencyPinEdge(BaseModel):
    """A declared requirement on a first-party distribution.

    Attributes:
        table: The pyproject table that declares it.
        label: The table as findings name it (``extra:spi``, ``group:dev``).
        target: The required distribution, normalised.
        requirement: The requirement string as written.
        specifier: Its version specifier (empty when unconstrained).
        line: The 1-based manifest line the requirement is written on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table: DependencyTable
    label: str = Field(min_length=1)
    target: str = Field(min_length=1)
    requirement: str = Field(min_length=1)
    specifier: str = ""
    line: int = Field(ge=1)
