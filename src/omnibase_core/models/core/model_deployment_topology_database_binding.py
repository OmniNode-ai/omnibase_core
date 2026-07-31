# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Secret-free consumer binding for a deployment database."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDeploymentTopologyDatabaseBinding"]

_REFERENCE_PATTERN = r"^[a-z_][a-z0-9_]*$"
_ENVIRONMENT_VARIABLE_PATTERN = r"^[A-Z][A-Z0-9_]*$"


class ModelDeploymentTopologyDatabaseBinding(BaseModel):
    """Map a consumer to a LOGIN principal and DSN environment-variable name."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    database_ref: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_REFERENCE_PATTERN,
        description="Logical database reference, never a physical DSN.",
    )
    principal: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_REFERENCE_PATTERN,
        description="LOGIN workload-principal reference.",
    )
    dsn_env: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=_ENVIRONMENT_VARIABLE_PATTERN,
        description="Environment-variable name holding the DSN; never the DSN value.",
    )
