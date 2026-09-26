# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Static module index used by the Pydantic ``extra=forbid`` gate."""

import ast
from pathlib import Path


class ModuleIndex:
    """Parsed view of one module's classes and import bindings."""

    __slots__ = ("classes", "imports", "module", "path")

    def __init__(self, path: Path, module: str, tree: ast.Module) -> None:
        self.path = path
        self.module = module
        self.classes: dict[str, ast.ClassDef] = {}
        self.imports: dict[str, tuple[str, str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.setdefault(node.name, node)

        package = module.rsplit(".", 1)[0] if "." in module else ""
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[alias.asname or alias.name.split(".")[0]] = (
                        alias.name,
                        "",
                    )
            elif isinstance(node, ast.ImportFrom):
                source = _absolute_import_module(node, package)
                if source is None:
                    continue
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = (source, alias.name)


def _absolute_import_module(node: ast.ImportFrom, package: str) -> str | None:
    if not node.level:
        return node.module
    parts = package.split(".") if package else []
    if node.level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (node.level - 1)]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base) if base else None


__all__ = ["ModuleIndex"]
