# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, field_validator

from omnibase_core.enums.enum_hook_bit import EnumHookBit


class ModelHookActivation(BaseModel):
    """Declares a Claude Code hook that a package requires active."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook_bit: EnumHookBit
    enabled_by_default: bool = True
    description: str = ""

    @field_validator("hook_bit", mode="before")
    @classmethod
    def coerce_hook_bit(cls, v: object) -> EnumHookBit:
        if isinstance(v, EnumHookBit):
            return v
        if isinstance(v, str):
            return EnumHookBit[v]
        if isinstance(v, int):
            return EnumHookBit(v)
        raise ValueError(f"Cannot coerce {v!r} to EnumHookBit")
