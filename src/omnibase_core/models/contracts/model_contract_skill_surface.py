# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-declared Agent Skills surface (OMN-21373).

Schema for the top-level ``skill_surface:`` section of a node ``contract.yaml``.
The shim skill render node reads these keys to render a SKILL.md.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.skill.model_agent_skill_frontmatter import (
    description_rule_ids,
    name_house_rule_ids,
    name_rule_ids,
    normalized_name,
    rule_message,
)


class ModelContractSkillSurface(BaseModel):
    """Agent Skills surface declared in a contract YAML ``skill_surface:`` block.

    ``id`` is the Agent Skills skill name, and the ``cli_id`` key (attribute
    ``cli_command``) is the command name passed to ``uv run onex skill <cli_id>``,
    kept as today's id. ``description`` supplies the skill
    description when present; otherwise the renderer uses the contract description.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    id: str = Field(
        ...,
        description="Agent Skills skill name rendered in SKILL.md frontmatter.",
    )

    cli_command: str = Field(
        ...,
        alias="cli_id",
        min_length=1,
        description="Command name passed to uv run onex skill <cli_id>; read from the cli_id key.",
    )

    description: str | None = Field(
        default=None,
        description="Skill description; falls back to the contract description when absent.",
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, value: object) -> str:
        error = rule_message(name_rule_ids(value) or name_house_rule_ids(value), value)
        if error is not None:
            raise ValueError(error)
        assert isinstance(value, str)
        return normalized_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: object) -> object:
        if value is not None:
            error = rule_message(description_rule_ids(value), value)
            if error is not None:
                raise ValueError(error)
        return value
