# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceSchemaArgumentParser — schema-driven CLI argument parser for the registry-driven CLI.

Generates a fully functional ``argparse.ArgumentParser`` at runtime from a
command's JSON Schema (as referenced via ``args_schema_ref`` in the
``cli.contribution.v1`` contract, then resolved and provided as a Python dict).

## Design Goals

- **Zero hardcoded flag definitions** — every flag is derived from the schema.
- **Deterministic** — the same schema always produces the same parser.
- **Type-safe** — type coercion (string, integer, boolean, array, enum) is
  performed before dispatch.
- **Rich help text** — schema descriptions, defaults, required markers, and
  examples are reflected in ``--help`` output.
- **--json flag** — auto-added to every dynamic command for structured output.

## JSON Schema -> argparse Mapping

Given a schema like::

    {
      "type": "object",
      "properties": {
        "limit": {
          "type": "integer",
          "description": "Max results to return.",
          "default": 10
        },
        "tags": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Filter tags (repeatable)."
        },
        "mode": {
          "type": "string",
          "enum": ["fast", "slow"],
          "description": "Execution mode."
        }
      },
      "required": ["mode"]
    }

The parser will produce::

    --limit INT           Max results to return. (default: 10)
    --tags TAGS           Filter tags (repeatable). (repeatable)
    --mode {fast,slow}    Execution mode. [required]
    --json                Return structured JSON output.

## Usage

    from omnibase_core.services.cli.service_schema_argument_parser import ServiceSchemaArgumentParser

    parser = ServiceSchemaArgumentParser.from_schema(
        command_id="com.omninode.memory.query",
        display_name="Query Memory",
        description="Search the memory store.",
        args_schema=schema_dict,
        permissions=["memory.read"],
        risk="low",
    )
    namespace = parser.parse_args(["--mode", "fast", "--limit", "5"])

See Also:
    - ``omnibase_core.errors.error_schema_argument_parser.SchemaParseError``
    - ``omnibase_core.services.cli.service_command_dispatcher.ServiceCommandDispatcher``

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "ServiceSchemaArgumentParser",
]

import argparse

from omnibase_core.errors.error_schema_argument_parser import SchemaParseError

# JSON Schema values are heterogeneous (strings, ints, bools, lists, dicts).
# dict[str, object] is the ONEX-preferred form for open-ended schema dicts.
# type[str] | type[int] | type[float] covers the argparse coercion types.


class ServiceSchemaArgumentParser:
    """Schema-driven CLI argument parser factory.

    Converts a JSON Schema (``dict``) into a fully-configured
    ``argparse.ArgumentParser``.  All flag definitions are derived from the
    schema -- no hardcoded argument definitions are permitted for dynamic
    commands.

    The ``--json`` flag is automatically added to every parser regardless of
    the schema contents.

    Thread Safety:
        ``from_schema`` is a pure function (no shared mutable state).
        The returned ``ArgumentParser`` is not thread-safe by itself (standard
        argparse behavior).

    .. versionadded:: 0.19.0  (OMN-2553)
    """

    @classmethod
    def from_schema(
        cls,
        *,
        command_id: str,
        display_name: str,
        description: str,
        args_schema: dict[str, object],
        permissions: list[str] | None = None,
        risk: str = "low",
        examples: list[str] | None = None,
    ) -> argparse.ArgumentParser:
        """Build an ``ArgumentParser`` from a JSON Schema dict.

        Args:
            command_id: Globally namespaced command ID (for help text).
            display_name: Human-readable command name.
            description: Full description of what the command does.
            args_schema: Resolved JSON Schema dict (object type, top-level
                ``properties`` and optional ``required`` array).
            permissions: Required permission strings (shown in help).
            risk: Risk level string (shown in help, e.g. "low", "high").
            examples: Optional list of example invocation strings.

        Returns:
            Fully-configured ``ArgumentParser`` with one flag per schema
            property plus the automatic ``--json`` flag.

        Raises:
            SchemaParseError: If the schema is not an object type, is missing
                ``properties``, or contains an unsupported property type.

        Notes:
            - Same schema input always produces a parser with the same flags
              (deterministic: properties are sorted by name).
            - ``boolean`` types generate a ``--flag / --no-flag`` pair via
              ``BooleanOptionalAction``.
            - ``array`` types use ``nargs="+"`` and append to a list.
        """
        # Validate top-level schema structure.
        if not isinstance(args_schema, dict):
            raise SchemaParseError(
                f"args_schema for command '{command_id}' must be a dict, "
                f"got {type(args_schema).__name__}"
            )
        schema_type = args_schema.get("type")
        if schema_type != "object":
            raise SchemaParseError(
                f"args_schema for command '{command_id}' must have type='object', "
                f"got type='{schema_type}'"
            )
        properties: object = args_schema.get("properties", {})
        if not isinstance(properties, dict):
            raise SchemaParseError(
                f"args_schema 'properties' for command '{command_id}' must be a dict."
            )

        required_fields: object = args_schema.get("required", [])
        if not isinstance(required_fields, list):
            raise SchemaParseError(
                f"args_schema 'required' for command '{command_id}' must be a list."
            )
        required_set: set[str] = {str(r) for r in required_fields}

        # Build extended description for the parser epilog.
        epilog_parts: list[str] = []
        if permissions:
            epilog_parts.append(f"Required permissions: {', '.join(permissions)}")
        epilog_parts.append(f"Risk level: {risk}")
        if examples:
            epilog_parts.append("Examples:")
            for ex in examples:
                epilog_parts.append(f"  {ex}")

        parser = argparse.ArgumentParser(
            prog=command_id,
            description=f"{display_name}\n\n{description}",
            epilog="\n".join(epilog_parts) if epilog_parts else None,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=True,
        )

        # Add flags from schema properties (sorted for determinism).
        for prop_name in sorted(properties.keys()):
            prop_schema = properties[prop_name]
            if not isinstance(prop_schema, dict):
                raise SchemaParseError(
                    f"Property '{prop_name}' in args_schema for command "
                    f"'{command_id}' must be a dict."
                )
            cls._add_argument(
                parser=parser,
                command_id=command_id,
                prop_name=prop_name,
                prop_schema=prop_schema,
                is_required=prop_name in required_set,
            )

        # Always add --json flag.
        parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Return structured JSON output regardless of output schema.",
        )

        return parser

    @classmethod
    def _add_argument(
        cls,
        *,
        parser: argparse.ArgumentParser,
        command_id: str,
        prop_name: str,
        prop_schema: dict[str, object],
        is_required: bool,
    ) -> None:
        """Add a single argument to the parser from a property schema.

        Args:
            parser: The parser to add the argument to.
            command_id: Command ID for error messages.
            prop_name: Property name (becomes ``--prop-name`` flag).
            prop_schema: Property's JSON Schema sub-dict.
            is_required: Whether this argument is required.

        Raises:
            SchemaParseError: If the property type is unsupported.
        """
        flag = f"--{prop_name.replace('_', '-')}"
        prop_type: str = str(prop_schema.get("type", "string"))
        description: str = str(prop_schema.get("description", ""))
        default: object = prop_schema.get("default")
        raw_enum: object = prop_schema.get("enum")
        enum_values: list[object] | None = (
            raw_enum if isinstance(raw_enum, list) else None
        )

        # Build help string with required marker.
        help_parts: list[str] = []
        if description:
            help_parts.append(description)
        if is_required:
            help_parts.append("[required]")
        elif default is not None:
            help_parts.append(f"(default: {default})")
        help_text = " ".join(help_parts) if help_parts else argparse.SUPPRESS

        if prop_type == "boolean":
            # Boolean: --flag / --no-flag pair.
            bool_default: bool | None = default if isinstance(default, bool) else None
            parser.add_argument(
                flag,
                action=argparse.BooleanOptionalAction,
                default=bool_default,
                help=help_text,
                required=is_required,
            )
            return

        if prop_type == "array":
            # Array: repeatable flag, appends items.
            items_schema: object = prop_schema.get("items", {})
            item_type_str: str = (
                str(items_schema.get("type", "string"))
                if isinstance(items_schema, dict)
                else "string"
            )
            item_type: type[str] | type[int] | type[float] = (
                cls._resolve_primitive_type(item_type_str, command_id, prop_name)
            )
            help_with_repeat = (
                f"{help_text} (repeatable)" if help_text else "(repeatable)"
            )
            parser.add_argument(
                flag,
                type=item_type,
                nargs="+",
                default=default,
                help=help_with_repeat,
                required=is_required,
                metavar=prop_name.upper(),
            )
            return

        if enum_values is not None:
            # Enum: restrict choices to listed string values.
            choices = [str(v) for v in enum_values]
            parser.add_argument(
                flag,
                type=str,
                choices=choices,
                default=default,
                help=help_text,
                required=is_required,
            )
            return

        # Primitive: string, integer, number.
        py_type: type[str] | type[int] | type[float] = cls._resolve_primitive_type(
            prop_type, command_id, prop_name
        )
        parser.add_argument(
            flag,
            type=py_type,
            default=default,
            help=help_text,
            required=is_required,
            metavar=prop_name.upper(),
        )

    @staticmethod
    def _resolve_primitive_type(
        type_str: str,
        command_id: str,
        prop_name: str,
    ) -> type[str] | type[int] | type[float]:
        """Resolve a JSON Schema primitive type string to a Python type.

        Args:
            type_str: JSON Schema type string (e.g. "string", "integer").
            command_id: Command ID for error messages.
            prop_name: Property name for error messages.

        Returns:
            Python type callable suitable for argparse ``type=`` argument.

        Raises:
            SchemaParseError: If the type is not supported.
        """
        mapping: dict[str, type[str] | type[int] | type[float]] = {
            "string": str,
            "integer": int,
            "number": float,
        }
        if type_str not in mapping:
            raise SchemaParseError(
                f"Unsupported property type '{type_str}' for property "
                f"'{prop_name}' in command '{command_id}'. "
                f"Supported types: {sorted(mapping)}"
            )
        return mapping[type_str]
