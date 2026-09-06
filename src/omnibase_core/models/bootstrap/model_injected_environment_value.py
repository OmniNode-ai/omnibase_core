# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One immutable value captured by typed environment bootstrap."""

from pydantic import BaseModel, ConfigDict


class ModelInjectedEnvironmentValue(BaseModel):
    """One immutable environment value captured at the bootstrap boundary."""

    name: str
    value: str

    model_config = ConfigDict(extra="forbid", frozen=True)
