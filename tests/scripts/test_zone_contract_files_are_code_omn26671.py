# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26671: a contract-only diff is not docs-only.

omnimarket#6815 changed one file, ``contracts/OMN-22577.yaml``. The zone filter
counted ``contracts/`` as documentation, so the heavy matrix and every test
split were skipped and the contract-shape tests that refuse a bad entry never
ran. These cases pin the recorded file list of that pull request and its
neighbours.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_file_zone import EnumFileZone
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract
from omnibase_core.validation.zone_classifier import classify_path
from scripts.ci.detect_test_paths import compute_selection

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
ADJACENCY = REPO_ROOT / "scripts" / "ci" / "test_selection_adjacency.yaml"
# omnimarket#6815 (merge 52a9984662): the whole recorded file list.
PR_6815_FILES = ["contracts/OMN-22577.yaml"]


def _docs_only_exit(diff: str) -> int:
    env = {
        "ZONE_DIFF_FILTER_FAKE_DIFF": diff,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "zone_diff_filter.py"),
            "--check",
            "docs-only",
        ],
        env=env,
        cwd=REPO_ROOT,
        check=False,
    ).returncode


def test_pr_6815_file_list_is_not_docs_only() -> None:
    assert _docs_only_exit(",".join(PR_6815_FILES)) == 1


def test_pr_6815_file_list_selects_the_contract_shape_tests() -> None:
    assert all(classify_path(Path(p)) != EnumFileZone.DOCS for p in PR_6815_FILES)
    selection = compute_selection(
        PR_6815_FILES, ADJACENCY, "dev", pyproject_dependency_relevant=False
    )
    selected = set(selection.selected_paths)
    assert selected, "a contract-only diff must select tests"
    assert "tests/ci/" in selected
    assert (REPO_ROOT / "tests/ci/test_repo_evidence_caller_omn20074.py").is_file(), (
        "the contract-shape test lives under a selected root"
    )


def test_a_docs_only_diff_still_skips() -> None:
    docs = "docs/architecture.md,README.md,drift/dod_receipts/x.yaml,.evidence/x.yaml"
    assert _docs_only_exit(docs) == 0
    selection = compute_selection(
        ["docs/architecture.md", "README.md"],
        ADJACENCY,
        "dev",
        pyproject_dependency_relevant=False,
    )
    assert selection.selected_paths == []


def test_contract_mixed_with_docs_is_not_docs_only() -> None:
    assert _docs_only_exit("docs/x.md,contracts/OMN-22577.yaml") == 1


def test_a_bad_contract_entry_is_refused_by_the_contract_shape_model() -> None:
    """Known bad: a sole file_exists item is refused; the corrected one passes.

    The refusal only guards a contract-only diff when the filter sends that
    diff to the tests, so the test also pins that reachability (red on base).
    """
    assert _docs_only_exit("contracts/OMN-20074.yaml") == 1
    good = yaml.safe_load(
        (REPO_ROOT / "contracts" / "OMN-20074.yaml").read_text(encoding="utf-8")
    )
    ModelTicketContract.from_yaml(yaml.safe_dump(good))
    bad = yaml.safe_load(yaml.safe_dump(good))
    bad["dod_evidence"][0]["checks"] = [
        {"check_type": "file_exists", "check_value": "x"}
    ]
    with pytest.raises(Exception, match="file_exists"):
        ModelTicketContract.from_yaml(yaml.safe_dump(bad))
