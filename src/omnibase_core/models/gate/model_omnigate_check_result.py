# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate check result model."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelOmniGateCheckResult(BaseModel):
    """Result of one OmniGate check captured in a receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    command: str
    status: EnumReceiptStatus
    duration_ms: int = Field(ge=0)
    stdout_preview: str | None = Field(default=None, max_length=4096)
    stdout_hash: str | None = None

    @field_validator("stdout_hash")
    @classmethod
    def _validate_stdout_hash(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.match(value):
            msg = f"stdout_hash must match sha256:<64 hex chars>, got: {value}"
            raise ValueError(msg)
        return value


__all__ = ["ModelOmniGateCheckResult"]
