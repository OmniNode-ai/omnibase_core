"""
Model for Docker healthcheck test configuration.
"""

import shlex

from pydantic import BaseModel, Field


class ModelDockerHealthcheckTest(BaseModel):
    """Docker healthcheck test command configuration."""

    command: list[str] = Field(
        description="Health check command as list[Any]of strings"
    )

    @classmethod
    def from_string(cls, test_string: str) -> "ModelDockerHealthcheckTest":
        """Create from a string command."""
        # Split shell command into list of strings
        return cls(command=shlex.split(test_string))

    def to_compose_format(self) -> list[str]:
        """Convert to Docker Compose format."""
        return self.command
