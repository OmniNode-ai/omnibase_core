# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire optional field model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_wire_field_type import EnumWireFieldType


class ModelWireOptionalField(BaseModel):
    """An optional field in a wire schema contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Canonical field name")
    type: EnumWireFieldType = Field(..., description="Field type")
    nullable: bool = Field(default=True, description="Whether the field can be null")
    description: str = Field(default="", description="Field description")
