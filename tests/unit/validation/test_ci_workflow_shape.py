# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"

STDLIB_ONLY_GUARD_COMMANDS = {
    "exports-validation": "python3 scripts/validation/validate-all-exports.py",
    "node-purity-check": "python3 scripts/check_node_purity.py --verbose",
    "no-env-fallbacks": "python3 scripts/validate_no_env_fallbacks.py",
    "naming-conventions": "python3 scripts/validate_class_naming.py",
    "pydantic-patterns": (
        "python3 scripts/validation/validate-pydantic-patterns.py $files"
    ),
}

DEPENDENCY_GUARD_PROFILES = {
    # job id: (sync command, measured timeout budget in minutes)
    #
    # OMN-15980: mypy-validation-scripts, enum-governance,
    # contract-config-compliance, sdk-boundary-check, aislop-patterns,
    # doc-content-scan, spdx-headers, no-new-os-environ,
    # duplicate-registry-ids, and pull-request-workflow-ratchet raised
    # 6/7 -> 20. These are the jobs directly evidenced hitting their OLD
    # budget on the self-hosted omnibase-ci fleet under push-event load in
    # two live runs 9 days apart (run 30860114454 / commit f87a02ac,
    # 2026-08-03; run 31596723212 / commit c81db71e, 2026-08-12) — see the
    # matching timeout-minutes comment on mypy-validation-scripts in
    # .github/workflows/ci.yml for the full byte-cited rationale.
    # breaking-schema-change, demo-path-topic-coherence,
    # dispatch-surface-test-required, and no-noncanonical-lifecycle-classes
    # were NOT observed cancelled in either run and are left at 7 —
    # evidence-scoped, not a blanket bump of every job in this dict.
    "mypy-validation-scripts": ("uv sync --frozen", 20),
    "enum-governance": ("uv sync --frozen --no-dev", 20),
    "contract-config-compliance": ("uv sync --frozen --no-dev", 20),
    "breaking-schema-change": ("uv sync --frozen --no-dev", 7),
    "sdk-boundary-check": ("uv sync --frozen", 20),
    "demo-path-topic-coherence": ("uv sync --frozen --no-dev", 7),
    "dispatch-surface-test-required": ("uv sync --frozen --no-dev", 7),
    "aislop-patterns": ("uv sync --frozen --no-dev", 20),
    "doc-content-scan": ("uv sync --frozen --no-dev", 20),
    "spdx-headers": ("uv sync --frozen --no-dev", 20),
    "no-new-os-environ": ("uv sync --frozen --no-dev", 20),
    "duplicate-registry-ids": ("uv sync --frozen", 20),
    "no-noncanonical-lifecycle-classes": ("uv sync --frozen --no-dev", 7),
    "pull-request-workflow-ratchet": ("uv sync --frozen --no-dev", 20),
}

NO_DEV_WORKFLOW_EXECUTION_CONTRACT = "d7dfb006ec524bc384a900b284fc56cbf2a3d7d00a9e1709906ed4e5aebb0d8e"  # pragma: allowlist secret

# SHA-256 over canonical JSON of each complete audited guard job. No job key is
# excluded: steps, env, defaults, container, runs-on, if, continue-on-error,
# strategy, needs, permissions, timeout, and future job-level keys are all part
# of the contract. Updating a digest requires auditing the readable workflow
# diff first; this deliberately avoids another partial execution-surface list.
AUDITED_GUARD_JOB_EXECUTION_CONTRACTS = {
    "exports-validation": (
        "992688f96b514d884eed9932a5f3676ebc4c1fb2c633e626a7eb5c9fa6348c75"  # pragma: allowlist secret
    ),
    "mypy-validation-scripts": (
        "2423622dc22413cc48dc86c623484359251b1046235dc61d3b8fd947512cd69e"  # pragma: allowlist secret
    ),
    "core-infra-boundary": (
        "a6fa1e4ffb7740fc365e526a88e488cccf2d1f08474c6e6b2f2cbe8bdb95f85d"  # pragma: allowlist secret
    ),
    "check-deterministic-skills": (
        "e9092b6a2e64c9dcc5d1d89ac7171a0e84547dbd1dfc4c962660c522fba99e7a"  # pragma: allowlist secret
    ),
    "node-purity-check": (
        "11a091eb4a9382801797ca89fef8090e43385b5b1c991949d7b4ed13afef3b06"  # pragma: allowlist secret
    ),
    "enum-governance": (
        "a46c3a30ecb40d58ad032a1920f24b93cef38716bccecd708e7a41014499727b"  # pragma: allowlist secret
    ),
    "contract-config-compliance": (
        "e37fad25fe594d66ccb0bd113e5be34a418301a06121500936ad8d8eb11e677c"  # pragma: allowlist secret
    ),
    "breaking-schema-change": (
        "9409004bc80f756cb90e51d387dc888fd3a2f62b70d45ea0d87bb32dcbc68389"  # pragma: allowlist secret
    ),
    "no-env-fallbacks": (
        "e6ee4cb21d27caaba2d3a0514683f4df9ab448d588e7ce107f1c610f4c928cb7"  # pragma: allowlist secret
    ),
    "detect-secrets": (
        "4c87091b2cd5322878766b784d30158edbbd607fb304ea416df805067a0eb0c2"  # pragma: allowlist secret
    ),
    "sdk-boundary-check": (
        "30800b3a56c20e4c0d8b0365b17cb847f6c8149264aa03a8fe8e254136fc6cba"  # pragma: allowlist secret
    ),
    "demo-path-topic-coherence": (
        "8ff2f91d5081d541f624c2e55562b05dd1945d6c0a6913a26c5099b4dd455e72"  # pragma: allowlist secret
    ),
    "dispatch-surface-test-required": (
        "6392730ab2e8a48efa83053c3dbb571a4f52c271e188b8e038a8be31535bedc4"  # pragma: allowlist secret
    ),
    "naming-conventions": (
        "4c018ad075660fc1c8d68c65c84c00b5c7bcd82ba4a70267baa7f6e2ce377aa7"  # pragma: allowlist secret
    ),
    "pydantic-patterns": (
        "0c69ccc1414177fc6b8ce43a34990d8fbd3c63de3ad58a0dc0eb735cf95d8f1b"  # pragma: allowlist secret
    ),
    "aislop-patterns": (
        "ccd7eef29e492fdd919b57e24dbecd266764613d65a6dd666f1625b3d209afa7"  # pragma: allowlist secret
    ),
    "doc-content-scan": (
        "1e8c24ae8e37648af73bfabb75575112632b8cd4ac169045d4ac8b5b9664e7cc"  # pragma: allowlist secret
    ),
    "spdx-headers": (
        "a0d28fb716ae9560bc17be1d8f3631474ba82e00db2ad2b4490820fedcad8d8a"  # pragma: allowlist secret
    ),
    "no-new-os-environ": (
        "9cc6299ee4ee8831d443d25614c7ca92e607a96237c9b7d9db378acd6853e4e6"  # pragma: allowlist secret
    ),
    "duplicate-registry-ids": (
        "6d4d2c5bb43d103924a336575a5022d17cedf8e086ceff477121255d52e71dca"  # pragma: allowlist secret
    ),
    "no-noncanonical-lifecycle-classes": (
        "1b72b1142f9e17cff1a1299435b989685423de14563cf081fbb9f6323f929264"  # pragma: allowlist secret
    ),
    "pull-request-workflow-ratchet": (
        "fe67a135dbeae73e46d4908920ba75b4419cb4ccd181b4d4c12d559f5f216a1f"  # pragma: allowlist secret
    ),
}

OTHER_AUDITED_GUARD_JOBS = {
    "core-infra-boundary",
    "check-deterministic-skills",
    "detect-secrets",
}

NO_DEV_DIRECT_EXECUTABLES = {
    "enum-governance": ".venv/bin/python",
    "contract-config-compliance": ".venv/bin/python",
    "breaking-schema-change": ".venv/bin/python",
    "demo-path-topic-coherence": ".venv/bin/onex-demo-path-topic-gate",
    "dispatch-surface-test-required": ".venv/bin/python",
    "aislop-patterns": ".venv/bin/python",
    "doc-content-scan": ".venv/bin/python",
    "spdx-headers": ".venv/bin/python",
    "no-new-os-environ": ".venv/bin/python",
    "no-noncanonical-lifecycle-classes": ".venv/bin/python",
    "pull-request-workflow-ratchet": ".venv/bin/python",
}

FORBIDDEN_EXECUTION_ENV_KEYS = {"BASH_ENV", "ENV", "PATH"}
WORKFLOW_CONTRACT_SCOPE = "<workflow>"

EXPECTED_FIVE_MINUTE_JOBS = {
    "exports-validation",
    "core-infra-boundary",
    "check-deterministic-skills",
    "node-purity-check",
    "no-env-fallbacks",
    "version-pin-check",
    "naming-conventions",
    "pydantic-patterns",
}


def _ci_workflow() -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _workflow_job_steps(
    workflow: dict[str, object], name: str
) -> list[dict[str, object]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def _ci_job(name: str) -> dict[str, object]:
    jobs = _ci_workflow()["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _job_steps(name: str) -> list[dict[str, object]]:
    return _workflow_job_steps(_ci_workflow(), name)


def _job_run_commands(name: str) -> list[str]:
    return [str(step["run"]).strip() for step in _job_steps(name) if "run" in step]


def _contains_literal(value: object, literal: str) -> bool:
    if isinstance(value, str):
        return literal in value
    if isinstance(value, dict):
        return any(
            _contains_literal(key, literal) or _contains_literal(item, literal)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_literal(item, literal) for item in value)
    return False


def _execution_contract_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _workflow_execution_surface(workflow: dict[str, object]) -> dict[str, object]:
    return {
        "env": workflow.get("env", {}),
        "defaults": workflow.get("defaults", {}),
    }


def _guard_job_contract_violations(
    workflow: dict[str, object], job_names: set[str] | None = None
) -> list[str]:
    """Return audited guard jobs whose complete job definition changed."""
    selected_names = (
        set(AUDITED_GUARD_JOB_EXECUTION_CONTRACTS) if job_names is None else job_names
    )
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return sorted(selected_names)

    violations: list[str] = []
    for job_name in sorted(selected_names):
        job = jobs.get(job_name)
        expected_digest = AUDITED_GUARD_JOB_EXECUTION_CONTRACTS.get(job_name)
        if (
            not isinstance(job, dict)
            or expected_digest is None
            or _execution_contract_digest(job) != expected_digest
        ):
            violations.append(job_name)
    return violations


def _guard_contract_diagnostics(
    workflow: dict[str, object], violations: list[str]
) -> str:
    """Render expected and actual digests for an intentional contract update."""
    jobs = workflow.get("jobs")
    details = ["Audited guard job execution contract mismatch:"]
    for job_name in violations:
        expected = AUDITED_GUARD_JOB_EXECUTION_CONTRACTS.get(job_name, "<undeclared>")
        job = jobs.get(job_name) if isinstance(jobs, dict) else None
        actual = (
            _execution_contract_digest(job)
            if isinstance(job, dict)
            else "<missing-or-invalid-job>"
        )
        details.append(f"- {job_name}: expected={expected} actual={actual}")
    return "\n".join(details)


def _env_keys(container: dict[str, object]) -> set[str] | None:
    env = container.get("env", {})
    if not isinstance(env, dict):
        return None
    return {str(key) for key in env}


def _literal_no_dev_job_names(workflow: dict[str, object]) -> set[str]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return set()
    return {
        str(job_name)
        for job_name, job in jobs.items()
        if _contains_literal(job, "--no-dev")
    }


def _no_dev_contract_violations(workflow: dict[str, object]) -> list[str]:
    """Return scopes that differ from the audited no-dev execution contract."""
    violations: set[str] = set()
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return [WORKFLOW_CONTRACT_SCOPE]

    declared_jobs = set(NO_DEV_DIRECT_EXECUTABLES)
    discovered_jobs = _literal_no_dev_job_names(workflow)
    violations.update(declared_jobs.symmetric_difference(discovered_jobs))
    violations.update(_guard_job_contract_violations(workflow, declared_jobs))

    workflow_env_keys = _env_keys(workflow)
    if (
        workflow_env_keys is None
        or workflow_env_keys & FORBIDDEN_EXECUTION_ENV_KEYS
        or _execution_contract_digest(_workflow_execution_surface(workflow))
        != NO_DEV_WORKFLOW_EXECUTION_CONTRACT
    ):
        violations.add(WORKFLOW_CONTRACT_SCOPE)

    for job_name in declared_jobs:
        job = jobs.get(job_name)
        if not isinstance(job, dict):
            violations.add(job_name)
            continue

        job_env_keys = _env_keys(job)
        if job_env_keys is None or job_env_keys & FORBIDDEN_EXECUTION_ENV_KEYS:
            violations.add(job_name)

    return sorted(violations)


def _boundary_validation_step() -> dict[str, object]:
    job = _ci_job("boundary-validation")
    steps = job["steps"]

    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and "validate-boundaries" in str(
            step.get("uses", "")
        ):
            return step

    raise AssertionError("boundary-validation job must run validate-boundaries")


def test_parallel_unit_split_timeout_tolerates_self_hosted_runner_pressure() -> None:
    job = _ci_job("test-parallel")

    assert job["timeout-minutes"] >= 35


def test_docs_validation_timeout_tolerates_merge_queue_pressure() -> None:
    job = _ci_job("docs-validation")

    assert job["timeout-minutes"] >= 10


def test_pr_and_merge_queue_use_bounded_xdist_workers() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    workers = data["env"]["PYTEST_XDIST_WORKERS"]

    assert "github.event_name == 'pull_request'" in workers
    assert "github.event_name == 'merge_group'" in workers
    assert "OMNI_PUBLIC_PR_PYTEST_XDIST_WORKERS || '1'" in workers
    assert "OMNI_MERGE_GROUP_PYTEST_XDIST_WORKERS || '2'" in workers


def test_trusted_full_matrix_uses_one_xdist_worker_per_shard() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    workers = data["env"]["PYTEST_XDIST_WORKERS"]

    assert "OMNI_PYTEST_XDIST_WORKERS || '1'" in workers


def test_test_shards_restore_uv_cache_without_competing_to_save_it() -> None:
    setup_uv_steps = [
        step
        for step in _job_steps("test-parallel")
        if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]

    assert len(setup_uv_steps) == 1
    assert setup_uv_steps[0]["with"]["enable-cache"] is True
    assert setup_uv_steps[0]["with"]["save-cache"] is False


def test_audited_guard_jobs_match_complete_execution_contracts() -> None:
    workflow = _ci_workflow()
    expected_jobs = (
        set(STDLIB_ONLY_GUARD_COMMANDS)
        | set(DEPENDENCY_GUARD_PROFILES)
        | OTHER_AUDITED_GUARD_JOBS
    )
    violations = _guard_job_contract_violations(workflow)

    assert set(AUDITED_GUARD_JOB_EXECUTION_CONTRACTS) == expected_jobs
    assert violations == [], _guard_contract_diagnostics(workflow, violations)


@pytest.mark.parametrize(
    ("job_name", "expected_command"), STDLIB_ONLY_GUARD_COMMANDS.items()
)
def test_stdlib_only_guards_do_not_build_a_project_environment(
    job_name: str, expected_command: str
) -> None:
    steps = _job_steps(job_name)
    rendered = "\n".join(
        str(step.get("uses", "")) + "\n" + str(step.get("run", "")) for step in steps
    )

    assert "astral-sh/setup-uv" not in rendered
    assert "uv sync" not in rendered
    assert expected_command in rendered
    assert _ci_job(job_name)["timeout-minutes"] == 5


@pytest.mark.parametrize(
    "mutation",
    ["if-false", "continue-on-error", "mask-command-failure"],
)
def test_bare_guard_contract_rejects_advisory_or_masked_execution(
    mutation: str,
) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "exports-validation")
    validation_step = next(
        step for step in steps if step.get("name") == "Validate __all__ exports"
    )

    if mutation == "if-false":
        validation_step["if"] = "${{ false }}"
    elif mutation == "continue-on-error":
        validation_step["continue-on-error"] = True
    else:
        run = validation_step.get("run")
        assert isinstance(run, str)
        validation_step["run"] = f"{run} || true"

    assert _guard_job_contract_violations(workflow) == ["exports-validation"]


def test_no_dev_contract_rejects_job_container_environment_injection() -> None:
    workflow = copy.deepcopy(_ci_workflow())
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["enum-governance"]
    assert isinstance(job, dict)
    job["container"] = {
        "image": "ubuntu:24.04",
        "env": {"PYTHONPATH": "${{ github.workspace }}/ci_injection"},
    }

    assert _guard_job_contract_violations(workflow) == ["enum-governance"]
    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


@pytest.mark.parametrize(
    ("job_name", "expected_sync", "expected_timeout"),
    (
        (job_name, expected_sync, expected_timeout)
        for job_name, (
            expected_sync,
            expected_timeout,
        ) in DEPENDENCY_GUARD_PROFILES.items()
    ),
)
def test_dependency_guards_use_minimal_locked_sync_and_measured_budgets(
    job_name: str, expected_sync: str, expected_timeout: int
) -> None:
    job = _ci_job(job_name)
    setup_uv_steps = [
        step
        for step in _job_steps(job_name)
        if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]
    sync_commands = [
        command for command in _job_run_commands(job_name) if "uv sync" in command
    ]

    assert len(setup_uv_steps) == 1
    assert setup_uv_steps[0]["with"]["save-cache"] is False
    assert sync_commands == [expected_sync]
    assert "--all-extras" not in sync_commands[0]
    assert job["timeout-minutes"] == expected_timeout


def test_no_dev_execution_surface_matches_declared_contract() -> None:
    workflow = _ci_workflow()

    assert _literal_no_dev_job_names(workflow) == set(NO_DEV_DIRECT_EXECUTABLES)
    for job_name in NO_DEV_DIRECT_EXECUTABLES:
        assert all(("run" in step) ^ ("uses" in step) for step in _job_steps(job_name))
    assert _no_dev_contract_violations(workflow) == []


@pytest.mark.parametrize(
    ("job_name", "expected_executable"), NO_DEV_DIRECT_EXECUTABLES.items()
)
def test_no_dev_jobs_sync_once_then_use_direct_environment_executable(
    job_name: str, expected_executable: str
) -> None:
    run_steps = _job_run_commands(job_name)
    run_lines = [
        line.strip()
        for run_step in run_steps
        for line in run_step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    sync_lines = [line for line in run_lines if line.startswith("uv sync")]
    direct_lines = [line for line in run_lines if line.startswith(".venv/bin/")]

    assert sync_lines == ["uv sync --frozen --no-dev"]
    assert all("uv run" not in run_step for run_step in run_steps)
    assert len(direct_lines) == 1
    assert direct_lines[0].startswith(f"{expected_executable} ")


def _workflow_with_enum_execution(run: str) -> dict[str, object]:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "enum-governance")
    execution_step = next(
        step for step in steps if step.get("name") == "Run enum governance validator"
    )
    execution_step["run"] = run
    return workflow


@pytest.mark.parametrize(
    "opaque_execution",
    [
        'UV_BIN=uv\nif true; then "$UV_BIN" --offline run python; fi',
        'UV_BIN=uv\n/usr/bin/time "$UV_BIN" --offline run python',
        'UV_BIN=uv\nfind . -maxdepth 0 -exec "$UV_BIN" --offline run python \\;',
        "builtin eval 'uv --offline run python'",
        "if true; then eval 'uv --offline run python'; fi",
        "builtin source /dev/stdin <<'SCRIPT'\nuv --offline run python\nSCRIPT",
        "if true; then source /dev/stdin <<'SCRIPT'\nuv --offline run python\nSCRIPT\nfi",
        "env -S 'uv --offline sync --frozen'",
        "bash scripts/ci/hidden-uv.sh",
        "bash /dev/stdin <<'SCRIPT'\nuv --offline run python\nSCRIPT",
        "if true; then dash -c 'uv --offline run python'; fi",
    ],
)
def test_no_dev_contract_rejects_reviewer_execution_evasions(
    opaque_execution: str,
) -> None:
    assert _no_dev_contract_violations(
        _workflow_with_enum_execution(opaque_execution)
    ) == ["enum-governance"]


def test_no_dev_contract_rejects_plain_uv_run() -> None:
    workflow = _workflow_with_enum_execution(
        "uv run python -m omnibase_core.validation.checker_enum_governance"
    )

    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


def test_no_dev_contract_rejects_custom_action_step() -> None:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "enum-governance")
    steps.append(
        {
            "name": "Opaque dependency action",
            "uses": "example/hidden-uv@0123456789abcdef",
            "with": {"command": "sync --frozen"},
        }
    )

    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


@pytest.mark.parametrize("scope", ["workflow", "job"])
@pytest.mark.parametrize("env_name", ["BASH_ENV", "ENV", "PATH"])
def test_no_dev_contract_forbids_execution_environment_indirection(
    scope: str, env_name: str
) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    if scope == "workflow":
        target = workflow
    else:
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        target = jobs["enum-governance"]
        assert isinstance(target, dict)
    env = target.setdefault("env", {})
    assert isinstance(env, dict)
    env[env_name] = "/tmp/opaque-execution-hook"

    expected = [WORKFLOW_CONTRACT_SCOPE] if scope == "workflow" else ["enum-governance"]
    assert _no_dev_contract_violations(workflow) == expected


@pytest.mark.parametrize("scope", ["workflow", "job"])
def test_no_dev_contract_rejects_any_inherited_env_change(scope: str) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    if scope == "workflow":
        target = workflow
    else:
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        target = jobs["enum-governance"]
        assert isinstance(target, dict)
    env = target.setdefault("env", {})
    assert isinstance(env, dict)
    env["AUDITED_CONTEXT"] = "changed"

    expected = [WORKFLOW_CONTRACT_SCOPE] if scope == "workflow" else ["enum-governance"]
    assert _no_dev_contract_violations(workflow) == expected


@pytest.mark.parametrize("scope", ["workflow", "job"])
def test_no_dev_contract_rejects_default_shell_changes(scope: str) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    if scope == "workflow":
        target = workflow
    else:
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        target = jobs["enum-governance"]
        assert isinstance(target, dict)
    target["defaults"] = {"run": {"shell": "bash -c 'source /tmp/hook; {0}'"}}

    expected = [WORKFLOW_CONTRACT_SCOPE] if scope == "workflow" else ["enum-governance"]
    assert _no_dev_contract_violations(workflow) == expected


@pytest.mark.parametrize("step_field", ["env", "with"])
def test_no_dev_contract_rejects_step_env_and_with_changes(
    step_field: str,
) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "enum-governance")
    if step_field == "env":
        execution_step = next(
            step
            for step in steps
            if step.get("name") == "Run enum governance validator"
        )
        execution_step["env"] = {"UV_BIN": "uv"}
    else:
        setup_step = next(
            step
            for step in steps
            if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
        )
        setup_with = setup_step["with"]
        assert isinstance(setup_with, dict)
        setup_with["version"] = "9.9.9"

    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


def test_no_dev_contract_rejects_step_reordering() -> None:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "enum-governance")
    steps[0], steps[1] = steps[1], steps[0]

    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


@pytest.mark.parametrize(
    "later_sync",
    ["uv sync --frozen", "uv sync --frozen --no-dev"],
)
def test_no_dev_contract_rejects_any_later_sync(later_sync: str) -> None:
    workflow = copy.deepcopy(_ci_workflow())
    steps = _workflow_job_steps(workflow, "enum-governance")
    steps.append({"name": "Later dependency sync", "run": later_sync})

    assert _no_dev_contract_violations(workflow) == ["enum-governance"]


def test_no_dev_contract_rejects_undeclared_safe_no_dev_job() -> None:
    workflow = copy.deepcopy(_ci_workflow())
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    jobs["future-no-dev-job"] = {
        "steps": [
            {"run": "uv sync --frozen --no-dev"},
            {"run": ".venv/bin/python -m example"},
        ]
    }

    assert _no_dev_contract_violations(workflow) == ["future-no-dev-job"]


def test_no_dev_contract_rejects_renamed_no_dev_job() -> None:
    workflow = copy.deepcopy(_ci_workflow())
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    jobs["renamed-enum-governance"] = jobs.pop("enum-governance")

    assert _no_dev_contract_violations(workflow) == [
        "enum-governance",
        "renamed-enum-governance",
    ]


def test_five_minute_job_set_is_dependency_free_and_count_locked() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    five_minute_jobs = {
        job_name
        for job_name, job in data["jobs"].items()
        if job.get("timeout-minutes") == 5
    }

    assert five_minute_jobs == EXPECTED_FIVE_MINUTE_JOBS


def test_cross_repo_boundary_validation_job_is_blocking() -> None:
    job = _ci_job("boundary-validation")

    assert "continue-on-error" not in job


def test_cross_repo_boundary_validation_action_is_not_warn_only() -> None:
    step = _boundary_validation_step()

    assert "continue-on-error" not in step
    assert step["with"]["checks"] == "boundary-parity"
    assert step["with"]["warn-only"] == "false"


def test_cross_repo_boundary_validation_clones_all_boundary_repos() -> None:
    step = _boundary_validation_step()

    repos = {repo.strip() for repo in step["with"]["repos"].split(",")}
    assert repos == {
        "omniclaude",
        "omnidash",
        "omniintelligence",
        "omnibase_infra",
        "omnibase_core",
        "omnimemory",
        "omnimarket",
        "onex_change_control",
    }


def test_ci_summary_is_hosted_no_needs_poller() -> None:
    job = _ci_job("ci-summary")

    assert "needs" not in job
    assert job["runs-on"] == "ubuntu-latest"
    assert job["if"] == "always()"
    assert any(
        "scripts/ci/ci_summary_gate.py" in str(step.get("run", ""))
        for step in job["steps"]
        if isinstance(step, dict)
    )


_TIMEOUT_METHOD_RE = re.compile(r"--timeout-method=(\S+)")


def _has_pytest_token(run: str) -> bool:
    """True when a non-comment line of the run script invokes pytest."""
    return any(
        token == "pytest" or token.endswith("/pytest")
        for line in run.splitlines()
        if not line.lstrip().startswith("#")
        for token in line.split()
    )


def _all_workflow_run_commands() -> list[tuple[str, str, str]]:
    """Every ``(workflow file, job, run script)`` triple in .github/workflows."""
    commands: list[tuple[str, str, str]] = []
    for path in sorted(WORKFLOW_PATH.parent.glob("*.yml")) + sorted(
        WORKFLOW_PATH.parent.glob("*.yaml")
    ):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            continue
        jobs = data.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if isinstance(step, dict) and "run" in step:
                    commands.append((path.name, str(job_name), str(step["run"])))
    return commands


def test_no_workflow_pytest_invocation_uses_thread_timeout_method() -> None:
    """OMN-16348: every ``--timeout-method`` in any workflow must be ``signal``.

    OMN-15977 banned pytest-timeout's ``thread`` method: its watcher thread
    fires only when the GIL is released, so a CPU-bound pure-Python runaway
    holds the GIL continuously and the declared ``--timeout`` ceiling silently
    never fires (the config behind the 2026-08-12 46/53-minute pre-push
    runaways that needed manual SIGKILL). The ban was originally enforced
    per-file (``pyproject.toml`` addopts + the pre-push hook) and missed
    ci.yml, whose explicit CLI flag overrides the addopts ``signal`` default.
    This assertion is per-invocation-surface — the OMN-15977 guards were
    per-file, which is exactly why a third surface stayed invisible — so it
    scans every run step of every workflow file: none may pass
    ``--timeout-method=`` with any value other than ``signal``.
    """
    commands = _all_workflow_run_commands()

    # Positive control: the scanner must actually be seeing ci.yml's pytest
    # steps — an empty scan would vacuously pass while enforcing nothing.
    assert any(
        source == WORKFLOW_PATH.name and _has_pytest_token(run)
        for source, _, run in commands
    )

    violations = [
        f"{source}::{job}: {line.strip()}"
        for source, job, run in commands
        for line in run.splitlines()
        for method in _TIMEOUT_METHOD_RE.findall(line)
        if method != "signal"
    ]
    assert violations == [], (
        "workflow passes a non-signal --timeout-method (banned by OMN-15977; "
        "the explicit CLI flag overrides the addopts signal default): "
        f"{violations}"
    )
