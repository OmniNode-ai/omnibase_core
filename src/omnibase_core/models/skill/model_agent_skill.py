# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical typed Agent Skill representation (OMN-21373)."""

import unicodedata
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from omnibase_core.models.skill.model_agent_skill_frontmatter import (
    SPEC_FIELD_KEYS,
    ModelAgentSkillFrontmatter,
)
from omnibase_core.models.skill.model_agent_skill_onex_keys import (
    METADATA_PREFIX_CLAUDE_CODE,
    METADATA_PREFIX_ONEX,
    decode_onex_value,
    decode_onex_value_result,
    encode_onex_value,
)
from omnibase_core.models.skill.model_claude_code_skill_extensions import (
    CLAUDE_CODE_EXTENSION_KEYS,
    ModelClaudeCodeSkillExtensions,
    decode_extension_value_result,
)


class ModelAgentSkill(BaseModel):
    """One representation shared by parsing and direct construction."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    frontmatter: ModelAgentSkillFrontmatter
    extensions: ModelClaudeCodeSkillExtensions = Field(
        default_factory=ModelClaudeCodeSkillExtensions
    )
    body: str = ""
    directory_name: str

    @model_validator(mode="before")
    @classmethod
    def canonicalize(cls, value: object) -> object:
        if not isinstance(value, dict):
            if not hasattr(value, "frontmatter"):
                return value
            value = {
                key: getattr(value, key)
                for key in cls.model_fields
                if hasattr(value, key)
            }
        data = dict(value)
        body = data.get("body", "")
        if isinstance(body, str):
            lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
            data["body"] = "\n".join(lines) + "\n" if lines else ""
        if "frontmatter" not in data:
            return data
        front_model = ModelAgentSkillFrontmatter.model_validate(data["frontmatter"])
        front = front_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        extensions = ModelClaudeCodeSkillExtensions.model_validate(
            data.get("extensions", {})
        ).to_frontmatter()
        metadata = dict(front_model.metadata)
        for key, text in list(metadata.items()):
            if key.startswith(METADATA_PREFIX_CLAUDE_CODE):
                extension_key = key.removeprefix(METADATA_PREFIX_CLAUDE_CODE)
                if extension_key not in CLAUDE_CODE_EXTENSION_KEYS:
                    raise ValueError(f"reserved-metadata-prefix: {key}")
                if extension_key in extensions:
                    raise ValueError(f"duplicate-representation: {key}")
                extension_value, error = decode_extension_value_result(
                    extension_key, text
                )
                if error is not None:
                    raise ValueError(error)
                extensions[extension_key] = extension_value
                del metadata[key]
            elif key.startswith(METADATA_PREFIX_ONEX):
                onex_key = key.removeprefix(METADATA_PREFIX_ONEX)
                onex_value, error = decode_onex_value_result(onex_key, text)
                if error is not None:
                    raise ValueError(error)
                metadata[key] = encode_onex_value(onex_key, onex_value)
        # Check after promotion so metadata insertion order cannot hide collisions.
        for key in metadata:
            if (key in SPEC_FIELD_KEYS and key in front) or (
                key in CLAUDE_CODE_EXTENSION_KEYS and key in extensions
            ):
                raise ValueError(f"duplicate-representation: {key}")
        front["metadata"] = metadata
        data["frontmatter"] = front
        data["extensions"] = extensions
        return data

    @model_validator(mode="after")
    def validate_directory(self) -> Self:
        if unicodedata.normalize(
            "NFKC", self.frontmatter.name.strip()
        ) != unicodedata.normalize("NFKC", self.directory_name):
            raise ValueError("name-dir-mismatch: name must match directory")
        return self

    def onex_value(self, key: str) -> JsonValue | None:
        """Read a typed ONEX metadata value."""
        text = self.frontmatter.metadata.get(METADATA_PREFIX_ONEX + key)
        return None if text is None else decode_onex_value(key, text)
