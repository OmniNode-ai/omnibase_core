# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Centralized ModelObjectData implementation."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelObjectData(BaseModel):
    """Generic objectdata model for common use."""

    model_config = ConfigDict(extra="forbid")

    data: SerializedDict | None = Field(
        default_factory=dict,
        description="Arbitrary object data for flexible field content",
    )
