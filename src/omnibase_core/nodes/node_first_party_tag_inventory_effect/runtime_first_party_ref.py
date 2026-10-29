# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Composition root for the generic first-party reference validator.

The default runtime is in-process. A broker overlay pair does not exist yet;
there is deliberately no invented broker configuration or parity claim.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import cast

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.handler import (
    NodeFirstPartyTagInventoryEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

# The concrete effect classes are the registry keys: a protocol key would add a
# protocols -> models import edge the layering ratchet freezes.
TAG_INVENTORY_SERVICE = cast(
    "type[NodeFirstPartyTagInventoryEffect]", NodeFirstPartyTagInventoryEffect
)
REPORT_WRITER_SERVICE = cast(
    "type[NodeValidationReportWriteEffect]", NodeValidationReportWriteEffect
)


def create_container(
    inventory: NodeFirstPartyTagInventoryEffect | None = None,
) -> ModelONEXContainer:
    """Register defaults or an explicit inventory overlay; resolution is separate."""
    container = ModelONEXContainer()

    async def register() -> None:
        registry = container.service_registry
        if inventory is None:
            await registry.register_instance(
                interface=TAG_INVENTORY_SERVICE,
                instance=NodeFirstPartyTagInventoryEffect(),
            )
        else:
            await registry.register_instance(
                interface=TAG_INVENTORY_SERVICE, instance=inventory
            )
        await registry.register_instance(
            interface=REPORT_WRITER_SERVICE, instance=NodeValidationReportWriteEffect()
        )

    run_coro_sync(register())
    return container


def resolve_effects(
    container: ModelONEXContainer,
) -> tuple[NodeFirstPartyTagInventoryEffect, NodeValidationReportWriteEffect]:
    """Both runtime effects always resolve through the container service API."""
    return (
        container.get_service(TAG_INVENTORY_SERVICE),
        container.get_service(REPORT_WRITER_SERVICE),
    )


def run(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the blocking check; read, parse, inventory and contract errors fail closed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args(argv)
    if container is None:
        container = create_container()
    inventory, writer = resolve_effects(container)
    validator_id = ValidatorFirstPartyRef.validator_id
    try:
        validator = ValidatorFirstPartyRef(root=args.root, inventory=inventory.handle)
        result = validator.validate(
            [args.root / path for path in args.targets] if args.targets else args.root
        )
        report = ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(
                    validator_id=validator_id,
                    severity="FAIL",
                    rule_id=issue.code,
                    location=f"{issue.file_path}:{issue.line_number}",
                    message=issue.message,
                    remediation=issue.suggestion,
                )
                for issue in result.issues
            ),
            request=ModelValidationRequestRef(profile="strict"),
            validators_run=(validator_id,),
        )
    except (
        OSError,
        ValueError,
        ModelOnexError,
        yaml.YAMLError,
        subprocess.SubprocessError,
    ) as exc:
        report = ModelValidationReport.from_runtime_errors(validator_id, (str(exc),))
    if args.report_json:
        writer.handle(
            ModelValidationReportWriteInput(
                report_path=str(args.report_json), report=report
            )
        )
    for finding in report.findings:
        sys.stdout.write(f"{finding.severity}: {finding.message}\n")
    sys.stdout.write(
        f"{report.overall_status}: first_party_ref ({len(report.findings)} findings)\n"
    )
    return 0 if report.overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
