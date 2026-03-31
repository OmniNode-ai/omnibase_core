# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance report reducer — pure state accumulator.

Pure function: delta(state, check_result) -> (new_state, intents[])

Accumulates per-node compliance check results into a summary report.
Repeated results for the same node_id replace the previous entry (not append).
Zero I/O — state persistence is handled by the EFFECT node.

.. versionadded:: OMN-7070
"""

from __future__ import annotations

from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.models.reducer.model_intent import ModelIntent


def reduce_compliance(
    state: ModelComplianceReportState,
    check_result: ModelComplianceCheckResult,
) -> tuple[ModelComplianceReportState, list[ModelIntent]]:
    """Pure reducer: accumulate a check result into report state.

    Replace-on-duplicate: if a result for the same node_id already exists,
    the old entry is replaced and counts are adjusted accordingly.

    Returns:
        Tuple of (new_state, intents). Intents list is currently empty
        as no side effects are needed during accumulation.
    """
    new_results: list[ModelComplianceCheckResult] = []
    replaced = False
    old_passed = False

    for existing in state.results:
        if existing.node_id == check_result.node_id:
            new_results.append(check_result)
            replaced = True
            old_passed = existing.passed
        else:
            new_results.append(existing)

    if not replaced:
        new_results.append(check_result)

    if replaced:
        passed_delta = (1 if check_result.passed else 0) - (1 if old_passed else 0)
        new_state = ModelComplianceReportState(
            total=state.total,
            passed=state.passed + passed_delta,
            failed=state.failed - passed_delta,
            results=new_results,
            run_id=state.run_id,
            repo_root=state.repo_root,
            scan_started_at=state.scan_started_at,
        )
    else:
        new_state = ModelComplianceReportState(
            total=state.total + 1,
            passed=state.passed + (1 if check_result.passed else 0),
            failed=state.failed + (0 if check_result.passed else 1),
            results=new_results,
            run_id=state.run_id,
            repo_root=state.repo_root,
            scan_started_at=state.scan_started_at,
        )

    return new_state, []


class NodeComplianceReportReducer:
    """Handler wrapper for the compliance reducer.

    Delegates to the pure ``reduce_compliance`` function.
    """

    def execute(
        self,
        state: ModelComplianceReportState,
        check_result: ModelComplianceCheckResult,
    ) -> tuple[ModelComplianceReportState, list[ModelIntent]]:
        return reduce_compliance(state, check_result)
