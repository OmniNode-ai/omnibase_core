"""
CLI Handler Mixin for ONEX Tool Nodes.

Provides standardized CLI argument parsing and main() function implementation.
Eliminates boilerplate code for command-line interface handling.
"""

import argparse
import json
import sys
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class MixinCLIHandler[InputStateT, OutputStateT]:
    """
    Mixin that provides CLI handling capabilities to tool nodes.

    Features:
    - Standard argument parsing with common flags
    - Input/output handling (JSON, YAML, files)
    - Error handling and exit codes
    - Ready-to-use main() implementation

    Usage:
        class MyTool(MixinCLIHandler, MixinContractMetadata, ProtocolReducer):
            def get_cli_description(self) -> str:
                return self.description  # From MixinContractMetadata

            def add_custom_arguments(self, parser: argparse.ArgumentParser) -> None:
                parser.add_argument('--custom-flag', help='My custom flag')

            def process(self, input_state: MyInputState) -> MyOutputState:
                # Tool logic here
                return output

        if __name__ == "__main__":
            tool = MyTool()
            sys.exit(tool.main())
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the CLI handler mixin."""
        super().__init__(**kwargs)

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinCLIHandler",
            {"mixin_class": self.__class__.__name__},
        )

    def process(self, input_state: InputStateT) -> OutputStateT:
        """Process method that should be implemented by the tool."""
        msg = "Tool must implement process method"
        raise ModelOnexError(msg, EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED)

    def get_cli_description(self) -> str:
        """Get CLI description. Override to customize."""
        if hasattr(self, "description"):
            description: str = self.description
            return description
        return f"{self.__class__.__name__} - ONEX Tool"

    def add_custom_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add custom CLI arguments. Override to add tool-specific args."""
        # Default implementation - no custom arguments
        # Override in subclasses to add tool-specific arguments
        return

    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with standard ONEX flags."""
        parser = argparse.ArgumentParser(
            description=self.get_cli_description(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Standard input/output arguments
        parser.add_argument(
            "--input",
            type=str,
            help="Input data as JSON string or file path",
        )

        parser.add_argument(
            "--input-file",
            type=str,
            help="Path to input JSON/YAML file",
        )

        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: stdout)",
        )

        parser.add_argument(
            "--format",
            choices=["json", "yaml"],
            default="json",
            help="Output format (default: json)",
        )

        # Operational flags
        parser.add_argument(
            "--introspect",
            action="store_true",
            help="Run introspection and report capabilities",
        )

        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Validate input without processing",
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )

        parser.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Suppress non-error output",
        )

        # Add custom arguments from tool
        self.add_custom_arguments(parser)

        return parser

    def parse_input(self, args: argparse.Namespace) -> SerializedDict | None:
        """Parse input from CLI arguments."""
        input_data = None

        # Try --input first (JSON string or file path)
        if args.input:
            try:
                # Try parsing as JSON
                input_data = json.loads(args.input)
                emit_log_event(
                    LogLevel.DEBUG,
                    "Parsed input as JSON string",
                    {"size": len(args.input)},
                )
            except json.JSONDecodeError:
                # Try as file path
                input_path = Path(args.input)
                if input_path.exists():
                    input_data = self._load_file(input_path)
                else:
                    msg = f"Input is neither valid JSON nor existing file: {args.input}"
                    raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)

        # Try --input-file
        elif args.input_file:
            input_path = Path(args.input_file)
            if not input_path.exists():
                raise ModelOnexError(
                    message=f"Input file not found: {args.input_file}",
                    error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                )
            input_data = self._load_file(input_path)

        # Try stdin if no input specified
        elif not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                try:
                    input_data = json.loads(stdin_data)
                    emit_log_event(
                        LogLevel.DEBUG,
                        "Parsed input from stdin",
                        {"size": len(stdin_data)},
                    )
                except json.JSONDecodeError as e:
                    msg = f"Invalid JSON from stdin: {e}"
                    raise ModelOnexError(msg, EnumCoreErrorCode.PARSING_ERROR)

        return input_data

    def _load_file(self, path: Path) -> SerializedDict:
        """Load JSON or YAML file."""
        content = path.read_text()

        if path.suffix in [".yaml", ".yml"]:
            from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
            from omnibase_core.utils.util_safe_yaml_loader import (
                load_yaml_content_as_model,
            )

            # Load and validate YAML using Pydantic model

            yaml_model = load_yaml_content_as_model(content, ModelGenericYaml)

            data = yaml_model.model_dump()
        else:
            data = json.loads(content)

        emit_log_event(
            LogLevel.DEBUG,
            f"Loaded input from file: {path}",
            {"format": path.suffix, "size": len(content)},
        )

        return data

    def format_output(self, output: OutputStateT, output_format: str) -> str:
        """Format output based on requested format."""
        # Convert output to dict
        if hasattr(output, "model_dump"):
            output_dict = output.model_dump()
        elif isinstance(output, dict):
            output_dict = output
        else:
            output_dict = {"result": str(output)}

        # Format as requested
        if output_format == "yaml":
            from omnibase_core.utils.util_safe_yaml_loader import serialize_data_to_yaml

            return serialize_data_to_yaml(output_dict, default_flow_style=False)
        return json.dumps(output_dict, indent=2)

    def main(self, argv: list[str] | None = None) -> int:
        """Main entry point for CLI execution."""
        try:
            # Parse arguments
            parser = self.create_parser()
            args = parser.parse_args(argv)

            # Set logging level
            if args.verbose:
                # Would set to DEBUG in real implementation
                pass
            elif args.quiet:
                # Would set to ERROR in real implementation
                pass

            # Handle introspection
            if args.introspect:
                return self._handle_introspection()

            # Parse input
            input_data = self.parse_input(args)
            if input_data is None and not args.validate_only:
                emit_log_event(
                    LogLevel.ERROR,
                    "No input provided",
                    {"tool": self.__class__.__name__},
                )
                parser.error(
                    "No input provided. Use --input, --input-file, or pipe to stdin",
                )

            # Create input state
            if input_data:
                input_state = self._create_input_state(input_data)

                # Validate only if requested
                if args.validate_only:
                    emit_log_event(
                        LogLevel.INFO,
                        "✅ Input validation successful",
                        {"tool": self.__class__.__name__},
                    )
                    return 0

                # Process
                emit_log_event(
                    LogLevel.INFO,
                    f"Processing with {self.__class__.__name__}",
                    {"has_input": True},
                )

                output_state = self.process(input_state)

                # Format output
                output_str = self.format_output(output_state, args.format)

                # Write output
                if args.output:
                    Path(args.output).write_text(output_str)
                    emit_log_event(
                        LogLevel.INFO,
                        f"Wrote output to: {args.output}",
                        {"size": len(output_str), "format": args.format},
                    )
                else:
                    pass

            return 0

        except KeyboardInterrupt:
            emit_log_event(
                LogLevel.WARNING,
                "Process interrupted by user",
                {"tool": self.__class__.__name__},
            )
            return 130

        except Exception as e:  # catch-all-ok: CLI handler returns error exit code with logging, appropriate for CLI
            emit_log_event(
                LogLevel.ERROR,
                f"Tool execution failed: {e}",
                {
                    "tool": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            if not (hasattr(args, "quiet") and args.quiet):
                pass
            return 1

    def _create_input_state(self, data: SerializedDict) -> InputStateT:
        """Create input state from dictionary data."""
        from typing import cast

        # Get input state class from type hints
        if hasattr(self.process, "__annotations__"):
            annotations = self.process.__annotations__
            if "input_state" in annotations:
                input_class = annotations["input_state"]
                return cast("InputStateT", input_class(**data))

        # Fallback - return data as-is
        return data  # type: ignore[return-value]  # Fallback when input state class unavailable; dict substitutes for InputStateT

    def _handle_introspection(self) -> int:
        """Handle introspection request."""
        if hasattr(self, "introspect"):
            # Use tool's introspection method
            self.introspect()
        else:
            # Basic introspection - print tool info to stdout
            default_version = ModelSemVer(major=1, minor=0, patch=0)
            introspection_info = {
                "tool_name": self.__class__.__name__,
                "description": self.get_cli_description(),
                "version": getattr(self, "node_version", str(default_version)),
                "status": "healthy",
            }
            import json

            # print-ok: CLI introspection output to stdout
            print(json.dumps(introspection_info, indent=2))

        return 0
