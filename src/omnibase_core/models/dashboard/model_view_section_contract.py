# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract of one section of a view (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_view_field_map import ModelViewFieldMap
from omnibase_core.models.dashboard.model_view_slug import ViewSlug

__all__ = ["ModelViewSectionContract"]


class ModelViewSectionContract(BaseModel):
    """What one section of a view shows, of which kind, from which rows."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    section_id: ViewSlug = Field(
        ..., description="Slug of the section, unique within its view"
    )
    kind: EnumWidgetType = Field(..., description="View kind the section renders as")
    title: str = Field(..., min_length=1, description="Section title")
    field_map: ModelViewFieldMap = Field(
        ..., description="Row selection and field bindings"
    )
    supported_empty_state_reasons: tuple[EnumEmptyStateReason, ...] = Field(
        default=(), description="Typed empty-state reasons this section can surface"
    )

    @field_validator("kind")
    @classmethod
    def validate_kind_is_a_view_kind(cls, value: EnumWidgetType) -> EnumWidgetType:
        """Refuse a widget kind that is not one of the eight view kinds.

        Raises:
            ValueError: If ``value`` is not a view kind.
        """
        if not value.is_view_kind:
            raise ValueError(f"'{value.value}' is not a view kind")
        return value
