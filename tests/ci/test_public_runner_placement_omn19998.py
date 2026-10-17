# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Public-repository runner placement in omnibase_core (OMN-19998).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
omnibase_core is public, so:

* no routing-seam fallback in a workflow names the self-hosted fleet; a
  reusable workflow (``workflow_call``) falls back to the fleet only for a
  private caller, read from ``github.event.repository.private``, so a private
  repository calling it keeps its lab runner and a public one gets a hosted one;
* the two jobs that read the route job's decision (``lint`` and
  ``wheel-content-parity``) run on ``ubuntu-latest`` and leave the shrink-only
  baseline;
* the check-public-runner-placement hook runs as a pre-commit hook and as a
  step of ``lint-imports``, which the required Quality Gate / CI Summary chain
  aggregates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOW = WORKFLOWS / "ci.yml"
PRECOMMIT = REPO_ROOT / ".pre-commit-config.yaml"
BASELINE = (
    REPO_ROOT
    / "src"
    / "omnibase_core"
    / "contracts"
    / "public_runner_placement_baseline.yaml"
)

FLEET_FALLBACK = """'["self-hosted","omnibase-ci"]'"""
PRIVATE_CALLER = "github.event.repository.private &&"
HOSTED_JOBS = ("lint", "wheel-content-parity")
HOOK_ID = "check-public-runner-placement"
HOOK_MODULE = "omnibase_core.handlers.handler_public_runner_placement_cli"


def fleet_fallbacks(text: str) -> list[str]:
    """Code lines that fall back to the self-hosted fleet for a public caller."""
    reusable = "workflow_call:" in text
    return [
        line.strip()
        for line in text.splitlines()
        if FLEET_FALLBACK in line
        and not line.lstrip().startswith("#")
        and not (reusable and PRIVATE_CALLER in line)
    ]


def test_fleet_fallback_detector_positive_control() -> None:
    planted = (
        "    runs-on: ${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || "
        """'["self-hosted","omnibase-ci"]') }}\n"""
    )
    private_caller = (
        "        || fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || "
        """(github.event.repository.private && '["self-hosted","omnibase-ci"]' """
        """|| '["ubuntu-latest"]'))\n"""
    )
    hosted = (
        "    runs-on: ${{ fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || "
        """'["ubuntu-latest"]') }}\n"""
    )
    assert fleet_fallbacks(planted) == [planted.strip()]
    assert fleet_fallbacks(hosted) == []
    # The private-caller form is accepted only in a reusable workflow; in a
    # workflow only omnibase_core runs, the caller is always public.
    assert fleet_fallbacks("on:\n  workflow_call:\n" + private_caller) == []
    assert fleet_fallbacks(private_caller) == [private_caller.strip()]


def test_no_workflow_falls_back_to_the_self_hosted_fleet() -> None:
    offenders = {
        path.name: found
        for path in sorted(WORKFLOWS.glob("*.y*ml"))
        if (found := fleet_fallbacks(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}, (
        "A public repository's routing fallback must be GitHub-hosted "
        "(RULING 2026-10-16T07:07:09Z): " + repr(offenders)
    )


def _load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize("job_id", HOSTED_JOBS)
def test_route_consumers_run_on_a_hosted_runner(job_id: str) -> None:
    assert _load(CI_WORKFLOW)["jobs"][job_id]["runs-on"] == "ubuntu-latest"


@pytest.mark.parametrize("job_id", HOSTED_JOBS)
def test_hosted_jobs_left_the_baseline(job_id: str) -> None:
    baseline = _load(BASELINE)["repos"]["omnibase_core"]
    assert job_id not in baseline[".github/workflows/ci.yml"]


def test_placement_check_is_a_step_of_a_job_quality_gate_requires() -> None:
    jobs = _load(CI_WORKFLOW)["jobs"]
    steps = jobs["lint-imports"]["steps"]
    runs = "\n".join(str(step.get("run", "")) for step in steps)
    assert HOOK_MODULE in runs
    assert "--repo omnibase_core" in runs
    assert "--baseline-ratchet-base-ref" in runs
    needs = jobs["quality-gate"]["needs"]
    assert "lint-imports" in needs


def test_precommit_runs_the_placement_hook_for_this_public_repository() -> None:
    hooks = [
        hook
        for repo in _load(PRECOMMIT)["repos"]
        for hook in repo.get("hooks", [])
        if hook.get("id") == HOOK_ID
    ]
    assert len(hooks) == 1
    assert HOOK_MODULE in hooks[0]["entry"]
    assert hooks[0]["args"][:2] == ["--repo", "omnibase_core"]
