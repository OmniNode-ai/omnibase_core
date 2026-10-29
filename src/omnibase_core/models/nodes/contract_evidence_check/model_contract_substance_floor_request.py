# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The contract files judged against the substance floor (OMN-14409)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractSubstanceFloorRequest"]


class ModelContractSubstanceFloorRequest(BaseModel):
    """The contract files judged against the substance floor (OMN-14409)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[Path, ...]
