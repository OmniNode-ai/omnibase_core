# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceExplainRenderer — diagnostic explain renderer for registry-driven CLI commands.

Renders a human-readable diagnostic view of a ``ModelCliCommandEntry`` from
the local catalog cache.  All output is derived exclusively from the catalog
entry — no live registry calls are made.

## Output Fields

For each command, the renderer outputs:

- Contract ID (fully namespaced command ID)
- Contract fingerprint (sha256, sourced from catalog metadata)
- Publishing node ID (publisher)
- Required permissions list
- Invocation path (event topic, HTTP endpoint, callable ref, or subprocess cmd)
- Risk classification
- HITL requirement
- Visibility level
- CLI version compatibility (from policy context if provided)
- Last catalog refresh timestamp (from catalog metadata if provided)
- Full args schema (formatted, not raw JSON/YAML)
- Usage examples from contract

## Offline Safety

``ServiceExplainRenderer`` never imports from network-dependent modules.
It reads only from the ``ModelCliCommandEntry`` passed to ``render()``.

## Usage

    from omnibase_core.services.cli.service_explain_renderer import ServiceExplainRenderer

    renderer = ServiceExplainRenderer()
    output = renderer.render(command_entry)
    print(output)

    # With optional catalog metadata
    output = renderer.render(
        command_entry,
        catalog_refresh_ts="2026-02-25T01:00:00Z",
        cli_version="0.19.0",
    )

See Also:
    - ``omnibase_core.models.contracts.model_cli_contribution.ModelCliCommandEntry``
    - ``omnibase_core.services.catalog.service_catalog_manager.ServiceCatalogManager``

.. versionadded:: 0.19.0  (OMN-2576)
"""

from __future__ import annotations

__all__ = [
    "ServiceExplainRenderer",
]

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliCommandEntry,
    )

# Width of the separator line used in output.
_SEPARATOR_WIDTH = 60


class ServiceExplainRenderer:
    """Renders a human-readable diagnostic view of a catalog command entry.

    Produces a formatted string showing all diagnostic fields for a single
    ``ModelCliCommandEntry``.  The output is designed to be readable at the
    terminal — not raw JSON or YAML.

    This class is stateless: ``render()`` depends only on the arguments
    passed to it.

    Thread Safety:
        Stateless after construction; safe to share across threads.

    .. versionadded:: 0.19.0  (OMN-2576)
    """

    def render(
        self,
        command_entry: ModelCliCommandEntry,
        *,
        catalog_refresh_ts: str | None = None,
        cli_version: str | None = None,
    ) -> str:
        """Render a human-readable diagnostic view of a command entry.

        All data is sourced from ``command_entry`` and the optional metadata
        parameters.  No network calls are made.

        Args:
            command_entry: The ``ModelCliCommandEntry`` to explain.
            catalog_refresh_ts: ISO-8601 timestamp of the last catalog refresh.
                If not provided, ``(not available)`` is shown.
            cli_version: The running CLI version string (e.g. ``"0.19.0"``).
                If not provided, ``(not configured)`` is shown.

        Returns:
            Multi-line formatted string with all diagnostic fields.
        """
        lines: list[str] = []
        sep = "-" * _SEPARATOR_WIDTH

        lines.append(sep)
        lines.append(f"  omn explain: {command_entry.display_name}")
        lines.append(sep)

        # Contract identity
        lines.append("")
        lines.append("IDENTITY")
        lines.append(f"  Contract ID   : {command_entry.id}")
        lines.append(f"  Display Name  : {command_entry.display_name}")
        lines.append(f"  Group         : {command_entry.group}")
        lines.append(f"  Visibility    : {command_entry.visibility.value}")

        # Catalog metadata
        lines.append("")
        lines.append("CATALOG METADATA")
        refresh_display = (
            catalog_refresh_ts if catalog_refresh_ts else "(not available)"
        )
        version_display = cli_version if cli_version else "(not configured)"
        lines.append(f"  Last Refresh  : {refresh_display}")
        lines.append(f"  CLI Version   : {version_display}")

        # Invocation path
        lines.append("")
        lines.append("INVOCATION")
        inv = command_entry.invocation
        lines.append(f"  Type          : {inv.invocation_type.value}")
        if inv.topic:
            lines.append(f"  Topic         : {inv.topic}")
        if inv.endpoint:
            lines.append(f"  Endpoint      : {inv.endpoint}")
        if inv.callable_ref:
            lines.append(f"  Callable      : {inv.callable_ref}")
        if inv.subprocess_cmd:
            lines.append(f"  Command       : {inv.subprocess_cmd}")

        # Security & policy
        lines.append("")
        lines.append("SECURITY & POLICY")
        lines.append(f"  Risk Level    : {command_entry.risk.value}")
        lines.append(
            f"  HITL Required : {'yes' if command_entry.requires_hitl else 'no'}"
        )
        if command_entry.permissions:
            lines.append(f"  Permissions   : {', '.join(command_entry.permissions)}")
        else:
            lines.append("  Permissions   : (none)")

        # Description
        lines.append("")
        lines.append("DESCRIPTION")
        # Wrap description at 70 chars with 4-space indent
        for paragraph in command_entry.description.splitlines():
            lines.append(f"  {paragraph}" if paragraph else "")

        # Args schema
        lines.append("")
        lines.append("ARGS SCHEMA")
        lines.append(f"  Schema Ref    : {command_entry.args_schema_ref}")
        lines.append(f"  Output Ref    : {command_entry.output_schema_ref}")
        lines.append("")
        lines.append(
            "  (Schema is referenced — use 'omn schema <ref>' to view full schema.)"
        )

        # Examples
        lines.append("")
        lines.append("EXAMPLES")
        if command_entry.examples:
            for example in command_entry.examples:
                lines.append(f"  # {example.description}")
                lines.append(f"  {example.invocation}")
                if example.expected_output:
                    lines.append(f"  => {example.expected_output}")
                lines.append("")
        else:
            lines.append("  (no examples provided)")

        lines.append(sep)

        return "\n".join(lines)

    def render_not_found(self, command_id: str) -> str:
        """Render a not-found message for an unknown command ID.

        Args:
            command_id: The command ID that was not found in the catalog.

        Returns:
            Formatted not-found error message.
        """
        sep = "-" * _SEPARATOR_WIDTH
        lines: list[str] = [
            sep,
            "  omn explain: command not found",
            sep,
            "",
            f"  Command '{command_id}' is not in the local catalog.",
            "",
            "  Possible reasons:",
            "    - The command ID is misspelled",
            "    - The command is hidden or policy-blocked",
            "    - The catalog has not been refreshed (run: omn refresh)",
            "",
            "  Tip: run 'omn --help' to see all available commands.",
            sep,
        ]
        return "\n".join(lines)

    def render_schema_fields(
        self,
        args_schema: dict[str, object],
        command_id: str,
    ) -> str:
        """Render the args schema fields in a human-readable format.

        Formats the resolved JSON Schema dict as an indented field listing,
        showing name, type, description, default, and required status.

        Args:
            args_schema: Resolved JSON Schema dict (object type).
            command_id: Command ID for context in the header.

        Returns:
            Multi-line formatted string of schema fields.
        """
        lines: list[str] = []
        lines.append(f"Args schema for '{command_id}':")

        schema_type = args_schema.get("type")
        if schema_type != "object":
            lines.append(
                f"  (non-object schema type: {schema_type!r} — raw JSON shown)"
            )
            lines.append(f"  {json.dumps(args_schema, indent=2, default=str)}")
            return "\n".join(lines)

        properties: object = args_schema.get("properties", {})
        required_raw: object = args_schema.get("required", [])
        required_set: set[str] = (
            {str(r) for r in required_raw} if isinstance(required_raw, list) else set()
        )

        if not isinstance(properties, dict) or not properties:
            lines.append("  (no properties defined)")
            return "\n".join(lines)

        for prop_name in sorted(properties.keys()):
            prop_schema = properties[prop_name]
            if not isinstance(prop_schema, dict):
                lines.append(f"  {prop_name}: (malformed property schema)")
                continue

            prop_type = str(prop_schema.get("type", "string"))
            description = str(prop_schema.get("description", ""))
            default = prop_schema.get("default")
            enum_values: object = prop_schema.get("enum")
            is_required = prop_name in required_set

            type_display = prop_type
            if enum_values and isinstance(enum_values, list):
                type_display = f"enum({', '.join(str(v) for v in enum_values)})"

            req_marker = " [required]" if is_required else ""
            default_marker = f" (default: {default})" if default is not None else ""

            lines.append(
                f"  --{prop_name.replace('_', '-')}"
                f"  <{type_display}>{req_marker}{default_marker}"
            )
            if description:
                lines.append(f"      {description}")

        return "\n".join(lines)
