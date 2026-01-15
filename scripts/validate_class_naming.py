#!/usr/bin/env python3
"""
ONEX Class Naming Convention Validation.

Validates that class names match their expected prefixes based on ONEX naming
conventions and file/directory structure.

ONEX Naming Conventions:
- Model*     - Pydantic data models (in models/, model_*.py)
- Service*   - Service classes (in services/, service_*.py)
- Util*      - Utility classes (in utils/, util_*.py)
- Protocol*  - Abstract protocol definitions (in protocols/, protocol_*.py)
- Enum*      - Enumeration types (in enums/, enum_*.py)
- *Error     - Exception classes (in errors/, exception_*.py)
- Node*      - ONEX node implementations (in nodes/, node_*.py)
- Mixin*     - Mixin classes (in mixins/, mixin_*.py)

Usage:
    poetry run python scripts/validate_class_naming.py
    poetry run python scripts/validate_class_naming.py --verbose
    poetry run python scripts/validate_class_naming.py --fix-suggestions

Exit Codes:
    0 - All class names conform to conventions
    1 - Violations found
    2 - Script error (could not run validation)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple


class NamingRule(NamedTuple):
    """A naming convention rule."""

    # Directory pattern (relative to src/omnibase_core/)
    dir_pattern: str
    # File pattern (regex)
    file_pattern: str
    # Expected class prefix (or suffix for *Error)
    expected_prefix: str
    # Whether this is a suffix (True) or prefix (False)
    is_suffix: bool = False
    # Human-readable description
    description: str = ""


# Define all naming rules
NAMING_RULES: list[NamingRule] = [
    NamingRule(
        dir_pattern="models",
        file_pattern=r"^model_.*\.py$",
        expected_prefix="Model",
        description="Pydantic data models",
    ),
    NamingRule(
        dir_pattern="services",
        file_pattern=r"^service_.*\.py$",
        expected_prefix="Service",
        description="Service classes",
    ),
    NamingRule(
        dir_pattern="utils",
        file_pattern=r"^util_.*\.py$",
        expected_prefix="Util",
        description="Utility classes",
    ),
    NamingRule(
        dir_pattern="protocols",
        file_pattern=r"^protocol_.*\.py$",
        expected_prefix="Protocol",
        description="Abstract protocol definitions",
    ),
    NamingRule(
        dir_pattern="enums",
        file_pattern=r"^enum_.*\.py$",
        expected_prefix="Enum",
        description="Enumeration types",
    ),
    NamingRule(
        dir_pattern="errors",
        file_pattern=r"^exception_.*\.py$",
        expected_prefix="Error",
        is_suffix=True,
        description="Exception classes",
    ),
    NamingRule(
        dir_pattern="nodes",
        file_pattern=r"^node_.*\.py$",
        expected_prefix="Node",
        description="ONEX node implementations",
    ),
    NamingRule(
        dir_pattern="mixins",
        file_pattern=r"^mixin_.*\.py$",
        expected_prefix="Mixin",
        description="Mixin classes",
    ),
    NamingRule(
        dir_pattern="infrastructure",
        file_pattern=r"^node_.*\.py$",
        expected_prefix="Node",
        description="Infrastructure node bases",
    ),
]

# Classes that are explicitly allowed exceptions to naming rules
# Format: (file_pattern, class_name)
#
# NOTE: These are legacy exceptions that should be addressed in future refactoring.
# Each exception documents why the naming deviation exists.
# New code should follow naming conventions strictly.
ALLOWED_EXCEPTIONS: set[tuple[str, str]] = {
    # Type aliases and special protocol-related classes
    ("protocol_", "T_co"),
    ("protocol_", "T"),
    # Base classes in infrastructure that don't follow strict naming
    ("infra_bases.py", "BaseNode"),
    ("node_base.py", "BaseNode"),
    ("node_core_base.py", "BaseNode"),
    # Private holder classes in utils (start with underscore handled separately)
    #
    # --- LEGACY EXCEPTIONS (TODO: Address in future refactoring) ---
    #
    # Enums placed in model files (should move to enums/ directory)
    ("model_coercion_mode.py", "EnumCoercionMode"),
    ("model_status_protocol.py", "EnumStatusProtocol"),
    ("model_topic_parser.py", "EnumTopicStandard"),
    #
    # Protocols defined in model files (should move to protocols/ directory)
    # These follow the Protocol pattern but are co-located with related models
    ("model_protocol_action_payload.py", "ProtocolActionPayload"),
    ("model_protocol_intent_payload.py", "ProtocolIntentPayload"),
    #
    # Utility classes without Util prefix (legacy naming)
    # FieldConverter is a dataclass used for field conversion strategies
    ("util_field_converter.py", "FieldConverter"),
    # ToolLoggerCodeBlock is a context manager for logging
    ("util_tool_logger_code_block.py", "ToolLoggerCodeBlock"),
    #
    # --- Contract Validation Pipeline (OMN-1128) ---
    #
    # Validator classes in validation/ directory don't have a specific prefix
    # These are domain-specific validators, not protocol definitions
    ("validator_contract_pipeline.py", "ContractValidationPipeline"),
    ("validator_expanded_contract.py", "ExpandedContractValidator"),
    ("validator_expanded_contract_graph.py", "ExpandedContractGraphValidator"),
    ("validator_merge.py", "MergeValidator"),
}


@dataclass
class Violation:
    """A naming convention violation."""

    file_path: Path
    line_number: int
    class_name: str
    expected_pattern: str
    actual_pattern: str
    rule: NamingRule
    suggested_name: str | None = None


@dataclass
class ValidationResult:
    """Result of validating all files."""

    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    classes_checked: int = 0
    skipped_files: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


class ClassDefinitionFinder(ast.NodeVisitor):
    """AST visitor to find all class definitions in a file."""

    def __init__(self) -> None:
        self.classes: list[tuple[str, int]] = []  # (class_name, line_number)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Record class definition with line number."""
        self.classes.append((node.name, node.lineno))
        self.generic_visit(node)


def get_applicable_rule(file_path: Path, src_root: Path) -> NamingRule | None:
    """
    Determine which naming rule applies to a given file.

    Args:
        file_path: Path to the Python file
        src_root: Root source directory (src/omnibase_core)

    Returns:
        NamingRule if file matches a rule pattern, None otherwise
    """
    try:
        relative_path = file_path.relative_to(src_root)
    except ValueError:
        return None

    # Get directory parts and filename
    parts = relative_path.parts
    filename = file_path.name

    # Skip __init__.py and test files
    if filename == "__init__.py" or filename.startswith("test_"):
        return None

    # Check each rule
    for rule in NAMING_RULES:
        # Check if file is in the rule's directory (or subdirectory)
        dir_match = any(part == rule.dir_pattern for part in parts[:-1])
        if not dir_match:
            # Also check parent directories for nested structures
            parent_str = str(relative_path.parent)
            if not parent_str.startswith(rule.dir_pattern):
                continue

        # Check if filename matches the rule's pattern
        if re.match(rule.file_pattern, filename):
            return rule

    return None


def is_allowed_exception(file_path: Path, class_name: str) -> bool:
    """Check if a class is an allowed exception to naming rules."""
    # Private classes (start with underscore) are always allowed
    if class_name.startswith("_"):
        return True

    # Single-letter type variables are allowed
    if len(class_name) <= 4 and class_name.isupper():
        return True

    # Check explicit exceptions
    filename = file_path.name
    for file_pattern, allowed_class in ALLOWED_EXCEPTIONS:
        if file_pattern in filename and class_name == allowed_class:
            return True

    return False


def check_class_name(class_name: str, rule: NamingRule) -> tuple[bool, str | None]:
    """
    Check if a class name follows the naming convention.

    Args:
        class_name: The class name to check
        rule: The naming rule to apply

    Returns:
        Tuple of (is_valid, suggested_name)
    """
    if rule.is_suffix:
        # For suffix rules (like *Error)
        is_valid = class_name.endswith(rule.expected_prefix)
        if not is_valid:
            # Suggest adding the suffix
            suggested = f"{class_name}{rule.expected_prefix}"
            return False, suggested
    else:
        # For prefix rules (like Model*, Service*, etc.)
        is_valid = class_name.startswith(rule.expected_prefix)
        if not is_valid:
            # Suggest replacing the wrong prefix with the correct one
            # Try to detect existing prefix
            for known_prefix in [
                "Model",
                "Service",
                "Util",
                "Protocol",
                "Enum",
                "Node",
                "Mixin",
            ]:
                if class_name.startswith(known_prefix):
                    base_name = class_name[len(known_prefix) :]
                    suggested = f"{rule.expected_prefix}{base_name}"
                    return False, suggested
            # No known prefix found, just prepend
            suggested = f"{rule.expected_prefix}{class_name}"
            return False, suggested

    return True, None


def validate_file(
    file_path: Path, src_root: Path
) -> tuple[list[Violation], int, str | None]:
    """
    Validate a single Python file for naming conventions.

    Args:
        file_path: Path to the Python file
        src_root: Root source directory

    Returns:
        Tuple of (violations, classes_checked, error_message)
    """
    violations: list[Violation] = []

    # Get applicable rule
    rule = get_applicable_rule(file_path, src_root)
    if rule is None:
        return [], 0, None

    # Parse the file
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        return [], 0, f"Syntax error: {e}"
    except Exception as e:
        return [], 0, f"Error reading file: {e}"

    # Find all class definitions
    finder = ClassDefinitionFinder()
    finder.visit(tree)

    classes_checked = 0
    for class_name, line_number in finder.classes:
        # Skip allowed exceptions
        if is_allowed_exception(file_path, class_name):
            continue

        classes_checked += 1

        # Check naming convention
        is_valid, suggested_name = check_class_name(class_name, rule)
        if not is_valid:
            if rule.is_suffix:
                expected_pattern = f"*{rule.expected_prefix}"
                actual_pattern = (
                    f"*{class_name[-5:]}" if len(class_name) > 5 else class_name
                )
            else:
                expected_pattern = f"{rule.expected_prefix}*"
                actual_pattern = f"{class_name[: len(rule.expected_prefix)]}*"

            violations.append(
                Violation(
                    file_path=file_path,
                    line_number=line_number,
                    class_name=class_name,
                    expected_pattern=expected_pattern,
                    actual_pattern=actual_pattern,
                    rule=rule,
                    suggested_name=suggested_name,
                )
            )

    return violations, classes_checked, None


def find_python_files(src_root: Path) -> list[Path]:
    """Find all Python files to validate."""
    return sorted(src_root.rglob("*.py"))


def format_violation(
    violation: Violation, src_root: Path, show_suggestions: bool
) -> str:
    """Format a violation for output."""
    try:
        relative_path = violation.file_path.relative_to(src_root.parent.parent)
    except ValueError:
        relative_path = violation.file_path

    msg = (
        f"{relative_path}:{violation.line_number}: "
        f"Class '{violation.class_name}' should match pattern '{violation.expected_pattern}' "
        f"(found in {violation.rule.dir_pattern}/ with {violation.rule.description})"
    )

    if show_suggestions and violation.suggested_name:
        msg += f"\n  Suggested: '{violation.suggested_name}'"

    return msg


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate ONEX class naming conventions"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show suggested fixes for violations",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help="Source directory (default: src/omnibase_core)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Determine source directory
    if args.src_dir:
        src_root = args.src_dir
    else:
        cwd = Path.cwd()
        src_root = cwd / "src" / "omnibase_core"

        if not src_root.exists():
            # Try from script location
            script_dir = Path(__file__).parent
            src_root = script_dir.parent / "src" / "omnibase_core"

    if not src_root.exists():
        print(f"Error: Source directory not found: {src_root}", file=sys.stderr)
        return 2

    if args.verbose:
        print(f"Validating class naming conventions in {src_root}")
        print()

    # Find all Python files
    python_files = find_python_files(src_root)

    if args.verbose:
        print(f"Found {len(python_files)} Python files to scan")
        print()

    # Validate each file
    result = ValidationResult()
    for file_path in python_files:
        violations, classes_checked, error = validate_file(file_path, src_root)

        if error:
            result.errors.append((file_path, error))
            continue

        if violations:
            result.violations.extend(violations)

        if classes_checked > 0:
            result.files_checked += 1
            result.classes_checked += classes_checked

    # Output results
    if args.json:
        import json

        output = {
            "violations": [
                {
                    "file": str(v.file_path),
                    "line": v.line_number,
                    "class_name": v.class_name,
                    "expected_pattern": v.expected_pattern,
                    "suggested_name": v.suggested_name,
                    "rule_dir": v.rule.dir_pattern,
                    "rule_description": v.rule.description,
                }
                for v in result.violations
            ],
            "files_checked": result.files_checked,
            "classes_checked": result.classes_checked,
            "violation_count": len(result.violations),
            "error_count": len(result.errors),
        }
        print(json.dumps(output, indent=2))
        return 1 if result.violations else 0

    if result.violations:
        print("ONEX Class Naming Convention Validation FAILED")
        print("=" * 70)
        print()

        # Group violations by directory/rule
        violations_by_rule: dict[str, list[Violation]] = {}
        for v in result.violations:
            key = f"{v.rule.dir_pattern} ({v.rule.description})"
            if key not in violations_by_rule:
                violations_by_rule[key] = []
            violations_by_rule[key].append(v)

        for rule_key, violations in sorted(violations_by_rule.items()):
            print(f"[{rule_key}]")
            for v in sorted(
                violations, key=lambda x: (str(x.file_path), x.line_number)
            ):
                print(f"  {format_violation(v, src_root, args.fix_suggestions)}")
            print()

        print("-" * 70)
        print(
            f"Summary: {len(result.violations)} violation(s) in {result.files_checked} files"
        )
        print(f"Total classes checked: {result.classes_checked}")

        if result.errors:
            print()
            print(f"Errors parsing {len(result.errors)} file(s):")
            for file_path, error in result.errors:
                print(f"  {file_path}: {error}")

        return 1

    # Success
    if args.verbose:
        print("ONEX Class Naming Convention Validation PASSED")
        print(f"  Files checked: {result.files_checked}")
        print(f"  Classes checked: {result.classes_checked}")

        if result.errors:
            print()
            print(f"  Errors parsing {len(result.errors)} file(s):")
            for file_path, error in result.errors:
                print(f"    {file_path}: {error}")
    else:
        print(
            f"OK: {result.classes_checked} classes in {result.files_checked} files conform to naming conventions"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
