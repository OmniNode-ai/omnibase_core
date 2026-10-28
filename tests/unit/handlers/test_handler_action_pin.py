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

from typing import Literal

import pytest
from pydantic import ValidationError

from omnibase_core.handlers.handler_action_pin import HandlerActionPin
from omnibase_core.handlers.handler_action_pin_rules import (
    extract_uses,
    is_candidate,
)
from omnibase_core.models.action_pins import (
    ModelActionPinCheckInput,
    ModelActionPinKnownException,
    ModelActionPinOverlay,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

pytestmark = pytest.mark.unit

_ORG = "OmniNode-ai"
_SHA = "a1b2" * 10
_TAG = "dev-20261018024445-b6ee996befa1"
_TAG_PATTERN = r"dev-\d{14}-[0-9a-f]{12}"
_FIRST = f"{_ORG}/omnibase_core/.github/workflows/zone-filter.yml"
_OTHER_FIRST = f"{_ORG}/omniclaude/.github/workflows/kb-gate.yml"
_PATH = ".github/workflows/ci.yml"


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
