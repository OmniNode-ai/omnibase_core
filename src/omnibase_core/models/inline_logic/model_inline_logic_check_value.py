# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A contract ``check_value`` as the inline-logic check reads it (OMN-21534)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelInlineLogicCheckValue"]


class ModelInlineLogicCheckValue(BaseModel):
    """One ``check_value`` of a ``dod_evidence`` item: the item id, check type and command text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    evidence_ref: str
    check_type: str | None = None
    check_value: str
