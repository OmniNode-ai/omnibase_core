# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed metadata migrations measured from the ONEX corpus (OMN-21373)."""

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_agent_skill_codec import (
    parse_skill_md,
    read_skill_md,
)
from omnibase_core.models.skill.model_agent_skill import ModelAgentSkill
from omnibase_core.models.skill.model_agent_skill_onex_keys import (
    DECLARED_ONEX_KEY_TYPES,
    decode_onex_value,
    encode_onex_value,
)
from tests.fixtures.agent_skill_tree import agent_skill_fixture_root

FIXTURES = agent_skill_fixture_root() / "migration"


@pytest.mark.unit
@pytest.mark.parametrize("key", sorted(DECLARED_ONEX_KEY_TYPES))
def test_migration_preserves_value_and_type(key: str) -> None:
    before = read_skill_md((FIXTURES / key / "SKILL.md").read_text()).get(key)
    after = read_skill_md((FIXTURES / key / "converted" / "SKILL.md").read_text()).get(
        key
    )
    assert before == after
    assert type(before) is type(after)
    assert decode_onex_value(key, encode_onex_value(key, before)) == before


@pytest.mark.unit
def test_string_that_looks_like_list_stays_string() -> None:
    encoded = encode_onex_value("mode", "[]")
    assert encoded == '"[]"'
    source = read_skill_md("---\nmetadata:\n  onex.mode: '\"[]\"'\n---\n")
    assert source.get("mode") == "[]"
    assert type(source.get("mode")) is str
    skill = parse_skill_md(
        "---\nname: skill\ndescription: A skill\nmetadata:\n  onex.mode: '\"[]\"'\n---\n",
        "skill",
    )
    assert skill.onex_value("mode") == "[]"
    assert skill.onex_value("missing") is None


@pytest.mark.unit
def test_undeclared_key_refused() -> None:
    with pytest.raises(ModelOnexError, match="reserved-metadata-prefix"):
        decode_onex_value("unknown", '"value"')


@pytest.mark.unit
@pytest.mark.parametrize(
    ("key", "text"),
    [
        ("mode", "[]"),
        ("debug", "1"),
        ("tags", "[1]"),
        ("inputs", '["entry"]'),
        ("args", "not-json"),
    ],
)
def test_onex_type_mismatches(key: str, text: str) -> None:
    with pytest.raises(ModelOnexError, match="onex-value-type"):
        decode_onex_value(key, text)
    with pytest.raises(ValidationError, match="onex-value-type"):
        ModelAgentSkill.model_validate(
            {
                "frontmatter": {
                    "name": "skill",
                    "description": "Description",
                    "metadata": {f"onex.{key}": text},
                },
                "directory_name": "skill",
            }
        )
