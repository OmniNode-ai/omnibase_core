# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent Skills frontmatter and shared conformance rules (OMN-21373)."""

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator

SPEC_FIELD_KEYS = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
)
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500


def normalized_name(value: str) -> str:
    """Apply the reference name normalization."""
    return unicodedata.normalize("NFKC", value.strip())


def name_rule_ids(value: object) -> list[str]:
    """Reference name rules, in reference validation order."""
    if not isinstance(value, str) or not value.strip():
        return ["name-missing"]
    value = normalized_name(value)
    rules: list[str] = []
    if len(value) > MAX_NAME_LENGTH:
        rules.append("name-length")
    if value != value.lower():
        rules.append("name-case")
    if value.startswith("-") or value.endswith("-"):
        rules.append("name-hyphen-edge")
    if "--" in value:
        rules.append("name-double-hyphen")
    if not all(char.isalnum() or char == "-" for char in value):
        rules.append("name-chars")
    return rules


def name_house_rule_ids(value: object) -> list[str]:
    """Require an ASCII name after reference normalization."""
    if (
        isinstance(value, str)
        and value.strip()
        and not re.fullmatch(r"[a-z0-9-]+", normalized_name(value))
    ):
        return ["house-ascii-name"]
    return []


def description_rule_ids(value: object) -> list[str]:
    """Reference description rules."""
    if not isinstance(value, str) or not value.strip():
        return ["description-missing"]
    return ["description-length"] if len(value) > MAX_DESCRIPTION_LENGTH else []


def compatibility_rule_ids(value: object) -> list[str]:
    """Reference compatibility rules (blank values are accepted)."""
    if not isinstance(value, str):
        return ["compatibility-type"]
    return ["compatibility-length"] if len(value) > MAX_COMPATIBILITY_LENGTH else []


def compatibility_spec_rule_ids(value: object) -> list[str]:
    """The specification also requires nonblank compatibility."""
    return (
        ["compatibility-empty"] if isinstance(value, str) and not value.strip() else []
    )


def contains_delimiter(value: object) -> bool:
    """Find the frontmatter delimiter in keys or values at any depth."""
    if isinstance(value, str):
        return "---" in value
    if isinstance(value, dict):
        return any(
            contains_delimiter(k) or contains_delimiter(v) for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_delimiter(v) for v in value)
    return False


def rule_message(rules: list[str], value: object) -> str | None:
    """Describe the first rule in a rule function's result."""
    return f"{rules[0]}: {value!r}" if rules else None


class ModelAgentSkillFrontmatter(BaseModel):
    """Strict specification fields for an Agent Skill."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    allowed_tools: str | None = Field(default=None, alias="allowed-tools")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        error = rule_message(name_rule_ids(value) or name_house_rule_ids(value), value)
        if error is not None:
            raise ValueError(error)
        assert isinstance(value, str)
        return normalized_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: object) -> object:
        error = rule_message(description_rule_ids(value), value)
        if error is not None:
            raise ValueError(error)
        return value

    @field_validator("compatibility", mode="before")
    @classmethod
    def validate_compatibility(cls, value: object) -> object:
        if value is not None:
            error = rule_message(
                compatibility_rule_ids(value) or compatibility_spec_rule_ids(value),
                value,
            )
            if error is not None:
                raise ValueError(error)
        return value

    @field_validator("*", mode="before")
    @classmethod
    def validate_delimiters(cls, value: object) -> object:
        if contains_delimiter(value):
            raise ValueError("frontmatter-delimiter-in-value: delimiter in frontmatter")
        return value
