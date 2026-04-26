# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ``util_dod_receipt_migration``.

These tests cover the legacy DoD receipt backfill utility introduced for
OMN-9790. The utility rewrites pre-OMN-9786 receipts (lacking ``verifier``,
``probe_command``, ``probe_stdout``, ``schema_version``) so that they
validate against the extended ``ModelDodReceipt`` schema while preserving
audit trail (``original_status``).

The utility is invoked one file at a time via ``migrate_receipt_file``;
the directory walk is exercised separately via ``migrate_receipts_in_root``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_dod_receipt_migration import (
    LEGACY_VERIFIER_SENTINEL,
    SENTINEL_PROBE_COMMAND,
    SENTINEL_PROBE_STDOUT,
    SENTINEL_SCHEMA_VERSION,
    migrate_receipt_file,
    migrate_receipts_in_root,
)


def _legacy_yaml_payload() -> dict[str, Any]:
    """Return a representative pre-9786 legacy receipt payload."""
    return {
        "ticket_id": "OMN-9409",
        "evidence_item_id": "dod-001",
        "check_type": "file_exists",
        "check_value": "drift/dod_receipts/OMN-9409/dod-001/file_exists.yaml",
        "status": "PASS",
        "run_timestamp": "2026-04-23T23:15:00Z",
        "commit_sha": "e22100e230d412379f798be58fd49234b4fb821a",
        "runner": "polish-infra-1390",
        "actual_output": "...",
        "exit_code": 0,
        "pr_number": 1390,
    }


@pytest.mark.unit
class TestMigrateReceiptFileYaml:
    def test_legacy_receipt_without_verifier_marked_advisory(
        self, tmp_path: Path
    ) -> None:
        """A legacy receipt should be downgraded to ADVISORY and tagged."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump(_legacy_yaml_payload()))

        modified = migrate_receipt_file(receipt_path)

        assert modified is True
        migrated = yaml.safe_load(receipt_path.read_text())
        assert migrated["status"] == "ADVISORY"
        assert migrated["verifier"] == LEGACY_VERIFIER_SENTINEL
        assert migrated["probe_command"] == SENTINEL_PROBE_COMMAND
        assert migrated["probe_stdout"] == SENTINEL_PROBE_STDOUT
        assert migrated["schema_version"] == SENTINEL_SCHEMA_VERSION

    def test_migration_preserves_original_status_in_history_field(
        self, tmp_path: Path
    ) -> None:
        """``original_status`` must record the prior status verbatim."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump(_legacy_yaml_payload()))

        migrate_receipt_file(receipt_path)

        migrated = yaml.safe_load(receipt_path.read_text())
        assert migrated["original_status"] == "PASS"
        assert migrated["status"] == "ADVISORY"

    def test_migration_records_iso_migrated_at_field(self, tmp_path: Path) -> None:
        """``migrated_at`` must be an ISO-8601 string (timezone-aware)."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump(_legacy_yaml_payload()))

        migrate_receipt_file(receipt_path)

        migrated = yaml.safe_load(receipt_path.read_text())
        # ISO-8601 strings include 'T' separator and a timezone marker.
        assert "T" in migrated["migrated_at"]
        assert migrated["migrated_at"].endswith("+00:00") or migrated[
            "migrated_at"
        ].endswith("Z")

    def test_missing_status_filled_with_unknown_sentinel(self, tmp_path: Path) -> None:
        """A legacy file with no ``status`` field still migrates cleanly."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump({"ticket_id": "OMN-9", "runner": "w"}))

        migrate_receipt_file(receipt_path)

        migrated = yaml.safe_load(receipt_path.read_text())
        assert migrated["status"] == "ADVISORY"
        assert migrated["original_status"] == "UNKNOWN"


@pytest.mark.unit
class TestMigrateReceiptFileJson:
    def test_legacy_json_receipt_marked_advisory(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "dod_report.json"
        receipt_path.write_text(json.dumps(_legacy_yaml_payload()))

        modified = migrate_receipt_file(receipt_path)

        assert modified is True
        migrated = json.loads(receipt_path.read_text())
        assert migrated["status"] == "ADVISORY"
        assert migrated["verifier"] == LEGACY_VERIFIER_SENTINEL
        assert migrated["original_status"] == "PASS"


@pytest.mark.unit
class TestMigrateReceiptFileIdempotency:
    def test_running_migration_twice_produces_identical_bytes(
        self, tmp_path: Path
    ) -> None:
        """Idempotency: a second run must emit byte-identical contents."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump(_legacy_yaml_payload()))

        migrate_receipt_file(receipt_path)
        after_first = receipt_path.read_bytes()
        modified_second = migrate_receipt_file(receipt_path)
        after_second = receipt_path.read_bytes()

        assert modified_second is False
        assert after_first == after_second

    def test_already_migrated_receipt_not_modified(self, tmp_path: Path) -> None:
        """Receipt with ``verifier`` already set must be left untouched."""
        already_migrated = {
            "ticket_id": "OMN-9",
            "status": "ADVISORY",
            "verifier": "ci-receipt-gate",
            "runner": "worker-1",
        }
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump(already_migrated))
        before = receipt_path.read_bytes()

        modified = migrate_receipt_file(receipt_path)
        after = receipt_path.read_bytes()

        assert modified is False
        assert before == after


@pytest.mark.unit
class TestMigrateReceiptFileMalformedInput:
    def test_unsupported_extension_returns_false(self, tmp_path: Path) -> None:
        """Files outside .yaml/.yml/.json are silently skipped."""
        receipt_path = tmp_path / "report.txt"
        receipt_path.write_text("not a receipt")

        modified = migrate_receipt_file(receipt_path)

        assert modified is False
        assert receipt_path.read_text() == "not a receipt"

    def test_yaml_top_level_list_raises_value_error(self, tmp_path: Path) -> None:
        """Receipts must be mappings; lists raise a clean error."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text(yaml.safe_dump([{"ticket_id": "OMN-1"}]))

        with pytest.raises(ModelOnexError, match="must be a mapping"):
            migrate_receipt_file(receipt_path)

    def test_invalid_yaml_raises_value_error(self, tmp_path: Path) -> None:
        """Unparseable YAML raises ModelOnexError, not yaml.YAMLError."""
        receipt_path = tmp_path / "file_exists.yaml"
        receipt_path.write_text("{not: valid: yaml: at: all")

        with pytest.raises(ModelOnexError, match="failed to parse"):
            migrate_receipt_file(receipt_path)

    def test_invalid_json_raises_value_error(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "report.json"
        receipt_path.write_text("not json at all")

        with pytest.raises(ModelOnexError, match="failed to parse"):
            migrate_receipt_file(receipt_path)

    def test_missing_file_raises_value_error(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "missing.yaml"

        with pytest.raises(ModelOnexError, match="does not exist"):
            migrate_receipt_file(receipt_path)


@pytest.mark.unit
class TestMigrateReceiptsInRoot:
    def test_walks_drift_and_evidence_directories(self, tmp_path: Path) -> None:
        """The walker must traverse drift/dod_receipts and .evidence."""
        drift_dir = tmp_path / "drift" / "dod_receipts" / "OMN-1" / "dod-001"
        drift_dir.mkdir(parents=True)
        (drift_dir / "file_exists.yaml").write_text(
            yaml.safe_dump(_legacy_yaml_payload())
        )

        evidence_dir = tmp_path / ".evidence" / "OMN-2"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "dod_report.json").write_text(
            json.dumps(_legacy_yaml_payload())
        )

        modified, skipped = migrate_receipts_in_root(tmp_path)

        assert modified == 2
        assert skipped == 0

    def test_walker_is_idempotent(self, tmp_path: Path) -> None:
        drift_dir = tmp_path / "drift" / "dod_receipts" / "OMN-1" / "dod-001"
        drift_dir.mkdir(parents=True)
        (drift_dir / "file_exists.yaml").write_text(
            yaml.safe_dump(_legacy_yaml_payload())
        )

        first = migrate_receipts_in_root(tmp_path)
        second = migrate_receipts_in_root(tmp_path)

        assert first == (1, 0)
        assert second == (0, 1)

    def test_walker_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        drift_dir = tmp_path / "drift" / "dod_receipts" / "OMN-1" / "dod-001"
        drift_dir.mkdir(parents=True)
        target = drift_dir / "file_exists.yaml"
        target.write_text(yaml.safe_dump(_legacy_yaml_payload()))
        before = target.read_bytes()

        modified, skipped = migrate_receipts_in_root(tmp_path, dry_run=True)

        assert modified == 1
        assert skipped == 0
        assert target.read_bytes() == before

    def test_missing_root_returns_zero_zero(self, tmp_path: Path) -> None:
        """Walker must not raise when neither location exists."""
        modified, skipped = migrate_receipts_in_root(tmp_path / "absent")

        assert modified == 0
        assert skipped == 0
