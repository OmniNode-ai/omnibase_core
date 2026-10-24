# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tolerant skill source view for migrations (OMN-21373)."""

from pydantic import BaseModel, ConfigDict, JsonValue

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.skill.model_agent_skill_onex_keys import (
    METADATA_PREFIX_CLAUDE_CODE,
    METADATA_PREFIX_ONEX,
    decode_onex_value,
)
from omnibase_core.models.skill.model_claude_code_skill_extensions import (
    decode_extension_value,
)


class ModelAgentSkillSource(BaseModel):
    """A source document without conformance requirements."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    has_frontmatter: bool
    frontmatter: dict[str, JsonValue]
    body: str

    def get(self, key: str) -> JsonValue | None:
        """Read top-level, typed migrated, then ordinary metadata values."""
        if key in self.frontmatter:
            return self.frontmatter[key]
        metadata = self.frontmatter.get("metadata")
        if not isinstance(metadata, dict):
            return None
        for prefix, decode in (
            (METADATA_PREFIX_ONEX, decode_onex_value),
            (METADATA_PREFIX_CLAUDE_CODE, decode_extension_value),
        ):
            if prefix + key in metadata:
                text = metadata[prefix + key]
                if not isinstance(text, str):
                    raise ModelOnexError(
                        f"{'onex' if prefix == METADATA_PREFIX_ONEX else 'extension'}-value-type: {key}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
                return decode(key, text)
        return metadata.get(key)
