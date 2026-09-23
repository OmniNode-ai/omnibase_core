# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed projection of contract sections consumed by FSM drift validation."""

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelFsmBindingContractDocument(BaseModel):
    """Contract root projection; unrelated contract fields remain uninterpreted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fsm_handler_binding: object | None = None
    state_machine: object | None = None

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """Parse the contract and validate only fields consumed by this check."""
        try:
            document = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ModelOnexError(
                message=f"FSM contract YAML is invalid: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                message="FSM contract root must be a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return cls.model_validate(
            {
                "fsm_handler_binding": document.get("fsm_handler_binding"),
                "state_machine": document.get("state_machine"),
            }
        )


__all__ = ["ModelFsmBindingContractDocument"]
