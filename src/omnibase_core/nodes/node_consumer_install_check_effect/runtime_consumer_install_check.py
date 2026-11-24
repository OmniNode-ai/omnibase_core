# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI runtime of the consumer install check (OMN-26670).

CI builds the head, then runs this module with the built wheel as the candidate. Exit 0 when every
consumer imports and collects, 1 when any does not, 2 when the overlay or the request is invalid.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_request import (
    ModelConsumerInstallRequest,
)
from omnibase_core.nodes.node_consumer_install_check_effect.exec_subprocess import (
    HandlerSubprocessExec,
)
from omnibase_core.nodes.node_consumer_install_check_effect.handler_consumer_install_check import (
    HandlerConsumerInstallCheck,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

__all__ = ["build_container", "main"]

_HANDLER_TOKEN = cast("type[HandlerConsumerInstallCheck]", HandlerConsumerInstallCheck)
_EXEC_TOKEN = cast("type[HandlerSubprocessExec]", HandlerSubprocessExec)


def build_container(
    command_handler: type[HandlerSubprocessExec] = HandlerSubprocessExec,
) -> ModelONEXContainer:
    """Register the handler and the runner it drives; a test registers a fake runner."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    run_coro_sync(
        registry.register_service(
            _EXEC_TOKEN,
            command_handler,
            EnumServiceLifecycle.SINGLETON,
            EnumInjectionScope.GLOBAL,
        )
    )
    run_coro_sync(
        registry.register_instance(
            _HANDLER_TOKEN, HandlerConsumerInstallCheck(container)
        )
    )
    return container


def main(
    argv: Sequence[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """CLI entry: print one line per consumer and one FAIL line per finding."""
    parser = argparse.ArgumentParser(
        description="Install a candidate build into its consumers and import them."
    )
    parser.add_argument("--candidate-distribution", required=True)
    parser.add_argument("--candidate-spec", required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--consumer-ref", action="append", default=[], metavar="NAME=REF"
    )
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    overrides = tuple(
        (name, ref)
        for name, _, ref in (item.partition("=") for item in args.consumer_ref)
    )
    owned = container is None
    if container is None:
        container = build_container()
    try:
        request = ModelConsumerInstallRequest(
            candidate_distribution=args.candidate_distribution,
            candidate_spec=args.candidate_spec,
            overlay_path=args.overlay,
            work_dir=args.work_dir,
            consumer_ref_overrides=overrides,
        )
        result = container.get_service(_HANDLER_TOKEN).handle(request)
    except (OSError, ValueError, ModelOnexError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    finally:
        if owned:
            container.close()
    for outcome in result.outcomes:
        sys.stdout.write(
            f"consumer={outcome.consumer} ref={outcome.ref} sha={outcome.resolved_sha} "
            f"entry_points_imported={outcome.entry_points_imported} "
            f"tests_collected={outcome.tests_collected} elapsed={outcome.elapsed_seconds:.1f}s "
            f"stages={ {k: round(v, 1) for k, v in outcome.stage_seconds.items()} } "
            f"smoke={outcome.smoke_summary or 'none'}\n"
        )
    sys.stdout.write(
        f"candidate={result.candidate_distribution} passed={str(result.passed).lower()} "
        f"elapsed={result.elapsed_seconds:.1f}s budget={result.budget_seconds:.0f}s\n"
    )
    if result.over_budget:
        sys.stdout.write(
            f"::warning::consumer install check took {result.elapsed_seconds:.0f}s, "
            f"over the {result.budget_seconds:.0f}s bound\n"
        )
    if args.report is not None:
        args.report.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    for line in result.failure_lines:
        sys.stderr.write(f"::error::{line}\n")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
