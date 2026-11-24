# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pathlib import Path

import click

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
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.doctor.model_doctor_report import ModelDoctorReport

# Built-in checks registered at import time. Annotated explicitly: without it
# the inferred element type is the metaclass, not type[DoctorCheckBase].
_BUILTIN_CHECKS: list[type[DoctorCheckBase]] = [
    CheckDocker,
    CheckKafka,
    CheckPostgres,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
    CheckEnvVars,
    CheckPythonVersion,
    CheckJsRuntime,
]

# Checks that only make sense on a developer install (OMN-26616).
_DEVELOPER_ONLY: frozenset[type[DoctorCheckBase]] = frozenset(
    {CheckDocker, CheckLinear, CheckReposSynced}
)


@click.command("doctor")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def doctor(ctx: click.Context, use_json: bool) -> None:
    """Run diagnostic checks on your ONEX environment."""
    registry = DoctorRegistry()

    # Customer installs (OMNI_HOME unset or non-existent) run only the checks
    # a customer needs. Developer-only checks (Docker, Linear, repo sync) run
    # only on a developer install where OMNI_HOME points at an existing
    # multi-repo registry directory.
    _bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=("OMNI_HOME",)
    )
    _raw_omni_home = _bootstrap.environment.optional("OMNI_HOME")
    developer_install = bool(_raw_omni_home and Path(_raw_omni_home).is_dir())
    if developer_install:
        builtin_checks = list(_BUILTIN_CHECKS)
    else:
        builtin_checks = [c for c in _BUILTIN_CHECKS if c not in _DEVELOPER_ONLY]

    # Register built-ins
    for check_cls in builtin_checks:
        # Why: Registry stores protocol contracts rather than instantiating them directly.
        registry.register(check_cls)

    # Discover entry-point checks from other packages. On a customer install
    # the developer-only checks stay out even when a package advertises them.
    registry.discover(exclude=frozenset() if developer_install else _DEVELOPER_ONLY)

    results = registry.run_all()
    report = ModelDoctorReport.from_results(results)

    if use_json:
        click.echo(report.render_json())
    else:
        report.render_human()

    if report.failed > 0:
        ctx.exit(1)
