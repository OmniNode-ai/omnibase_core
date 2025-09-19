#!/usr/bin/env python3
"""
Static Import Validation for ONEX Architecture

Performs comprehensive static analysis of Python import statements to detect:
- Missing imported modules/classes/functions
- Broken relative imports
- Circular import dependencies
- Import statement syntax issues

This complements the existing validate-imports.py which tests actual module imports.
This script performs static analysis without executing any code.

Usage:
    python scripts/validate-imports-static.py
    python scripts/validate-imports-static.py --path src/
    python scripts/validate-imports-static.py --strict
    python scripts/validate-imports-static.py --check-circular

Pre-commit usage:
    python scripts/validate-imports-static.py --quiet
"""

import argparse
import ast
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class ImportIssue:
    """Represents an import validation issue."""

    def __init__(
        self,
        file_path: Path,
        line_number: int,
        issue_type: str,
        description: str,
        import_statement: str,
        severity: str = "error"
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.issue_type = issue_type
        self.description = description
        self.import_statement = import_statement
        self.severity = severity


class StaticImportValidator:
    """Static analysis validator for Python imports."""

    def __init__(self, base_path: Path, strict: bool = False, check_circular: bool = False):
        self.base_path = base_path.resolve()
        self.strict = strict
        self.check_circular = check_circular
        self.issues: List[ImportIssue] = []
        self.module_map: Dict[str, Path] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.python_files: List[Path] = []

        # If base_path is a single file, use its parent for module resolution
        if self.base_path.is_file():
            self.module_base = self.base_path.parent
            while self.module_base.name != "src" and self.module_base.parent != self.module_base:
                self.module_base = self.module_base.parent
            if self.module_base.name != "src":
                # Fallback to a reasonable directory structure
                self.module_base = self.base_path.parent
        else:
            self.module_base = self.base_path

        # Build module map
        self._build_module_map()

    def _build_module_map(self) -> None:
        """Build a map of available modules to their file paths."""
        # Handle both single files and directories
        if self.base_path.is_file():
            # Single file: use the module base for finding all modules
            search_path = self.module_base
            target_files = [self.base_path]
        else:
            # Directory: search within the directory
            search_path = self.base_path
            target_files = []

        # Find all Python files
        for py_file in search_path.rglob("*.py"):
            # Skip archived files and test files for module resolution
            if "/archived/" in str(py_file) or "__pycache__" in str(py_file):
                continue

            self.python_files.append(py_file)

            # Convert file path to module name
            try:
                rel_path = py_file.relative_to(self.module_base)
                if rel_path.name == "__init__.py":
                    # Package module
                    module_parts = rel_path.parent.parts
                else:
                    # Regular module
                    module_parts = rel_path.with_suffix("").parts

                if module_parts:
                    module_name = ".".join(module_parts)
                    self.module_map[module_name] = py_file

                    # Also add intermediate package names for __init__.py files
                    if rel_path.name == "__init__.py":
                        for i in range(1, len(module_parts) + 1):
                            partial_name = ".".join(module_parts[:i])
                            if partial_name not in self.module_map:
                                self.module_map[partial_name] = py_file.parent / "__init__.py"

            except ValueError:
                # Path is not relative to module_base, skip
                continue

        # If we're validating a single file, make sure it's in our files list
        if self.base_path.is_file() and self.base_path not in target_files:
            if self.base_path not in self.python_files:
                self.python_files.append(self.base_path)

    def _parse_file(self, file_path: Path) -> Optional[ast.AST]:
        """Parse a Python file and return its AST."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            self.issues.append(ImportIssue(
                file_path=file_path,
                line_number=e.lineno or 0,
                issue_type="syntax_error",
                description=f"Syntax error: {e.msg}",
                import_statement="",
                severity="error"
            ))
            return None
        except Exception as e:
            self.issues.append(ImportIssue(
                file_path=file_path,
                line_number=0,
                issue_type="parse_error",
                description=f"Failed to parse file: {e}",
                import_statement="",
                severity="error"
            ))
            return None

    def _resolve_relative_import(self, module: str, current_file: Path, level: int) -> Optional[str]:
        """Resolve a relative import to an absolute module name."""
        try:
            # Get current module path
            rel_path = current_file.relative_to(self.base_path)
            if rel_path.name == "__init__.py":
                current_parts = rel_path.parent.parts
            else:
                current_parts = rel_path.parent.parts

            # Go up 'level' directories
            if level > len(current_parts):
                return None

            base_parts = current_parts[:-level] if level > 0 else current_parts

            if module:
                return ".".join(base_parts + (module,))
            else:
                return ".".join(base_parts) if base_parts else None

        except ValueError:
            return None

    def _check_module_exists(self, module_name: str, from_name: Optional[str] = None) -> bool:
        """Check if a module exists in our codebase or is a standard library module."""
        # For project modules (starting with known project prefixes), only check our module map
        project_prefixes = ['omnibase_core', 'omnibase_spi', 'enums']
        if any(module_name.startswith(prefix) for prefix in project_prefixes):
            # Check if it's exactly in our module map
            if module_name in self.module_map:
                return True

            # Check if it's a submodule of something in our map, but be more precise
            for mapped_module in self.module_map:
                if module_name.startswith(mapped_module + "."):
                    # Additional check: the mapped module should be a proper parent
                    remaining = module_name[len(mapped_module) + 1:]
                    if "." not in remaining:
                        # Direct child module - check if it exists
                        return module_name in self.module_map
                    else:
                        # Multi-level submodule - need to check intermediate levels
                        parts = remaining.split(".")
                        current = mapped_module
                        for part in parts:
                            current = f"{current}.{part}"
                            if current not in self.module_map:
                                return False
                        return True

            return False  # Project module not found in our codebase

        # Check if it's in our module map (for non-project modules)
        if module_name in self.module_map:
            return True

        # Check if it's a submodule of something in our map (for non-project modules)
        for mapped_module in self.module_map:
            if module_name.startswith(mapped_module + "."):
                return True

        # Check if it's a built-in or standard library module
        try:
            import importlib.util
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                # Additional check: make sure it's not from our project directory
                # to avoid false positives from installed packages
                if spec.origin:
                    origin_path = Path(spec.origin)
                    try:
                        origin_path.relative_to(self.module_base)
                        # If we get here, it's in our project directory
                        return module_name in self.module_map
                    except ValueError:
                        # Not in our project directory, it's external
                        return True
                return True
        except (ImportError, ValueError, ModuleNotFoundError):
            pass

        # If we have a from_name, check if it could be an attribute
        if from_name and module_name in self.module_map:
            return True

        return False

    def _check_import_from_attributes(self, module_name: str, names: List[str], file_path: Path) -> List[str]:
        """Check if imported names exist in the target module."""
        missing_names = []

        # For our own modules, we can try to parse and check
        if module_name in self.module_map:
            target_file = self.module_map[module_name]
            target_ast = self._parse_file(target_file)

            if target_ast:
                # Extract available names from the target module
                available_names = set()

                for node in ast.walk(target_ast):
                    if isinstance(node, ast.ClassDef):
                        available_names.add(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        available_names.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                available_names.add(target.id)
                    elif isinstance(node, ast.ImportFrom):
                        # Add re-exported names
                        if node.names:
                            for alias in node.names:
                                if alias.name == "*":
                                    continue
                                name = alias.asname if alias.asname else alias.name
                                if name:
                                    available_names.add(name)

                # Check for missing names
                for name in names:
                    if name not in available_names and name != "*":
                        missing_names.append(name)

        return missing_names

    def _validate_import_statement(self, node: Union[ast.Import, ast.ImportFrom], file_path: Path) -> None:
        """Validate a single import statement."""
        try:
            if isinstance(node, ast.Import):
                # Handle 'import module' statements
                for alias in node.names:
                    module_name = alias.name
                    if not self._check_module_exists(module_name):
                        self.issues.append(ImportIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="missing_module",
                            description=f"Module '{module_name}' not found",
                            import_statement=f"import {module_name}",
                            severity="error"
                        ))

            elif isinstance(node, ast.ImportFrom):
                # Handle 'from module import name' statements
                module_name = node.module
                level = node.level

                if level > 0:
                    # Relative import
                    resolved_module = self._resolve_relative_import(module_name or "", file_path, level)
                    if resolved_module is None:
                        self.issues.append(ImportIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="invalid_relative_import",
                            description=f"Invalid relative import level {level}",
                            import_statement=f"from {'.' * level}{module_name or ''} import ...",
                            severity="error"
                        ))
                        return
                    module_name = resolved_module

                if module_name and not self._check_module_exists(module_name):
                    imported_names = [alias.name for alias in node.names if alias.name != "*"]
                    self.issues.append(ImportIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="missing_module",
                        description=f"Module '{module_name}' not found",
                        import_statement=f"from {module_name} import {', '.join(imported_names)}",
                        severity="error"
                    ))

                # Check if imported names exist in the module
                elif module_name and self.strict:
                    imported_names = [alias.name for alias in node.names if alias.name != "*"]
                    missing_names = self._check_import_from_attributes(module_name, imported_names, file_path)

                    for missing_name in missing_names:
                        self.issues.append(ImportIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="missing_import_name",
                            description=f"Name '{missing_name}' not found in module '{module_name}'",
                            import_statement=f"from {module_name} import {missing_name}",
                            severity="warning" if not self.strict else "error"
                        ))

                # Build dependency graph for circular import detection
                if self.check_circular and module_name:
                    try:
                        current_rel = file_path.relative_to(self.base_path)
                        if current_rel.name == "__init__.py":
                            current_module = ".".join(current_rel.parent.parts)
                        else:
                            current_module = ".".join(current_rel.with_suffix("").parts)

                        self.dependency_graph[current_module].add(module_name)
                    except ValueError:
                        pass

        except Exception as e:
            self.issues.append(ImportIssue(
                file_path=file_path,
                line_number=getattr(node, 'lineno', 0),
                issue_type="validation_error",
                description=f"Error validating import: {e}",
                import_statement="",
                severity="warning"
            ))

    def _detect_circular_imports(self) -> None:
        """Detect circular import dependencies."""
        def has_cycle(start: str, visited: Set[str], rec_stack: Set[str]) -> Optional[List[str]]:
            """DFS to detect cycles in dependency graph."""
            visited.add(start)
            rec_stack.add(start)

            for neighbor in self.dependency_graph.get(start, set()):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, rec_stack)
                    if cycle:
                        return [start] + cycle
                elif neighbor in rec_stack:
                    return [start, neighbor]

            rec_stack.remove(start)
            return None

        visited = set()
        for module in self.dependency_graph:
            if module not in visited:
                cycle = has_cycle(module, visited, set())
                if cycle:
                    # Find a file to report the issue against
                    report_file = None
                    for py_file in self.python_files:
                        if cycle[0] in str(py_file):
                            report_file = py_file
                            break

                    if not report_file:
                        report_file = self.python_files[0] if self.python_files else Path(".")

                    self.issues.append(ImportIssue(
                        file_path=report_file,
                        line_number=0,
                        issue_type="circular_import",
                        description=f"Circular import detected: {' -> '.join(cycle)}",
                        import_statement="",
                        severity="warning"
                    ))

    def validate_file(self, file_path: Path) -> None:
        """Validate imports in a single Python file."""
        # Skip archived files
        if "/archived/" in str(file_path):
            return

        tree = self._parse_file(file_path)
        if tree is None:
            return

        # Find all import statements
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._validate_import_statement(node, file_path)

    def validate_all(self) -> bool:
        """Validate all Python files in the base path."""
        print(f"🔍 Static Import Validation - {self.base_path}")
        print("=" * 50)

        # Determine which files to validate
        if self.base_path.is_file():
            files_to_validate = [self.base_path]
        else:
            files_to_validate = self.python_files

        for py_file in files_to_validate:
            self.validate_file(py_file)

        if self.check_circular:
            print("🔄 Checking for circular imports...")
            self._detect_circular_imports()

        return len([issue for issue in self.issues if issue.severity == "error"]) == 0

    def print_results(self, quiet: bool = False) -> bool:
        """Print validation results."""
        if not self.issues:
            if not quiet:
                print("\n✅ Static import validation: All imports valid")
            return True

        # Group issues by severity
        errors = [issue for issue in self.issues if issue.severity == "error"]
        warnings = [issue for issue in self.issues if issue.severity == "warning"]

        if not quiet:
            print(f"\n📊 Static Import Validation Results:")
            print("=" * 50)

            for issue in errors + warnings:
                severity_icon = "❌" if issue.severity == "error" else "⚠️"
                rel_path = issue.file_path.relative_to(self.base_path) if self.base_path in issue.file_path.parents else issue.file_path

                print(f"{severity_icon} {rel_path}:{issue.line_number}")
                print(f"   {issue.issue_type}: {issue.description}")
                if issue.import_statement:
                    print(f"   Import: {issue.import_statement}")
                print()

            print(f"Results: {len(self.issues)} issues found ({len(errors)} errors, {len(warnings)} warnings)")

        if errors:
            if not quiet:
                print(f"\n🚫 {len(errors)} import errors need to be fixed")
            return False
        else:
            if warnings and not quiet:
                print(f"\n✅ No import errors (but {len(warnings)} warnings)")
            elif not quiet:
                print("\n✅ All imports valid!")
            return True


def main() -> int:
    """Main validation entry point."""
    parser = argparse.ArgumentParser(description="Validate Python imports statically")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="Path to validate (default: current directory)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (check if imported names exist)"
    )
    parser.add_argument(
        "--check-circular",
        action="store_true",
        help="Check for circular import dependencies"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (for pre-commit hooks)"
    )

    args = parser.parse_args()

    # Find src directory if we're in project root
    if args.path == Path(".") and (Path("src").exists()):
        args.path = Path("src")

    if not args.path.exists():
        print(f"❌ Path does not exist: {args.path}")
        return 1

    validator = StaticImportValidator(
        base_path=args.path,
        strict=args.strict,
        check_circular=args.check_circular
    )

    # Run validation
    success = validator.validate_all()

    # Print results
    success = validator.print_results(quiet=args.quiet)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())