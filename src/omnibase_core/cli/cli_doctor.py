# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import click
from pathlib import Path

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)

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
    def _get_omni_home() -> Path | None:
        bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
            declared_keys=("OMNI_HOME",)
        )
        raw = bootstrap.environment.optional("OMNI_HOME")
        return Path(raw) if raw else None

    builtin_checks = list(_BUILTIN_CHECKS)
    omni_home = _get_omni_home()
    developer_install = bool(omni_home is not None and omni_home.is_dir())
    if not developer_install:
        developer_only = {CheckDocker, CheckLinear, CheckReposSynced}
        builtin_checks = [
            check_cls for check_cls in builtin_checks if check_cls not in developer_only
        ]

    # Register built-ins
    for check_cls in builtin_checks:
        # Why: Registry stores protocol contracts rather than instantiating them directly.
        registry.register(check_cls)

    # Discover entry-point checks from other packages. On a customer
    # install the developer-only checks are skipped even when advertised by
    # an installed package.
    from importlib.metadata import entry_points

    developer_only_classes = {CheckDocker, CheckLinear, CheckReposSynced}
    for _ep in entry_points(group="onex.doctor"):
        _loaded = _ep.load()
        if isinstance(_loaded, type) and issubclass(_loaded, DoctorCheckBase):
            if not developer_install and _loaded in developer_only_classes:
                continue
            try:
                registry.register(_loaded)
            except ValueError:  # substrate-allow: duplicate entry point registration
                pass

    results = registry.run_all()
    report = ModelDoctorReport.from_results(results)

    if use_json:
        click.echo(report.render_json())
    else:
        report.render_human()

    if report.failed > 0:
        ctx.exit(1)
