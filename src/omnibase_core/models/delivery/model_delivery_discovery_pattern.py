# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery discovery pattern facts."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["ModelDeliveryDiscoveryPattern"]


class ModelDeliveryDiscoveryPattern(BaseModel):
    """Immutable delivery discovery pattern data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    consumer_kind: str
    file_pattern: str
    reference_pattern: str

    @field_validator("reference_pattern")
    @classmethod
    def _has_ref_group(cls, value: str) -> str:
        try:
            compiled = re.compile(value)
        except re.error as exc:
            raise ValueError(
                f"reference_pattern is not a valid regular expression: {exc}"
            ) from exc
        if "ref" not in compiled.groupindex:
            raise ValueError("reference_pattern must contain named group ref")
        return value
