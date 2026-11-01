# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Composition root for the generic first-party reference validator.

The default runtime is in-process. A broker overlay pair does not exist yet;
there is deliberately no invented broker configuration or parity claim.

Without ``--baseline`` every finding fails. ``--baseline FILE`` holds today's findings
of a consumer in the shared shrink-only per-file baseline (``HandlerFindingBaseline``,
OMN-21900): a finding outside it fails, an entry whose finding is gone fails as stale,
and ``--write-baseline`` creates the file or shrinks it and refuses to add an entry.
The contract keeps its zero target; the baseline is the only holding structure and
carries no suppression marker.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import cast

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.finding_baseline.model_finding_baseline import (
    ModelFindingBaseline,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_input import (
    ModelFindingBaselineInput,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_scope import (
    ModelFindingBaselineScope,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_finding_baseline_check_effect.handler_finding_baseline import (
    HandlerFindingBaseline,
    normalize_text,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.handler import (
    NodeFirstPartyTagInventoryEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

# The concrete effect classes are the registry keys: a protocol key would add a
# protocols -> models import edge the layering ratchet freezes.
TAG_INVENTORY_SERVICE = cast(
    "type[NodeFirstPartyTagInventoryEffect]", NodeFirstPartyTagInventoryEffect
)
REPORT_WRITER_SERVICE = cast(
    "type[NodeValidationReportWriteEffect]", NodeValidationReportWriteEffect
)
BASELINE_SERVICE = cast("type[HandlerFindingBaseline]", HandlerFindingBaseline)

HOOK_ID = ValidatorFirstPartyRef.validator_id
ZERO_TARGET_NOTE = (
    "# Zero target: first_party_ref is blocking with max_violations 0 and no suppressions.\n"
    "# This file only holds the findings that were not removable when the hook was wired;\n"
    "# it is generated, it only shrinks, and it carries no suppression marker, allowlist or\n"
    "# exception entry.\n"
)
# Sibling-pin rules report line 1 of pyproject.toml, so their identity is the message.
_MESSAGE_TEXT_RULES = frozenset({"missing_source", "wrong_repo", "release_pin"})
_STALE_RULE = "stale_pin"


def _finding_text(issue: ModelValidationIssue, root: Path) -> str:
    if issue.code in _MESSAGE_TEXT_RULES:
        return normalize_text(issue.message)
    if issue.code == _STALE_RULE:
        # The trailing merge and hour counts move every night; the pin does not.
        return normalize_text(issue.message.partition(" trails ")[0])
    lines = (root / str(issue.file_path)).read_text(encoding="utf-8").splitlines()
    number = issue.line_number or 0
    return normalize_text(
        lines[number - 1] if 0 < number <= len(lines) else issue.message
    )


def _source_findings(
    issues: tuple[ModelValidationIssue, ...] | list[ModelValidationIssue], root: Path
) -> tuple[ModelSourceFinding, ...]:
    return tuple(
        ModelSourceFinding(
            path=str(issue.file_path),
            line=issue.line_number or 0,
            rule=issue.code or "first_party_ref",
            text=_finding_text(issue, root),
            message=issue.message,
        )
        for issue in issues
    )


def _load_baseline(path: Path) -> ModelFindingBaseline | None:
    if not path.is_file():
        return None
    baseline = load_yaml_content_as_model(
        path.read_text(encoding="utf-8"), ModelFindingBaseline
    )
    if baseline.hook != HOOK_ID:
        raise ModelOnexError(
            message=f"{path} is the baseline of hook {baseline.hook!r}, not {HOOK_ID!r}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return baseline


def _render(handler: HandlerFindingBaseline, baseline: ModelFindingBaseline) -> str:
    text = handler.render(baseline)
    head, separator, body = text.partition("---\n")
    return head + ZERO_TARGET_NOTE + separator + body


def _write_baseline(
    handler: HandlerFindingBaseline,
    path: Path,
    baseline: ModelFindingBaseline | None,
    findings: tuple[ModelSourceFinding, ...],
    scope: ModelFindingBaselineScope,
) -> int:
    entries = baseline.entries if baseline is not None else ()
    shrink = handler.shrink(findings, entries, scope)
    if baseline is not None and shrink.added:
        for finding in shrink.added:
            sys.stdout.write(
                f"REFUSED: --write-baseline would add an entry: {finding.path} "
                f"[{finding.rule}] {finding.text!r}\n"
            )
        sys.stdout.write(f"{path} was not written; a baseline only shrinks\n")
        return 1
    document = (
        handler.create(HOOK_ID, findings)
        if baseline is None
        else baseline.model_copy(update={"entries": shrink.kept})
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(handler, document), encoding="utf-8")
    sys.stdout.write(f"WROTE: {path} with {len(document.entries)} entries\n")
    return 0


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
        await registry.register_instance(
            interface=BASELINE_SERVICE, instance=HandlerFindingBaseline()
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
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Committed shrink-only baseline; a finding outside it fails.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Create the baseline when absent; afterwards only shrink it.",
    )
    args = parser.parse_args(argv)
    if args.write_baseline and args.baseline is None:
        parser.error("--write-baseline needs --baseline FILE")
    if container is None:
        container = create_container()
    inventory, writer = resolve_effects(container)
    validator_id = ValidatorFirstPartyRef.validator_id
    try:
        validator = ValidatorFirstPartyRef(root=args.root, inventory=inventory.handle)
        result = validator.validate(
            [args.root / path for path in args.targets] if args.targets else args.root
        )
        baseline_path = args.root / args.baseline if args.baseline is not None else None
        baseline = _load_baseline(baseline_path) if baseline_path is not None else None
        issues = tuple(result.issues)
        if baseline_path is not None:
            findings = _source_findings(issues, args.root)
            scope = (
                ModelFindingBaselineScope(
                    files=tuple(path.as_posix() for path in args.targets)
                )
                if args.targets
                else ModelFindingBaselineScope(dirs=("",))
            )
            handler = container.get_service(BASELINE_SERVICE)
            if args.write_baseline:
                return _write_baseline(
                    handler, baseline_path, baseline, findings, scope
                )
            report = handler.handle(
                ModelFindingBaselineInput(
                    hook_id=HOOK_ID,
                    findings=findings,
                    baseline=baseline,
                    scope=scope,
                )
            )
        else:
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
                    for issue in issues
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
