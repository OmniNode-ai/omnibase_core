"""
CLI Command Definition Model

Defines the structure for CLI commands discovered dynamically from node contracts.
This replaces hardcoded command enums with flexible, contract-driven command definitions.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_argument_description import (
    ModelArgumentDescription,
)
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_node_reference import ModelNodeReference


class ModelCliCommandDefinition(BaseModel):
    """
    CLI command definition discovered from node contracts.

    This model represents a single CLI command that can be executed via the ONEX CLI.
    Commands are discovered dynamically from node contract.yaml files, enabling
    third-party nodes to automatically expose their functionality via CLI.
    """

    command_name: str = Field(
        default=...,
        description="CLI command name (e.g., 'generate', 'validate')",
        pattern=r"^[a-z][a-z0-9_-]*$",
    )

    target_node: ModelNodeReference = Field(
        default=...,
        description="Target node for execution",
    )

    action: str = Field(default=..., description="Action to execute on the target node")

    description: str = Field(
        default=..., description="Human-readable command description"
    )

    required_args: list[ModelArgumentDescription] = Field(
        default_factory=list,
        description="Required command arguments",
    )

    optional_args: list[ModelArgumentDescription] = Field(
        default_factory=list,
        description="Optional command arguments",
    )

    event_type: ModelEventType = Field(
        default=..., description="Event type for execution"
    )

    examples: list[str] = Field(
        default_factory=list,
        description="Usage examples for help display",
    )

    category: str = Field(
        default="general",
        description="Command category for grouping in help",
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    deprecated: bool = Field(
        default=False,
        description="Whether this command is deprecated",
    )

    deprecation_message: str | None = Field(
        default=None,
        description="Deprecation warning message",
    )

    def get_qualified_name(self) -> str:
        """Get the qualified command name including namespace if present."""
        if hasattr(self.target_node, "namespace") and self.target_node.namespace:
            return f"{self.target_node.namespace}:{self.command_name}"
        return self.command_name

    def get_help_text(self) -> str:
        """Generate help text for this command."""
        help_lines = [self.description]

        if self.deprecated:
            help_lines.insert(
                0,
                f"[DEPRECATED] {self.deprecation_message or 'This command is deprecated'}",
            )

        if self.required_args:
            help_lines.append("\nRequired arguments:")
            for arg in self.required_args:
                help_lines.append(f"  --{arg.name}: {arg.description}")

        if self.optional_args:
            help_lines.append("\nOptional arguments:")
            for arg in self.optional_args:
                default_text = (
                    f" (default: {arg.default_value})"
                    if arg.default_value is not None
                    else ""
                )
                help_lines.append(f"  --{arg.name}: {arg.description}{default_text}")

        if self.examples:
            help_lines.append("\nExamples:")
            for example in self.examples:
                help_lines.append(f"  {example}")

        return "\n".join(help_lines)

    def matches_command(self, command_name: str) -> bool:
        """Check if this definition matches the given command name."""
        return (
            self.command_name == command_name
            or self.get_qualified_name() == command_name
        )
