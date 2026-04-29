# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DB Boundary Exceptions Registry Model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.governance.model_db_boundary_exception import (
    ModelDbBoundaryException,
)


class ModelDbBoundaryExceptionsRegistry(BaseModel):
    """Registry of all DB boundary exceptions.

    Loaded from registry/db-boundary-exceptions.yaml and validated
    by the check-db-boundary CLI tool.
    """

    model_config = ConfigDict(frozen=True)

    exceptions: list[ModelDbBoundaryException] = Field(
        default_factory=list,
        description="List of registered DB boundary exceptions",
    )
