# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One skipped testcase observed at the artifact boundary."""

from pydantic import BaseModel, ConfigDict, Field


class ModelIntegrationSkipRecord(BaseModel):
    """Test label, trimmed reason, and original XML location."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    test_name: str
    reason: str
    path: str
    line: int = Field(ge=1)
