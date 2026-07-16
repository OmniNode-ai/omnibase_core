# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoDbInOrchestratorCheckCompute — no-DB-in-orchestrator COMPUTE handler.

The first WS8 *archetype-specific* layering rule (OMN-14694, epic OMN-2362).
Unlike the universal OMN-14659 lints (which AST-scan every file blindly), this
rule keys off each node's declared archetype: it only flags database-driver
imports inside ``.py`` modules that sit in an ORCHESTRATOR node package.

Architecture: COMPUTE node — pure, deterministic, no I/O, on the def-B
``handle(request) -> response`` shape (OMN-14355). Content arrives via explicit
``(path, source)`` pairs on the request — an intermixed set of ``contract.yaml``
files (the archetype seam) and ``.py`` modules. The filesystem walk + read
happens at the paired EFFECT boundary (``node_source_file_gather_effect``) or
the CLI runtime, never inside this handler. This is a synchronous
typed-request handler on the def-B shape — no event-envelope import, not the
event-driven shape.

Seam: a node directory is an ORCHESTRATOR package when its ``contract.yaml``
declares ``node_type: orchestrator`` OR ``descriptor.node_archetype:
orchestrator`` (see :mod:`.archetype_resolver`). Only ``.py`` files whose
parent directory equals such a contract's directory are DB-scanned.

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork. This node emits ``FAIL`` (DB driver import in an orchestrator
package) and ``ERROR`` (unparseable contract YAML or unparseable Python)
findings.

Ticket: OMN-14694 (WS8 canary — no-db-in-orchestrator).
"""

from __future__ import annotations

import ast
from typing import Final, Literal

import yaml

from omnibase_core.models.nodes.no_db_in_orchestrator_check.model_no_db_in_orchestrator_check_input import (
    ModelNoDbInOrchestratorCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_db_in_orchestrator_check_compute.archetype_resolver import (
    CONTRACT_FILENAME,
    contract_declares_orchestrator,
    node_dir_of,
)
from omnibase_core.nodes.node_no_db_in_orchestrator_check_compute.visitor_db_io import (
    VALIDATOR_ID,
    DbIoImportVisitor,
)

__all__ = ["NodeNoDbInOrchestratorCheckCompute"]

# This node reports FAIL/ERROR findings at face value — "default" is the
# precedence profile that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoDbInOrchestratorCheckCompute:
    """COMPUTE handler: flag DB-driver imports inside ORCHESTRATOR node packages."""

    def handle(
        self, request: ModelNoDbInOrchestratorCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        findings: list[ModelValidationFinding] = []

        contracts, python_files = self._partition(request.files)

        # 1. Resolve the archetype seam: which node directories are orchestrators.
        orchestrator_dirs, contract_errors = self._orchestrator_dirs(contracts)
        findings.extend(contract_errors)

        # 2. DB-scan only the Python modules that live in an orchestrator package.
        for file in python_files:
            if node_dir_of(file.path) in orchestrator_dirs:
                findings.extend(self._scan_python(file.path, file.source))

        embedded_findings = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for finding in findings
        )
        return ModelValidationReport.from_findings(
            findings=embedded_findings,
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _partition(
        files: list[ModelSourceFile],
    ) -> tuple[list[ModelSourceFile], list[ModelSourceFile]]:
        """Split the intermixed input into (contract.yaml files, .py files)."""
        contracts: list[ModelSourceFile] = []
        python_files: list[ModelSourceFile] = []
        for file in files:
            name = file.path.replace("\\", "/").rsplit("/", 1)[-1]
            if name == CONTRACT_FILENAME:
                contracts.append(file)
            elif name.endswith(".py"):
                python_files.append(file)
        return contracts, python_files

    @staticmethod
    def _orchestrator_dirs(
        contracts: list[ModelSourceFile],
    ) -> tuple[set[str], list[ModelValidationFinding]]:
        """Return the set of orchestrator node dirs + ERROR findings for bad YAML."""
        orchestrator_dirs: set[str] = set()
        errors: list[ModelValidationFinding] = []
        for contract in contracts:
            try:
                is_orchestrator = contract_declares_orchestrator(contract.source)
            except yaml.YAMLError as exc:
                errors.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="ERROR",
                        location=contract.path,
                        message=(
                            f"{contract.path}: unparseable contract.yaml — cannot "
                            f"determine node archetype: {exc}"
                        ),
                        remediation=None,
                    )
                )
                continue
            if is_orchestrator:
                orchestrator_dirs.add(node_dir_of(contract.path))
        return orchestrator_dirs, errors

    @staticmethod
    def _scan_python(path: str, source: str) -> list[ModelValidationFinding]:
        """AST-scan one orchestrator-package module for DB-driver imports."""
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            return [
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    location=path,
                    message=f"{path}: SyntaxError: {exc}",
                    remediation=None,
                )
            ]
        visitor = DbIoImportVisitor(path, source.splitlines())
        visitor.visit(tree)
        return visitor.findings
