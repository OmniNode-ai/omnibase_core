# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One dod_evidence check to classify (OMN-17427)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractComplianceCheckRequest"]


class ModelContractComplianceCheckRequest(BaseModel):
    """One dod_evidence check to classify (OMN-17427)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    check_value: str
    check_type: str = "command"
    changed_paths: tuple[str, ...] | None = None
