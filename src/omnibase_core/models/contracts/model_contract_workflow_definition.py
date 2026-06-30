# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-side workflow definition model (OMN-12835).

Typed binding of a contract's declared ``workflow_definition`` block: workflow
metadata plus the typed execution-graph DAG, so declared graphs are no longer
silently dropped on parse.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_contract_execution_graph import (
    ModelContractExecutionGraph,
)
from omnibase_core.models.contracts.model_contract_workflow_metadata import (
    ModelContractWorkflowMetadata,
)


class ModelContractWorkflowDefinition(BaseModel):
    """
    Typed binding of a contract's declared ``workflow_definition`` block.

    Carries workflow metadata plus the typed execution-graph DAG so that
    declared graphs are no longer silently dropped on parse. ``coordination_rules``
    is intentionally left as a free-form mapping — it overlays runtime
    coordination knobs that are validated downstream, not structurally here.
    """

    workflow_metadata: ModelContractWorkflowMetadata = Field(
        description="Descriptive metadata for the declared workflow",
    )

    execution_graph: ModelContractExecutionGraph = Field(
        description="Typed, validated execution-graph DAG",
    )

    coordination_rules: dict[str, object] | None = Field(
        default=None,
        description="Optional free-form coordination overlay (execution_mode, retries, etc.)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
