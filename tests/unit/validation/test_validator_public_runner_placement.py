# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""check-public-runner-placement in the generic format (OMN-19998, OMN-21280, OMN-21503).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
The negative controls are the failing cases: a public repository that carries a
self-hosted job fails with no baseline to excuse it, and the same job in a
private repository does not.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)
from omnibase_core.validation import checker_public_runner_placement as checker
from omnibase_core.validation.validator_public_runner_placement import (
    ValidatorPublicCiPlacement,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "validation" / "public_runner_placement"
SELF_HOSTED = "self_hosted_in_public"
UNPARSEABLE = "workflow_does_not_parse"
CI = ".github/workflows/ci.yml"
HOSTED = "ubuntu-latest"
LAB = "[self-hosted, omnibase-ci]"
COMPUTED = '${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || \'["self-hosted","omnibase-ci"]\') }}'
PRIVATE_GUARDED = (
    "${{ github.event.repository.private && ("
    'fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || \'["self-hosted","omnibase-ci"]\')'
    ") || 'ubuntu-latest' }}"
)

# A public repository's workflow: every job but `lint`, `docs` and `routed` is
# or may resolve to a self-hosted runner, and none of them is excused.
FIXTURE_PUBLIC_WORKFLOW = f"""\
name: ci
on: [pull_request, push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: [{{run: echo ok}}]
  docs:
    runs-on: [ubuntu-22.04]
    steps: [{{run: echo ok}}]
  routed:
    runs-on: {PRIVATE_GUARDED}
    steps: [{{run: echo ok}}]
  literal:
    runs-on: self-hosted
    steps: [{{run: echo ok}}]
  labels:
    runs-on: [self-hosted, omnibase-ci]
    steps: [{{run: echo ok}}]
  group:
    runs-on: {{group: lab}}
    steps: [{{run: echo ok}}]
  variable:
    runs-on: >-
      ${{{{
        github.event_name != 'pull_request'
        && fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '["ubuntu-latest"]')
        || fromJSON(vars.OMNI_PUBLIC_PR_RUNS_ON_JSON || '["ubuntu-latest"]')
      }}}}
    steps: [{{run: echo ok}}]
  matrix:
    strategy: {{matrix: {{os: [ubuntu-latest]}}}}
    runs-on: ${{{{ matrix.os }}}}
    steps: [{{run: echo ok}}]
  call:
    uses: OmniNode-ai/omnibase_core/.github/workflows/x.yml@abc
"""
FIXTURE_SELF_HOSTED = ("group", "labels", "literal", "matrix", "variable")


def _contract() -> ModelValidatorSubcontract:
    return ValidatorPublicCiPlacement().contract


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _workflow(**jobs: str) -> str:
    body = "".join(
        f"  {name}:\n    runs-on: {runs_on}\n    steps:\n      - run: echo ok\n"
        for name, runs_on in jobs.items()
    )
    return f"name: ci\non: [pull_request]\njobs:\n{body}"


def _issues(
    source: str,
    tmp_path: Path,
    *,
    public: bool = True,
    contract: ModelValidatorSubcontract | None = None,
) -> list[tuple[str, str]]:
    """(rule_id, job or message) for a workflow written to a throwaway repository."""
    target = tmp_path / "omnibase_infra" / CI
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    validator = ValidatorPublicCiPlacement(
        contract,
        repository="omnibase_infra",
        public=public,
        root=tmp_path / "omnibase_infra",
    )
    return [
        (str(i.code), (i.context or {}).get("job", i.message))
        for i in validator.validate(target).issues
    ]


def _kind(runs_on: object) -> str | None:
    return checker.runs_on_kind(runs_on, _rules()[SELF_HOSTED])


@pytest.mark.parametrize(
    ("runs_on", "kind"),
    [
        ("ubuntu-latest", None),
        ("ubuntu-22.04", None),
        ("windows-latest", None),
        ("macos-14", None),
        (["ubuntu-latest"], None),
        ("self-hosted", "self_hosted_label"),
        ("omnibase-ci", "self_hosted_label"),
        (["self-hosted", "omnibase-ci"], "self_hosted_label"),
        (["ubuntu-latest", "gpu"], "self_hosted_label"),
        ({"group": "lab"}, "self_hosted_label"),
        ({"labels": ["self-hosted"]}, "self_hosted_label"),
        ({"labels": ["ubuntu-latest"]}, None),
        ("${{ 'ubuntu-latest' }}", None),
        (
            "${{ github.event_name == 'push' && 'ubuntu-latest' || 'ubuntu-22.04' }}",
            None,
        ),
        ("${{ fromJSON('[\"ubuntu-latest\"]') }}", None),
        ('${{ fromJSON(\'["ubuntu-latest", "macos-14"]\') }}', None),
        ('${{ fromJSON(\'["ubuntu-latest", "omnibase-ci"]\') }}', "computed"),
        ("${{ fromJSON('[\"\"]') }}", "computed"),
        (COMPUTED, "computed"),
        ("${{ fromJSON(vars.LAB_PROBE_RUNS_ON_JSON) }}", "computed"),
        ("${{ fromJSON(needs.route.outputs.labels) }}", "computed"),
        ("${{ matrix.os }}", "computed"),
        (
            "${{ github.event_name == 'push' && 'my-box' || 'ubuntu-latest' }}",
            "computed",
        ),
        (None, None),
    ],
)
def test_runs_on_kind(runs_on: object, kind: str | None) -> None:
    assert _kind(runs_on) == kind


@pytest.mark.parametrize(
    ("runs_on", "kind"),
    [
        # A public repository can never take the parenthesized branch.
        (PRIVATE_GUARDED, None),
        (
            "${{ github.event.repository.private && (fromJSON(vars.X)) "
            "|| fromJSON('[\"ubuntu-latest\"]') }}",
            None,
        ),
        (
            "${{\n  github.event.repository.private && (\n    (a && b)\n    "
            "|| fromJSON(vars.X || '[\")\"]')\n  ) || 'ubuntu-latest'\n}}",
            None,
        ),
        # Without parentheses an inner `||` would bind outside the guard.
        (
            "${{ github.event.repository.private && vars.A || vars.B "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || (vars.B) "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) && (vars.B) "
            "|| 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || 'omnibase-ci' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A) || vars.B }}",
            "computed",
        ),
        (
            "${{ !github.event.repository.private && (vars.A) || 'ubuntu-latest' }}",
            "computed",
        ),
        (
            "${{ github.event.repository.private && (vars.A || 'ubuntu-latest' }}",
            "computed",
        ),
    ],
)
def test_private_caller_guard_is_proved_hosted_only_in_its_exact_shape(
    runs_on: str, kind: str | None
) -> None:
    assert _kind(runs_on) == kind


@pytest.mark.timeout(2)
@pytest.mark.parametrize(("ending", "kind"), [("", None), ("]", "computed")])
def test_runs_on_json_array_repeated_empty_labels(
    ending: str, kind: str | None
) -> None:
    array = '[""' + ' ""' * 10_000 + ending
    expression = "${{ fromJSON('" + array + "') }}"
    assert _kind(expression) == kind


def test_reusable_workflow_call_has_no_runs_on() -> None:
    source = "on: [pull_request]\njobs:\n  call:\n    uses: OmniNode-ai/omnibase_core/.github/workflows/x.yml@abc\n"
    assert checker.self_hosted_jobs(source, CI, _rules()[SELF_HOSTED]) == {}


def test_hosted_only_public_repository_passes_clean(tmp_path: Path) -> None:
    assert _issues(_workflow(lint=HOSTED, test="windows-latest"), tmp_path) == []


def test_fixture_public_workflow_refuses_every_self_hosted_job(tmp_path: Path) -> None:
    """AC1 (OMN-21280): every job that is or may resolve to self-hosted fails."""
    assert _issues(FIXTURE_PUBLIC_WORKFLOW, tmp_path) == [
        (SELF_HOSTED, job) for job in FIXTURE_SELF_HOSTED
    ]


def test_the_check_has_no_baseline_to_excuse_a_job() -> None:
    """AC1 (OMN-21280): the input carries no baseline, and one passed is refused."""
    assert set(ModelPublicRunnerPlacementInput.model_fields) == {
        "repository",
        "public",
        "files",
    }
    with pytest.raises(ValidationError):
        ModelPublicRunnerPlacementInput.model_validate(
            {"repository": "omnibase_infra", "baseline": [[CI, "literal"]]}
        )


def test_negative_control_self_hosted_job_fails(tmp_path: Path) -> None:
    assert _issues(_workflow(lint=HOSTED, probe=LAB), tmp_path) == [
        (SELF_HOSTED, "probe")
    ]


def test_negative_control_computed_job_fails(tmp_path: Path) -> None:
    assert _issues(_workflow(probe=COMPUTED), tmp_path) == [(SELF_HOSTED, "probe")]


def test_the_same_jobs_in_a_private_repository_pass(tmp_path: Path) -> None:
    assert _issues(FIXTURE_PUBLIC_WORKFLOW, tmp_path, public=False) == []


def test_invalid_workflow_is_an_error(tmp_path: Path) -> None:
    [(rule, message)] = _issues("jobs: [unclosed", tmp_path)
    assert rule == UNPARSEABLE
    assert "does not parse" in message


# --- planted violations, clean twins, every parameter ------------------------

FIXTURE_CASES = {
    SELF_HOSTED: (
        "violation_self_hosted_in_public.yml",
        "clean_self_hosted_in_public.yml",
    ),
    UNPARSEABLE: (
        "violation_workflow_does_not_parse.yml",
        "clean_workflow_does_not_parse.yml",
    ),
}


def _codes(
    fixture: str, contract: ModelValidatorSubcontract | None = None
) -> list[str]:
    validator = ValidatorPublicCiPlacement(contract, repository="probe", root=FIXTURES)
    return [str(i.code) for i in validator.validate(FIXTURES / fixture).issues]


@pytest.mark.parametrize(("rule_id", "files"), sorted(FIXTURE_CASES.items()))
def test_planted_violation_yields_exactly_one_issue_and_clean_yields_none(
    rule_id: str, files: tuple[str, str]
) -> None:
    violation, clean = files
    assert _codes(violation) == [rule_id]
    assert _codes(clean) == []


@pytest.mark.parametrize("rule_id", sorted(FIXTURE_CASES))
def test_disabling_a_rule_row_clears_its_fixture(rule_id: str) -> None:
    contract = _contract()
    rows = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    disabled = contract.model_copy(update={"rules": rows})
    assert _codes(FIXTURE_CASES[rule_id][0], disabled) == []


# parameter -> (single-job runs-on that exercises it, "flags" or "clears")
CONTROLS: dict[str, tuple[str, str]] = {
    "hosted_label_pattern": (HOSTED, "flags"),
    "unprovable_context_pattern": ("${{ matrix.os }}", "clears"),
    "self_hosted_marker": ("${{ format(self-hosted) }}", "clears"),
    "returned_literal_pattern": (
        "${{ github.event_name == 'push' && 'my-box' || 'ubuntu-latest' }}",
        "clears",
    ),
    "json_array_literal_pattern": (
        '${{ fromJSON(\'["ubuntu-latest", "omnibase-ci"]\') }}',
        "clears",
    ),
    "private_guard_pattern": (PRIVATE_GUARDED, "flags"),
    "hosted_fallback_pattern": (PRIVATE_GUARDED, "flags"),
}


def _mutated(key: str, value: str) -> ModelValidatorSubcontract:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == SELF_HOSTED and row.parameters:
            row = row.model_copy(update={"parameters": {**row.parameters, key: value}})
        rows.append(row)
    return contract.model_copy(update={"rules": rows})


def test_every_parameter_of_the_rule_row_has_a_control() -> None:
    declared = set(_rules()[SELF_HOSTED].parameters or {})
    assert declared == set(CONTROLS) | {"remediation"}


@pytest.mark.parametrize("key", sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(key: str, tmp_path: Path) -> None:
    runs_on, direction = CONTROLS[key]
    source = _workflow(probe=runs_on)
    before = _issues(source, tmp_path / "a")
    mutated = _mutated(key, "zz-unmatched" if key == "self_hosted_marker" else "(?!)")
    after = _issues(source, tmp_path / "b", contract=mutated)
    assert (before, after) == (
        ([], [(SELF_HOSTED, "probe")])
        if direction == "flags"
        else ([(SELF_HOSTED, "probe")], [])
    )


def test_remediation_text_is_the_rule_parameter(tmp_path: Path) -> None:
    mutated = _mutated("remediation", "Move the job to a hosted label.")
    target = tmp_path / CI
    target.parent.mkdir(parents=True)
    target.write_text(_workflow(probe=LAB))
    validator = ValidatorPublicCiPlacement(mutated, repository="r", root=tmp_path)
    [issue] = validator.validate(target).issues
    assert issue.suggestion == "Move the job to a hosted label."


def test_invalid_contract_fails_instead_of_passing() -> None:
    rows = {
        r.rule_id: r.model_copy(update={"parameters": {}}) for r in _contract().rules
    }
    request = ModelPublicRunnerPlacementInput(
        repository="r",
        files=(ModelSourceFile(path=CI, source=_workflow(probe=LAB)),),
    )
    with pytest.raises(ModelOnexError, match="hosted_label_pattern"):
        checker.check_public_runner_placement(request, rows)


def test_checker_is_pure_over_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("checker performed I/O")

    request = ModelPublicRunnerPlacementInput(
        repository="r",
        files=(ModelSourceFile(path=CI, source=_workflow(probe=LAB)),),
    )
    rules = _rules()
    with monkeypatch.context() as patched:
        patched.setattr("builtins.open", refuse)
        patched.setattr(Path, "read_text", refuse)
        issues = checker.check_public_runner_placement(request, rules)
    assert [i.code for i in issues] == [SELF_HOSTED]


# --- the entry over real directories and as a module --------------------------


def _repo(tmp_path: Path, workflow: str) -> Path:
    repo = tmp_path / "omnibase_infra"
    target = repo / CI
    target.parent.mkdir(parents=True)
    target.write_text(workflow)
    return repo


def _module(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_public_runner_placement",
            *argv,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_fails_a_public_repository_with_a_self_hosted_job(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, FIXTURE_PUBLIC_WORKFLOW)
    result = _module("--root", str(repo), "--repo", "omnibase_infra")
    assert result.returncode == 1
    for job in FIXTURE_SELF_HOSTED:
        assert f"{CI}:jobs.{job}" in result.stdout


def test_module_passes_a_hosted_public_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _workflow(lint=HOSTED, routed=PRIVATE_GUARDED))
    assert _module("--root", str(repo), "--repo", "omnibase_infra").returncode == 0


def test_module_private_repository_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, FIXTURE_PUBLIC_WORKFLOW)
    assert _module("--root", str(repo), "--visibility", "private").returncode == 0


@pytest.mark.parametrize(
    "flag", ["--baseline", "--base-ref", "--baseline-ratchet-base-ref"]
)
def test_module_refuses_the_retired_baseline_flags(tmp_path: Path, flag: str) -> None:
    """OMN-21280: no flag brings a baseline or a base comparison back."""
    repo = _repo(tmp_path, _workflow(lint=HOSTED))
    assert _module("--root", str(repo), flag, "x").returncode == 2


def test_omnibase_core_passes_its_own_check() -> None:
    """Positive control: core's own workflows, with no baseline (OMN-21280)."""
    result = _module("--root", str(ROOT), "--repo", "omnibase_core")
    assert result.returncode == 0, result.stdout
