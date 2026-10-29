# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The contract files whose check values are linted (OMN-17427)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractCheckValuesLintRequest"]


class ModelContractCheckValuesLintRequest(BaseModel):
    """The contract files whose check values are linted (OMN-17427)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[Path, ...]
