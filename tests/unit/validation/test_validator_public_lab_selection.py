# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""check-public-lab-selection in the generic format (OMN-19998).

RULING 2026-11-05T09:10:44Z orders it made impossible for the lab to run public
repositories. The failing controls are the planted selections: a lab label, a lab
variable, an unprovable value, a new caller of a lab-selecting reusable workflow, a
flipped seam value and a new route are each refused.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_public_lab_route_kind import EnumPublicLabRouteKind
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_public_lab_node_route import (
    ModelPublicLabNodeRoute,
)
from omnibase_core.models.version_drift.model_public_lab_node_routes import (
    ModelPublicLabNodeRoutes,
)
from omnibase_core.models.version_drift.model_public_lab_selection_input import (
    ModelPublicLabSelectionInput,
)
from omnibase_core.validation import checker_public_lab_selection as checker
from omnibase_core.validation.validator_public_lab_selection import (
    ValidatorPublicLabSelection,
    load_packaged_routes,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "validation" / "public_lab_selection"
CI = ".github/workflows/ci.yml"
REPO = "omnibase_infra"
# The route count on the day the check was added. Lower it when a route ends; it
# may never rise.
ROUTE_CEILING = 59
SEAM = "${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '[\"ubuntu-latest\"]') }}"
FORK_BRANCH = (
    "${{ (github.event_name == 'pull_request' && "
    "github.event.pull_request.head.repo.full_name != github.repository) && "
    "fromJSON(vars.OMNI_PUBLIC_PR_RUNS_ON_JSON || '[\"ubuntu-latest\"]') || "
    "fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '[\"ubuntu-latest\"]') }}"
)
PRIVATE_GUARDED = (
    "${{ github.event.repository.private && ("
    'fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || \'["self-hosted","omnibase-ci"]\')'
    ") || 'ubuntu-latest' }}"
)


def _rules() -> dict[str, ModelValidatorRule]:
    validator = ValidatorPublicLabSelection(routes=ModelPublicLabNodeRoutes())
    return {r.rule_id: r for r in validator.contract.rules}


def _route(job: str = "probe", workflow: str = CI) -> ModelPublicLabNodeRoute:
    return ModelPublicLabNodeRoute(
        repository=REPO,
        workflow=workflow,
        job=job,
        kind=EnumPublicLabRouteKind.LAB_JOB_NODE,
        destination="node_lab_work_unit_effect",
        plan_step="R4",
        reason="Reaches the lab broker.",
    )


def _workflow(runs_on: str, extra: str = "") -> str:
    return (
        f"name: ci\non: [pull_request]\njobs:\n  probe:\n    runs-on: {runs_on}\n"
        f"{extra}    steps: [{{run: echo ok}}]\n"
    )


def _judge(
    source: str,
    routes: tuple[ModelPublicLabNodeRoute, ...] = (),
    public: bool = True,
) -> tuple[str, ...]:
    request = ModelPublicLabSelectionInput(
        repository=REPO,
        public=public,
        files=(ModelSourceFile(path=CI, source=source),),
        routes=ModelPublicLabNodeRoutes(routes=routes),
    )
    issues = checker.check_public_lab_selection(request, _rules())
    return tuple(str(i.code) for i in issues)


@pytest.mark.parametrize(
    "runs_on",
    [
        "[self-hosted, omnibase-ci]",
        "omnibase-verify",
        "{group: omnibase-ci}",
        "${{ fromJSON(vars.LAB_PROBE_RUNS_ON_JSON) }}",
        "${{ fromJSON(vars.SOME_NEW_RUNS_ON_JSON || '[\"ubuntu-latest\"]') }}",
        "${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '[\"self-hosted\"]') }}",
        "${{ fromJSON(needs.route.outputs.labels) }}",
        "${{ github.event_name == 'push' && 'omnibase-ci' || 'ubuntu-latest' }}",
        "${{ matrix.unknown }}",
    ],
)
def test_failing_control_a_lab_selection_is_refused(runs_on: str) -> None:
    assert _judge(_workflow(runs_on)) == (checker.RULE_LAB_SELECTED,)


@pytest.mark.parametrize(
    "runs_on",
    ["ubuntu-latest", "[ubuntu-24.04]", "macos-15", SEAM, FORK_BRANCH, PRIVATE_GUARDED],
)
def test_a_hosted_job_passes(runs_on: str) -> None:
    assert _judge(_workflow(runs_on)) == ()


def test_a_matrix_of_hosted_labels_passes_and_a_lab_one_is_refused() -> None:
    runs_on = "${{ matrix.os }}"
    hosted = "    strategy: {matrix: {os: [ubuntu-latest, macos-15]}}\n"
    lab = "    strategy: {matrix: {os: [ubuntu-latest, self-hosted]}}\n"
    assert _judge(_workflow(runs_on, hosted)) == ()
    assert _judge(_workflow(runs_on, lab)) == (checker.RULE_LAB_SELECTED,)


def test_a_private_repository_passes() -> None:
    assert _judge(_workflow("[self-hosted, omnibase-ci]"), public=False) == ()


def test_a_typed_route_covers_exactly_its_own_job() -> None:
    source = _workflow("[self-hosted, omnibase-ci]")
    assert _judge(source, routes=(_route(),)) == ()
    assert _judge(source, routes=(_route(job="other"),)) == (
        checker.RULE_LAB_SELECTED,
        checker.RULE_ROUTE_STALE,
    )


def test_a_route_for_a_job_that_moved_warns_so_the_count_falls() -> None:
    assert _judge(_workflow("ubuntu-latest"), routes=(_route(),)) == (
        checker.RULE_ROUTE_STALE,
    )


def test_failing_control_a_new_caller_of_a_routed_reusable_is_refused() -> None:
    callee = _route(job="gate", workflow=".github/workflows/gate-reusable.yml")
    caller = (
        "name: ci\non: [pull_request]\njobs:\n  gate:\n"
        "    uses: OmniNode-ai/omnibase_infra/.github/workflows/gate-reusable.yml@abc\n"
    )
    assert _judge(caller, routes=(callee,)) == (checker.RULE_REUSABLE_CALLER,)
    hosted_callee = (
        "name: ci\non: [pull_request]\njobs:\n  gate:\n"
        "    uses: OmniNode-ai/omnibase_infra/.github/workflows/other.yml@abc\n"
    )
    assert _judge(hosted_callee, routes=(callee,)) == ()
    leaving = callee.model_copy(
        update={
            "kind": EnumPublicLabRouteKind.MOVES_TO_HOSTED,
            "destination": "ubuntu-latest",
        }
    )
    assert _judge(caller, routes=(leaving,)) == ()


@pytest.mark.parametrize(
    ("value", "refused"),
    [
        ('["ubuntu-latest"]', False),
        ('["self-hosted","omnibase-ci"]', True),
        ("[]", True),
        ("not json", True),
    ],
)
def test_failing_control_a_flipped_seam_value_is_refused(
    value: str, refused: bool
) -> None:
    request = ModelPublicLabSelectionInput(
        repository=REPO, variables={"OMNI_TRUSTED_CI_RUNS_ON_JSON": value}
    )
    issues = checker.check_seam_values(request, _rules())
    assert bool(issues) is refused


def test_a_private_repository_may_hold_a_lab_seam_value() -> None:
    request = ModelPublicLabSelectionInput(
        repository=REPO,
        public=False,
        variables={"OMNI_TRUSTED_CI_RUNS_ON_JSON": '["self-hosted"]'},
    )
    assert checker.check_seam_values(request, _rules()) == ()


def test_failing_control_a_new_route_is_refused_and_a_removed_one_passes() -> None:
    base = ModelPublicLabNodeRoutes(routes=(_route(),))
    grown = ModelPublicLabNodeRoutes(routes=(_route(), _route(job="another")))
    empty = ModelPublicLabNodeRoutes()
    issues = checker.check_routes_only_shrink(base, grown, _rules(), "routes.yaml")
    assert [i.code for i in issues] == [checker.RULE_ROUTE_ADDED]
    assert checker.check_routes_only_shrink(base, empty, _rules(), "routes.yaml") == ()


def test_a_broken_workflow_is_refused() -> None:
    assert _judge("jobs: [unclosed") == (checker.RULE_UNPARSEABLE,)


def test_a_route_is_typed_and_not_an_exception_by_name() -> None:
    fields = _route().model_dump()
    with pytest.raises(ValidationError, match="must name a node"):
        ModelPublicLabNodeRoute(**{**fields, "destination": "some job"})
    with pytest.raises(ValidationError):
        ModelPublicLabNodeRoute(**{**fields, "plan_step": "someday"})
    with pytest.raises(ValidationError):
        ModelPublicLabNodeRoute(**{**fields, "kind": "excused"})
    with pytest.raises(ValidationError):
        ModelPublicLabNodeRoute(**fields, excused=True)
    with pytest.raises(ValidationError, match="more than one route"):
        ModelPublicLabNodeRoutes(routes=(_route(), _route()))


def test_the_packaged_routes_load_and_the_count_never_rises() -> None:
    routes = load_packaged_routes()
    assert len(routes.routes) <= ROUTE_CEILING
    assert "omnibase_core" not in {route.repository for route in routes.routes}


@pytest.mark.parametrize(
    ("fixture", "code"),
    [
        ("violation_lab_selected_in_public.yml", checker.RULE_LAB_SELECTED),
        ("violation_workflow_does_not_parse.yml", checker.RULE_UNPARSEABLE),
        ("clean_lab_selected_in_public.yml", None),
        ("clean_workflow_does_not_parse.yml", None),
    ],
)
def test_the_fixtures(fixture: str, code: str | None) -> None:
    found = _judge((FIXTURES / fixture).read_text(encoding="utf-8"))
    assert found == ((code,) if code else ())


def _cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_public_lab_selection",
            "--root",
            str(root),
            "--repo",
            "some_public_repo",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _tree(tmp_path: Path, runs_on: str) -> Path:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(_workflow(runs_on), encoding="utf-8")
    return tmp_path


def test_failing_control_the_entry_point_exits_non_zero_on_a_planted_job(
    tmp_path: Path,
) -> None:
    done = _cli(_tree(tmp_path, "[self-hosted, omnibase-ci]"))
    assert done.returncode == 1, done.stdout
    assert checker.RULE_LAB_SELECTED in done.stdout


def test_the_entry_point_passes_a_hosted_tree_and_a_private_repository(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path, "ubuntu-latest")
    assert _cli(root).returncode == 0
    (root / ".github/workflows/ci.yml").write_text(
        _workflow("[self-hosted]"), encoding="utf-8"
    )
    assert _cli(root, "--visibility", "private").returncode == 0


def test_failing_control_the_entry_point_refuses_a_flipped_seam(tmp_path: Path) -> None:
    root = _tree(tmp_path, "ubuntu-latest")
    flipped = json.dumps({"OMNI_PUBLIC_PR_RUNS_ON_JSON": '["self-hosted"]'})
    done = _cli(root, "--variables-json", flipped)
    assert done.returncode == 1
    assert checker.RULE_SEAM_VALUE in done.stdout


def test_failing_control_the_entry_point_refuses_route_growth(tmp_path: Path) -> None:
    root = _tree(tmp_path, "ubuntu-latest")
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump({"routes": []}), encoding="utf-8")
    done = _cli(root, "--base-routes", str(base))
    assert done.returncode == 1
    assert checker.RULE_ROUTE_ADDED in done.stdout
