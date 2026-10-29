# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Whether one check is inert and why it is non-hermetic, if it is (OMN-17427)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelContractComplianceCheckVerdict"]


class ModelContractComplianceCheckVerdict(BaseModel):
    """Whether one check is inert and why it is non-hermetic, if it is (OMN-17427)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    inert: bool
    non_hermetic_reason: str | None = None
