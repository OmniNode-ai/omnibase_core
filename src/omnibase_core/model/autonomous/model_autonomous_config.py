"""
Model for Autonomous Development Configuration

Configuration model for autonomous scenario processing.
"""

from pydantic import BaseModel, Field


class ModelAutonomousScenarioConfig(BaseModel):
    """Configuration for autonomous scenario processing."""

    max_scenarios_per_batch: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum scenarios to process per batch",
    )
    context_size_limit: int = Field(
        default=50000,
        ge=1000,
        le=100000,
        description="Maximum context size in tokens",
    )
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model to use for processing",
    )
    cost_limit_per_scenario: float = Field(
        default=2.0,
        ge=0.1,
        le=100.0,
        description="Cost limit per scenario in USD",
    )
    timeout_hours: int = Field(
        default=8,
        ge=1,
        le=24,
        description="Timeout per scenario in hours",
    )
    require_local_fallback: bool = Field(
        default=True,
        description="Require local LLM fallback if cloud fails",
    )
    create_pr_on_success: bool = Field(
        default=True,
        description="Create PR automatically on successful completion",
    )
    dry_run_mode: bool = Field(
        default=False,
        description="Run in dry mode without actual task submission",
    )
    task_type: str = Field(
        default="autonomous_tool_bootstrap",
        description="Task type for processing pipeline routing",
    )
    task_queue: str = Field(
        default="llm_analysis",
        description="Specific task queue to submit jobs to",
    )
