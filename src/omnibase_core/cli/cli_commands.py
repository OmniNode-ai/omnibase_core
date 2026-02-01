"""CLI commands for omnibase_core.

This module provides the main CLI entry point using Click.
The entry point 'onex' is configured in pyproject.toml.

Usage:
    onex --help
    onex --version
    onex validate src/
"""

from __future__ import annotations

import os
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

            # Find partial matches - components that share substrings with the filter
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
        except Exception as e:  # catch-all-ok: health checks must not crash CLI
            # Ensures CLI stability even if health check functions fail
            # Examples: ImportError (missing modules), AttributeError (API changes),
            # RuntimeError (check logic bugs), OSError (system resource issues)
            # All failures are reported gracefully without crashing the CLI
            click.echo(f"  [{click.style('FAIL', fg='red')}] {check_name}")
            click.echo(f"       Error: {e}")
            all_healthy = False

    click.echo("-" * 40)
    if all_healthy:
        click.echo(click.style("All health checks passed!", fg="green"))
        ctx.exit(EnumCLIExitCode.SUCCESS)
    else:
        click.echo(click.style("Some health checks failed.", fg="red"))
        ctx.exit(EnumCLIExitCode.ERROR)


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


# Register composition-report command from separate module
from omnibase_core.cli.cli_composition_report import composition_report

cli.add_command(composition_report)

# Register contract command group from separate module
from omnibase_core.cli.cli_contract import contract

cli.add_command(contract)

# Register demo command group from separate module
from omnibase_core.cli.cli_demo import demo

cli.add_command(demo)


if __name__ == "__main__":
    cli()
