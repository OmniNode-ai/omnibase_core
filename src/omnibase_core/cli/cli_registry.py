# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Registry status CLI commands.

Provides the ``onex registry status`` command for inspecting active backends,
discovered nodes, and registered entry points with provenance information.

.. versionadded:: 0.36.0
    Added as part of CLI Registry Status (OMN-7066)
"""

from __future__ import annotations

from importlib.metadata import entry_points

import click

# Entry-point group names used by the ONEX platform.
_EP_GROUP_NODES = "onex.nodes"
_EP_GROUP_BACKENDS = "onex.backends"
_EP_GROUP_CLI = "onex.cli"


def _count_entry_points(group: str) -> int:
    """Count entry points registered under *group*."""
    return len(list(entry_points(group=group)))


def _discover_node_count() -> int:
    """Return the number of nodes discovered via the onex.nodes entry-point group."""
    return _count_entry_points(_EP_GROUP_NODES)


def _discover_backend_count() -> int:
    """Return the number of backends discovered via the onex.backends entry-point group."""
    return _count_entry_points(_EP_GROUP_BACKENDS)


def _discover_cli_extensions() -> list[str]:
    """Return names of CLI extensions discovered via the onex.cli entry-point group."""
    return sorted(ep.name for ep in entry_points(group=_EP_GROUP_CLI))


@click.group("registry")
def registry() -> None:  # stub-ok: Click group, subcommands via @registry.command()
    """Inspect the ONEX service registry."""


@registry.command("status")
@click.pass_context
def registry_status(ctx: click.Context) -> None:
    """Show active backends, discovered nodes, and entry-point extensions.

    Displays provenance for each backend — whether it was registered as a
    default, discovered via an entry point, or explicitly overridden.

    \b
    Examples:
        onex registry status
    """
    # -- Backend status lines ------------------------------------------------
    # When auto_configure_registry (OMN-7065) lands, this section will query
    # the live ServiceRegistry to report actual resolved backends with their
    # provenance.  Until then, report the built-in defaults that omnibase_core
    # ships as local-first fallbacks.
    _default_backends: list[tuple[str, str, str, str]] = [
        ("EventBus", "in-memory", "default", "omnibase_core"),
        ("StateStore", "none", "default", "omnibase_core"),
        ("Metrics", "in-memory", "default", "omnibase_core"),
        ("Tracing", "in-memory", "default", "omnibase_core"),
    ]

    for label, impl, source, package in _default_backends:
        click.echo(f"{label + ':':<13} {impl} (source: {source}, package: {package})")

    # -- Discovery counts ----------------------------------------------------
    node_count = _discover_node_count()
    backend_count = _discover_backend_count()
    cli_extensions = _discover_cli_extensions()

    click.echo(f"{'Nodes:':<13} {node_count} discovered")
    click.echo(f"{'Backends:':<13} {backend_count} registered ({_EP_GROUP_BACKENDS})")

    ext_names = f": {', '.join(cli_extensions)}" if cli_extensions else ""
    click.echo(
        f"{'CLI:':<13} {len(cli_extensions)} extension(s) ({_EP_GROUP_CLI}){ext_names}"
    )
