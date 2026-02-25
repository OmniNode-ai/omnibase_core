# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Individual check result model for contract.verify.replay.

.. versionadded:: 0.20.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelVerifyCheckResult"]

CheckStatus = Literal["pass", "fail", "skip"]


class ModelVerifyCheckResult(BaseModel):
    """Result of a single static verification check.

    Attributes:
        check_name: Machine-readable name of the check (e.g. ``schema_validation``).
        status: Outcome of the check: ``pass``, ``fail``, or ``skip``.
        message: Human-readable description of the result. Present on
            ``fail`` and ``skip``; optional on ``pass``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: check names are machine-readable identifiers, not UUIDs
    check_name: str = Field(..., min_length=1, description="Name of the check.")
    status: CheckStatus = Field(..., description="Check outcome.")
    message: str | None = Field(
        default=None,
        description="Human-readable detail (required on fail/skip).",
    )
