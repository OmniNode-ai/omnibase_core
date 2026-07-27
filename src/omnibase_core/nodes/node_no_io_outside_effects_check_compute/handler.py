# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoIoOutsideEffectsCheckCompute — archetype-purity COMPUTE handler.

The single WS8 archetype-purity invariant ``no-io-outside-effects`` (OMN-14662,
seeded by OMN-14694, epic OMN-2362). It collapses six point-lints into ONE
rule: **I/O and direct adapter/bus instantiation are permitted only in EFFECT
nodes.** Every ``.py`` module co-located with a non-EFFECT contract (COMPUTE,
REDUCER, ORCHESTRATOR) must be pure.

Unlike the universal OMN-14659 lints (which AST-scan every file blindly), this
rule keys off each node's declared archetype: it flags a forbidden I/O surface
only inside ``.py`` modules that sit in a **non-EFFECT** node package. EFFECT
packages are where I/O legitimately lives and are never scanned.

Architecture: COMPUTE node — pure, deterministic, no I/O, on the def-B
``handle(request) -> response`` shape (OMN-14355). Content arrives via explicit
``(path, source)`` pairs on the request — an intermixed set of ``contract.yaml``
files (the archetype seam) and ``.py`` modules. The filesystem walk + read
happens at the paired EFFECT boundary (``node_source_file_gather_effect``) or
the CLI runtime, never inside this handler.

Seam: a node directory is a **non-EFFECT** package when its ``contract.yaml``
does NOT declare ``effect`` (via ``node_type`` or ``descriptor.node_archetype``
— see :func:`.archetype_resolver.resolve_archetype`). Fail-closed: a contract
that names no recognised archetype is treated as non-EFFECT and scanned. Only
``.py`` files whose parent directory equals such a contract's directory are
scanned for forbidden I/O surfaces (see :class:`.visitor_io.IoSurfaceVisitor`).

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork. This node emits ``FAIL`` (forbidden I/O surface in a non-EFFECT
package) and ``ERROR`` (unparseable contract YAML or unparseable Python)
findings.

Ticket: OMN-14694 (WS8 seed) → OMN-14662 (archetype-purity collapse).
"""

from __future__ import annotations

import ast
from typing import Final, Literal

import yaml

from omnibase_core.enums.enum_node_archetype import EnumNodeArchetype
from omnibase_core.models.nodes.no_io_outside_effects_check.model_no_io_outside_effects_check_input import (
    ModelNoIoOutsideEffectsCheckInput,
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
from omnibase_core.nodes.node_no_io_outside_effects_check_compute.archetype_resolver import (
    CONTRACT_FILENAME,
    node_dir_of,
    resolve_archetype,
)
from omnibase_core.nodes.node_no_io_outside_effects_check_compute.visitor_io import (
    VALIDATOR_ID,
    IoSurfaceVisitor,
)

__all__ = ["NodeNoIoOutsideEffectsCheckCompute"]

# This node reports FAIL/ERROR findings at face value — "default" is the
# precedence profile that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoIoOutsideEffectsCheckCompute:
    """COMPUTE handler: flag forbidden I/O surfaces inside non-EFFECT node packages."""

    def handle(
        self, request: ModelNoIoOutsideEffectsCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        findings: list[ModelValidationFinding] = []

        contracts, python_files = self._partition(request.files)

        # 1. Resolve the archetype seam: which node directories are non-EFFECT.
        non_effect_dirs, contract_errors = self._non_effect_dirs(contracts)
        findings.extend(contract_errors)

        # 2. Scan only the Python modules that live in a non-EFFECT package.
        for file in python_files:
            if node_dir_of(file.path) in non_effect_dirs:
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
    def _non_effect_dirs(
        contracts: list[ModelSourceFile],
    ) -> tuple[set[str], list[ModelValidationFinding]]:
        """Return the set of non-EFFECT node dirs + ERROR findings for bad YAML.

        Fail-closed: any contract whose archetype is not EFFECT (including an
        unresolved archetype) contributes its directory to the scan set — only
        a contract that positively declares EFFECT is exempted.
        """
        non_effect_dirs: set[str] = set()
        errors: list[ModelValidationFinding] = []
        for contract in contracts:
            try:
                archetype = resolve_archetype(contract.source)
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
            if archetype is not EnumNodeArchetype.EFFECT:
                non_effect_dirs.add(node_dir_of(contract.path))
        return non_effect_dirs, errors

    @staticmethod
    def _scan_python(path: str, source: str) -> list[ModelValidationFinding]:
        """AST-scan one non-EFFECT-package module for forbidden I/O surfaces."""
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
        visitor = IoSurfaceVisitor(path, source.splitlines())
        visitor.visit(tree)
        return visitor.findings
