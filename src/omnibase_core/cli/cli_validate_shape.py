# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI validation tool for ONEX execution shapes.

Provides the ``onex validate-shape`` subcommand for checking whether a
message-category + target-node-kind combination conforms to the canonical
ONEX execution shapes.

Usage:
    onex validate-shape check --source event --target orchestrator
    onex validate-shape list
    onex validate-shape matrix
"""

from __future__ import annotations

import sys

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_execution_shape import (
    EnumExecutionShape,
    EnumMessageCategory,
)
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.validation.model_execution_shape import ModelExecutionShape
from omnibase_core.models.validation.model_execution_shape_validation import (
    ModelExecutionShapeValidation,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid source and target values for CLI argument parsing
VALID_SOURCES: list[str] = [c.value for c in EnumMessageCategory]
VALID_TARGETS: list[str] = [
    k.value for k in EnumNodeKind if EnumNodeKind.is_core_node_type(k)
]


def _resolve_source(raw: str) -> EnumMessageCategory:
    """Resolve a user-supplied source string to an ``EnumMessageCategory``.

    Matching is case-insensitive.

    Args:
        raw: User-supplied string (e.g. ``"event"``).

    Returns:
        The matching ``EnumMessageCategory``.

    Raises:
        click.BadParameter: If the value does not match any known category.
    """
    normalised = raw.strip().lower()
    for category in EnumMessageCategory:
        if category.value == normalised:
            return category
    raise click.BadParameter(
        f"Unknown source category '{raw}'. Valid values: {', '.join(VALID_SOURCES)}",
        param_hint="'--source'",
    )


def _resolve_target(raw: str) -> EnumNodeKind:
    """Resolve a user-supplied target string to an ``EnumNodeKind``.

    Matching is case-insensitive.  Only core four-node architecture
    types are accepted (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR).

    Args:
        raw: User-supplied string (e.g. ``"orchestrator"``).

    Returns:
        The matching ``EnumNodeKind``.

    Raises:
        click.BadParameter: If the value does not match a core node kind.
    """
    normalised = raw.strip().lower()
    for kind in EnumNodeKind:
        if kind.value == normalised and EnumNodeKind.is_core_node_type(kind):
            return kind
    raise click.BadParameter(
        f"Unknown target node kind '{raw}'. Valid values: {', '.join(VALID_TARGETS)}",
        param_hint="'--target'",
    )


# ---------------------------------------------------------------------------
# Click command group
# ---------------------------------------------------------------------------


@click.group("validate-shape")
def validate_shape() -> None:  # stub-ok
    """Validate execution shapes against ONEX canonical patterns.

    Execution shapes define the valid patterns for message flow between
    node types in the ONEX four-node architecture.  Use this command to
    check whether a proposed source-category / target-node-kind
    combination is architecturally valid.

    \\b
    Canonical shapes:
      EVENT   -> ORCHESTRATOR   (workflow coordination)
      EVENT   -> REDUCER        (state aggregation)
      INTENT  -> EFFECT         (external actions)
      COMMAND -> ORCHESTRATOR   (workflow execution)
      COMMAND -> EFFECT         (direct execution)
    """
    pass  # noqa: PIE790 — Click group; subcommands are registered below


@validate_shape.command()
@click.option(
    "--source",
    "-s",
    required=True,
    type=str,
    help=f"Message category ({', '.join(VALID_SOURCES)}).",
)
@click.option(
    "--target",
    "-t",
    required=True,
    type=str,
    help=f"Target node kind ({', '.join(VALID_TARGETS)}).",
)
def check(source: str, target: str) -> None:
    """Check if a source/target combination is a valid execution shape.

    \\b
    Examples:
        onex validate-shape check --source event --target orchestrator
        onex validate-shape check -s command -t reducer
    """
    source_category = _resolve_source(source)
    target_kind = _resolve_target(target)

    result = ModelExecutionShapeValidation.validate_shape(
        source_category=source_category,
        target_node_kind=target_kind,
    )

    if result.is_allowed:
        click.echo(
            click.style("ALLOWED", fg="green")
            + f"  {source_category.value} -> {target_kind.value}"
        )
        click.echo(
            f"  Shape: {result.matched_shape.value if result.matched_shape else 'N/A'}"
        )
        click.echo(f"  {result.rationale}")
        sys.exit(EnumCLIExitCode.SUCCESS.value)

    click.echo(
        click.style("FORBIDDEN", fg="red")
        + f"  {source_category.value} -> {target_kind.value}"
    )
    click.echo(f"  {result.rationale}")

    # Suggest valid shapes for the given source category
    valid_for_source = EnumExecutionShape.get_shapes_for_category(source_category)
    if valid_for_source:
        click.echo("\n  Valid targets for this source category:")
        for shape in valid_for_source:
            target_str = EnumExecutionShape.get_target_node_kind(shape)
            click.echo(
                f"    - {source_category.value} -> {target_str}  ({shape.value})"
            )

    # Suggest valid shapes for the given target kind
    valid_for_target = EnumExecutionShape.get_shapes_for_target(target_kind.value)
    if valid_for_target:
        click.echo(f"\n  Valid sources for {target_kind.value} nodes:")
        for shape in valid_for_target:
            src_cat = EnumExecutionShape.get_source_category(shape)
            click.echo(f"    - {src_cat.value} -> {target_kind.value}  ({shape.value})")

    sys.exit(EnumCLIExitCode.ERROR.value)


@validate_shape.command("list")
def list_shapes() -> None:
    """List all canonical execution shapes.

    \\b
    Example:
        onex validate-shape list
    """
    shapes = ModelExecutionShape.get_all_shapes()
    click.echo("Canonical ONEX Execution Shapes")
    click.echo("=" * 50)
    for shape_model in shapes:
        click.echo(
            f"  {shape_model.source_category.value:>8} -> {shape_model.target_node_kind.value:<14}"
            f"  {shape_model.shape.value}"
        )
        if shape_model.description:
            click.echo(f"{'':>28}{shape_model.description}")
    click.echo(f"\nTotal: {len(shapes)} canonical shapes")


@validate_shape.command()
def matrix() -> None:
    """Display a full compatibility matrix of source/target combinations.

    \\b
    Example:
        onex validate-shape matrix
    """
    categories = list(EnumMessageCategory)
    node_kinds = [k for k in EnumNodeKind if EnumNodeKind.is_core_node_type(k)]

    # Header
    header_cells = [f"{k.value:>14}" for k in node_kinds]
    click.echo(f"{'':>10} " + " ".join(header_cells))
    click.echo("-" * (11 + 15 * len(node_kinds)))

    for category in categories:
        row_cells: list[str] = []
        for kind in node_kinds:
            result = ModelExecutionShapeValidation.validate_shape(
                source_category=category,
                target_node_kind=kind,
            )
            if result.is_allowed:
                cell = click.style("ALLOWED", fg="green")
                # Pad to 14 chars (ALLOWED is 7 chars, need 7 more padding)
                cell += " " * 7
            else:
                cell = click.style("---", fg="red")
                cell += " " * 11
            row_cells.append(cell)
        click.echo(f"{category.value:>10} " + " ".join(row_cells))

    click.echo()
    click.echo(
        "Legend: "
        + click.style("ALLOWED", fg="green")
        + " = canonical shape, "
        + click.style("---", fg="red")
        + " = forbidden pattern"
    )
