# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One observed JUnit testcase, including tests which ran."""

from pydantic import BaseModel, ConfigDict


class ModelSkipCountRecord(BaseModel):
    """A stable test identity and its observed skip state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    identity: str
    skipped: bool
