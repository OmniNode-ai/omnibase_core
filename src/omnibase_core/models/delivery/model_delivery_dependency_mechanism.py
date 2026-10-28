# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery dependency mechanism facts."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelDeliveryDependencyMechanism"]


class ModelDeliveryDependencyMechanism(BaseModel):
    """Immutable delivery dependency mechanism data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mechanism_name: str
    pattern: str
    ruling: str = Field(min_length=1)

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(
                f"pattern is not a valid regular expression: {exc}"
            ) from exc
        return value
