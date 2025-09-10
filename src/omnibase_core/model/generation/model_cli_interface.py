"""
CLI interface model for contract representation.

Represents CLI interface definitions from contracts with strongly typed components.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from .model_cli_command import ModelCliCommand
from .model_cli_entrypoint import ModelCliEntrypoint


class ModelCliInterface(BaseModel):
    """CLI interface definition from contract with strongly typed components."""

    entrypoint: ModelCliEntrypoint | None = Field(
        None,
        description="Strongly typed CLI entrypoint",
    )
    commands: list[ModelCliCommand] = Field(
        default_factory=list,
        description="Strongly typed CLI commands",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelCliInterface"]:
        """Create from contract dict data with backwards compatibility."""
        if data is None:
            return None

        # Parse entrypoint
        entrypoint = None
        if "entrypoint" in data:
            if isinstance(data["entrypoint"], str):
                entrypoint = ModelCliEntrypoint.from_string(data["entrypoint"])
            elif isinstance(data["entrypoint"], dict):
                entrypoint = ModelCliEntrypoint.from_dict(data["entrypoint"])

        # Parse commands
        commands = []
        if "commands" in data:
            for cmd_data in data["commands"]:
                if isinstance(cmd_data, str):
                    # Legacy string format
                    commands.append(
                        ModelCliCommand(
                            name=cmd_data,
                            description=f"Execute {cmd_data} command",
                        ),
                    )
                elif isinstance(cmd_data, dict):
                    # Structured format
                    commands.append(ModelCliCommand.from_dict(cmd_data))

        return cls(entrypoint=entrypoint, commands=commands)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        # Custom transformation logic for CLI interface format
        result = {}

        if self.entrypoint:
            result["entrypoint"] = self.entrypoint.to_string()

        if self.commands:
            result["commands"] = [cmd.to_dict() for cmd in self.commands]

        return result

    def get_command_names(self) -> list[str]:
        """Get list of command names for backwards compatibility."""
        return [cmd.name for cmd in self.commands]

    def get_entrypoint_string(self) -> str | None:
        """Get entrypoint as string for backwards compatibility."""
        return self.entrypoint.to_string() if self.entrypoint else None

    def add_command(self, name: str, description: str, **kwargs) -> "ModelCliInterface":
        """Add a new command to the interface."""
        command = ModelCliCommand(name=name, description=description, **kwargs)
        updated = self.model_copy(deep=True)
        updated.commands.append(command)
        return updated

    def has_command(self, name: str) -> bool:
        """Check if interface has a specific command."""
        return any(cmd.name == name for cmd in self.commands)
