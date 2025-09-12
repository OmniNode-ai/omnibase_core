"""
Pydantic model for CLI output.

Structured output model for CLI command results.
"""

from pydantic import BaseModel


class ModelCLIOutput(BaseModel):
    """Structured output for CLI commands."""

    # Define fields as appropriate for your CLI output
    value: str | None = None
    # Add more fields as needed
