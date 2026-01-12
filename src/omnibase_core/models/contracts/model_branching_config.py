"""
Branching Configuration Model.

Defines conditional logic, decision points, and branching
strategies for dynamic workflow execution paths.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelBranchingConfig(BaseModel):
    """
    Conditional branching logic and decision trees.

    Defines conditional logic, decision points, and branching
    strategies for dynamic workflow execution paths.
    """

    decision_points: list[str] = Field(
        default_factory=list,
        description="Named decision points in the workflow",
    )

    condition_evaluation_strategy: str = Field(
        default="eager",
        description="Condition evaluation strategy (eager, lazy, cached)",
    )

    branch_merge_strategy: str = Field(
        default="wait_all",
        description="Strategy for merging parallel branches (wait_all, wait_any, wait_majority)",
    )

    default_branch_enabled: bool = Field(
        default=True,
        description="Enable default branch for unmatched conditions",
    )

    condition_timeout_ms: int = Field(
        default=1000,
        description="Timeout for condition evaluation in milliseconds",
        ge=1,
    )

    nested_branching_enabled: bool = Field(
        default=True,
        description="Enable nested branching structures",
    )

    max_branch_depth: int = Field(
        default=10,
        description="Maximum branching depth",
        ge=1,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
