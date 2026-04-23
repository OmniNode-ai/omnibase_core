# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorHardcodedTopics (OMN-9152)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_hardcoded_topics import (
    _RULE_TOPIC_ENV_VAR,
    _RULE_TOPIC_LITERAL,
    ValidatorHardcodedTopics,
)


def _make_contract(
    *,
    rules: list[ModelValidatorRule] | None = None,
    suppression_comments: list[str] | None = None,
) -> ModelValidatorSubcontract:
    default_rules = [
        ModelValidatorRule(
            rule_id=_RULE_TOPIC_LITERAL,
            description="test",
            severity=EnumSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=_RULE_TOPIC_ENV_VAR,
            description="test",
            severity=EnumSeverity.ERROR,
            enabled=True,
        ),
    ]
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="hardcoded_topics",
        validator_name="Test",
        validator_description="Test",
        target_patterns=["**/*.py", "**/*.yaml"],
        exclude_patterns=[],
        suppression_comments=suppression_comments
        or [
            "# onex-topic-sot",
            "# onex-topic-test-fixture",
            "# onex-topic-doc-example",
            "# onex-topic-allow:",
        ],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=EnumSeverity.ERROR,
        rules=rules if rules is not None else default_rules,
    )


def _write(tmp_path: Path, content: str, name: str = "test.py") -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))
    return p


@pytest.mark.unit
class TestValidatorHardcodedTopicsInit:
    def test_validator_id(self) -> None:
        assert ValidatorHardcodedTopics.validator_id == "hardcoded_topics"

    def test_init_with_contract(self, tmp_path: Path) -> None:
        contract = _make_contract()
        v = ValidatorHardcodedTopics(contract=contract)
        assert v.contract.validator_id == "hardcoded_topics"


@pytest.mark.unit
class TestTopicLiteralDetection:
    def test_detects_evt_topic(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """TOPIC = "onex.evt.platform.node-introspection.v1"\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert not result.is_valid
        assert any(i.code == _RULE_TOPIC_LITERAL for i in result.issues)

    def test_detects_cmd_topic(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """TOPIC = "onex.cmd.runtime.start-session.v1"\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert not result.is_valid

    def test_detects_dlq_topic(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """TOPIC = "onex.dlq.platform.dlq-message.v1"\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert not result.is_valid

    def test_clean_file_no_violations(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """TOPIC = "something-else"\nprint("hello")\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_reports_file_and_line(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            x = 1
            TOPIC = "onex.evt.test.event.v1"
            y = 2
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.line_number == 2
        assert issue.file_path == p

    def test_multiple_violations_in_one_file(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            B = "onex.cmd.test.b.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert len(result.issues) == 2


@pytest.mark.unit
class TestEnvVarDetection:
    def test_detects_input_topic_assignment(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            import os
            ONEX_INPUT_TOPIC = "onex.evt.test.input.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) >= 1

    def test_detects_output_topic_assignment(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            OUTPUT_TOPIC = "something"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) >= 1


@pytest.mark.unit
class TestApprovedFiles:
    def test_topics_py_exempt(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            B = "onex.cmd.test.b.v1"
            """,
            name="topics.py",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_contract_yaml_exempt(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            subscriptions:
              - topic: "onex.evt.test.a.v1"
            """,
            name="contract.yaml",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_topic_constants_py_exempt(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            MY_TOPIC: str = "onex.evt.test.a.v1"
            """,
            name="topic_constants.py",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid


@pytest.mark.unit
class TestSuppression:
    def test_onex_topic_sot_suppresses(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"  # onex-topic-sot
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_onex_topic_test_fixture_suppresses(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"  # onex-topic-test-fixture
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_onex_topic_allow_suppresses(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"  # onex-topic-allow: legacy adapter
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_unsuppressed_line_still_fails(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            B = "onex.evt.test.b.v1"  # onex-topic-sot
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert not result.is_valid
        assert len(result.issues) == 1
        assert result.issues[0].line_number == 1


@pytest.mark.unit
class TestRuleConfiguration:
    def test_disabled_rule_skipped(self, tmp_path: Path) -> None:
        rules = [
            ModelValidatorRule(
                rule_id=_RULE_TOPIC_LITERAL,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=False,
            ),
            ModelValidatorRule(
                rule_id=_RULE_TOPIC_ENV_VAR,
                description="test",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
        ]
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract(rules=rules))
        result = v.validate_file(p)
        literal_issues = [i for i in result.issues if i.code == _RULE_TOPIC_LITERAL]
        assert len(literal_issues) == 0

    def test_severity_override(self, tmp_path: Path) -> None:
        rules = [
            ModelValidatorRule(
                rule_id=_RULE_TOPIC_LITERAL,
                description="test",
                severity=EnumSeverity.WARNING,
                enabled=True,
            ),
        ]
        p = _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract(rules=rules))
        result = v.validate_file(p)
        assert len(result.issues) == 1
        assert result.issues[0].severity == EnumSeverity.WARNING

    def test_yaml_file_with_topic_in_contract_field_exempt(
        self, tmp_path: Path
    ) -> None:
        p = _write(
            tmp_path,
            """\
            contract_kind: validation_subcontract
            validation:
              subscriptions:
                - topic: "onex.evt.test.a.v1"
            """,
            name="some_contract.yaml",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 0


@pytest.mark.unit
class TestDirectoryValidation:
    def test_validates_directory(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            """\
            A = "onex.evt.test.a.v1"
            """,
            name="bad.py",
        )
        _write(
            tmp_path,
            """\
            B = "clean"
            """,
            name="good.py",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate(tmp_path)
        assert not result.is_valid
        assert len(result.issues) == 1


@pytest.mark.unit
class TestEdgeCases:
    def test_empty_file(self, tmp_path: Path) -> None:
        p = _write(tmp_path, "")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_unreadable_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("A = 1\n")
        p.chmod(0o000)
        try:
            v = ValidatorHardcodedTopics(contract=_make_contract())
            result = v.validate_file(p)
            assert result.is_valid
        finally:
            p.chmod(0o644)

    def test_single_quote_topic(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """TOPIC = 'onex.evt.test.event.v1'\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert not result.is_valid

    def test_partial_match_not_flagged(self, tmp_path: Path) -> None:
        p = _write(tmp_path, """x = "not-a-onex-topic"\n""")
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        assert result.is_valid

    def test_docstring_topic_not_flagged_by_env_rule(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            '''\
            """
            Set ONEX_INPUT_TOPIC = "onex.evt.test.v1" to configure.
            """
            ''',
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 0

    def test_detects_unversioned_literal(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """TOPIC = "onex.evt.billing.charge_succeeded"\n""",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        literal_issues = [i for i in result.issues if i.code == _RULE_TOPIC_LITERAL]
        assert len(literal_issues) == 1

    def test_detects_export_topic_env_var(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            export INPUT_TOPIC=onex.cmd.user.created.v1
            """,
            name="deploy.sh",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 1

    def test_detects_dockerfile_env_topic(self, tmp_path: Path) -> None:
        p = _write(
            tmp_path,
            """\
            ENV INPUT_TOPIC=onex.cmd.user.created.v1
            """,
            name="Dockerfile",
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 1

    def test_detects_indented_env_var_assignment(self, tmp_path: Path) -> None:
        # Lines nested inside functions, conditionals, or YAML blocks are
        # common. The regex must not require start-of-line with zero
        # indentation.
        p = _write(
            tmp_path,
            """\
            def configure():
                INPUT_TOPIC = "onex.evt.test.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 1
        assert env_issues[0].line_number == 2

    def test_comment_header_does_not_gate_env_var_detection(
        self, tmp_path: Path
    ) -> None:
        p = _write(
            tmp_path,
            """\
            # Module header line one
            # Module header line two
            INPUT_TOPIC = "onex.evt.test.v1"
            """,
        )
        v = ValidatorHardcodedTopics(contract=_make_contract())
        result = v.validate_file(p)
        env_issues = [i for i in result.issues if i.code == _RULE_TOPIC_ENV_VAR]
        assert len(env_issues) == 1
        assert env_issues[0].line_number == 3
