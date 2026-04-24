# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command for packing ONEX nodes into .oncp contract package archives."""

from __future__ import annotations

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path

import click

# NOTE(OMN-7537): metadata.yaml and contract.yaml are external contract files
# with varying schemas across node types. Pydantic models would require a
# separate model per node type. yaml.safe_load is the correct approach here
# for reading untrusted third-party contract files.
# spdx-skip: manual YAML validation for external contract files


def _get_registry_dir() -> Path:
    """Return the local ONEX registry directory."""
    return Path.home() / ".omnibase" / "registry"


def _compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_metadata(metadata_path: Path) -> dict[str, object]:
    """Validate metadata.yaml and return parsed contents."""
    import yaml

    if not metadata_path.exists():
        raise click.ClickException(f"metadata.yaml not found at {metadata_path}")

    with open(metadata_path) as f:
        metadata = yaml.safe_load(f)

    if not isinstance(metadata, dict):
        raise click.ClickException("metadata.yaml is not a valid YAML mapping")

    required = ["name", "version", "entry_points"]
    for field in required:
        if field not in metadata:
            raise click.ClickException(f"metadata.yaml missing required field: {field}")

    return metadata


def _validate_contract(contract_path: Path) -> dict[str, object]:
    """Validate contract.yaml and return parsed contents."""
    import yaml

    if not contract_path.exists():
        raise click.ClickException(f"contract.yaml not found at {contract_path}")

    with open(contract_path) as f:
        contract = yaml.safe_load(f)

    if not isinstance(contract, dict):
        raise click.ClickException("contract.yaml is not a valid YAML mapping")

    # Contract uses 'name' + 'contract_version' or 'node_version' (not bare 'version')
    if "name" not in contract:
        raise click.ClickException("contract.yaml missing required field: name")

    has_version = (
        "contract_version" in contract
        or "node_version" in contract
        or "version" in contract
    )
    if not has_version:
        raise click.ClickException(
            "contract.yaml missing version field (contract_version, node_version, or version)"
        )

    return contract


def _check_handlers(node_dir: Path, contract: dict[str, object]) -> list[str]:
    """Verify all handlers declared in contract.yaml exist on disk."""
    handlers_dir = node_dir / "handlers"
    declared_handlers: list[str] = []

    # Contract may declare handlers in two formats:
    # 1. Singular: handler: { module: ..., class: ... }
    # 2. Plural: handlers: { handler_name: { file: ..., class: ... } }
    handler_section = contract.get("handler")
    handlers_section = contract.get("handlers", {})

    # Check singular handler format
    if isinstance(handler_section, dict):
        handler_module = handler_section.get("module", "")
        if handler_module:
            # Convert module path to file path
            handler_file = handler_module.split(".")[-1] + ".py"
            handler_path = handlers_dir / handler_file
            if not handler_path.exists():
                raise click.ClickException(
                    f"Handler module '{handler_module}' declared in contract "
                    f"but file not found at {handler_path}"
                )
            declared_handlers.append(handler_file)

    # Check plural handlers format
    if isinstance(handlers_section, dict):
        for handler_name, handler_config in handlers_section.items():
            if isinstance(handler_config, dict):
                handler_file = handler_config.get("file")
                if handler_file:
                    declared_handlers.append(handler_file)
                    handler_path = handlers_dir / handler_file
                    if not handler_path.exists():
                        raise click.ClickException(
                            f"Handler file '{handler_file}' declared in contract "
                            f"but not found at {handler_path}"
                        )

    return declared_handlers


def _check_tests(node_dir: Path) -> bool:
    """Check if tests directory exists and has test files."""
    tests_dir = node_dir / "tests"
    if not tests_dir.exists():
        return False
    return any(tests_dir.glob("test_*.py"))


@click.command("pack")
@click.argument(
    "node_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for .oncp archive (default: <name>-<version>.oncp in cwd).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate only, do not produce archive.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation output.",
)
def cli_pack(
    node_dir: Path,
    output: Path | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Pack an ONEX node into a .oncp contract package archive.

    Validates metadata.yaml, contract.yaml, handler existence, and test
    existence, then produces a .oncp tar.gz archive.

    \b
    Examples:
        onex pack src/omnimarket/nodes/node_aislop_sweep/
        onex pack src/omnimarket/nodes/node_aislop_sweep/ -o my-package.oncp
        onex pack src/omnimarket/nodes/node_aislop_sweep/ --dry-run
    """
    node_dir = node_dir.resolve()

    # Step 1: Validate metadata.yaml
    metadata_path = node_dir / "metadata.yaml"
    metadata = _validate_metadata(metadata_path)
    if verbose:
        click.echo(f"  [PASS] metadata.yaml: {metadata['name']} v{metadata['version']}")

    # Step 2: Validate contract.yaml
    contract_path = node_dir / "contract.yaml"
    contract = _validate_contract(contract_path)
    contract_version = (
        contract.get("contract_version")
        or contract.get("node_version")
        or contract.get("version", "?")
    )
    if isinstance(contract_version, dict):
        contract_version = f"{contract_version.get('major', '?')}.{contract_version.get('minor', '?')}.{contract_version.get('patch', '?')}"
    if verbose:
        click.echo(f"  [PASS] contract.yaml: {contract['name']} v{contract_version}")

    # Step 3: Check handlers exist
    handlers = _check_handlers(node_dir, contract)
    if verbose:
        if handlers:
            click.echo(
                f"  [PASS] {len(handlers)} handler(s) found: {', '.join(handlers)}"
            )
        else:
            click.echo("  [PASS] No handlers declared in contract")

    # Step 4: Check tests exist (warning only, not a hard block)
    has_tests = _check_tests(node_dir)
    if verbose:
        if has_tests:
            click.echo("  [PASS] tests/ directory with test files found")
        else:
            click.echo("  [WARN] No tests/ directory or test files found")

    # Step 5: Compute archive hash for provenance
    archive_hash = _compute_sha256(metadata_path)

    if dry_run:
        click.echo(f"\nDry run complete for {metadata['name']} v{metadata['version']}")
        click.echo(f"  Node directory: {node_dir}")
        click.echo(f"  Handlers: {len(handlers)}")
        click.echo(f"  Tests: {'yes' if has_tests else 'no'}")
        click.echo(f"  Archive hash (metadata): {archive_hash[:16]}...")
        return

    # Step 6: Build .oncp archive
    package_name = metadata["name"]
    package_version = metadata["version"]
    archive_name = output or Path(f"{package_name}-{package_version}.oncp")

    # Create tar.gz with node directory contents
    with tarfile.open(archive_name, "w:gz") as tar:
        # Add metadata.yaml
        tar.add(metadata_path, arcname="metadata.yaml")

        # Add contract.yaml
        tar.add(contract_path, arcname="contract.yaml")

        # Add all node files (handlers, tests, __init__.py, etc.)
        for item in node_dir.iterdir():
            if item.name in ("metadata.yaml", "contract.yaml"):
                continue  # Already added
            arcname = f"{package_name}/{item.name}"
            tar.add(item, arcname=arcname)

        # Add provenance manifest
        provenance = {
            "package_name": package_name,
            "package_version": package_version,
            "archive_sha256": archive_hash,
            "packed_from": str(node_dir),
        }
        provenance_bytes = json.dumps(provenance, indent=2).encode("utf-8")
        info = tarfile.TarInfo(name="provenance.json")
        info.size = len(provenance_bytes)
        tar.addfile(info, BytesIO(provenance_bytes))

    archive_size = archive_name.stat().st_size
    click.echo(
        f"Packed {package_name} v{package_version} -> {archive_name} ({archive_size:,} bytes)"
    )
