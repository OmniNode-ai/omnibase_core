# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import hashlib
import json
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
    "mypy-validation-scripts": ("uv sync --frozen", 7),
    "enum-governance": ("uv sync --frozen --no-dev", 7),
    "contract-config-compliance": ("uv sync --frozen --no-dev", 7),
    "breaking-schema-change": ("uv sync --frozen --no-dev", 7),
    "sdk-boundary-check": ("uv sync --frozen", 7),
    "demo-path-topic-coherence": ("uv sync --frozen --no-dev", 7),
    "dispatch-surface-test-required": ("uv sync --frozen --no-dev", 7),
    "aislop-patterns": ("uv sync --frozen --no-dev", 7),
    "doc-content-scan": ("uv sync --frozen --no-dev", 6),
    "spdx-headers": ("uv sync --frozen --no-dev", 6),
    "no-new-os-environ": ("uv sync --frozen --no-dev", 6),
    "duplicate-registry-ids": ("uv sync --frozen", 7),
    "no-noncanonical-lifecycle-classes": ("uv sync --frozen --no-dev", 7),
    "pull-request-workflow-ratchet": ("uv sync --frozen --no-dev", 6),
}

NO_DEV_WORKFLOW_EXECUTION_CONTRACT = (
    "d7dfb006ec524bc384a900b284fc56cbf2a3d7d00a9e1709906ed4e5aebb0d8e"
)

# SHA-256 over canonical JSON of each job's complete ordered steps plus inherited
# job env/defaults. This locks every run/uses step and every step key, including
# with/env/if/id/shell, without attempting to interpret shell syntax. Updating a
# digest requires auditing the readable workflow diff first.
NO_DEV_JOB_EXECUTION_CONTRACTS = {
    "enum-governance": (
        "4f9d527f1dbc432d05852d1e86d006adbb92cbeb1445cbc5aedb4275d2db7b6b"
    ),
    "contract-config-compliance": (
        "856550ce6318cf4e5ef2c623561019f2b1d389f57f7277aa65df421913cf74b3"
    ),
    "breaking-schema-change": (
        "5b3d3a100c83ff8d5cccf5cc316c17e1c2cf888be3555fbf23fd2bcfd20c89f9"
    ),
    "demo-path-topic-coherence": (
        "ac6c4c93b7b73ca86ffb9079b3f704a7bf4ed0722a2816e3e9f8150d96bb1d13"
    ),
    "dispatch-surface-test-required": (
        "e3ab562dbc0eea02827d3203928ffbb63b8f05224f6f58f97579c8a0f80690a8"
    ),
    "aislop-patterns": (
        "3a89cbab7e77abb9f4d1d16ad6ce2f99b13340889b38e75e745f7c9cea74ec8c"
    ),
    "doc-content-scan": (
        "ec5409c441f9a9db7cbb452626de866d111a95daad9b2f4e39fd8a7d1f4c61ef"
    ),
    "spdx-headers": (
        "8efdce9449a64b7759ab9cefd6a88c35133ddc964a27d8e3cf345b6d4fb81cdb"
    ),
    "no-new-os-environ": (
        "405eb439e6c2c4861eddf69c0b0bd628fa4af77f1aa4942c30507c9e366e4ebc"
    ),
    "no-noncanonical-lifecycle-classes": (
        "c98604598238d5543f1f6786f6b540d8eeeba0a825cb6747fb84d97784d65664"
    ),
    "pull-request-workflow-ratchet": (
        "ed0d0b95a8a02f19d98526cf9255443c7782cf8da72e4b00587f6781853ff412"
    ),
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


def _job_execution_surface(job: dict[str, object]) -> dict[str, object]:
    return {
        "steps": job.get("steps", []),
        "env": job.get("env", {}),
        "defaults": job.get("defaults", {}),
    }


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

    declared_jobs = set(NO_DEV_JOB_EXECUTION_CONTRACTS)
    discovered_jobs = _literal_no_dev_job_names(workflow)
    violations.update(declared_jobs.symmetric_difference(discovered_jobs))

    workflow_env_keys = _env_keys(workflow)
    if (
        workflow_env_keys is None
        or workflow_env_keys & FORBIDDEN_EXECUTION_ENV_KEYS
        or _execution_contract_digest(_workflow_execution_surface(workflow))
        != NO_DEV_WORKFLOW_EXECUTION_CONTRACT
    ):
        violations.add(WORKFLOW_CONTRACT_SCOPE)

    for job_name, expected_digest in NO_DEV_JOB_EXECUTION_CONTRACTS.items():
        job = jobs.get(job_name)
        if not isinstance(job, dict):
            violations.add(job_name)
            continue

        job_env_keys = _env_keys(job)
        if (
            job_env_keys is None
            or job_env_keys & FORBIDDEN_EXECUTION_ENV_KEYS
            or _execution_contract_digest(_job_execution_surface(job))
            != expected_digest
        ):
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

    assert _literal_no_dev_job_names(workflow) == set(NO_DEV_JOB_EXECUTION_CONTRACTS)
    assert set(NO_DEV_DIRECT_EXECUTABLES) == set(NO_DEV_JOB_EXECUTION_CONTRACTS)
    for job_name in NO_DEV_JOB_EXECUTION_CONTRACTS:
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
