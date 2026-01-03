"""GitHub Actions workflow job model.

This module defines ModelJob, a Pydantic model representing a single job
within a GitHub Actions workflow. Jobs contain steps and can define
dependencies on other jobs, matrix strategies, and service containers.

Example:
    Job definition in YAML::

        build:
          runs-on: ubuntu-latest
          needs: [lint, test]
          steps:
            - uses: actions/checkout@v4
            - run: npm build

See Also:
    - ModelStep: Individual step within a job
    - WorkflowStrategy: Matrix strategy configuration
    - WorkflowServices: Service container configuration
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_workflow_configuration import (
    WorkflowServices,
    WorkflowStrategy,
)

from .model_git_hub_actions_container import ModelGitHubActionsContainer
from .model_step import ModelStep


class ModelJob(BaseModel):
    """GitHub Actions workflow job definition.

    Represents a single job in a GitHub Actions workflow. Jobs run on
    specified runners and contain a sequence of steps. Jobs can depend
    on other jobs and use matrix strategies for parallel execution.

    Attributes:
        runs_on: Runner label(s) for job execution (e.g., "ubuntu-latest").
        steps: Ordered list of steps to execute in the job.
        name: Optional display name for the job.
        needs: Job dependencies - jobs that must complete before this one.
        if_: Conditional expression for job execution.
        env: Environment variables available to all steps.
        timeout_minutes: Maximum job duration in minutes.
        strategy: Matrix strategy for parallel job variants.
        continue_on_error: Whether workflow continues if job fails.
        container: Docker container for job execution (string for image name,
            or ModelGitHubActionsContainer for full configuration).
        services: Service containers (databases, caches) for the job.
        outputs: Job outputs available to dependent jobs.

    Example:
        Creating a job model::

            job = ModelJob(
                runs_on="ubuntu-latest",
                steps=[ModelStep(run="echo hello")],
                needs=["build"],
                timeout_minutes=30
            )
    """

    runs_on: str | list[str] = Field(default=..., alias="runs-on")
    steps: list[ModelStep]
    name: str | None = None
    needs: str | list[str] | None = None
    if_: str | None = Field(default=None, alias="if")
    env: dict[str, str] | None = None
    timeout_minutes: int | None = Field(default=None, alias="timeout-minutes")
    strategy: WorkflowStrategy | None = None
    continue_on_error: bool | None = Field(default=None, alias="continue-on-error")
    container: str | ModelGitHubActionsContainer | None = None
    services: WorkflowServices | None = None
    outputs: dict[str, str] | None = None
