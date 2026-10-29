# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed ``dod_verify`` overlay for parent and factory task tickets."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator


class ModelDodVerifyOverlay(BaseModel):
    """The ``dod_verify`` overlay; its values are overlay data, never module constants."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    parent_tickets: tuple[str, ...] = ()
    factory_task_tickets: tuple[str, ...] = ()

    @field_validator("parent_tickets", "factory_task_tickets")
    @classmethod
    def _validate_ticket_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(re.fullmatch(r"OMN-[0-9]+", value) is None for value in values):
            raise ValueError("overlay ticket ids must match ^OMN-[0-9]+$")
        return values
