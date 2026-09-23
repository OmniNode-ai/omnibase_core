# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Workflow-shape pins for the Receipt Gate's pin-only exemption (OMN-18882).

``receipt-gate.yml`` is the third gate in the OMN-18848 family. The other two
already read the occ-autobind producer's terminal outcome; this one did not,
so a dependency-pin-only PR hard-failed on "PR body is missing required
'Evidence-Source:' line" forever -- the producer correctly declines to mint a
companion for a manifest+lockfile bump, so the citation it demands can never
exist (measured on omnimarket#2701).

These are the falsifiers. A future edit that drops the early omnibase_core
checkout, invokes the probe by a bare workspace-relative path, moves the probe
after the hard fail, or adds a downstream step that misses the new condition
must turn this module red. It is deliberately the same shape as
``test_occ_preflight_wait_workflow_shape_omn17864.py``, because the two gates
now carry the same exemption and must not drift apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"

PIN_ONLY_CONDITION = (
    "steps.resolve_evidence_source.outputs.evidence_not_required != 'true'"
)
BOT_EXEMPT_CONDITION = "steps.bot_exempt.outputs.exempt != 'true'"

HARD_FAIL_MARKER = (
    "RECEIPT GATE FAILED: PR body is missing required 'Evidence-Source:' line"
)
PROBE_FLAG = "--check-no-companion-required"
WAIT_MODULE = "occ_preflight_wait.py"
# The directory leaf the early checkout lands in. It must differ from
# occ-preflight.yml's `.occ-preflight-deps/omnibase_core_wait`, because a
# repository can run both reusables in the same workflow run and
# actions/checkout CLEANS the path it is given.
OCC_PREFLIGHT_LEAF = ".occ-preflight-deps/omnibase_core_wait"


def _workflow() -> dict[Any, Any]:
    # PyYAML (YAML 1.1) parses the bare `on:` top-level key as the boolean
    # True, not the string "on".
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _workflow_call_inputs() -> dict[str, Any]:
    workflow = _workflow()
    on_block = workflow.get(True, workflow.get("on"))
    assert isinstance(on_block, dict), (
        f"no 'on:' block found; top-level keys: {sorted(map(str, workflow))}"
    )
    inputs = on_block["workflow_call"]["inputs"]
    assert isinstance(inputs, dict)
    return inputs


def _verify_job() -> dict[str, Any]:
    job = _workflow()["jobs"]["verify"]
    assert isinstance(job, dict)
    return job


def _steps() -> list[dict[str, Any]]:
    steps = _verify_job()["steps"]
    assert isinstance(steps, list)
    return steps


def _step_index(step_id: str) -> int:
    for idx, step in enumerate(_steps()):
        if step.get("id") == step_id:
            return idx
    raise AssertionError(f"verify job has no step with id {step_id!r}")


def _resolve_evidence_source_step() -> dict[str, Any]:
    step = _steps()[_step_index("resolve_evidence_source")]
    assert isinstance(step, dict)
    return step


def _is_omnibase_core_checkout(step: dict[str, Any]) -> bool:
    if not str(step.get("uses", "")).startswith("actions/checkout@"):
        return False
    with_block = step.get("with")
    if not isinstance(with_block, dict):
        return False
    return with_block.get("repository") == "OmniNode-ai/omnibase_core"


# ---------------------------------------------------------------------------
# 1. The early checkout that makes the shared module available.
# ---------------------------------------------------------------------------


def test_core_ref_input_exists_and_defaults_to_dev() -> None:
    """The probe lives on ``dev``; omnibase_core's ``main`` is release-synced
    and therefore lags it. Mirrors occ-preflight.yml's own ``core-ref``."""
    inputs = _workflow_call_inputs()
    assert "core-ref" in inputs, (
        "receipt-gate.yml must declare a 'core-ref' workflow_call input for the "
        f"early omnibase_core checkout; got {sorted(inputs)}"
    )
    assert inputs["core-ref"].get("type") == "string"
    assert inputs["core-ref"].get("default") == "dev"


def test_an_omnibase_core_checkout_precedes_resolve_evidence_source() -> None:
    """Without it, an EXTERNAL caller's workspace holds no copy of
    occ_preflight_wait.py and the probe cannot run at all. The later
    'Check out omnibase_core (for receipt-gate deps)' step is pinned to a fix
    SHA and runs AFTER this step -- it does not satisfy this requirement."""
    resolve_idx = _step_index("resolve_evidence_source")
    preceding = [s for s in _steps()[:resolve_idx] if _is_omnibase_core_checkout(s)]
    assert preceding, (
        "no 'actions/checkout' step targeting OmniNode-ai/omnibase_core precedes "
        "'resolve_evidence_source' -- an external caller's workspace has no copy "
        "of scripts/ci/occ_preflight_wait.py to run"
    )
    for step in preceding:
        with_block = step["with"]
        assert with_block.get("ref") == "${{ inputs.core-ref }}", (
            "the early omnibase_core checkout must honor the core-ref input, got "
            f"{with_block.get('ref')!r}"
        )


def test_the_early_checkout_path_is_workspace_relative_and_collision_free() -> None:
    """``actions/checkout`` refuses a path outside GITHUB_WORKSPACE, and it
    CLEANS the path it is given -- so this leaf must differ both from
    occ-preflight.yml's and from this workflow's own later deps checkout."""
    resolve_idx = _step_index("resolve_evidence_source")
    preceding = [s for s in _steps()[:resolve_idx] if _is_omnibase_core_checkout(s)]
    assert preceding, "expected the pre-resolve omnibase_core checkout to exist"
    later_paths = {
        str(s["with"].get("path", ""))
        for s in _steps()[resolve_idx:]
        if _is_omnibase_core_checkout(s)
    }
    for step in preceding:
        path_value = str(step["with"].get("path", ""))
        assert path_value, "the pre-resolve omnibase_core checkout must declare a path"
        assert not path_value.startswith("/"), (
            f"checkout path {path_value!r} is absolute; actions/checkout rejects "
            "any path outside GITHUB_WORKSPACE"
        )
        assert "runner.temp" not in path_value and "RUNNER_TEMP" not in path_value, (
            f"checkout path {path_value!r} resolves outside GITHUB_WORKSPACE"
        )
        assert path_value != OCC_PREFLIGHT_LEAF, (
            f"checkout path {path_value!r} collides with occ-preflight.yml's own "
            "early checkout; actions/checkout cleans the path it is given, so a "
            "shared leaf lets one gate wipe the other's module mid-run"
        )
        assert path_value not in later_paths, (
            f"checkout path {path_value!r} collides with this workflow's later "
            "omnibase_core deps checkout, which is pinned to a different ref"
        )


def test_the_early_checkout_is_skipped_when_the_module_is_already_in_tree() -> None:
    """A self-referential omnibase_core PR must test its OWN edit to the
    module, not silently run the core-ref default instead."""
    resolve_idx = _step_index("resolve_evidence_source")
    preceding = [s for s in _steps()[:resolve_idx] if _is_omnibase_core_checkout(s)]
    for step in preceding:
        condition = str(step.get("if", ""))
        assert f"hashFiles('scripts/ci/{WAIT_MODULE}')" in condition, (
            "the early omnibase_core checkout must carry a hashFiles guard on "
            f"scripts/ci/{WAIT_MODULE} so an omnibase_core PR editing that module "
            f"exercises its own copy; got if: {condition!r}"
        )


# ---------------------------------------------------------------------------
# 2. The probe inside Resolve Evidence-Source.
# ---------------------------------------------------------------------------


def test_resolve_evidence_source_invokes_the_shared_probe() -> None:
    """AC7: the pin-only token is defined ONCE, in
    scripts/ci/occ_preflight_wait.py. The gate must resolve it through that
    module rather than re-spelling the literal in bash."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert WAIT_MODULE in run_block, (
        "resolve_evidence_source must drive scripts/ci/occ_preflight_wait.py for "
        "the pin-only verdict"
    )
    assert PROBE_FLAG in run_block, (
        f"resolve_evidence_source must pass {PROBE_FLAG} to the shared module"
    )
    assert "DEPENDENCY_PIN_ONLY" not in run_block, (
        "the pin-only reason token must not be re-spelled in this workflow -- it "
        "is defined once, in AUTOBIND_NO_COMPANION_REQUIRED_REASONS, and a second "
        "copy is how the fleet's definition of the exemption splits in silence"
    )


def test_the_probe_is_invoked_by_an_absolute_path() -> None:
    """A bare workspace-relative invocation resolves only for omnibase_core's
    own callers and hard-fails 'No such file or directory' for every external
    one -- the exact OMN-17864 follow-up failure."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert f"python3 scripts/ci/{WAIT_MODULE}" not in run_block, (
        "the probe must not be invoked by a bare workspace-relative path"
    )
    assert "GITHUB_WORKSPACE" in run_block, (
        "the probe must be resolved from an absolute path rooted at GITHUB_WORKSPACE"
    )


def test_the_probe_prefers_the_in_tree_module_when_this_repo_is_omnibase_core() -> None:
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert f'"$GITHUB_WORKSPACE/scripts/ci/{WAIT_MODULE}"' in run_block, (
        "the probe must prefer $GITHUB_WORKSPACE/scripts/ci/"
        f"{WAIT_MODULE} when present, so a self-referential omnibase_core PR "
        "tests its own edit"
    )


def test_the_probe_runs_before_the_missing_evidence_source_hard_fail() -> None:
    """A probe placed after the hard fail is dead code: the step has already
    exited 1."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert HARD_FAIL_MARKER in run_block, (
        "the existing 'missing Evidence-Source' hard fail must remain in place"
    )
    assert run_block.index(PROBE_FLAG) < run_block.index(HARD_FAIL_MARKER), (
        "the pin-only probe must run BEFORE the missing-Evidence-Source hard "
        "fail, or it can never be reached"
    )


def test_the_exempt_branch_emits_the_output_and_a_notice() -> None:
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert "evidence_not_required=true" in run_block, (
        "the exempt branch must write evidence_not_required=true to $GITHUB_OUTPUT"
    )
    assert "::notice::Evidence-Source not required:" in run_block, (
        "the exempt branch must announce itself in the same voice as the two "
        "existing 'Evidence-Source not required:' notices in this step"
    )


def test_the_probe_is_consulted_only_when_no_evidence_source_was_found() -> None:
    """A PR that DOES cite evidence is evaluated on that evidence, whatever
    the producer said."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    probe_at = run_block.index(PROBE_FLAG)
    preceding = run_block[:probe_at]
    guard = '[ -z "$evidence_source" ]'
    assert guard in preceding, (
        f"the probe must sit inside a {guard} guard so a PR that already cites "
        "evidence never pays for it and can never be exempted by it"
    )


def test_the_probe_passes_the_repository_and_pr_number() -> None:
    step = _resolve_evidence_source_step()
    run_block = str(step.get("run", ""))
    env_block = step.get("env", {})
    assert isinstance(env_block, dict)
    rendered = run_block + " " + " ".join(f"{k}={v}" for k, v in env_block.items())
    assert "--repo" in run_block, "the probe must be told which repository to read"
    assert "--pr-number" in run_block, "the probe must be told which PR to read"
    assert "github.repository" in rendered, (
        "the probe's --repo must resolve from github.repository"
    )


# ---------------------------------------------------------------------------
# 3. The drift-proofing walk: every downstream step honours the exemption.
# ---------------------------------------------------------------------------


def _steps_after_resolve_evidence_source() -> list[dict[str, Any]]:
    return list(_steps()[_step_index("resolve_evidence_source") + 1 :])


def test_every_step_after_resolve_evidence_source_honors_the_pin_only_exemption() -> (
    None
):
    later = _steps_after_resolve_evidence_source()
    assert later, "expected steps after resolve_evidence_source"
    missing = [
        str(step.get("name", step.get("uses", "<unnamed>")))
        for step in later
        if PIN_ONLY_CONDITION not in str(step.get("if", ""))
    ]
    assert not missing, (
        "these verify steps run AFTER resolve_evidence_source but do not carry "
        f"{PIN_ONLY_CONDITION!r}: {missing}. A dependency-pin-only PR has no OCC "
        "evidence to check out, so an unguarded step fails confusingly instead "
        "of passing the gate (OMN-18882)"
    )


def test_pin_only_exemption_is_paired_with_the_bot_exempt_one() -> None:
    """The two exemptions are parallel mechanisms gating the same set of
    steps; a step guarded by only one of them is drift."""
    for step in _steps_after_resolve_evidence_source():
        condition = str(step.get("if", ""))
        if BOT_EXEMPT_CONDITION in condition:
            assert PIN_ONLY_CONDITION in condition, (
                f"step {step.get('name')!r} honours the OMN-13762 bot exemption "
                "but not the OMN-18882 pin-only one"
            )


def test_resolve_evidence_source_itself_is_not_gated_on_its_own_output() -> None:
    """The producing step cannot depend on the output it produces, and the
    steps BEFORE it have no such output to read."""
    resolve_idx = _step_index("resolve_evidence_source")
    for step in _steps()[: resolve_idx + 1]:
        assert PIN_ONLY_CONDITION not in str(step.get("if", "")), (
            f"step {step.get('name')!r} runs at or before resolve_evidence_source "
            "and cannot read its output"
        )
