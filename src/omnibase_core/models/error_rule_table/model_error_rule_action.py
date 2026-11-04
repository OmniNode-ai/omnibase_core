# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Action reference; the validator checks the terminal and executable branches."""

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRuleAction(BaseModel):
    """A closed registry reference or an explicitly reasoned terminal action."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(min_length=1)
    contract: str | None = None
    digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: str | None = Field(default=None, min_length=1)
