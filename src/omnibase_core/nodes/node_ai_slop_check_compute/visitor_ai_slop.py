# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST docstring matching with core's three suppression locations."""

from __future__ import annotations

import ast

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.nodes.node_ai_slop_check_compute.matcher_ai_slop import (
    SUPPRESSION_MARKER,
    CompiledRule,
    docstring_message,
    make_finding,
)


class AiSlopVisitor(ast.NodeVisitor):
    """Check module, class, function and async function docstring lines."""

    def __init__(
        self, path: str, source_lines: list[str], rules: dict[str, CompiledRule]
    ) -> None:
        self.path = path
        self.source_lines = source_lines
        self.rules = rules
        self.findings: list[ModelValidationFinding] = []

    def _check_docstring(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module,
        def_lineno: int,
    ) -> None:
        docstring = ast.get_docstring(node, clean=False)
        if not docstring or not node.body:
            return
        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr) or not isinstance(
            first_stmt.value, ast.Constant
        ):
            return
        if not isinstance(first_stmt.value.value, str):
            return
        docstring_lineno = first_stmt.value.lineno
        for line in (def_lineno, docstring_lineno, def_lineno - 1):
            if (
                1 <= line <= len(self.source_lines)
                and SUPPRESSION_MARKER in self.source_lines[line - 1]
            ):
                return
        for offset, doc_line in enumerate(docstring.splitlines()):
            for name, (pattern, rule) in self.rules.items():
                match_fn = pattern.search if name == "md_separator" else pattern.match
                if match_fn(doc_line):
                    self.findings.append(
                        make_finding(
                            self.path,
                            docstring_lineno + offset,
                            name,
                            rule.severity,
                            docstring_message(name, doc_line),
                        )
                    )

    def visit_Module(self, node: ast.Module) -> None:
        self._check_docstring(node, 1)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_docstring(node, node.lineno)
        self.generic_visit(node)
