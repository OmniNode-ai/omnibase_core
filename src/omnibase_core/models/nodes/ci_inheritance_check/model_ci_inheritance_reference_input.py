# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the ci-inheritance handler: the workflow facts plus the rule data (OMN-21518)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_rules import (
    ModelCiInheritanceRules,
)

__all__ = ["ModelCiInheritanceReferenceInput"]


class ModelCiInheritanceReferenceInput(BaseModel):
    """The handler reads no constant: the rules arrive with the request."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    check: ModelCiInheritanceCheckInput
    rules: ModelCiInheritanceRules
