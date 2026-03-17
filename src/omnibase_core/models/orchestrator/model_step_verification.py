# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Step verification model for orchestrator proof conditions.

Defines a concrete proof condition that can be attached to any orchestrator
step. Each verification specifies a check_type and a target, allowing the
orchestration runtime to verify that a step's prerequisites or postconditions
are satisfied.

Example:
    >>> from omnibase_core.models.orchestrator.model_step_verification import (
    ...     ModelStepVerification,
    ... )
    >>> v = ModelStepVerification(
    ...     check_type="command_exit_0",
    ...     target="uv --version",
    ...     description="Verify uv is installed",
    ... )
    >>> v.check_type
    'command_exit_0'
"""

from typing import Literal

from pydantic import BaseModel, Field


class ModelStepVerification(BaseModel):
    """Concrete proof condition for an orchestrator step.

    Not onboarding-specific -- any orchestrator step can declare
    verification criteria using this model.

    Attributes:
        check_type: The kind of verification to perform.
        target: Check-type-specific target (command, path, host:port, URL,
            or Python module name).
        timeout_seconds: Maximum time allowed for the check.
        description: Human-readable explanation of what is being verified.
    """

    check_type: Literal[
        "command_exit_0",
        "file_exists",
        "tcp_probe",
        "http_health",
        "python_import",
    ] = Field(description="Type of verification check to perform")
    target: str = Field(description="Check-specific target value")
    timeout_seconds: int = Field(
        default=10, description="Maximum time for the check in seconds"
    )
    description: str | None = Field(
        default=None, description="Human-readable description of the verification"
    )


__all__ = ["ModelStepVerification"]
