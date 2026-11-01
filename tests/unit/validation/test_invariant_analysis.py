# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Falsifiers for the global invariant-analysis gate (OMN-21565)."""

from __future__ import annotations

import ast
import builtins
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_invariant_analysis import HandlerInvariantAnalysis
from omnibase_core.handlers.handler_invariant_analysis_rules import (
    analyse_document,
    build_registry,
    is_exempt_by_lifecycle,
    parse_overlay,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_rules import (
    ModelInvariantAnalysisRules,
)
from omnibase_core.validation.validator_invariant_analysis import (
    ValidatorInvariantAnalysis,
    build_analysis_container,
)

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/invariant_analysis"
PRODUCTION = Path(__file__).resolve().parents[3] / "src/omnibase_core"
PLANTED = {
    "invariant_unaddressed",
    "satisfied_by_task_absent",
    "not_applicable_unreasoned",
    "invariant_unknown_or_retired",
    "scope_declaration_missing_or_unknown",
}
NEAR_MISSES = {
    "coverage_block_without_marker": True,
    "unknown_scope_tag": True,
    "coverage_names_unknown_id": True,
    "coverage_names_superseded_id": True,
    "marker_without_scopes": True,
    "unbalanced_coverage_markers": True,
    "duplicated_coverage_markers": True,
    "reversed_coverage_markers": True,
    "missing_coverage_block": True,
    "missing_active_invariant": True,
    "marker_in_fenced_block_ignored": False,
    "inline_marker_in_prose_ignored": False,
    "marker_below_header_window_ignored": False,
    "neither_marker_nor_block": False,
    "valid_coverage": False,
}


def contract():
    return ValidatorInvariantAnalysis().contract


def request(
    name="plan_bad.md", *, held=None, text=None, overlay=None, registry_raw=None
):
    held = held or contract()
    rules = ModelInvariantAnalysisRules.from_contract(held)
    return ModelInvariantAnalysisInput(
        path=name,
        text=text if text is not None else (FIXTURES / name).read_text(),
        registry=build_registry(
            registry_raw
            if registry_raw is not None
            else yaml.safe_load((FIXTURES / "registry.yaml").read_text()),
            rules,
        ),
        overlay=parse_overlay(
            overlay
            if overlay is not None
            else yaml.safe_load((FIXTURES / "overlay.yaml").read_text())
        ),
        contract=held,
    )


def findings(req):
    return HandlerInvariantAnalysis(build_analysis_container()).handle(req).findings


def ids(req):
    return {f.rule_id for f in findings(req)}


def workdir(root, name="plan_bad.md"):
    root.mkdir(parents=True, exist_ok=True)
    for file in ("registry.yaml", "lifecycle.yaml", name):
        shutil.copy(FIXTURES / file, root / file)
    shutil.copy(FIXTURES / "overlay.yaml", root / "invariant_analysis.overlay.yaml")
    return root


def changed_contract(rule_id, key=None, value=None, *, enabled=None):
    raw = contract().model_dump(mode="python")
    row = next(r for r in raw["rules"] if r["rule_id"] == rule_id)
    if enabled is not None:
        row["enabled"] = enabled
    else:
        row["parameters"][key] = value
    return ModelValidatorSubcontract.model_validate(raw)


def test_planted_rule_set_and_report():
    req = request()
    report = HandlerInvariantAnalysis(build_analysis_container()).handle(req)
    assert ids(req) == PLANTED
    assert report.overall_status == "ERROR"
    for f in report.findings:
        assert f.severity == "ERROR"
        assert f.location == req.path
        assert f.remediation == next(
            r.parameters["remediation"]
            for r in req.contract.rules
            if r.rule_id == f.rule_id
        )


def test_heading_removed_stops_plan_rules():
    req = request()
    assert ids(
        req.model_copy(update={"text": req.text.replace("## Invariant analysis", "")})
    ) == {"analysis_section_missing"}


def test_clean_plan_and_blocking_contract():
    assert ids(request("plan_clean.md")) == set()
    assert (
        HandlerInvariantAnalysis(build_analysis_container())
        .handle(request("plan_clean.md"))
        .overall_status
        == "PASS"
    )
    assert all(r.severity.value == "error" and r.enabled for r in contract().rules)
    assert contract().max_violations == 0
    assert contract().fail_on_error and not contract().fail_on_warning


@pytest.mark.parametrize(("name", "code"), [("plan_bad.md", 1), ("plan_clean.md", 0)])
def test_validator_exit_and_global_scan(tmp_path, monkeypatch, name, code):
    root = workdir(tmp_path, name)
    monkeypatch.chdir(root)
    validator = ValidatorInvariantAnalysis()
    result = validator.validate([root / name, root / "registry.yaml"])
    assert validator.get_exit_code(result) == code
    assert {i.rule_name for i in result.issues} == (PLANTED if code else set())
    assert all(i.code == i.rule_name for i in result.issues)


def test_registry_change_invalidates_unchanged_clean_plan(tmp_path):
    root = workdir(tmp_path, "plan_clean.md")
    validator = ValidatorInvariantAnalysis()
    assert validator.validate(root).is_valid
    path = root / "registry.yaml"
    raw = yaml.safe_load(path.read_text())
    extra = dict(raw["invariants"][0], id="INV-D")
    raw["invariants"].append(extra)
    path.write_text(yaml.safe_dump(raw))
    assert {i.rule_name for i in validator.validate(root).issues} == {
        "invariant_unaddressed"
    }


@pytest.mark.parametrize("case", NEAR_MISSES, ids=list(NEAR_MISSES))
def test_near_miss_authority_coverage(case):
    assert ids(request(f"near_miss_{case}.md")) == (
        {"authority_doc_coverage"} if NEAR_MISSES[case] else set()
    )


@pytest.mark.parametrize(
    "path", sorted(FIXTURES.glob("registry_invalid_*.yaml")), ids=lambda p: p.stem
)
def test_registry_invalid_once_per_run(tmp_path, path):
    root = workdir(tmp_path)
    shutil.copy(path, root / "registry.yaml")
    result = ValidatorInvariantAnalysis().validate(root)
    assert [i.rule_name for i in result.issues] == ["registry_invalid"]


def test_registry_invalid_yaml_syntax_once_per_run(tmp_path):
    root = workdir(tmp_path)
    (root / "registry.yaml").write_text("scopes: [\n")
    result = ValidatorInvariantAnalysis().validate(root)
    assert [i.rule_name for i in result.issues] == ["registry_invalid"]


def test_registry_missing_once_and_overlay_missing_raises(tmp_path):
    root = workdir(tmp_path)
    (root / "registry.yaml").unlink()
    assert [
        i.rule_name for i in ValidatorInvariantAnalysis().validate(root).issues
    ] == ["registry_invalid"]
    (root / "invariant_analysis.overlay.yaml").unlink()
    with pytest.raises(ModelOnexError):
        ValidatorInvariantAnalysis().validate(root)


@pytest.mark.parametrize(
    "defect",
    [
        "absent_rule",
        "absent_parameter",
        "bad_regex",
        "wrong_type",
        "disabled_bad_regex",
    ],
)
def test_configuration_invalid_contract_fails_closed(defect):
    raw = contract().model_dump(mode="python")
    if defect == "absent_rule":
        raw["rules"].pop()
    elif defect == "absent_parameter":
        raw["rules"][0]["parameters"].pop("message")
    elif defect == "wrong_type":
        raw["rules"][0]["parameters"]["heading_pattern"] = 3
    else:
        raw["rules"][0]["parameters"]["heading_pattern"] = "["
        if defect == "disabled_bad_regex":
            raw["rules"][0]["enabled"] = False
    with pytest.raises(ModelOnexError) as caught:
        ModelInvariantAnalysisRules.from_contract(
            ModelValidatorSubcontract.model_validate(raw)
        )
    assert caught.value.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR


# Every key is explicitly exercised; adding a contract key without a probe fails.
PARAMETER_MUTATIONS = {
    "analysis_section_missing": {
        "heading_pattern": "^NEVER$",
        "section_end_pattern": "^Scopes:",
    },
    "scope_declaration_missing_or_unknown": {
        "scopes_pattern": "^NEVER(.*)$",
        "scope_split_pattern": ";",
    },
    "invariant_unaddressed": {},
    "satisfied_by_task_absent": {
        "entry_pattern": "^NEVER(.*)(.*)$",
        "task_split_pattern": ";",
    },
    "not_applicable_unreasoned": {
        "entry_pattern": "^NEVER(.*)(.*)$",
        "trim_pattern": "^.*$",
    },
    "invariant_unknown_or_retired": {"entry_pattern": "^NEVER(.*)$"},
    "registry_invalid": {
        "overlay_filename": "missing.yaml",
        "id_pattern": "^OTHER$",
        "required_fields": ["additional"],
        "required_ruled_fields": ["additional"],
        "valid_statuses": ["other"],
        "active_status": "other",
        "superseded_status": "other",
        "lifecycle_entries_key": "other",
        "lifecycle_path_key": "other",
        "lifecycle_status_key": "other",
    },
    "authority_doc_coverage": {
        "marker_pattern": "^NEVER(.*)$",
        "header_scan_lines": 1,
        "coverage_start": "OTHER_START",
        "coverage_end": "OTHER_END",
        "id_pattern": "\\bOTHER\\b",
        "fence_pattern": "^NEVER$",
        "scope_split_pattern": ";",
        "markdown_glob": "*.txt",
        "scan_exclusions": ["*"],
    },
}


def test_configuration_parameter_inventory():
    assert {r.rule_id for r in contract().rules} == set(PARAMETER_MUTATIONS)
    for row in contract().rules:
        assert set(row.parameters) == {"message", "remediation"} | set(
            PARAMETER_MUTATIONS[row.rule_id]
        )


def configuration_probe(held, rule_id, key, tmp_path):
    """Return observable findings from a corpus designed to exercise every setting."""
    root = workdir(tmp_path)
    clean = (FIXTURES / "plan_clean.md").read_text()
    # Comma tasks, a punctuated long placeholder, and an ended section exercise parsers.
    shutil.copy(FIXTURES / "plan_bad.md", root / "plan_other.md")
    (root / "plan_extra.md").write_text(clean + "\n- INV-Z satisfied-by T1\n")
    (root / "plan_reason.md").write_text(
        clean.replace(
            "This change does not modify data storage.", "...not applicable..."
        )
    )
    for case in NEAR_MISSES:
        shutil.copy(FIXTURES / f"near_miss_{case}.md", root)
    # A marker on line two is inside the default header window.
    (root / "header.md").write_text("# Header\n<!-- authority-doc: architecture -->\n")
    (root / "fenced.md").write_text(
        "```markdown\n<!-- authority-doc: architecture -->\n```\n"
    )
    (root / "multi.md").write_text(
        "<!-- authority-doc: architecture, data -->\n<!-- invariant-coverage:start -->\n- INV-A\n- INV-B\n<!-- invariant-coverage:end -->\n"
    )
    (root / "lifecycle.yaml").write_text(
        "plans:\n  - path: plan_bad.md\n    status: parked\n"
    )
    try:
        result = ValidatorInvariantAnalysis(contract=held).validate(root)
    except ModelOnexError as exc:
        return [("configuration_error", "", exc.error_code)]
    return [(i.rule_name, Path(i.file_path).name, i.message) for i in result.issues]


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [(row.rule_id, key) for row in contract().rules for key in row.parameters],
)
def test_configuration_every_contract_parameter_changes_verdict(tmp_path, rule_id, key):
    old = next(r.parameters[key] for r in contract().rules if r.rule_id == rule_id)
    new = (
        "Changed diagnostic"
        if key in ("message", "remediation")
        else PARAMETER_MUTATIONS[rule_id][key]
    )
    held = changed_contract(rule_id, key, new)
    if key in ("message", "remediation"):
        req = rule_fixture(rule_id)
        before = findings(req)
        after = findings(req.model_copy(update={"contract": held}))
        assert before != after
    else:
        assert configuration_probe(
            contract(), rule_id, key, tmp_path / "before"
        ) != configuration_probe(held, rule_id, key, tmp_path / "after"), (
            rule_id,
            key,
            old,
        )


OVERLAY_MUTATIONS = {
    "registry_path": "missing.yaml",
    "lifecycle_path": "other.yaml",
    "plan_globs": ["absent_*.md"],
    "exempt_lifecycle_statuses": [],
    "always_scopes": [],
    "task_heading_pattern": "^NEVER(T\\d+)$",
    "min_reason_length": 100,
    "denied_placeholders": ["This change does not modify data storage"],
    "skip_dirs": ["."],
}


@pytest.mark.parametrize("key", OVERLAY_MUTATIONS)
def test_configuration_every_overlay_field_changes_verdict(tmp_path, key):
    assert set(OVERLAY_MUTATIONS) == set(type(request().overlay).model_fields)
    root = workdir(tmp_path)
    shutil.copy(FIXTURES / "plan_clean.md", root)
    # Non-exempt bad plan exercises scope policy; exempt second copy exercises lifecycle.
    shutil.copy(FIXTURES / "plan_bad.md", root / "plan_exempt.md")
    (root / "lifecycle.yaml").write_text(
        "plans:\n  - path: plan_exempt.md\n    status: parked\n"
    )
    (root / "other.yaml").write_text("plans: []\n")
    (root / "nested").mkdir()
    shutil.copy(
        FIXTURES / "near_miss_missing_coverage_block.md",
        root / "nested" / "authority.md",
    )
    before = ValidatorInvariantAnalysis().validate(root)
    raw = yaml.safe_load((root / "invariant_analysis.overlay.yaml").read_text())
    if key == "skip_dirs":
        raw[key] = ["nested"]
    else:
        raw[key] = OVERLAY_MUTATIONS[key]
    (root / "invariant_analysis.overlay.yaml").write_text(yaml.safe_dump(raw))
    after = ValidatorInvariantAnalysis().validate(root)
    assert [(i.rule_name, i.file_path, i.message) for i in before.issues] != [
        (i.rule_name, i.file_path, i.message) for i in after.issues
    ]


def test_configuration_source_has_no_policy_literals():
    forbidden = {
        "registry.yaml",
        "plan_*.md",
        "architecture",
        "data",
        "process",
        "n/a",
        "todo",
        "not applicable",
        "Invariant analysis",
    }
    for path in production_files():
        tree = ast.parse(path.read_text())
        assert not [
            (node.lineno, node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in forbidden
        ], path


def production_files():
    return [
        *PRODUCTION.glob("models/invariant_analysis/*.py"),
        *PRODUCTION.glob("handlers/handler_invariant_analysis*.py"),
        PRODUCTION / "validation/validator_invariant_analysis.py",
        PRODUCTION
        / "nodes/node_validation_report_write_effect/runtime_invariant_analysis.py",
    ]


def rule_fixture(rule_id):
    if rule_id == "analysis_section_missing":
        return request(text="Scopes: architecture")
    if rule_id == "authority_doc_coverage":
        return request("near_miss_missing_coverage_block.md")
    if rule_id == "registry_invalid":
        return request().model_copy(
            update={"registry": None, "registry_error": "broken registry"}
        )
    return request()


@pytest.mark.parametrize("rule_id", PARAMETER_MUTATIONS)
def test_replay_disabled_row_loses_exactly_its_findings(rule_id):
    req = rule_fixture(rule_id)
    before = findings(req)
    after = findings(
        req.model_copy(update={"contract": changed_contract(rule_id, enabled=False)})
    )
    assert any(f.rule_id == rule_id for f in before)
    assert after == tuple(f for f in before if f.rule_id != rule_id)


def test_replay_corpus_names_no_invariant_analysis_assertions():
    """The committed T0.8a corpus currently names none of OMN-21565's rule ids."""
    raw = yaml.safe_load((FIXTURES.parent / "andon_replay/corpus.yaml").read_text())
    named = [
        a
        for a in raw["assertions"]
        if a["rule_id"].split(":")[-1] in PARAMETER_MUTATIONS
    ]
    assert named == []


def test_purity_handler_and_rule_functions():
    req = request()
    raw = yaml.safe_load((FIXTURES / "registry.yaml").read_text())
    overlay = req.overlay.model_dump()
    rules = ModelInvariantAnalysisRules.from_contract(req.contract)
    handler = HandlerInvariantAnalysis(build_analysis_container())

    def forbidden(*args, **kwargs):
        raise AssertionError("pure check attempted I/O")

    environment = MagicMock()
    environment.__getitem__.side_effect = forbidden
    environment.get.side_effect = forbidden
    environment.__iter__.side_effect = forbidden
    with (
        patch.object(builtins, "open", forbidden),
        patch.object(Path, "read_text", forbidden),
        patch.object(Path, "read_bytes", forbidden),
        patch.object(Path, "open", forbidden),
        patch.object(Path, "exists", forbidden),
        patch.object(Path, "is_file", forbidden),
        patch.object(os, "getenv", forbidden),
        patch.object(os, "environ", environment),
    ):
        assert {f.rule_id for f in handler.handle(req).findings} == PLANTED
        assert analyse_document(req, rules)
        assert build_registry(raw, rules) == req.registry
        assert parse_overlay(overlay) == req.overlay
        assert not is_exempt_by_lifecycle(req.path, {}, req.overlay, rules)


@pytest.mark.parametrize("path", production_files(), ids=lambda p: p.name)
def test_configuration_production_source_has_no_runtime_literals(path):
    """AC7: execute the four required literal scanners against actual source."""
    from omnibase_core.validation.hardcoded_model_config import handler as model_config
    from omnibase_core.validation.hardcoded_model_config.models import (
        ModelHardcodedModelConfigPolicy,
    )
    from omnibase_core.validation.validator_hardcoded_topics import (
        ValidatorHardcodedTopics,
    )
    from omnibase_core.validation.validator_url_authority import scan_source
    from omnibase_core.validators import contract_config_compliance

    source = path.read_text()
    repo_path = "src/omnibase_core/" + path.relative_to(PRODUCTION).as_posix()
    policy = ModelHardcodedModelConfigPolicy.model_validate(
        yaml.safe_load(Path(model_config.__file__).with_name("policy.yaml").read_text())
    )
    assert scan_source("omnibase_core", repo_path, source) == []
    assert model_config.scan(repo_path, source, policy) == []
    assert not ValidatorHardcodedTopics().validate_file(path).issues
    assert contract_config_compliance.validate_file(path) == []


@pytest.mark.parametrize(
    ("name", "globs", "expected"),
    [
        ("plan_bad.md", ("**/plan_*.md",), True),
        ("nested/plan_bad.md", ("plan_*.md",), False),
        ("nested/deeper/plan_bad.md", ("**/plan_*.md",), True),
        (".git/deeper/notes.md", ("**/.git/**",), True),
        ("notes.md", ("**/plan_*.md",), False),
    ],
)
def test_configuration_plan_globs_match_scan_semantics(name, globs, expected):
    from omnibase_core.handlers.handler_invariant_analysis_rules import matches_globs

    assert matches_globs(name, globs) is expected


@pytest.mark.parametrize("key", OVERLAY_MUTATIONS)
def test_configuration_every_overlay_field_is_required(key):
    raw = yaml.safe_load((FIXTURES / "overlay.yaml").read_text())
    del raw[key]
    with pytest.raises(ModelOnexError):
        parse_overlay(raw)


@pytest.mark.parametrize("expression", ["[", "^heading$"])
def test_configuration_overlay_requires_valid_task_capture(expression):
    raw = yaml.safe_load((FIXTURES / "overlay.yaml").read_text())
    raw["task_heading_pattern"] = expression
    with pytest.raises(ModelOnexError):
        parse_overlay(raw)


@pytest.mark.parametrize("disabled", [False, True], ids=["enabled", "disabled"])
@pytest.mark.parametrize("row", contract().rules, ids=lambda row: row.rule_id)
def test_configuration_all_parameters_fail_closed_even_when_disabled(row, disabled):
    for key, value in row.parameters.items():
        for defect in ("missing", "ill_typed"):
            params = dict(row.parameters)
            if defect == "missing":
                del params[key]
            else:
                params[key] = 7 if isinstance(value, (str, list)) else "invalid"
            broken = row.model_copy(
                update={"enabled": not disabled, "parameters": params}
            )
            held = contract().model_copy(
                update={
                    "rules": tuple(
                        broken if r.rule_id == row.rule_id else r
                        for r in contract().rules
                    )
                }
            )
            with pytest.raises(ModelOnexError) as caught:
                ModelInvariantAnalysisRules.from_contract(held)
            assert (
                caught.value.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
            )


def test_registry_change_also_invalidates_unchanged_authority_doc(tmp_path):
    root = workdir(tmp_path, "plan_clean.md")
    shutil.copy(FIXTURES / "near_miss_valid_coverage.md", root / "authority.md")
    validator = ValidatorInvariantAnalysis()
    assert validator.validate(root).is_valid
    raw = yaml.safe_load((root / "registry.yaml").read_text())
    raw["invariants"].append(dict(raw["invariants"][0], id="INV-D"))
    (root / "registry.yaml").write_text(yaml.safe_dump(raw))
    issues = validator.validate(root).issues
    assert {(i.file_path.name, i.rule_name) for i in issues} == {
        ("plan_clean.md", "invariant_unaddressed"),
        ("authority.md", "authority_doc_coverage"),
    }


def test_configuration_skips_directories_and_lifecycle_only_exempts_plans(tmp_path):
    root = workdir(tmp_path, "plan_clean.md")
    for dirname in ("_scratch", "archive", ".git/deeper"):
        folder = root / dirname
        folder.mkdir(parents=True)
        shutil.copy(
            FIXTURES / "near_miss_missing_coverage_block.md", folder / "authority.md"
        )
    shutil.copy(FIXTURES / "plan_bad.md", root / "plan_parked.md")
    shutil.copy(FIXTURES / "near_miss_missing_coverage_block.md", root / "authority.md")
    (root / "lifecycle.yaml").write_text(
        "plans:\n  - path: plan_parked.md\n    status: parked\n  - path: authority.md\n    status: parked\n"
    )
    issues = ValidatorInvariantAnalysis().validate(root).issues
    assert [(i.file_path.name, i.rule_name) for i in issues] == [
        ("authority.md", "authority_doc_coverage")
    ]


def test_configuration_skip_dirs_judge_root_relative_parts_only(tmp_path):
    root = workdir(tmp_path / "archive" / "checkout", "plan_bad.md")
    result = ValidatorInvariantAnalysis().validate(root)
    assert {i.rule_name for i in result.issues} == PLANTED
