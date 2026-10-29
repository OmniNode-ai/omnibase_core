# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure Agent Skills codec boundaries (OMN-21373)."""

import ast
import inspect
import sys

import pytest

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.validation import checker_agent_skill_codec
from omnibase_core.validation.checker_agent_skill_codec import (
    check_skill_md,
    parse_skill_md,
    read_skill_md,
    render_skill_md,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("No frontmatter", "frontmatter-missing"),
        ("---\nname: skill\n---\n", "description-missing"),
        (
            '---\nname: skill\ndescription: A skill\ncompatibility: ""\n---\n',
            "compatibility-empty",
        ),
    ],
)
def test_parse_refuses_rule_ids(text: str, rule: str) -> None:
    with pytest.raises(ModelOnexError, match=f"agent skill refused: .*{rule}") as exc:
        parse_skill_md(text, "skill")
    assert exc.value.message.startswith(f"{rule}:")
    assert exc.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_tolerant_reader() -> None:
    text = "A body without frontmatter.\r\n"
    source = read_skill_md(text)
    assert not source.has_frontmatter
    assert source.frontmatter == {}
    assert source.body == text
    source = read_skill_md(
        "---\nvalues: [one, two]\ndate: 2026-10-24\ntext: left --- right\n---\nBody\n"
    )
    assert source.has_frontmatter
    assert source.get("values") == ["one", "two"]
    assert source.get("date") == "2026-10-24"
    assert source.get("text") == "left --- right"
    assert source.body == "Body\n"
    assert read_skill_md("---\n---\n").frontmatter == {}
    assert read_skill_md("---\n  \n\t\n---\n").frontmatter == {}
    assert not read_skill_md("--- suffix\nname: skill\n---\n").has_frontmatter
    assert not read_skill_md("---\nname: skill\n").has_frontmatter


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "---\n- entry\n---\n",
        "---\nkey: [broken\n---\n",
        "---\nkey: first\nkey: second\n---\n",
        "---\nmetadata:\n  key: first\n  key: second\n---\n",
    ],
)
def test_reader_bad_yaml(text: str) -> None:
    with pytest.raises(ModelOnexError, match="frontmatter-yaml") as exc:
        read_skill_md(text)
    assert exc.value.message.startswith("frontmatter-yaml:")
    assert exc.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_reader_precedence() -> None:
    source = read_skill_md(
        "---\nmode: top\nmetadata:\n  onex.mode: '\"migrated\"'\n  mode: plain\n  claude-code.model: opus\n  other: fallback\n---\n"
    )
    assert source.get("mode") == "top"
    assert source.get("model") == "opus"
    assert source.get("other") == "fallback"
    assert source.get("missing") is None


@pytest.mark.unit
@pytest.mark.parametrize("body", ["", "\r\nText\r\n\r\n"])
def test_render_determinism(body: str) -> None:
    model = parse_skill_md(
        "---\nname: skill\ndescription: A skill\n---\n" + body, "skill"
    )
    for profile in EnumAgentSkillRenderProfile:
        rendered = render_skill_md(model, profile)
        assert rendered == render_skill_md(model, profile)
        assert "\r" not in rendered
        assert rendered.endswith("\n") and not rendered.endswith("\n\n")
        if not model.body:
            assert rendered.endswith("---\n")


@pytest.mark.unit
def test_sorted_unique_verdict_rules() -> None:
    verdict = check_skill_md(
        "---\nname: Upper_Name\ndescription: A skill\nmetadata:\n  onex.first: a\n  onex.second: b\n---\n",
        "Upper_Name",
    )
    assert verdict.house_rules == ("house-ascii-name", "reserved-metadata-prefix")
    assert verdict.reference_rules == ("name-case", "name-chars")


@pytest.mark.unit
def test_import_boundary() -> None:
    allowed = sys.stdlib_module_names | {
        "pydantic",
        "yaml",
        "strictyaml",
        "omnibase_core",
    }
    for node in ast.walk(ast.parse(inspect.getsource(checker_agent_skill_codec))):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed for alias in node.names), (
                ast.dump(node)
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None and node.module.split(".")[0] in allowed, (
                ast.dump(node)
            )
