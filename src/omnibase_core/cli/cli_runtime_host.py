# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI command for runtime-host-dev (dev/test only).

WARNING: This CLI is for development and testing ONLY.
Do NOT use in production environments.

This provides a simple entry point for testing the Runtime Host with
LocalHandler only. It validates contract paths and provides basic
runtime host initialization for development purposes.

Usage:
    omninode-runtime-host-dev CONTRACT.yaml
    omninode-runtime-host-dev --validate-only CONTRACT.yaml
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.contracts.model_runtime_host_contract import (
    ModelRuntimeHostContract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@click.command(name="runtime-host-dev")
@click.option(
    "--validate-only",
    "-v",
    is_flag=True,
    default=False,
    help=(
        "Validate the contract against schema and exit. "
        "Does not start the runtime. "
        "Exit code: 0 = valid, 1 = invalid."
    ),
)
@click.argument(
    "contract_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
def main(validate_only: bool, contract_path: Path) -> None:
    """Start runtime host in dev/test mode (LocalHandler only).

    WARNING: This command is for DEVELOPMENT and TESTING only.
    Do NOT use in production environments.

    This is a Phase 1 MVP CLI that provides basic runtime host
    initialization for local development and testing purposes.

    \b
    Arguments:
        CONTRACT_PATH: Path to the RuntimeHostContract YAML file.

    \b
    Options:
        --validate-only / -v: Validate contract schema and exit (no runtime start).

    \b
    Examples:
        omninode-runtime-host-dev contracts/dev_config.yaml
        omninode-runtime-host-dev --validate-only contracts/dev_config.yaml
    """
    # Hard check for production environment - NEVER run in prod
    env_value = os.environ.get("ENVIRONMENT", "").lower()
    if env_value == "prod":
        click.echo(
            click.style(
                "ERROR: Cannot run dev runtime host in production environment!",
                fg="red",
            )
        )
        click.echo(
            "The ENVIRONMENT variable is set to 'prod'. "
            "This CLI is for development and testing only."
        )
        sys.exit(EnumCLIExitCode.ERROR)  # error-ok: CLI exit code for production check

    if validate_only:
        _run_validate_only(contract_path)
        return

    # Print prominent warning about dev/test usage
    click.echo(
        click.style(
            "=" * 60,
            fg="yellow",
        )
    )
    click.echo(
        click.style(
            "WARNING: This is a DEV/TEST runtime host.",
            fg="yellow",
            bold=True,
        )
    )
    click.echo(
        click.style(
            "         Not for production use.",
            fg="yellow",
            bold=True,
        )
    )
    click.echo(
        click.style(
            "=" * 60,
            fg="yellow",
        )
    )

    # Log warning for structured logging consumers
    emit_log_event_sync(
        EnumLogLevel.WARNING,
        "Starting dev/test runtime host - NOT FOR PRODUCTION",
        {
            "contract_path": str(contract_path),
            "environment": env_value or "not set",
        },
    )

    # MVP: Just validate and print info
    # Actual runtime integration comes in later tickets
    click.echo(f"\nLoading contract from: {contract_path}")

    # Verify the file is readable and report basic info
    try:
        contract_content = contract_path.read_text()
        line_count = len(contract_content.splitlines())
        click.echo(
            f"Contract file size: {len(contract_content)} bytes ({line_count} lines)"
        )
    except OSError as e:
        click.echo(
            click.style(
                f"ERROR: Failed to read contract file: {e}",
                fg="red",
            )
        )
        sys.exit(EnumCLIExitCode.ERROR)  # error-ok: CLI exit code for I/O failure

    click.echo(
        click.style(
            "\nRuntime host dev mode started successfully.",
            fg="green",
        )
    )
    click.echo("MVP: Contract validated. Actual runtime integration coming soon.")


def _run_validate_only(contract_path: Path) -> None:
    """Validate the contract schema and exit.

    Parses and validates the contract YAML against the RuntimeHostContract
    schema. Prints a summary of validation results and exits with:
        - 0 if the contract is valid
        - 1 if the contract is invalid (parse error, schema mismatch, etc.)

    Args:
        contract_path: Path to the YAML contract file to validate.
    """
    click.echo(f"Validating contract: {contract_path}")

    try:
        contract = ModelRuntimeHostContract.from_yaml(contract_path)
    except ModelOnexError as e:
        click.echo(
            click.style(
                "INVALID",
                fg="red",
                bold=True,
            )
        )
        click.echo(f"Validation failed: {e.message}")
        # Print any additional context details (e.g. validation_error summary)
        additional = e.context.get("additional_context")
        if additional and isinstance(additional, dict):
            for key, value in additional.items():
                if key not in ("validation_errors",):
                    click.echo(f"  {key}: {value}")
        sys.exit(EnumCLIExitCode.ERROR)  # error-ok: CLI exit code for invalid contract

    # Report success
    handler_count = len(contract.handlers)
    node_count = len(contract.nodes)
    click.echo(
        click.style(
            "VALID",
            fg="green",
            bold=True,
        )
    )
    click.echo(
        f"Contract is valid: {handler_count} handler(s), "
        f"{node_count} node(s), "
        f"event_bus.kind={contract.event_bus.kind!r}"
    )


if __name__ == "__main__":
    main()
