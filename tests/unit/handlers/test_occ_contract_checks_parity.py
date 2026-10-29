# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Parity of the ported contract checks with their onex_change_control originals.

OMN-17427. ``handler_contract_check_values_lint``,
``handler_contract_substance_floor`` and ``handler_contract_compliance_check``
are ports of three onex_change_control gate scripts. The verdicts in
``tests/fixtures/occ_contract_checks_parity/parity_corpus.json`` were recorded by running the
ORIGINALS (onex_change_control at 6adc28168d023d027bf9c1172f262ac03c9d9055) over
a stratified sample of that commit's real contracts, its admissibility case
corpus and synthetic cases. This test runs the ports over the same inputs and
requires identical answers.

The verdicts are recorded rather than computed live so the test runs on every
runner: a live comparison would need an onex_change_control checkout, and a test
that skips where the checkout is absent is not a check.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_check_values_lint import (
    lint_contract,
    lint_contract_warnings,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_compliance_check import (
    is_inert_check,
    non_hermetic_reason,
    substitute_tokens,
    validate_substitution_context,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_substance_floor import (
    derive_proof_tier,
    evaluate_contract,
)

pytestmark = pytest.mark.unit

_FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "occ_contract_checks_parity"
)
_PR, _REPO, _TICKET = 321, "OmniNode-ai/omnimarket", "OMN-9999"


class _Case(TypedDict):
    check_type: str
    check_value: str
    changed_paths: list[str] | None
    occ: dict[str, object]


class _File(TypedDict):
    text: str
    occ: dict[str, object]


def _load_corpus() -> tuple[list[_Case], dict[str, _File]]:
    loaded = json.loads((_FIXTURES / "parity_corpus.json").read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    assert isinstance(loaded["cases"], list)
    assert isinstance(loaded["files"], dict)
    return cast("list[_Case]", loaded["cases"]), cast(
        "dict[str, _File]", loaded["files"]
    )


_CASES, _FILES = _load_corpus()


def test_the_corpus_is_not_vacuous() -> None:
    """Every verdict class the originals produce is represented."""
    tiers = {c["occ"]["proof_tier"] for c in _CASES}
    assert {"L0", "L1", "L2"} <= tiers, tiers
    assert {c["occ"]["inert"] for c in _CASES} == {True, False}
    assert any(c["occ"]["non_hermetic"] for c in _CASES)
    assert any(c["occ"]["substitution_error_bad_context"] for c in _CASES)
    assert any(c["occ"]["substituted"] != c["check_value"] for c in _CASES)
    assert len(_CASES) >= 900
    verdicts = [v["occ"] for v in _FILES.values()]
    assert sum(1 for v in verdicts if v["lint"]) >= 10
    assert sum(1 for v in verdicts if v["warnings"]) >= 1
    assert sum(1 for v in verdicts if not v["floor_passed"]) >= 1
    assert sum(1 for v in verdicts if not v["lint"]) >= 10


def _case_id(case: _Case) -> str:
    return f"{case['check_type']}:{case['check_value'][:60]}"


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_check_value_verdicts_match_the_original(case: _Case) -> None:
    check_type = case["check_type"]
    value = case["check_value"]
    changed = case["changed_paths"]
    expected = case["occ"]
    changed_paths = frozenset(changed) if changed is not None else None
    actual = {
        "proof_tier": derive_proof_tier(check_type, value).value,
        "inert": is_inert_check(value, changed_paths, check_type),
        "non_hermetic": non_hermetic_reason(
            {"check_type": check_type, "check_value": value}
        ),
        "substituted": substitute_tokens(value, _PR, _REPO, _TICKET),
        "substitution_error": validate_substitution_context(value, _PR, _REPO, _TICKET),
        "substitution_error_bad_context": validate_substitution_context(
            value, 0, "not a repo; rm", "OMN-x"
        ),
    }
    assert actual == expected


@pytest.mark.parametrize("name", sorted(_FILES))
def test_contract_file_verdicts_match_the_original(name: str, tmp_path: Path) -> None:
    path = tmp_path / name
    path.write_text(_FILES[name]["text"], encoding="utf-8")
    expected = _FILES[name]["occ"]
    result = evaluate_contract(path)
    actual = {
        "lint": [[label, fragment] for _, label, fragment in lint_contract(path)],
        "warnings": [
            [label, fragment] for _, label, fragment in lint_contract_warnings(path)
        ],
        "floor_ticket_id": result.ticket_id,
        "floor_passed": result.passed,
        "floor_tiers": [[f.dod_item, f.tier.value] for f in result.findings],
    }
    assert actual == expected
