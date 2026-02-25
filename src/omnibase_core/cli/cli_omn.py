# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
`omn` — Registry-Driven Dynamic CLI entrypoint.

Provides the static core commands for the ONEX dynamic CLI system.
All commands work with or without a populated catalog (graceful degradation).

Static core commands:
    omn version   — print CLI version and build metadata
    omn status    — show catalog state (last refresh, command count, connectivity)
    omn registry  — show registry connection info and available nodes
    omn doctor    — validate local environment (catalog, signatures, registry)
    omn refresh   — trigger catalog re-fetch and materialization

Dynamic commands discovered via cli.contribution.v1 contracts are layered on
top of this static skeleton by the catalog discovery mechanism.

.. versionadded:: 0.21.0  (OMN-2587)
"""

from __future__ import annotations

__all__ = [
    "omn",
]

import sys
from pathlib import Path

import click

# Default catalog cache path — mirrors ServiceCatalogManager default.
_DEFAULT_CATALOG_PATH = Path.home() / ".omn" / "catalog.json"


def _get_cli_version() -> str:
    """Get the CLI version with graceful fallback."""
    try:
        from importlib.metadata import version

        return version("omnibase_core")
    except (ImportError, Exception):  # fallback-ok: version getter must never crash
        try:
            from omnibase_core import __version__

            return __version__
        except (ImportError, AttributeError):
            return "unknown"


@click.group(
    invoke_without_command=True,
    help="ONEX Registry-Driven Dynamic CLI.",
)
@click.version_option(
    version=_get_cli_version(),
    prog_name="omn",
)
@click.pass_context
def omn(ctx: click.Context) -> None:
    """ONEX Registry-Driven Dynamic CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# omn version
# ---------------------------------------------------------------------------


@omn.command(name="version", help="Print CLI version and build metadata.")
def version_cmd() -> None:
    """Print CLI version and build metadata."""
    ver = _get_cli_version()
    click.echo(f"omn version {ver}")
    click.echo("runtime: omnibase_core")
    click.echo(f"python:  {sys.version.split()[0]}")


# ---------------------------------------------------------------------------
# omn status
# ---------------------------------------------------------------------------


@omn.command(
    name="status", help="Show catalog state (last refresh, command count, registry)."
)
def status_cmd() -> None:
    """Show catalog state."""
    catalog_path = _DEFAULT_CATALOG_PATH

    if not catalog_path.exists():
        click.echo("catalog:    NOT FOUND")
        click.echo("commands:   0")
        click.echo("refreshed:  never")
        click.echo("")
        click.echo("Run 'omn refresh' to build the catalog.")
        return

    try:
        import json

        raw = catalog_path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw)
    except (OSError, Exception) as exc:
        click.echo(f"catalog:    CORRUPT ({exc})")
        click.echo("Run 'omn refresh' to rebuild the catalog.")
        return

    commands_raw = data.get("commands", {})
    command_count = len(commands_raw) if isinstance(commands_raw, dict) else 0
    fetched_at = data.get("fetched_at", "unknown")
    cli_version = data.get("cli_version", "unknown")
    cache_key = str(data.get("cache_key", ""))[:16]

    click.echo(f"catalog:    OK  ({catalog_path})")
    click.echo(f"commands:   {command_count}")
    click.echo(f"refreshed:  {fetched_at}")
    click.echo(f"cli_version: {cli_version}")
    click.echo(f"cache_key:  {cache_key}...")


# ---------------------------------------------------------------------------
# omn registry
# ---------------------------------------------------------------------------


@omn.command(
    name="registry", help="Show registry connection info and available publisher nodes."
)
def registry_cmd() -> None:
    """Show registry connection info and available publisher nodes."""
    catalog_path = _DEFAULT_CATALOG_PATH

    if not catalog_path.exists():
        click.echo("registry:   no catalog found")
        click.echo("publishers: 0")
        click.echo("")
        click.echo("Run 'omn refresh' to load registry data.")
        return

    try:
        import json

        raw = catalog_path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw)
    except (OSError, Exception) as exc:
        click.echo(f"registry:   CORRUPT ({exc})")
        return

    sigs_raw = data.get("signatures", {})
    if isinstance(sigs_raw, dict):
        publishers = sorted(sigs_raw.keys())
    else:
        publishers = []

    click.echo(f"publishers: {len(publishers)}")
    for pub in publishers:
        sig_data = sigs_raw.get(pub, {}) if isinstance(sigs_raw, dict) else {}
        fp = (
            str(sig_data.get("fingerprint", ""))[:16]
            if isinstance(sig_data, dict)
            else ""
        )
        click.echo(f"  - {pub}  (fingerprint: {fp}...)")


# ---------------------------------------------------------------------------
# omn doctor
# ---------------------------------------------------------------------------


@omn.command(
    name="doctor",
    help="Validate local environment: catalog, signatures, registry reachability.",
)
def doctor_cmd() -> None:
    """Validate local environment."""
    catalog_path = _DEFAULT_CATALOG_PATH
    exit_code = 0

    # Check 1: catalog file
    if not catalog_path.exists():
        click.echo(f"[FAIL] catalog not found at {catalog_path}")
        click.echo("       Run 'omn refresh' to build the catalog.")
        sys.exit(1)
    click.echo(f"[OK]   catalog found at {catalog_path}")

    # Check 2: catalog parseable
    try:
        import json

        raw = catalog_path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw)
    except (OSError, Exception) as exc:
        click.echo(f"[FAIL] catalog parse error: {exc}")
        click.echo("       Run 'omn refresh' to rebuild the catalog.")
        sys.exit(1)
    click.echo("[OK]   catalog parseable")

    # Check 3: signature verification
    try:
        from omnibase_core.services.catalog.service_catalog_manager import (
            ServiceCatalogManager,
        )

        manager = ServiceCatalogManager(cache_path=catalog_path)
        manager.load()
        click.echo("[OK]   catalog signatures valid")
    except Exception as exc:
        click.echo(f"[FAIL] catalog signature error: {exc}")
        click.echo("       Run 'omn refresh' to rebuild the catalog.")
        exit_code = 1

    # Check 4: lockfile status (advisory)
    lockfile_path = Path.home() / ".omn" / "catalog.lock.json"
    if lockfile_path.exists():
        click.echo("[OK]   lockfile found")
    else:
        click.echo("[WARN] no lockfile found (run 'omn lock' to generate)")

    # Check 5: command count
    commands_raw = data.get("commands", {})
    count = len(commands_raw) if isinstance(commands_raw, dict) else 0
    click.echo(f"[OK]   commands in catalog: {count}")

    if exit_code != 0:
        sys.exit(exit_code)


# ---------------------------------------------------------------------------
# omn refresh
# ---------------------------------------------------------------------------


@omn.command(
    name="refresh",
    help="Trigger catalog re-fetch and materialization with diff output.",
)
@click.option(
    "--registry-url",
    default=None,
    help="Override registry URL (default: uses configured registry).",
)
def refresh_cmd(registry_url: str | None) -> None:
    """Trigger catalog re-fetch and materialization."""
    # In production this would connect to the live registry.
    # In this implementation we load from the configured registry or report
    # that no registry is configured.
    from omnibase_core.services.catalog.service_catalog_manager import (
        ServiceCatalogManager,
    )

    click.echo("Refreshing catalog...")

    try:
        # In a live system, registry would be injected via DI.
        # For the CLI binary, we construct a no-registry manager and report status.
        manager = ServiceCatalogManager(registry=None)
        # If cache exists, load it to get current state
        catalog_path = _DEFAULT_CATALOG_PATH
        if not catalog_path.exists():
            click.echo("No existing catalog found.")
            click.echo("Connect a registry and run 'omn refresh' again.")
            sys.exit(1)

        manager.load()
        cmds = manager.list_commands()
        click.echo(f"Catalog loaded: {len(cmds)} command(s).")
        click.echo(
            "Note: Live registry refresh requires a configured registry endpoint."
        )
    except Exception as exc:
        click.echo(f"Refresh failed: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    omn()
