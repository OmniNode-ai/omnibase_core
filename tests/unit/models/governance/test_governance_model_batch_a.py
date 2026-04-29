# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Red tests for governance model Batch A — 7 simple models (OMN-10245)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel


@pytest.mark.unit
class TestGovernanceBatchAImports:
    """Assert all Batch A governance models importable from omnibase_core.models.governance.*"""

    def test_model_doc_cross_ref_check_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_doc_cross_ref_check import (
            ModelDocCrossRefCheck,
        )

        assert issubclass(ModelDocCrossRefCheck, BaseModel)

    def test_model_doc_reference_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_doc_reference import (
            ModelDocReference,
        )

        assert issubclass(ModelDocReference, BaseModel)

    def test_model_contract_drift_input_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_contract_drift_input import (
            ModelContractDriftInput,
        )

        assert issubclass(ModelContractDriftInput, BaseModel)

    def test_model_handler_compliance_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_handler_compliance_result import (
            ModelHandlerComplianceResult,
        )

        assert issubclass(ModelHandlerComplianceResult, BaseModel)

    def test_model_drift_history_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_drift_history import (
            ModelDriftHistory,
        )

        assert issubclass(ModelDriftHistory, BaseModel)

    def test_model_dependency_snapshot_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dependency_history import (
            ModelDependencySnapshot,
        )

        assert issubclass(ModelDependencySnapshot, BaseModel)

    def test_model_dependency_history_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dependency_history import (
            ModelDependencyHistory,
        )

        assert issubclass(ModelDependencyHistory, BaseModel)
