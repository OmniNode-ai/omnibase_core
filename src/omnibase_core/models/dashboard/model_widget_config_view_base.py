# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Base for the configs of the seven row-driven view kinds (OMN-21997).

Each concrete config narrows ``config_kind`` to a literal (the union
discriminator) and names its ``EnumWidgetType`` in ``_WIDGET_TYPE``. The base
enforces that ``widget_type`` and ``config_kind`` agree with it, the same rule
the five older configs each repeat by hand.
"""

from __future__ import annotations

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_widget_type import EnumWidgetType

__all__ = ["ModelWidgetConfigViewBase"]


class ModelWidgetConfigViewBase(BaseModel):
    """Common shape of a view-kind widget config."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    _WIDGET_TYPE: ClassVar[EnumWidgetType]

    config_kind: str = Field(..., description="Discriminator for widget config union")
    widget_type: EnumWidgetType = Field(..., description="Widget type enum value")

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type and config_kind name this config's kind.

        Raises:
            ValueError: If widget_type or config_kind is not this config's kind.
        """
        expected = type(self)._WIDGET_TYPE
        if self.widget_type is not expected:
            raise ValueError(
                f"widget_type must be {expected.name} for {expected.value} config, "
                f"got {self.widget_type.value}"
            )
        if self.config_kind != expected.value:
            raise ValueError(
                f"config_kind must be '{expected.value}' for {expected.name} widget, "
                f"got '{self.config_kind}'"
            )
        return self
