"""
Composition Report CLI Command.

Provides a CLI command to generate composition analysis reports from
execution manifests. The report explains what ran and why during a
pipeline execution.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import json
from pathlib import Path
from typing import Literal, assert_never, cast

import click
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.pipeline.manifest_logger import ManifestLogger

OutputFormat = Literal["json", "yaml", "markdown", "text"]


def _format_text_report(
    manifest: ModelExecutionManifest,
    verbose: bool = False,
    show_predicates: bool = False,
    show_timing: bool = False,
) -> str:
    """
    Format a human-readable text report.

    Args:
        manifest: The manifest to format
        verbose: Include detailed traces
        show_predicates: Show predicate evaluations
        show_timing: Show timing breakdown

    Returns:
        Formatted text report
    """
    lines = [
        "=" * 70,
        "COMPOSITION REPORT",
        "=" * 70,
        "",
        f"Manifest ID:  {manifest.manifest_id}",
        f"Status:       {'SUCCESS' if manifest.is_successful() else 'FAILED'}",
        f"Duration:     {manifest.get_total_duration_ms():.1f}ms",
        "",
        "-" * 70,
        "NODE IDENTITY",
        "-" * 70,
        f"  ID:         {manifest.node_identity.node_id}",
        f"  Kind:       {manifest.node_identity.node_kind.value}",
        f"  Version:    {manifest.node_identity.get_version_string()}",
    ]

    if manifest.node_identity.namespace:
        lines.append(f"  Namespace:  {manifest.node_identity.namespace}")

    lines.extend(
        [
            "",
            "-" * 70,
            "CONTRACT IDENTITY",
            "-" * 70,
            f"  ID:         {manifest.contract_identity.contract_id}",
        ]
    )

    if manifest.contract_identity.contract_path:
        lines.append(f"  Path:       {manifest.contract_identity.contract_path}")
    if manifest.contract_identity.profile_name:
        lines.append(f"  Profile:    {manifest.contract_identity.profile_name}")

    # Activation Summary
    activation = manifest.activation_summary
    if activation.total_evaluated > 0:
        lines.extend(
            [
                "",
                "-" * 70,
                "CAPABILITY ACTIVATION",
                "-" * 70,
                f"  Activated:  {activation.get_activated_count()}",
                f"  Skipped:    {activation.get_skipped_count()}",
                f"  Total:      {activation.total_evaluated}",
                "",
            ]
        )

        if activation.activated_capabilities:
            lines.append("  Activated Capabilities:")
            for cap in activation.activated_capabilities:
                reason_str = f" ({cap.reason.value})" if verbose else ""
                lines.append(f"    - {cap.capability_name}{reason_str}")
                if show_predicates and cap.predicate_expression:
                    lines.append(f"      Predicate: {cap.predicate_expression}")
                    lines.append(f"      Result:    {cap.predicate_result}")

        if verbose and activation.skipped_capabilities:
            lines.append("")
            lines.append("  Skipped Capabilities:")
            for cap in activation.skipped_capabilities:
                lines.append(f"    - {cap.capability_name} ({cap.reason.value})")

    # Ordering Summary
    ordering = manifest.ordering_summary
    if ordering.resolved_order:
        lines.extend(
            [
                "",
                "-" * 70,
                "EXECUTION ORDER",
                "-" * 70,
                f"  Policy:     {ordering.ordering_policy or 'default'}",
                "",
                "  Handler Order:",
            ]
        )
        for i, handler_id in enumerate(ordering.resolved_order, 1):
            lines.append(f"    {i}. {handler_id}")

    # Hook Traces
    if manifest.hook_traces:
        lines.extend(
            [
                "",
                "-" * 70,
                "EXECUTION TRACE",
                "-" * 70,
                f"  Hooks Executed: {manifest.get_hook_count()}",
                "",
            ]
        )

        if verbose or show_timing:
            for trace in manifest.hook_traces:
                status_icon = (
                    "[OK]"
                    if trace.is_success()
                    else "[FAIL]"
                    if trace.is_failure()
                    else "[SKIP]"
                )
                timing = f" ({trace.duration_ms:.1f}ms)" if show_timing else ""
                lines.append(
                    f"    {status_icon} {trace.handler_id} @ {trace.phase.value}{timing}"
                )
                if trace.has_error():
                    lines.append(f"         Error: {trace.error_message}")

    # Emissions
    emissions = manifest.emissions_summary
    if not emissions.is_empty():
        lines.extend(
            [
                "",
                "-" * 70,
                "EMISSIONS",
                "-" * 70,
            ]
        )
        if emissions.has_events():
            types_str = ", ".join(emissions.event_types)
            lines.append(f"  Events:      {emissions.events_count} ({types_str})")
        if emissions.has_intents():
            types_str = ", ".join(emissions.intent_types)
            lines.append(f"  Intents:     {emissions.intents_count} ({types_str})")
        if emissions.has_projections():
            lines.append(f"  Projections: {emissions.projections_count}")
        if emissions.has_actions():
            lines.append(f"  Actions:     {emissions.actions_count}")

    # Failures
    if manifest.has_failures():
        lines.extend(
            [
                "",
                "-" * 70,
                "FAILURES",
                "-" * 70,
            ]
        )
        for failure in manifest.failures:
            lines.append(f"  [{failure.error_code}] {failure.error_message}")
            if failure.handler_id:
                lines.append(f"    Handler: {failure.handler_id}")
            if failure.phase:
                lines.append(f"    Phase:   {failure.phase.value}")

    lines.extend(
        [
            "",
            "=" * 70,
        ]
    )

    return "\n".join(lines)


@click.command("composition-report")
@click.argument(
    "manifest_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "yaml", "markdown", "text"]),
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
    "--verbose",
    "-v",
    is_flag=True,
    help="Include detailed traces and skip reasons",
)
@click.option(
    "--show-predicates",
    is_flag=True,
    help="Show predicate expressions and evaluation results",
)
@click.option(
    "--show-timing",
    is_flag=True,
    help="Show timing breakdown for each hook",
)
@click.pass_context
def composition_report(
    ctx: click.Context,
    manifest_path: Path,
    output_format: str,
    output: Path | None,
    verbose: bool,
    show_predicates: bool,
    show_timing: bool,
) -> None:
    """Generate a composition analysis report from an execution manifest.

    Reads a manifest JSON file and produces a human-readable report
    explaining what ran and why during the pipeline execution.

    \b
    Examples:
        onex composition-report manifest.json
        onex composition-report manifest.json --format markdown -o report.md
        onex composition-report manifest.json --verbose --show-predicates
        onex composition-report manifest.json --show-timing
    """
    # Inherit verbose from parent context if not explicitly set
    verbose = verbose or (ctx.obj.get("verbose", False) if ctx.obj else False)

    try:
        # Load manifest
        manifest_data = json.loads(manifest_path.read_text())
        manifest = ModelExecutionManifest.model_validate(manifest_data)

        # Format output - cast to OutputFormat for exhaustiveness checking
        # Click's Choice validator guarantees output_format is one of the valid values
        format_typed: OutputFormat = cast(OutputFormat, output_format)
        result: str
        match format_typed:
            case "json":
                result = ManifestLogger.to_json(manifest)
            case "yaml":
                result = ManifestLogger.to_yaml(manifest)
            case "markdown":
                result = ManifestLogger.to_markdown(manifest, verbose=verbose)
            case "text":
                result = _format_text_report(
                    manifest,
                    verbose=verbose,
                    show_predicates=show_predicates,
                    show_timing=show_timing,
                )
            case _ as unreachable:
                # This case is unreachable due to Click's Choice validator
                # and the Literal type. assert_never ensures compile-time
                # exhaustiveness checking - if a new format is added to
                # OutputFormat, mypy will error here until it's handled.
                assert_never(unreachable)

        # Output
        if output:
            output.write_text(result)
            click.echo(f"Report written to {output}")
        else:
            click.echo(result)

        # Success - no need to call ctx.exit(), just return

    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in manifest file: {e}") from e
    except ValidationError as e:
        # Pydantic validation failed - manifest structure is invalid
        raise click.ClickException(f"Invalid manifest structure: {e}") from e
    except ModelOnexError as e:
        # ONEX-specific errors (e.g., missing PyYAML for YAML output)
        raise click.ClickException(str(e)) from e
    except OSError as e:
        # File I/O errors (read or write)
        raise click.ClickException(f"File I/O error: {e}") from e


# Export for use
__all__ = ["composition_report"]
