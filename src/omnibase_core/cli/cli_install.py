# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command for installing ONEX contract packages with validation."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import click


def _in_virtualenv() -> bool:
    """Check if running inside a virtual environment."""
    return sys.prefix != sys.base_prefix


def _get_registry_path() -> Path:
    """Return the path to the local installed nodes registry."""
    return Path.home() / ".omnibase" / "installed_nodes.json"


def _load_registry() -> dict[str, dict[str, str]]:
    """Load the installed nodes registry from disk."""
    path = _get_registry_path()
    if path.exists():
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    return {}


def _save_registry(registry: dict[str, dict[str, str]]) -> None:
    """Save the installed nodes registry to disk."""
    path = _get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2))


def _rollback_install(package_name: str) -> None:
    """Uninstall a package after failed validation."""
    click.echo(f"Rolling back: uninstalling {package_name}", err=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
        capture_output=True,
        check=False,
    )


def from_yaml_contract(contract_path: Path) -> object:
    """Load and parse a contract.yaml file.

    Uses yaml.safe_load for parsing untrusted third-party contract files.
    This is intentional — third-party contracts are not internal Pydantic models.
    """
    import yaml

    with open(contract_path) as f:
        return yaml.safe_load(f)


def _validate_contract(contract_path: Path) -> dict[str, object]:
    """Validate a contract.yaml file and return its contents.

    Raises:
        click.ClickException: If the contract is missing required fields.
    """
    try:
        raw = from_yaml_contract(contract_path)
    except Exception as e:
        msg = f"contract.yaml at {contract_path} is not valid: {e}"
        raise click.ClickException(msg) from e

    if not isinstance(raw, dict):
        msg = f"contract.yaml at {contract_path} is not a valid YAML mapping"
        raise click.ClickException(msg)

    contract: dict[str, object] = raw

    required_fields = ["name", "version"]
    for field in required_fields:
        if field not in contract:
            msg = f"contract.yaml missing required field: {field}"
            raise click.ClickException(msg)

    # Validate topic format if event_bus_enabled
    if contract.get("event_bus_enabled"):
        for topic_key in ("publish_topics", "subscribe_topics"):
            topics = contract.get(topic_key, [])
            if isinstance(topics, list):
                for topic in topics:
                    if isinstance(topic, str) and not topic.startswith("onex."):
                        msg = f"Invalid topic format in {topic_key}: {topic} (must start with 'onex.')"
                        raise click.ClickException(msg)

    return contract


@click.command("install")
@click.argument("package_name")
@click.option(
    "--test/--no-test",
    default=False,
    help="Run golden chain test after install (default: off for untrusted packages).",
)
@click.option("--dry-run", is_flag=True, help="Analyze package without installing.")
@click.option(
    "--upgrade",
    is_flag=True,
    help="Allow upgrading existing registered packages.",
)
@click.option(
    "--allow-unsigned",
    is_flag=True,
    help="Allow packages without onex-signature metadata.",
)
def cli_install(
    package_name: str,
    test: bool,
    dry_run: bool,
    upgrade: bool,
    allow_unsigned: bool,
) -> None:
    """Install an ONEX contract package with validation.

    Wraps pip install with contract.yaml validation, provenance checks,
    and local registry tracking. Rolls back on validation failure.
    """
    if not _in_virtualenv():
        raise click.ClickException(
            "onex install must be run inside a virtual environment"
        )

    # Step 1: pip install (skip for dry-run)
    if not dry_run:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise click.ClickException(f"pip install failed: {result.stderr.strip()}")
        click.echo(f"Installed {package_name}")

    # Step 2: Discover entry points
    eps = importlib.metadata.entry_points(group="onex.nodes")
    # Normalize package name for comparison (PEP 503)
    normalized = package_name.replace("-", "_").replace(".", "_").lower()
    matching = [
        ep
        for ep in eps
        if ep.dist
        and ep.dist.name.replace("-", "_").replace(".", "_").lower() == normalized
    ]

    if not matching:
        click.echo(f"Warning: {package_name} has no onex.nodes entry points", err=True)
        if not dry_run:
            return

    # Step 3: Validate contract.yaml for each discovered node
    validated_contracts: list[dict[str, object]] = []
    for ep in matching:
        try:
            module = importlib.import_module(ep.module)
        except ImportError as e:
            if not dry_run:
                _rollback_install(package_name)
            raise click.ClickException(f"Cannot import module {ep.module}: {e}") from e

        if module.__file__ is None:
            if not dry_run:
                _rollback_install(package_name)
            raise click.ClickException(f"Module {ep.module} has no __file__ attribute")

        contract_path = Path(module.__file__).parent / "contract.yaml"
        if not contract_path.exists():
            if not dry_run:
                _rollback_install(package_name)
            raise click.ClickException(f"Missing contract.yaml in {ep.module}")

        try:
            contract = _validate_contract(contract_path)
        except click.ClickException:
            if not dry_run:
                _rollback_install(package_name)
            raise

        validated_contracts.append(contract)
        click.echo(
            f"Validated: {contract.get('name', 'unknown')} "
            f"v{contract.get('version', '?')}"
        )

    # Step 4: Check provenance / signature
    if not dry_run and matching:
        try:
            dist = matching[0].dist
            if dist is not None:
                metadata = dist.metadata
                has_signature = metadata.get("onex-signature") is not None
                if not has_signature and not allow_unsigned:
                    _rollback_install(package_name)
                    raise click.ClickException(
                        f"{package_name} has no onex-signature metadata. "
                        "Use --allow-unsigned to install anyway."
                    )
                if not has_signature:
                    click.echo(f"Warning: {package_name} is unsigned", err=True)
        except click.ClickException:
            raise
        except Exception:  # noqa: BLE001
            click.echo("Warning: could not check package signature", err=True)

    if dry_run:
        click.echo(f"\nDry run complete for {package_name}")
        for contract in validated_contracts:
            click.echo(f"  Node: {contract.get('name', 'unknown')}")
        return

    # Step 5: Check version conflicts and register
    registry = _load_registry()
    for contract in validated_contracts:
        contract_name = str(contract.get("name", ""))
        if contract_name in registry and not upgrade:
            _rollback_install(package_name)
            raise click.ClickException(
                f"Node '{contract_name}' is already registered. "
                "Use --upgrade to replace."
            )
        registry[contract_name] = {
            "package": package_name,
            "version": str(contract.get("version", "")),
        }

    _save_registry(registry)
    click.echo(f"Registered {len(validated_contracts)} node(s) in local registry")

    # Step 6: Golden chain test (opt-in)
    if test:
        click.echo("Running golden chain tests...")
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
            check=False,
        )
        if test_result.returncode != 0:
            click.echo("Warning: golden chain tests failed", err=True)


@click.command("uninstall")
@click.argument("package_name")
def cli_uninstall(package_name: str) -> None:
    """Uninstall an ONEX contract package and deregister from local registry."""
    # Deregister from local registry
    registry = _load_registry()
    removed = [
        name for name, info in registry.items() if info.get("package") == package_name
    ]
    for name in removed:
        del registry[name]
    _save_registry(registry)

    # pip uninstall
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
        check=False,
    )
    click.echo(f"Uninstalled {package_name}, deregistered {len(removed)} node(s)")
