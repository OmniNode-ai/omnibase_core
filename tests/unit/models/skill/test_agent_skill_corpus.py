# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Optional externally supplied Agent Skills corpus agreement (OMN-21373)."""

import json
from pathlib import Path

import pytest

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_agent_skill_codec import (
    parse_skill_md,
    read_skill_md,
)


@pytest.mark.unit
def test_external_corpus() -> None:
    manifest = (
        Path(__file__).resolve().parents[4] / ".onex_state/agent_skill_corpus.json"
    )
    if not manifest.exists():
        pytest.skip("repository-local .onex_state/agent_skill_corpus.json is absent")
    entries = json.loads(manifest.read_text())
    disagreements = []
    checked = 0
    for entry in entries:
        assert entry["expected"] in {"pass", "fail"}
        for path in sorted(Path(entry["root"]).glob("*/SKILL.md")):
            checked += 1
            text = path.read_text()
            try:
                read_skill_md(text)
            except ModelOnexError as exc:
                disagreements.append(f"{path}: tolerant read failed: {exc}")
            try:
                parse_skill_md(
                    text, path.parent.name, EnumAgentSkillRenderProfile.CLAUDE_CODE
                )
            except ModelOnexError as exc:
                if entry["expected"] == "pass":
                    disagreements.append(f"{path}: expected pass, refused: {exc}")
            else:
                if entry["expected"] == "fail":
                    disagreements.append(f"{path}: expected fail, parsed successfully")
    assert checked, "the corpus manifest names no SKILL.md"
    assert not disagreements, "Corpus disagreements:\n" + "\n".join(disagreements)
