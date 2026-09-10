# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed waiver entry for the Pydantic extra-forbid ratchet."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class ModelExtraForbidWaiver(BaseModel):
    """An expiring waiver whose ticket and pull request are checked by the validator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fqn: str = ""
    ticket: str = ""
    pr: str = ""
    expires_at: date | str | None = None
    reason: str = ""


__all__ = ["ModelExtraForbidWaiver"]
