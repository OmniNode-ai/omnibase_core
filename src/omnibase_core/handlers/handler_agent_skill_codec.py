# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure Agent Skills validation, tolerant reading and canonical rendering (OMN-21373)."""

import json
import math
import unicodedata
from collections.abc import Callable, Mapping
from importlib import import_module
from typing import cast

import yaml
from pydantic import JsonValue, ValidationError

from omnibase_core.enums.enum_agent_skill_render_profile import (
    EnumAgentSkillRenderProfile,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.skill.model_agent_skill import ModelAgentSkill
from omnibase_core.models.skill.model_agent_skill_frontmatter import (
    SPEC_FIELD_KEYS,
    compatibility_rule_ids,
    compatibility_spec_rule_ids,
    contains_delimiter,
    description_rule_ids,
    name_house_rule_ids,
    name_rule_ids,
    normalized_name,
)
from omnibase_core.models.skill.model_agent_skill_onex_keys import (
    METADATA_PREFIX_CLAUDE_CODE,
    METADATA_PREFIX_ONEX,
    decode_onex_value,
)
from omnibase_core.models.skill.model_agent_skill_source import ModelAgentSkillSource
from omnibase_core.models.skill.model_agent_skill_verdict import ModelAgentSkillVerdict
from omnibase_core.models.skill.model_claude_code_skill_extensions import (
    CLAUDE_CODE_EXTENSION_KEYS,
    ModelClaudeCodeSkillExtensions,
    decode_extension_value,
    encode_extension_value,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

_strictyaml = import_module("strictyaml")
_STRICT_LOAD: Callable[[str], object] = _strictyaml.load
_STRICT_YAML_ERROR: type[Exception] = _strictyaml.YAMLError


def _error_rules(exc: Exception) -> list[str]:
    if isinstance(exc, ValidationError):
        return [
            str(error.get("ctx", {}).get("error", error["msg"])).split(":", 1)[0]
            for error in exc.errors()
        ]
    message = exc.message if isinstance(exc, ModelOnexError) else str(exc)
    return [message.split(":", 1)[0]]


def check_skill_md(
    text: str,
    directory_name: str,
    profile: EnumAgentSkillRenderProfile = EnumAgentSkillRenderProfile.AGENT_SKILLS,
) -> ModelAgentSkillVerdict:
    """Return independent reference, specification and house verdicts."""
    reference: list[str] = []
    spec: list[str] = []
    house: list[str] = []
    diagnostics: list[str] = []
    skill: ModelAgentSkill | None = None

    def verdict() -> ModelAgentSkillVerdict:
        return ModelAgentSkillVerdict(
            profile=profile,
            reference_rules=tuple(reference),
            spec_rules=tuple(spec),
            house_rules=tuple(house),
            diagnostics=tuple(diagnostics),
            skill=skill,
        )

    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        reference.append("frontmatter-missing")
        return verdict()
    try:
        raw = getattr(_STRICT_LOAD(parts[1]), "data", None)
    except _STRICT_YAML_ERROR as exc:
        reference.append("frontmatter-yaml")
        diagnostics.append(str(exc))
        return verdict()
    if not isinstance(raw, dict):
        reference.append("frontmatter-yaml")
        return verdict()
    front = dict(raw)
    raw_metadata = raw.get("metadata", {})
    if isinstance(raw_metadata, dict):
        if any(isinstance(v, (list, dict)) for v in raw_metadata.values()):
            spec.append("metadata-non-string")
        front["metadata"] = {str(k): str(v) for k, v in raw_metadata.items()}
    else:
        spec.append("metadata-non-string")
    allowed = set(SPEC_FIELD_KEYS)
    if profile == EnumAgentSkillRenderProfile.CLAUDE_CODE:
        allowed.update(CLAUDE_CODE_EXTENSION_KEYS)
    unexpected = sorted(set(front) - allowed)
    if unexpected:
        reference.append("unexpected-field")
        diagnostics.append(f"unexpected-field: {', '.join(unexpected)}")
    name = front.get("name")
    reference.extend(name_rule_ids(name))
    if (
        isinstance(name, str)
        and name.strip()
        and normalized_name(name) != unicodedata.normalize("NFKC", directory_name)
    ):
        reference.append("name-dir-mismatch")
    reference.extend(description_rule_ids(front.get("description")))
    if "compatibility" in front:
        reference.extend(compatibility_rule_ids(front["compatibility"]))
        spec.extend(compatibility_spec_rule_ids(front["compatibility"]))
    house.extend(name_house_rule_ids(name))
    # A plain delimiter inside a scalar can make the reference split succeed
    # on a truncated mapping. Inspect the complete line-delimited mapping too.
    complete_lines = text.splitlines(keepends=True)
    complete_frontmatter: object = raw
    if complete_lines and complete_lines[0].rstrip("\r\n") == "---":
        for index in range(1, len(complete_lines)):
            if complete_lines[index].rstrip("\r\n") == "---":
                try:
                    complete_frontmatter = getattr(
                        _STRICT_LOAD("".join(complete_lines[1:index])), "data", None
                    )
                except _STRICT_YAML_ERROR:
                    pass
                break
    if contains_delimiter(complete_frontmatter):
        house.append("frontmatter-delimiter-in-value")
    extensions: dict[str, JsonValue] = {}
    if profile == EnumAgentSkillRenderProfile.CLAUDE_CODE:
        try:
            typed = load_yaml_mapping_no_duplicates(
                parts[1], source="skill frontmatter"
            )
            extensions = {
                key: cast("JsonValue", typed[key])
                for key in CLAUDE_CODE_EXTENSION_KEYS
                if key in typed
            }
            ModelClaudeCodeSkillExtensions.model_validate(extensions)
        except (ValueError, yaml.YAMLError) as exc:
            house.extend(
                _error_rules(exc)
                if isinstance(exc, ValueError)
                else ["extension-value-type"]
            )
            diagnostics.append(str(exc))
    active_extensions = set(extensions) | (set(front) & set(CLAUDE_CODE_EXTENSION_KEYS))
    metadata = front.get("metadata", {})
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if (key in SPEC_FIELD_KEYS and key in front) or (
                key in CLAUDE_CODE_EXTENSION_KEYS and key in active_extensions
            ):
                house.append("duplicate-representation")
            try:
                if key.startswith(METADATA_PREFIX_CLAUDE_CODE):
                    extension_key = key.removeprefix(METADATA_PREFIX_CLAUDE_CODE)
                    if extension_key not in CLAUDE_CODE_EXTENSION_KEYS:
                        house.append("reserved-metadata-prefix")
                        diagnostics.append(f"reserved-metadata-prefix: {key}")
                        continue
                    if extension_key in active_extensions:
                        house.append("duplicate-representation")
                    decode_extension_value(extension_key, value)
                    active_extensions.add(extension_key)
                elif key.startswith(METADATA_PREFIX_ONEX):
                    decode_onex_value(key.removeprefix(METADATA_PREFIX_ONEX), value)
            except ModelOnexError as exc:
                house.extend(_error_rules(exc))
                diagnostics.append(str(exc))
        if set(metadata) & active_extensions:
            house.append("duplicate-representation")
    if not (reference or spec or house):
        try:
            body = parts[2].removeprefix("\n")
            skill = ModelAgentSkill.model_validate(
                {
                    "frontmatter": {
                        key: front[key] for key in SPEC_FIELD_KEYS if key in front
                    },
                    "extensions": extensions,
                    "body": body,
                    "directory_name": directory_name,
                }
            )
        except ValueError as exc:
            for rule in _error_rules(exc):
                if rule in {"compatibility-empty", "metadata-non-string"}:
                    spec.append(rule)
                elif rule in {
                    "name-dir-mismatch",
                    *name_rule_ids(name),
                    *description_rule_ids(front.get("description")),
                }:
                    reference.append(rule)
                else:
                    house.append(rule if " " not in rule else "extension-value-type")
            diagnostics.append(str(exc))
    return verdict()


def parse_skill_md(
    text: str,
    directory_name: str,
    profile: EnumAgentSkillRenderProfile = EnumAgentSkillRenderProfile.CLAUDE_CODE,
) -> ModelAgentSkill:
    """Parse a conformant document, or refuse it with stable rule IDs."""
    verdict = check_skill_md(text, directory_name, profile)
    if not verdict.conformant:
        rules = sorted(
            {*verdict.reference_rules, *verdict.spec_rules, *verdict.house_rules}
        )
        raise ModelOnexError(
            f"{rules[0]}: agent skill refused: {','.join(rules)}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    assert verdict.skill is not None
    return verdict.skill


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    return str(value)


def read_skill_md(text: str) -> ModelAgentSkillSource:
    """Read line-delimited frontmatter using tolerant YAML semantics."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].rstrip("\r\n") == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip("\r\n") != "---":
                continue
            content = "".join(lines[1:index])
            try:
                raw = (
                    load_yaml_mapping_no_duplicates(content, source="skill frontmatter")
                    if content.strip()
                    else {}
                )
            except (ValueError, yaml.YAMLError) as exc:
                raise ModelOnexError(
                    f"frontmatter-yaml: {exc}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from exc
            frontmatter = {str(key): _json_value(value) for key, value in raw.items()}
            return ModelAgentSkillSource(
                has_frontmatter=True,
                frontmatter=frontmatter,
                body="".join(lines[index + 1 :]),
            )
    return ModelAgentSkillSource(has_frontmatter=False, frontmatter={}, body=text)


def _scalar(value: JsonValue) -> str:
    encoded = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        # YAML normalizes NEL and forbids raw C1 controls and surrogates.
        return "".join(
            f"\\u{ord(char):04x}"
            if 0x7F <= ord(char) <= 0x9F
            or 0xD800 <= ord(char) <= 0xDFFF
            or ord(char) in (0xFFFE, 0xFFFF)
            else char
            for char in encoded
        )
    if isinstance(value, float):
        if math.isinf(value):
            return ".inf" if value > 0 else "-.inf"
        # PyYAML requires a decimal mantissa to recognize an exponent as float.
        if "e" in encoded and "." not in encoded:
            return encoded.replace("e", ".0e")
    return encoded


def _entry(
    key: str, value: JsonValue, indent: int, *, plain_key: bool = False
) -> list[str]:
    prefix = " " * indent + (key if plain_key else _scalar(key)) + ":"
    if isinstance(value, (dict, list)):
        return [prefix, *_block(value, indent + 2)]
    return [prefix + " " + _scalar(value)]


def _block(value: dict[str, JsonValue] | list[JsonValue], indent: int) -> list[str]:
    lines: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            lines.extend(_entry(key, value[key], indent))
    else:
        for item in value:
            prefix = " " * indent + "-"
            if isinstance(item, (dict, list)):
                lines.append(prefix + " ")
                lines.extend(_block(item, indent + 2))
            else:
                lines.append(prefix + " " + _scalar(item))
    return lines


def render_skill_md(
    skill: ModelAgentSkill, profile: EnumAgentSkillRenderProfile
) -> str:
    """Render fixed key order and block YAML without an emitter library."""
    front = skill.frontmatter.model_dump(mode="json", by_alias=True, exclude_none=True)
    metadata = dict(skill.frontmatter.metadata)
    extensions = skill.extensions.to_frontmatter()
    if profile == EnumAgentSkillRenderProfile.AGENT_SKILLS:
        for key, value in extensions.items():
            metadata[METADATA_PREFIX_CLAUDE_CODE + key] = encode_extension_value(
                key, value
            )
    front["metadata"] = metadata
    lines = ["---"]
    for key in SPEC_FIELD_KEYS:
        if key in front and (key != "metadata" or metadata):
            lines.extend(_entry(key, cast("JsonValue", front[key]), 0, plain_key=True))
    if profile == EnumAgentSkillRenderProfile.CLAUDE_CODE:
        for key, value in extensions.items():
            lines.extend(_entry(key, value, 0, plain_key=True))
    lines.append("---")
    return "\n".join(lines) + "\n" + ("\n" + skill.body if skill.body else "")
