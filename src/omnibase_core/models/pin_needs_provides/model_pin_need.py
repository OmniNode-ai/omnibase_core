# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One thing a verifier needs from its environment, or a caller provides (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPinNeed(BaseModel):
    """A kind of environment input and its name; both are free data, compared exactly."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(min_length=1, description="Kind of input, such as a secret")
    name: str = Field(min_length=1, description="Name of the input within its kind")

    def label(self) -> str:
        """The need as one diagnostic word."""
        return f"{self.kind}:{self.name}"
