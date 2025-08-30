"""
Model for Docker healthcheck test configuration.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelDockerHealthcheckTest(BaseModel):
    """Docker healthcheck test command configuration."""

    command: List[str] = Field(description="Health check command as list of strings")

    @classmethod
    def from_string(cls, test_string: str) -> "ModelDockerHealthcheckTest":
        """Create from a string command."""
        # Split shell command into list
        import shlex

        return cls(command=shlex.split(test_string))

    def to_compose_format(self) -> List[str]:
        """Convert to Docker Compose format."""
        return self.command
