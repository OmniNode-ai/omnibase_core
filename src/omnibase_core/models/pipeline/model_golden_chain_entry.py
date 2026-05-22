# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Golden chain entry model for event chain verification."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelGoldenChainEntry"]


class ModelGoldenChainEntry(BaseModel):
    """A single event in a golden (expected) chain sequence."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sequence: int
    event_type: str
    topic: str
    source_node: str
