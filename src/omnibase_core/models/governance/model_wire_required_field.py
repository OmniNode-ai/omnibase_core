# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire required field model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_wire_field_type import EnumWireFieldType
from omnibase_core.models.governance.model_wire_field_constraints import (
    ModelWireFieldConstraints,
)


class ModelWireRequiredField(BaseModel):
    """A required field in a wire schema contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Canonical field name")
    type: EnumWireFieldType = Field(..., description="Field type")
    description: str = Field(default="", description="Field description")
    constraints: ModelWireFieldConstraints | None = Field(
        default=None, description="Optional field constraints"
    )
