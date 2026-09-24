# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI commands for omnibase_core."""

from __future__ import annotations

import importlib
import json as _json
import os
import socket
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.errors.model_onex_error import ModelOnexError

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
        try:  # fallback-ok: version getter must never crash
            from omnibase_core import __version__

            return __version__
        except (ImportError, AttributeError):
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


# --------------------------------------------------------------------------
# Lazy built-in command loading (OMN-19444)
# --------------------------------------------------------------------------
#
# Every built-in core command used to be imported at module level: ``from
# omnibase_core.cli.cli_doctor import doctor`` followed immediately by
# ``cli.add_command(doctor)``, repeated ~20 times. That meant importing this
# module at all -- for ANY onex invocation, from ``onex doctor --help`` to a
# bare ``onex --help`` -- paid for every command's own transitive import
# tree whether or not that command was ever invoked (measured: 5.1-6.1s on a
# clean install, most of it commands nobody asked for). ``_LazyCoreCommandGroup``
# defers each built-in's import to the first time click actually resolves that
# command by name, so ``onex <cmd> ...`` only pays for ``<cmd>``'s own
# dependency tree.
#
# This is deliberately scoped to CORE'S OWN commands only. The onex.cli
# EXTENSION group (kafka, delegate, market, cloud, ... contributed by other
# distributions via ``load_cli_extensions`` below) keeps its existing eager,
# fail-loud-at-import-time contract untouched: that is a dated, ticketed
# operator ruling (OMN-16967, 2026-08-29), pinned by
# ``tests/unit/cli/test_cli_extension_loader_fail_loud_omn16967.py``, and
# reversing it is a separate architectural decision this ticket does not make.
_LAZY_BUILTIN_COMMANDS: dict[str, tuple[str, str]] = {
    "compliance": ("omnibase_core.cli.cli_compliance", "compliance_group"),
    "composition-report": (
        "omnibase_core.cli.cli_composition_report",
        "composition_report",
    ),
    "contract": ("omnibase_core.cli.cli_contract", "contract"),
    "demo": ("omnibase_core.cli.cli_demo", "demo"),
    "db": ("omnibase_core.cli.cli_db_migration", "db"),
    "spdx": ("omnibase_core.cli.cli_spdx", "spdx"),
    "validate-shape": ("omnibase_core.cli.cli_validate_shape", "validate_shape"),
    "new": ("omnibase_core.cli.cli_new", "new_group"),
    "init": ("omnibase_core.cli.cli_init", "init_command"),
    "registry": ("omnibase_core.cli.cli_registry", "registry"),
    "doctor": ("omnibase_core.cli.cli_doctor", "doctor"),
    "install": ("omnibase_core.cli.cli_install", "cli_install"),
    "uninstall": ("omnibase_core.cli.cli_install", "cli_uninstall"),
    "scaffold-channel-adapter": (
        "omnibase_core.cli.cli_scaffold_channel",
        "cli_scaffold_channel_adapter",
    ),
    "port-openclaw": ("omnibase_core.cli.cli_port_openclaw", "cli_port_openclaw"),
    "run": ("omnibase_core.cli.cli_run", "run"),
    "run-node": ("omnibase_core.cli.cli_run_node", "run_node"),
    "pack": ("omnibase_core.cli.cli_pack", "cli_pack"),
    "bootstrap": ("omnibase_core.cli.cli_bootstrap", "bootstrap"),
    "config": ("omnibase_core.cli.cli_config", "config_group"),
    "refresh-credentials": (
        "omnibase_core.cli.cli_refresh_credentials",
        "refresh_credentials",
    ),
    "hooks": ("omnibase_core.cli.cli_hooks", "hooks_group"),
}


class _LazyCoreCommandGroup(click.Group):
    """A :class:`click.Group` whose built-in core subcommands import lazily.

    ``list_commands`` answers from names alone (no import). ``get_command``
    imports the target module on first resolution of that specific name,
    validates the resolved attribute is a real click command, caches it on
    ``self.commands`` (so a second lookup is free, matching click's own
    behaviour for eagerly-registered commands), and returns it.
    """

    def __init__(
        self,
        *args: object,
        lazy_commands: dict[str, tuple[str, str]] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._lazy_commands: dict[str, tuple[str, str]] = dict(lazy_commands or {})

    def list_commands(self, ctx: click.Context) -> list[str]:
        names = set(super().list_commands(ctx))
        names.update(self._lazy_commands)
        return sorted(names)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        target = self._lazy_commands.get(cmd_name)
        if target is None:
            return None
        module_path, attr_name = target
        module = importlib.import_module(module_path)
        resolved = getattr(module, attr_name)
        if not isinstance(resolved, (click.Command, click.Group)):
            raise ModelOnexError(
                f"the built-in command {cmd_name!r} resolved to "
                f"{type(resolved).__name__} from "
                f"'{module_path}.{attr_name}', not a click.Command or "
                "click.Group. This is a packaging defect in omnibase_core "
                "itself, not a plugin.",
                error_code=EnumCoreErrorCode.REGISTRY_VALIDATION_FAILED,
            )
        self.add_command(resolved, cmd_name)
        return resolved


@click.group(cls=_LazyCoreCommandGroup, invoke_without_command=True)
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


# Populated post-construction (rather than via a decorator kwarg) so the
# forwarding contract of click's own ``**attrs`` plumbing through
# ``click.group()`` -> ``click.command()`` -> ``Command.__init__`` is never a
# question: this is a plain attribute assignment on the already-built group.
cli._lazy_commands = _LAZY_BUILTIN_COMMANDS


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
    # Function-local (OMN-19444): emit_log_event_sync is used only inside this
    # command. At module level it pulled in omnibase_core.logging.logging_emit
    # -> omnibase_core.models.core (and the whole contract/orchestrator/event
    # model tree beneath it) on EVERY onex invocation, whether or not
    # ``validate`` was the command being run (measured ~1.9-4.5s, depending on
    # what else the interpreter had already imported).
    from omnibase_core.logging.logging_structured import emit_log_event_sync

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

    # OMN-16680: declared OUTSIDE the try because `ctx.exit()` must be called
    # outside it. `ctx.exit()` signals completion by raising
    # `click.exceptions.Exit`, which subclasses RuntimeError and was therefore
    # caught by the `except Exception` catch-all below and re-raised as
    # `ClickException("Unexpected error: EnumCLIExitCode.SUCCESS")`. That made
    # exit code 1 the only reachable outcome of `onex validate` on ANY input,
    # including a fully clean tree.
    overall_success = True

    try:
        # Import validation suite lazily to avoid circular imports
        from omnibase_core.validation.validator_cli import ServiceValidationSuite

        suite = ServiceValidationSuite()

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

    ctx.exit(EnumCLIExitCode.SUCCESS if overall_success else EnumCLIExitCode.ERROR)


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
            click.echo(f"    Entry point: {node.entry_point_value}")


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
    results: list[dict[str, str | bool]] = []

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
        from omnibase_core.errors.model_onex_error import ModelOnexError

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
        from omnibase_core.errors.model_onex_error import ModelOnexError

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
    raw = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
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


# Every built-in core command above (compliance, composition-report,
# contract, demo, db, spdx, validate-shape, new, init, registry, doctor,
# install, uninstall, scaffold-channel-adapter, port-openclaw, run,
# run-node, pack, bootstrap, config, refresh-credentials, hooks) is
# registered lazily via _LAZY_BUILTIN_COMMANDS above (OMN-19444), not
# imported and attached here.

# --------------------------------------------------------------------------
# onex.cli extension discovery (OMN-16967)
# --------------------------------------------------------------------------
#
# Packages contribute subcommands by advertising them in the ``onex.cli``
# entry-point group; installing the package is what makes its command exist.
# That is the registration contract for every CLI surface that lives outside
# this repo (``onex kafka`` from omnibase_infra, ``onex market`` and
# ``onex cloud`` from omnimarket), and it is what lets those repos add commands
# without a circular import back into omnibase_core.
#
# THIS LOADER FAILS LOUD, AND THAT IS THE POINT (2026-08-29 operator ruling).
# It previously logged a warning and skipped on every failure mode below. A
# skipped registration is invisible: the CLI starts fine, the command is simply
# absent, and the log line lands in a stream nobody reads during an install. The
# operator named this drift class directly — features get built outside
# entry-point registration *because nothing enforces the binding*. A malformed
# registration is a packaging defect in an installed distribution, so it is
# raised at import time, where whoever installed the package is standing.
#
# Three malformed shapes, all fatal:
#   * the target does not import / the attribute is missing;
#   * the target is not a click.Command or click.Group;
#   * the name is already taken (by a core command or by another distribution).
#
# The conflict case deserves its own note: click's ``add_command`` would let a
# second registration silently REPLACE the first, and ``entry_points`` has no
# defined ordering across distributions. Skipping and overwriting are both wrong
# — one of the two commands would win nondeterministically, per machine. Naming
# the collision is the only honest option.
#
# Security note: entry points are resolved from pip-installed packages, whose
# trust boundary is the Python environment itself. Loading is limited to the
# installed package set — no arbitrary code is executed from untrusted sources.
from importlib.metadata import EntryPoint
from importlib.metadata import entry_points as _entry_points

_CLI_EXTENSION_GROUP = "onex.cli"


def load_cli_extensions(
    group: click.Group,
    extension_points: Iterable[EntryPoint],
) -> list[str]:
    """Attach every advertised ``onex.cli`` extension to ``group``, or raise.

    Args:
        group: The root CLI the extensions are attached to.
        extension_points: The entry points to load, normally the live
            ``onex.cli`` group. Injected so the failure modes are testable
            without installing a broken distribution.

    Returns:
        The names attached, in the order they were processed.

    Raises:
        ModelOnexError: If any entry point fails to load, resolves to something
            that is not a click command, or claims a name that is already
            registered. Never partial-and-silent: a command that was advertised
            and did not arrive is reported, not skipped.
    """
    attached: list[str] = []
    for entry_point in extension_points:
        origin = (
            entry_point.dist.name
            if entry_point.dist is not None
            else "an unknown distribution"
        )
        try:
            command = entry_point.load()
            # boundary-ok: entry points are provided by pip-installed packages.
        except Exception as exc:
            raise ModelOnexError(
                f"the '{_CLI_EXTENSION_GROUP}' entry point "
                f"'{entry_point.name}' (from {origin}) points at "
                f"'{entry_point.value}', which failed to load: "
                f"{type(exc).__name__}: {exc}. The command it advertises does "
                f"not exist, so this is a packaging defect in {origin}, not a "
                f"CLI fault.",
                error_code=EnumCoreErrorCode.IMPORT_ERROR,
            ) from exc

        if not isinstance(command, (click.Command, click.Group)):
            raise ModelOnexError(
                f"the '{_CLI_EXTENSION_GROUP}' entry point "
                f"'{entry_point.name}' (from {origin}) resolved to "
                f"{type(command).__name__}, not a click.Command or click.Group. "
                f"'{entry_point.value}' must name a click command object.",
                error_code=EnumCoreErrorCode.REGISTRY_VALIDATION_FAILED,
            )

        if entry_point.name in group.commands:
            raise ModelOnexError(
                f"the '{_CLI_EXTENSION_GROUP}' entry point "
                f"'{entry_point.name}' (from {origin}) collides with a command "
                f"that is already registered. Entry points have no defined "
                f"order across distributions, so allowing this would make which "
                f"'onex {entry_point.name}' runs depend on the machine. Rename "
                f"one of them.",
                error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )

        group.add_command(command, entry_point.name)
        attached.append(entry_point.name)

    return attached


load_cli_extensions(cli, _entry_points(group=_CLI_EXTENSION_GROUP))

if __name__ == "__main__":
    cli()
