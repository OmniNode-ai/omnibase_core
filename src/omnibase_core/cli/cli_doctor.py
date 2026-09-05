# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import click

from omnibase_core.cli.cli_user_config import user_config_path
from omnibase_core.doctor.checks import (
    CheckDocker,
    CheckEnvVars,
    CheckJsRuntime,
    CheckKafka,
    CheckLinear,
    CheckPostgres,
    CheckPythonVersion,
    CheckReposSynced,
    CheckStaleWorktrees,
)
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.models.doctor.model_doctor_report import ModelDoctorReport

# Built-in checks that construct with no declared dependency.
_BUILTIN_CHECKS = [
    CheckDocker,
    CheckKafka,
    CheckPostgres,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
    CheckPythonVersion,
    CheckJsRuntime,
]


def _build_env_vars_check() -> DoctorCheckBase:
    """Bind the credential check to the user config it proves the binding from.

    The location is resolved here, at the CLI boundary, and passed in. The check
    must not resolve its own authority: a check that supplies the thing it then
    asserts on reports its own health, which is how a doctor came to print
    "All 2 dependencies bound" with both real values absent (OMN-17554).
    """
    return CheckEnvVars(user_config_path())


@click.command("doctor")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def doctor(ctx: click.Context, use_json: bool) -> None:
    """Run diagnostic checks on your ONEX environment."""
    registry = DoctorRegistry()

    # Register built-ins
    for check_cls in _BUILTIN_CHECKS:
        # Why: Registry stores protocol contracts rather than instantiating them directly.
        registry.register(check_cls)  # type: ignore[type-abstract]

    registry.register(CheckEnvVars, factory=_build_env_vars_check)

    # Discover entry-point checks from other packages
    registry.discover()

    results = registry.run_all()
    report = ModelDoctorReport.from_results(results)

    if use_json:
        click.echo(report.render_json())
    else:
        report.render_human()

    if report.failed > 0:
        ctx.exit(1)
