# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One offending fragment of a contract check value (OMN-17427)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractCheckValuesFinding"]


class ModelContractCheckValuesFinding(BaseModel):
    """One offending fragment of a contract check value (OMN-17427)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    pattern: str
    fragment: str
