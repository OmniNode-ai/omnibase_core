"""
Workflow Coordination Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

Dedicated subcontract model for workflow coordination functionality providing:
- Workflow instance management and tracking
- Node assignment and coordination
- Progress monitoring and synchronization
- Execution graphs and rule management
- Performance metrics and optimization

This model is composed into node contracts that require workflow coordination functionality,
providing clean separation between node logic and workflow coordination behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_workflow import ModelWorkflow
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import all individual model components


class ModelWorkflowCoordinationSubcontract(BaseModel):
    """
    Workflow Coordination Subcontract for ORCHESTRATOR nodes.

    Provides workflow orchestration, node coordination, and execution
    management capabilities specifically for ORCHESTRATOR nodes in the ONEX architecture.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    subcontract_name: str = Field(
        default="workflow_coordination_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the subcontract",
    )

    applicable_node_types: list[str] = Field(
        default=["ORCHESTRATOR"],
        description="Node types this subcontract applies to (ORCHESTRATOR only)",
    )

    # Configuration
    max_concurrent_workflows: int = Field(
        default=10,
        description="Maximum number of concurrent workflows",
        ge=1,
        le=100,
    )

    default_workflow_timeout_ms: int = Field(
        default=600000,
        description="Default workflow timeout in milliseconds",
        ge=60000,
        le=3600000,
    )

    node_coordination_timeout_ms: int = Field(
        default=30000,
        description="Node coordination timeout in milliseconds",
        ge=5000,
        le=300000,
    )

    checkpoint_interval_ms: int = Field(
        default=60000,
        description="Checkpoint interval in milliseconds",
        ge=10000,
        le=600000,
    )

    auto_retry_enabled: bool = Field(
        default=True,
        description="Whether automatic retry is enabled",
    )

    parallel_execution_enabled: bool = Field(
        default=True,
        description="Whether parallel execution is enabled",
    )

    workflow_persistence_enabled: bool = Field(
        default=True,
        description="Whether workflow state persistence is enabled",
    )

    # Failure recovery configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed operations",
        ge=0,
        le=10,
    )

    retry_delay_ms: int = Field(
        default=2000,
        description="Delay between retries in milliseconds",
        ge=1000,
        le=60000,
    )

    exponential_backoff: bool = Field(
        default=True,
        description="Whether to use exponential backoff for retries",
    )

    model_config = {
        "extra": "ignore",  # Allow extra fields from YAML contracts
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
    }
