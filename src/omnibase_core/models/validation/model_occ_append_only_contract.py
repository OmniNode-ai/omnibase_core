# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract projection required by OCC append-only validation."""

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelOccAppendOnlyContract(BaseModel):
    """The DoD evidence entries inspected by the append-only gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dod_evidence: list[dict[str, object]] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """Parse a ticket contract and type-check its append-only evidence rows."""
        try:
            document = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ModelOnexError(
                message=f"OCC contract YAML is invalid: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                message="OCC contract root must be a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return cls.model_validate({"dod_evidence": document.get("dod_evidence", [])})


__all__ = ["ModelOccAppendOnlyContract"]
