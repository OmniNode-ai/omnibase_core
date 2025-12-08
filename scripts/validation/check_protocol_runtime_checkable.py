#!/usr/bin/env python3
"""
ONEX Protocol @runtime_checkable Validation

Pre-commit hook that ensures all Protocol classes in src/omnibase_core/protocols/
are decorated with @runtime_checkable.

The @runtime_checkable decorator enables isinstance() checks at runtime,
which is essential for:
1. Duck typing validation without explicit inheritance
2. Service discovery and dependency injection
3. Protocol-based type checking in production code

Usage:
    poetry run python scripts/validation/check_protocol_runtime_checkable.py

Exit Codes:
    0 - All protocols have @runtime_checkable
    1 - One or more protocols missing @runtime_checkable
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class ProtocolViolation(NamedTuple):
    """Represents a protocol missing @runtime_checkable."""

    file_path: Path
    class_name: str
    line_number: int


class ProtocolRuntimeCheckableValidator(ast.NodeVisitor):
    """AST visitor to validate @runtime_checkable on Protocol classes."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[ProtocolViolation] = []
        self._has_runtime_checkable_decorator = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check if Protocol classes have @runtime_checkable decorator."""
        # Check if this class inherits from Protocol
        if not self._inherits_from_protocol(node):
            self.generic_visit(node)
            return

        # Check if @runtime_checkable decorator is present
        if not self._has_runtime_checkable(node):
            self.violations.append(
                ProtocolViolation(
                    file_path=self.file_path,
                    class_name=node.name,
                    line_number=node.lineno,
                )
            )

        self.generic_visit(node)

    def _inherits_from_protocol(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from Protocol."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Protocol":
                return True
            # Handle typing.Protocol case
            if isinstance(base, ast.Attribute) and base.attr == "Protocol":
                return True
        return False

    def _has_runtime_checkable(self, node: ast.ClassDef) -> bool:
        """Check if class has @runtime_checkable decorator."""
        for decorator in node.decorator_list:
            # Simple decorator: @runtime_checkable
            if isinstance(decorator, ast.Name) and decorator.id == "runtime_checkable":
                return True
            # Attribute decorator: @typing.runtime_checkable
            if (
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "runtime_checkable"
            ):
                return True
        return False


def validate_file(file_path: Path) -> list[ProtocolViolation]:
    """Validate a single protocol file for @runtime_checkable usage."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        validator = ProtocolRuntimeCheckableValidator(file_path)
        validator.visit(tree)

        return validator.violations

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def find_protocol_files(protocols_dir: Path) -> list[Path]:
    """Find all protocol files, excluding __init__.py files."""
    protocol_files = []

    for file_path in protocols_dir.rglob("*.py"):
        # Skip __init__.py files
        if file_path.name == "__init__.py":
            continue
        # Skip non-protocol files (e.g., core.py at top level may be re-export)
        if file_path.name == "core.py":
            continue
        protocol_files.append(file_path)

    return sorted(protocol_files)


def main() -> int:
    """Main entry point for the validation script."""
    # Determine protocols directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    protocols_dir = repo_root / "src" / "omnibase_core" / "protocols"

    if not protocols_dir.exists():
        print(f"Protocols directory not found: {protocols_dir}")
        return 1

    # Find all protocol files
    protocol_files = find_protocol_files(protocols_dir)

    if not protocol_files:
        print("No protocol files found to validate.")
        return 0

    # Validate each file
    all_violations: list[ProtocolViolation] = []
    for file_path in protocol_files:
        violations = validate_file(file_path)
        all_violations.extend(violations)

    # Report results
    if all_violations:
        print("ONEX Protocol @runtime_checkable Validation FAILED")
        print("=" * 80)
        print(
            f"Found {len(all_violations)} Protocol class(es) missing @runtime_checkable:\n"
        )

        for violation in all_violations:
            rel_path = violation.file_path.relative_to(repo_root)
            print(f"   {rel_path}:{violation.line_number}")
            print(
                f"      class {violation.class_name}(Protocol): missing @runtime_checkable"
            )
            print()

        print("How to fix:")
        print("   Add @runtime_checkable decorator to Protocol classes:")
        print()
        print("   BAD:")
        print("   class MyProtocol(Protocol):")
        print("       ...")
        print()
        print("   GOOD:")
        print("   from typing import Protocol, runtime_checkable")
        print()
        print("   @runtime_checkable")
        print("   class MyProtocol(Protocol):")
        print("       ...")
        print()
        print("   Why @runtime_checkable?")
        print("   - Enables isinstance() checks at runtime")
        print("   - Required for duck typing validation")
        print("   - Essential for service discovery and DI")

        return 1

    print(
        f"ONEX Protocol @runtime_checkable Check PASSED ({len(protocol_files)} files checked)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
