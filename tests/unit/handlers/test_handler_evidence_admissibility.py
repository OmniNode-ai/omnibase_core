# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-15309 — the single admissibility predicate, proven by execution.

Ported from onex_change_control (6adc28168d023d027bf9c1172f262ac03c9d9055) for
OMN-17427; the runner demotion tests (_demote, _has_effective_check) stay
with the runner, which is not ported.

Every assertion here RUNS the predicate against a real check_value and asserts
the verdict. None of them assert intent: there is no test that reads a comment,
counts a regex, or checks that a constant is spelled a certain way.

The corpus lives in ``tests/fixtures/occ_contract_checks_parity/evidence_admissibility_cases.yaml.txt`` and is
shared with the ``predicate-parity`` CI step, which runs the SAME file against
omniclaude's ``classify_check_value`` (OMN-14505). That is what holds the two
implementations to one definition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.handlers.handler_contract_compliance_check import (
    is_inert_check as _is_inert_check,
)
from omnibase_core.handlers.handler_evidence_admissibility import (
    EXECUTED_HERMETIC_COMMANDS,
    LIVE_PROBE_COMMANDS,
    EnumAdmissibilityRule,
    admissible_evidence_guidance,
    classify_evidence,
)

_CASES_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "occ_contract_checks_parity"
    / "evidence_admissibility_cases.yaml.txt"
)
_RUNNER_PROFILE = LIVE_PROBE_COMMANDS | EXECUTED_HERMETIC_COMMANDS


def _load_cases() -> list[dict[str, Any]]:
    raw = yaml.safe_load(_CASES_PATH.read_text(encoding="utf-8"))
    cases = raw["cases"]
    assert isinstance(cases, list), "corpus 'cases' must be a list"
    assert cases, "corpus must be non-empty"
    return cases


CASES = _load_cases()
CASE_IDS = [c["id"] for c in CASES]


def test_corpus_ids_are_unique() -> None:
    assert len(CASE_IDS) == len(set(CASE_IDS)), "duplicate case ids in the corpus"


def test_corpus_is_non_vacuous() -> None:
    """A corpus that only contains rejects (or only accepts) proves nothing.

    Both verdicts must be represented in BOTH profiles, or a predicate that
    hard-codes one answer would pass the whole suite.
    """
    for profile in ("live", "runner"):
        verdicts = {bool(c[profile]) for c in CASES}
        assert verdicts == {True, False}, (
            f"corpus is vacuous for the {profile!r} profile: every case expects "
            f"{verdicts}"
        )


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_runner_profile_verdict(case: dict[str, Any]) -> None:
    """The contract-compliance profile (executes the value)."""
    verdict = classify_evidence(
        case["check_value"],
        admissible_probes=_RUNNER_PROFILE,
        changed_paths=case.get("changed_paths"),
    )
    assert verdict.admissible is bool(case["runner"]), (
        f"{case['id']}: expected runner-profile admissible="
        f"{case['runner']}, got {verdict.admissible} — {verdict.reason}"
    )
    assert verdict.rule is EnumAdmissibilityRule(case["rule"]), (
        f"{case['id']}: expected rule={case['rule']}, got {verdict.rule} — "
        f"{verdict.reason}"
    )


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_live_profile_verdict(case: dict[str, Any]) -> None:
    """The deploy-gate profile (text-only; live surfaces alone)."""
    verdict = classify_evidence(
        case["check_value"],
        admissible_probes=LIVE_PROBE_COMMANDS,
        changed_paths=case.get("changed_paths"),
    )
    assert verdict.admissible is bool(case["live"]), (
        f"{case['id']}: expected live-profile admissible={case['live']}, got "
        f"{verdict.admissible} — {verdict.reason}"
    )


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_compliance_runner_agrees_with_predicate(case: dict[str, Any]) -> None:
    """``_is_inert_check`` is the predicate, not a second copy of it.

    This is the wiring assertion: the compliance runner's INERT decision and the
    shared predicate must be the same function applied to the same input. If
    someone reintroduces a local regex list in contract_compliance_check.py,
    this test goes RED.
    """
    changed = case.get("changed_paths")
    inert = _is_inert_check(
        case["check_value"], frozenset(changed) if changed else None
    )
    assert inert is not bool(case["runner"]), (
        f"{case['id']}: compliance runner says inert={inert} but the shared "
        f"predicate says admissible={case['runner']}"
    )


# ---------------------------------------------------------------------------
# The OMN-15309 contradiction: the prescribed shape must not be a demoted shape
# ---------------------------------------------------------------------------

#: The exact string contract_compliance_check.py used to prescribe at lines
#: 111-116 while _INERT_CHECK_PATTERNS unconditionally demoted it.
_FORMERLY_PRESCRIBED = (
    "grep -q '^status: PASS$' "
    '"$CONTRACT_REPO_DIR/drift/dod_receipts/OMN-15309/dod-deploy/command.yaml"'
)


def test_formerly_prescribed_shape_is_refused_and_no_longer_prescribed() -> None:
    """OMN-15309 AC1: no shape this file recommends is refused by this file.

    Two halves, both executed:
      (a) the old prescribed shape is REFUSED by the predicate, and
      (b) the file no longer prescribes it — the author-facing guidance names it
          under REFUSED, and the guidance text contains at least one shape the
          predicate ADMITS.
    """
    verdict = classify_evidence(_FORMERLY_PRESCRIBED, admissible_probes=_RUNNER_PROFILE)
    assert verdict.admissible is False
    assert verdict.rule is EnumAdmissibilityRule.INSIDE_OWN_DIFF

    guidance = admissible_evidence_guidance("OmniNode-ai/omnibase_core")
    assert "REFUSED" in guidance
    assert "drift/dod_receipts" in guidance.split("REFUSED", 1)[1], (
        "the receipt-grep shape must appear under REFUSED, not as a recommendation"
    )

    # AC1 proper: every shape the guidance recommends must be ADMISSIBLE.
    recommended = guidance.split("REFUSED", 1)[0]
    recommended_shapes = [
        line.strip()
        for line in recommended.splitlines()
        if line.startswith("    ") and line.strip()
    ]
    assert recommended_shapes, "guidance must recommend at least one shape"
    for shape in recommended_shapes:
        shape_verdict = classify_evidence(shape, admissible_probes=_RUNNER_PROFILE)
        assert shape_verdict.admissible is True, (
            f"guidance recommends a shape the predicate refuses: {shape!r} — "
            f"{shape_verdict.reason}"
        )


def test_guidance_refused_examples_are_actually_refused() -> None:
    """The REFUSED examples must be refused, or the guidance is lying."""
    refused_examples = [
        "grep -q '^status: PASS$' drift/dod_receipts/OMN-15309/dod-deploy/command.yaml",
        "test -f src/path/added_by_this_pr.py",
        "gh api repos/OWNER/REPO/pulls/1927 --jq .merged",
        "echo 'docker exec omninode-runtime true'",
    ]
    for value in refused_examples:
        verdict = classify_evidence(value, admissible_probes=_RUNNER_PROFILE)
        assert verdict.admissible is False, (
            f"guidance calls {value!r} REFUSED but the predicate admits it: "
            f"{verdict.reason}"
        )


# ---------------------------------------------------------------------------
# Fail-closed properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "",
        "   ",
        # unbalanced quote — shlex raises, and the predicate must NOT fall back
        # to "looks like it has docker in it"
        "docker exec 'unterminated",
    ],
)
def test_fails_closed(value: object) -> None:
    verdict = classify_evidence(value, admissible_probes=_RUNNER_PROFILE)
    assert verdict.admissible is False


# ---------------------------------------------------------------------------
# The demotion machinery: an inadmissible PASS must never survive as a PASS
# ---------------------------------------------------------------------------
