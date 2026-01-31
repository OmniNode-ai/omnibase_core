"""Import graph scanner using AST analysis.

Extracts import statements from Python files to build
a dependency graph for validation rules.

Related ticket: OMN-1771
"""

from __future__ import annotations

import ast
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelImportInfo(BaseModel):
    """Information about a single import statement."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module: str = Field(description="The imported module (e.g., 'os.path')")
    name: str | None = Field(
        default=None,
        description="The imported name (e.g., 'join' in 'from os.path import join')",
    )
    alias: str | None = Field(
        default=None,
        description="The alias if renamed (e.g., 'p' in 'import os.path as p')",
    )
    line_number: int = Field(description="Line number of the import")
    is_from_import: bool = Field(
        default=False,
        description="Whether this is a 'from X import Y' style import",
    )

    @property
    def full_import_path(self) -> str:
        """Get the full import path (module + name if from-import)."""
        if self.is_from_import and self.name:
            return f"{self.module}.{self.name}"
        return self.module


class ModelFileImports(BaseModel):
    """All imports from a single file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file_path: Path = Field(description="Path to the source file")
    imports: tuple[ModelImportInfo, ...] = Field(
        default_factory=tuple,
        description="All imports in this file",
    )
    parse_error: str | None = Field(
        default=None,
        description="Error message if file could not be parsed",
    )


class _ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts import statements."""

    def __init__(self) -> None:
        self.imports: list[ModelImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        for alias in node.names:
            self.imports.append(
                ModelImportInfo(
                    module=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=False,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        if node.module is None:
            # Relative import with no module (e.g., 'from . import X')
            module = ""
        else:
            module = node.module

        for alias in node.names:
            self.imports.append(
                ModelImportInfo(
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=True,
                )
            )
        self.generic_visit(node)


class ScannerImportGraph:
    """Scans Python files to extract import information.

    Uses AST analysis for accurate import extraction,
    handling both 'import X' and 'from X import Y' styles.
    """

    def scan_file(self, path: Path) -> ModelFileImports:
        """Extract imports from a single file.

        Args:
            path: Path to the Python file.

        Returns:
            ModelFileImports with all imports or an error message.
        """
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))

            visitor = _ImportVisitor()
            visitor.visit(tree)

            return ModelFileImports(
                file_path=path,
                imports=tuple(visitor.imports),
            )
        except SyntaxError as e:
            return ModelFileImports(
                file_path=path,
                parse_error=f"Syntax error at line {e.lineno}: {e.msg}",
            )
        except OSError as e:
            return ModelFileImports(
                file_path=path,
                parse_error=f"Could not read file: {e}",
            )

    def scan_files(self, files: list[Path]) -> dict[Path, ModelFileImports]:
        """Extract imports from multiple files.

        Args:
            files: List of file paths to scan.

        Returns:
            Dict mapping file paths to their imports.
        """
        return {path: self.scan_file(path) for path in files}

    def get_all_imports(
        self,
        file_imports: dict[Path, ModelFileImports],
    ) -> list[tuple[Path, ModelImportInfo]]:
        """Flatten all imports with their source files.

        Args:
            file_imports: Dict from scan_files().

        Returns:
            List of (file_path, import_info) tuples.
        """
        result: list[tuple[Path, ModelImportInfo]] = []

        for path, imports in file_imports.items():
            if imports.parse_error:
                continue
            for imp in imports.imports:
                result.append((path, imp))

        return result
