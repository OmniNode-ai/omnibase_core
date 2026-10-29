# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the action-pin check handler (OMN-17427).

Third-party ``uses:`` refs must be a full 40-hex commit sha. First-party refs
(the organisations the overlay names) must be a dev-merge tag matching the
overlay's tag pattern; a first-party sha is a finding unless the overlay lists
that exact value as a known exception with a reason. Fixture text is assembled
from ``_ORG`` so this file holds no literal first-party reference.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.action_pins import (
    ModelActionPinCheckInput,
    ModelActionPinKnownException,
    ModelActionPinOverlay,
    ModelActionPinRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_action_pin_check_effect import matcher_action_pin
from omnibase_core.nodes.node_action_pin_check_effect.handler_action_pin import (
    HandlerActionPin,
)
from omnibase_core.nodes.node_action_pin_check_effect.runtime_action_pin_check import (
    load_rules,
)
from omnibase_core.validation.checker_action_pin import action_pin_rules
from omnibase_core.validation.validator_action_pin import ValidatorActionPin

pytestmark = pytest.mark.unit

_ORG = "OmniNode-ai"
_SHA = "a1b2" * 10
_TAG = "dev-20261018024445-b6ee996befa1"
_TAG_PATTERN = r"dev-\d{14}-[0-9a-f]{12}"
_FIRST = f"{_ORG}/omnibase_core/.github/workflows/zone-filter.yml"
_OTHER_FIRST = f"{_ORG}/omniclaude/.github/workflows/kb-gate.yml"
_PATH = ".github/workflows/ci.yml"
_RULES = load_rules()


def extract_uses(source: str) -> tuple[tuple[int, str], ...]:
    return matcher_action_pin.extract_uses(source, _RULES)


def is_candidate(path: str) -> bool:
    return matcher_action_pin.is_candidate(path, _RULES)


def _overlay(
    *,
    main: Literal["fail", "warn"] = "fail",
    exceptions: tuple[ModelActionPinKnownException, ...] = (),
) -> ModelActionPinOverlay:
    return ModelActionPinOverlay(
        first_party_orgs=(_ORG,),
        tag_pattern=_TAG_PATTERN,
        first_party_main=main,
        known_exceptions=exceptions,
    )


def _check(
    *uses: str,
    overlay: ModelActionPinOverlay | None = None,
    stale: bool = False,
    path: str = _PATH,
) -> ModelValidationReport:
    body = "jobs:\n  a:\n    steps:\n" + "".join(f"      - uses: {u}\n" for u in uses)
    return HandlerActionPin().handle(
        ModelActionPinCheckInput(
            rules=_RULES,
            overlay=overlay or _overlay(),
            files=(ModelSourceFile(path=path, source=body),),
            report_stale_exceptions=stale,
        )
    )


def _severities(report: ModelValidationReport) -> list[str]:
    return [f.severity for f in report.findings]


class TestThirdParty:
    def test_full_sha_passes(self) -> None:
        report = _check(f"actions/checkout@{_SHA}")
        assert report.overall_status == "PASS"
        assert report.findings == ()

    def test_uppercase_sha_passes(self) -> None:
        assert _check(f"actions/checkout@{_SHA.upper()}").overall_status == "PASS"

    @pytest.mark.parametrize(
        "ref",
        ["v4", "main", "0.34.0", _SHA[:39], _SHA[:7], _SHA + "0", _TAG],
    )
    def test_anything_but_a_full_sha_fails(self, ref: str) -> None:
        report = _check(f"actions/checkout@{ref}")
        assert report.overall_status == "FAIL"
        assert _severities(report) == ["FAIL"]
        assert "40-hex" in report.findings[0].message

    def test_no_ref_fails(self) -> None:
        assert _check("docker://alpine:3.20").overall_status == "FAIL"

    def test_org_lookalike_is_third_party(self) -> None:
        assert _check(f"{_ORG}-evil/x@{_SHA}").overall_status == "PASS"
        assert _check(f"{_ORG}-evil/x@{_TAG}").overall_status == "FAIL"

    def test_local_action_passes(self) -> None:
        assert _check("./.github/actions/local").overall_status == "PASS"


class TestFirstParty:
    def test_dev_tag_passes(self) -> None:
        report = _check(f"{_FIRST}@{_TAG}")
        assert report.overall_status == "PASS"
        assert report.findings == ()

    def test_sha_fails_and_names_the_tag_rule(self) -> None:
        report = _check(f"{_FIRST}@{_SHA}")
        assert report.overall_status == "FAIL"
        assert "dev-merge tag" in report.findings[0].message
        assert _TAG_PATTERN in report.findings[0].message

    @pytest.mark.parametrize(
        "ref", ["v1", "dev", "dev-2026-b6ee996befa1", f"{_TAG}x", f"x{_TAG}", "HEAD"]
    )
    def test_other_refs_fail(self, ref: str) -> None:
        assert _check(f"{_FIRST}@{ref}").overall_status == "FAIL"

    def test_org_match_ignores_case(self) -> None:
        assert _check(f"{_ORG.lower()}/x/y.yml@{_SHA}").overall_status == "FAIL"
        assert _check(f"{_ORG.lower()}/x/y.yml@{_TAG}").overall_status == "PASS"

    def test_main_fails_by_default(self) -> None:
        assert _check(f"{_FIRST}@main").overall_status == "FAIL"

    def test_main_warns_when_the_overlay_keeps_it(self) -> None:
        report = _check(f"{_FIRST}@main", overlay=_overlay(main="warn"))
        assert report.overall_status == "WARN"
        assert "remove" in report.findings[0].message

    def test_third_party_main_still_fails_under_warn(self) -> None:
        report = _check("third/party@main", overlay=_overlay(main="warn"))
        assert report.overall_status == "FAIL"


class TestKnownExceptions:
    _EXC = ModelActionPinKnownException(
        uses=f"{_OTHER_FIRST}@{_SHA}", reason="no dev-merge tag exists for this commit"
    )

    def test_listed_sha_warns_with_the_reason(self) -> None:
        report = _check(
            f"{_OTHER_FIRST}@{_SHA}", overlay=_overlay(exceptions=(self._EXC,))
        )
        assert report.overall_status == "WARN"
        assert "no dev-merge tag exists" in report.findings[0].message

    def test_moved_sha_is_not_admitted(self) -> None:
        moved = "f" * 40
        report = _check(
            f"{_OTHER_FIRST}@{moved}", overlay=_overlay(exceptions=(self._EXC,))
        )
        assert report.overall_status == "FAIL"

    def test_exception_does_not_admit_another_action(self) -> None:
        report = _check(f"{_FIRST}@{_SHA}", overlay=_overlay(exceptions=(self._EXC,)))
        assert report.overall_status == "FAIL"

    def test_exception_never_admits_a_third_party_tag(self) -> None:
        exc = ModelActionPinKnownException(
            uses="actions/checkout@v4", reason="a third party is never excepted"
        )
        assert (
            _check(
                "actions/checkout@v4", overlay=_overlay(exceptions=(exc,))
            ).overall_status
            == "FAIL"
        )

    def test_unused_exception_warns_on_a_full_scan_only(self) -> None:
        overlay = _overlay(exceptions=(self._EXC,))
        full = _check(f"{_FIRST}@{_TAG}", overlay=overlay, stale=True)
        assert full.overall_status == "WARN"
        assert "no longer used" in full.findings[0].message
        assert _check(f"{_FIRST}@{_TAG}", overlay=overlay).overall_status == "PASS"

    def test_reason_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionPinKnownException(uses=f"{_FIRST}@{_SHA}", reason="")


class TestOverlay:
    def test_bad_tag_pattern_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionPinOverlay(first_party_orgs=(_ORG,), tag_pattern="(")

    def test_no_first_party_org_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionPinOverlay(first_party_orgs=(), tag_pattern=_TAG_PATTERN)

    def test_unknown_field_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionPinOverlay.model_validate(
                {"first_party_orgs": [_ORG], "tag_pattern": "x", "baseline": []}
            )


class TestReviewFindings:
    """Bypasses a hostile review found; each input must be a finding."""

    def test_hash_inside_a_ref_is_part_of_the_ref(self) -> None:
        third = _check(f"actions/checkout@{_SHA}#branch")
        assert third.overall_status == "FAIL"
        assert _check(f"{_FIRST}@{_TAG}#branch").overall_status == "FAIL"

    def test_hash_after_whitespace_is_a_comment(self) -> None:
        assert _check(f"actions/checkout@{_SHA} # v4").overall_status == "PASS"

    def test_quoted_key_is_read(self) -> None:
        assert extract_uses('      - "uses": actions/checkout@v4\n') == (
            (1, "actions/checkout@v4"),
        )

    def test_flow_mapping_is_read(self) -> None:
        assert extract_uses("      - {uses: x/y@main, with: {a: b}}\n") == (
            (1, "x/y@main"),
        )
        assert extract_uses("      - { 'uses': 'x/y@v1' }\n") == ((1, "x/y@v1"),)

    def test_greedy_tag_pattern_never_admits_a_sha_or_main(self) -> None:
        greedy = ModelActionPinOverlay(first_party_orgs=(_ORG,), tag_pattern=".*")
        assert _check(f"{_FIRST}@{_SHA}", overlay=greedy).overall_status == "FAIL"
        assert _check(f"{_FIRST}@main", overlay=greedy).overall_status == "FAIL"

    def test_whitespace_reason_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ModelActionPinKnownException(uses=f"{_FIRST}@{_SHA}", reason=" " * 12)


class TestScanning:
    def test_location_names_file_and_line(self) -> None:
        report = _check("actions/checkout@v4")
        assert report.findings[0].location == f"{_PATH}:4"

    def test_one_finding_per_use(self) -> None:
        report = _check("a/b@v1", f"actions/checkout@{_SHA}", "c/d@v2")
        assert _severities(report) == ["FAIL", "FAIL"]

    def test_quoted_value_and_trailing_comment(self) -> None:
        source = f'jobs:\n  a:\n    steps:\n      - uses: "x/y@{_SHA}"  # v1\n'
        assert extract_uses(source) == ((4, f"x/y@{_SHA}"),)

    def test_commented_out_use_is_ignored(self) -> None:
        assert extract_uses("# uses: a/b@v1\n  # - uses: c/d@v1\n") == ()

    def test_job_level_uses_is_read(self) -> None:
        assert extract_uses(f"jobs:\n  j:\n    uses: {_FIRST}@{_TAG}\n") == (
            (3, f"{_FIRST}@{_TAG}"),
        )

    def test_only_workflow_files_are_candidates(self) -> None:
        assert is_candidate(".github/workflows/ci.yml")
        assert is_candidate(".github/workflows/ci.yaml")
        assert not is_candidate(".github/workflows/sub/ci.yml")
        assert not is_candidate("src/ci.yml")
        assert not is_candidate(".github/workflows/readme.md")

    def test_non_candidate_file_is_not_judged(self) -> None:
        assert _check("a/b@v1", path="docs/ci.yml").overall_status == "PASS"

    def test_report_names_the_validator(self) -> None:
        report = _check("a/b@v1")
        assert report.findings[0].validator_id == "action-pins"
        assert report.findings[0].remediation


_CONTRACT = Path(matcher_action_pin.__file__).parent / "contract.yaml"
_SHA_ONLY_7 = "[0-9a-f]{7}"
_NO_MATCH = "^(?!)"


def _block(*uses: str) -> str:
    return "jobs:\n  a:\n    steps:\n" + "".join(f"      - uses: {u}\n" for u in uses)


def _mutated_rules(rule_id: str, key: str, value: object) -> ModelActionPinRules:
    rows = {r.rule_id: r for r in ValidatorActionPin().contract.rules}
    row = rows[rule_id]
    rows[rule_id] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return action_pin_rules(rows)


def _projection(
    rules: ModelActionPinRules,
    source: str,
    *,
    overlay: ModelActionPinOverlay,
    path: str = _PATH,
    stale: bool = False,
) -> tuple[object, ...]:
    report = HandlerActionPin().handle(
        ModelActionPinCheckInput(
            rules=rules,
            overlay=overlay,
            files=(ModelSourceFile(path=path, source=source),),
            report_stale_exceptions=stale,
        )
    )
    return (
        report.overall_status,
        tuple(
            (f.validator_id, f.severity, f.message, f.remediation)
            for f in report.findings
        ),
    )


_EXCEPTION = ModelActionPinKnownException(
    uses=f"{_OTHER_FIRST}@{_SHA}", reason="no dev-merge tag exists for this commit"
)
_THIRD = _block("actions/checkout@v4")
_FIRST_SHA = _block(f"{_FIRST}@{_SHA}")
_FIRST_MAIN = _block(f"{_FIRST}@main")
_EXC_USED = _block(f"{_OTHER_FIRST}@{_SHA}")
_FIRST_TAG = _block(f"{_FIRST}@{_TAG}")
_FLOW = "      - {uses: actions/checkout@v4}\n"
_MUT = "mutated {location}"

# (rule id, parameter key, mutated value, workflow source, overlay, file path, stale flag)
_PARAMETER_CASES = [
    ("uses_extraction", "report_validator_name", "other-id", _THIRD, _overlay(), _PATH, False),
    ("uses_extraction", "workflow_dir", "ci", _THIRD, _overlay(), _PATH, False),
    ("uses_extraction", "workflow_suffixes", [".yml"], _THIRD, _overlay(), ".github/workflows/ci.yaml", False),
    ("uses_extraction", "local_prefixes", ["zz"], _block("./.github/actions/local"), _overlay(), _PATH, False),
    ("uses_extraction", "block_uses_pattern", _NO_MATCH, _THIRD, _overlay(), _PATH, False),
    ("uses_extraction", "flow_uses_pattern", _NO_MATCH, _FLOW, _overlay(), _PATH, False),
    ("third_party_not_sha", "full_sha_pattern", _SHA_ONLY_7, _block(f"actions/checkout@{_SHA}"), _overlay(), _PATH, False),
    ("third_party_not_sha", "message_template", _MUT, _THIRD, _overlay(), _PATH, False),
    ("third_party_not_sha", "remediation", "mutated remediation", _THIRD, _overlay(), _PATH, False),
    ("first_party_not_tag", "message_template", _MUT, _FIRST_SHA, _overlay(), _PATH, False),
    ("first_party_not_tag", "remediation", "mutated remediation", _FIRST_SHA, _overlay(), _PATH, False),
    ("first_party_not_tag", "main_ref", "trunk", _FIRST_MAIN, _overlay(main="warn"), _PATH, False),
    ("first_party_main_allowance", "message_template", _MUT, _FIRST_MAIN, _overlay(main="warn"), _PATH, False),
    ("known_exception_used", "message_template", _MUT, _EXC_USED, _overlay(exceptions=(_EXCEPTION,)), _PATH, False),
    ("known_exception_stale", "message_template", "mutated {uses}", _FIRST_TAG, _overlay(exceptions=(_EXCEPTION,)), _PATH, True),
]  # fmt: skip


class TestContractRuleData:
    def test_contract_binds_the_handler(self) -> None:
        routing = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))[
            "handler_routing"
        ]
        module, _, name = routing["default_handler"].partition(":")
        assert module == "handler_action_pin"
        assert name == HandlerActionPin.__name__
        assert (_CONTRACT.parent / f"{module}.py").is_file()

    def test_every_contract_parameter_is_covered_by_a_mutation_case(self) -> None:
        declared = {
            (row.rule_id, key)
            for row in ValidatorActionPin().contract.rules
            for key in (row.parameters or {})
        }
        assert declared == {(case[0], case[1]) for case in _PARAMETER_CASES}

    @pytest.mark.parametrize(
        ("rule_id", "key", "value", "source", "overlay", "path", "stale"),
        _PARAMETER_CASES,
        ids=[f"{case[0]}.{case[1]}" for case in _PARAMETER_CASES],
    )
    def test_mutating_a_parameter_changes_the_verdict(
        self,
        rule_id: str,
        key: str,
        value: object,
        source: str,
        overlay: ModelActionPinOverlay,
        path: str,
        stale: bool,
    ) -> None:
        base = _projection(_RULES, source, overlay=overlay, path=path, stale=stale)
        changed = _projection(
            _mutated_rules(rule_id, key, value),
            source,
            overlay=overlay,
            path=path,
            stale=stale,
        )
        assert changed != base

    def test_missing_parameter_fails_the_contract_load(self) -> None:
        rows = {r.rule_id: r for r in ValidatorActionPin().contract.rules}
        row = rows["third_party_not_sha"]
        rows["third_party_not_sha"] = row.model_copy(update={"parameters": {}})
        with pytest.raises(ModelOnexError):
            action_pin_rules(rows)
