# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: contract-validation validates with the in-tree ModelTicketContract.

OCC retirement S8. The workflow used to check out the change-control repository
at a pinned sha and run its ``validate-yaml``. It now validates the branch
ticket's ``contracts/<ticket>.yaml`` with this repository's own
``ModelTicketContract``, run through ``uv run`` against the checked-out source,
so there is no PyPI pin to drift behind the model. The required context name
``contract-validation`` does not change.

Failure modes this catches: a change-control reference creeping back in
(checkout, auth preflight, ``validate-yaml``); the validation step validating
with anything but the in-tree ``ModelTicketContract`` (a ``--with
omnibase-core==`` pin would validate against a published copy instead); the job
or workflow name moving and retiring the required context; the skip semantics
changing; and the extracted validator no longer failing an invalid contract.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "contract-validation.yml"
VALID_CONTRACT = REPO_ROOT / "contracts" / "OMN-20074.yaml"
MODEL_MODULE = "omnibase_core.models.ticket.model_ticket_contract"
FORBIDDEN_REFERENCE = re.compile(
    r"onex[_-]change[_-]control|validate-yaml", re.IGNORECASE
)
HEREDOC = re.compile(r"<<\s*'(?P<tag>\w+)'\n(?P<body>.*?)\n\s*(?P=tag)\n", re.DOTALL)


def _doc() -> dict[Any, Any]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _steps() -> list[dict[str, Any]]:
    return _doc()["jobs"]["contract-validation"]["steps"]


def _validation_step() -> dict[str, Any]:
    matches = [step for step in _steps() if step.get("id") == "validate-contract"]
    assert len(matches) == 1
    return matches[0]


def _validator_source() -> str:
    heredocs = HEREDOC.findall(_validation_step()["run"])
    assert len(heredocs) == 1, "exactly one inline validator in the validation step"
    return heredocs[0][1]


def _run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-", str(path)],
        input=_validator_source() + "\n",
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_workflow_names_no_change_control_repository() -> None:
    offenders = [
        number
        for number, line in enumerate(
            WORKFLOW.read_text(encoding="utf-8").splitlines(), 1
        )
        if FORBIDDEN_REFERENCE.search(line)
    ]
    assert offenders == [], f"change-control references at lines {offenders}"


def test_reference_detector_sees_a_planted_change_control_checkout() -> None:
    """Positive control: the scan above flags the shapes this change removed."""
    planted = (
        "repository: OmniNode-ai/onex_change_control",
        "path: .onex_change_control_validators",
        "uv run validate-yaml ../contracts/OMN-1.yaml",
        "gh api repos/OmniNode-ai/onex_change_control --silent",
    )
    for line in planted:
        assert FORBIDDEN_REFERENCE.search(line), line


def test_workflow_checks_out_only_the_calling_repository() -> None:
    checkouts = [
        step
        for step in _steps()
        if str(step.get("uses", "")).startswith("actions/checkout")
    ]
    assert checkouts, "the calling repository must be checked out"
    for step in checkouts:
        assert "repository" not in (step.get("with") or {}), step.get("name")


def test_required_context_name_is_unchanged() -> None:
    doc = _doc()
    assert doc["name"] == "Contract Validation"
    assert "contract-validation" in doc["jobs"]
    assert doc["jobs"]["contract-validation"]["name"] == "contract-validation"


def test_validation_step_validates_with_the_in_tree_model_not_a_published_pin() -> None:
    run = _validation_step()["run"]
    assert not re.search(r"omnibase[-_]core\s*[=<>~!]", run), (
        "a published omnibase-core pin would validate against a copy, not this tree"
    )
    assert "--with" not in run
    tree = ast.parse(_validator_source())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == MODEL_MODULE
        for alias in node.names
    }
    assert imported == {"ModelTicketContract"}
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "model_validate"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ModelTicketContract"
        for node in ast.walk(tree)
    )


def test_validation_step_skips_without_a_ticket_or_a_contract_and_fails_on_an_invalid_one() -> (
    None
):
    run = _validation_step()["run"]
    assert run.count("validation-status=skipped") == 2
    assert "validation-status=passed" in run
    assert "validation-status=failed" in run
    assert "merge_group" in "".join(
        str(step.get("env", "")) + str(step.get("run", "")) for step in _steps()
    )


def test_extracted_validator_passes_a_valid_contract() -> None:
    result = _run_validator(VALID_CONTRACT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK]" in result.stdout


def test_extracted_validator_fails_an_invalid_contract(tmp_path: Path) -> None:
    """Positive control: the extracted validator refuses a planted bad contract."""
    data = yaml.safe_load(VALID_CONTRACT.read_text(encoding="utf-8"))
    data["unknown_top_level_field"] = "extra=forbid must refuse this"
    planted = tmp_path / "OMN-20074.yaml"
    planted.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = _run_validator(planted)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "::error file=" in result.stdout


def test_extracted_validator_fails_a_malformed_yaml_file(tmp_path: Path) -> None:
    planted = tmp_path / "OMN-20074.yaml"
    planted.write_text("ticket_id: [unterminated\n", encoding="utf-8")
    result = _run_validator(planted)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "YAML parse error" in result.stdout
