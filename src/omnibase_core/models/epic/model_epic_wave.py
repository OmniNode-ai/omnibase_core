# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEpicWave — a wave of parallel ticket execution within an epic.

Migration-phase capture model. Status fields use ``str`` instead of enums
to avoid breaking existing state files during initial adoption.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEpicWave"]


class ModelEpicWave(BaseModel):
    """A wave of parallel ticket execution within an epic.

    Migration-phase capture model. The ``status`` field uses ``str`` instead
    of an enum to accommodate the 9+ distinct wave status strings observed
    in production state files.
    """

    model_config = ConfigDict(
        extra="allow", from_attributes=True, populate_by_name=True
    )

    wave_number: int = Field(..., ge=0, alias="wave")
    ticket_ids: list[str] = Field(default_factory=list, alias="tickets")
    status: str = Field(default="pending")
