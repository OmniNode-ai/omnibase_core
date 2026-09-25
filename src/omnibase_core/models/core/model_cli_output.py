# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Pydantic model for CLI output.

Structured output model for CLI command results.
"""

from pydantic import BaseModel, ConfigDict


class ModelCLIOutput(BaseModel):
    """Structured output for CLI commands."""

    model_config = ConfigDict(extra="forbid")

    # Define fields as appropriate for your CLI output
    value: str | None = None
    # Add more fields as needed
