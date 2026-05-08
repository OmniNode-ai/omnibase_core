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
            try:
                return EnumHookBit[v]
            except KeyError as exc:
                raise ValueError(f"Cannot coerce {v!r} to EnumHookBit") from exc
        if isinstance(v, int):
            try:
                return EnumHookBit(v)
            except ValueError as exc:
                raise ValueError(f"Cannot coerce {v!r} to EnumHookBit") from exc
        raise ValueError(f"Cannot coerce {v!r} to EnumHookBit")
