"""CLI commands for omnibase_core.

This module provides the main CLI entry point using Click.
The entry point 'onex' is configured in pyproject.toml.

Usage:
    onex --help
    onex --version
    onex validate src/
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.structured import emit_log_event_sync
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.validation.validation_utils import ModelValidationResult


def get_version() -> str:
    """Get the package version.

    Returns:
        The version string from pyproject.toml or __init__.py.
    """
    try:
        from importlib.metadata import version

        return version("omnibase_core")
    except Exception:
        # Fallback to __init__.py version
        try:
            from omnibase_core import __version__

            return __version__
        except Exception:  # fallback-ok: version getter must never crash
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
    Examples:
        onex --help
        onex --version
        onex validate src/
        onex info
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

    # Default to src/ if no directories specified
    if not directories:
        default_path = Path("src/")
        if default_path.exists():
            directories = (default_path,)
        else:
            emit_log_event_sync(
                EnumLogLevel.ERROR,
                "No directories specified and default 'src/' not found",
                {"cwd": str(Path.cwd())},
            )
            raise click.ClickException("No directories specified and 'src/' not found")

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
        from omnibase_core.validation.cli import ModelValidationSuite

        suite = ModelValidationSuite()
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

        sys.exit(EnumCLIExitCode.SUCCESS if overall_success else EnumCLIExitCode.ERROR)

    except ModelOnexError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Validation failed with ONEX error",
            {"error_code": str(e.error_code), "message": e.message},
        )
        raise click.ClickException(str(e)) from e
    except Exception as e:
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
                for error in result.errors[:5]:
                    click.echo(f"         - {error}")
                if error_count > 5:
                    click.echo(f"         ... and {error_count - 5} more")


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
                d for d in distributions() if d.metadata["Name"].startswith("omnibase")
            ]
            if onex_packages:
                click.echo("\nInstalled ONEX packages:")
                for pkg in onex_packages:
                    click.echo(f"  - {pkg.metadata['Name']} {pkg.version}")
        except Exception:
            pass


@cli.command()
@click.option(
    "--component",
    "-c",
    type=str,
    default=None,
    help="Specific component to check health for.",
)
@click.pass_context
def health(ctx: click.Context, component: str | None) -> None:
    """Check health status of ONEX components.

    Performs basic health checks on ONEX infrastructure.
    """
    verbose = ctx.obj.get("verbose", False)

    click.echo("ONEX Health Check")
    click.echo("-" * 40)

    checks = [
        ("Core imports", _check_core_imports),
        ("Validation system", _check_validation_system),
        ("Error handling", _check_error_handling),
    ]

    # Store available component names for error messages
    available_components = [name for name, _ in checks]

    if component:
        checks = [
            (name, func) for name, func in checks if component.lower() in name.lower()
        ]
        if not checks:
            click.echo(
                click.style(
                    f"No health checks match component filter: '{component}'", fg="red"
                )
            )
            click.echo("\nAvailable components:")
            for comp_name in available_components:
                click.echo(f"  - {comp_name}")
            click.echo(
                "\nHint: Use a partial match, e.g., 'onex health --component core'"
            )
            sys.exit(EnumCLIExitCode.ERROR)

    all_healthy = True
    for check_name, check_func in checks:
        try:
            is_healthy, message = check_func()
            status = (
                click.style("OK", fg="green")
                if is_healthy
                else click.style("FAIL", fg="red")
            )
            click.echo(f"  [{status}] {check_name}")
            if verbose or not is_healthy:
                click.echo(f"       {message}")
            if not is_healthy:
                all_healthy = False
        except Exception as e:
            click.echo(f"  [{click.style('FAIL', fg='red')}] {check_name}")
            click.echo(f"       Error: {e}")
            all_healthy = False

    click.echo("-" * 40)
    if all_healthy:
        click.echo(click.style("All health checks passed!", fg="green"))
        sys.exit(EnumCLIExitCode.SUCCESS)
    else:
        click.echo(click.style("Some health checks failed.", fg="red"))
        sys.exit(EnumCLIExitCode.ERROR)


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
        from omnibase_core.validation.cli import ModelValidationSuite

        suite = ModelValidationSuite()
        validator_count = len(suite.validators)
        return True, f"Validation suite loaded with {validator_count} validators"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:  # fallback-ok: health check returns status, not raises
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
    except Exception as e:  # fallback-ok: health check returns status, not raises
        return False, f"Error: {e}"


if __name__ == "__main__":
    cli()
