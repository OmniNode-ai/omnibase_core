# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A predeclared safety-failure condition of a manifest (OMN-22001)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_retrospective_reason_code import (
    EnumRetrospectiveReasonCode,
)

_SAFETY_CODES = frozenset(
    {
        EnumRetrospectiveReasonCode.UNAUTHORIZED_EFFECT,
        EnumRetrospectiveReasonCode.FALSE_COMPLETION,
        EnumRetrospectiveReasonCode.DUPLICATE_EFFECT,
    }
)


class ModelManifestSafetyCondition(BaseModel):
    """Valid evidence that proves this condition makes the experiment FAIL.

    Attributes:
        code: The safety reason code the condition maps to.
        condition: The condition, in words.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: EnumRetrospectiveReasonCode
    condition: str = Field(min_length=1)

    @field_validator("code")
    @classmethod
    def _code_is_a_safety_code(
        cls, value: EnumRetrospectiveReasonCode
    ) -> EnumRetrospectiveReasonCode:
        if value not in _SAFETY_CODES:
            raise ValueError(f"{value.value} is not a safety reason code")
        return value
