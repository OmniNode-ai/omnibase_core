# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI commands for omnibase_core."""

from __future__ import annotations

import json as _json
import os
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.validation.validator_utils import ModelValidationResult

# Display configuration constants
MAX_ERRORS_DISPLAYED = 5  # Maximum errors shown before truncation in validation output


def get_version() -> str:
    """Get the package version with graceful fallback chain.

    Version Resolution Order:
        1. importlib.metadata.version("omnibase_core") - Reads from installed package metadata
        2. omnibase_core.__version__ - Falls back to module-level __version__ attribute
        3. "unknown" - Final fallback if all methods fail (never raises)

    Returns:
        The version string, or "unknown" if version cannot be determined.

    Note:
        This function is designed to never raise exceptions, ensuring
        CLI --version flag always works even in degraded environments.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("omnibase_core")
    except (ImportError, PackageNotFoundError):
        # Fallback to __init__.py version
        try:
            from omnibase_core import __version__

            return __version__
        except (
            ImportError,
            AttributeError,
        ):  # fallback-ok: version getter must never crash
            return "unknown"


def print_version(
    ctx: click.Context,
    _param: click.Parameter,
    value: bool,
) -> None:
    """Print version and exit.

    Args:
        ctx: Click context.
        _param: Click parameter (unused).
        value: Whether the flag was provided.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"onex version {get_version()}")
    ctx.exit(0)


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the version and exit.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """ONEX CLI - Command line tools for omnibase_core.

    The onex CLI provides tools for working with ONEX nodes,
    validation, and development workflows.

    \b
    Verbose Mode (-v, --verbose):
        Enables detailed output. Supported by:
        - validate: Shows file counts and error details
        - info: Shows Python path, working directory, installed ONEX packages
        - health: Shows detailed status messages for each check

    \b
    Examples:
        onex --help
        onex --version
        onex validate src/
        onex info
        onex --verbose health
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if ctx.invoked_subcommand is None:
        # No subcommand provided, show help
        click.echo(ctx.get_help())


@cli.command()
@click.argument(
    "directories",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Enable strict validation mode.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Quiet output (errors only).",
)
@click.pass_context
def validate(
    ctx: click.Context,
    directories: tuple[Path, ...],
    strict: bool,
    quiet: bool,
) -> None:
    """Validate ONEX compliance for directories.

    Runs ONEX architecture and pattern validation on the specified
    directories. If no directories are provided, defaults to 'src/'.

    \b
    Examples:
        onex validate
        onex validate src/ tests/
        onex validate --strict src/
    """
    verbose = ctx.obj.get("verbose", False)

    # Default to ONEX_SRC_DIR or src/ if no directories specified
    if not directories:
        env_src_dir = os.environ.get("ONEX_SRC_DIR")
        default_path = Path(env_src_dir) if env_src_dir else Path("src/")
        if default_path.exists():
            directories = (default_path,)
        else:
            message = f"No directories specified and default '{default_path}' not found"
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "No directories specified and no default source directory found",
                {"cwd": str(Path.cwd()), "onex_src_dir": env_src_dir},
            )
            raise click.ClickException(message)

    if verbose and not quiet:
        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Starting ONEX validation",
            {
                "directories": [str(d) for d in directories],
                "strict": strict,
            },
        )

    try:
        # Import validation suite lazily to avoid circular imports
        from omnibase_core.validation.validator_cli import ServiceValidationSuite

        suite = ServiceValidationSuite()
        overall_success = True

        for directory in directories:
            if not quiet:
                click.echo(f"Validating {directory}...")

            results = suite.run_all_validations(
                directory,
                strict=strict,
            )

            for validation_type, result in results.items():
                _display_validation_result(
                    validation_type, result, verbose=verbose, quiet=quiet
                )
                if not result.is_valid:
                    overall_success = False

        if not quiet:
            if overall_success:
                click.echo(click.style("All validations passed!", fg="green"))
            else:
                click.echo(click.style("Validation failures detected.", fg="red"))

        ctx.exit(EnumCLIExitCode.SUCCESS if overall_success else EnumCLIExitCode.ERROR)

    except ModelOnexError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Validation failed with ONEX error",
            {"error_code": str(e.error_code), "message": e.message},
        )
        raise click.ClickException(str(e)) from e
    except (
        Exception
    ) as e:  # catch-all-ok: CLI catch-all for user-friendly error messages
        # Catches unexpected errors in validation pipeline
        # Examples: FileNotFoundError (missing files), PermissionError (access denied),
        # OSError (disk issues), RuntimeError (validation logic bugs)
        # All other exceptions are converted to user-friendly ClickException
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Unexpected error during validation",
            {"error": str(e), "type": type(e).__name__},
        )
        raise click.ClickException(f"Unexpected error: {e}") from e


def _display_validation_result(
    validation_type: str,
    result: ModelValidationResult[None],
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Display validation result.

    Args:
        validation_type: Type of validation performed.
        result: The validation result.
        verbose: Whether to show verbose output.
        quiet: Whether to suppress non-error output.
    """
    if quiet and result.is_valid:
        return

    status_icon = (
        click.style("PASS", fg="green")
        if result.is_valid
        else click.style("FAIL", fg="red")
    )
    click.echo(f"  [{status_icon}] {validation_type}")

    if verbose or not result.is_valid:
        if result.metadata:
            click.echo(f"       Files processed: {result.metadata.files_processed}")

        if result.errors:
            error_count = len(result.errors)
            click.echo(f"       Issues: {error_count}")
            if verbose:
                for error in result.errors[:MAX_ERRORS_DISPLAYED]:
                    click.echo(f"         - {error}")
                if error_count > MAX_ERRORS_DISPLAYED:
                    click.echo(
                        f"         ... and {error_count - MAX_ERRORS_DISPLAYED} more"
                    )


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display information about omnibase_core.

    Shows version, Python version, and package information.
    """
    verbose = ctx.obj.get("verbose", False)

    click.echo(f"omnibase_core version: {get_version()}")
    click.echo(f"Python version: {sys.version.split()[0]}")

    if verbose:
        click.echo(f"Python path: {sys.executable}")
        click.echo(f"Working directory: {Path.cwd()}")

        # Show installed dependencies
        try:
            from importlib.metadata import distributions

            onex_packages = [
                d
                for d in distributions()
                if d.metadata.get("Name", "").startswith("omnibase")
            ]
            if onex_packages:
                click.echo("\nInstalled ONEX packages:")
                for pkg in onex_packages:
                    click.echo(f"  - {pkg.metadata['Name']} {pkg.version}")
        except (AttributeError, ImportError, KeyError, TypeError) as e:
            # Show error in verbose mode for debugging (this block only runs when verbose=True)
            # ImportError: metadata module not available
            # KeyError: metadata field missing (e.g., "Name")
            # AttributeError: malformed package object missing .version
            # TypeError: iteration/comparison issues with malformed metadata
            click.echo(
                click.style(
                    f"\nWarning: Could not list ONEX packages: {e}", fg="yellow"
                )
            )


@cli.command()
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Fail on duplicate entry-point names.",
)
@click.pass_context
def discover(ctx: click.Context, strict: bool) -> None:
    """Discover external ONEX nodes registered via entry points."""
    from omnibase_core.discovery.discovery_external_nodes import (
        discover_external_nodes,
    )
    from omnibase_core.errors.error_node_discovery import NodeDiscoveryError

    verbose = ctx.obj.get("verbose", False)
    try:
        nodes = discover_external_nodes(strict=strict)
    except NodeDiscoveryError as e:
        raise click.ClickException(str(e)) from e

    if not nodes:
        click.echo("No external ONEX nodes found.")
        return

    click.echo(f"Found {len(nodes)} external ONEX node(s):")
    for name, node in sorted(nodes.items()):
        click.echo(f"  {name} ({node.package_name} {node.package_version})")
        if verbose:
            click.echo(
                f"    Class: {node.node_class.__module__}.{node.node_class.__name__}"
            )


@cli.command()
@click.option(
    "--component",
    "-c",
    type=str,
    default=None,
    help="Specific component to check health for.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output results as structured JSON.",
)
@click.pass_context
def health(ctx: click.Context, component: str | None, as_json: bool) -> None:
    """Check health status of ONEX components.

    Performs basic health checks on ONEX infrastructure including
    Kafka reachability. Use --json for structured output.
    """
    verbose = ctx.obj.get("verbose", False)

    if not as_json:
        click.echo("ONEX Health Check")
        click.echo("-" * 40)

    checks = [
        ("Core imports", _check_core_imports),
        ("Validation system", _check_validation_system),
        ("Error handling", _check_error_handling),
        ("Kafka reachability", _check_kafka_reachable),
    ]

    available_components = [name for name, _ in checks]

    if component:
        checks = [
            (name, func) for name, func in checks if component.lower() in name.lower()
        ]
        if not checks:
            if as_json:
                click.echo(
                    _json.dumps(
                        {
                            "error": f"No health checks match component filter: '{component}'",
                            "available_components": available_components,
                        },
                        indent=2,
                    )
                )
            else:
                click.echo(
                    click.style(
                        f"No health checks match component filter: '{component}'",
                        fg="red",
                    )
                )
                partial_matches = _find_partial_matches(component, available_components)
                if partial_matches:
                    click.echo("\nDid you mean:")
                    for match in partial_matches:
                        click.echo(f"  - '{match}'")
                click.echo("\nAvailable components:")
                for comp_name in available_components:
                    click.echo(f"  - {comp_name}")
                click.echo(
                    "\nHint: Use a partial match, e.g., 'onex health --component core'"
                )
            ctx.exit(EnumCLIExitCode.ERROR)

    all_healthy = True
    results: list[dict] = []

    for check_name, check_func in checks:
        try:
            is_healthy, message = check_func()
            if not as_json:
                status = (
                    click.style("OK", fg="green")
                    if is_healthy
                    else click.style("FAIL", fg="red")
                )
                click.echo(f"  [{status}] {check_name}")
                if verbose or not is_healthy:
                    click.echo(f"       {message}")
            results.append(
                {"name": check_name, "healthy": is_healthy, "message": message}
            )
            if not is_healthy:
                all_healthy = False
        except Exception as e:  # noqa: BLE001  # catch-all-ok: health checks must not crash CLI
            if not as_json:
                click.echo(f"  [{click.style('FAIL', fg='red')}] {check_name}")
                click.echo(f"       Error: {e}")
            results.append({"name": check_name, "healthy": False, "message": str(e)})
            all_healthy = False

    if as_json:
        click.echo(
            _json.dumps(
                {
                    "overall": "healthy" if all_healthy else "unhealthy",
                    "checks": results,
                },
                indent=2,
            )
        )
    else:
        click.echo("-" * 40)
        if all_healthy:
            click.echo(click.style("All health checks passed!", fg="green"))
        else:
            click.echo(click.style("Some health checks failed.", fg="red"))

    ctx.exit(EnumCLIExitCode.SUCCESS if all_healthy else EnumCLIExitCode.ERROR)


def _find_partial_matches(
    filter_text: str, available_components: list[str]
) -> list[str]:
    """Find components that partially match the filter text.

    Uses multiple matching strategies:
    1. Component name contains any word from the filter
    2. Filter contains any word from the component name
    3. Common substring matching (minimum 3 characters)

    Args:
        filter_text: The user-provided filter string.
        available_components: List of available component names.

    Returns:
        List of component names that partially match, sorted by relevance.
    """
    matches: list[str] = []
    filter_lower = filter_text.lower()
    filter_words = set(filter_lower.replace("_", " ").replace("-", " ").split())

    for comp_name in available_components:
        comp_lower = comp_name.lower()
        comp_words = set(comp_lower.replace("_", " ").replace("-", " ").split())

        # Strategy 1: Any filter word appears in any component word
        for filter_word in filter_words:
            if len(filter_word) >= 3:  # Skip very short words
                for comp_word in comp_words:
                    if filter_word in comp_word or comp_word in filter_word:
                        if comp_name not in matches:
                            matches.append(comp_name)
                        break
                if comp_name in matches:
                    break

        # Strategy 2: Significant substring overlap (min 3 chars)
        if comp_name not in matches:
            # Check if filter shares a significant substring with component
            for i in range(len(filter_lower) - 2):
                substring = filter_lower[i : i + 3]
                if substring in comp_lower:
                    matches.append(comp_name)
                    break

    return matches


def _check_core_imports() -> tuple[bool, str]:
    """Check that core imports work.

    Returns:
        Tuple of (is_healthy, message).
    """
    try:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        # Verify we can use the imports
        _ = EnumCoreErrorCode.VALIDATION_ERROR
        _ = ModelOnexError

        return True, "Core imports successful"
    except ImportError as e:
        return False, f"Import error: {e}"


def _check_validation_system() -> tuple[bool, str]:
    """Check that validation system is available.

    Returns:
        Tuple of (is_healthy, message).
    """
    try:
        from omnibase_core.validation.validator_cli import ServiceValidationSuite

        suite = ServiceValidationSuite()
        validator_count = len(suite.validators)
        return True, f"Validation suite loaded with {validator_count} validators"
    except ImportError as e:
        return False, f"Import error: {e}"
    except PYDANTIC_MODEL_ERRORS as e:
        # AttributeError: suite missing .validators attribute
        # TypeError: validators not iterable
        # ValueError: validation configuration error
        return False, f"Error: {e}"


def _check_error_handling() -> tuple[bool, str]:
    """Check that error handling system works.

    Returns:
        Tuple of (is_healthy, message).
    """
    try:
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        # Create and catch a test error
        try:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Test error",
            )
        except ModelOnexError:
            pass

        return True, "Error handling system operational"
    except (AttributeError, ImportError, TypeError) as e:
        # ImportError: module not available
        # AttributeError: missing expected enum value or class attribute
        # TypeError: error class instantiation failure
        return False, f"Error: {e}"


def _check_kafka_reachable() -> tuple[bool, str]:
    """Check Kafka/Redpanda TCP reachability.

    Returns:
        Tuple of (is_healthy, message).
    """
    raw = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    first = raw.split(",")[0].strip()
    host, sep, port_str = first.rpartition(":")
    if not sep:
        host, port = first, 19092
    else:
        try:
            port = int(port_str)
        except ValueError:
            return False, f"Invalid port in KAFKA_BOOTSTRAP_SERVERS: {port_str!r}"

    try:
        conn = socket.create_connection((host, port), timeout=3)
        conn.close()
        return True, f"Kafka reachable at {host}:{port}"
    except (TimeoutError, OSError):
        return False, f"Kafka not reachable at {host}:{port}"


# Register compliance command group from separate module
from omnibase_core.cli.cli_compliance import compliance_group

cli.add_command(compliance_group, "compliance")

# Register composition-report command from separate module
from omnibase_core.cli.cli_composition_report import composition_report

cli.add_command(composition_report)

# Register contract command group from separate module
from omnibase_core.cli.cli_contract import contract

cli.add_command(contract)

# Register demo command group from separate module
from omnibase_core.cli.cli_demo import demo

cli.add_command(demo)

# Register db command group from separate module
from omnibase_core.cli.cli_db_migration import db

cli.add_command(db)

# Register spdx command group from separate module
from omnibase_core.cli.cli_spdx import spdx

cli.add_command(spdx)

# Register validate-shape command group from separate module
from omnibase_core.cli.cli_validate_shape import validate_shape

cli.add_command(validate_shape)

# Register new (scaffolding) command group from separate module
from omnibase_core.cli.cli_new import new_group

cli.add_command(new_group, "new")

# Register init command from separate module
from omnibase_core.cli.cli_init import init_command

cli.add_command(init_command, "init")

# Register registry command group from separate module
from omnibase_core.cli.cli_registry import registry

cli.add_command(registry)

# Register run command from separate module
from omnibase_core.cli.cli_run import run_workflow

cli.add_command(run_workflow)

# Register doctor command from separate module
from omnibase_core.cli.cli_doctor import doctor

cli.add_command(doctor)


# Register install/uninstall commands from separate module
from omnibase_core.cli.cli_install import cli_install, cli_uninstall

cli.add_command(cli_install)
cli.add_command(cli_uninstall)

# Register scaffold-channel-adapter command from separate module
from omnibase_core.cli.cli_scaffold_channel import cli_scaffold_channel_adapter

cli.add_command(cli_scaffold_channel_adapter)

# Register port-openclaw command from separate module
from omnibase_core.cli.cli_port_openclaw import cli_port_openclaw

cli.add_command(cli_port_openclaw)

# Register run-node command (Kafka-based remote node execution)
from omnibase_core.cli.cli_run_node import run_node

cli.add_command(run_node)

# Register bootstrap command group
from omnibase_core.cli.cli_bootstrap import bootstrap

cli.add_command(bootstrap)

# Register config command group (init + get)
from omnibase_core.cli.cli_config import config_group

cli.add_command(config_group)

# Register refresh-credentials command
from omnibase_core.cli.cli_refresh_credentials import refresh_credentials

cli.add_command(refresh_credentials)

# Load CLI extension groups registered by other packages via the onex.cli entry-point group.
# Each entry point must expose a click.Group or click.Command.
# This enables infra packages (e.g. omnibase_infra) to contribute subcommands
# (e.g. `onex kafka`) without creating circular imports in omnibase_core.
#
# Security note: entry points are resolved from pip-installed packages, whose
# trust boundary is the Python environment itself. Loading is limited to the
# installed package set — no arbitrary code is executed from untrusted sources.
import logging as _logging
from importlib.metadata import entry_points as _entry_points

_extension_log = _logging.getLogger(__name__)

for _ep in _entry_points(group="onex.cli"):
    try:
        _cmd = _ep.load()
        # boundary-ok: entry points are provided by pip-installed packages.
        if isinstance(_cmd, (click.Command, click.Group)):
            if _ep.name in cli.commands:
                _extension_log.warning(
                    "onex.cli extension %r conflicts with an existing command, skipping",
                    _ep.name,
                )
            else:
                cli.add_command(_cmd, _ep.name)
        else:
            _extension_log.warning(
                "onex.cli extension %r is not a click.Command or click.Group (got %s), skipping",
                _ep.name,
                type(_cmd).__name__,
            )
    except (ImportError, ModuleNotFoundError, AttributeError, TypeError) as _ext_err:
        # Narrow catch: expected failure modes when loading a broken/missing extension.
        # RuntimeError and other unexpected exceptions are NOT caught — they propagate
        # and remain visible rather than being silently swallowed.
        _extension_log.warning(
            "onex.cli extension %r failed to load: %s", _ep.name, _ext_err
        )

if __name__ == "__main__":
    cli()
