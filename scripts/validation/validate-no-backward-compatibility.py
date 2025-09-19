#!/usr/bin/env python3
"""
Backward Compatibility Anti-Pattern Detection Hook

Detects and rejects backward compatibility patterns in code submissions.
Backward compatibility == tech debt when there are no consumers.

ZERO TOLERANCE: No backward compatibility patterns allowed.

Usage:
    # Pre-commit mode (staged files only)
    validate-no-backward-compatibility.py file1.py file2.py ...

    # Directory mode (recursive scan)
    validate-no-backward-compatibility.py --dir /path/to/directory
    validate-no-backward-compatibility.py -d src/omnibase_core

    # Mixed mode (files + directories)
    validate-no-backward-compatibility.py file1.py --dir src/ other_file.py
"""

import argparse
import ast
import re
import sys
from pathlib import Path


class BackwardCompatibilityDetector:
    """Detects backward compatibility anti-patterns in code."""

    def __init__(self):
        self.errors: list[str] = []
        self.checked_files = 0

    def validate_python_file(self, py_path: Path) -> bool:
        """Check Python file for backward compatibility patterns."""
        # Validate file existence and basic properties
        if not py_path.exists():
            self.errors.append(f"{py_path}: File does not exist")
            return False

        if not py_path.is_file():
            self.errors.append(f"{py_path}: Path is not a regular file")
            return False

        if py_path.stat().st_size == 0:
            # Empty files are valid, just skip them
            self.checked_files += 1
            return True

        # Check if file is too large (> 10MB) to prevent memory issues
        max_file_size = 10 * 1024 * 1024  # 10MB
        if py_path.stat().st_size > max_file_size:
            self.errors.append(
                f"{py_path}: File too large ({py_path.stat().st_size} bytes), skipping"
            )
            return False

        content = None
        try:
            # Try UTF-8 first, then fallback encodings
            encodings_to_try = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

            for encoding in encodings_to_try:
                try:
                    with open(py_path, encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    if encoding == encodings_to_try[-1]:  # Last encoding failed
                        self.errors.append(
                            f"{py_path}: Unable to decode file with any supported encoding "
                            f"(tried: {', '.join(encodings_to_try)})"
                        )
                        return False
                    continue

        except FileNotFoundError:
            self.errors.append(f"{py_path}: File not found")
            return False
        except PermissionError:
            self.errors.append(f"{py_path}: Permission denied - cannot read file")
            return False
        except OSError as e:
            self.errors.append(f"{py_path}: OS error reading file - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{py_path}: Unexpected error reading file - {e}")
            return False

        self.checked_files += 1
        file_errors = []

        # Check for backward compatibility patterns with error handling
        try:
            self._check_backward_compatibility_patterns(content, py_path, file_errors)
        except Exception as e:
            self.errors.append(f"{py_path}: Error during pattern analysis - {e}")
            return False

        # Check AST for compatibility code patterns with comprehensive error handling
        try:
            tree = ast.parse(content, filename=str(py_path))
            try:
                self._check_ast_for_compatibility(tree, py_path, file_errors)
            except Exception as e:
                self.errors.append(
                    f"{py_path}: Error during AST compatibility analysis - {e}"
                )
                return False
        except SyntaxError as e:
            # Skip files with syntax errors but report for debugging
            if hasattr(e, "lineno") and hasattr(e, "offset"):
                self.errors.append(
                    f"{py_path}: Python syntax error at line {e.lineno}, column {e.offset}: {e.msg}"
                )
            else:
                self.errors.append(f"{py_path}: Python syntax error: {e.msg}")
            return False
        except ValueError as e:
            self.errors.append(f"{py_path}: Invalid Python code - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{py_path}: Failed to parse Python AST - {e}")
            return False

        if file_errors:
            self.errors.extend([f"{py_path}: {error}" for error in file_errors])
            return False

        return True

    def _check_backward_compatibility_patterns(
        self,
        content: str,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Check for backward compatibility anti-patterns using regex."""
        if not content:
            return

        try:
            # Pattern 1: Comments mentioning backward/backwards compatibility
            compatibility_comment_patterns = [
                r"backward\s+compatibility",
                r"backwards\s+compatibility",
                r"for\s+compatibility",
                r"legacy\s+support",
                r"maintain\s+compatibility",
                r"compatibility\s+layer",
                r"compatibility\s+wrapper",
                r"migration\s+path",
                r"deprecated\s+for\s+compatibility",
            ]

            try:
                lines = content.split("\n")
            except Exception as e:
                errors.append(f"Error splitting content into lines: {e}")
                return

            for line_num, line in enumerate(lines, 1):
                try:
                    line_lower = line.lower()
                    for pattern in compatibility_comment_patterns:
                        try:
                            if re.search(pattern, line_lower):
                                errors.append(
                                    f"Line {line_num}: Backward compatibility comment detected - "
                                    f"'{line.strip()}'. No consumers exist, remove legacy support."
                                )
                        except re.error as e:
                            errors.append(
                                f"Line {line_num}: Regex error with pattern '{pattern}': {e}"
                            )
                        except Exception as e:
                            errors.append(
                                f"Line {line_num}: Error checking pattern '{pattern}': {e}"
                            )
                except Exception as e:
                    errors.append(f"Line {line_num}: Error processing line: {e}")
        except Exception as e:
            errors.append(f"Error in compatibility comment pattern checking: {e}")
            return

        # Pattern 2: Method/function names suggesting compatibility
        try:
            compatibility_method_patterns = [
                r"def\s+.*_legacy\s*\(",
                r"def\s+.*_deprecated\s*\(",
                r"def\s+.*_compat\s*\(",
                r"def\s+.*_backward\s*\(",
                r"def\s+.*_backwards\s*\(",
                r"def\s+to_dict\s*\([^)]*\)\s*:\s*\n\s*[\"']{3}.*backward.*compatibility",
                r"def\s+to_dict\s*\([^)]*\)\s*:\s*\n\s*[\"']{3}.*legacy.*support",
            ]

            for pattern in compatibility_method_patterns:
                try:
                    matches = re.finditer(
                        pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL
                    )
                    for match in matches:
                        try:
                            line_num = content[: match.start()].count("\n") + 1
                            errors.append(
                                f"Line {line_num}: Backward compatibility method detected - "
                                f"remove legacy support methods"
                            )
                        except Exception as e:
                            errors.append(
                                f"Error calculating line number for method pattern match: {e}"
                            )
                except re.error as e:
                    errors.append(f"Regex error with method pattern '{pattern}': {e}")
                except Exception as e:
                    errors.append(f"Error checking method pattern '{pattern}': {e}")
        except Exception as e:
            errors.append(f"Error in compatibility method pattern checking: {e}")
            return

        # Pattern 3: Configuration allowing extra fields for compatibility
        try:
            extra_allow_patterns = [
                r'extra\s*=\s*["\']allow["\'].*compatibility',
                r"Config:.*extra.*allow.*compatibility",
            ]

            for pattern in extra_allow_patterns:
                try:
                    matches = re.finditer(
                        pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL
                    )
                    for match in matches:
                        try:
                            line_num = content[: match.start()].count("\n") + 1
                            errors.append(
                                f"Line {line_num}: Configuration allowing extra fields for compatibility - "
                                f"remove permissive configuration"
                            )
                        except Exception as e:
                            errors.append(
                                f"Error calculating line number for config pattern match: {e}"
                            )
                except re.error as e:
                    errors.append(f"Regex error with config pattern '{pattern}': {e}")
                except Exception as e:
                    errors.append(f"Error checking config pattern '{pattern}': {e}")
        except Exception as e:
            errors.append(f"Error in compatibility config pattern checking: {e}")
            return

        # Pattern 4: Protocol* backward compatibility patterns
        # Only match actual backward compatibility code patterns, not imports
        try:
            protocol_compat_patterns = [
                r'startswith\s*\(\s*["\']Protocol["\'].*compatibility',
                r"#.*Protocol.*backward.*compatibility",  # Comments only
                r"#.*Protocol.*legacy.*support",  # Comments only
                r"#.*simple.*Protocol.*names.*compatibility",  # Comments only
                r'if.*startswith\s*\(\s*["\']Protocol["\']',  # Conditional checks
            ]

            for pattern in protocol_compat_patterns:
                try:
                    matches = re.finditer(
                        pattern, content, re.MULTILINE | re.IGNORECASE
                    )
                    for match in matches:
                        try:
                            line_num = content[: match.start()].count("\n") + 1
                            # Skip legitimate imports and assignments
                            try:
                                content_lines = content.splitlines()
                                if line_num <= len(content_lines):
                                    line_content = content_lines[line_num - 1].strip()
                                    if (
                                        line_content.startswith("from ")
                                        or line_content.startswith("import ")
                                        or "=" in line_content
                                        and "import" not in line_content
                                    ):
                                        continue
                                else:
                                    errors.append(
                                        f"Line number {line_num} out of range for file content"
                                    )
                                    continue
                            except Exception as e:
                                errors.append(
                                    f"Error checking line content at line {line_num}: {e}"
                                )
                                continue

                            errors.append(
                                f"Line {line_num}: Protocol backward compatibility pattern detected - "
                                f"remove Protocol* legacy support"
                            )
                        except Exception as e:
                            errors.append(
                                f"Error processing protocol pattern match: {e}"
                            )
                except re.error as e:
                    errors.append(f"Regex error with protocol pattern '{pattern}': {e}")
                except Exception as e:
                    errors.append(f"Error checking protocol pattern '{pattern}': {e}")
        except Exception as e:
            errors.append(f"Error in protocol compatibility pattern checking: {e}")

    def _check_ast_for_compatibility(
        self,
        tree: ast.AST,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Check AST for backward compatibility patterns."""

        class CompatibilityVisitor(ast.NodeVisitor):
            def __init__(self, errors: list[str], file_path: Path):
                self.errors = errors
                self.file_path = file_path

            def visit_If(self, node):
                """Check for compatibility conditions."""
                try:
                    # Look for conditions that check for legacy support
                    if isinstance(node.test, ast.Call):
                        if isinstance(node.test.func, ast.Attribute):
                            # Check for startswith("Protocol") patterns ONLY in backward compatibility context
                            try:
                                if (
                                    node.test.func.attr == "startswith"
                                    and len(node.test.args) > 0
                                    and isinstance(node.test.args[0], ast.Constant)
                                    and node.test.args[0].value == "Protocol"
                                ):
                                    # Only flag if this is in a backward compatibility context
                                    # Check if there are comments nearby mentioning compatibility
                                    source_lines = []
                                    try:
                                        with open(
                                            self.file_path, "r", encoding="utf-8"
                                        ) as f:
                                            source_lines = f.readlines()
                                    except Exception as e:
                                        self.errors.append(
                                            f"Error reading source file for context check: {e}"
                                        )

                                    # Check lines around this node for compatibility keywords
                                    context_found = False
                                    if source_lines:
                                        try:
                                            start_line = max(0, node.lineno - 3)
                                            end_line = min(
                                                len(source_lines), node.lineno + 2
                                            )
                                            context_text = "".join(
                                                source_lines[start_line:end_line]
                                            ).lower()

                                            if any(
                                                keyword in context_text
                                                for keyword in [
                                                    "backward",
                                                    "backwards",
                                                    "compatibility",
                                                    "legacy",
                                                    "support",
                                                ]
                                            ):
                                                context_found = True
                                        except Exception as e:
                                            self.errors.append(
                                                f"Error analyzing context around line {node.lineno}: {e}"
                                            )

                                    if context_found:
                                        self.errors.append(
                                            f"Line {node.lineno}: Protocol backward compatibility condition - "
                                            f"remove Protocol* legacy support"
                                        )
                            except Exception as e:
                                self.errors.append(
                                    f"Error checking startswith pattern at line {node.lineno}: {e}"
                                )

                    try:
                        self.generic_visit(node)
                    except Exception as e:
                        self.errors.append(
                            f"Error visiting child nodes of If statement at line {node.lineno}: {e}"
                        )
                except Exception as e:
                    self.errors.append(
                        f"Error processing If node at line {getattr(node, 'lineno', 'unknown')}: {e}"
                    )

            def visit_FunctionDef(self, node):
                """Check function definitions for compatibility patterns."""
                try:
                    # Check function names
                    compatibility_suffixes = [
                        "_legacy",
                        "_deprecated",
                        "_compat",
                        "_backward",
                        "_backwards",
                    ]
                    try:
                        for suffix in compatibility_suffixes:
                            if node.name.endswith(suffix):
                                self.errors.append(
                                    f"Line {node.lineno}: Backward compatibility function '{node.name}' - "
                                    f"remove legacy support methods"
                                )
                    except Exception as e:
                        self.errors.append(
                            f"Error checking function name '{node.name}' at line {node.lineno}: {e}"
                        )

                    # Check docstrings
                    try:
                        if (
                            node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        ):
                            docstring = node.body[0].value.value.lower()
                            if any(
                                pattern in docstring
                                for pattern in [
                                    "backward compatibility",
                                    "backwards compatibility",
                                    "legacy support",
                                    "migration path",
                                ]
                            ):
                                self.errors.append(
                                    f"Line {node.lineno}: Function '{node.name}' has backward compatibility docstring - "
                                    f"remove legacy support"
                                )
                    except Exception as e:
                        self.errors.append(
                            f"Error checking docstring for function '{node.name}' at line {node.lineno}: {e}"
                        )

                    try:
                        self.generic_visit(node)
                    except Exception as e:
                        self.errors.append(
                            f"Error visiting child nodes of function '{node.name}' at line {node.lineno}: {e}"
                        )
                except Exception as e:
                    self.errors.append(
                        f"Error processing function node at line {getattr(node, 'lineno', 'unknown')}: {e}"
                    )

        try:
            visitor = CompatibilityVisitor(errors, file_path)
            visitor.visit(tree)
        except Exception as e:
            errors.append(f"Error during AST visitor traversal: {e}")

    def find_python_files_in_directory(self, directory: Path) -> list[Path]:
        """Recursively find all Python files in a directory."""
        python_files = []

        # Validate directory path
        try:
            if not directory.exists():
                self.errors.append(f"Directory does not exist: {directory}")
                return python_files

            if not directory.is_dir():
                self.errors.append(f"Path is not a directory: {directory}")
                return python_files

        except Exception as e:
            self.errors.append(
                f"Error checking directory properties for {directory}: {e}"
            )
            return python_files

        # Check if we have permission to read the directory
        try:
            list(directory.iterdir())  # Test if we can read directory contents
        except PermissionError:
            self.errors.append(
                f"Permission denied - cannot read directory: {directory}"
            )
            return python_files
        except OSError as e:
            self.errors.append(f"OS error accessing directory {directory}: {e}")
            return python_files
        except Exception as e:
            self.errors.append(f"Unexpected error accessing directory {directory}: {e}")
            return python_files

        try:
            # Recursively find all .py files with error handling
            try:
                python_files = list(directory.rglob("*.py"))
            except Exception as e:
                self.errors.append(
                    f"Error during recursive glob search in {directory}: {e}"
                )
                return []

            # Filter out common directories to skip
            skip_patterns = {
                "__pycache__",
                ".pytest_cache",
                ".git",
                "node_modules",
                ".venv",
                "venv",
                ".tox",
                "build",
                "dist",
                ".mypy_cache",
            }

            filtered_files = []
            for py_file in python_files:
                try:
                    # Check if any part of the path contains skip patterns
                    skip_file = False
                    for part in py_file.parts:
                        if part in skip_patterns:
                            skip_file = True
                            break

                    if not skip_file:
                        # Additional validation: ensure the file is readable
                        try:
                            if py_file.is_file() and py_file.stat().st_size >= 0:
                                filtered_files.append(py_file)
                        except Exception as e:
                            self.errors.append(f"Error validating file {py_file}: {e}")
                            continue

                except Exception as e:
                    self.errors.append(f"Error processing file path {py_file}: {e}")
                    continue

            return filtered_files

        except Exception as e:
            self.errors.append(f"Error scanning directory {directory}: {e}")
            return []

    def validate_all_python_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided Python files."""
        if not file_paths:
            return True

        success = True
        processed_files = 0

        for py_path in file_paths:
            try:
                if not self.validate_python_file(py_path):
                    success = False
                processed_files += 1
            except Exception as e:
                self.errors.append(
                    f"{py_path}: Unexpected error during validation - {e}"
                )
                success = False

        # Sanity check: ensure we processed the expected number of files
        if processed_files != len(file_paths):
            self.errors.append(
                f"Warning: Expected to process {len(file_paths)} files, "
                f"but only processed {processed_files}"
            )

        return success

    def collect_files_from_args(
        self, files: list[str], directories: list[str]
    ) -> list[Path]:
        """Collect Python files from file arguments and directory scans."""
        all_files = []

        # Add individual files with comprehensive error handling
        for file_arg in files:
            try:
                file_path = Path(file_arg)

                try:
                    if file_path.exists():
                        if file_path.suffix == ".py":
                            if file_path.is_file():
                                all_files.append(file_path)
                            else:
                                self.errors.append(
                                    f"Path is not a regular file: {file_path}"
                                )
                        else:
                            self.errors.append(f"Skipping non-Python file: {file_path}")
                    else:
                        self.errors.append(f"File not found: {file_path}")
                except Exception as e:
                    self.errors.append(f"Error checking file {file_arg}: {e}")

            except Exception as e:
                self.errors.append(f"Error processing file argument '{file_arg}': {e}")

        # Add files from directories with error handling
        for dir_arg in directories:
            try:
                dir_path = Path(dir_arg)
                dir_files = self.find_python_files_in_directory(dir_path)
                all_files.extend(dir_files)
            except Exception as e:
                self.errors.append(
                    f"Error processing directory argument '{dir_arg}': {e}"
                )

        # Remove duplicates while preserving order with error handling
        try:
            seen = set()
            unique_files = []
            for file_path in all_files:
                try:
                    abs_path = file_path.resolve()
                    if abs_path not in seen:
                        seen.add(abs_path)
                        unique_files.append(file_path)
                except Exception as e:
                    self.errors.append(f"Error resolving file path {file_path}: {e}")
                    continue

            return unique_files
        except Exception as e:
            self.errors.append(f"Error during file deduplication: {e}")
            return all_files  # Return original list if deduplication fails

    def print_results(self, verbose: bool = False) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ Backward Compatibility Detection FAILED")
            print("=" * 65)
            print(
                f"Found {len(self.errors)} backward compatibility violations in {self.checked_files} files:\n",
            )

            for error in self.errors:
                print(f"   • {error}")

            print("\n🔧 How to fix:")
            print("   Remove ALL backward compatibility patterns:")
            print("   ")
            print("   ❌ BAD:")
            print("   # Accept simple Protocol* names for backward compatibility")
            print('   if dependency.startswith("Protocol"):')
            print("       continue")
            print("   ")
            print("   def to_dict(self) -> dict:")
            print('       """Convert to dictionary for backward compatibility."""')
            print("       return self.model_dump()")
            print("   ")
            print("   ✅ GOOD:")
            print("   # Only accept fully qualified protocol paths")
            print('   if "protocol" in dependency.lower():')
            print("       continue")
            print("   ")
            print("   # No wrapper methods - use model_dump() directly")
            print("   ")
            print("   💡 Remember:")
            print("   • No consumers exist - backward compatibility = tech debt")
            print("   • Remove legacy support code completely")
            print("   • Use proper ONEX patterns from day one")
            print("   • Clean code is better than compatible code")

        else:
            files_msg = (
                f"{self.checked_files} file{'s' if self.checked_files != 1 else ''}"
            )
            print(f"✅ Backward Compatibility Check PASSED ({files_msg} checked)")

            if verbose and self.checked_files > 0:
                print("   No backward compatibility anti-patterns detected.")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for the hook."""
    parser = argparse.ArgumentParser(
        description="Backward Compatibility Anti-Pattern Detection Hook",
        epilog="""
Examples:
  # Pre-commit mode (validate specific staged files)
  %(prog)s file1.py file2.py src/model.py

  # Directory mode (scan entire directory recursively)
  %(prog)s --dir src/omnibase_core
  %(prog)s -d src/

  # Mixed mode (files + directories)
  %(prog)s file1.py --dir src/ other_file.py -d tests/

  # Verbose output
  %(prog)s --dir src/ --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "files", nargs="*", help="Python files to validate (for pre-commit hook usage)"
    )

    parser.add_argument(
        "-d",
        "--dir",
        action="append",
        dest="directories",
        help="Directory to scan recursively for Python files (can be used multiple times)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0")

    return parser


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        parser = create_argument_parser()

        try:
            args = parser.parse_args()
        except SystemExit as e:
            # argparse calls sys.exit() on error, re-raise to handle gracefully
            return e.code if e.code is not None else 1
        except Exception as e:
            print(f"❌ Error parsing command line arguments: {e}")
            return 1

        # Validate arguments
        if not args.files and not args.directories:
            print("❌ Must provide either files or directories to scan")
            print("Use --help for usage information")
            return 1

        try:
            detector = BackwardCompatibilityDetector()
        except Exception as e:
            print(f"❌ Error initializing detector: {e}")
            return 1

        # Collect all Python files from arguments
        try:
            python_files = detector.collect_files_from_args(
                files=args.files or [], directories=args.directories or []
            )
        except Exception as e:
            print(f"❌ Error collecting files from arguments: {e}")
            return 1

        # Early exit if no files to process and no collection errors
        if not python_files and not detector.errors:
            print("✅ Backward Compatibility Check PASSED (no Python files to check)")
            return 0

        # Early exit if there were collection errors
        if detector.errors:
            print("❌ File Collection FAILED")
            for error in detector.errors:
                print(f"   • {error}")
            return 1

        if args.verbose:
            try:
                files_msg = f"Checking {len(python_files)} Python file{'s' if len(python_files) != 1 else ''}..."
                print(files_msg)
                if len(python_files) <= 10:  # Show file list for small sets
                    for py_file in python_files:
                        print(f"   • {py_file}")
                print()
            except Exception as e:
                print(f"Warning: Error displaying verbose information: {e}")

        # Validate all collected files
        try:
            success = detector.validate_all_python_files(python_files)
            detector.print_results(verbose=args.verbose)
            return 0 if success else 1
        except Exception as e:
            print(f"❌ Validation process failed: {e}")
            if detector.errors:
                print("\nPartial errors encountered:")
                for error in detector.errors[:5]:  # Show first 5 errors
                    print(f"   • {error}")
                if len(detector.errors) > 5:
                    print(f"   ... and {len(detector.errors) - 5} more errors")
            return 1

    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error in main(): {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
