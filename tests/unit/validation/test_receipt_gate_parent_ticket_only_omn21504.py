# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A PR whose only cited ticket is a parent ticket is refused (OMN-21504).

The parent tickets are the ``dod_verify`` overlay's ``parent_tickets``. The
Python predicate and the receipt-gate ``parent_only`` step must agree: both are
exercised here, the step as the bash the runner executes. Fixture ticket ids
are invented.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.models.config_overlay import ModelDodVerifyOverlay
from omnibase_core.validation.validator_receipt_gate import (
    find_parent_only_citation,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
SCHEMA_PATH = (
    REPO_ROOT
    / "src"
    / "omnibase_core"
    / "schemas"
    / "config_overlay"
    / "dod_verify.schema.json"
)

PARENT = "OMN-90001"
TASK = "OMN-90002"
OVERLAY_WITH_PARENT = {
    "schema_version": "dod_verify.v1",
    "parent_tickets": [PARENT],
}
OVERLAY_WITHOUT_PARENT = {
    "schema_version": "dod_verify.v1",
    "parent_tickets": ["OMN-90003"],
}


def _step() -> dict[str, Any]:
    steps = yaml.safe_load(WORKFLOW_PATH.read_text())["jobs"]["dod-verify"]["steps"]
    return next(s for s in steps if s.get("id") == "parent_only")


def _run_step(
    tmp_path: Path, cited: list[str], overlay: dict[str, Any] | str
) -> subprocess.CompletedProcess[str]:
    step = _step()
    script = str(step["run"])
    assert "${{" not in script
    dod = tmp_path / "dod"
    dod.mkdir(parents=True)
    (dod / "tickets.txt").write_text("".join(f"{t}\n" for t in cited))
    overlay_text = overlay if isinstance(overlay, str) else json.dumps(overlay)
    assert set(step["env"]) == {"DOD_VERIFY_OVERLAY"}
    return subprocess.run(
        ["/bin/bash", "-c", script],
        env={
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin",
            "RUNNER_TEMP": str(tmp_path),
            "DOD_VERIFY_OVERLAY": overlay_text,
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )


def test_overlay_key_and_schema_are_registered() -> None:
    assert EnumConfigOverlayKey("dod_verify").schema_ref == "omnibase_core:dod_verify"
    assert (
        json.loads(SCHEMA_PATH.read_text()) == ModelDodVerifyOverlay.model_json_schema()
    )


def test_overlay_rejects_non_ticket_ids_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ModelDodVerifyOverlay.model_validate(
            {"schema_version": "dod_verify.v1", "parent_tickets": ["not-a-ticket"]}
        )
    with pytest.raises(ValidationError):
        ModelDodVerifyOverlay.model_validate({**OVERLAY_WITH_PARENT, "extra": 1})


def test_predicate_refuses_parent_only_citation_naming_the_ticket() -> None:
    overlay = ModelDodVerifyOverlay.model_validate(OVERLAY_WITH_PARENT)
    assert find_parent_only_citation([PARENT], overlay.parent_tickets) == (PARENT,)


def test_predicate_control_task_ticket_is_not_refused() -> None:
    overlay = ModelDodVerifyOverlay.model_validate(OVERLAY_WITH_PARENT)
    assert find_parent_only_citation([TASK], overlay.parent_tickets) == ()
    assert find_parent_only_citation([PARENT, TASK], overlay.parent_tickets) == ()


def test_predicate_cited_nothing_is_not_this_checks_refusal() -> None:
    assert find_parent_only_citation([], (PARENT,)) == ()


def test_step_refuses_a_pr_citing_only_the_parent(tmp_path: Path) -> None:
    result = _run_step(tmp_path, [PARENT], OVERLAY_WITH_PARENT)
    assert result.returncode != 0
    assert PARENT in result.stdout + result.stderr


def test_step_control_pr_citing_a_task_ticket_passes(tmp_path: Path) -> None:
    result = _run_step(tmp_path, [TASK], OVERLAY_WITH_PARENT)
    assert result.returncode == 0, result.stderr


def test_step_mixed_parent_and_task_citation_passes(tmp_path: Path) -> None:
    result = _run_step(tmp_path, [PARENT, TASK], OVERLAY_WITH_PARENT)
    assert result.returncode == 0, result.stderr


def test_same_pr_is_verified_under_an_overlay_that_omits_the_ticket(
    tmp_path: Path,
) -> None:
    refused = _run_step(tmp_path / "a", [PARENT], OVERLAY_WITH_PARENT)
    verified = _run_step(tmp_path / "b", [PARENT], OVERLAY_WITHOUT_PARENT)
    assert refused.returncode != 0
    assert verified.returncode == 0, verified.stderr


def test_step_with_no_overlay_configured_lists_no_parent(tmp_path: Path) -> None:
    result = _run_step(tmp_path, [PARENT], "")
    assert result.returncode == 0, result.stderr


def test_step_refuses_an_overlay_that_is_not_valid_json(tmp_path: Path) -> None:
    result = _run_step(tmp_path, [TASK], "{not json")
    assert result.returncode != 0


def test_later_steps_wait_on_the_parent_check() -> None:
    steps = yaml.safe_load(WORKFLOW_PATH.read_text())["jobs"]["dod-verify"]["steps"]
    ids = [s.get("id") for s in steps]
    assert ids.index("tickets") < ids.index("parent_only") < ids.index("head_checkout")
    guarded = next(s for s in steps if s.get("id") == "head_checkout")
    assert "steps.parent_only.outcome != 'failure'" in guarded["if"]


def test_parent_check_reads_only_the_resolved_tickets_and_the_overlay() -> None:
    script = str(_step()["run"])
    for network_reader in ("gh ", "curl", "wget", "linear"):
        assert network_reader not in script
    assert "tickets.txt" in script


def test_core_requires_repo_evidence_dod_verify_on_dev() -> None:
    manifest = yaml.safe_load(
        (REPO_ROOT / ".github" / "required-checks.yaml").read_text(encoding="utf-8")
    )
    rows = [g for g in manifest["gates"] if g["name"] == "repo-evidence / dod-verify"]
    assert len(rows) == 1
    assert rows[0]["mode"] == "REQUIRED"
    assert rows[0]["branch"] == "dev"
    assert rows[0]["job_path"] == ["repo-evidence", "dod-verify"]


def test_caller_pins_the_reusable_and_the_verifier_by_dev_merge_tag() -> None:
    caller = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "call-repo-evidence-gate.yml").read_text(
            encoding="utf-8"
        )
    )
    job = caller["jobs"]["repo-evidence"]
    assert job["uses"].startswith(
        "OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@dev-"
    )
    assert str(job["with"]["verifier-tag"]).startswith("dev-")
