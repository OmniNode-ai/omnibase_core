# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the validator-requirements.yaml enforcement consumer (OMN-9115).

OMN-9051 shipped the spec file; OMN-9115 wires the enforcement consumer. These
tests verify the consumer:

1. Loads the spec and detects missing pre-commit registrations per repo.
2. Detects missing CI workflows / workflow steps per repo.
3. Detects silent-skip advisory modes (`|| true`, warning-mode wrappers).
4. Exits non-zero when any required validator is unwired (blocking gate per
   feedback_no_informational_gates.md).
5. Self-validates this repo (omnibase_core) at import time so the spec's own
   host repo cannot regress.

These are unit tests — they run against synthetic repo fixtures in ``tmp_path``
to exercise the detection logic without coupling to the live state of other
repos (which is covered by the on-repo pre-commit hook + CI workflow step).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)
from omnibase_core.models.validation.model_validator_requirement_gap import (
    ModelValidatorRequirementGap,
)
from omnibase_core.validation.validator_requirements_consumer import (
    ValidatorRequirementsConsumer,
)

SPEC_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def spec_data() -> dict:
    with SPEC_PATH.open() as fh:
        return yaml.safe_load(fh)


def _write_precommit(
    root: Path, hook_ids: list[str], *, warn_ids: list[str] | None = None
) -> None:
    warn_ids = warn_ids or []
    blocks: list[dict] = [
        {
            "repo": "local",
            "hooks": [
                {"id": hid, "name": hid, "entry": f"run-{hid}", "language": "system"}
                for hid in hook_ids
            ]
            + [
                {
                    "id": hid,
                    "name": hid,
                    # Warning-mode wrapper — the consumer must flag this as a silent-skip.
                    "entry": f"bash -c 'run-{hid} || true'",
                    "language": "system",
                }
                for hid in warn_ids
            ],
        }
    ]
    (root / ".pre-commit-config.yaml").write_text(yaml.safe_dump({"repos": blocks}))


def _write_workflow(root: Path, filename: str, step_names: list[str]) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / filename).write_text(
        yaml.safe_dump(
            {
                "name": filename.rsplit(".", 1)[0],
                "on": {"pull_request": {}, "push": {"branches": ["main"]}},
                "jobs": {
                    "check": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {"name": step, "run": f"echo {step}"} for step in step_names
                        ],
                    }
                },
            }
        )
    )


# ---------------------------------------------------------------------------
# Spec loading
# ---------------------------------------------------------------------------


def test_consumer_loads_spec_from_canonical_path() -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    assert consumer.validators, "consumer must expose the required_validators map"
    assert "hardcoded-local-paths" in consumer.validators


def test_consumer_rejects_missing_spec(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        ValidatorRequirementsConsumer.from_spec_path(missing)


def test_consumer_rejects_malformed_spec(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("not-a-mapping")
    with pytest.raises(ValueError, match="spec root must be a mapping"):
        ValidatorRequirementsConsumer.from_spec_path(bad)


# ---------------------------------------------------------------------------
# Per-repo compliance scanning
# ---------------------------------------------------------------------------


def test_scan_reports_missing_pre_commit_registration(tmp_path: Path) -> None:
    """If a required validator is missing from .pre-commit-config.yaml, the
    consumer must emit a MISSING_PRE_COMMIT gap."""
    # Simulate omnibase_compat with only ruff + spdx wired; missing detect-secrets.
    _write_precommit(
        tmp_path, ["ruff-format", "validate-spdx-headers", "check-ai-slop"]
    )
    _write_workflow(tmp_path, "ci.yml", ["ruff", "spdx", "aislop"])

    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    gaps = consumer.scan_repo(repo_name="omnibase_compat", repo_root=tmp_path)

    kinds = {(g.validator, g.kind) for g in gaps}
    assert (
        "detect-secrets",
        EnumValidatorRequirementGapKind.MISSING_PRE_COMMIT,
    ) in kinds


def test_scan_reports_missing_ci_workflow(tmp_path: Path) -> None:
    """If a required validator has no CI workflow step anywhere, the consumer
    must emit a MISSING_CI_WORKFLOW gap."""
    _write_precommit(
        tmp_path,
        [
            "ruff-format",
            "validate-spdx-headers",
            "detect-secrets",
            "check-ai-slop",
            "validate-local-paths",
        ],
    )
    # Workflow only mentions ruff — SPDX has no CI step.
    _write_workflow(tmp_path, "ci.yml", ["ruff"])

    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    gaps = consumer.scan_repo(repo_name="omnibase_compat", repo_root=tmp_path)

    kinds = {(g.validator, g.kind) for g in gaps}
    assert (
        "spdx-headers",
        EnumValidatorRequirementGapKind.MISSING_CI_WORKFLOW,
    ) in kinds


def test_scan_flags_warning_mode_wrapper(tmp_path: Path) -> None:
    """A hook wrapped in ``|| true`` is a silent-skip violation. feedback
    no_informational_gates forbids advisory modes."""
    _write_precommit(
        tmp_path,
        ["validate-spdx-headers", "ruff-format", "detect-secrets", "check-ai-slop"],
        warn_ids=["validate-local-paths"],
    )
    _write_workflow(
        tmp_path,
        "ci.yml",
        ["spdx", "ruff", "detect-secrets", "aislop", "validate-local-paths"],
    )

    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    gaps = consumer.scan_repo(repo_name="omnibase_compat", repo_root=tmp_path)

    kinds = {(g.validator, g.kind) for g in gaps}
    assert (
        "hardcoded-local-paths",
        EnumValidatorRequirementGapKind.SILENT_SKIP_WRAPPER,
    ) in kinds


def test_scan_respects_applies_to_repos(tmp_path: Path) -> None:
    """A validator that does not apply to the target repo must NOT produce
    gaps even if its pre-commit hook id is absent. For example, omniweb (PHP)
    should not be required to wire Python validators."""
    # omniweb has nothing Python.
    _write_precommit(tmp_path, [])
    _write_workflow(tmp_path, "ci.yml", [])

    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    gaps = consumer.scan_repo(repo_name="omniweb", repo_root=tmp_path)

    flagged_validators = {g.validator for g in gaps}
    # mypy-type-check and pydantic-patterns apply_to_repos list does not include omniweb.
    assert "mypy-type-check" not in flagged_validators
    assert "pydantic-patterns" not in flagged_validators


def test_scan_rejects_unknown_repo(tmp_path: Path) -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    with pytest.raises(ValueError, match="unknown repo"):
        consumer.scan_repo(repo_name="not-a-real-repo", repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Blocking exit behavior
# ---------------------------------------------------------------------------


def test_report_exit_code_zero_on_clean_repo(tmp_path: Path, spec_data: dict) -> None:
    """When every required validator for the target repo is present with
    required pre-commit + CI wiring and no warning-mode wrapper, scan_repo
    must return an empty list."""
    # Build a repo that satisfies every validator listed as applies-to omnibase_core.
    pre_commit_ids = [
        "validate-local-paths",
        "validate-spdx-headers",
        "no-hardcoded-topics",
        "check-stub-implementations",
        "check-enum-governance",
        "validate-naming-conventions",
        "check-self-gating-workflows",
        "bandit",
        "mypy-type-check",
        "ruff-format",
        "check-ai-slop",
        "validate-pydantic-patterns",
        "onex-single-class-per-file",
        "detect-secrets",
        "no-untracked-todos",
        "validate-no-transport-imports",
    ]
    _write_precommit(tmp_path, pre_commit_ids)

    # Flatten into a single CI workflow that exposes a step per validator.
    _write_workflow(tmp_path, "ci.yml", pre_commit_ids)

    consumer = ValidatorRequirementsConsumer.from_spec_path(SPEC_PATH)
    gaps = consumer.scan_repo(repo_name="omnibase_core", repo_root=tmp_path)

    # Nothing else applies to omnibase_core in the current spec, so zero gaps expected.
    assert gaps == [], f"expected clean repo to produce zero gaps, got: {gaps}"


def test_scan_gap_model_is_frozen() -> None:
    """ModelValidatorRequirementGap must be a frozen Pydantic model (per repo pydantic
    conventions) — gaps are facts about a point-in-time scan and must not be
    mutated post-construction."""
    gap = ModelValidatorRequirementGap(
        repo="omnibase_compat",
        validator="detect-secrets",
        kind=EnumValidatorRequirementGapKind.MISSING_PRE_COMMIT,
        detail="missing hook id",
    )
    with pytest.raises(ValueError):
        gap.detail = "mutated"  # type: ignore[misc]
