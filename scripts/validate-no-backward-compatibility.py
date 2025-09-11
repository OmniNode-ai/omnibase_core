#!/usr/bin/env python3
"""
Backward Compatibility Anti-Pattern Detection Hook

Detects and rejects backward compatibility patterns in code submissions.
Backward compatibility == tech debt when there are no consumers.

ZERO TOLERANCE: No backward compatibility patterns allowed.
"""

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
        try:
            with open(py_path, encoding="utf-8") as f:
                content = f.read()

            self.checked_files += 1
            file_errors = []

            # Check for backward compatibility patterns
            self._check_backward_compatibility_patterns(content, py_path, file_errors)

            # Check AST for compatibility code patterns
            try:
                tree = ast.parse(content, filename=str(py_path))
                self._check_ast_for_compatibility(tree, py_path, file_errors)
            except SyntaxError:
                # Skip files with syntax errors - other tools will catch them
                pass

            if file_errors:
                self.errors.extend([f"{py_path}: {error}" for error in file_errors])
                return False

            return True

        except Exception as e:
            self.errors.append(f"{py_path}: Failed to parse file - {e!s}")
            return False

    def _check_backward_compatibility_patterns(
        self,
        content: str,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Check for backward compatibility anti-patterns using regex."""

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

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            for pattern in compatibility_comment_patterns:
                if re.search(pattern, line_lower):
                    errors.append(
                        f"Line {line_num}: Backward compatibility comment detected - "
                        f"'{line.strip()}'. No consumers exist, remove legacy support."
                    )

        # Pattern 2: Method/function names suggesting compatibility
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
            matches = re.finditer(
                pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL
            )
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Backward compatibility method detected - "
                    f"remove legacy support methods"
                )

        # Pattern 3: Configuration allowing extra fields for compatibility
        extra_allow_patterns = [
            r'extra\s*=\s*["\']allow["\'].*compatibility',
            r"Config:.*extra.*allow.*compatibility",
        ]

        for pattern in extra_allow_patterns:
            matches = re.finditer(
                pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL
            )
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Configuration allowing extra fields for compatibility - "
                    f"remove permissive configuration"
                )

        # Pattern 4: Protocol* backward compatibility patterns
        protocol_compat_patterns = [
            r'startswith\s*\(\s*["\']Protocol["\'].*compatibility',
            r"Protocol.*backward.*compatibility",
            r"Protocol.*legacy.*support",
            r"simple.*Protocol.*names.*compatibility",
        ]

        for pattern in protocol_compat_patterns:
            matches = re.finditer(
                pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL
            )
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
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
                                with open(self.file_path, "r") as f:
                                    source_lines = f.readlines()
                            except:
                                pass

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
                # Check function names
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

    def validate_all_python_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided Python files."""
        success = True

        for py_path in file_paths:
            if not self.validate_python_file(py_path):
                success = False

        return success

    def print_results(self) -> None:
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
            print(
                f"✅ Backward Compatibility Check PASSED ({self.checked_files} files checked)",
            )


def main() -> int:
    """Main entry point for the validation hook."""
    if len(sys.argv) < 2:
        print("Usage: validate-no-backward-compatibility.py <path1.py> [path2.py] ...")
        return 1

    detector = BackwardCompatibilityDetector()

    # Process all provided Python files
    python_files = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.suffix == ".py" and path.exists():
            python_files.append(path)

    if not python_files:
        print("✅ Backward Compatibility Check PASSED (no Python files to check)")
        return 0

    success = detector.validate_all_python_files(python_files)
    detector.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
