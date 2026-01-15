"""GitHub Actions workflow input model.

This module defines ModelWorkflowInput, a Pydantic model representing an
input parameter for manually-triggered (workflow_dispatch) GitHub Actions
workflows. Inputs allow users to provide values when triggering a workflow.

Example:
    Input definition in workflow YAML::

        on:
          workflow_dispatch:
            inputs:
              environment:
                description: 'Deployment environment'
                required: true
                type: choice
                options:
                  - production
                  - staging

See Also:
    - ModelJob: Job definition using these inputs
    - GitHub Actions documentation on workflow_dispatch
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowInput(BaseModel):
    """GitHub Actions workflow_dispatch input definition.

    Represents a single input parameter for manual workflow triggers.
    Inputs can be strings, choices (dropdowns), or booleans.

    Attributes:
        description: Human-readable description shown in the UI.
        required: Whether the input must be provided to trigger.
        default: Default value if user doesn't provide one.
        type: Input type - "string", "choice", or "boolean".
        options: List of allowed values for choice type inputs.

    Example:
        Creating workflow inputs::

            env_input = ModelWorkflowInput(
                description="Target environment",
                required=True,
                type="choice",
                options=["prod", "staging", "dev"]
            )

            dry_run = ModelWorkflowInput(
                description="Perform dry run only",
                type="boolean",
                default=False
            )
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    description: str = Field(default=..., description="Input description")
    required: bool = Field(default=False, description="Whether input is required")
    default: object = Field(default=None, description="Default value")
    type: str = Field(
        default="string", description="Input type (string/choice/boolean)"
    )
    options: list[str] | None = Field(
        default=None, description="Options for choice type"
    )
