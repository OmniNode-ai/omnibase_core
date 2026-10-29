# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the decisions of the OCC ``check-hardcoded-topics`` hook (OMN-20074).

The fixtures are verbatim fleet files; ``manifest.yaml`` records, per file, the
violation lines produced by onex_change_control rev 8d7e85bc00e7 for that path.
The handler must reproduce them, and the byte-exact output lines, so consumers
that change only ``repo:`` and ``rev:`` see no difference in what is flagged.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_check_input import (
    ModelNoHardcodedTopicsCheckInput,
)
from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_rules import (
    ModelNoHardcodedTopicsRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.handler_no_hardcoded_topics import (
    HandlerNoHardcodedTopics,
)
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.runtime_no_hardcoded_topics_check import (
    main,
)
from omnibase_core.validation.validator_no_hardcoded_topics import (
    ValidatorNoHardcodedTopics,
    load_rules,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_hardcoded_topics"
LITERAL = re.compile(r"""["']onex\.(evt|cmd)\.""")
MESSAGE = "hardcoded topic string -- use a constant from the canonical topic registry"


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    repo: str
    source_path: str
    source_rev: str
    expected_violation_lines: list[int]


def _cases() -> list[_Case]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    return [_Case(**item) for item in raw]


def _rules() -> ModelNoHardcodedTopicsRules:
    return load_rules(ValidatorNoHardcodedTopics().contract)


APPROVED_BASENAMES = _rules().approved_basenames


def _scan(
    path: str, source: str, rules: ModelNoHardcodedTopicsRules | None = None
) -> list[str]:
    report = HandlerNoHardcodedTopics().handle(
        ModelNoHardcodedTopicsCheckInput(
            files=[ModelSourceFile(path=path, source=source)],
            rules=rules or _rules(),
        )
    )
    return [finding.message for finding in report.findings]


def _fixture_text(case: _Case) -> str:
    return (FIXTURES / f"{case.id}.txt").read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.id)
def test_fleet_file_decision_matches_the_occ_hook(case: _Case) -> None:
    messages = _scan(case.source_path, _fixture_text(case))
    assert messages == [
        f"{case.source_path}:{line}: {MESSAGE}"
        for line in case.expected_violation_lines
    ]


def test_positive_control_flags_a_real_fleet_file() -> None:
    case = next(c for c in _cases() if c.id == "positive-control-py")
    assert case.expected_violation_lines
    assert _scan(case.source_path, _fixture_text(case))


@pytest.mark.parametrize(
    "case_id",
    [
        "skip-docstring",
        "skip-comment-line",
        "skip-template-docstring-state",
        "skip-test-file",
        "skip-approved-basename-py",
        "skip-approved-basename-yaml",
    ],
)
def test_each_skip_class_is_a_skip_of_a_file_that_holds_a_literal(case_id: str) -> None:
    case = next(c for c in _cases() if c.id == case_id)
    text = _fixture_text(case)
    assert LITERAL.search(text), "a skip fixture must contain a quoted topic literal"
    assert _scan(case.source_path, text) == []


@pytest.mark.parametrize("case_id", ["skip-test-file", "skip-approved-basename-py"])
def test_path_skips_are_what_clears_the_file(case_id: str) -> None:
    case = next(c for c in _cases() if c.id == case_id)
    assert _scan("src/service.py", _fixture_text(case))


@pytest.mark.parametrize("basename", sorted(APPROVED_BASENAMES))
def test_every_approved_basename_is_skipped(basename: str) -> None:
    assert _scan(f"src/pkg/{basename}", 'T = "onex.evt.a.b.v1"\n') == []


def test_the_approved_basenames_are_the_twelve_of_the_occ_hook() -> None:
    assert (
        frozenset(
            {
                "platform_topic_suffixes.py",
                "topics.py",
                "topics.ts",
                "contract.yaml",
                "handler_contract.yaml",
                "topics.yaml",
                "contract_topic_extractor.py",
                "check_topic_drift.py",
                "topic_constants.py",
                "constants_topic_taxonomy.py",
                "topic_naming_baseline.txt",
                "governance_emitter.py",
            }
        )
        == APPROVED_BASENAMES
    )


@pytest.mark.parametrize(
    ("path", "flagged"),
    [
        ("src/a/test_service.py", False),
        ("src/a/service_test.py", False),
        ("web/a.test.ts", False),
        ("web/a.test.js", False),
        ("/repo/tests/helpers.py", False),
        # pre-commit passes repo-relative paths, and the OCC rule needs a
        # leading slash before ``tests``: a relative tests/ helper is flagged.
        ("tests/helpers.py", True),
        ("src/a/service.py", True),
    ],
)
def test_test_file_rule(path: str, flagged: bool) -> None:
    assert bool(_scan(path, 'T = "onex.cmd.a.b.v1"\n')) is flagged


@pytest.mark.parametrize(
    ("path", "flagged"),
    [
        ("src/pkg/wire_schemas/event_v1.yaml", False),
        ("src/pkg/wire_schemas/event_v12.yml", False),
        ("src/pkg/wire_schemas/event.yaml", True),
        ("src/pkg/other/event_v1.yaml", True),
        ("wire_schemas/event_v1.yaml", True),
    ],
)
def test_wire_schema_contract_skip(path: str, flagged: bool) -> None:
    assert bool(_scan(path, "topic: 'onex.evt.a.b.v1'\n")) is flagged


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ('T = "onex.evt.a.b.v1"\n', 1),
        ("T = 'onex.cmd.a.b.v1'\n", 1),
        ('T = "onex.evt.a.b.v1", "onex.cmd.a.b.v1"\n', 1),
        ('T = "onex.dlq.a.b.v1"\n', 0),
        ("T = onex.evt.a.b.v1\n", 0),
        ('T = "x.onex.evt.a.b.v1"\n', 0),
        ('# T = "onex.evt.a.b.v1"\n', 0),
        ('    // T = "onex.evt.a.b.v1"\n', 0),
        ('"""\nT = "onex.evt.a.b.v1"\n"""\n', 0),
        ("'''\nT = 'onex.evt.a.b.v1'\n'''\n", 0),
        ('"""doc"""\nT = "onex.evt.a.b.v1"\n', 1),
        ('/*\n T = "onex.evt.a.b.v1"\n*/\n', 0),
        ('/* T = "onex.evt.a.b.v1" */\nX = 1\n', 0),
        ('/* a */ T = "onex.evt.a.b.v1"\n', 0),
        ('/*\n * c\n */\nT = "onex.evt.a.b.v1"\n', 1),
        ('T = "onex.evt.a.b.v1"\nU = "onex.cmd.a.b.v1"\n', 2),
    ],
)
def test_line_rules(source: str, count: int) -> None:
    assert len(_scan("src/service.py", source)) == count


def test_non_utf8_bytes_are_replaced_not_fatal(tmp_path: Path) -> None:
    target = tmp_path / "service.py"
    target.write_bytes(b'T = "onex.evt.a.b.v1"  # \xff\xfe\n')
    assert main([str(target)]) == 1


def test_main_prints_the_occ_lines_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "service.py"
    target.write_text('T = "onex.evt.a.b.v1"\n', encoding="utf-8")
    assert main([str(target)]) == 1
    assert capsys.readouterr().out == (
        f"{target}:1: {MESSAGE}\n\n"
        "1 violation(s). Move topic strings to an approved constant file.\n"
    )


def test_main_is_silent_and_zero_on_a_clean_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "service.py"
    target.write_text("X = 1\n", encoding="utf-8")
    assert main([str(target)]) == 0
    assert capsys.readouterr().out == ""


def test_main_with_no_files_is_zero() -> None:
    assert main([]) == 0


def test_an_unreadable_named_file_is_an_error_not_a_pass(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.py")]) == 1


# --- rule data: every parameter of every rule row is read, and a change flips a verdict ---

ROOT = Path(__file__).resolve().parents[3]
NODE_DIR = (
    ROOT / "src" / "omnibase_core" / "nodes" / "node_no_hardcoded_topics_check_compute"
)
LITERAL_SOURCE = 'T = "onex.evt.a.b.v1"\n'


def _contract_rows() -> dict[str, dict[str, object]]:
    return {
        rule.rule_id: dict(rule.parameters or {})
        for rule in ValidatorNoHardcodedTopics().contract.rules
    }


def _mutated(rule_id: str, key: str, value: object) -> ModelNoHardcodedTopicsRules:
    contract = ValidatorNoHardcodedTopics().contract
    rows = [
        r.model_copy(update={"parameters": {**(r.parameters or {}), key: value}})
        if r.rule_id == rule_id
        else r
        for r in contract.rules
    ]
    return load_rules(contract.model_copy(update={"rules": rows}))


# (rule_id, key): (new value, path, source, flagged before, flagged after)
CONTROLS: dict[tuple[str, str], tuple[object, str, str, bool, bool]] = {
    ("topic_literal", "validator_name"): (
        "other-id",
        "src/a.py",
        LITERAL_SOURCE,
        True,
        True,
    ),
    ("topic_literal", "topic_literal_pattern"): (
        "(?!)",
        "src/a.py",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("topic_literal", "message"): ("changed", "src/a.py", LITERAL_SOURCE, True, True),
    ("topic_literal", "remediation"): (
        "changed",
        "src/a.py",
        LITERAL_SOURCE,
        True,
        True,
    ),
    ("exempt_path", "approved_basenames"): (
        ["service.py"],
        "src/service.py",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "test_dir_marker"): (
        "/src/",
        "/repo/src/a.py",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "test_name_prefix"): (
        "svc_",
        "src/svc_a.py",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "test_name_suffixes"): (
        ["_svc.py"],
        "src/a_svc.py",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "wire_schema_dir"): (
        "schemas",
        "src/pkg/schemas/event_v1.yaml",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "wire_schema_name_pattern"): (
        r"event\.yaml",
        "src/pkg/wire_schemas/event.yaml",
        LITERAL_SOURCE,
        True,
        False,
    ),
    ("exempt_path", "wire_schema_min_parts"): (
        9,
        "src/pkg/wire_schemas/event_v1.yaml",
        LITERAL_SOURCE,
        False,
        True,
    ),
    ("skip_line", "comment_prefixes"): (
        ["%"],
        "src/a.py",
        "% " + LITERAL_SOURCE,
        True,
        False,
    ),
    ("skip_line", "block_comment_open"): (
        "<!--",
        "src/a.py",
        "<!--\n" + LITERAL_SOURCE + "*/\n",
        True,
        False,
    ),
    ("skip_line", "block_comment_close"): (
        "-->",
        "src/a.py",
        "/*\n-->\n" + LITERAL_SOURCE,
        False,
        True,
    ),
    ("skip_line", "docstring_delimiters"): (
        ["'''"],
        "src/a.py",
        '"""\n' + LITERAL_SOURCE + '"""\n',
        False,
        True,
    ),
}


def test_every_parameter_of_every_rule_row_has_a_control() -> None:
    assert {
        (rule_id, key) for rule_id, row in _contract_rows().items() for key in row
    } == set(CONTROLS)


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(rule_id: str, key: str) -> None:
    value, path, source, before, after = CONTROLS[(rule_id, key)]
    assert bool(_scan(path, source)) is before
    mutated = _mutated(rule_id, key, value)
    assert bool(_scan(path, source, mutated)) is after
    if key == "validator_name":
        report = HandlerNoHardcodedTopics().handle(
            ModelNoHardcodedTopicsCheckInput(
                files=[ModelSourceFile(path=path, source=source)], rules=mutated
            )
        )
        assert report.findings[0].rule_id == "other-id"
    if key == "message":
        assert _scan(path, source, mutated) == [f"{path}:1: changed"]


def test_remediation_parameter_is_the_summary_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _rules().remediation == "Move topic strings to an approved constant file."
    target = tmp_path / "service.py"
    target.write_text(LITERAL_SOURCE, encoding="utf-8")
    assert main([str(target)]) == 1
    assert capsys.readouterr().out.endswith(f"1 violation(s). {_rules().remediation}\n")


@pytest.mark.parametrize(
    ("rule_id", "key"),
    sorted((rule_id, key) for rule_id, row in _contract_rows().items() for key in row),
)
def test_a_missing_parameter_fails_the_load_instead_of_passing(
    rule_id: str, key: str
) -> None:
    contract = ValidatorNoHardcodedTopics().contract
    rows = [
        r.model_copy(
            update={
                "parameters": {
                    k: v for k, v in (r.parameters or {}).items() if k != key
                }
            }
        )
        if r.rule_id == rule_id
        else r
        for r in contract.rules
    ]
    with pytest.raises(ModelOnexError, match="parameters"):
        load_rules(contract.model_copy(update={"rules": rows}))


@pytest.mark.parametrize("rule_id", ["topic_literal", "exempt_path", "skip_line"])
def test_a_disabled_or_missing_rule_row_fails_the_load(rule_id: str) -> None:
    contract = ValidatorNoHardcodedTopics().contract
    disabled = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    with pytest.raises(ModelOnexError, match="rule row"):
        load_rules(contract.model_copy(update={"rules": disabled}))
    absent = [r for r in contract.rules if r.rule_id != rule_id]
    with pytest.raises(ModelOnexError, match="rule row"):
        load_rules(contract.model_copy(update={"rules": absent}))


def test_node_contract_binds_the_handler() -> None:
    contract = yaml.safe_load((NODE_DIR / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["name"] == "node_no_hardcoded_topics_check_compute"
    assert contract["node_type"] == "compute"
    module_name, _, class_name = contract["handler_routing"][
        "default_handler"
    ].partition(":")
    assert (NODE_DIR / f"{module_name}.py").is_file()
    module = importlib.import_module(
        f"omnibase_core.nodes.node_no_hardcoded_topics_check_compute.{module_name}"
    )
    assert getattr(module, class_name) is HandlerNoHardcodedTopics
    for field in ("input_model", "output_model"):
        path, _, name = contract[field].rpartition(".")
        assert hasattr(importlib.import_module(path), name)
