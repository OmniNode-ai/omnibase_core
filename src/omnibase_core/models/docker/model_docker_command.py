"""
Model for Docker command configuration.
"""

import shlex

from pydantic import BaseModel, Field


class ModelDockerCommand(BaseModel):
    """Docker command configuration."""

    command: list[str] = Field(description="Command as list[Any]of strings")

    @classmethod
    def from_string(cls, cmd_string: str) -> "ModelDockerCommand":
        """Create from a string command."""
        import shlex

        return cls(command=shlex.split(cmd_string))

    def to_string(self) -> str:
        """Convert to shell command string."""

        return " ".join(shlex.quote(arg) for arg in self.command)
