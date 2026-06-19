# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Backend reference violation model for backend-secret-discipline checks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelBackendRefViolation(BaseModel):
    """A single backend-ref or mutual-exclusion finding."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: str
    message: str


__all__ = ["ModelBackendRefViolation"]
