# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agreement with the installed Agent Skills reference (OMN-21373)."""

from pathlib import Path

import pytest
import strictyaml
import yaml
from skills_ref.validator import validate

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.handlers.handler_agent_skill_codec import (
    check_skill_md,
    render_skill_md,
)
from omnibase_core.models.skill.model_agent_skill_frontmatter import SPEC_FIELD_KEYS
from omnibase_core.models.skill.model_claude_code_skill_extensions import (
    CLAUDE_CODE_EXTENSION_KEYS,
)
from tests.fixtures.agent_skill_tree import agent_skill_fixture_root

FIXTURES = agent_skill_fixture_root()
EXPECTED = yaml.safe_load((FIXTURES / "rules" / "expected.yaml").read_text())
MESSAGE_RULES = (
    ("must start with YAML frontmatter", "frontmatter-missing"),
    ("not properly closed", "frontmatter-missing"),
    ("Invalid YAML", "frontmatter-yaml"),
    ("must be a YAML mapping", "frontmatter-yaml"),
    ("Unexpected fields in frontmatter", "unexpected-field"),
    ("Missing required field in frontmatter: name", "name-missing"),
    ("Field 'name' must be a non-empty string", "name-missing"),
    ("exceeds 64 character limit", "name-length"),
    ("must be lowercase", "name-case"),
    ("cannot start or end with a hyphen", "name-hyphen-edge"),
    ("cannot contain consecutive hyphens", "name-double-hyphen"),
    ("contains invalid characters", "name-chars"),
    ("must match skill name", "name-dir-mismatch"),
    ("Missing required field in frontmatter: description", "description-missing"),
    ("Field 'description' must be a non-empty string", "description-missing"),
    ("Description exceeds 1024 character limit", "description-length"),
    ("Field 'compatibility' must be a string", "compatibility-type"),
    ("Compatibility exceeds 500 character limit", "compatibility-length"),
)


def reference_rules(directory: Path) -> list[str]:
    rules = []
    for message in validate(directory):
        matches = [rule for fragment, rule in MESSAGE_RULES if fragment in message]
        assert len(matches) == 1, f"Unmapped reference message: {message}"
        rules.extend(matches)
    return sorted(set(rules))


@pytest.mark.unit
def test_rule_agreement_and_declared_divergences() -> None:
    disagreements = []
    declared_divergences: dict[str, list[str]] = {}
    assert set(EXPECTED) == {
        path.parent.name for path in (FIXTURES / "rules").glob("*/SKILL.md")
    }
    for name, expected in EXPECTED.items():
        directory = FIXTURES / "rules" / name
        verdict = check_skill_md((directory / "SKILL.md").read_text(), name)
        actual = {
            "reference": list(verdict.reference_rules),
            "spec": list(verdict.spec_rules),
            "house": list(verdict.house_rules),
        }
        reference = reference_rules(directory)
        if actual != expected or actual["reference"] != reference:
            disagreements.append(
                f"{name}: model={actual}; expected={expected}; skills-ref={reference}; diagnostics={verdict.diagnostics}"
            )
        for rule in (*verdict.spec_rules, *verdict.house_rules):
            if rule not in reference:
                declared_divergences.setdefault(rule, []).append(name)
    assert not disagreements, "Fixtures with differing verdicts:\n" + "\n".join(
        disagreements
    )
    assert set(declared_divergences) == {
        "compatibility-empty",
        "metadata-non-string",
        "house-ascii-name",
        "reserved-metadata-prefix",
        "duplicate-representation",
        "extension-value-type",
        "onex-value-type",
        "frontmatter-delimiter-in-value",
    }, declared_divergences


def without_extensions(text: str) -> str:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    skipping = False
    for line in lines:
        if line and not line[0].isspace():
            skipping = line.split(":", 1)[0] in CLAUDE_CODE_EXTENSION_KEYS
        if not skipping:
            result.append(line)
    return "".join(result)


@pytest.mark.unit
@pytest.mark.parametrize(
    "directory", sorted((FIXTURES / "claude_code").iterdir()), ids=lambda p: p.name
)
def test_claude_code_agreement(directory: Path, tmp_path: Path) -> None:
    text = (directory / "SKILL.md").read_text()
    verdict = check_skill_md(
        text, directory.name, EnumAgentSkillRenderProfile.CLAUDE_CODE
    )
    assert verdict.conformant, verdict
    assert reference_rules(directory) == ["unexpected-field"]
    target = tmp_path / directory.name
    target.mkdir()
    (target / "SKILL.md").write_text(without_extensions(text))
    assert validate(target) == []


@pytest.mark.unit
def test_all_conformant_fixtures_render_for_reference(tmp_path: Path) -> None:
    count = 0
    for path in sorted(FIXTURES.rglob("SKILL.md")):
        profile = (
            EnumAgentSkillRenderProfile.CLAUDE_CODE
            if "claude_code" in path.relative_to(FIXTURES).parts
            else EnumAgentSkillRenderProfile.AGENT_SKILLS
        )
        verdict = check_skill_md(path.read_text(), path.parent.name, profile)
        if not verdict.conformant:
            continue
        assert verdict.skill is not None
        rendered = render_skill_md(
            verdict.skill, EnumAgentSkillRenderProfile.AGENT_SKILLS
        )
        data = strictyaml.load(rendered.split("---", 2)[1]).data
        assert set(data) <= set(SPEC_FIELD_KEYS)
        target = tmp_path / path.relative_to(FIXTURES).parent
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text(rendered)
        assert validate(target) == [], str(path)
        count += 1
    assert count >= 10


@pytest.mark.unit
def test_reference_string_scalars_and_name_normalization() -> None:
    verdict = check_skill_md(
        (FIXTURES / "rules" / "yes-description" / "SKILL.md").read_text(),
        "yes-description",
    )
    assert verdict.skill is not None
    assert verdict.skill.frontmatter.description == "yes"
    verdict = check_skill_md(
        (FIXTURES / "rules" / "nfkc" / "SKILL.md").read_text(), "nfkc"
    )
    assert verdict.skill is not None
    assert verdict.skill.frontmatter.name == "nfkc"
