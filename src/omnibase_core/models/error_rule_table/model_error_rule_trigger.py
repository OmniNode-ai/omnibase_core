# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Named trigger data for an error-rule row."""

from pydantic import BaseModel, ConfigDict


class ModelErrorRuleTrigger(BaseModel):
    """State triggers name a registered state check; other triggers match keys."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str
    state_check: str | None = None
