# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical Agent Skills bytes and convergence (OMN-21373)."""

from pathlib import Path

import pytest

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.handlers.handler_agent_skill_codec import (
    parse_skill_md,
    render_skill_md,
)
from tests.fixtures.agent_skill_tree import agent_skill_fixture_root

FIXTURES = agent_skill_fixture_root() / "canonical"


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    sorted(FIXTURES.glob("*/*/SKILL.md")),
    ids=lambda p: str(p.relative_to(FIXTURES)),
)
def test_canonical_bytes(path: Path) -> None:
    profile = EnumAgentSkillRenderProfile(path.parents[1].name)
    data = path.read_bytes()
    skill = parse_skill_md(data.decode(), path.parent.name, profile)
    assert render_skill_md(skill, profile).encode() == data


@pytest.mark.unit
@pytest.mark.parametrize("profile", list(EnumAgentSkillRenderProfile))
def test_noncanonical_converges(profile: EnumAgentSkillRenderProfile) -> None:
    text = "---\r\nname: skill\r\ndescription: A skill\r\nmetadata:\r\n  z: last\r\n  a: first\r\n---\r\n\r\nBody.\r\n\r\n\r\n"
    first = render_skill_md(parse_skill_md(text, "skill", profile), profile)
    assert first != text
    assert first.index('"a":') < first.index('"z":')
    assert render_skill_md(parse_skill_md(first, "skill", profile), profile) == first
