# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelTrajectoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    step: int
    agent: str
    action: str
    target: str
    result: str
