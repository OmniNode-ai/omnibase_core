"""
CLI Service for ONEX CLI operations.

This service handles CLI argument parsing, flag handling, and command line
integration extracted from ModelNodeBase as part of NODEBASE-001 Phase 4.

Author: ONEX Framework Team
"""

import json
import sys
import time
from pathlib import Path
from typing import Protocol, Union

from omnibase_core.core.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_config import (
    ModelCliConfig,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_error_details import (
    ModelCliErrorDetails,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_health_check_result import (
    ModelCliHealthCheckResult,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_introspection_data import (
    ModelCliIntrospectionData,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_output_data import (
    ModelCliOutputData,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_parsed_args import (
    ModelCliParsedArgs,
)
from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_result import (
    ModelCliResult,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ProtocolTool(Protocol):
    """Protocol for tools that can be used with CLI service."""

    def health_check(self) -> dict[str, str | bool] | bool | None:
        """Optional health check method."""
        ...

    def process(self, input_state: object) -> object:
        """Optional process method."""
        ...

    def get_version(self) -> str:
        """Optional version method."""
        ...

    def get_tool_metadata(self) -> dict[str, str | int | bool]:
        """Optional metadata method."""
        ...


ToolInputStateType = Union[dict[str, str | int | bool], object]
ToolResultType = Union[dict[str, str | int | bool], object, str, int, bool, None]


class CliService:
    """
    CLI service for handling command line argument parsing and flag operations.

    Extracted from ModelNodeBase as part of NODEBASE-001 Phase 4 deconstruction.
    Provides centralized CLI handling for all ONEX tools and services.
    """

    def __init__(self, config: ModelCliConfig | None = None):
        """
        Initialize CLI service with configuration.

        Args:
            config: Optional CLI configuration (creates default if not provided)
        """
        self._config = config or ModelCliConfig()

        # Performance timing
        self._operation_start_time = None

        emit_log_event(
            LogLevel.INFO,
            "CLI Service initialized",
            {
                "health_check_enabled": self._config.enable_health_check_flag,
                "introspect_enabled": self._config.enable_introspect_flag,
                "help_enabled": self._config.enable_help_flag,
            },
        )

    def parse_command_line_arguments(
        self,
        args: list[str] | None = None,
    ) -> ModelCliResult:
        """
        Parse command line arguments and return structured result.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            ModelCliResult: Parsed CLI arguments and flags
        """
        start_time = time.time()

        try:
            if args is None:
                args = sys.argv[1:]  # Skip script name

            emit_log_event(
                LogLevel.DEBUG,
                f"Parsing CLI arguments: {args}",
                {"arg_count": len(args)},
            )

            # Initialize result
            parsed_args = {}
            flags_detected = []

            # Check for special flags first
            if self._config.enable_health_check_flag and "--health-check" in args:
                flags_detected.append("--health-check")

                # Create proper parsed args model for health check
                parsed_args_model = ModelCliParsedArgs(
                    boolean_args={"health_check": True},
                )

                return ModelCliResult(
                    exit_code=self._config.default_exit_code_success,
                    parsed_args=parsed_args_model,
                    flags_detected=flags_detected,
                    operation_type="health_check",
                    success=True,
                    message="Health check flag detected",
                    should_exit=False,  # Don't exit yet, need to run health check
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            if self._config.enable_introspect_flag and "--introspect" in args:
                flags_detected.append("--introspect")

                # Create proper parsed args model for introspect
                parsed_args_model = ModelCliParsedArgs(
                    boolean_args={"introspect": True},
                )

                return ModelCliResult(
                    exit_code=self._config.default_exit_code_success,
                    parsed_args=parsed_args_model,
                    flags_detected=flags_detected,
                    operation_type="introspect",
                    success=True,
                    message="Introspect flag detected",
                    should_exit=False,  # Don't exit yet, need to run introspection
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            if self._config.enable_help_flag and ("--help" in args or "-h" in args):
                flags_detected.extend(
                    [flag for flag in ["--help", "-h"] if flag in args],
                )

                # Create proper parsed args model for help
                parsed_args_model = ModelCliParsedArgs(boolean_args={"help": True})

                return ModelCliResult(
                    exit_code=self._config.default_exit_code_success,
                    parsed_args=parsed_args_model,
                    flags_detected=flags_detected,
                    operation_type="help",
                    success=True,
                    message="Help flag detected",
                    should_exit=False,  # Don't exit yet, need to generate help
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Check for version flag - but only treat -v as version if it's alone or with --version
            version_detected = False
            if self._config.enable_version_flag:
                if "--version" in args:
                    version_detected = True
                    flags_detected.append("--version")
                elif "-v" in args and len(args) == 1:
                    # Only treat -v as version flag if it's the only argument
                    version_detected = True
                    flags_detected.append("-v")

            if version_detected:
                # Create proper parsed args model for version
                parsed_args_model = ModelCliParsedArgs(boolean_args={"version": True})

                return ModelCliResult(
                    exit_code=self._config.default_exit_code_success,
                    parsed_args=parsed_args_model,
                    flags_detected=flags_detected,
                    operation_type="version",
                    success=True,
                    message="Version flag detected",
                    should_exit=False,  # Don't exit yet, need to show version
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Parse remaining arguments as key-value pairs
            i = 0
            while i < len(args):
                arg = args[i]

                if arg.startswith("--"):
                    # Long form argument
                    if "=" in arg:
                        # Format: --key=value
                        key, value = arg[2:].split("=", 1)
                        parsed_args[key] = value
                        flags_detected.append(arg)
                    else:
                        # Format: --key value (or just --key)
                        key = arg[2:]
                        if i + 1 < len(args) and not args[i + 1].startswith("-"):
                            # Has value
                            parsed_args[key] = args[i + 1]
                            i += 1
                        else:
                            # Boolean flag
                            parsed_args[key] = "true"
                        flags_detected.append(arg)
                elif arg.startswith("-") and len(arg) > 1:
                    # Short form argument
                    key = arg[1:]
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        # Has value
                        parsed_args[key] = args[i + 1]
                        i += 1
                    else:
                        # Boolean flag
                        parsed_args[key] = "true"
                    flags_detected.append(arg)
                else:
                    # Positional argument
                    pos_key = (
                        f"arg_{len([k for k in parsed_args if k.startswith('arg_')])}"
                    )
                    parsed_args[pos_key] = arg

                i += 1

            # Convert parsed_args dict to proper model
            string_args = {}
            integer_args = {}
            boolean_args = {}

            for key, value in parsed_args.items():
                # Try to determine the type of each parsed argument
                if isinstance(value, str):
                    # Try to convert to int if possible
                    try:
                        integer_args[key] = int(value)
                    except ValueError:
                        # Try to convert to bool if it's a boolean string
                        if value.lower() in ("true", "false"):
                            boolean_args[key] = value.lower() == "true"
                        else:
                            string_args[key] = value
                # All values are strings at this point, so this is safe
                # (unreachable code removed by earlier type checking)

            # Create proper parsed args model
            parsed_args_model = ModelCliParsedArgs(
                string_args=string_args,
                integer_args=integer_args,
                boolean_args=boolean_args,
            )

            return ModelCliResult(
                exit_code=self._config.default_exit_code_success,
                parsed_args=parsed_args_model,
                flags_detected=flags_detected,
                operation_type="normal",
                success=True,
                message=f"Successfully parsed {len(args)} CLI arguments",
                should_exit=False,  # Normal operation, continue processing
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return self.handle_cli_error(e, "parse_arguments")

    def handle_health_check_flag(self, tool_instance: ProtocolTool) -> ModelCliResult:
        """
        Handle --health-check flag execution.

        Args:
            tool_instance: The tool instance to run health check on

        Returns:
            ModelCliResult: Health check result with appropriate exit code
        """
        start_time = time.time()

        try:
            emit_log_event(
                LogLevel.INFO,
                "Executing health check",
                {"tool_type": type(tool_instance).__name__},
            )

            # Try to run health check on the tool
            if hasattr(tool_instance, "health_check"):
                health_result = tool_instance.health_check()

                # Determine if health check passed
                if isinstance(health_result, dict):
                    success = health_result.get("status") in [
                        "healthy",
                        "success",
                        True,
                    ]
                    message = health_result.get("message", "Health check completed")
                else:
                    success = health_result is not None
                    message = "Health check completed successfully"

                exit_code = (
                    self._config.default_exit_code_success
                    if success
                    else self._config.default_exit_code_error
                )

                # Create proper health check result model
                if isinstance(health_result, dict):
                    health_check_model = ModelCliHealthCheckResult(
                        status=health_result.get(
                            "status",
                            "healthy" if success else "unhealthy",
                        ),
                        node_name=health_result.get(
                            "node_name",
                            type(tool_instance).__name__,
                        ),
                        details={str(k): str(v) for k, v in health_result.items()},
                    )
                else:
                    health_check_model = ModelCliHealthCheckResult(
                        status="healthy" if success else "unhealthy",
                        node_name=type(tool_instance).__name__,
                        details={
                            "result": (
                                str(health_result)
                                if health_result is not None
                                else "None"
                            ),
                        },
                    )

                # Create proper parsed args model
                parsed_args_model = ModelCliParsedArgs(
                    boolean_args={"health_check": True},
                )

                return ModelCliResult(
                    exit_code=exit_code,
                    parsed_args=parsed_args_model,
                    flags_detected=["--health-check"],
                    operation_type="health_check",
                    success=success,
                    message=message,
                    health_check_result=health_check_model,
                    should_exit=True,  # Health check should exit
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            # Tool doesn't have health_check method
            error_details_model = ModelCliErrorDetails(
                error_code="HEALTH_CHECK_NOT_IMPLEMENTED",
                error_message="Tool does not implement health_check method",
                context={"tool_type": type(tool_instance).__name__},
            )

            # Create proper parsed args model
            parsed_args_model = ModelCliParsedArgs(
                boolean_args={"health_check": True},
            )

            return ModelCliResult(
                exit_code=self._config.default_exit_code_error,
                parsed_args=parsed_args_model,
                flags_detected=["--health-check"],
                operation_type="health_check",
                success=False,
                message="Tool does not implement health_check method",
                should_exit=True,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_details=error_details_model,
            )

        except Exception as e:
            return self.handle_cli_error(e, "health_check")

    def handle_introspect_flag(
        self,
        tool_instance: ProtocolTool,
        contract_path: Path,
    ) -> ModelCliResult:
        """
        Handle --introspect flag execution.

        Args:
            tool_instance: The tool instance to introspect
            contract_path: Path to the contract file for introspection

        Returns:
            ModelCliResult: Introspection result with metadata
        """
        start_time = time.time()

        try:
            emit_log_event(
                LogLevel.INFO,
                "Executing introspection",
                {
                    "tool_type": type(tool_instance).__name__,
                    "contract_path": str(contract_path),
                },
            )

            # Build introspection data
            introspection_data = {}

            # Try to get comprehensive introspection data from new method first
            if hasattr(tool_instance, "get_introspection_data"):
                try:
                    comprehensive_data = tool_instance.get_introspection_data()
                    introspection_data.update(comprehensive_data)
                    emit_log_event(
                        LogLevel.DEBUG,
                        "Retrieved comprehensive introspection data",
                        {"data_sections": list(comprehensive_data.keys())},
                    )
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Failed to get comprehensive introspection data: {e!s}, using fallback",
                        {"tool_type": type(tool_instance).__name__, "error": str(e)},
                    )
                    # Fall back to basic introspection
                    introspection_data = self._build_basic_introspection_data(
                        tool_instance,
                        contract_path,
                    )
            else:
                # Fall back to basic introspection for tools without comprehensive support
                introspection_data = self._build_basic_introspection_data(
                    tool_instance,
                    contract_path,
                )

            # Output introspection data
            if self._config.output_format == "json":
                output_text = json.dumps(introspection_data, indent=2)
            else:
                # Convert introspection_data to expected format
                formatted_data: dict[str, str | int | bool | list[str]] = {}
                for key, value in introspection_data.items():
                    if isinstance(value, str | int | bool) or (
                        isinstance(value, list)
                        and all(isinstance(item, str) for item in value)
                    ):
                        formatted_data[key] = value
                    else:
                        formatted_data[key] = str(value)
                output_text = self._format_introspection_text(formatted_data)

            # Create proper introspection data model
            tool_methods = introspection_data.get("tool_methods", [])
            actions_list = []
            if isinstance(tool_methods, list):
                actions_list = [str(method) for method in tool_methods if method]

            introspection_model = ModelCliIntrospectionData(
                actions=actions_list,
                protocols=["ProtocolCliService"],  # This is a CLI service protocol
                metadata={
                    str(k): str(v)
                    for k, v in introspection_data.items()
                    if k != "tool_methods"
                },
            )

            # Create proper output data model
            output_model = ModelCliOutputData(
                content=output_text,
                format_type=self._config.output_format,
                success=True,
            )

            # Create proper parsed args model
            parsed_args_model = ModelCliParsedArgs(boolean_args={"introspect": True})

            return ModelCliResult(
                exit_code=self._config.default_exit_code_success,
                parsed_args=parsed_args_model,
                flags_detected=["--introspect"],
                operation_type="introspect",
                success=True,
                message="Introspection completed successfully",
                introspection_data=introspection_model,
                output_data=output_model,
                should_exit=True,  # Introspection should exit
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return self.handle_cli_error(e, "introspection")

    def convert_args_to_input_state(
        self,
        parsed_args: dict[str, str | int | bool],
        tool_instance: ProtocolTool,
    ) -> ToolInputStateType:
        """
        Convert parsed CLI arguments to tool-specific input state.

        Args:
            parsed_args: Dictionary of parsed CLI arguments
            tool_instance: The tool instance for input state creation

        Returns:
            ToolInputStateType: Tool-specific input state object
        """
        try:
            # Try to get input state class from tool
            if hasattr(tool_instance, "_get_input_state_class"):
                input_state_class = tool_instance._get_input_state_class()
                # Try to create input state with parsed args
                result_obj: object = input_state_class(**parsed_args)
                return result_obj
            if hasattr(tool_instance, "input_state_class"):
                input_state_class = tool_instance.input_state_class
                result_instance: object = input_state_class(**parsed_args)
                return result_instance
            # Fallback to simple dictionary
            emit_log_event(
                LogLevel.WARNING,
                "Tool does not provide input state class, using dict",
                {"tool_type": type(tool_instance).__name__},
            )
            return dict(parsed_args)

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to convert CLI args to input state: {e!s}",
                {
                    "tool_type": type(tool_instance).__name__,
                    "parsed_args": parsed_args,
                },
            )
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to convert CLI arguments to input state: {e!s}",
                parsed_args=str(parsed_args),
            ) from e

    def generate_help_text(
        self,
        tool_instance: ProtocolTool,
        contract_path: Path,
    ) -> str:
        """
        Generate help text for the tool based on contract and CLI interface.

        Args:
            tool_instance: The tool instance
            contract_path: Path to the contract file

        Returns:
            str: Generated help text
        """
        try:
            help_lines = []

            # Tool name and description
            tool_name = type(tool_instance).__name__
            help_lines.append(f"ONEX Tool: {tool_name}")
            help_lines.append("=" * (len(tool_name) + 12))
            help_lines.append("")

            # Add basic usage
            help_lines.append("USAGE:")
            help_lines.append(f"  python -m {type(tool_instance).__module__} [OPTIONS]")
            help_lines.append("")

            # Standard options
            help_lines.append("OPTIONS:")
            if self._config.enable_help_flag:
                help_lines.append("  --help, -h          Show this help message")
            if self._config.enable_health_check_flag:
                help_lines.append("  --health-check      Run tool health check")
            if self._config.enable_introspect_flag:
                help_lines.append("  --introspect        Show tool introspection data")
            if self._config.enable_version_flag:
                help_lines.append("  --version, -v       Show tool version")

            # Try to read contract for additional CLI info
            if contract_path and contract_path.exists():
                try:
                    import yaml

                    with open(contract_path) as f:
                        contract_data = yaml.safe_load(f)

                    if "cli_interface" in contract_data:
                        cli_interface = contract_data["cli_interface"]
                        if isinstance(cli_interface, dict):
                            help_lines.append("")
                            help_lines.append("TOOL-SPECIFIC OPTIONS:")

                            # Add tool-specific options
                            if "arguments" in cli_interface:
                                for arg_name, arg_info in cli_interface[
                                    "arguments"
                                ].items():
                                    if isinstance(arg_info, dict):
                                        description = arg_info.get(
                                            "description",
                                            "No description",
                                        )
                                        help_lines.append(
                                            f"  --{arg_name}        {description}",
                                        )
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Failed to parse contract CLI interface: {e!s}",
                        {"contract_path": str(contract_path)},
                    )

            help_lines.append("")
            help_lines.append(
                "For more information, see the tool's contract.yaml file.",
            )

            return "\n".join(help_lines)

        except Exception as e:
            return f"Error generating help text: {e!s}"

    def handle_cli_error(self, error: Exception, operation: str) -> ModelCliResult:
        """
        Handle CLI errors with appropriate exit codes and error messages.

        Args:
            error: The exception that occurred
            operation: The operation that failed

        Returns:
            ModelCliResult: Error result with appropriate exit code
        """
        emit_log_event(
            LogLevel.ERROR,
            f"CLI error in {operation}: {error!s}",
            {
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

        # Determine exit code
        exit_code = self._config.default_exit_code_error
        if isinstance(error, OnexError):
            exit_code = error.get_exit_code()
        elif operation in self._config.exit_code_mappings:
            exit_code = self._config.exit_code_mappings[operation]

        # Create proper error details model
        error_details_model = ModelCliErrorDetails(
            error_code=f"CLI_ERROR_{operation.upper()}",
            error_message=str(error),
            context={
                "operation": operation,
                "error_type": type(error).__name__,
            },
        )

        # Create proper parsed args model (empty for errors)
        parsed_args_model = ModelCliParsedArgs()

        return ModelCliResult(
            exit_code=exit_code,
            parsed_args=parsed_args_model,
            flags_detected=[],
            operation_type="error",
            success=False,
            message=f"CLI error in {operation}: {error!s}",
            should_exit=True,
            error_details=error_details_model,
        )

    def determine_exit_code(
        self,
        result: ToolResultType,
        error: Exception | None = None,
    ) -> int:
        """
        Determine appropriate CLI exit code from result or error.

        Args:
            result: The operation result
            error: Optional exception

        Returns:
            int: Appropriate CLI exit code
        """
        if error:
            if isinstance(error, OnexError):
                return int(error.get_exit_code())
            return int(self._config.default_exit_code_error)

        if result is None:
            return int(self._config.default_exit_code_error)

        # Check for status field
        if hasattr(result, "status"):
            status = result.status
            if hasattr(status, "value"):
                status = status.value

            if status == EnumOnexStatus.SUCCESS.value:
                return int(self._config.default_exit_code_success)
            if status in [EnumOnexStatus.ERROR.value, EnumOnexStatus.UNKNOWN.value]:
                return int(self._config.default_exit_code_error)
            # WARNING, PARTIAL, etc. - use success code
            return int(self._config.default_exit_code_success)

        return int(self._config.default_exit_code_success)

    def should_run_health_check(self, args: list[str] | None = None) -> bool:
        """
        Check if --health-check flag is present in arguments.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            bool: True if --health-check flag is present
        """
        if not self._config.enable_health_check_flag:
            return False

        if args is None:
            args = sys.argv

        return "--health-check" in args

    def should_run_introspect(self, args: list[str] | None = None) -> bool:
        """
        Check if --introspect flag is present in arguments.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            bool: True if --introspect flag is present
        """
        if not self._config.enable_introspect_flag:
            return False

        if args is None:
            args = sys.argv

        return "--introspect" in args

    def _format_introspection_text(
        self,
        data: dict[str, str | int | bool | list[str]],
    ) -> str:
        """
        Format introspection data as human-readable text.

        Args:
            data: Introspection data dictionary

        Returns:
            str: Formatted text
        """
        lines = []
        lines.append("=== TOOL INTROSPECTION ===")
        lines.append("")

        for key, value in data.items():
            if key == "tool_methods" and isinstance(value, list):
                lines.append(f"{key.replace('_', ' ').title()}:")
                for method in value:
                    lines.append(f"  - {method}")
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")

        lines.append("")
        lines.append("=" * 26)

        return "\n".join(lines)

    def _build_basic_introspection_data(
        self,
        tool_instance: ProtocolTool,
        contract_path: Path,
    ) -> dict:
        """
        Build basic introspection data for tools that don't support comprehensive introspection.

        Args:
            tool_instance: The tool instance to introspect
            contract_path: Path to the contract file

        Returns:
            dict: Basic introspection data
        """
        introspection_data = {
            "tool_class": type(tool_instance).__name__,
            "tool_module": type(tool_instance).__module__,
            "contract_path": str(contract_path),
            "contract_exists": contract_path.exists() if contract_path else False,
            "has_process_method": hasattr(tool_instance, "process"),
            "has_health_check": hasattr(tool_instance, "health_check"),
            "tool_methods": [
                method for method in dir(tool_instance) if not method.startswith("_")
            ],
            "introspection_type": "basic_fallback",
        }

        # Try to get version information
        if hasattr(tool_instance, "version"):
            introspection_data["version"] = str(tool_instance.version)
        elif hasattr(tool_instance, "get_version"):
            try:
                introspection_data["version"] = str(tool_instance.get_version())
            except Exception:
                introspection_data["version"] = "unknown"

        # Try to get additional tool metadata
        if hasattr(tool_instance, "get_tool_metadata"):
            try:
                introspection_data["tool_metadata"] = tool_instance.get_tool_metadata()
            except Exception as e:
                introspection_data["metadata_error"] = str(e)

        return introspection_data
