# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ManifestLogger.

Tests the logger's ability to output manifests in various formats.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.manifest import (
    ModelContractIdentity,
    ModelEmissionsSummary,
    ModelExecutionManifest,
    ModelHookTrace,
    ModelManifestFailure,
    ModelNodeIdentity,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.pipeline import ManifestLogger


@pytest.fixture
def sample_manifest() -> ModelExecutionManifest:
    """Create a sample manifest for testing."""
    node_identity = ModelNodeIdentity(
        node_id="test-compute-node",
        node_kind=EnumNodeKind.COMPUTE,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        namespace="test.namespace",
    )
    contract_identity = ModelContractIdentity(
        contract_id="test-contract",
        contract_path="contracts/test.yaml",
        profile_name="default",
    )
    hook_trace = ModelHookTrace(
        hook_id="hook-1",
        handler_id="handler_test",
        phase=EnumHandlerExecutionPhase.EXECUTE,
        status=EnumExecutionStatus.SUCCESS,
        started_at=datetime.now(UTC),
        duration_ms=45.5,
    )
    emissions = ModelEmissionsSummary(
        events_count=2,
        event_types=["UserCreated", "UserUpdated"],
    )
    return ModelExecutionManifest(
        node_identity=node_identity,
        contract_identity=contract_identity,
        hook_traces=[hook_trace],
        emissions_summary=emissions,
    )


@pytest.mark.unit
class TestManifestLoggerToJson:
    """Test ManifestLogger.to_json()."""

    def test_to_json_is_valid(self, sample_manifest: ModelExecutionManifest) -> None:
        """Test that to_json produces valid JSON."""
        json_str = ManifestLogger.to_json(sample_manifest)
        data = json.loads(json_str)
        assert "manifest_id" in data
        assert "node_identity" in data

    def test_to_json_with_indent(self, sample_manifest: ModelExecutionManifest) -> None:
        """Test JSON indentation."""
        json_str = ManifestLogger.to_json(sample_manifest, indent=4)
        # 4-space indent should have more whitespace
        assert "    " in json_str


@pytest.mark.unit
class TestManifestLoggerToYaml:
    """Test ManifestLogger.to_yaml()."""

    def test_to_yaml_is_valid(self, sample_manifest: ModelExecutionManifest) -> None:
        """Test that to_yaml produces valid YAML."""
        yaml_str = ManifestLogger.to_yaml(sample_manifest)
        data = yaml.safe_load(yaml_str)
        assert "manifest_id" in data
        assert "node_identity" in data


@pytest.mark.unit
class TestManifestLoggerToDict:
    """Test ManifestLogger.to_dict()."""

    def test_to_dict_returns_dict(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that to_dict returns a dictionary."""
        data = ManifestLogger.to_dict(sample_manifest)
        assert isinstance(data, dict)
        assert "manifest_id" in data


@pytest.mark.unit
class TestManifestLoggerToMarkdown:
    """Test ManifestLogger.to_markdown()."""

    def test_to_markdown_has_header(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that Markdown has header."""
        md = ManifestLogger.to_markdown(sample_manifest)
        assert "# Execution Manifest" in md

    def test_to_markdown_has_node_identity(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that Markdown includes node identity."""
        md = ManifestLogger.to_markdown(sample_manifest)
        assert "## Node Identity" in md
        assert "test-compute-node" in md

    def test_to_markdown_has_contract_identity(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that Markdown includes contract identity."""
        md = ManifestLogger.to_markdown(sample_manifest)
        assert "## Contract Identity" in md
        assert "test-contract" in md

    def test_to_markdown_has_hook_table(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that Markdown includes hook execution table."""
        md = ManifestLogger.to_markdown(sample_manifest)
        assert "## Execution Trace" in md
        assert "handler_test" in md

    def test_to_markdown_has_emissions(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that Markdown includes emissions."""
        md = ManifestLogger.to_markdown(sample_manifest)
        assert "## Emissions" in md
        assert "Events" in md


@pytest.mark.unit
class TestManifestLoggerToText:
    """Test ManifestLogger.to_text()."""

    def test_to_text_has_header(self, sample_manifest: ModelExecutionManifest) -> None:
        """Test that text has header."""
        text = ManifestLogger.to_text(sample_manifest)
        assert "EXECUTION MANIFEST" in text

    def test_to_text_has_status(self, sample_manifest: ModelExecutionManifest) -> None:
        """Test that text shows status."""
        text = ManifestLogger.to_text(sample_manifest)
        assert "SUCCESS" in text

    def test_to_text_has_node_info(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that text shows node info."""
        text = ManifestLogger.to_text(sample_manifest)
        assert "test-compute-node" in text


@pytest.mark.unit
class TestManifestLoggerWithFailures:
    """Test ManifestLogger with failed manifests."""

    def test_markdown_shows_failures(self) -> None:
        """Test that Markdown shows failures."""
        node_identity = ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        contract_identity = ModelContractIdentity(contract_id="test-contract")
        failure = ModelManifestFailure(
            failed_at=datetime.now(UTC),
            error_code="TEST_ERROR",
            error_message="Test failure occurred",
        )
        manifest = ModelExecutionManifest(
            node_identity=node_identity,
            contract_identity=contract_identity,
            failures=[failure],
        )

        md = ManifestLogger.to_markdown(manifest)
        assert "## Failures" in md
        assert "TEST_ERROR" in md
        assert "Test failure occurred" in md

    def test_text_shows_failures(self) -> None:
        """Test that text shows failures."""
        node_identity = ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        contract_identity = ModelContractIdentity(contract_id="test-contract")
        failure = ModelManifestFailure(
            failed_at=datetime.now(UTC),
            error_code="TEST_ERROR",
            error_message="Test failure",
        )
        manifest = ModelExecutionManifest(
            node_identity=node_identity,
            contract_identity=contract_identity,
            failures=[failure],
        )

        text = ManifestLogger.to_text(manifest)
        assert "FAILURES" in text
        assert "TEST_ERROR" in text


@pytest.mark.unit
class TestManifestLoggerLogSummary:
    """Test ManifestLogger.log_summary()."""

    def test_log_summary_calls_logger(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Test that log_summary calls the logger."""
        logged_messages: list[tuple[str, dict[str, Any] | None]] = []

        class MockLogger:
            def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
                logged_messages.append((message, extra))

        ManifestLogger.log_summary(sample_manifest, MockLogger())

        assert len(logged_messages) == 1
        message, extra = logged_messages[0]
        assert "manifest" in message.lower()
        assert extra is not None
        assert "manifest_id" in extra
        assert "node_id" in extra


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
