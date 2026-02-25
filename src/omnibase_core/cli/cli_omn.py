# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
omn — OmniNode Registry-Driven CLI entry point.

This module provides the ``omn`` CLI binary, the runtime-facing entry point
for the registry-driven command system introduced by OMN-2359.

Commands are **not hardcoded** here; they are discovered dynamically from the
local catalog (populated by ``omn refresh``).  This module provides only the
meta-commands that are always available regardless of catalog state:

- ``omn --help``   : Lists all visible catalog commands, grouped by category.
- ``omn explain <command>`` : Prints diagnostic details for a single command.

All other commands (node-provided, core, experimental) are dispatched via
``ServiceCommandDispatcher`` using entries from ``ServiceCatalogManager``.

## Offline Safety

``omn --help`` and ``omn explain`` read exclusively from the local catalog
cache (``~/.omn/catalog.json``).  No live registry calls are made.

## Entry Point

Registered in ``pyproject.toml`` as::

    [project.scripts]
    omn = "omnibase_core.cli.cli_omn:omn_cli"

.. versionadded:: 0.19.0  (OMN-2576)
"""

from __future__ import annotations

import click

from omnibase_core.errors.error_catalog import CatalogLoadError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_catalog(cli_version: str | None = None) -> object:
    """Load the local catalog manager.

    Returns a ready ``ServiceCatalogManager`` (already ``load()``ed), or
    raises ``CatalogLoadError`` if the cache is missing/corrupt.

    Args:
        cli_version: Optional CLI version string to pass to the manager.

    Returns:
        A loaded ``ServiceCatalogManager`` instance.

    Raises:
        CatalogLoadError: If the cache file is absent or invalid.
    """
    from omnibase_core.services.catalog.service_catalog_manager import (
        ServiceCatalogManager,
    )

    manager = ServiceCatalogManager(cli_version=cli_version)
    manager.load()
    return manager


# ---------------------------------------------------------------------------
# Root group with dynamic help
# ---------------------------------------------------------------------------


class _OmnGroup(click.Group):
    """Custom Click group that uses the catalog for root-level help output."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Override to render catalog-driven grouped help.

        Falls back to standard Click help if the catalog is unavailable.

        Args:
            ctx: Click context.
            formatter: Click help formatter (unused; we write directly).
        """
        try:
            manager = _load_catalog()
            from omnibase_core.services.catalog.service_catalog_manager import (
                ServiceCatalogManager,
            )
            from omnibase_core.services.cli.service_help_formatter import (
                ServiceHelpFormatter,
            )

            assert isinstance(manager, ServiceCatalogManager)
            entries = manager.list_commands()
            help_text = ServiceHelpFormatter().format_help(entries)
            click.echo(help_text, nl=False)
        except CatalogLoadError:
            # Catalog not yet populated — show minimal fallback help.
            click.echo(
                "omn — OmniNode Registry-Driven CLI\n"
                "\n"
                "Usage: omn <command> [options]\n"
                "       omn explain <command>\n"
                "\n"
                "Catalog not yet loaded. Run 'omn refresh' to populate commands.\n"
            )
        except Exception:  # catch-all-ok: help output must never crash
            super().format_help(ctx, formatter)


@click.group(cls=_OmnGroup, invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    default=False,
    is_eager=True,
    expose_value=False,
    callback=lambda ctx, _param, value: (
        _print_version_and_exit(ctx) if value and not ctx.resilient_parsing else None
    ),
    help="Show the omn CLI version and exit.",
)
@click.pass_context
def omn_cli(ctx: click.Context) -> None:
    """omn — OmniNode Registry-Driven CLI.

    Run 'omn --help' to list available commands.
    Run 'omn explain <command>' for diagnostic info on a command.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _print_version_and_exit(ctx: click.Context) -> None:
    """Print omn version and exit.

    Args:
        ctx: Click context for exit.
    """
    try:
        from importlib.metadata import version

        ver = version("omnibase_core")
    except Exception:  # catch-all-ok: version getter must never crash
        ver = "unknown"

    click.echo(f"omn (omnibase_core) version {ver}")
    ctx.exit(0)


# ---------------------------------------------------------------------------
# omn explain <command>
# ---------------------------------------------------------------------------


@omn_cli.command(name="explain")
@click.argument("command_id", metavar="<command>")
@click.pass_context
def explain_command(ctx: click.Context, command_id: str) -> None:
    """Print diagnostic information for a registry command.

    Shows all fields from the local catalog for <command>:
    contract ID, fingerprint, publisher, permissions, invocation path,
    risk classification, HITL requirement, visibility, version compat,
    last refresh timestamp, full args schema, and usage examples.

    Reads exclusively from the local catalog cache. No network calls.

    \b
    Examples:
        omn explain com.omninode.memory.query
        omn explain com.omninode.events.publish

    \b
    Exit codes:
        0  Command found and explained.
        1  Command not found in catalog (or catalog not loaded).
    """
    from omnibase_core.services.cli.service_explain_renderer import (
        ServiceExplainRenderer,
    )

    renderer = ServiceExplainRenderer()

    try:
        manager = _load_catalog()
        from omnibase_core.services.catalog.service_catalog_manager import (
            ServiceCatalogManager,
        )

        assert isinstance(manager, ServiceCatalogManager)

        entry = manager.get_command(command_id)

        if entry is None:
            click.echo(renderer.render_not_found(command_id))
            ctx.exit(1)

        # Pull catalog metadata for context if available
        catalog_refresh_ts: str | None = None
        try:
            from pathlib import Path

            cache_path = Path.home() / ".omn" / "catalog.json"
            if cache_path.exists():
                import json

                raw = json.loads(cache_path.read_text(encoding="utf-8"))
                catalog_refresh_ts = str(raw.get("fetched_at", ""))
        except Exception:  # catch-all-ok: metadata enrichment is best-effort
            pass

        output = renderer.render(
            entry,
            catalog_refresh_ts=catalog_refresh_ts or None,
        )
        click.echo(output)
        ctx.exit(0)

    except CatalogLoadError as exc:
        click.echo(
            f"Error: Catalog not loaded — {exc}\n"
            "Run 'omn refresh' to build the catalog.",
            err=True,
        )
        ctx.exit(1)


if __name__ == "__main__":
    omn_cli()
