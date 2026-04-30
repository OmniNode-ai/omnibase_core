# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern


class ModelPrmMatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pattern: EnumPrmPattern
    affected_agents: tuple[str, ...]
    affected_targets: tuple[str, ...]
    step_range: tuple[int, int]
    severity_level: Literal[1, 2, 3]
    dedup_key: str
