# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the compliance report reducer node.

Verifies:
1. Reducer accumulates per-node results correctly
2. Reducer is pure (same input -> same output, no side effects)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.models.nodes.compliance_report.model_compliance_check_detail import (
    ModelComplianceCheckDetail,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.nodes.node_compliance_report_reducer.handler import (
    reduce_compliance,
)


@pytest.mark.unit
class TestReducerAccumulatesResults:
    """Reducer aggregates per-node results into summary."""

    def test_accumulate_single_passing_result(self) -> None:
        state = ModelComplianceReportState(total=0, passed=0, failed=0, results=[])
        check = ModelComplianceCheckResult(
            node_id="node_a",
            passed=True,
            checks=(
                ModelComplianceCheckDetail(
                    check_name="contract_parse", passed=True, message="OK"
                ),
            ),
        )

        new_state, intents = reduce_compliance(state, check)

        assert new_state.total == 1
        assert new_state.passed == 1
        assert new_state.failed == 0
        assert len(new_state.results) == 1
        assert new_state.results[0].node_id == "node_a"
        assert intents == []

    def test_accumulate_single_failing_result(self) -> None:
        state = ModelComplianceReportState(total=0, passed=0, failed=0, results=[])
        check = ModelComplianceCheckResult(
            node_id="node_b",
            passed=False,
            checks=(
                ModelComplianceCheckDetail(
                    check_name="handler_resolution",
                    passed=False,
                    message="Handler not importable",
                ),
            ),
        )

        new_state, intents = reduce_compliance(state, check)

        assert new_state.total == 1
        assert new_state.passed == 0
        assert new_state.failed == 1
        assert len(new_state.results) == 1
        assert intents == []

    def test_accumulate_multiple_results(self) -> None:
        state = ModelComplianceReportState(total=0, passed=0, failed=0, results=[])

        check_a = ModelComplianceCheckResult(node_id="node_a", passed=True)
        check_b = ModelComplianceCheckResult(node_id="node_b", passed=False)
        check_c = ModelComplianceCheckResult(node_id="node_c", passed=True)

        state, _ = reduce_compliance(state, check_a)
        state, _ = reduce_compliance(state, check_b)
        state, _ = reduce_compliance(state, check_c)

        assert state.total == 3
        assert state.passed == 2
        assert state.failed == 1
        assert len(state.results) == 3

    def test_replace_on_duplicate_node_id(self) -> None:
        state = ModelComplianceReportState(total=0, passed=0, failed=0, results=[])

        first = ModelComplianceCheckResult(node_id="node_a", passed=False)
        state, _ = reduce_compliance(state, first)
        assert state.total == 1
        assert state.failed == 1

        replacement = ModelComplianceCheckResult(node_id="node_a", passed=True)
        state, _ = reduce_compliance(state, replacement)

        assert state.total == 1
        assert state.passed == 1
        assert state.failed == 0
        assert len(state.results) == 1
        assert state.results[0].passed is True

    def test_preserves_run_identity(self) -> None:
        run_id = uuid4()
        now = datetime.now(tz=UTC)
        state = ModelComplianceReportState(
            total=0,
            passed=0,
            failed=0,
            results=[],
            run_id=run_id,
            repo_root="/some/repo",
            scan_started_at=now,
        )

        check = ModelComplianceCheckResult(node_id="node_a", passed=True)
        new_state, _ = reduce_compliance(state, check)

        assert new_state.run_id == run_id
        assert new_state.repo_root == "/some/repo"
        assert new_state.scan_started_at == now


@pytest.mark.unit
class TestReducerIsPure:
    """Reducer has no side effects — same input always produces same output."""

    def test_same_input_same_output(self) -> None:
        state = ModelComplianceReportState(
            total=1,
            passed=1,
            failed=0,
            results=[ModelComplianceCheckResult(node_id="node_a", passed=True)],
        )
        check = ModelComplianceCheckResult(node_id="node_b", passed=False)

        result_1, intents_1 = reduce_compliance(state, check)
        result_2, intents_2 = reduce_compliance(state, check)

        assert result_1.total == result_2.total
        assert result_1.passed == result_2.passed
        assert result_1.failed == result_2.failed
        assert len(result_1.results) == len(result_2.results)
        for r1, r2 in zip(result_1.results, result_2.results, strict=True):
            assert r1.node_id == r2.node_id
            assert r1.passed == r2.passed
        assert intents_1 == intents_2

    def test_does_not_mutate_input_state(self) -> None:
        original_results: list[ModelComplianceCheckResult] = [
            ModelComplianceCheckResult(node_id="node_a", passed=True)
        ]
        state = ModelComplianceReportState(
            total=1,
            passed=1,
            failed=0,
            results=original_results,
        )

        check = ModelComplianceCheckResult(node_id="node_b", passed=False)
        new_state, _ = reduce_compliance(state, check)

        assert len(state.results) == 1
        assert len(new_state.results) == 2
        assert state.total == 1
        assert new_state.total == 2
