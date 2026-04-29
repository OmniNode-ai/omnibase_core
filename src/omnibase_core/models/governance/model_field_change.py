# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Field change model for contract drift detection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelFieldChange(BaseModel):
    """A single field-level change between current and pinned contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    path: str = Field(description="Dot-separated path to the changed field.")
    change_type: str = Field(description="One of: 'added', 'removed', 'modified'.")
    old_value: str | int | float | bool | list[object] | dict[str, object] | None = (
        Field(default=None, description="Value in the pinned contract.")
    )
    new_value: str | int | float | bool | list[object] | dict[str, object] | None = (
        Field(default=None, description="Value in the current contract.")
    )
    is_breaking: bool = Field(
        description="True when this change is likely to break existing consumers."
    )
