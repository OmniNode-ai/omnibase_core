# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelAislopRule Pydantic models (OMN-11132)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_aislop_config import ModelAislopConfig
from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_aislop_rule_override import (
    ModelAislopRuleOverride,
)
from omnibase_core.models.validation.model_aislop_rule_set import ModelAislopRuleSet


@pytest.mark.unit
class TestModelAislopRule:
    def test_minimal_rule(self) -> None:
        rule = ModelAislopRule(
            name="sycophancy",
            severity="ERROR",
            pattern_type="regex_ast_docstring",
            pattern=r"^\s*Excellent",
            description="Sycophantic opener",
        )
        assert rule.name == "sycophancy"
        assert rule.severity == "ERROR"
        assert rule.enabled is True
        assert rule.file_globs == ["*.py"]
        assert rule.suppression_annotation == "ai-slop-ok"

    def test_rule_serialization_roundtrip(self) -> None:
        rule = ModelAislopRule(
            name="test_rule",
            severity="WARNING",
            pattern_type="grep_code",
            pattern=r"\bFIXME\b",
            file_globs=["*.py", "*.yaml"],
            description="FIXME marker",
        )
        data = rule.model_dump()
        restored = ModelAislopRule.model_validate(data)
        assert restored == rule

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelAislopRule(
                name="bad",
                severity="FATAL",  # type: ignore[arg-type]
                pattern_type="grep_code",
                pattern="x",
                description="bad severity",
            )

    def test_invalid_pattern_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelAislopRule(
                name="bad",
                severity="ERROR",
                pattern_type="unknown_type",  # type: ignore[arg-type]
                pattern="x",
                description="bad pattern_type",
            )


@pytest.mark.unit
class TestModelAislopRuleSet:
    def test_empty_ruleset(self) -> None:
        rs = ModelAislopRuleSet()
        assert rs.rules == []

    def test_ruleset_with_rules(self) -> None:
        rs = ModelAislopRuleSet(
            rules=[
                ModelAislopRule(
                    name="r1",
                    severity="ERROR",
                    pattern_type="grep_code",
                    pattern="x",
                    description="rule 1",
                ),
                ModelAislopRule(
                    name="r2",
                    severity="WARNING",
                    pattern_type="regex_line",
                    pattern="y",
                    description="rule 2",
                ),
            ]
        )
        assert len(rs.rules) == 2

    def test_ruleset_roundtrip(self) -> None:
        rs = ModelAislopRuleSet(
            rules=[
                ModelAislopRule(
                    name="x",
                    severity="INFO",
                    pattern_type="ast_check",
                    pattern="check_id",
                    description="info rule",
                )
            ],
        )
        data = rs.model_dump()
        assert ModelAislopRuleSet.model_validate(data) == rs


@pytest.mark.unit
class TestModelAislopRuleOverride:
    def test_all_none_fields(self) -> None:
        override = ModelAislopRuleOverride(name="sycophancy")
        assert override.severity is None
        assert override.enabled is None
        assert override.file_globs is None
        assert override.allow_new is False

    def test_partial_override(self) -> None:
        override = ModelAislopRuleOverride(name="sycophancy", enabled=False)
        assert override.enabled is False
        assert override.severity is None

    def test_allow_new_override(self) -> None:
        override = ModelAislopRuleOverride(name="my_custom", allow_new=True)
        assert override.allow_new is True


@pytest.mark.unit
class TestModelAislopConfig:
    def test_empty_config(self) -> None:
        cfg = ModelAislopConfig()
        assert cfg.overrides == []
        assert cfg.custom_rules == []

    def test_config_with_overrides(self) -> None:
        cfg = ModelAislopConfig(
            overrides=[
                ModelAislopRuleOverride(name="sycophancy", enabled=False),
                ModelAislopRuleOverride(name="todo_fixme", severity="ERROR"),
            ]
        )
        assert len(cfg.overrides) == 2

    def test_custom_rule_requires_allow_new(self) -> None:
        """custom_rules entry without matching allow_new=True override must fail."""
        with pytest.raises(ValidationError, match="allow_new"):
            ModelAislopConfig(
                overrides=[],
                custom_rules=[
                    ModelAislopRule(
                        name="my_rule",
                        severity="WARNING",
                        pattern_type="grep_code",
                        pattern="x",
                        description="orphan",
                    )
                ],
            )

    def test_custom_rule_with_allow_new_passes(self) -> None:
        cfg = ModelAislopConfig(
            overrides=[ModelAislopRuleOverride(name="my_rule", allow_new=True)],
            custom_rules=[
                ModelAislopRule(
                    name="my_rule",
                    severity="WARNING",
                    pattern_type="grep_code",
                    pattern="x",
                    description="custom rule",
                )
            ],
        )
        assert len(cfg.custom_rules) == 1
