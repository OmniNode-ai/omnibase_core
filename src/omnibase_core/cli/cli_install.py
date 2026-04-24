# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command for installing ONEX contract packages with validation.

Supports two installation modes:
1. `.oncp` archives — unpack to local registry directory
2. pip packages — install via pip with contract validation
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import click


def _in_virtualenv() -> bool:
    """Check if running inside a virtual environment."""
    return sys.prefix != sys.base_prefix


def _get_registry_dir() -> Path:
    """Return the local ONEX registry directory for unpacked .oncp packages."""
    return Path.home() / ".omnibase" / "registry"


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


def _rollback_install(pkg: str) -> None:
    """Uninstall a package after failed validation."""
    click.echo(f"Rolling back: uninstalling {pkg}", err=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
        capture_output=True,
        check=False,
    )


def _validate_contract(contract_path: Path) -> dict[str, object]:
    """Validate a contract.yaml file with the Pydantic contract model.

    Raises:
        click.ClickException: If the contract is malformed or invalid.
    """
    from pydantic import ValidationError

    try:
        from omnibase_core.contracts.contract_loader import load_contract
        from omnibase_core.models.contracts.model_yaml_contract import (
            ModelYamlContract,
        )

        contract = load_contract(contract_path)
        ModelYamlContract.model_validate(contract)
    except Exception as e:
        if isinstance(e, click.ClickException):
            raise
        msg = f"contract.yaml at {contract_path} is not valid: {e}"
        if isinstance(e, ValidationError):
            msg = f"contract.yaml at {contract_path} failed model validation: {e}"
        raise click.ClickException(msg) from e

    # name is always required
    raw_name = contract.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        msg = "contract.yaml missing required field: name"
        raise click.ClickException(msg)

    if "contract_version" not in contract:
        msg = "contract.yaml missing required field: contract_version"
        raise click.ClickException(msg)

    return contract


def _entry_point_module(value: str) -> str:
    """Return the importable module portion of an entry-point value."""
    return value.split(":", 1)[0].strip()


def _resolve_entry_point_contract_path(entry_point_value: str) -> Path:
    """Resolve a packaged contract path without importing the node module."""
    module_path = _entry_point_module(entry_point_value)
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise click.ClickException(
            f"Cannot resolve module {module_path} from installed metadata"
        )
    if spec.submodule_search_locations:
        module_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
    elif spec.origin is not None:
        module_dir = Path(spec.origin).resolve().parent
    else:
        raise click.ClickException(
            f"Module {module_path} has no import origin for contract resolution"
        )

    contract_path = module_dir / "contract.yaml"
    if not contract_path.exists():
        raise click.ClickException(f"Missing contract.yaml in {module_path}")
    return contract_path


def _install_oncp(
    archive_path: Path,
    dry_run: bool,
    upgrade: bool,
    verbose: bool,
) -> list[dict[str, object]]:
    """Install an .oncp archive by unpacking to the local registry directory.

    Returns:
        List of validated contract dicts for each node in the archive.
    """
    registry_dir = _get_registry_dir()

    if not archive_path.exists():
        raise click.ClickException(f"Archive not found: {archive_path}")

    # Verify it's a valid .oncp archive
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getnames()
    except Exception as e:
        raise click.ClickException(f"Invalid .oncp archive: {e}") from e

    if "metadata.yaml" not in members or "contract.yaml" not in members:
        raise click.ClickException(
            "Invalid .oncp archive: missing metadata.yaml or contract.yaml"
        )

    # Extract metadata to get package info
    # NOTE(OMN-7537): metadata.yaml is an external contract file.
    import yaml

    with tarfile.open(archive_path, "r:gz") as tar:
        mf = tar.extractfile("metadata.yaml")
        if mf is None:
            raise click.ClickException("Cannot read metadata.yaml from archive")
        metadata = yaml.safe_load(mf)

    if not isinstance(metadata, dict):
        raise click.ClickException("metadata.yaml is not a valid YAML mapping")
    raw_name = metadata.get("name")
    raw_version = metadata.get("version")
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise click.ClickException(
            "Invalid .oncp archive: metadata.yaml 'name' must be a non-empty string"
        )
    if not isinstance(raw_version, str) or not raw_version.strip():
        raise click.ClickException(
            "Invalid .oncp archive: metadata.yaml 'version' must be a non-empty string"
        )
    package_name = raw_name.strip()
    package_version = raw_version.strip()
    # Reject path-like names that would let install_path escape registry_dir.
    # shutil.rmtree(install_path) on --upgrade would otherwise target an
    # attacker-chosen location.
    if (
        package_name in {".", ".."}
        or "/" in package_name
        or "\\" in package_name
        or Path(package_name).is_absolute()
    ):
        raise click.ClickException(
            "Invalid .oncp archive: metadata.yaml 'name' must be a safe package basename "
            "(no path separators, no '.'/'..', no absolute paths)"
        )
    install_path = registry_dir / package_name

    if verbose:
        click.echo(f"  Package: {package_name} v{package_version}")
        click.echo(f"  Install path: {install_path}")

    if install_path.exists() and not upgrade:
        raise click.ClickException(
            f"Node '{package_name}' is already installed at {install_path}. "
            "Use --upgrade to replace."
        )

    # Stage extraction in a temp dir so --dry-run exercises real validation
    # and --upgrade is atomic: the existing install is only removed once the
    # new archive has successfully extracted AND its contract has validated.
    registry_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=registry_dir) as tmp_dir:
        staged_path = Path(tmp_dir) / package_name
        with tarfile.open(archive_path, "r:gz") as tar:
            # PEP 706 data filter rejects absolute paths, traversal, symlink
            # escapes, and device files.
            tar.extractall(path=staged_path, filter="data")

        contract = _validate_contract(staged_path / "contract.yaml")

        if dry_run:
            click.echo(f"\nDry run: would unpack {archive_path.name} to {install_path}")
            click.echo(f"  Archive members: {len(members)}")
            return [contract]

        if install_path.exists():
            shutil.rmtree(install_path)
        shutil.move(str(staged_path), str(install_path))

    # Register in local registry
    registry = _load_registry()
    registry[package_name] = {
        "package": package_name,
        "version": package_version,
        "source": "oncp",
        "path": str(install_path),
        "archive": str(archive_path),
    }
    _save_registry(registry)

    click.echo(f"Installed {package_name} v{package_version} to {install_path}")
    return [contract]


@click.command("install")
@click.argument("package_path")
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
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed installation output.",
)
def cli_install(
    package_path: str,
    test: bool,
    dry_run: bool,
    upgrade: bool,
    allow_unsigned: bool,
    verbose: bool,
) -> None:
    """Install an ONEX contract package with validation.

    Supports two modes:
    1. .oncp archives — unpack to ~/.omnibase/registry/<name>/
    2. pip packages — install via pip with contract validation

    \b
    Examples:
        onex install node_aislop_sweep-1.0.0.oncp
        onex install ./my-package.oncp --upgrade
        onex install omnimarket --dry-run
    """
    path = Path(package_path)

    # Mode 1: .oncp archive
    if path.exists() and path.suffix == ".oncp":
        validated = _install_oncp(
            path, dry_run=dry_run, upgrade=upgrade, verbose=verbose
        )
        if dry_run:
            return
        if test and validated:
            click.echo("Running golden chain tests...")
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
                check=False,
            )
            if test_result.returncode != 0:
                click.echo("Warning: golden chain tests failed", err=True)
        return

    # Mode 2: pip package (original behavior)
    if not _in_virtualenv():
        raise click.ClickException(
            "onex install must be run inside a virtual environment for pip packages"
        )

    # Step 1: pip install (skip for dry-run)
    if not dry_run:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise click.ClickException(f"pip install failed: {result.stderr.strip()}")
        click.echo(f"Installed {package_path}")

    # Step 2: Discover entry points
    eps = importlib.metadata.entry_points(group="onex.nodes")
    # Normalize package name for comparison (PEP 503)
    normalized = package_path.replace("-", "_").replace(".", "_").lower()
    matching = [
        ep
        for ep in eps
        if ep.dist
        and ep.dist.name.replace("-", "_").replace(".", "_").lower() == normalized
    ]

    if not matching:
        click.echo(f"Warning: {package_path} has no onex.nodes entry points", err=True)
        if not dry_run:
            return

    # Step 3: Validate contract.yaml for each discovered node
    validated_contracts: list[dict[str, object]] = []
    for ep in matching:
        try:
            contract_path = _resolve_entry_point_contract_path(ep.value)
        except click.ClickException:
            if not dry_run:
                _rollback_install(package_path)
            raise

        try:
            contract = _validate_contract(contract_path)
        except click.ClickException:
            if not dry_run:
                _rollback_install(package_path)
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
                    _rollback_install(package_path)
                    raise click.ClickException(
                        f"{package_path} has no onex-signature metadata. "
                        "Use --allow-unsigned to install anyway."
                    )
                if not has_signature:
                    click.echo(f"Warning: {package_path} is unsigned", err=True)
        except click.ClickException:
            raise
        except Exception:  # noqa: BLE001
            click.echo("Warning: could not check package signature", err=True)

    if dry_run:
        click.echo(f"\nDry run complete for {package_path}")
        for contract in validated_contracts:
            click.echo(f"  Node: {contract.get('name', 'unknown')}")
        return

    # Step 5: Check version conflicts and register
    registry = _load_registry()
    for contract in validated_contracts:
        contract_name = str(contract.get("name", ""))
        if contract_name in registry and not upgrade:
            _rollback_install(package_path)
            raise click.ClickException(
                f"Node '{contract_name}' is already registered. "
                "Use --upgrade to replace."
            )
        registry[contract_name] = {
            "package": package_path,
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
