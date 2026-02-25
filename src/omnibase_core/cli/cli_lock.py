# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
``omn lock`` CLI command — contract lockfile generation and CI enforcement.

Usage:
    omn lock                       # generate omn.lock from current catalog
    omn lock --check               # verify lockfile without modifying it (CI)
    omn lock --diff                # show drifted contracts since last lock
    omn lock --output PATH         # write lockfile to a custom path

CI Integration:
    Add ``omn lock --check`` to your CI pre-flight steps.  It exits non-zero
    if any contract fingerprints have drifted since the lockfile was generated.

    Example GitHub Actions step:

        - name: Verify contract lockfile
          run: omn lock --check

Commit the generated ``omn.lock`` to version control.  It is human-readable
YAML, suitable for code review.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from pathlib import Path

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.errors.error_lock import (
    LockDriftError,
    LockError,
    LockFileError,
    LockPartialError,
)

__all__ = ["lock"]


@click.group()
@click.pass_context
def lock(ctx: click.Context) -> None:
    """Contract lockfile generation and CI enforcement.

    ``omn lock`` pins the exact contract fingerprints used by the CLI at a
    point in time, analogous to ``poetry.lock`` or ``package-lock.json``.

    \b
    Commit ``omn.lock`` to version control so CI can verify determinism.

    \b
    Examples:
        omn lock                  # generate or update omn.lock
        omn lock check            # verify (CI-safe, no modifications)
        omn lock diff             # show drifted contracts
    """
    ctx.ensure_object(dict)


@lock.command("generate")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for the lockfile (default: ./omn.lock).",
)
@click.option(
    "--catalog",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to catalog cache file (default: ~/.omn/catalog.json).",
)
@click.pass_context
def generate(
    ctx: click.Context,
    output: Path | None,
    catalog: Path | None,
) -> None:
    """Generate omn.lock from the current catalog.

    Reads the current command catalog (populated by ``omn refresh``) and
    writes a lockfile pinning each command's contract fingerprint.

    The lockfile is deterministic: the same catalog state always produces
    identical lockfile bytes.

    Commit the generated ``omn.lock`` to version control.

    \b
    Examples:
        omn lock generate
        omn lock generate --output /path/to/omn.lock
    """
    from omnibase_core.cli.cli_commands import get_version
    from omnibase_core.services.catalog.service_catalog_manager import (
        CatalogLoadError,
        ServiceCatalogManager,
    )
    from omnibase_core.services.lock.service_lock_manager import ServiceLockManager

    catalog_path = catalog or (Path.home() / ".omn" / "catalog.json")
    lock_path = output or Path("omn.lock")
    cli_ver = get_version()

    try:
        # Load the catalog without enforcing CLI version (version is for lockfile metadata only).
        mgr = ServiceCatalogManager(cache_path=catalog_path, cli_version="")
        mgr.load()
    except CatalogLoadError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Failed to load catalog: {exc}") from exc

    try:
        lock_mgr = ServiceLockManager(
            catalog=mgr,
            lock_path=lock_path,
            cli_version=cli_ver,
        )
        lockfile = lock_mgr.generate()
    except LockError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Failed to generate lockfile: {exc}") from exc

    n_commands = len(lockfile.commands)
    click.echo(
        click.style(
            f"Lockfile written: {lock_path} ({n_commands} command(s) pinned)",
            fg="green",
        )
    )
    ctx.exit(EnumCLIExitCode.SUCCESS)


@lock.command("check")
@click.option(
    "--lockfile",
    "-l",
    "lockfile_path",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Path to lockfile (default: ./omn.lock).",
)
@click.option(
    "--catalog",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to catalog cache file (default: ~/.omn/catalog.json).",
)
@click.pass_context
def check(
    ctx: click.Context,
    lockfile_path: Path | None,
    catalog: Path | None,
) -> None:
    """Verify the lockfile without modifying it (CI-safe).

    Compares the current catalog fingerprints against the lockfile.
    Exits 0 if no drift is detected, non-zero if any fingerprint has
    changed.  Never modifies the lockfile or catalog.

    Use this command in CI pre-flight steps.

    \b
    Examples:
        omn lock check
        omn lock check --lockfile /path/to/omn.lock
    """
    from omnibase_core.cli.cli_commands import get_version
    from omnibase_core.services.catalog.service_catalog_manager import (
        CatalogLoadError,
        ServiceCatalogManager,
    )
    from omnibase_core.services.lock.service_lock_manager import ServiceLockManager

    catalog_path = catalog or (Path.home() / ".omn" / "catalog.json")
    lock_path = lockfile_path or Path("omn.lock")
    cli_ver = get_version()

    try:
        # Load without CLI version enforcement (version is stored in lockfile only).
        mgr = ServiceCatalogManager(cache_path=catalog_path, cli_version="")
        mgr.load()
    except CatalogLoadError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Failed to load catalog: {exc}") from exc

    lock_mgr = ServiceLockManager(
        catalog=mgr,
        lock_path=lock_path,
        cli_version=cli_ver,
    )

    drift_found = False
    try:
        lock_mgr.check()
    except LockFileError as exc:
        raise click.ClickException(str(exc)) from exc
    except LockPartialError as exc:
        click.echo(click.style(f"[PARTIAL] {exc}", fg="red"), err=True)
        drift_found = True
    except LockDriftError as exc:
        click.echo(click.style(f"[DRIFT DETECTED] {exc}", fg="red"), err=True)
        drift_found = True
    except LockError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Unexpected error during check: {exc}") from exc

    exit_code = EnumCLIExitCode.ERROR if drift_found else EnumCLIExitCode.SUCCESS
    if not drift_found:
        click.echo(click.style("Lockfile check passed: no drift detected.", fg="green"))
    ctx.exit(exit_code)


@lock.command("diff")
@click.option(
    "--lockfile",
    "-l",
    "lockfile_path",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Path to lockfile (default: ./omn.lock).",
)
@click.option(
    "--catalog",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to catalog cache file (default: ~/.omn/catalog.json).",
)
@click.pass_context
def diff(
    ctx: click.Context,
    lockfile_path: Path | None,
    catalog: Path | None,
) -> None:
    """Show contracts that have drifted since the lockfile was generated.

    Compares the lockfile against the current catalog and prints a
    human-readable list of drifted contracts with status:

    \b
      changed  — fingerprint changed (contract mutated)
      added    — new command in catalog not yet in lockfile
      removed  — command in lockfile no longer in catalog

    Exits 0 if no drift, non-zero if drift is detected.

    \b
    Examples:
        omn lock diff
        omn lock diff --lockfile /path/to/omn.lock
    """
    from omnibase_core.cli.cli_commands import get_version
    from omnibase_core.services.catalog.service_catalog_manager import (
        CatalogLoadError,
        ServiceCatalogManager,
    )
    from omnibase_core.services.lock.service_lock_manager import ServiceLockManager

    catalog_path = catalog or (Path.home() / ".omn" / "catalog.json")
    lock_path = lockfile_path or Path("omn.lock")
    cli_ver = get_version()

    try:
        # Load without CLI version enforcement (version is stored in lockfile only).
        mgr = ServiceCatalogManager(cache_path=catalog_path, cli_version="")
        mgr.load()
    except CatalogLoadError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Failed to load catalog: {exc}") from exc

    lock_mgr = ServiceLockManager(
        catalog=mgr,
        lock_path=lock_path,
        cli_version=cli_ver,
    )

    from omnibase_core.services.lock.service_lock_manager import ModelLockDiffResult

    try:
        diff_result: ModelLockDiffResult = lock_mgr.diff()
    except LockFileError as exc:
        raise click.ClickException(str(exc)) from exc
    except LockPartialError as exc:
        click.echo(click.style(f"[PARTIAL LOCKFILE] {exc}", fg="yellow"))
        ctx.exit(EnumCLIExitCode.ERROR)
    except LockError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # catch-all-ok: surfaced to user as ClickException
        raise click.ClickException(f"Unexpected error during diff: {exc}") from exc

    if diff_result.is_clean:
        click.echo(
            click.style("No drift detected. Lockfile is up to date.", fg="green")
        )
        ctx.exit(EnumCLIExitCode.SUCCESS)

    click.echo(
        click.style(
            f"Drift detected: {len(diff_result.drifted)} command(s) have changed.",
            fg="red",
        )
    )
    for entry in sorted(diff_result.drifted, key=lambda e: e.command_id):
        status_color = {
            "changed": "yellow",
            "added": "cyan",
            "removed": "red",
        }.get(entry.status, "white")
        tag = click.style(f"[{entry.status.upper()}]", fg=status_color)
        click.echo(f"  {tag} {entry.command_id}")
        if entry.locked_fingerprint:
            click.echo(f"    locked:  {entry.locked_fingerprint}")
        if entry.current_fingerprint:
            click.echo(f"    current: {entry.current_fingerprint}")

    ctx.exit(EnumCLIExitCode.ERROR)
