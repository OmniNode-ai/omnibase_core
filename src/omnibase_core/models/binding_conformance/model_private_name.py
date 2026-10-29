# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One private name taken from the deployment's overlays."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_private_name_kind import (
    EnumPrivateNameKind,
)


class ModelPrivateName(BaseModel):
    """A name that must appear in no shipped file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumPrivateNameKind
    value: str = Field(min_length=1)
