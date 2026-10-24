# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claude Code skill extensions for OMN-21373.

Source: https://code.claude.com/docs/en/skills, read 2026-10-24.
"""

import json
import math
from typing import cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationInfo,
    field_validator,
)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.skill.model_agent_skill_frontmatter import contains_delimiter

CLAUDE_CODE_EXTENSIONS_SOURCE_TITLE = (
    "Claude Code documentation, Extend Claude with skills, frontmatter reference"
)
CLAUDE_CODE_EXTENSIONS_READ_DATE = "2026-10-24"
CLAUDE_CODE_EXTENSION_KEYS: tuple[str, ...] = (
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
)
# A space-separated string or a list of strings, as the source documents.
StringOrStringList = str | list[str]

_BOOL_KEYS = {"disable-model-invocation", "user-invocable", "background"}
_LIST_KEYS = {"arguments", "disallowed-tools", "paths"}


def _valid_hooks(value: object) -> bool:
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(k, str) and _valid_hooks(v) for k, v in value.items()
        )
    if isinstance(value, list):
        return bool(value) and all(_valid_hooks(v) for v in value)
    return type(value) in (str, bool, int) or (
        isinstance(value, float) and not math.isnan(value)
    )


def extension_value_error(key: str, value: object) -> str | None:
    """Return the rule message for an invalid extension value."""
    valid = False
    if key in _BOOL_KEYS:
        valid = type(value) is bool
    elif key in _LIST_KEYS:
        valid = isinstance(value, str) or (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(v, str) for v in value)
        )
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except ValueError:
                decoded = None
            if isinstance(decoded, list):
                valid = False
    elif key == "hooks":
        valid = isinstance(value, dict) and _valid_hooks(value)
    elif key in CLAUDE_CODE_EXTENSION_KEYS:
        valid = isinstance(value, str)
    if not valid:
        return f"extension-value-type: {key}"
    if contains_delimiter(value):
        return f"frontmatter-delimiter-in-value: {key}"
    return None


def encode_extension_value(key: str, value: JsonValue) -> str:
    """Encode a declared extension for string-valued metadata."""
    error = extension_value_error(key, value)
    if error is not None:
        raise ModelOnexError(error, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
    return (
        value
        if isinstance(value, str)
        else json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    )


def decode_extension_value_result(key: str, text: str) -> tuple[JsonValue, str | None]:
    """Decode metadata and return a rule message for invalid values."""
    value: object = text
    if key in _BOOL_KEYS or key == "hooks":
        try:
            value = json.loads(text)
        except ValueError:
            return None, f"extension-value-type: {key}"
    elif key in _LIST_KEYS:
        try:
            decoded = json.loads(text)
        except ValueError:
            decoded = None
        if isinstance(decoded, list):
            value = decoded
    return cast("JsonValue", value), extension_value_error(key, value)


def decode_extension_value(key: str, text: str) -> JsonValue:
    """Decode metadata according to the extension's declared type."""
    value, error = decode_extension_value_result(key, text)
    if error is not None:
        raise ModelOnexError(error, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
    return value


class ModelClaudeCodeSkillExtensions(BaseModel):
    """Extensions documented at https://code.claude.com/docs/en/skills on 2026-10-24."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    when_to_use: str | None = None
    argument_hint: str | None = Field(default=None, alias="argument-hint")
    arguments: StringOrStringList | None = None
    disable_model_invocation: bool | None = Field(
        default=None, alias="disable-model-invocation"
    )
    user_invocable: bool | None = Field(default=None, alias="user-invocable")
    disallowed_tools: StringOrStringList | None = Field(
        default=None, alias="disallowed-tools"
    )
    model: str | None = None
    effort: str | None = None
    context: str | None = None
    agent: str | None = None
    background: bool | None = None
    hooks: dict[str, JsonValue] | None = None
    paths: StringOrStringList | None = None
    shell: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_extension(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            return None
        assert info.field_name is not None
        field = cls.model_fields[info.field_name]
        error = extension_value_error(field.alias or info.field_name, value)
        if error is not None:
            raise ValueError(error)
        return value

    def to_frontmatter(self) -> dict[str, JsonValue]:
        """Return non-None extensions in their documented order."""
        values = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        return {key: values[key] for key in CLAUDE_CODE_EXTENSION_KEYS if key in values}
