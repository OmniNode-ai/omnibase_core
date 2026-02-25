# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceHelpFormatter — schema-driven root help formatter for the registry-driven CLI.

Formats the root-level ``omn --help`` output by grouping visible commands from
the local catalog into logical sections:

- **Core** — core platform commands (group starts with "core" or group="core")
- **Node-provided** — commands contributed by nodes (all non-core, non-experimental)
- **Experimental** — commands with ``visibility == EXPERIMENTAL``

Hidden and policy-blocked commands are absent from the catalog entirely (they
are filtered out during ``ServiceCatalogManager.load()`` / ``refresh()``), so
this formatter never needs to check visibility itself.

## Design

- Input: a list of ``ModelCliCommandEntry`` objects from the catalog
- Output: a formatted string suitable for terminal display
- Offline safe: no network calls, reads only from supplied entries
- ``format_help()`` is a pure function (no shared mutable state)

## Usage

    from omnibase_core.services.cli.service_help_formatter import ServiceHelpFormatter

    formatter = ServiceHelpFormatter()
    catalog_entries = manager.list_commands()
    help_text = formatter.format_help(catalog_entries)
    print(help_text)

See Also:
    - ``omnibase_core.services.catalog.service_catalog_manager.ServiceCatalogManager``
    - ``omnibase_core.enums.enum_cli_command_visibility.EnumCliCommandVisibility``

.. versionadded:: 0.19.0  (OMN-2576)
"""

from __future__ import annotations

__all__ = [
    "ServiceHelpFormatter",
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliCommandEntry,
    )

from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility

# Width of the separator line used in output.
_SEPARATOR_WIDTH = 60

# Groups considered "Core" regardless of visibility.
_CORE_GROUPS: frozenset[str] = frozenset(
    {"core", "core-cli", "platform", "system", "catalog"}
)


class ServiceHelpFormatter:
    """Schema-driven root help formatter for the registry-driven CLI.

    Groups visible catalog commands into Core / Node-provided / Experimental
    sections and formats them for terminal display.

    The catalog is expected to contain only visible, policy-filtered commands.
    Hidden/blocked commands should be filtered out before calling
    ``format_help()``.

    Thread Safety:
        Stateless after construction; safe to share across threads.

    .. versionadded:: 0.19.0  (OMN-2576)
    """

    def format_help(
        self,
        entries: list[ModelCliCommandEntry],
        *,
        cli_version: str | None = None,
    ) -> str:
        """Format the root help output from a list of catalog entries.

        Groups commands by category and formats each section with a one-line
        description per command.  Hidden/blocked commands must already be
        excluded from ``entries`` (policy filtering is done by the catalog).

        Args:
            entries: List of visible ``ModelCliCommandEntry`` from the catalog.
            cli_version: Optional CLI version string shown in the header.

        Returns:
            Multi-line formatted string ready for terminal display.
        """
        core: list[ModelCliCommandEntry] = []
        node_provided: list[ModelCliCommandEntry] = []
        experimental: list[ModelCliCommandEntry] = []

        for entry in entries:
            # Experimental commands go in their own section
            if entry.visibility == EnumCliCommandVisibility.EXPERIMENTAL:
                experimental.append(entry)
            elif entry.group.lower() in _CORE_GROUPS:
                core.append(entry)
            else:
                node_provided.append(entry)

        # Sort each section by display_name for deterministic output
        core.sort(key=lambda e: e.display_name.lower())
        node_provided.sort(key=lambda e: e.display_name.lower())
        experimental.sort(key=lambda e: e.display_name.lower())

        lines: list[str] = []
        sep = "-" * _SEPARATOR_WIDTH

        # Header
        version_str = f" v{cli_version}" if cli_version else ""
        lines.append(f"omn{version_str} — OmniNode Registry-Driven CLI")
        lines.append("")
        lines.append("Usage: omn <command> [options]")
        lines.append("       omn explain <command>")
        lines.append("       omn --help")
        lines.append("")
        lines.append(sep)

        # Core section
        if core:
            lines.append("")
            lines.append("CORE COMMANDS")
            lines.append("")
            for entry in core:
                lines.append(self._format_entry_line(entry))
            lines.append("")

        # Node-provided section
        if node_provided:
            lines.append(sep)
            lines.append("")
            lines.append("NODE-PROVIDED COMMANDS")
            lines.append("")
            for entry in node_provided:
                lines.append(self._format_entry_line(entry))
            lines.append("")

        # Experimental section
        if experimental:
            lines.append(sep)
            lines.append("")
            lines.append("EXPERIMENTAL COMMANDS  [not for production use]")
            lines.append("")
            for entry in experimental:
                lines.append(self._format_entry_line(entry))
            lines.append("")

        # Empty catalog
        if not core and not node_provided and not experimental:
            lines.append("")
            lines.append("  No commands available.")
            lines.append("  Run 'omn refresh' to populate the catalog.")
            lines.append("")

        lines.append(sep)
        lines.append("")
        lines.append("  Run 'omn explain <command>' for detailed command info.")
        lines.append("  Run 'omn refresh' to update the command catalog.")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_entry_line(entry: ModelCliCommandEntry) -> str:
        """Format a single command entry as a one-line help listing.

        Args:
            entry: The command entry to format.

        Returns:
            Formatted string: ``  <id>  <one-line description>``
        """
        # Truncate description to first sentence / 60 chars for compact display
        description = entry.description.split("\n")[0].strip()
        if len(description) > 65:
            description = description[:62] + "..."

        # Pad command ID to 40 chars for alignment
        id_field = entry.id
        if len(id_field) > 40:
            id_field = id_field[:37] + "..."

        return f"  {id_field:<40}  {description}"
