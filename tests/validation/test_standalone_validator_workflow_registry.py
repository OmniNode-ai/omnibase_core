# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the standalone-validator-workflow classification gate (OMN-14430).

``test_live_ci_rollup_is_airtight`` (test_validator_rollup_coverage.py) can only
speak to the small set of validators governed by
architecture-handshakes/validator-requirements.yaml. Most of omnibase_core's
``.github/workflows/validator-*.yml`` files are NOT part of that governed spec at
all, and a file in that class which independently triggers on ``pull_request``
gets its own ``github.run_id`` — structurally invisible to ``ci.yml``'s
``ci-summary`` default-deny poller regardless of the governed spec. These tests
prove the closing registry (``standalone-validator-debt.yaml``) actually
classifies every such file, and that the classification cannot silently go
stale.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.validator_standalone_workflow_registry import (
    verify_standalone_validator_registry,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEBT_MANIFEST_PATH = (
    REPO_ROOT / "architecture-handshakes" / "standalone-validator-debt.yaml"
)


def test_live_registry_is_airtight() -> None:
    """Every live validator-*.yml that gates on pull_request must be classified;
    every classified entry must still match a live file."""
    gaps = verify_standalone_validator_registry(
        repo_root=REPO_ROOT, debt_manifest_path=DEBT_MANIFEST_PATH
    )
    assert not gaps, "standalone-validator classification gaps:\n" + "\n".join(
        f"  {g.workflow_file} — {g.detail}" for g in gaps
    )


def test_decorative_debt_is_the_reported_count(tmp_path: Path) -> None:
    """Locks the OMN-14430 audit count so a silent increase (a NEW decorative
    validator shipped without classification) or an unnoticed decrease (an
    entry quietly dropped without migrating/fixing the underlying file) both
    fail loud. Migrating an entry to `migrated_into_ci_yml` legitimately lowers
    this number — update the constant in the same PR as the migration."""
    manifest = yaml.safe_load(DEBT_MANIFEST_PATH.read_text(encoding="utf-8"))
    # OMN-14877 (2026-07-21): the 18 remaining decorative validators were
    # batch-migrated into ci.yml and reclassified to migrated_into_ci_yml. The
    # one remaining advisory entry is OMN-14891's git-env-isolation validator
    # from current dev.
    assert len(manifest["decorative_debt"]) == 1


def test_planted_undeclared_standalone_validator_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a new validator-*.yml that triggers on pull_request and
    is not classified anywhere must be flagged."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "validator-new-undeclared-check.yml").write_text(
        yaml.safe_dump(
            {
                "name": "New Undeclared Check",
                "on": {"pull_request": {}},
                "jobs": {"validate": {"name": "validate"}},
            }
        ),
        encoding="utf-8",
    )
    empty_manifest = tmp_path / "standalone-validator-debt.yaml"
    empty_manifest.write_text(
        yaml.safe_dump(
            {
                "migrated_into_ci_yml": [],
                "natively_required_contexts": [],
                "decorative_debt": [],
            }
        ),
        encoding="utf-8",
    )
    gaps = verify_standalone_validator_registry(
        repo_root=tmp_path, debt_manifest_path=empty_manifest
    )
    offenders = {g.workflow_file for g in gaps}
    assert "validator-new-undeclared-check.yml" in offenders


def test_planted_stale_entry_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a decorative_debt entry that no longer matches a live
    file (retired without updating the registry) must be flagged."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    manifest_path = tmp_path / "standalone-validator-debt.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "migrated_into_ci_yml": [],
                "natively_required_contexts": [],
                "decorative_debt": [
                    {"workflow_file": "validator-long-gone.yml", "context": "validate"}
                ],
            }
        ),
        encoding="utf-8",
    )
    gaps = verify_standalone_validator_registry(
        repo_root=tmp_path, debt_manifest_path=manifest_path
    )
    offenders = {g.workflow_file for g in gaps}
    assert "validator-long-gone.yml" in offenders


def test_planted_regressed_migration_is_detected(tmp_path: Path) -> None:
    """PLANTED FAILURE: a file listed as migrated_into_ci_yml (so it should be
    workflow_dispatch-only) that regresses to triggering on pull_request again
    must be flagged — the migration silently un-doing itself is exactly the
    kind of drift this registry exists to catch."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "validator-regressed.yml").write_text(
        yaml.safe_dump(
            {
                "name": "Regressed",
                "on": {"pull_request": {}, "workflow_dispatch": {}},
                "jobs": {"validate": {"name": "validate"}},
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "standalone-validator-debt.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "migrated_into_ci_yml": [
                    {
                        "workflow_file": "validator-regressed.yml",
                        "ci_job_key": "regressed",
                    }
                ],
                "natively_required_contexts": [],
                "decorative_debt": [],
            }
        ),
        encoding="utf-8",
    )
    gaps = verify_standalone_validator_registry(
        repo_root=tmp_path, debt_manifest_path=manifest_path
    )
    offenders = {g.workflow_file for g in gaps}
    assert "validator-regressed.yml" in offenders


def test_malformed_manifest_raises_value_error(tmp_path: Path) -> None:
    """Malformed manifest surfaces as a deterministic ValueError, not a raw
    KeyError/TypeError."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    manifest_path = tmp_path / "standalone-validator-debt.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"decorative_debt": "not-a-list"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="decorative_debt"):
        verify_standalone_validator_registry(
            repo_root=tmp_path, debt_manifest_path=manifest_path
        )
