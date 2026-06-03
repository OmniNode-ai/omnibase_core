# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for breaking-schema-change validator (OMN-12621)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.breaking_schema_change import (
    main,
    validate_file,
    validate_paths,
)

# ---------------------------------------------------------------------------
# Fixture content
# ---------------------------------------------------------------------------

_BREAKING_DECLARATION = """\
current:
  topic: onex.evt.payments.payment-captured.v2
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 2, minor: 0, patch: 0}
baseline:
  topic: onex.evt.payments.payment-captured.v1
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 1, minor: 0, patch: 0}
"""

_COMPATIBLE_DECLARATION = """\
current:
  topic: onex.evt.payments.payment-captured.v1
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 1, minor: 1, patch: 0}
baseline:
  topic: onex.evt.payments.payment-captured.v1
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 1, minor: 0, patch: 0}
"""

_MIGRATION_CONTRACT = """\
contract_version: {major: 1, minor: 0, patch: 0}
ticket: OMN-12621
old_binding:
  topic: onex.evt.payments.payment-captured.v1
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 1, minor: 0, patch: 0}
new_binding:
  topic: onex.evt.payments.payment-captured.v2
  event_name: PAYMENT_CAPTURED
  schema_version: {major: 2, minor: 0, patch: 0}
old_consumer_group: payments-ledger-v1
new_consumer_group: payments-ledger-v2
compatibility_window_hours: 72
cutover_criteria:
  - old_topic_drained
  - new_topic_consumer_healthy
"""


def _write(d: Path, name: str, content: str) -> Path:
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# PROOF: fires on breaking change lacking migration; passes when present
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBreakingSchemaValidator:
    def test_breaking_without_migration_fires(self, tmp_path: Path) -> None:
        decl = _write(tmp_path, "payments.topic-schema.yaml", _BREAKING_DECLARATION)
        findings = validate_file(decl)
        assert len(findings) == 1
        assert findings[0].rule == "missing_topic_migration_contract"
        assert findings[0].delta == "major_bump"

    def test_breaking_with_adjacent_migration_passes(self, tmp_path: Path) -> None:
        decl = _write(tmp_path, "payments.topic-schema.yaml", _BREAKING_DECLARATION)
        _write(tmp_path, "payments.migration.yaml", _MIGRATION_CONTRACT)
        findings = validate_file(decl)
        assert findings == []

    def test_compatible_change_passes(self, tmp_path: Path) -> None:
        decl = _write(tmp_path, "payments.topic-schema.yaml", _COMPATIBLE_DECLARATION)
        findings = validate_file(decl)
        assert findings == []

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        suppressed = _BREAKING_DECLARATION.replace(
            "onex.evt.payments.payment-captured.v2",
            "onex.evt.payments.payment-captured.v2  # breaking-schema-ok: handled in OMN-12621",
            1,
        )
        decl = _write(tmp_path, "payments.topic-schema.yaml", suppressed)
        findings = validate_file(decl)
        assert findings == []

    def test_validate_paths_directory(self, tmp_path: Path) -> None:
        _write(tmp_path, "payments.topic-schema.yaml", _BREAKING_DECLARATION)
        findings = validate_paths([tmp_path])
        assert len(findings) == 1

    def test_main_exit_one_on_finding(self, tmp_path: Path) -> None:
        _write(tmp_path, "payments.topic-schema.yaml", _BREAKING_DECLARATION)
        assert main([str(tmp_path)]) == 1

    def test_main_exit_zero_when_migration_present(self, tmp_path: Path) -> None:
        _write(tmp_path, "payments.topic-schema.yaml", _BREAKING_DECLARATION)
        _write(tmp_path, "payments.migration.yaml", _MIGRATION_CONTRACT)
        assert main([str(tmp_path)]) == 0
