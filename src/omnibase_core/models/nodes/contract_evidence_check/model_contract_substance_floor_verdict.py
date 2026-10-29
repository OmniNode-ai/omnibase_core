# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The substance floor verdict of one contract (OMN-14409)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractSubstanceFloorVerdict"]


class ModelContractSubstanceFloorVerdict(BaseModel):
    """The substance floor verdict of one contract (OMN-14409)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path
    ticket_id: str
    passed: bool
    failure_message: str = ""
