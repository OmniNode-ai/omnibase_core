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

NO_DEV_WORKFLOW_EXECUTION_CONTRACT = "d7dfb006ec524bc384a900b284fc56cbf2a3d7d00a9e1709906ed4e5aebb0d8e"  # pragma: allowlist secret

# SHA-256 over canonical JSON of each complete audited guard job. No job key is
# excluded: steps, env, defaults, container, runs-on, if, continue-on-error,
# strategy, needs, permissions, timeout, and future job-level keys are all part
# of the contract. Updating a digest requires auditing the readable workflow
# diff first; this deliberately avoids another partial execution-surface list.
AUDITED_GUARD_JOB_EXECUTION_CONTRACTS = {
    "exports-validation": (
        "54ac4c9daa5992acfd905b46e1d994db0091303b779bc179da509a9ed9184f4e"  # pragma: allowlist secret
    ),
    "mypy-validation-scripts": (
        "05cb980f356187d9a359d068b136553085243698d2286fe55e8800b68138d79d"  # pragma: allowlist secret
    ),
    "core-infra-boundary": (
        "403fa52e3d6f4b8954bc692c6ec40d133278cc00cc34807fa7552732866275ad"  # pragma: allowlist secret
    ),
    "check-deterministic-skills": (
        "8f0e02654254289640c6298ed043de77e3b3ce203421c8e1e4f229a9afd2e717"  # pragma: allowlist secret
    ),
    "node-purity-check": (
        "b633627655c01a98bcce39c4e998529c976659f10cdd70f1a5969772bf8444eb"  # pragma: allowlist secret
    ),
    "enum-governance": (
        "b2e4c2e5fc424c462712c9b4d48aea0cb85af1c67d4000f556f4b6ddf56bc215"  # pragma: allowlist secret
    ),
    "contract-config-compliance": (
        "83cd9a9099bc9f063e98b64bc03cb576290ebc545ae310ee7e41fbe73e29f95c"  # pragma: allowlist secret
    ),
    "breaking-schema-change": (
        "ee0658f793f00e8e6f179d913343d37504e128dcf73a459b075230adae4a64d8"  # pragma: allowlist secret
    ),
    "no-env-fallbacks": (
        "a0f24383df3a8974b1615035d4df05eb67924a1cda40d9c7a7f85379d816a475"  # pragma: allowlist secret
    ),
    "detect-secrets": (
        "e52c18585e93fd68b8ea8e1db1689fb5bd255e352e176e362b359ede4f346d9b"  # pragma: allowlist secret
    ),
    "version-pin-check": (
        "ade3ee77ab47c64b1cfc44f135116eec3d290c7505a30e54d8093c27a56f59bb"  # pragma: allowlist secret
    ),
    "sdk-boundary-check": (
        "75dc4af7bbf72d5b9cf033d906ebefa51b95bd43c2c89acac430e526e3af923e"  # pragma: allowlist secret
    ),
    "demo-path-topic-coherence": (
        "94bf6dfc92a03f6c281789316292e59c61ef6d7cd3aca07aae1f2e710d5da094"  # pragma: allowlist secret
    ),
    "dispatch-surface-test-required": (
        "7f292453c6e38618c81f8e39e6361183e936ed6fbcdf9823b3a4b6cb1d1fcd81"  # pragma: allowlist secret
    ),
    "naming-conventions": (
        "4c018ad075660fc1c8d68c65c84c00b5c7bcd82ba4a70267baa7f6e2ce377aa7"  # pragma: allowlist secret
    ),
    "pydantic-patterns": (
        "0c69ccc1414177fc6b8ce43a34990d8fbd3c63de3ad58a0dc0eb735cf95d8f1b"  # pragma: allowlist secret
    ),
    "aislop-patterns": (
        "677edc4eb5c9e263658b04262fc5830a80a9888fbe03b365c76ceb8d58be8319"  # pragma: allowlist secret
    ),
    "doc-content-scan": (
        "83527bb968e8fec272ecb192139b9d941fc8247ae70ec4dbd446a7a1adaddff4"  # pragma: allowlist secret
    ),
    "spdx-headers": (
        "5ba1941f8549116b224e51ea893864bae25febdbb0e0eafae8f5cf268d7613f0"  # pragma: allowlist secret
    ),
    "no-new-os-environ": (
        "486c2017dc4561d97747ff09d30819011a8aee9a1f30e844ff3b40ca97c2bcdf"  # pragma: allowlist secret
    ),
    "duplicate-registry-ids": (
        "c457353e5aa56dda35a5d34b968e393024e84c3ac60a64bb964fbf52c304e691"  # pragma: allowlist secret
    ),
    "no-noncanonical-lifecycle-classes": (
        "5cae23b307954cd43c5e17198715700a045986a07bb3f5a2941c334936de6b5a"  # pragma: allowlist secret
    ),
    "pull-request-workflow-ratchet": (
        "4e10b330674d98df5a7341802e88b8471ff2e4e675c510a37e745373e362e91b"  # pragma: allowlist secret
    ),
}

OTHER_AUDITED_GUARD_JOBS = {
    "core-infra-boundary",
    "check-deterministic-skills",
    "detect-secrets",
    "version-pin-check",
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
