# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import click
from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.doctor.checks import (
    CheckDocker,
    CheckKafka,
    CheckPostgres,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
    CheckEnvVars,
    CheckPythonVersion,
    CheckNodeVersion,
)
from omnibase_core.models.doctor.model_doctor_report import ModelDoctorReport


# Built-in checks registered at import time
_BUILTIN_CHECKS = [
    CheckDocker,
    CheckKafka,
    CheckPostgres,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
    CheckEnvVars,
    CheckPythonVersion,
    CheckNodeVersion,
]


@click.command("doctor")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def doctor(ctx: click.Context, use_json: bool) -> None:
    """Run diagnostic checks on your ONEX environment."""
    registry = DoctorRegistry()

    # Register built-ins
    for check_cls in _BUILTIN_CHECKS:
        registry.register(check_cls)

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
