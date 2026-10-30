# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed messages of each lineage finding kind."""

from pydantic import BaseModel, ConfigDict


class ModelDevTagLineageRuleParameters(BaseModel):
    """Presentation lives in the contract rule row."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    message: str
    remediation: str
