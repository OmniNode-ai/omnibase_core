#!/usr/bin/env python3
"""
Backward Compatibility Anti-Pattern Detection Hook

Detects and rejects backward compatibility patterns in code submissions.
Backward compatibility == tech debt when there are no consumers.

Strict typing is enforced: No backward compatibility patterns allowed.

Usage:
    # Pre-commit mode (staged files only)
    validate-no-backward-compatibility.py file1.py file2.py ...

    # Directory mode (recursive scan)
    validate-no-backward-compatibility.py --dir /path/to/directory
    validate-no-backward-compatibility.py -d src/omnibase_core

    # Mixed mode (files + directories)
    validate-no-backward-compatibility.py file1.py --dir src/ other_file.py
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# Regex flag constants to avoid union type violations - use inline to prevent union
# ONEX compliance: No union of flags, use individual flags or inline combination

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent memory issues


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

        # Check if file is too large to prevent memory issues
        if py_path.stat().st_size > MAX_FILE_SIZE:
            self.errors.append(
                f"{py_path}: File too large ({py_path.stat().st_size} bytes), skipping"
            )
            return False

        try:
            # Try UTF-8 first, then fallback encodings
            encodings_to_try = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
            content = None

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
            self.errors.append(f"{py_path}: OS/IO error reading file - {e}")
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
        except MemoryError:
            self.errors.append(f"{py_path}: File too large to parse in memory")
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
        """Check for backward compatibility anti-patterns using regex.

        Patterns detected:
        1. Comments mentioning backward compatibility (excluding negative contexts)
        2. Method/function names suggesting compatibility (_legacy, _compat, etc.)
        3. Configuration allowing extra fields (extra='allow') near compatibility mentions
        4. Protocol* backward compatibility patterns

        Pattern improvements (PR #88):
        - Added 'compat' shorthand detection (not just 'compatibility')
        - Added multi-line context detection (3 lines before, 1 line after)
        - Added negative context exclusion ("No backward compatibility" is OK)
        - Added ConfigDict pattern detection
        - Added various spacing variations (extra='allow', extra = 'allow', etc.)
        """

        # Pattern 1: Comments mentioning backward/backwards compatibility
        # Exclude negative contexts (e.g., "No backward compatibility", "prevent backward compatibility")
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

        # Negative patterns that indicate rejection of backward compatibility
        negative_patterns = [
            r"no\s+(backward|backwards)\s+compatibility",
            r"prevent\s+(backward|backwards)\s+compatibility",
            r"avoid\s+(backward|backwards)\s+compatibility",
            r"without\s+(backward|backwards)\s+compatibility",
            r"not\s+(backward|backwards)\s+compatibility",
            r"reject\s+(backward|backwards)\s+compatibility",
            r"forbid\s+(backward|backwards)\s+compatibility",
        ]

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()

            # Check if line contains negative context first
            is_negative = any(
                re.search(neg_pattern, line_lower) for neg_pattern in negative_patterns
            )
            if is_negative:
                continue  # Skip lines that explicitly reject backward compatibility

            # Check for positive backward compatibility mentions
            for pattern in compatibility_comment_patterns:
                if re.search(pattern, line_lower):
                    errors.append(
                        f"Line {line_num}: Backward compatibility comment detected - "
                        f"'{line.strip()}'. No consumers exist, remove legacy support."
                    )

        # Pattern 2: Method/function names suggesting compatibility
        # Exclude legitimate business domain methods for deprecation handling
        compatibility_method_patterns = [
            r"def\s+.*_legacy\s*\(",
            r"def\s+.*_compat\s*\(",
            r"def\s+.*_backward\s*\(",
            r"def\s+.*_backwards\s*\(",
            r"def\s+to_dict\s*\([^)]*\)\s*:\s*\n\s*[\"']{3}.*backward.*compatibility",
            r"def\s+to_dict\s*\([^)]*\)\s*:\s*\n\s*[\"']{3}.*legacy.*support",
        ]

        # Separate pattern for _deprecated methods with explicit exclusions
        deprecated_method_pattern = r"def\s+.*_deprecated\s*\("
        legitimate_deprecated_methods = [
            "is_deprecated",
            "create_deprecated",
            "get_deprecated",
            "mark_deprecated",
            "check_deprecated",
        ]

        for pattern in compatibility_method_patterns:
            # ONEX compliance: Use combined flags instead of union
            flags = re.MULTILINE | re.IGNORECASE
            matches = re.finditer(pattern, content, flags)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Backward compatibility method detected - "
                    f"remove legacy support methods"
                )

        # Check _deprecated methods separately with exclusions
        deprecated_matches = re.finditer(
            deprecated_method_pattern, content, re.MULTILINE | re.IGNORECASE
        )
        for match in deprecated_matches:
            # Extract the method name to check if it's legitimate
            method_def = match.group(0)
            method_name = re.search(r"def\s+(\w+)", method_def)
            if (
                method_name
                and method_name.group(1) not in legitimate_deprecated_methods
            ):
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Backward compatibility method detected - "
                    f"remove legacy support methods"
                )

        # Pattern 3: Configuration allowing extra fields for compatibility
        # Enhanced patterns to catch all backward compatibility extra='allow' patterns
        # Detect extra='allow' when near compatibility-related comments (within 3 lines)

        # First, check for explicit same-line patterns
        extra_allow_same_line_patterns = [
            r'extra\s*=\s*["\']allow["\']\s*#.*(compat|backward|backwards|legacy|migration)',  # Same line comment after
            r'#.*(compat|backward|backwards|legacy|migration).*extra\s*=\s*["\']allow["\']',  # Same line comment before
        ]

        for pattern in extra_allow_same_line_patterns:
            flags = re.MULTILINE | re.IGNORECASE
            matches = re.finditer(pattern, content, flags)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Configuration allowing extra fields for compatibility - "
                    f"remove permissive configuration"
                )

        # Second, check for multi-line patterns (comment within 3 lines of extra='allow')
        # Find all extra='allow' statements
        extra_allow_pattern = r'extra\s*=\s*["\']allow["\']'
        extra_matches = list(
            re.finditer(extra_allow_pattern, content, re.MULTILINE | re.IGNORECASE)
        )

        # Check context around each extra='allow' for compatibility keywords
        compatibility_keywords = [
            "backward",
            "backwards",
            "compat",
            "legacy",
            "migration",
        ]

        for match in extra_matches:
            line_num = content[: match.start()].count("\n") + 1
            lines = content.split("\n")

            # Check 3 lines before and 1 line after for compatibility keywords
            start_line = max(0, line_num - 4)  # 3 lines before (0-indexed)
            end_line = min(len(lines), line_num + 1)  # Current line + 1 after
            context_lines = lines[start_line:end_line]
            context_text = "\n".join(context_lines).lower()

            # Check if any compatibility keyword appears in context
            has_compat_keyword = any(
                keyword in context_text for keyword in compatibility_keywords
            )

            if has_compat_keyword:
                # Avoid duplicate reporting (already caught by same-line patterns)
                already_reported = False
                for pattern in extra_allow_same_line_patterns:
                    if re.search(pattern, lines[line_num - 1], re.IGNORECASE):
                        already_reported = True
                        break

                if not already_reported:
                    errors.append(
                        f"Line {line_num}: Configuration allowing extra fields for compatibility - "
                        f"remove permissive configuration"
                    )

        # Pattern 4: Protocol* backward compatibility patterns
        # Only match actual backward compatibility code patterns, not imports
        protocol_compat_patterns = [
            r'startswith\s*\(\s*["\']Protocol["\'].*compatibility',
            r"#.*Protocol.*backward.*compatibility",  # Comments only
            r"#.*Protocol.*legacy.*support",  # Comments only
            r"#.*simple.*Protocol.*names.*compatibility",  # Comments only
            r'if.*startswith\s*\(\s*["\']Protocol["\']',  # Conditional checks
        ]

        for pattern in protocol_compat_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                # Skip legitimate imports and assignments
                line_content = content.splitlines()[line_num - 1].strip()
                if line_content.startswith(("from ", "import ")) or (
                    "=" in line_content and "import" not in line_content
                ):
                    continue

                errors.append(
                    f"Line {line_num}: Protocol backward compatibility pattern detected - "
                    f"remove Protocol* legacy support"
                )

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
                # Look for conditions that check for legacy support
                if isinstance(node.test, ast.Call):
                    if isinstance(node.test.func, ast.Attribute):
                        # Check for startswith("Protocol") patterns ONLY in backward compatibility context
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
                                with open(self.file_path, encoding="utf-8") as f:
                                    source_lines = f.readlines()
                            except FileNotFoundError:
                                self.errors.append(
                                    "Error reading source file for context check: File not found"
                                )
                            except PermissionError:
                                self.errors.append(
                                    "Error reading source file for context check: Permission denied"
                                )
                            except UnicodeDecodeError as e:
                                self.errors.append(
                                    f"Error reading source file for context check: Encoding error - {e}"
                                )
                            except OSError as e:
                                self.errors.append(
                                    f"Error reading source file for context check: OS/IO error - {e}"
                                )

                            # Check lines around this node for compatibility keywords
                            context_found = False
                            if source_lines:
                                start_line = max(0, node.lineno - 3)
                                end_line = min(len(source_lines), node.lineno + 2)
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

                            if context_found:
                                self.errors.append(
                                    f"Line {node.lineno}: Protocol backward compatibility condition - "
                                    f"remove Protocol* legacy support"
                                )

                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                """Check function definitions for compatibility patterns."""
                # Check function names - but exclude legitimate business domain methods and Python dunder methods
                legitimate_deprecation_methods = [
                    "is_deprecated",
                    "create_deprecated",
                    "get_deprecated",
                    "mark_deprecated",
                    "check_deprecated",
                ]

                # Skip Python dunder methods (they're legitimate Python features, not backward compatibility)
                if node.name.startswith("__") and node.name.endswith("__"):
                    self.generic_visit(node)
                    return

                # Skip legitimate deprecation business logic methods
                if node.name in legitimate_deprecation_methods:
                    self.generic_visit(node)
                    return

                compatibility_suffixes = [
                    "_legacy",
                    "_deprecated",
                    "_compat",
                    "_backward",
                    "_backwards",
                ]
                for suffix in compatibility_suffixes:
                    if node.name.endswith(suffix):
                        self.errors.append(
                            f"Line {node.lineno}: Backward compatibility function '{node.name}' - "
                            f"remove legacy support methods"
                        )

                # Check docstrings
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

                self.generic_visit(node)

        visitor = CompatibilityVisitor(errors, file_path)
        visitor.visit(tree)

    def find_python_files_in_directory(self, directory: Path) -> list[Path]:
        """Recursively find all Python files in a directory."""
        python_files = []

        if not directory.exists():
            self.errors.append(f"Directory does not exist: {directory}")
            return python_files

        if not directory.is_dir():
            self.errors.append(f"Path is not a directory: {directory}")
            return python_files

        try:
            # Recursively find all .py files
            python_files = list(directory.rglob("*.py"))

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
                # Check if any part of the path contains skip patterns
                skip_file = False
                for part in py_file.parts:
                    if part in skip_patterns:
                        skip_file = True
                        break

                if not skip_file:
                    filtered_files.append(py_file)

            return filtered_files

        except Exception as e:
            self.errors.append(f"Error scanning directory {directory}: {e}")
            return []

    def validate_all_python_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided Python files."""
        success = True

        for py_path in file_paths:
            if not self.validate_python_file(py_path):
                success = False

        return success

    def collect_files_from_args(
        self, files: list[str], directories: list[str]
    ) -> list[Path]:
        """Collect Python files from file arguments and directory scans."""
        all_files = []

        # Add individual files
        for file_arg in files:
            file_path = Path(file_arg)
            if file_path.exists() and file_path.suffix == ".py":
                all_files.append(file_path)
            elif file_path.exists():
                self.errors.append(f"Skipping non-Python file: {file_path}")
            else:
                self.errors.append(f"File not found: {file_path}")

        # Add files from directories
        for dir_arg in directories:
            dir_path = Path(dir_arg)
            dir_files = self.find_python_files_in_directory(dir_path)
            all_files.extend(dir_files)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in all_files:
            abs_path = file_path.resolve()
            if abs_path not in seen:
                seen.add(abs_path)
                unique_files.append(file_path)

        return unique_files

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
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    if not args.files and not args.directories:
        print(
            "Error: Must provide either files or directories to scan", file=sys.stderr
        )
        return 1

    detector = BackwardCompatibilityDetector()

    # Collect all Python files from arguments
    python_files = detector.collect_files_from_args(
        files=args.files or [], directories=args.directories or []
    )

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
        files_msg = f"Checking {len(python_files)} Python file{'s' if len(python_files) != 1 else ''}..."
        print(files_msg)
        if len(python_files) <= 10:  # Show file list for small sets
            for py_file in python_files:
                print(f"   • {py_file}")
        print()

    # Validate all collected files
    success = detector.validate_all_python_files(python_files)
    detector.print_results(verbose=args.verbose)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
