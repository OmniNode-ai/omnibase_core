# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI commands for DB repository contract migration.

Provides tools to convert positional parameters ($1, $2) to named parameters (:param).
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import yaml

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync

# Positional parameter pattern ($1, $2, etc.)
_POSITIONAL_PARAM_PATTERN = re.compile(r"\$(\d+)")


def convert_positional_to_named(sql: str, param_order: list[str]) -> str:
    """Convert positional parameters ($N) to named parameters (:param).

    Args:
        sql: SQL string with positional parameters ($1, $2, ...).
        param_order: Ordered list of parameter names mapping indices to names.
            Index 0 corresponds to $1, index 1 to $2, etc.

    Returns:
        SQL string with named parameters (:param_name).

    Raises:
        ValueError: If SQL contains a positional index out of bounds of param_order.
    """

    def replace_positional(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index < 1 or index > len(param_order):
            msg = (
                f"Positional parameter ${index} is out of bounds. "
                f"param_order has {len(param_order)} entries (valid: $1-${len(param_order)})."
            )
            # error-ok: standard ValueError for parameter validation in regex callback
            raise ValueError(msg)
        # $1 maps to param_order[0], $2 to param_order[1], etc.
        param_name = param_order[index - 1]
        return f":{param_name}"

    return _POSITIONAL_PARAM_PATTERN.sub(replace_positional, sql)


def migrate_operation(op_data: dict[str, object]) -> dict[str, object]:
    """Migrate a single operation from positional to named parameters.

    Creates a new dict with SQL converted from positional ($1, $2) to named (:param)
    parameters. The param_order field is always removed from the result, regardless
    of whether migration occurred.

    If the SQL contains no positional parameters, the operation is returned as-is
    (minus param_order). Does not mutate the input dict.

    Args:
        op_data: Operation dict with 'sql', 'params', and optionally 'param_order'.

    Returns:
        New operation dict with named params and param_order removed.

    Raises:
        ValueError: If SQL contains positional params but param_order is missing
            or not a list/tuple.
    """
    sql_value = op_data.get("sql", "")
    sql = str(sql_value) if sql_value else ""
    param_order_value = op_data.get("param_order")

    # Check if SQL has positional parameters
    positional_matches = _POSITIONAL_PARAM_PATTERN.findall(sql)
    if not positional_matches:
        # No positional params, return as-is (but remove param_order if present)
        result = dict(op_data)
        result.pop("param_order", None)
        return result

    # Positional params found - need param_order to migrate
    if not param_order_value or not isinstance(param_order_value, (list, tuple)):
        msg = (
            "Operation uses positional parameters but has no param_order. "
            "Cannot migrate without knowing parameter names."
        )
        # error-ok: standard ValueError for missing required field in migration
        raise ValueError(msg)

    # Ensure param_order is list of strings
    param_order: list[str] = [str(p) for p in param_order_value]

    # Convert SQL
    converted_sql = convert_positional_to_named(sql, param_order)

    # Create result without param_order
    result = dict(op_data)
    result["sql"] = converted_sql
    result.pop("param_order", None)

    return result


def migrate_contract(contract_data: dict[str, object]) -> dict[str, object]:
    """Migrate entire contract from positional to named parameters.

    Iterates through all operations in the contract's 'ops' dict and converts
    each from positional to named parameters. Does not mutate the input dict.

    Edge cases:
        - If 'ops' is missing or not a dict, returns contract unchanged.
        - Non-dict operations are preserved as-is (not migrated).
        - Individual operation migration errors propagate (not caught here).

    Args:
        contract_data: Full contract dict with 'ops' containing operations.

    Returns:
        New contract dict with all dict-type operations migrated.
    """
    result = dict(contract_data)
    ops = result.get("ops", {})

    if not isinstance(ops, dict):
        return result

    migrated_ops: dict[str, object] = {}
    for op_name, op_data in ops.items():
        if isinstance(op_data, dict):
            migrated_ops[op_name] = migrate_operation(op_data)
        else:
            migrated_ops[op_name] = op_data

    result["ops"] = migrated_ops
    return result


@click.group()
@click.pass_context
def db(ctx: click.Context) -> None:
    """Database repository contract tools.

    Commands for working with DB repository contracts, including
    migration tools for converting parameter styles.
    """
    ctx.ensure_object(dict)


@db.command(name="migrate-params")
@click.argument(
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Output file path. If not specified, prints to stdout.",
)
@click.option(
    "--in-place",
    "-i",
    is_flag=True,
    default=False,
    help="Modify the input file in place.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be changed without making changes.",
)
@click.pass_context
def migrate_params(
    ctx: click.Context,
    input_file: Path,
    output: Path | None,
    in_place: bool,
    dry_run: bool,
) -> None:
    """Convert positional parameters ($1, $2) to named parameters (:param).

    Reads a DB repository contract YAML file and converts any operations
    using positional parameters to use named parameters instead.

    The param_order field maps positional indices to parameter names:
    - $1 maps to param_order[0]
    - $2 maps to param_order[1]
    - etc.

    After conversion, the param_order field is removed since it's no longer
    needed with named parameters.

    \b
    Examples:
        # Preview changes
        onex db migrate-params contract.yaml --dry-run

        # Output to stdout
        onex db migrate-params contract.yaml

        # Save to new file
        onex db migrate-params contract.yaml -o migrated.yaml

        # Modify in place
        onex db migrate-params contract.yaml --in-place
    """
    if in_place and output:
        raise click.ClickException("Cannot use both --in-place and --output")

    emit_log_event_sync(
        EnumLogLevel.DEBUG,
        "Starting parameter migration",
        {
            "input_file": str(input_file),
            "output": str(output) if output else None,
            "in_place": in_place,
            "dry_run": dry_run,
        },
    )

    try:
        # Read input file
        with input_file.open() as f:
            # yaml-ok: migration tool reads arbitrary YAML to transform, not validate
            contract_data = yaml.safe_load(f)

        if not isinstance(contract_data, dict):
            raise click.ClickException(f"Invalid YAML structure in {input_file}")

        # Check if migration is needed
        ops = contract_data.get("ops", {})
        if not isinstance(ops, dict):
            raise click.ClickException(
                f"Invalid 'ops' structure in {input_file}: expected dict, got {type(ops).__name__}"
            )
        needs_migration = False
        migration_ops: list[str] = []

        for op_name, op_data in ops.items():
            if isinstance(op_data, dict):
                sql_value = op_data.get("sql", "")
                sql = str(sql_value) if sql_value else ""
                if _POSITIONAL_PARAM_PATTERN.search(sql):
                    needs_migration = True
                    migration_ops.append(op_name)

        if not needs_migration:
            click.echo(
                click.style(
                    "No positional parameters found. No migration needed.", fg="green"
                )
            )
            ctx.exit(EnumCLIExitCode.SUCCESS)

        # Report what will be migrated
        click.echo(f"Operations to migrate: {', '.join(migration_ops)}")

        if dry_run:
            click.echo("\n" + click.style("Dry run - no changes made", fg="yellow"))
            for op_name in migration_ops:
                op_data = ops[op_name]
                if not isinstance(op_data, dict):
                    continue
                click.echo(f"\n  Operation: {op_name}")
                before_sql = str(op_data.get("sql", ""))[:80]
                click.echo(f"    Before: {before_sql}...")
                try:
                    migrated = migrate_operation(op_data)
                    after_sql = str(migrated.get("sql", ""))[:80]
                    click.echo(f"    After:  {after_sql}...")
                except ValueError as e:
                    click.echo(click.style(f"    Error: {e}", fg="red"))
            ctx.exit(EnumCLIExitCode.SUCCESS)

        # Validate all operations first before writing any output
        validation_errors: list[tuple[str, str]] = []
        for op_name in migration_ops:
            op_data = ops[op_name]
            if not isinstance(op_data, dict):
                continue
            try:
                migrate_operation(op_data)
            except ValueError as e:
                validation_errors.append((op_name, str(e)))

        if validation_errors:
            click.echo(click.style("\nValidation errors:", fg="red"))
            for op_name, error in validation_errors:
                click.echo(f"  {op_name}: {error}")
            raise click.ClickException(
                f"Cannot migrate: {len(validation_errors)} operation(s) have errors"
            )

        # Perform migration (validation already passed)
        migrated_contract = migrate_contract(contract_data)

        # Generate output YAML
        output_yaml = yaml.dump(
            migrated_contract,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Write output
        if in_place:
            with input_file.open("w") as f:
                f.write(output_yaml)
            click.echo(click.style(f"Migrated {input_file} in place", fg="green"))
        elif output:
            with output.open("w") as f:
                f.write(output_yaml)
            click.echo(click.style(f"Migrated contract saved to {output}", fg="green"))
        else:
            # Print to stdout
            click.echo(output_yaml)

        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Parameter migration completed",
            {"operations_migrated": migration_ops},
        )
        ctx.exit(EnumCLIExitCode.SUCCESS)

    except yaml.YAMLError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "YAML parsing error",
            {"error": str(e), "file": str(input_file)},
        )
        raise click.ClickException(f"YAML parsing error: {e}") from e
    except ValueError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Migration error",
            {"error": str(e), "file": str(input_file)},
        )
        raise click.ClickException(str(e)) from e


__all__ = [
    "db",
    "convert_positional_to_named",
    "migrate_operation",
    "migrate_contract",
]
