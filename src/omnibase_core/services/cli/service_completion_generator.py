# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceCompletionGenerator — dynamic shell completion generation for the registry-driven CLI.

Generates shell completion scripts (zsh, bash) entirely from the local catalog
and caller-supplied resolved schemas.  No network calls are made during
completion generation; the catalog must have been loaded via
``ServiceCatalogManager.load()`` or ``ServiceCatalogManager.refresh()`` first.

## Design Goals

- **Zero hardcoded command or flag names** — all completions are derived from
  catalog entries and their resolved JSON Schema argument definitions.
- **Deterministic** — the same catalog + same schemas always produce the same
  script bytes (commands and flags sorted by name).
- **Type-accurate** — JSON Schema types map to shell completion specifiers:
  ``string`` → freeform, ``integer`` → numeric, ``boolean`` → no-argument flag,
  ``enum`` → choice list, ``array`` → freeform (repeatable).
- **Policy-aware** — ``HIDDEN`` commands are excluded from completion output.
  Only ``PUBLIC``, ``EXPERIMENTAL``, and ``DEPRECATED`` commands are included.

## Supported Shells

- ``zsh`` — generates a ``#compdef`` function using ``_arguments`` with
  full flag specs and choice lists.
- ``bash`` — generates a ``complete`` registration using ``_complete_omn``
  with per-command option arrays and ``compgen``.

## Usage

    from omnibase_core.services.cli.service_completion_generator import (
        ServiceCompletionGenerator,
    )

    # Catalog loaded via ServiceCatalogManager.
    commands = catalog_manager.list_commands()

    # Resolved schemas: args_schema_ref -> JSON Schema dict.
    resolved_schemas = {
        "schema://com.omninode.memory.query.args.v1": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results."},
                "mode": {
                    "type": "string",
                    "enum": ["fast", "slow"],
                    "description": "Execution mode.",
                },
            },
            "required": ["mode"],
        },
    }

    script = ServiceCompletionGenerator.generate(
        shell="zsh",
        commands=commands,
        resolved_schemas=resolved_schemas,
    )
    print(script)  # pipe to file or source directly

## Refresh Reminder

After ``omn refresh``, users must re-source or re-install the completion script
for changes to take effect.  ``ServiceCompletionGenerator`` appends a comment
to each generated script reminding the user of this requirement.

See Also:
    - ``ServiceCatalogManager`` — provides ``list_commands()``
    - ``ServiceSchemaArgumentParser`` — sibling service that uses the same schema
      mapping logic for argparse
    - ``omnibase_core.errors.error_completion_generator.CompletionGenerationError``
    - ``omnibase_core.enums.enum_cli_command_visibility.EnumCliCommandVisibility``

.. versionadded:: 0.19.0  (OMN-2581)
"""

from __future__ import annotations

__all__ = [
    "ServiceCompletionGenerator",
]

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.errors.error_completion_generator import (
    CompletionGenerationError,
    CompletionUnsupportedShellError,
)

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliCommandEntry,
    )

# Supported shell identifiers.
_SUPPORTED_SHELLS: frozenset[str] = frozenset({"zsh", "bash"})

# JSON Schema type → shell completion hint (for documentation / metavar).
_SCHEMA_TYPE_TO_METAVAR: dict[str, str] = {
    "string": "STRING",
    "integer": "INT",
    "number": "FLOAT",
    "array": "ITEM",
    "boolean": "",
    "enum": "CHOICE",
}


class ServiceCompletionGenerator:
    """Dynamic shell completion generator for the registry-driven CLI.

    Generates completion scripts from a loaded command catalog and caller-supplied
    resolved JSON Schemas.  All output is deterministic and contains no hardcoded
    command or flag names.

    This class is a pure, stateless factory — all methods are class methods.
    No instances are created.

    Thread Safety:
        All methods are pure functions (no shared mutable state).

    .. versionadded:: 0.19.0  (OMN-2581)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        *,
        shell_name: str,
        commands: list[ModelCliCommandEntry],
        resolved_schemas: dict[str, dict[str, object]],
    ) -> str:
        """Generate a shell completion script for the given shell.

        Reads the provided command catalog and their resolved JSON Schemas,
        then produces a complete, sourceable shell completion script.

        Only ``PUBLIC``, ``EXPERIMENTAL``, and ``DEPRECATED`` commands are
        included — ``HIDDEN`` commands are excluded from all completion output.

        The generated script is deterministic: commands and flags are sorted
        alphabetically.

        Args:
            shell_name: Target shell name.  Supported values: ``"zsh"``, ``"bash"``.
            commands: List of ``ModelCliCommandEntry`` objects from the catalog.
                Typically obtained from ``ServiceCatalogManager.list_commands()``.
            resolved_schemas: Mapping from ``args_schema_ref`` (as stored in each
                command entry) to the fully resolved JSON Schema dict.  If a
                command's schema reference is absent from this mapping, that
                command's flags will be omitted from the completion (the command
                itself will still complete).

        Returns:
            A complete, sourceable shell completion script as a single string.
            The caller is responsible for writing it to a file or sourcing it
            directly.

        Raises:
            CompletionUnsupportedShellError: If ``shell_name`` is not ``"zsh"`` or
                ``"bash"``.
            CompletionGenerationError: If schema processing fails for a command.

        Notes:
            - Same catalog + same schemas always produces identical output.
            - After ``omn refresh``, users must re-source or re-install the
              completion script to pick up changes.
        """
        if shell_name not in _SUPPORTED_SHELLS:
            raise CompletionUnsupportedShellError(
                f"Unsupported shell '{shell_name}'. "
                f"Supported shells: {sorted(_SUPPORTED_SHELLS)}"
            )

        # Filter to visible commands (exclude HIDDEN) and sort for determinism.
        visible = sorted(
            (
                cmd
                for cmd in commands
                if cmd.visibility != EnumCliCommandVisibility.HIDDEN
            ),
            key=lambda c: c.id,
        )

        if shell_name == "zsh":
            return cls._generate_zsh(visible, resolved_schemas)
        # shell_name == "bash"
        return cls._generate_bash(visible, resolved_schemas)

    # ------------------------------------------------------------------
    # Shell-specific generators
    # ------------------------------------------------------------------

    @classmethod
    def _generate_zsh(
        cls,
        commands: list[ModelCliCommandEntry],
        resolved_schemas: dict[str, dict[str, object]],
    ) -> str:
        """Generate a zsh completion script.

        The generated script defines a ``_omn`` completion function registered
        for the ``omn`` command.  Each subcommand dispatches to a per-command
        ``_arguments`` specification derived from the command's JSON Schema.

        Args:
            commands: Sorted, visible command entries.
            resolved_schemas: Mapping from args_schema_ref to resolved schema.

        Returns:
            Complete zsh completion script as a string.
        """
        lines: list[str] = []
        lines.append("#compdef omn")
        lines.append("")
        lines.append("# Auto-generated by ServiceCompletionGenerator (OMN-2581).")
        lines.append(
            "# Re-run 'omn export completion --shell zsh' after 'omn refresh'"
            " to pick up catalog changes."
        )
        lines.append("")
        lines.append("_omn() {")
        lines.append("  local state")
        lines.append("  _arguments -C \\")
        lines.append("    '1:command:->commands' \\")
        lines.append("    '*::args:->args'")
        lines.append("")
        lines.append("  case $state in")
        lines.append("    commands)")
        lines.append("      local -a cmds")
        lines.append("      cmds=(")

        for cmd in commands:
            # Escape colons in description for zsh spec format.
            desc_escaped = cmd.description.replace(":", "\\:").replace("'", "\\'")
            # Use first sentence or truncate long descriptions.
            short_desc = desc_escaped.split(".")[0][:80]
            lines.append(f"        '{cmd.id}:{short_desc}'")

        lines.append("      )")
        lines.append("      _describe 'command' cmds")
        lines.append("      ;;")
        lines.append("    args)")
        lines.append("      case $words[1] in")

        for cmd in commands:
            schema = resolved_schemas.get(cmd.args_schema_ref)
            flag_specs = cls._build_zsh_flag_specs(cmd.id, schema)

            lines.append(f"        {cmd.id})")
            if flag_specs:
                lines.append("          _arguments \\")
                for i, spec in enumerate(flag_specs):
                    continuation = " \\" if i < len(flag_specs) - 1 else ""
                    lines.append(f"            {spec}{continuation}")
            else:
                lines.append("          # No schema-defined flags for this command.")
            lines.append("          ;;")

        lines.append("      esac")
        lines.append("      ;;")
        lines.append("  esac")
        lines.append("}")
        lines.append("")
        lines.append("_omn")
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def _generate_bash(
        cls,
        commands: list[ModelCliCommandEntry],
        resolved_schemas: dict[str, dict[str, object]],
    ) -> str:
        """Generate a bash completion script.

        The generated script defines a ``_complete_omn`` function registered
        for the ``omn`` command via ``complete``.  Each subcommand has a
        corresponding option array populated from its JSON Schema.

        Args:
            commands: Sorted, visible command entries.
            resolved_schemas: Mapping from args_schema_ref to resolved schema.

        Returns:
            Complete bash completion script as a string.
        """
        lines: list[str] = []
        lines.append("#!/usr/bin/env bash")
        lines.append("")
        lines.append("# Auto-generated by ServiceCompletionGenerator (OMN-2581).")
        lines.append(
            "# Re-run 'omn export completion --shell bash' after 'omn refresh'"
            " to pick up catalog changes."
        )
        lines.append("")
        lines.append("_complete_omn() {")
        lines.append("  local cur prev words cword")
        lines.append("  _init_completion 2>/dev/null || {")
        lines.append("    cur=${COMP_WORDS[COMP_CWORD]}")
        lines.append("    prev=${COMP_WORDS[COMP_CWORD-1]}")
        lines.append("    words=(${COMP_WORDS[@]})")
        lines.append("    cword=$COMP_CWORD")
        lines.append("  }")
        lines.append("")

        # Build sorted list of command IDs for top-level completion.
        cmd_ids = " ".join(cmd.id for cmd in commands)
        lines.append(f"  local commands='{cmd_ids}'")
        lines.append("")
        lines.append("  if [[ $cword -eq 1 ]]; then")
        lines.append('    COMPREPLY=( $(compgen -W "$commands" -- "$cur") )')
        lines.append("    return 0")
        lines.append("  fi")
        lines.append("")
        lines.append("  local cmd=${words[1]}")
        lines.append("  case $cmd in")

        for cmd in commands:
            schema = resolved_schemas.get(cmd.args_schema_ref)
            flag_list, enum_map = cls._build_bash_flag_data(cmd.id, schema)

            lines.append(f"    {cmd.id})")
            if flag_list:
                flags_str = " ".join(flag_list)
                lines.append(f"      local opts='{flags_str}'")

                # For enum flags, add choice-based completion.
                if enum_map:
                    lines.append("      case $prev in")
                    for flag_name, choices in sorted(enum_map.items()):
                        choices_str = " ".join(choices)
                        lines.append(f"        {flag_name})")
                        lines.append(
                            f"          COMPREPLY=( $(compgen -W '{choices_str}' -- \"$cur\") )"
                        )
                        lines.append("          return 0")
                        lines.append("          ;;")
                    lines.append("      esac")

                lines.append('      COMPREPLY=( $(compgen -W "$opts" -- "$cur") )')
            else:
                lines.append("      # No schema-defined flags for this command.")
                lines.append("      COMPREPLY=( $(compgen -W '' -- \"$cur\") )")
            lines.append("      ;;")

        lines.append("  esac")
        lines.append("  return 0")
        lines.append("}")
        lines.append("")
        lines.append("complete -F _complete_omn omn")
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Schema → completion spec builders
    # ------------------------------------------------------------------

    @classmethod
    def _build_zsh_flag_specs(
        cls,
        command_id: str,
        schema: dict[str, object] | None,
    ) -> list[str]:
        """Build zsh ``_arguments`` flag specification strings for a command.

        Each string is a single zsh argument spec in the format:
        ``'--flag[description]:metavar:(choice1 choice2)'`` for enums, or
        ``'--flag[description]:metavar:'`` for freeform/typed flags, or
        ``'--flag[description]'`` for boolean flags.

        Args:
            command_id: Command ID for error context.
            schema: Resolved JSON Schema for the command, or ``None``.

        Returns:
            Sorted list of zsh argument spec strings.

        Raises:
            CompletionGenerationError: If the schema is structurally invalid.
        """
        if schema is None:
            return []

        if not isinstance(schema, dict):
            raise CompletionGenerationError(
                f"Schema for command '{command_id}' must be a dict, "
                f"got {type(schema).__name__}"
            )

        properties: object = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise CompletionGenerationError(
                f"Schema 'properties' for command '{command_id}' must be a dict."
            )

        specs: list[str] = []
        for prop_name in sorted(properties.keys()):
            prop_schema = properties[prop_name]
            if not isinstance(prop_schema, dict):
                raise CompletionGenerationError(
                    f"Property '{prop_name}' schema for command '{command_id}' "
                    "must be a dict."
                )
            spec = cls._zsh_flag_spec(prop_name, prop_schema)
            specs.append(spec)

        # Always add --json flag.
        specs.append("'--json[Return structured JSON output]'")

        return specs

    @classmethod
    def _zsh_flag_spec(cls, prop_name: str, prop_schema: dict[str, object]) -> str:
        """Build a single zsh argument spec string from a property schema.

        Args:
            prop_name: Property name (becomes ``--prop-name``).
            prop_schema: Property's JSON Schema sub-dict.

        Returns:
            Zsh argument spec string.
        """
        flag = f"--{prop_name.replace('_', '-')}"
        prop_type: str = str(prop_schema.get("type", "string"))
        description: str = str(prop_schema.get("description", ""))
        raw_enum: object = prop_schema.get("enum")
        enum_values: list[str] | None = (
            [str(v) for v in raw_enum] if isinstance(raw_enum, list) else None
        )

        # Escape brackets in description for zsh spec.
        desc_escaped = description.replace("[", "\\[").replace("]", "\\]")

        if prop_type == "boolean":
            # Boolean: no argument, just --flag
            no_flag = f"--no-{prop_name.replace('_', '-')}"
            return f"'({flag} {no_flag}){flag}[{desc_escaped}]'"

        if enum_values is not None:
            choices_str = " ".join(enum_values)
            metavar = prop_name.upper()
            return f"'{flag}[{desc_escaped}]:{metavar}:({choices_str})'"

        metavar = _SCHEMA_TYPE_TO_METAVAR.get(prop_type, "STRING")
        return f"'{flag}[{desc_escaped}]:{metavar}:'"

    @classmethod
    def _build_bash_flag_data(
        cls,
        command_id: str,
        schema: dict[str, object] | None,
    ) -> tuple[list[str], dict[str, list[str]]]:
        """Build bash flag data for a command.

        Returns two structures:
        - A sorted list of ``--flag`` strings for ``compgen -W``.
        - A dict mapping ``--flag`` → list of enum choices (for value completion).

        Args:
            command_id: Command ID for error context.
            schema: Resolved JSON Schema for the command, or ``None``.

        Returns:
            Tuple of (flag_list, enum_map).
            ``flag_list``: sorted list of flag strings.
            ``enum_map``: mapping of flag → choices (only for enum flags).

        Raises:
            CompletionGenerationError: If the schema is structurally invalid.
        """
        if schema is None:
            return [], {}

        if not isinstance(schema, dict):
            raise CompletionGenerationError(
                f"Schema for command '{command_id}' must be a dict, "
                f"got {type(schema).__name__}"
            )

        properties: object = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise CompletionGenerationError(
                f"Schema 'properties' for command '{command_id}' must be a dict."
            )

        flag_list: list[str] = []
        enum_map: dict[str, list[str]] = {}

        for prop_name in sorted(properties.keys()):
            prop_schema = properties[prop_name]
            if not isinstance(prop_schema, dict):
                raise CompletionGenerationError(
                    f"Property '{prop_name}' schema for command '{command_id}' "
                    "must be a dict."
                )
            flag = f"--{prop_name.replace('_', '-')}"
            prop_type: str = str(prop_schema.get("type", "string"))
            raw_enum: object = prop_schema.get("enum")

            if prop_type == "boolean":
                no_flag = f"--no-{prop_name.replace('_', '-')}"
                flag_list.append(flag)
                flag_list.append(no_flag)
            else:
                flag_list.append(flag)
                if isinstance(raw_enum, list):
                    enum_map[flag] = [str(v) for v in raw_enum]

        # Always add --json flag.
        flag_list.append("--json")

        return flag_list, enum_map
