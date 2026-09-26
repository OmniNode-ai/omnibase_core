# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI-specific override for a contract-declared LLM routing policy."""

from pydantic import BaseModel, ConfigDict, Field


class ModelCiOverridePolicy(BaseModel):
    """CI-mode override selecting a deterministic primary model key."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary: str = Field(..., description="model_id key to use in CI mode.")


__all__ = ["ModelCiOverridePolicy"]
