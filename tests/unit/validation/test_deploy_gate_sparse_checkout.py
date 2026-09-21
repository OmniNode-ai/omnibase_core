# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Prove deploy-gate imports work from its exact sparse support checkout."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

if TYPE_CHECKING:
    import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github/workflows/deploy-gate-reusable.yml"


def _sparse_checkout_paths() -> list[str]:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name") == "Fetch deploy-gate support scripts (omnibase_core)":
                return step["with"]["sparse-checkout"].splitlines()
    raise AssertionError("deploy-gate support checkout step was not found")


def _materialize_sparse_checkout(destination: Path, entries: list[str]) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    ).stdout.split(b"\0")
    for raw_path in tracked:
        if not raw_path:
            continue
        source_path = raw_path.decode("utf-8")
        if not any(
            source_path == entry.rstrip("/")
            or source_path.startswith(entry.rstrip("/") + "/")
            for entry in entries
        ):
            continue
        source = _REPO_ROOT / source_path
        target = destination / source_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_sparse_checkout_contains_and_runs_typed_deploy_evidence_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A git hook exports these values; without the canonical scrub, they
    # override ``cwd`` and retarget this source inventory query.
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "hostile.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "hostile-worktree"))
    support = tmp_path / "support"
    support.mkdir()
    entries = _sparse_checkout_paths()
    _materialize_sparse_checkout(support, entries)

    action = support / ".github/actions/deploy-gate"
    validator = action / "validate_pr_deploy_required.py"
    projection = action / "models/deploy_evidence_contract.py"
    assert validator.is_file()
    assert projection.is_file()

    contract = tmp_path / "contract.yaml"
    contract.write_text(
        """ticket_id: OMN-123
title: Runtime deployment
dod_evidence:
  - id: deploy
    description: Read deployment result
    source: command
    checks:
      - check_type: command
        check_value: docker inspect deployed service
""",
        encoding="utf-8",
    )
    malformed_contract = tmp_path / "malformed-contract.yaml"
    malformed_contract.write_text(
        """dod_evidence:
  - id: deploy
    description: Read deployment result
    source: command
    checks:
      - check_type: command
        check_value: docker inspect deployed service
        unknown: rejected
""",
        encoding="utf-8",
    )
    invocation = """
import importlib.util
import importlib
import json
from pathlib import Path
import sys
action = Path(sys.argv[1])
sys.path.insert(0, str(action))
spec = importlib.util.spec_from_file_location(
    "deploy_gate_validator", action / "validate_pr_deploy_required.py"
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
model_modules = (
    "models.deploy_evidence_contract",
    "models.deploy_evidence_item",
    "models.deploy_evidence_check",
)
model_package = importlib.import_module("models")
for name in model_modules:
    importlib.import_module(name)
model_paths = {
    "models": str(Path(model_package.__file__).resolve()),
    **{
        name: str(Path(sys.modules[name].__file__).resolve())
        for name in model_modules
    },
}
assert all(
    Path(path).is_relative_to(action.resolve()) for path in model_paths.values()
)
print(
    json.dumps(
        {
            "deploy_evidence": module.has_deploy_evidence(Path(sys.argv[2])),
            "malformed_evidence": module.has_deploy_evidence(Path(sys.argv[3])),
            "model_paths": model_paths,
        }
    )
)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            invocation,
            str(action),
            str(contract),
            str(malformed_contract),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["deploy_evidence"] is True
    assert response["malformed_evidence"] is False
    assert all(
        Path(path).is_relative_to(action.resolve())
        for path in response["model_paths"].values()
    )
