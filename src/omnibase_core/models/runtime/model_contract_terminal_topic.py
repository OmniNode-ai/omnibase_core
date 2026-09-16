# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One contract-declared terminal topic, paired with the outcome it declares.

Resolved from a contract by
``omnibase_core.runtime.contract_terminal_topics.resolve_terminal_topics``,
which documents why the outcome travels with the topic (OMN-18445).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_terminal_outcome import EnumTerminalOutcome

__all__ = ["ModelContractTerminalTopic"]


class ModelContractTerminalTopic(BaseModel):
    """One terminal topic, paired with the outcome its contract declares for it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(..., min_length=1)
    outcome: EnumTerminalOutcome = Field(...)
