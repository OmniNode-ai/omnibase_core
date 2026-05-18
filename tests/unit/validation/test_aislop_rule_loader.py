# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for aislop_rule_loader (OMN-11132)."""

import textwrap
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_aislop_config import ModelAislopConfig
from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_aislop_rule_override import (
    ModelAislopRuleOverride,
)
from omnibase_core.models.validation.model_aislop_rule_set import ModelAislopRuleSet
from omnibase_core.validation.aislop_rule_loader import (
    load_default_rules,
    load_repo_config,
    merge_rules,
    resolve_rules,
)


@pytest.mark.unit
def test_load_default_rules() -> None:
    ruleset = load_default_rules()
    assert isinstance(ruleset, ModelAislopRuleSet)
    names = {r.name for r in ruleset.rules}
    # All 14 expected rules must be present
    expected = {
        "sycophancy",
        "rest_docstring",
        "boilerplate_docstring",
        "md_separator",
        "step_narration",
        "obvious_comment",
        "hardcoded_ip",
        "hardcoded_localhost",
        "hardcoded_port",
        "hardcoded_topic",
        "prohibited_env_pattern",
        "compat_shim",
        "empty_impl",
        "todo_fixme",
    }
    assert expected.issubset(names), f"Missing rules: {expected - names}"


@pytest.mark.unit
def test_load_default_rules_parses_without_error() -> None:
    ruleset = load_default_rules()
    for rule in ruleset.rules:
        assert rule.name
        assert rule.pattern
        assert rule.severity in ("ERROR", "WARNING", "INFO")


@pytest.mark.unit
def test_load_repo_config_missing_returns_none(tmp_path: Path) -> None:
    result = load_repo_config(tmp_path)
    assert result is None


@pytest.mark.unit
def test_load_repo_config_reads_file(tmp_path: Path) -> None:
    onex_dir = tmp_path / ".onex"
    onex_dir.mkdir()
    (onex_dir / "aislop-rules.yaml").write_text(
        textwrap.dedent("""\
            overrides:
              - name: obvious_comment
                enabled: false
        """)
    )
    config = load_repo_config(tmp_path)
    assert config is not None
    assert len(config.overrides) == 1
    assert config.overrides[0].name == "obvious_comment"
    assert config.overrides[0].enabled is False


@pytest.mark.unit
def test_merge_no_config_returns_defaults() -> None:
    defaults = load_default_rules()
    merged = merge_rules(defaults, None)
    assert merged == defaults


@pytest.mark.unit
def test_merge_disables_rule() -> None:
    defaults = load_default_rules()
    config = ModelAislopConfig(
        overrides=[ModelAislopRuleOverride(name="sycophancy", enabled=False)]
    )
    merged = merge_rules(defaults, config)
    sycophancy = next(r for r in merged.rules if r.name == "sycophancy")
    assert sycophancy.enabled is False


@pytest.mark.unit
def test_merge_changes_severity() -> None:
    defaults = load_default_rules()
    config = ModelAislopConfig(
        overrides=[
            ModelAislopRuleOverride(name="boilerplate_docstring", severity="ERROR")
        ]
    )
    merged = merge_rules(defaults, config)
    rule = next(r for r in merged.rules if r.name == "boilerplate_docstring")
    assert rule.severity == "ERROR"


@pytest.mark.unit
def test_merge_changes_file_globs() -> None:
    defaults = load_default_rules()
    config = ModelAislopConfig(
        overrides=[
            ModelAislopRuleOverride(
                name="todo_fixme", file_globs=["*.py", "*.yaml", "*.ts"]
            )
        ]
    )
    merged = merge_rules(defaults, config)
    rule = next(r for r in merged.rules if r.name == "todo_fixme")
    assert "*.ts" in rule.file_globs


@pytest.mark.unit
def test_merge_adds_custom_rule() -> None:
    defaults = load_default_rules()
    custom = ModelAislopRule(
        name="my_custom",
        severity="WARNING",
        pattern_type="grep_code",
        pattern=r"\bDEPRECATED\b",
        description="Deprecated marker",
    )
    config = ModelAislopConfig(
        overrides=[ModelAislopRuleOverride(name="my_custom", allow_new=True)],
        custom_rules=[custom],
    )
    merged = merge_rules(defaults, config)
    names = [r.name for r in merged.rules]
    assert "my_custom" in names
    # Custom rule appended after defaults
    assert names.index("my_custom") == len(names) - 1


@pytest.mark.unit
def test_merge_unknown_name_without_allow_new_raises() -> None:
    defaults = load_default_rules()
    config = ModelAislopConfig(
        overrides=[ModelAislopRuleOverride(name="nonexistent_rule_xyz")]
    )
    with pytest.raises(ValueError, match="nonexistent_rule_xyz"):
        merge_rules(defaults, config)


@pytest.mark.unit
def test_merge_preserves_unoverridden_rules() -> None:
    defaults = load_default_rules()
    config = ModelAislopConfig(
        overrides=[ModelAislopRuleOverride(name="sycophancy", enabled=False)]
    )
    merged = merge_rules(defaults, config)
    # All default rules should still be present
    assert len(merged.rules) == len(defaults.rules)


@pytest.mark.unit
def test_resolve_rules_no_config_uses_defaults(tmp_path: Path) -> None:
    defaults = load_default_rules()
    resolved = resolve_rules(tmp_path)
    assert {r.name for r in resolved.rules} == {r.name for r in defaults.rules}


@pytest.mark.unit
def test_resolve_rules_with_config(tmp_path: Path) -> None:
    onex_dir = tmp_path / ".onex"
    onex_dir.mkdir()
    (onex_dir / "aislop-rules.yaml").write_text(
        textwrap.dedent("""\
            overrides:
              - name: rest_docstring
                severity: WARNING
        """)
    )
    resolved = resolve_rules(tmp_path)
    rule = next(r for r in resolved.rules if r.name == "rest_docstring")
    assert rule.severity == "WARNING"
