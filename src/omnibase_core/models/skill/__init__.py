# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Skill execution result models.

Provides ``ModelSkillResult``, the base contract for skill result files
written to ``~/.claude/skill-results/``.
"""

from __future__ import annotations

from omnibase_core.models.skill.model_skill_result import ModelSkillResult, SkillResult

__all__ = [
    "ModelSkillResult",
    "SkillResult",
]
