# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import importlib

import click

from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.doctor.model_doctor_report import ModelDoctorReport

_BUILTIN_CHECKS = list(
    importlib.import_module(
        "omnibase_core.nodes.node_cli_doctor_effect.handler"
    ).default_builtin_checks()
)


@click.command("doctor")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def doctor(ctx: click.Context, use_json: bool) -> None:
    """Run diagnostic checks on your ONEX environment."""
    registry = DoctorRegistry()

    _bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=("OMNI_HOME",)
    )
    _handler = importlib.import_module(
        "omnibase_core.nodes.node_cli_doctor_effect.handler"
    )
    developer = _handler.developer_install(_bootstrap.environment.optional("OMNI_HOME"))
    for check_cls in _handler.builtin_checks(_BUILTIN_CHECKS, developer=developer):
        # Why: Registry stores protocol contracts rather than instantiating them directly.
        registry.register(check_cls)

    # Discover entry-point checks from other packages
    registry.discover(developer=developer)

    results = registry.run_all()
    report = ModelDoctorReport.from_results(results)

    if use_json:
        click.echo(report.render_json())
    else:
        report.render_human()

    if report.failed > 0:
        ctx.exit(1)
