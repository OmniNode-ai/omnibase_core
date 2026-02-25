# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Command Example Model — usage example for a registry-driven CLI command.

Part of the cli.contribution.v1 contract schema.

.. versionadded:: 0.19.0  (OMN-2536)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCliCommandExample"]


class ModelCliCommandExample(BaseModel):
    """A single usage example for a CLI command.

    Attributes:
        description: Brief human-readable description of what the example does.
        invocation: The command-line string the user would type.
        expected_output: Optional sample of expected output.
    """

    description: str = Field(
        ...,
        min_length=1,
        description="Brief description of what this example demonstrates.",
    )
    invocation: str = Field(
        ...,
        min_length=1,
        description="The command-line string (e.g., 'onex memory query --limit 10').",
    )
    expected_output: str | None = Field(
        default=None,
        description="Sample of expected output for documentation.",
    )

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )
