# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Non-executable terminal result consumed by an error-rule matcher."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRuleNoneResult(BaseModel):
    """The terminal type cannot carry a claim, dispatch, ask or triage request."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rule_name: str = Field(min_length=1)
    message: str = Field(min_length=1)
    claims: tuple[()] = ()
    dispatches: tuple[()] = ()
    asks: tuple[()] = ()
    triages: tuple[()] = ()
    executable: Literal[False] = False
