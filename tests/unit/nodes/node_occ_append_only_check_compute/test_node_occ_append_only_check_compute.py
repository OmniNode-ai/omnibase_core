# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_occ_append_only_check_compute."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_append_only_violation_kind import (
    EnumAppendOnlyViolationKind,
)
from omnibase_core.models.nodes.occ_append_only_check.model_occ_append_only_check_input import (
    ModelOccAppendOnlyCheckInput,
)
from omnibase_core.nodes.node_occ_append_only_check_compute.handler import (
    NodeOccAppendOnlyCheckCompute,
)
from omnibase_core.nodes.node_occ_append_only_check_compute.runtime_occ_append_only_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

TICKET = "OMN-99999"


def _contract(items: dict[str, str]) -> dict[str, object]:
    return {
        "ticket_id": TICKET,
        "dod_evidence": [
            {"id": item_id, "description": text} for item_id, text in items.items()
        ],
    }


def test_handle_passes_when_only_appended() -> None:
    result = NodeOccAppendOnlyCheckCompute().handle(
        ModelOccAppendOnlyCheckInput(
            base_contract=_contract({"a": "one"}),
            head_contract=_contract({"a": "one", "b": "two"}),
        )
    )
    assert result.ok
    assert result.violations == ()


def test_handle_fails_when_entry_removed_and_receipt_modified() -> None:
    result = NodeOccAppendOnlyCheckCompute().handle(
        ModelOccAppendOnlyCheckInput(
            base_contract=_contract({"a": "one"}),
            head_contract=_contract({"b": "two"}),
            receipt_diff=(("M", f"drift/dod_receipts/{TICKET}/a/test.yaml"),),
        )
    )
    assert not result.ok
    assert result.reason == "APPEND_ONLY_VIOLATION"
    assert {v.kind for v in result.violations} == {
        EnumAppendOnlyViolationKind.ENTRY_REMOVED,
        EnumAppendOnlyViolationKind.RECEIPT_FILE_MUTATED,
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(),
    )


def _init_repo(tmp_path: Path, head_items: dict[str, str]) -> Path:
    repo = tmp_path / "occ"
    (repo / "contracts").mkdir(parents=True)
    contract_path = repo / "contracts" / f"{TICKET}.yaml"
    _git(tmp_path, "init", "-q", "-b", "dev", str(repo))
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")
    contract_path.write_text(yaml.safe_dump(_contract({"a": "one"})), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "feature")
    contract_path.write_text(yaml.safe_dump(_contract(head_items)), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "head")
    return repo


def test_main_exit_codes(tmp_path: Path) -> None:
    ok_repo = _init_repo(tmp_path / "ok", {"a": "one", "b": "two"})
    args = ["--ticket-id", TICKET, "--base-ref", "dev"]
    assert main(["--repo", str(ok_repo), *args]) == 0
    bad_repo = _init_repo(tmp_path / "bad", {"a": "edited"})
    assert main(["--repo", str(bad_repo), *args]) == 1
