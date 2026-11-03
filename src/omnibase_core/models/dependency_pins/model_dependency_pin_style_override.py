# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One distribution whose pin style differs from the policy default (OMN-22360)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyPinStyleOverride"]


class ModelDependencyPinStyleOverride(BaseModel):
    """A distribution and the pin style the policy wants for it.

    Attributes:
        distribution: The distribution name as the layer map declares it.
        style: ``range`` refuses an exact ``==`` pin; ``exact`` refuses anything else.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    distribution: str = Field(min_length=1)
    style: Literal["range", "exact"]
