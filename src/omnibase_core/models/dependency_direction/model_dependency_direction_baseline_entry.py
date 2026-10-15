# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One recorded, pre-existing dependency-direction violation (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_dependency_channel import EnumDependencyChannel

__all__ = ["ModelDependencyDirectionBaselineEntry"]


class ModelDependencyDirectionBaselineEntry(BaseModel):
    """A violation that existed when the gate was introduced.

    The baseline only shrinks: an entry matches by ``(path, channel, target)``
    and carries the ticket that removes it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(min_length=1)
    channel: EnumDependencyChannel
    target: str = Field(min_length=1)
    ticket: str = Field(pattern=r"^OMN-\d+$")

    def key(self) -> tuple[str, str, str]:
        """The identity a finding is matched on."""
        return (self.path, self.channel.value, self.target)
