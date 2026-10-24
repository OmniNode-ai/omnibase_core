# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent Skills rendering profiles (OMN-21373)."""

from enum import StrEnum

__all__ = ["EnumAgentSkillRenderProfile"]


class EnumAgentSkillRenderProfile(StrEnum):
    """Frontmatter vocabulary emitted by the skill renderer."""

    AGENT_SKILLS = "agent_skills"
    """Specification fields with extensions folded into metadata."""

    CLAUDE_CODE = "claude_code"
    """Specification fields and declared Claude Code extensions."""
