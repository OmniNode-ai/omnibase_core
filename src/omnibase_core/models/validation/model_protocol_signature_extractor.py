"""
Protocol Signature Extractor.

AST NodeVisitor for extracting protocol signatures for comparison.
"""

from __future__ import annotations

import ast


class ModelProtocolSignatureExtractor(ast.NodeVisitor):
    """Extracts protocol signature for comparison."""

    def __init__(self) -> None:
        self.methods: list[str] = []
        self.imports: list[str] = []
        self.class_name = ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition."""
        # Check if this class actually inherits from Protocol or typing.Protocol
        is_protocol = False
        for base in node.bases:
            if (isinstance(base, ast.Name) and base.id == "Protocol") or (
                isinstance(base, ast.Attribute) and base.attr == "Protocol"
            ):
                is_protocol = True
                break

        if is_protocol:
            self.class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Extract method signature
                    args = [arg.arg for arg in item.args.args if arg.arg != "self"]
                    returns = ast.unparse(item.returns) if item.returns else "None"
                    signature = f"{item.name}({', '.join(args)}) -> {returns}"
                    self.methods.append(signature)
                elif isinstance(item, ast.Expr) and isinstance(
                    item.value,
                    ast.Constant,
                ):
                    # Skip docstrings and ellipsis
                    continue
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Extract imports."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Extract from imports."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")


# Export the class
__all__ = ["ModelProtocolSignatureExtractor"]
