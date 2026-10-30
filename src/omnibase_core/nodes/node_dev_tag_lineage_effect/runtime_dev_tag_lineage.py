# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container composition root for dev-tag lineage, usable outside the source checkout."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_overlay import (
    ModelValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_dev_tag_lineage_effect.handler import (
    NodeDevTagLineageEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    run_validator,
)
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage


def create_container(
    overlay: ModelValidatorRuntimeOverlay, effect: NodeDevTagLineageEffect | None = None
) -> ModelONEXContainer:
    """Compose generic report services and the default or explicit lineage effect overlay."""
    container = build_validator_container(overlay)

    async def register() -> None:
        await container.service_registry.register_instance(
            interface=NodeDevTagLineageEffect,
            instance=effect if effect is not None else NodeDevTagLineageEffect(),
        )

    asyncio.run(register())
    return container


def run(
    argv: list[str] | None = None,
    *,
    container_factory: Callable[
        [ModelValidatorRuntimeOverlay], ModelONEXContainer
    ] = create_container,
) -> int:
    """Run through the generic report runtime; all runtime errors refuse the pin."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--package")
    parser.add_argument("--report-json")
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args(argv)
    try:
        handler = HandlerValidatorRuntimeOverlay()
        settings = handler.settings()
        overlay = handler.load(args.overlay or handler.default_overlay_path())
        container = container_factory(overlay)
        effect = container.get_service(NodeDevTagLineageEffect)
        validator = ValidatorDevTagLineage(
            root=args.root, resolver=effect.handle, package=args.package
        )
        targets = (
            [args.root / target for target in args.targets]
            if args.targets
            else [args.root]
        )
        result = run_validator(
            container,
            validator,
            targets,
            args.report_json
            or settings.default_report_path.format(validator_id=validator.validator_id),
            overlay.profile,
            settings.default_repository,
        )
        for issue in result.issues:
            sys.stdout.write(f"{issue.file_path}: {issue.rule_name}: {issue.message}\n")
        return 0 if result.is_valid else 1
    except (
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        KeyError,
        ImportError,
        AttributeError,
        ModelOnexError,
        yaml.YAMLError,
        subprocess.SubprocessError,
    ) as exc:
        sys.stdout.write(f"dev_tag_lineage: runtime error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run())
