# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeCrossRepoValidationOrchestrator.

Tests the orchestrator's event emission logic:
- Started event emission
- Violations batching (50 per batch)
- Completed event emission
- Event correlation via run_id

Related:
    - OMN-1776: Cross-repo validation orchestrator
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.events.validation import (
    ModelValidationRunCompletedEvent,
    ModelValidationRunStartedEvent,
    ModelValidationViolationsBatchEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleForbiddenImportsConfig,
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.models.validation.model_validation_discovery_config import (
    ModelValidationDiscoveryConfig,
)
from omnibase_core.models.validation.model_validation_policy_contract import (
    ModelValidationPolicyContract,
)
from omnibase_core.nodes.node_validation_orchestrator import (
    ModelResultCrossRepoValidationOrchestrator,
    NodeCrossRepoValidationOrchestrator,
)


def create_test_policy() -> ModelValidationPolicyContract:
    """Create a test policy contract."""
    return ModelValidationPolicyContract(
        policy_id="test_policy",
        policy_version=ModelSemVer(major=1, minor=0, patch=0),
        repo_id="omnibase_core",
        discovery=ModelValidationDiscoveryConfig(
            include_globs=("**/*.py",),
            exclude_globs=("**/tests/**",),
        ),
        rules={
            "repo_boundaries": ModelRuleRepoBoundariesConfig(
                enabled=True,
            ),
            "forbidden_imports": ModelRuleForbiddenImportsConfig(
                enabled=True,
            ),
        },
    )


def create_mock_validation_result(
    is_valid: bool = True,
    issues: list[ModelValidationIssue] | None = None,
) -> ModelValidationResult[None]:
    """Create a mock validation result."""
    if issues is None:
        issues = []

    return ModelValidationResult[None](
        is_valid=is_valid,
        issues=issues,
        summary=f"Test validation: {len(issues)} issues",
        metadata=ModelValidationMetadata(
            validation_type="cross_repo",
            duration_ms=100,
            files_processed=50,
            rules_applied=2,
            violations_found=len(issues),
        ),
    )


# =============================================================================
# Orchestrator Result Tests
# =============================================================================


@pytest.mark.unit
class TestModelResultCrossRepoValidationOrchestrator:
    """Tests for ModelResultCrossRepoValidationOrchestrator."""

    def test_result_creation(self) -> None:
        """Test result creation with events."""
        from uuid import uuid4

        run_id = uuid4()
        now = datetime.now(UTC)

        started = ModelValidationRunStartedEvent(
            run_id=run_id,
            repo_id="test",
            root_path="/test",
            policy_name="policy",
            started_at=now,
        )

        completed = ModelValidationRunCompletedEvent(
            run_id=run_id,
            repo_id="test",
            is_valid=True,
            total_violations=0,
            error_count=0,
            warning_count=0,
            suppressed_count=0,
            files_processed=10,
            rules_applied=2,
            duration_ms=100,
            completed_at=now,
        )

        result = ModelResultCrossRepoValidationOrchestrator(
            run_id=run_id,
            events=(started, completed),
        )

        assert result.run_id == run_id
        assert len(result.events) == 2
        assert result.is_valid is True
        assert result.started_event == started
        assert result.completed_event == completed
        assert result.total_violations == 0

    def test_result_violation_batches(self) -> None:
        """Test violation batch extraction from result."""
        from uuid import uuid4

        run_id = uuid4()
        now = datetime.now(UTC)

        started = ModelValidationRunStartedEvent(
            run_id=run_id,
            repo_id="test",
            root_path="/test",
            policy_name="policy",
            started_at=now,
        )

        batch1 = ModelValidationViolationsBatchEvent(
            run_id=run_id,
            repo_id="test",
            batch_index=0,
            batch_size=2,
            total_batches=2,
            violations=(),
        )

        batch2 = ModelValidationViolationsBatchEvent(
            run_id=run_id,
            repo_id="test",
            batch_index=1,
            batch_size=1,
            total_batches=2,
            violations=(),
        )

        completed = ModelValidationRunCompletedEvent(
            run_id=run_id,
            repo_id="test",
            is_valid=False,
            total_violations=3,
            error_count=3,
            warning_count=0,
            suppressed_count=0,
            files_processed=10,
            rules_applied=2,
            duration_ms=100,
            completed_at=now,
        )

        result = ModelResultCrossRepoValidationOrchestrator(
            run_id=run_id,
            events=(started, batch1, batch2, completed),
        )

        assert len(result.violation_batches) == 2
        assert result.violation_batches[0].batch_index == 0
        assert result.violation_batches[1].batch_index == 1


# =============================================================================
# Orchestrator Event Emission Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorEvents:
    """Tests for orchestrator event emission."""

    @pytest.mark.asyncio
    async def test_validate_emits_started_event(self) -> None:
        """Test that validate() emits a started event."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Should have started event
        assert result.started_event is not None
        assert result.started_event.repo_id == "test_repo"
        assert result.started_event.root_path == "/workspace/test"
        assert result.started_event.policy_name == "test_policy"

    @pytest.mark.asyncio
    async def test_validate_emits_completed_event(self) -> None:
        """Test that validate() emits a completed event."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Should have completed event
        assert result.completed_event is not None
        assert result.completed_event.is_valid is True
        assert result.completed_event.repo_id == "test_repo"
        assert result.completed_event.files_processed == 50
        assert result.completed_event.rules_applied == 2

    @pytest.mark.asyncio
    async def test_validate_correlation_id_propagated(self) -> None:
        """Test that correlation_id is propagated to all events."""
        from uuid import uuid4

        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)
        correlation_id = uuid4()

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
                correlation_id=correlation_id,
            )

        # All events should have same correlation_id
        for event in result.events:
            assert event.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_validate_run_id_consistent(self) -> None:
        """Test that run_id is consistent across all events."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # All events should have same run_id
        run_ids = {event.run_id for event in result.events}
        assert len(run_ids) == 1
        assert result.run_id in run_ids


# =============================================================================
# Violations Batching Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorBatching:
    """Tests for violation batching logic."""

    @pytest.mark.asyncio
    async def test_empty_violations_emits_single_batch(self) -> None:
        """Test that no violations emits a single empty batch."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        mock_result = create_mock_validation_result(is_valid=True, issues=[])

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Should have exactly one batch (empty)
        batches = result.violation_batches
        assert len(batches) == 1
        assert batches[0].batch_index == 0
        assert batches[0].batch_size == 0
        assert batches[0].total_batches == 1
        assert len(batches[0].violations) == 0

    @pytest.mark.asyncio
    async def test_violations_batched_at_50(self) -> None:
        """Test that violations are batched at 50 per batch."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(
            policy, violations_per_batch=50
        )

        # Create 125 issues (should result in 3 batches: 50, 50, 25)
        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message=f"Error {i}",
                code="TEST_ERROR",
                context={"suppressed": "false"},
            )
            for i in range(125)
        ]

        mock_result = create_mock_validation_result(is_valid=False, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        batches = result.violation_batches
        assert len(batches) == 3

        assert batches[0].batch_index == 0
        assert batches[0].batch_size == 50
        assert batches[0].total_batches == 3

        assert batches[1].batch_index == 1
        assert batches[1].batch_size == 50
        assert batches[1].total_batches == 3

        assert batches[2].batch_index == 2
        assert batches[2].batch_size == 25
        assert batches[2].total_batches == 3

    @pytest.mark.asyncio
    async def test_custom_batch_size(self) -> None:
        """Test that custom batch size is respected."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(
            policy, violations_per_batch=10
        )

        # Create 25 issues (should result in 3 batches with size 10: 10, 10, 5)
        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message=f"Warning {i}",
                context={"suppressed": "false"},
            )
            for i in range(25)
        ]

        mock_result = create_mock_validation_result(is_valid=True, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        batches = result.violation_batches
        assert len(batches) == 3
        assert batches[0].batch_size == 10
        assert batches[1].batch_size == 10
        assert batches[2].batch_size == 5


# =============================================================================
# Issue Conversion Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorIssueConversion:
    """Tests for issue to violation record conversion."""

    @pytest.mark.asyncio
    async def test_issue_fields_converted_correctly(self) -> None:
        """Test that issue fields are correctly converted to violation records."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Forbidden import: omnibase_infra",
                code="FORBIDDEN_IMPORT",
                file_path=Path("/src/module.py"),
                line_number=42,
                rule_name="forbidden_imports",
                context={"fingerprint": "abc123", "suppressed": "false"},
            ),
        ]

        mock_result = create_mock_validation_result(is_valid=False, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        batches = result.violation_batches
        assert len(batches) == 1
        assert len(batches[0].violations) == 1

        violation = batches[0].violations[0]
        assert violation.severity == EnumSeverity.ERROR.value
        assert violation.message == "Forbidden import: omnibase_infra"
        assert violation.code == "FORBIDDEN_IMPORT"
        assert violation.file_path == "/src/module.py"
        assert violation.line_number == 42
        assert violation.rule_name == "forbidden_imports"
        assert violation.fingerprint == "abc123"
        assert violation.suppressed is False

    @pytest.mark.asyncio
    async def test_suppressed_issues_marked(self) -> None:
        """Test that suppressed issues are correctly marked."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.INFO,  # Downgraded by baseline
                message="Baselined violation",
                context={"suppressed": "true"},
            ),
        ]

        mock_result = create_mock_validation_result(is_valid=True, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        batches = result.violation_batches
        assert len(batches[0].violations) == 1
        assert batches[0].violations[0].suppressed is True


# =============================================================================
# Completed Event Counts Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorCounts:
    """Tests for completed event count calculations."""

    @pytest.mark.asyncio
    async def test_error_count_calculation(self) -> None:
        """Test that error_count is calculated correctly."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.FATAL,
                message="Fatal 1",
                context={"suppressed": "false"},
            ),
            ModelValidationIssue(
                severity=EnumSeverity.CRITICAL,
                message="Critical 1",
                context={"suppressed": "false"},
            ),
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Error 1",
                context={"suppressed": "false"},
            ),
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message="Warning 1",
                context={"suppressed": "false"},
            ),
        ]

        mock_result = create_mock_validation_result(is_valid=False, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        completed = result.completed_event
        assert completed is not None
        assert completed.error_count == 3  # FATAL + CRITICAL + ERROR
        assert completed.warning_count == 1

    @pytest.mark.asyncio
    async def test_suppressed_count_calculation(self) -> None:
        """Test that suppressed_count is calculated correctly."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Error 1",
                context={"suppressed": "false"},
            ),
            ModelValidationIssue(
                severity=EnumSeverity.INFO,
                message="Suppressed 1",
                context={"suppressed": "true"},
            ),
            ModelValidationIssue(
                severity=EnumSeverity.INFO,
                message="Suppressed 2",
                context={"suppressed": "true"},
            ),
        ]

        mock_result = create_mock_validation_result(is_valid=False, issues=issues)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        completed = result.completed_event
        assert completed is not None
        assert completed.suppressed_count == 2
        assert completed.total_violations == 3


# =============================================================================
# Event Emitter Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorEventEmitter:
    """Tests for event emitter integration."""

    @pytest.mark.asyncio
    async def test_event_emitter_called_for_each_event(self) -> None:
        """Test that event emitter is called for each event."""
        policy = create_test_policy()

        # Create mock event emitter with async emit method
        mock_emitter = MagicMock()
        mock_emitter.emit = AsyncMock()

        orchestrator = NodeCrossRepoValidationOrchestrator(
            policy,
            event_emitter=mock_emitter,
        )

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Should be called for: started, batch, completed
        assert mock_emitter.emit.call_count == 3

    @pytest.mark.asyncio
    async def test_no_event_emitter_no_error(self) -> None:
        """Test that validation works without event emitter."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        mock_result = create_mock_validation_result(is_valid=True)

        with patch.object(orchestrator._engine, "validate", return_value=mock_result):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Should complete without error
        assert result.is_valid is True
        assert len(result.events) == 3


# =============================================================================
# Exception Handling Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorExceptionHandling:
    """Tests for exception handling and event lifecycle guarantee."""

    @pytest.mark.asyncio
    async def test_engine_exception_emits_completed_with_error_message(self) -> None:
        """Test that engine exceptions result in completed event with error_message.

        The orchestrator guarantees the started → completed event lifecycle even
        when the validation engine raises an exception. This is critical for
        consumers who need to reconstruct state from events.
        """
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        with patch.object(
            orchestrator._engine,
            "validate",
            side_effect=RuntimeError("Validation engine failed"),
        ):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        # Lifecycle should complete even on exception
        assert result.started_event is not None
        assert result.completed_event is not None
        assert result.completed_event.is_valid is False
        assert result.completed_event.error_message is not None
        assert "RuntimeError" in result.completed_event.error_message
        assert "Validation engine failed" in result.completed_event.error_message

    @pytest.mark.asyncio
    async def test_engine_exception_sets_zero_counts(self) -> None:
        """Test that engine exceptions result in zero file/rule counts."""
        policy = create_test_policy()
        orchestrator = NodeCrossRepoValidationOrchestrator(policy)

        with patch.object(
            orchestrator._engine,
            "validate",
            side_effect=ValueError("Invalid configuration"),
        ):
            result = await orchestrator.validate(
                root=Path("/workspace/test"),
                repo_id="test_repo",
            )

        completed = result.completed_event
        assert completed is not None
        assert completed.files_processed == 0
        assert completed.rules_applied == 0
        assert completed.total_violations == 0
        assert completed.error_count == 0
        assert completed.warning_count == 0


# =============================================================================
# Constructor Validation Tests
# =============================================================================


@pytest.mark.unit
class TestNodeCrossRepoValidationOrchestratorConstructor:
    """Tests for constructor parameter validation."""

    def test_violations_per_batch_minimum_validation(self) -> None:
        """Test that violations_per_batch must be >= 1."""
        policy = create_test_policy()

        with pytest.raises(ValueError, match="violations_per_batch must be >= 1"):
            NodeCrossRepoValidationOrchestrator(policy, violations_per_batch=0)

    def test_violations_per_batch_negative_rejected(self) -> None:
        """Test that negative violations_per_batch is rejected."""
        policy = create_test_policy()

        with pytest.raises(ValueError, match="violations_per_batch must be >= 1"):
            NodeCrossRepoValidationOrchestrator(policy, violations_per_batch=-1)

    def test_violations_per_batch_valid_minimum(self) -> None:
        """Test that violations_per_batch=1 is valid."""
        policy = create_test_policy()

        # Should not raise
        orchestrator = NodeCrossRepoValidationOrchestrator(
            policy, violations_per_batch=1
        )
        assert orchestrator._violations_per_batch == 1
