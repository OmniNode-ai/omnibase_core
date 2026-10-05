# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure AI-slop validation preserving core script findings and messages."""

from __future__ import annotations

import ast
from pathlib import PurePath

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_ai_slop_check_compute.matcher_ai_slop import (
    VALIDATOR_ID,
    check_lines,
    compile_rules,
    make_finding,
)
from omnibase_core.nodes.node_ai_slop_check_compute.visitor_ai_slop import AiSlopVisitor


class NodeAiSlopCheckCompute:
    """Compute a canonical report over explicit sources and typed rules."""

    def handle(self, request: ModelAiSlopCheckInput) -> ModelValidationReport:
        docstring_rules = compile_rules(request.rules, docstrings=True)
        if not docstring_rules:
            docstring_rules = compile_rules(
                request.fallback_docstring_rules, docstrings=True
            )
        line_rules = compile_rules(request.rules, docstrings=False)
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            suffix = PurePath(file.path).suffix
            if suffix not in (".py", ".md"):
                continue
            file_findings: list[ModelValidationFinding] = []
            lines = file.source.splitlines()
            if suffix == ".py":
                try:
                    tree = ast.parse(file.source, filename=file.path)
                except SyntaxError as exc:
                    findings.append(
                        make_finding(
                            file.path,
                            exc.lineno or 0,
                            "syntax_error",
                            "ERROR",
                            f"Syntax error: {exc.msg}",
                        )
                    )
                    continue
                visitor = AiSlopVisitor(file.path, lines, docstring_rules)
                visitor.visit(tree)
                file_findings.extend(visitor.findings)
            file_findings.extend(check_lines(file.path, lines, line_rules))
            findings.extend(
                sorted(
                    file_findings,
                    key=lambda f: int((f.location or "0").rsplit(":", 1)[-1]),
                )
            )
        embedded = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for finding in findings
            if request.report
            or finding.evidence["script_severity"] in ("ERROR", "WARNING")
        )
        return ModelValidationReport.from_findings(
            findings=embedded,
            request=ModelValidationRequestRef(
                profile="strict" if request.strict else "default"
            ),
            validators_run=(VALIDATOR_ID,),
        )
