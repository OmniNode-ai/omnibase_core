# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command for scaffolding new channel adapter contract packages."""

from __future__ import annotations

from pathlib import Path

import click


def _get_template_dir() -> Path:
    """Return the path to the channel_adapter template directory."""
    return Path(__file__).parent / "templates" / "channel_adapter"


def _render_templates(
    platform: str,
    library: str,
    output_dir: Path,
) -> Path:
    """Render channel adapter templates into the output directory.

    Returns:
        The path to the generated package directory.
    """
    from jinja2 import Environment, FileSystemLoader

    template_dir = _get_template_dir()
    env = Environment(  # noqa: S701  # code-gen templates, not HTML
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )

    platform_lower = platform.lower()
    platform_cap = platform.capitalize()
    node_dir_name = f"node_channel_{platform_lower}_adapter"
    pkg_dir = output_dir / node_dir_name

    context = {
        "platform": platform_lower,
        "Platform": platform_cap,
        "library": library,
        "node_dir_name": node_dir_name,
    }

    # Create directory structure
    handlers_dir = pkg_dir / "handlers"
    tests_dir = pkg_dir / "tests"
    handlers_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Template -> output path mapping
    file_map = {
        "contract.yaml.j2": pkg_dir / "contract.yaml",
        "node.py.j2": pkg_dir / "node.py",
        "__init__.py.j2": pkg_dir / "__init__.py",
        "handler_inbound.py.j2": handlers_dir / "handler_inbound.py",
        "handler_outbound.py.j2": handlers_dir / "handler_outbound.py",
        "test_handler_inbound.py.j2": tests_dir / "test_handler_inbound.py",
    }

    # Also create handlers __init__.py
    (handlers_dir / "__init__.py").write_text(
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
    )

    for template_name, output_path in file_map.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)
        output_path.write_text(rendered)

    return pkg_dir


@click.command("scaffold-channel-adapter")
@click.option(
    "--platform",
    required=True,
    help="Platform name (e.g., signal, whatsapp, matrix).",
)
@click.option(
    "--library",
    required=True,
    help="Python library to wrap (e.g., signalbot).",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".",
    help="Output directory for generated package.",
)
def cli_scaffold_channel_adapter(
    platform: str,
    library: str,
    output_dir: str,
) -> None:
    """Generate a new channel adapter contract package from templates.

    Creates a complete ONEX contract package skeleton for a new
    channel adapter, including contract.yaml, node shell, and handlers.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pkg_dir = _render_templates(platform, library, output_path)

    click.echo(f"Scaffolded channel adapter: {pkg_dir}")
    click.echo(f"  Platform: {platform}")
    click.echo(f"  Library: {library}")
    click.echo(f"  Contract: {pkg_dir / 'contract.yaml'}")
    click.echo(f"  Handler inbound: {pkg_dir / 'handlers' / 'handler_inbound.py'}")
    click.echo(f"  Handler outbound: {pkg_dir / 'handlers' / 'handler_outbound.py'}")
    click.echo(f"  Test: {pkg_dir / 'tests' / 'test_handler_inbound.py'}")
