# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for baseline I/O utilities.

Related ticket: OMN-1774
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_violation_baseline import (
    ModelBaselineGenerator,
    ModelBaselineViolation,
    ModelViolationBaseline,
)
from omnibase_core.validation.cross_repo.baseline_io import (
    read_baseline,
    write_baseline,
)


class TestWriteBaseline:
    """Tests for write_baseline function."""

    def test_write_baseline_creates_file(self, tmp_path: Path) -> None:
        """Test that write_baseline creates the file."""
        baseline_path = tmp_path / "baseline.yaml"
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[],
        )

        write_baseline(baseline_path, baseline)

        assert baseline_path.exists()

    def test_write_baseline_yaml_format(self, tmp_path: Path) -> None:
        """Test that the output is valid YAML."""
        baseline_path = tmp_path / "baseline.yaml"
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="a1b2c3d4e5f67890",
                    rule_id="repo_boundaries",
                    file_path="src/handlers/legacy.py",
                    symbol="fake_infra.services.kafka",
                    message="Forbidden import: fake_infra.services.kafka",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        write_baseline(baseline_path, baseline)

        # Verify it's valid YAML
        with baseline_path.open() as f:
            data = yaml.safe_load(f)

        assert data["schema_version"] == "1.0"
        assert data["policy_id"] == "test_policy"
        assert data["generator"]["tool"] == "test-tool"
        assert len(data["violations"]) == 1

    def test_write_baseline_matches_spec(self, tmp_path: Path) -> None:
        """Test that output matches the baseline file format spec."""
        baseline_path = tmp_path / "baseline.yaml"
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="omnibase_app_policy",
            generator=ModelBaselineGenerator(
                tool="omnibase-policy",
                version="0.5.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="a1b2c3d4e5f67890",
                    rule_id="repo_boundaries",
                    file_path="src/handlers/legacy.py",
                    symbol="fake_infra.services.kafka",
                    message="Forbidden import: fake_infra.services.kafka",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        write_baseline(baseline_path, baseline)

        with baseline_path.open() as f:
            data = yaml.safe_load(f)

        # Verify structure matches spec
        assert "schema_version" in data
        assert "created_at" in data
        assert "policy_id" in data
        assert "generator" in data
        assert "tool" in data["generator"]
        assert "version" in data["generator"]
        assert "violations" in data

        violation = data["violations"][0]
        assert "fingerprint" in violation
        assert "rule_id" in violation
        assert "file_path" in violation
        assert "symbol" in violation
        assert "message" in violation
        assert "first_seen" in violation

    def test_write_baseline_sorts_violations(self, tmp_path: Path) -> None:
        """Test that violations are sorted by fingerprint for stable diffs."""
        baseline_path = tmp_path / "baseline.yaml"
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="zzz111",
                    rule_id="rule_a",
                    file_path="z.py",
                    symbol="z_import",
                    message="Z message",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
                ModelBaselineViolation(
                    fingerprint="aaa222",
                    rule_id="rule_b",
                    file_path="a.py",
                    symbol="a_import",
                    message="A message",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        write_baseline(baseline_path, baseline)

        with baseline_path.open() as f:
            data = yaml.safe_load(f)

        # Should be sorted by fingerprint (aaa before zzz)
        assert data["violations"][0]["fingerprint"] == "aaa222"
        assert data["violations"][1]["fingerprint"] == "zzz111"


class TestReadBaseline:
    """Tests for read_baseline function."""

    def test_read_baseline_round_trip(self, tmp_path: Path) -> None:
        """Test that write then read produces equivalent baseline."""
        baseline_path = tmp_path / "baseline.yaml"
        original = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="a1b2c3d4e5f67890",
                    rule_id="repo_boundaries",
                    file_path="src/handlers/legacy.py",
                    symbol="fake_infra.services.kafka",
                    message="Forbidden import: fake_infra.services.kafka",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        write_baseline(baseline_path, original)
        restored = read_baseline(baseline_path)

        assert restored.schema_version == original.schema_version
        assert restored.policy_id == original.policy_id
        assert restored.generator.tool == original.generator.tool
        assert restored.generator.version == original.generator.version
        assert len(restored.violations) == len(original.violations)

        # Compare violations
        for orig_v, rest_v in zip(
            original.violations, restored.violations, strict=True
        ):
            assert rest_v.fingerprint == orig_v.fingerprint
            assert rest_v.rule_id == orig_v.rule_id
            assert rest_v.file_path == orig_v.file_path
            assert rest_v.symbol == orig_v.symbol
            assert rest_v.message == orig_v.message

    def test_read_baseline_missing_file(self, tmp_path: Path) -> None:
        """Test that reading a missing file raises ModelOnexError."""
        missing_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(ModelOnexError) as exc_info:
            read_baseline(missing_path)

        assert "not found" in str(exc_info.value).lower()

    def test_read_baseline_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that reading invalid YAML raises ModelOnexError."""
        invalid_path = tmp_path / "invalid.yaml"
        invalid_path.write_text("{ invalid yaml content [[[")

        with pytest.raises(ModelOnexError) as exc_info:
            read_baseline(invalid_path)

        assert "yaml" in str(exc_info.value).lower()

    def test_read_baseline_empty_file(self, tmp_path: Path) -> None:
        """Test that reading an empty file raises ModelOnexError."""
        empty_path = tmp_path / "empty.yaml"
        empty_path.write_text("")

        with pytest.raises(ModelOnexError) as exc_info:
            read_baseline(empty_path)

        assert "empty" in str(exc_info.value).lower()

    def test_read_baseline_invalid_schema(self, tmp_path: Path) -> None:
        """Test that reading an invalid schema raises ModelOnexError."""
        invalid_schema_path = tmp_path / "invalid_schema.yaml"
        invalid_schema_path.write_text(
            """
schema_version: "1.0"
policy_id: "test"
# Missing required fields
"""
        )

        with pytest.raises(ModelOnexError) as exc_info:
            read_baseline(invalid_schema_path)

        assert (
            "invalid" in str(exc_info.value).lower()
            or "format" in str(exc_info.value).lower()
        )


class TestBaselineModelMethods:
    """Tests for ModelViolationBaseline methods."""

    def test_violation_count(self) -> None:
        """Test violation_count method."""
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="abc123",
                    rule_id="rule_a",
                    file_path="a.py",
                    symbol="import_a",
                    message="Message A",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
                ModelBaselineViolation(
                    fingerprint="def456",
                    rule_id="rule_b",
                    file_path="b.py",
                    symbol="import_b",
                    message="Message B",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        assert baseline.violation_count() == 2

    def test_has_violation(self) -> None:
        """Test has_violation method."""
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[
                ModelBaselineViolation(
                    fingerprint="abc123",
                    rule_id="rule_a",
                    file_path="a.py",
                    symbol="import_a",
                    message="Message A",
                    first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
                ),
            ],
        )

        assert baseline.has_violation("abc123") is True
        assert baseline.has_violation("nonexistent") is False

    def test_get_violation(self) -> None:
        """Test get_violation method."""
        violation = ModelBaselineViolation(
            fingerprint="abc123",
            rule_id="rule_a",
            file_path="a.py",
            symbol="import_a",
            message="Message A",
            first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
        )
        baseline = ModelViolationBaseline(
            schema_version="1.0",
            created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
            policy_id="test_policy",
            generator=ModelBaselineGenerator(
                tool="test-tool",
                version="1.0.0",
            ),
            violations=[violation],
        )

        found = baseline.get_violation("abc123")
        assert found is not None
        assert found.fingerprint == "abc123"
        assert found.rule_id == "rule_a"

        not_found = baseline.get_violation("nonexistent")
        assert not_found is None
