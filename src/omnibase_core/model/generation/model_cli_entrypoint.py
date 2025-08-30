"""
CLI entrypoint model for strongly typed CLI interface representation.

Provides structured representation of CLI entrypoints with proper validation.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator


class ModelCliEntrypoint(BaseModel):
    """Strongly typed CLI entrypoint definition."""

    command: str = Field(..., description="Base command (e.g., 'poetry run onex')")
    subcommand: str = Field(..., description="Subcommand (e.g., 'exec', 'run')")
    node_reference: str = Field(..., description="Node reference (e.g., 'node_name')")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        """Validate command format."""
        if not v or not isinstance(v, str):
            raise ValueError("Command must be a non-empty string")
        return v

    @field_validator("subcommand")
    @classmethod
    def validate_subcommand(cls, v):
        """Validate subcommand format."""
        if not v or not isinstance(v, str):
            raise ValueError("Subcommand must be a non-empty string")
        return v

    @field_validator("node_reference")
    @classmethod
    def validate_node_reference(cls, v):
        """Validate node reference format."""
        if not v or not isinstance(v, str):
            raise ValueError("Node reference must be a non-empty string")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Node reference must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    @classmethod
    def from_string(cls, entrypoint_str: str) -> "ModelCliEntrypoint":
        """
        Parse entrypoint string into structured components.

        Args:
            entrypoint_str: String like "poetry run onex exec node_name"

        Returns:
            ModelCliEntrypoint with parsed components
        """
        if not entrypoint_str:
            raise ValueError("Entrypoint string cannot be empty")

        parts = entrypoint_str.strip().split()
        if len(parts) < 3:
            raise ValueError(
                "Entrypoint must have at least 3 parts: command subcommand node_reference"
            )

        # Extract components
        # Handle multi-word commands like "poetry run onex"
        if len(parts) >= 4 and parts[0] == "poetry" and parts[1] == "run":
            command = f"{parts[0]} {parts[1]} {parts[2]}"  # "poetry run onex"
            subcommand = parts[3] if len(parts) > 3 else "exec"
            node_reference = parts[4] if len(parts) > 4 else "unknown"
        else:
            command = parts[0]
            subcommand = parts[1] if len(parts) > 1 else "exec"
            node_reference = parts[2] if len(parts) > 2 else "unknown"

        return cls(
            command=command, subcommand=subcommand, node_reference=node_reference
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCliEntrypoint":
        """Create from dictionary data."""
        if "entrypoint" in data and isinstance(data["entrypoint"], str):
            # Parse from string format
            return cls.from_string(data["entrypoint"])

        return cls(
            command=data.get("command", "poetry run onex"),
            subcommand=data.get("subcommand", "exec"),
            node_reference=data.get("node_reference", "unknown"),
        )

    def to_string(self) -> str:
        """Convert to entrypoint string format."""
        return f"{self.command} {self.subcommand} {self.node_reference}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "command": self.command,
            "subcommand": self.subcommand,
            "node_reference": self.node_reference,
            "entrypoint": self.to_string(),
        }
