# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelHealthResult(BaseModel):
    """One health verdict with the plain-words message a customer reads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    healthy: bool = Field(description="True when the check passed or was skipped")
    message: str = Field(description="Plain words, with a Fix line when unhealthy")
