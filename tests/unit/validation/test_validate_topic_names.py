# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the cross-repo topic name CI validation script.

Covers:
- Valid canonical topic passes
- {env}. prefixed topic fails
- Flat legacy topic fails
- TypeScript topic scanned
- Invalid kind fails
- scan_file() extraction works

Related ticket: OMN-3740
"""

from pathlib import Path

import pytest

from omnibase_core.validation.scripts.validate_topic_names import (
    scan_file,
    validate_repo,
    validate_topic,
)


@pytest.mark.unit
class TestValidateTopic:
    """Tests for the validate_topic() function."""

    def test_valid_canonical_topic_passes(self) -> None:
        """A well-formed canonical ONEX topic should pass validation."""
        result = validate_topic("onex.evt.omnimemory.intent-stored.v1")
        assert result is None, f"Expected None (valid), got: {result}"

    def test_valid_canonical_cmd_topic_passes(self) -> None:
        """A cmd-kind canonical topic should pass validation."""
        result = validate_topic("onex.cmd.user-service.create-account.v2")
        assert result is None, f"Expected None (valid), got: {result}"

    def test_env_prefixed_topic_fails(self) -> None:
        """Topics with {env}. prefix should be rejected."""
        result = validate_topic("{env}.onex.evt.omnimemory.intent-stored.v1")
        assert result is not None
        assert "{env}." in result

    def test_flat_legacy_topic_fails(self) -> None:
        """Flat legacy topic names (no dots) should be rejected."""
        result = validate_topic("agent-actions")
        assert result is not None
        assert "flat" in result.lower()

    def test_invalid_kind_fails(self) -> None:
        """Topics with an invalid kind segment should be rejected."""
        result = validate_topic("onex.events.omnimemory.intent-stored.v1")
        assert result is not None
        assert "Kind" in result or "kind" in result.lower()

    def test_valid_dlq_topic_passes(self) -> None:
        """A dlq-kind topic should pass."""
        result = validate_topic("onex.dlq.service-a.failed-event.v1")
        assert result is None

    def test_valid_snapshot_topic_passes(self) -> None:
        """A snapshot-kind topic should pass."""
        result = validate_topic("onex.snapshot.registry.state-dump.v1")
        assert result is None


@pytest.mark.unit
class TestScanFile:
    """Tests for the scan_file() function."""

    def test_scan_python_file_extracts_topics(self, tmp_path: Path) -> None:
        """scan_file should extract TOPIC_* and SUFFIX_* from Python files."""
        py_file = tmp_path / "constants_topics.py"
        py_file.write_text(
            'TOPIC_INTENT_STORED = "onex.evt.omnimemory.intent-stored.v1"\n'
            'SUFFIX_DLQ = "onex.dlq.service.failed.v1"\n'
            'UNRELATED_VAR = "not-a-topic"\n',
            encoding="utf-8",
        )

        extractions = scan_file(py_file)
        assert len(extractions) == 2
        assert extractions[0].constant_value == "onex.evt.omnimemory.intent-stored.v1"
        assert extractions[0].line_number == 1
        assert extractions[1].constant_value == "onex.dlq.service.failed.v1"
        assert extractions[1].line_number == 2

    def test_scan_typescript_file_extracts_topics(self, tmp_path: Path) -> None:
        """scan_file should extract exported TOPIC_* and SUFFIX_* from TS files."""
        ts_file = tmp_path / "topics.ts"
        ts_file.write_text(
            'export const TOPIC_AGENT_ACTION = "onex.cmd.agent.run-action.v1"\n'
            'export const SUFFIX_SNAPSHOT = "onex.snapshot.dash.state.v1"\n'
            'const PRIVATE_VAR = "not-exported"\n',
            encoding="utf-8",
        )

        extractions = scan_file(ts_file)
        assert len(extractions) == 2
        assert extractions[0].constant_value == "onex.cmd.agent.run-action.v1"
        assert extractions[1].constant_value == "onex.snapshot.dash.state.v1"

    def test_scan_file_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        """scan_file should return empty list for nonexistent files."""
        result = scan_file(tmp_path / "does_not_exist.py")
        assert result == []

    def test_scan_file_unsupported_extension_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """scan_file should skip files with unsupported extensions."""
        txt_file = tmp_path / "topics.txt"
        txt_file.write_text('TOPIC_FOO = "onex.evt.svc.event.v1"\n')
        result = scan_file(txt_file)
        assert result == []


@pytest.mark.unit
class TestValidateRepo:
    """Tests for the validate_repo() integration function."""

    def test_repo_with_valid_topics_exits_clean(self, tmp_path: Path) -> None:
        """A repo with only canonical topics should produce a clean report."""
        topic_file = tmp_path / "constants_topics.py"
        topic_file.write_text(
            'TOPIC_A = "onex.evt.service-a.event-one.v1"\n'
            'TOPIC_B = "onex.cmd.service-b.do-thing.v2"\n',
            encoding="utf-8",
        )

        report = validate_repo(tmp_path)
        assert report.is_clean
        assert report.total_topics == 2
        assert report.scanned_files >= 1

    def test_repo_with_legacy_topic_has_violations(self, tmp_path: Path) -> None:
        """A repo containing flat legacy topics should report violations."""
        topic_file = tmp_path / "constants_topics.py"
        topic_file.write_text(
            'TOPIC_LEGACY = "agent-actions"\n',
            encoding="utf-8",
        )

        report = validate_repo(tmp_path)
        assert not report.is_clean
        assert len(report.violations) == 1
        assert "flat" in report.violations[0].lower()

    def test_repo_with_env_prefix_has_violations(self, tmp_path: Path) -> None:
        """A repo containing {env}. prefixed topics should report violations."""
        topic_file = tmp_path / "constants_topics.py"
        topic_file.write_text(
            'TOPIC_OLD = "{env}.onex.evt.service.event.v1"\n',
            encoding="utf-8",
        )

        report = validate_repo(tmp_path)
        assert not report.is_clean
        assert len(report.violations) == 1
        assert "{env}." in report.violations[0]
