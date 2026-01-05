# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Management CLI Commands.

Provides CLI commands for comparing, validating, and managing ONEX contracts.
The main entry point is the `contract` command group with subcommands for
various contract operations.

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering (OMN-1149)

Example:
    Compare two contract files::

        onex contract diff v1.yaml v2.yaml
        onex contract diff old.json new.json --format markdown
        onex contract diff a.yaml b.yaml -o diff_report.html -f html
"""

import json
from pathlib import Path
from typing import Literal, cast

import click
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.models.cli.model_output_format_options import (
    ModelOutputFormatOptions,
)
from omnibase_core.models.contracts.diff.model_contract_diff import ModelContractDiff

# Supported output formats for the diff command
OutputFormat = Literal["text", "json", "markdown", "html"]


# extra="allow" inherently uses Any for extra fields - this is intentional
# for CLI processing of arbitrary contract schemas
class _ContractWrapper(BaseModel):  # type: ignore[explicit-any]
    """Wrapper model for contract dict data in CLI diff operations.

    This model wraps arbitrary contract dictionaries loaded from YAML/JSON
    files for comparison. Uses extra="allow" to accept any contract schema.
    """

    model_config = ConfigDict(extra="allow")

    # Store the original name for display
    name: str | None = None


# Map CLI format strings to EnumOutputFormat
FORMAT_MAP: dict[str, EnumOutputFormat] = {
    "text": EnumOutputFormat.TEXT,
    "json": EnumOutputFormat.JSON,
    "markdown": EnumOutputFormat.MARKDOWN,
    # HTML is handled specially via render_html()
}


def _load_contract(path: Path) -> dict[str, object]:
    """Load contract data from YAML or JSON file.

    Attempts to parse the file based on extension, with fallback detection
    for files without standard extensions.

    Args:
        path: Path to the contract file.

    Returns:
        Parsed contract data as a dictionary.

    Raises:
        click.ClickException: If the file cannot be parsed or YAML support
            is not available for YAML files.
    """
    content = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            yaml_result: dict[str, object] = yaml.safe_load(
                content
            )  # yaml-ok: loading arbitrary contract schemas from user files
            return yaml_result
        except ImportError as e:
            msg = "PyYAML is required for YAML files. Install with: poetry add pyyaml"
            raise click.ClickException(msg) from e
    elif path.suffix == ".json":
        json_result: dict[str, object] = json.loads(content)
        return json_result
    else:
        # Try JSON first, then YAML for unknown extensions
        try:
            fallback_json: dict[str, object] = json.loads(content)
            return fallback_json
        except json.JSONDecodeError:
            try:
                import yaml

                fallback_yaml: dict[str, object] = yaml.safe_load(
                    content
                )  # yaml-ok: loading arbitrary contract schemas from user files
                return fallback_yaml
            except ImportError as e:
                msg = "Could not parse file as JSON. Install PyYAML for YAML support: poetry add pyyaml"
                raise click.ClickException(msg) from e


def _render_diff(
    diff: ModelContractDiff,
    output_format: OutputFormat,
    no_color: bool,
) -> str:
    """Render the diff in the requested format.

    Args:
        diff: The ModelContractDiff result.
        output_format: The target output format.
        no_color: If True, disable ANSI color codes for text output.

    Returns:
        Rendered diff as a string.
    """
    from omnibase_core.rendering.renderer_diff import RendererDiff

    # Create format options
    options = ModelOutputFormatOptions(
        color_enabled=not no_color,
        pretty_print=True,
        sort_keys=False,
    )

    # HTML needs special handling via dedicated method
    if output_format == "html":
        return RendererDiff.render_html(diff, options=options, standalone=True)

    # Other formats go through the main render() method
    enum_format = FORMAT_MAP[output_format]
    return RendererDiff.render(diff, enum_format, options=options)


@click.group("contract")
@click.pass_context
def contract(ctx: click.Context) -> None:
    """Contract management commands.

    Commands for comparing, validating, and managing ONEX contracts.
    Use the subcommands below to perform specific operations.

    \b
    Available commands:
        diff    Compare two contract files and show differences
    """
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@contract.command("diff")
@click.argument("before", type=click.Path(exists=True, path_type=Path))
@click.argument("after", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "markdown", "html"]),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Write output to file instead of stdout",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable colored output for text format",
)
@click.pass_context
def diff(
    ctx: click.Context,
    before: Path,
    after: Path,
    output_format: str,
    output: Path | None,
    no_color: bool,
) -> None:
    """Compare two contract files and show differences.

    BEFORE and AFTER are paths to contract YAML or JSON files.
    The command computes a semantic diff showing added, removed,
    modified, and moved fields between the two versions.

    \b
    Supported file formats:
        - YAML (.yaml, .yml)
        - JSON (.json)
        - Auto-detect for other extensions

    \b
    Examples:
        onex contract diff v1.yaml v2.yaml

        onex contract diff old.json new.json --format markdown

        onex contract diff a.yaml b.yaml -o diff_report.html -f html

        onex contract diff before.yaml after.yaml --no-color
    """
    # Inherit verbose from parent context if available
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    try:
        # Load both contracts
        before_data = _load_contract(before)
        after_data = _load_contract(after)

        # Import diff computer lazily to avoid circular imports
        from omnibase_core.contracts.diff_computer import compute_contract_diff

        # Create wrapper instances with contract names from file paths
        before_model = _ContractWrapper.model_validate(
            {"name": before.stem, **before_data}
        )
        after_model = _ContractWrapper.model_validate(
            {"name": after.stem, **after_data}
        )

        # Compute the diff
        diff_result = compute_contract_diff(before_model, after_model)

        # Render in requested format
        format_typed: OutputFormat = cast(OutputFormat, output_format)
        rendered = _render_diff(diff_result, format_typed, no_color)

        # Output to file or stdout
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
            click.echo(f"Diff written to {output}")
        else:
            click.echo(rendered)

        # Success - return normally (exit code 0)
        return

    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e.filename}") from e
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON: {e}") from e
    except click.ClickException:
        # Re-raise ClickExceptions as-is
        raise
    except (
        Exception
    ) as e:  # catch-all-ok: CLI boundary handler for user-friendly errors
        # Catches unexpected errors in diff computation
        # Examples: ValidationError (malformed contract), OSError (file access),
        # RuntimeError (diff algorithm bugs), ImportError (missing dependencies)
        raise click.ClickException(f"Error computing diff: {e}") from e


# Export for use
__all__ = ["contract", "diff"]
