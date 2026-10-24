# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Independent Agent Skills conformance verdicts (OMN-21373)."""

from pydantic import BaseModel, ConfigDict, field_validator

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.models.skill.model_agent_skill import ModelAgentSkill


class ModelAgentSkillVerdict(BaseModel):
    """Reference, specification and house rules for a source document."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    profile: EnumAgentSkillRenderProfile
    reference_rules: tuple[str, ...]
    spec_rules: tuple[str, ...]
    house_rules: tuple[str, ...]
    diagnostics: tuple[str, ...]
    skill: ModelAgentSkill | None = None

    @field_validator("reference_rules", "spec_rules", "house_rules")
    @classmethod
    def sorted_rules(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))

    @property
    def conformant(self) -> bool:
        """Whether all three rule sets pass."""
        return not (self.reference_rules or self.spec_rules or self.house_rules)
