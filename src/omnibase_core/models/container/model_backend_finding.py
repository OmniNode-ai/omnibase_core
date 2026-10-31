# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Diagnostic describing why a backend entry point was skipped."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_backend_finding_reason import EnumBackendFindingReason


class ModelBackendFinding(BaseModel):
    """Entry-point identity and the reason it could not supply a backend."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entry_point: str
    value: str
    reason: EnumBackendFindingReason
    detail: str = ""
