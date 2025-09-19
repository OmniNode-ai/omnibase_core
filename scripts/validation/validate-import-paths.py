#!/usr/bin/env python3
"""
Import path validation script for ONEX pre-commit hooks.

This script validates that all import statements in Python files can be resolved
to existing modules, preventing runtime import errors.

Key Features:
- AST-based import extraction (handles all Python import syntax)
- Internal vs external import validation
- Caching for performance optimization
- Integration with git diff for incremental validation
- Detailed error reporting with line numbers

Usage:
    python validate-import-paths.py [files...] [options]

Pre-commit integration:
    - id: validate-import-resolution
      entry: poetry run python scripts/validation/validate-import-paths.py
      language: system
      pass_filenames: true
      files: ^src/.*\\.py$
"""

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed


class ImportInfo:
    """Container for import statement information."""

    def __init__(self, module: str, line: int, import_type: str,
                 name: Optional[str] = None, alias: Optional[str] = None,
                 level: int = 0):
        self.module = module
        self.line = line
        self.import_type = import_type  # 'import' or 'from_import'
        self.name = name  # For 'from module import name'
        self.alias = alias
        self.level = level  # For relative imports


class ImportFailure:
    """Container for import validation failure information."""

    def __init__(self, file_path: str, import_info: ImportInfo, error: str):
        self.file_path = file_path
        self.import_info = import_info
        self.error = error

    def __repr__(self) -> str:
        return f"ImportFailure({self.file_path}:{self.import_info.line} -> {self.import_info.module})"


class ImportExtractor(ast.NodeVisitor):
    """AST visitor to extract import statements from Python source code."""

    def __init__(self):
        self.imports: List[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import module' statements."""
        for alias in node.names:
            self.imports.append(ImportInfo(
                module=alias.name,
                line=node.lineno,
                import_type='import',
                alias=alias.asname
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from module import name' statements."""
        if node.module is None and node.level == 0:
            # Skip malformed imports like 'from import something'
            return

        base_module = node.module or ''

        for alias in node.names:
            # For 'from module import *', track the module import
            if alias.name == '*':
                self.imports.append(ImportInfo(
                    module=base_module,
                    line=node.lineno,
                    import_type='from_import',
                    name='*',
                    level=node.level
                ))
            else:
                self.imports.append(ImportInfo(
                    module=base_module,
                    line=node.lineno,
                    import_type='from_import',
                    name=alias.name,
                    alias=alias.asname,
                    level=node.level
                ))


class ImportCache:
    """Caching mechanism for import validation results."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or Path('.import_validation_cache.json')
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()
        self.dirty = False

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load cached import results from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Validate cache structure
                    if isinstance(cache_data, dict):
                        return cache_data
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def save_cache(self) -> None:
        """Save cache to disk if dirty."""
        if self.dirty:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
                self.dirty = False
            except IOError:
                pass  # Silently fail cache saves

    def get_cached_result(self, module: str, file_mtime: float) -> Optional[bool]:
        """Get cached import validation result if still valid."""
        if module in self.cache:
            cache_entry = self.cache[module]
            cached_mtime = cache_entry.get('mtime', 0)
            if cached_mtime >= file_mtime:
                return cache_entry.get('valid')
        return None

    def cache_result(self, module: str, valid: bool, file_mtime: float) -> None:
        """Cache an import validation result."""
        self.cache[module] = {
            'valid': valid,
            'mtime': file_mtime,
            'timestamp': time.time()
        }
        self.dirty = True

    def clear_old_entries(self, max_age_days: int = 7) -> None:
        """Clear cache entries older than max_age_days."""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        old_keys = [
            key for key, value in self.cache.items()
            if value.get('timestamp', 0) < cutoff_time
        ]
        for key in old_keys:
            del self.cache[key]
        if old_keys:
            self.dirty = True


class ImportValidator:
    """Main import validation engine."""

    def __init__(self, project_root: Path, use_cache: bool = True, fast_fail: bool = False):
        self.project_root = project_root.resolve()
        self.use_cache = use_cache
        self.fast_fail = fast_fail
        self.cache = ImportCache() if use_cache else None
        self.failures: List[ImportFailure] = []

        # Performance tracking
        self.stats = {
            'files_processed': 0,
            'imports_checked': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        # Standard library modules (partial list for common ones)
        self.stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing',
            'collections', 'itertools', 'functools', 'operator', 're',
            'urllib', 'http', 'email', 'html', 'xml', 'sqlite3', 'hashlib',
            'uuid', 'random', 'math', 'statistics', 'decimal', 'fractions',
            'asyncio', 'concurrent', 'threading', 'multiprocessing',
            'subprocess', 'signal', 'socket', 'ssl', 'logging', 'argparse'
        }

    def validate_files(self, file_paths: List[Path]) -> bool:
        """Validate imports in multiple files."""
        self.failures.clear()

        for file_path in file_paths:
            if not self.validate_file(file_path):
                if self.fast_fail:
                    break

        # Save cache after processing
        if self.cache:
            self.cache.save_cache()

        return len(self.failures) == 0

    def validate_file(self, file_path: Path) -> bool:
        """Validate imports in a single Python file."""
        try:
            file_path = file_path.resolve()
            self.stats['files_processed'] += 1

            # Read and parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                self.failures.append(ImportFailure(
                    str(file_path),
                    ImportInfo('PARSE_ERROR', e.lineno or 0, 'error'),
                    f"Syntax error: {e.msg}"
                ))
                return False

            # Extract imports
            extractor = ImportExtractor()
            extractor.visit(tree)

            # Validate each import
            file_mtime = file_path.stat().st_mtime
            for import_info in extractor.imports:
                self.stats['imports_checked'] += 1

                if not self._validate_import(import_info, file_path, file_mtime):
                    if self.fast_fail:
                        return False

            return True

        except Exception as e:
            self.failures.append(ImportFailure(
                str(file_path),
                ImportInfo('FILE_ERROR', 0, 'error'),
                f"Failed to process file: {e}"
            ))
            return False

    def _validate_import(self, import_info: ImportInfo, source_file: Path,
                        file_mtime: float) -> bool:
        """Validate a single import statement."""

        # Handle relative imports
        if import_info.level > 0:
            return self._validate_relative_import(import_info, source_file)

        module_name = import_info.module

        # Check cache first
        if self.cache:
            cached_result = self.cache.get_cached_result(module_name, file_mtime)
            if cached_result is not None:
                self.stats['cache_hits'] += 1
                if not cached_result:
                    self._add_failure(import_info, source_file, "Cached failure")
                return cached_result
            self.stats['cache_misses'] += 1

        # Validate the import
        is_valid = self._resolve_import(module_name)

        # Cache the result
        if self.cache:
            self.cache.cache_result(module_name, is_valid, file_mtime)

        if not is_valid:
            self._add_failure(import_info, source_file, "Import resolution failed")

        return is_valid

    def _validate_relative_import(self, import_info: ImportInfo, source_file: Path) -> bool:
        """Validate relative imports (from . import or from .. import)."""
        try:
            # Calculate the package path for the source file
            rel_source = source_file.relative_to(self.project_root)

            # Go up 'level' directories from the source file
            package_path = rel_source.parent
            for _ in range(import_info.level - 1):
                package_path = package_path.parent

            # If module is specified, add it to the path
            if import_info.module:
                target_module_path = package_path / import_info.module.replace('.', '/')
            else:
                target_module_path = package_path

            # Check if target exists as file or package
            target_file = self.project_root / target_module_path.with_suffix('.py')
            target_package = self.project_root / target_module_path / '__init__.py'

            if target_file.exists() or target_package.exists():
                return True

            self._add_failure(import_info, source_file,
                            f"Relative import target not found: {target_module_path}")
            return False

        except Exception as e:
            self._add_failure(import_info, source_file,
                            f"Error validating relative import: {e}")
            return False

    def _resolve_import(self, module_name: str) -> bool:
        """Resolve a module import to check if it exists."""

        # Check if it's a standard library module
        root_module = module_name.split('.')[0]
        if root_module in self.stdlib_modules:
            return True

        # Try to find the module using importlib
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                return True
        except (ImportError, ValueError, ModuleNotFoundError):
            pass

        # For internal modules, check file system directly
        if module_name.startswith('omnibase_core'):
            return self._validate_internal_module(module_name)

        # For external modules, try a limited import attempt
        try:
            __import__(module_name)
            return True
        except ImportError:
            pass

        return False

    def _validate_internal_module(self, module_name: str) -> bool:
        """Validate internal omnibase_core module paths."""

        # Convert module name to file path
        # e.g., omnibase_core.models.core.model_schema_value ->
        #       src/omnibase_core/models/core/model_schema_value.py

        module_parts = module_name.split('.')
        if module_parts[0] != 'omnibase_core':
            return True  # Not our responsibility

        # Check in active src directory
        src_path = self.project_root / 'src'
        module_path = src_path
        for part in module_parts:
            module_path = module_path / part

        # Check as Python file
        py_file = module_path.with_suffix('.py')
        if py_file.exists():
            return True

        # Check as package (directory with __init__.py)
        init_file = module_path / '__init__.py'
        if init_file.exists():
            return True

        # Check if it exists in archived (this should be flagged as an issue)
        archived_path = self.project_root / 'archived' / 'src'
        archived_module_path = archived_path
        for part in module_parts:
            archived_module_path = archived_module_path / part

        archived_py_file = archived_module_path.with_suffix('.py')
        if archived_py_file.exists():
            # This is an error - importing from archived code
            return False

        return False

    def _add_failure(self, import_info: ImportInfo, source_file: Path, error: str) -> None:
        """Add an import failure to the results."""
        self.failures.append(ImportFailure(str(source_file), import_info, error))

    def generate_report(self) -> str:
        """Generate a human-readable validation report."""
        if not self.failures:
            report_lines = [
                "✅ All imports validated successfully",
                f"📊 Stats: {self.stats['files_processed']} files, "
                f"{self.stats['imports_checked']} imports checked"
            ]
            if self.cache:
                cache_hit_rate = (self.stats['cache_hits'] /
                                (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
                                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0)
                report_lines.append(f"🎯 Cache hit rate: {cache_hit_rate:.1f}%")

            return "\n".join(report_lines)

        report_lines = [
            f"❌ Found {len(self.failures)} import issues:",
            ""
        ]

        # Group failures by file
        by_file: Dict[str, List[ImportFailure]] = {}
        for failure in self.failures:
            file_path = failure.file_path
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(failure)

        for file_path, failures in sorted(by_file.items()):
            # Make path relative to project root for cleaner output
            try:
                rel_path = Path(file_path).relative_to(self.project_root)
                display_path = str(rel_path)
            except ValueError:
                display_path = file_path

            report_lines.append(f"📁 {display_path}:")

            for failure in sorted(failures, key=lambda f: f.import_info.line):
                line_num = failure.import_info.line
                module_name = failure.import_info.module
                error_msg = failure.error

                report_lines.append(f"  ❌ Line {line_num}: {module_name} - {error_msg}")

            report_lines.append("")

        # Add summary statistics
        report_lines.extend([
            f"📊 Validation Statistics:",
            f"  Files processed: {self.stats['files_processed']}",
            f"  Imports checked: {self.stats['imports_checked']}",
            f"  Failures found: {len(self.failures)}"
        ])

        if self.cache:
            cache_hit_rate = (self.stats['cache_hits'] /
                            (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
                            if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0)
            report_lines.append(f"  Cache hit rate: {cache_hit_rate:.1f}%")

        return "\n".join(report_lines)


def get_git_modified_files(project_root: Path) -> List[Path]:
    """Get list of Python files modified in the current git commit."""
    try:
        # Get staged files (for pre-commit hook)
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )

        files = []
        for line in result.stdout.strip().split('\n'):
            if line and line.endswith('.py') and line.startswith('src/'):
                file_path = project_root / line
                if file_path.exists():
                    files.append(file_path)

        return files

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: return empty list, caller should handle
        return []


def find_python_files(root_path: Path, patterns: List[str]) -> List[Path]:
    """Find Python files matching given patterns."""
    files = []

    for pattern in patterns:
        if '*' in pattern:
            # Handle glob patterns
            files.extend(root_path.glob(pattern))
        else:
            # Handle specific files
            file_path = root_path / pattern
            if file_path.exists() and file_path.suffix == '.py':
                files.append(file_path)

    # Remove duplicates and ensure all are Python files
    unique_files = []
    seen = set()
    for file_path in files:
        resolved_path = file_path.resolve()
        if (resolved_path not in seen and
            resolved_path.suffix == '.py' and
            resolved_path.exists()):
            unique_files.append(resolved_path)
            seen.add(resolved_path)

    return unique_files


def main() -> int:
    """Main entry point for the import validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Python import statements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate specific files
  python validate-import-paths.py src/module.py src/other.py

  # Validate all files in src/
  python validate-import-paths.py src/**/*.py

  # Use with pre-commit (validates staged files)
  python validate-import-paths.py --git-staged

  # Fast fail mode (stop on first error)
  python validate-import-paths.py --fast-fail src/**/*.py
        """
    )

    parser.add_argument(
        'files',
        nargs='*',
        help='Python files to validate (supports glob patterns)'
    )

    parser.add_argument(
        '--git-staged',
        action='store_true',
        help='Validate only git staged files (for pre-commit hooks)'
    )

    parser.add_argument(
        '--fast-fail',
        action='store_true',
        help='Stop validation on first error'
    )

    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable result caching'
    )

    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Project root directory (default: current directory)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Determine project root
    project_root = args.project_root.resolve()
    if not project_root.exists():
        print(f"❌ Project root does not exist: {project_root}", file=sys.stderr)
        return 1

    # Determine files to validate
    if args.git_staged:
        files_to_validate = get_git_modified_files(project_root)
        if not files_to_validate:
            if args.verbose:
                print("ℹ️  No staged Python files found, checking all src files")
            files_to_validate = find_python_files(project_root, ['src/**/*.py'])
    elif args.files:
        files_to_validate = find_python_files(project_root, args.files)
    else:
        # Default: validate all Python files in src/
        files_to_validate = find_python_files(project_root, ['src/**/*.py'])

    if not files_to_validate:
        if args.verbose:
            print("ℹ️  No Python files found to validate")
        return 0

    if args.verbose:
        print(f"🔍 Validating {len(files_to_validate)} Python files...")

    # Create validator and run validation
    validator = ImportValidator(
        project_root=project_root,
        use_cache=not args.no_cache,
        fast_fail=args.fast_fail
    )

    start_time = time.time()
    success = validator.validate_files(files_to_validate)
    end_time = time.time()

    # Generate and print report
    report = validator.generate_report()
    print(report)

    if args.verbose:
        print(f"\n⏱️  Validation completed in {end_time - start_time:.2f} seconds")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())