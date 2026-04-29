# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Red tests for governance model Batch B — autopilot, compliance, eval (OMN-10246)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel


@pytest.mark.unit
class TestGovernanceBatchBImports:
    """Assert all Batch B governance models importable from omnibase_core.models.governance.*"""

    def test_model_autopilot_step_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_autopilot_step_result import (
            ModelAutopilotStepResult,
        )

        assert issubclass(ModelAutopilotStepResult, BaseModel)

    def test_model_autopilot_cycle_record_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_autopilot_cycle_record import (
            ModelAutopilotCycleRecord,
        )

        assert issubclass(ModelAutopilotCycleRecord, BaseModel)

    def test_model_repo_compliance_breakdown_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_repo_compliance_breakdown import (
            ModelRepoComplianceBreakdown,
        )

        assert issubclass(ModelRepoComplianceBreakdown, BaseModel)

    def test_model_compliance_sweep_report_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_compliance_sweep_report import (
            ModelComplianceSweepReport,
        )

        assert issubclass(ModelComplianceSweepReport, BaseModel)

    def test_model_eval_summary_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_summary import (
            ModelEvalSummary,
        )

        assert issubclass(ModelEvalSummary, BaseModel)

    def test_model_eval_report_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_report import (
            ModelEvalReport,
        )

        assert issubclass(ModelEvalReport, BaseModel)

    def test_model_eval_metric_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_metric import (
            ModelEvalMetric,
        )

        assert issubclass(ModelEvalMetric, BaseModel)

    def test_model_eval_run_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_run import (
            ModelEvalRun,
        )

        assert issubclass(ModelEvalRun, BaseModel)

    def test_model_eval_run_pair_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_run_pair import (
            ModelEvalRunPair,
        )

        assert issubclass(ModelEvalRunPair, BaseModel)

    def test_model_eval_task_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_task import (
            ModelEvalTask,
        )

        assert issubclass(ModelEvalTask, BaseModel)

    def test_model_eval_suite_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_eval_suite import (
            ModelEvalSuite,
        )

        assert issubclass(ModelEvalSuite, BaseModel)
