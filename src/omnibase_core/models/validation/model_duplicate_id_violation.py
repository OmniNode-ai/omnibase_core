# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDuplicateIdViolation — a single duplicate-id (or structural) finding
reported by ValidatorDuplicateConfigIds (OMN-14401)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDuplicateIdViolation(BaseModel):
    """A single duplicate-id (or structural) violation found in a registry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registry_path: str
    group_label: str | None
    detail: str
