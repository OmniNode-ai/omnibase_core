# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed model invariants and generative round trips (OMN-21373)."""

import math
import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_agent_skill_codec import (
    parse_skill_md,
    render_skill_md,
)
from omnibase_core.models.skill.model_agent_skill import ModelAgentSkill
from omnibase_core.models.skill.model_agent_skill_frontmatter import (
    ModelAgentSkillFrontmatter,
)
from omnibase_core.models.skill.model_claude_code_skill_extensions import (
    CLAUDE_CODE_EXTENSION_KEYS,
    ModelClaudeCodeSkillExtensions,
    decode_extension_value,
    encode_extension_value,
)

if TYPE_CHECKING:
    from pydantic import JsonValue


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "limit", "rule"),
    [
        ("name", 64, "name-length"),
        ("description", 1024, "description-length"),
        ("compatibility", 500, "compatibility-length"),
    ],
)
def test_field_limits(field: str, limit: int, rule: str) -> None:
    data = {"name": "skill", "description": "Description", field: "a" * limit}
    ModelAgentSkillFrontmatter.model_validate(data)
    data[field] += "a"
    with pytest.raises(ValueError, match=rule):
        ModelAgentSkillFrontmatter.model_validate(data)


@pytest.mark.unit
def test_construction_paths_and_input_copy() -> None:
    metadata = {"claude-code.model": "opus"}
    frontmatter = {"name": "skill", "description": "Description", "metadata": metadata}
    direct = ModelAgentSkill.model_validate(
        {"frontmatter": frontmatter, "directory_name": "skill"}
    )
    parsed = parse_skill_md(
        "---\nname: skill\ndescription: Description\nmodel: opus\n---\n", "skill"
    )
    assert direct == parsed
    assert direct.extensions.model == "opus"
    assert direct.frontmatter.metadata == {}
    assert metadata == {"claude-code.model": "opus"}
    assert frontmatter["metadata"] == metadata
    via_model = ModelAgentSkill(
        frontmatter=ModelAgentSkillFrontmatter.model_validate(frontmatter),
        directory_name="skill",
    )
    assert via_model == direct


@pytest.mark.unit
@pytest.mark.parametrize("metadata", [{"claude-code.model": "opus"}, {"model": "opus"}])
def test_duplicate_extension(metadata: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="duplicate-representation"):
        ModelAgentSkill(
            frontmatter=ModelAgentSkillFrontmatter(
                name="skill", description="Description", metadata=metadata
            ),
            extensions=ModelClaudeCodeSkillExtensions(model="opus"),
            directory_name="skill",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("\r\n \r\nText\r\nNext\r\n \r\n\r\n", "Text\nNext\n"),
        (" \r\n\t\r", ""),
        ("Text  \r", "Text  \n"),
    ],
)
def test_body_normalization(body: str, expected: str) -> None:
    skill = ModelAgentSkill(
        frontmatter=ModelAgentSkillFrontmatter(name="skill", description="Description"),
        directory_name="skill",
        body=body,
    )
    assert skill.body == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("arguments", []),
        ("arguments", "[]"),
        ("arguments", '["one"]'),
        ("hooks", {}),
        ("hooks", {"nested": []}),
        ("hooks", {"nested": {}}),
        ("hooks", {"value": None}),
        ("hooks", {"value": math.nan}),
        ("background", "true"),
        ("model", 3),
    ],
)
def test_extension_value_types(key: str, value: object) -> None:
    with pytest.raises(ValueError, match="extension-value-type"):
        ModelClaudeCodeSkillExtensions.model_validate({key: value})


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    ["left --- right", {"left---right": "value"}, {"nested": ["left --- right"]}],
)
def test_extension_delimiters(value: object) -> None:
    key = "hooks" if isinstance(value, dict) else "model"
    with pytest.raises(ValueError, match="frontmatter-delimiter-in-value"):
        ModelClaudeCodeSkillExtensions.model_validate({key: value})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("key", "text"),
    [
        ("background", "not-json"),
        ("background", "42"),
        ("hooks", "[]"),
        ("arguments", "[1]"),
        ("paths", "[]"),
    ],
)
def test_bad_extension_decode(key: str, text: str) -> None:
    with pytest.raises(ModelOnexError, match="extension-value-type"):
        decode_extension_value(key, text)
    with pytest.raises(ValidationError, match="extension-value-type"):
        ModelAgentSkill.model_validate(
            {
                "frontmatter": {
                    "name": "skill",
                    "description": "Description",
                    "metadata": {f"claude-code.{key}": text},
                },
                "directory_name": "skill",
            }
        )


@pytest.mark.unit
def test_frontmatter_rules_and_delimiters() -> None:
    for field in (
        "name",
        "description",
        "license",
        "compatibility",
        "allowed-tools",
        "metadata",
    ):
        data: dict[str, object] = {"name": "skill", "description": "Description"}
        data[field] = {"a---b": "value"} if field == "metadata" else "left --- right"
        with pytest.raises(ValueError, match="frontmatter-delimiter-in-value"):
            ModelAgentSkillFrontmatter.model_validate(data)
    with pytest.raises(ValueError, match="compatibility-empty"):
        ModelAgentSkillFrontmatter(
            name="skill", description="Description", compatibility=" "
        )
    with pytest.raises(ValueError, match="name-dir-mismatch"):
        ModelAgentSkill(
            frontmatter=ModelAgentSkillFrontmatter(
                name="skill", description="Description"
            ),
            directory_name="other",
        )


SAFE = st.text(
    alphabet=st.one_of(
        st.sampled_from(string.printable),
        st.characters(categories=("L", "M", "N", "P", "S", "Zs")),
    ),
    max_size=100,
).filter(lambda s: "---" not in s)
NONBLANK = SAFE.filter(lambda s: bool(s.strip()))
METADATA_KEY = SAFE.filter(
    lambda s: not s.startswith(("onex.", "claude-code."))
    and s
    not in {
        *CLAUDE_CODE_EXTENSION_KEYS,
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
)
NAMES = st.lists(
    st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10),
    min_size=1,
    max_size=5,
).map("-".join)
HOOK_LEAF = st.one_of(
    SAFE,
    st.booleans(),
    st.integers(min_value=-100000, max_value=100000),
    st.floats(allow_nan=False),
)
HOOK_VALUE = st.recursive(
    HOOK_LEAF,
    lambda child: st.one_of(
        st.lists(child, min_size=1, max_size=3),
        st.dictionaries(SAFE, child, min_size=1, max_size=3),
    ),
    max_leaves=10,
)


@st.composite
def valid_models(draw: DrawFn) -> ModelAgentSkill:
    name = draw(NAMES)
    extensions: dict[str, JsonValue] = {}
    for key in draw(st.sets(st.sampled_from(CLAUDE_CODE_EXTENSION_KEYS))):
        if key in {"background", "user-invocable", "disable-model-invocation"}:
            extensions[key] = draw(st.booleans())
        elif key in {"arguments", "disallowed-tools", "paths"}:
            extensions[key] = draw(
                st.one_of(
                    SAFE.filter(lambda s: not s.lstrip().startswith("[")),
                    st.lists(SAFE, min_size=1, max_size=4),
                )
            )
        elif key == "hooks":
            extensions[key] = draw(
                st.dictionaries(SAFE, HOOK_VALUE, min_size=1, max_size=3)
            )
        else:
            extensions[key] = draw(SAFE)
    front = ModelAgentSkillFrontmatter(
        name=name,
        description=draw(NONBLANK),
        license=draw(st.one_of(st.none(), SAFE)),
        compatibility=draw(st.one_of(st.none(), NONBLANK)),
        metadata=draw(st.dictionaries(METADATA_KEY, SAFE, max_size=5)),
        allowed_tools=draw(st.one_of(st.none(), SAFE)),
    )
    body = draw(st.lists(SAFE, max_size=8))
    endings = draw(
        st.lists(
            st.sampled_from(["\n", "\r\n", "\r"]),
            min_size=len(body),
            max_size=len(body),
        )
    )
    return ModelAgentSkill(
        frontmatter=front,
        extensions=ModelClaudeCodeSkillExtensions.model_validate(extensions),
        body="".join(line + ending for line, ending in zip(body, endings, strict=True)),
        directory_name=name,
    )


@pytest.mark.unit
@settings(max_examples=200, deadline=None)
@given(valid_models())
def test_round_trip_and_fixed_point(skill: ModelAgentSkill) -> None:
    for profile in EnumAgentSkillRenderProfile:
        rendered = render_skill_md(skill, profile)
        parsed = parse_skill_md(rendered, skill.directory_name, profile)
        assert parsed == skill
        assert render_skill_md(parsed, profile) == rendered
    for key, value in skill.extensions.to_frontmatter().items():
        assert decode_extension_value(key, encode_extension_value(key, value)) == value


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        1e20,
        1e-20,
        5e-324,
        math.inf,
        -math.inf,
        "\x85",
        "\x7f",
        "\x80",
        "\ud800",
        "\ufffe",
        "\u2028",
        "\u2029",
    ],
)
def test_yaml_sensitive_scalar_round_trips(value: str | float) -> None:
    skill = ModelAgentSkill(
        frontmatter=ModelAgentSkillFrontmatter(
            name="skill", description="Description", metadata={"control": "\x85"}
        ),
        extensions=ModelClaudeCodeSkillExtensions(hooks={"value": value}),
        directory_name="skill",
    )
    for profile in EnumAgentSkillRenderProfile:
        rendered = render_skill_md(skill, profile)
        assert parse_skill_md(rendered, "skill", profile) == skill
        assert (
            render_skill_md(parse_skill_md(rendered, "skill", profile), profile)
            == rendered
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "metadata",
    [
        {"model": "one", "claude-code.model": "two"},
        {"claude-code.model": "two", "model": "one"},
    ],
)
def test_promoted_extension_collisions_are_order_independent(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(ValueError, match="duplicate-representation"):
        ModelAgentSkill(
            frontmatter=ModelAgentSkillFrontmatter(
                name="skill", description="Description", metadata=metadata
            ),
            directory_name="skill",
        )
