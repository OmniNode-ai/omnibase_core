# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command for assisted porting of OpenClaw skill packages to ONEX contract packages."""

from __future__ import annotations

from pathlib import Path

import click

from omnibase_core.cli.openclaw_analyzer import analyze_openclaw_package


@click.command("port-openclaw")
@click.argument("package_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".",
    help="Output directory for generated package.",
)
@click.option(
    "--analyze-only",
    is_flag=True,
    help="Phase A only: analyze and report, do not generate.",
)
def cli_port_openclaw(
    package_dir: str,
    output: str,
    analyze_only: bool,
) -> None:
    """Assisted porting of OpenClaw skill packages to ONEX contract packages.

    Analyzes an npm skill package, detects capabilities, classifies security
    tier, and optionally generates an ONEX contract package skeleton.
    """
    analysis = analyze_openclaw_package(Path(package_dir))

    click.echo(f"Analyzed: {analysis.name} v{analysis.version}")
    click.echo(f"  Description: {analysis.description}")
    click.echo(f"  Capabilities: {len(analysis.capabilities)}")
    click.echo(f"  Security tier: {analysis.security_tier}")
    click.echo(f"  Confidence level: {analysis.confidence_level}")
    click.echo(f"  Env vars: {', '.join(analysis.env_vars) or 'none'}")
    click.echo(f"  npm dependencies: {len(analysis.npm_dependencies)}")

    if analyze_only:
        if analysis.capabilities:
            click.echo("\nDetected capabilities:")
            for cap in analysis.capabilities:
                click.echo(
                    f"  [{cap.security_tier}] {cap.category}: {cap.details} "
                    f"({cap.source_file}:{cap.source_line})"
                )
        else:
            click.echo("\nNo capabilities detected (pure compute skill).")
        return

    if analysis.confidence_level == "blocked":
        click.echo(
            "\nBLOCKED: This skill cannot be automatically ported. "
            "Manual porting required."
        )
        raise click.ClickException(
            "This skill cannot be automatically ported. Manual porting required."
        )

    # Phase B: scaffold generation
    from omnibase_core.cli.openclaw_scaffold import generate_contract_package

    pkg_dir = generate_contract_package(analysis, Path(output))
    click.echo(f"\nGenerated: {pkg_dir}")

    contract_path = next(pkg_dir.rglob("contract.yaml"), None)
    if contract_path:
        click.echo(f"  Contract: {contract_path}")

    click.echo(f"  Confidence: {analysis.confidence_level}")

    if analysis.confidence_level == "requires_manual_review":
        click.echo(
            "  WARNING: This skill requires manual review before use. "
            "Check TODO markers in handler."
        )

    click.echo(f"\nTo install: onex install {pkg_dir}")
