#!/usr/bin/env python3
"""
Enhanced Union type usage validation for omni* repositories.
Validates that Union types are used properly according to ONEX standards.
Detects complex unions that should be replaced with proper models.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class UnionPattern:
    """Represents a Union pattern for analysis."""

    def __init__(self, types: List[str], line: int, file_path: str):
        self.types = sorted(types)  # Sort for consistent comparison
        self.line = line
        self.file_path = file_path
        self.type_count = len(types)

    def __hash__(self):
        return hash(tuple(self.types))

    def __eq__(self, other):
        return isinstance(other, UnionPattern) and self.types == other.types

    def get_signature(self) -> str:
        """Get a string signature for this union pattern."""
        return f"Union[{', '.join(self.types)}]"


class UnionUsageChecker(ast.NodeVisitor):
    """Enhanced checker for Union type usage patterns."""

    def __init__(self, file_path: str):
        self.union_count = 0
        self.issues = []
        self.file_path = file_path
        self.union_patterns: List[UnionPattern] = []

        # Track problematic patterns
        self.complex_unions: List[UnionPattern] = []
        self.primitive_heavy_unions: List[UnionPattern] = []
        self.generic_unions: List[UnionPattern] = []

        # Common problematic type combinations
        self.problematic_combinations = {
            frozenset(["str", "int", "bool", "float"]): "primitive_overload",
            frozenset(["str", "int", "bool", "dict"]): "mixed_primitive_complex",
            frozenset(["str", "int", "dict", "list"]): "mixed_primitive_complex",
            frozenset(["str", "int", "bool", "float", "dict"]): "everything_union",
            frozenset(["str", "int", "bool", "float", "list"]): "everything_union",
        }

    def _extract_type_name(self, node: ast.AST) -> str:
        """Extract type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            return type(node.value).__name__
        elif isinstance(node, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                return node.value.id
        elif isinstance(node, ast.Attribute):
            # Handle module.Type patterns
            return f"{self._extract_type_name(node.value)}.{node.attr}"
        return "Unknown"

    def _analyze_union_pattern(self, union_pattern: UnionPattern) -> None:
        """Analyze a union pattern for potential issues."""
        types_set = frozenset(union_pattern.types)

        # Check for complex unions (configurable complexity threshold)
        if union_pattern.type_count >= 3:  # Will be updated with min_complexity
            self.complex_unions.append(union_pattern)

            # Check for specific problematic combinations
            for problem_set, problem_type in self.problematic_combinations.items():
                if problem_set.issubset(types_set):
                    if problem_type == "primitive_overload":
                        self.issues.append(
                            f"Line {union_pattern.line}: Union with 4+ primitive types "
                            f"{union_pattern.get_signature()} should use a proper model or Enum"
                        )
                    elif problem_type == "mixed_primitive_complex":
                        self.issues.append(
                            f"Line {union_pattern.line}: Mixed primitive/complex Union "
                            f"{union_pattern.get_signature()} should use a discriminated model"
                        )
                    elif problem_type == "everything_union":
                        self.issues.append(
                            f"Line {union_pattern.line}: Overly broad Union "
                            f"{union_pattern.get_signature()} should use 'Any' or proper model"
                        )

            # Check for union with many different types (5+ suggests too broad)
            if union_pattern.type_count >= 5:
                self.issues.append(
                    f"Line {union_pattern.line}: Overly broad Union "
                    f"{union_pattern.get_signature()} should use 'Any' or proper model"
                )

        # Check for primitive-heavy unions
        primitive_types = {"str", "int", "bool", "float"}
        primitive_count = len([t for t in union_pattern.types if t in primitive_types])

        if primitive_count >= 3:
            self.primitive_heavy_unions.append(union_pattern)
            if union_pattern.type_count == primitive_count:
                self.issues.append(
                    f"Line {union_pattern.line}: All-primitive Union "
                    f"{union_pattern.get_signature()} should use a Value Object model"
                )

        # Check for generic unions that suggest missing abstraction
        if "dict" in union_pattern.types and "list" in union_pattern.types:
            self.generic_unions.append(union_pattern)
            self.issues.append(
                f"Line {union_pattern.line}: Generic collection Union "
                f"{union_pattern.get_signature()} should use specific data structures"
            )

        # Check for duplicate types (e.g., Union[str, int, str])
        if len(set(union_pattern.types)) != len(union_pattern.types):
            unique_types = list(set(union_pattern.types))
            self.issues.append(
                f"Line {union_pattern.line}: Union contains duplicate types "
                f"{union_pattern.get_signature()} → Union[{', '.join(sorted(unique_types))}]"
            )

        # Check for redundant None patterns
        if "None" in union_pattern.types and union_pattern.type_count > 2:
            non_none_types = [t for t in union_pattern.types if t != "None"]
            if len(non_none_types) == 1:
                self.issues.append(
                    f"Line {union_pattern.line}: Use Optional[{non_none_types[0]}] "
                    f"instead of {union_pattern.get_signature()}"
                )

        # Check for path/string/uuid combinations (common CLI pattern)
        path_like_types = {"str", "Path", "UUID"}
        if path_like_types.issubset(types_set) and union_pattern.type_count >= 4:
            self.issues.append(
                f"Line {union_pattern.line}: Path/ID/Value Union "
                f"{union_pattern.get_signature()} should use a CLI value model"
            )

    def visit_Subscript(self, node):
        """Visit subscript nodes (e.g., Union[str, int])."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            self.union_count += 1

            # Extract union types
            union_types = []
            if isinstance(node.slice, ast.Tuple):
                for elt in node.slice.elts:
                    type_name = self._extract_type_name(elt)
                    union_types.append(type_name)
            else:
                # Single element in Union (shouldn't happen, but handle it)
                type_name = self._extract_type_name(node.slice)
                union_types.append(type_name)

            # Create union pattern for analysis
            union_pattern = UnionPattern(union_types, node.lineno, self.file_path)
            self.union_patterns.append(union_pattern)

            # Analyze the pattern
            self._analyze_union_pattern(union_pattern)

            # Existing check for Union with None
            if len(union_types) == 2 and "None" in union_types:
                self.issues.append(
                    f"Line {node.lineno}: Use Optional[T] or T | None instead of Union[T, None]"
                )

        self.generic_visit(node)


def validate_python_file(file_path: Path) -> Tuple[int, List[str], List[UnionPattern]]:
    """Validate Union usage in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker(str(file_path))
        checker.visit(tree)

        return checker.union_count, checker.issues, checker.union_patterns

    except Exception as e:
        return 0, [f"Error parsing {file_path}: {e}"], []


def analyze_repeated_patterns(all_patterns: List[UnionPattern]) -> List[str]:
    """Analyze repeated union patterns across files."""
    pattern_counts = Counter()
    pattern_files = defaultdict(set)

    for pattern in all_patterns:
        signature = pattern.get_signature()
        pattern_counts[signature] += 1
        pattern_files[signature].add(pattern.file_path)

    issues = []
    for signature, count in pattern_counts.items():
        if count >= 3:  # Repeated 3+ times
            files = pattern_files[signature]
            issues.append(
                f"Repeated pattern '{signature}' found {count} times across "
                f"{len(files)} files - consider creating a reusable model"
            )

    return issues


def generate_model_suggestions(patterns: List[UnionPattern]) -> List[str]:
    """Generate specific suggestions for replacing unions with models."""
    suggestions = []

    # Group patterns by type combination
    type_groups = defaultdict(list)
    for pattern in patterns:
        key = tuple(sorted(pattern.types))
        type_groups[key].append(pattern)

    for types, pattern_list in type_groups.items():
        if len(pattern_list) >= 1:  # Show suggestions for any complex pattern
            types_set = set(types)
            types_str = ", ".join(types)

            # Generate context-aware suggestions
            suggestion = f"Replace Union[{types_str}]:"

            # CLI value patterns
            if {"str", "Path", "UUID"}.issubset(types_set):
                suggestion += "\n  • class ModelCliValue(BaseModel):"
                suggestion += "\n    - value: str | Path | UUID"
                suggestion += "\n    - type_hint: Literal['string', 'path', 'uuid']"

            # All primitives pattern
            elif types_set <= {"str", "int", "bool", "float"}:
                suggestion += "\n  • class ModelPrimitiveValue(BaseModel):"
                suggestion += "\n    - value: str | int | bool | float"
                suggestion += "\n    - type_hint: Literal['string', 'integer', 'boolean', 'float']"

            # Mixed primitive/complex pattern
            elif "dict" in types_set or "list" in types_set:
                suggestion += "\n  • class ModelFlexibleData(BaseModel):"
                suggestion += (
                    "\n    - data_type: Literal['primitive', 'collection', 'mapping']"
                )
                suggestion += "\n    - value: Any  # Use specific models for each type"

            # Configuration value pattern (common in CLI models)
            elif len(types_set) >= 5:
                suggestion += "\n  • class ModelConfigurationValue(BaseModel):"
                suggestion += "\n    - raw_value: Any"
                suggestion += (
                    "\n    - parsed_value: str | int | bool | float | Path | UUID"
                )
                suggestion += "\n    - value_type: str"

            # Date/time and value combinations
            elif "datetime" in types_set:
                suggestion += "\n  • class ModelTimestampedValue(BaseModel):"
                suggestion += "\n    - value: str | int | bool | float"
                suggestion += "\n    - timestamp: datetime | None = None"

            # Default model suggestion
            else:
                base_name = types[0].title() if types else "Value"
                suggestion += f"\n  • class Model{base_name}Union(BaseModel):"
                suggestion += f"\n    - value: {' | '.join(types)}"
                suggestion += "\n    - discriminator: str"

            # Add usage information
            locations = [f"{p.file_path}:{p.line}" for p in pattern_list[:3]]
            if len(pattern_list) > 3:
                locations.append(f"... and {len(pattern_list) - 3} more")

            suggestion += f"\n  • Found in {len(pattern_list)} locations:"
            for loc in locations:
                suggestion += f"\n    - {loc}"

            # Add example implementation
            if len(pattern_list) >= 2:
                suggestion += "\n  • Example implementation pattern:"
                if {"str", "int", "bool", "float"}.issubset(types_set):
                    suggestion += "\n    @field_validator('value')"
                    suggestion += "\n    def validate_value_type(cls, v):"
                    suggestion += "\n        return v  # Add specific validation logic"

            suggestions.append(suggestion)

    return suggestions


def main():
    """Enhanced main validation function."""
    parser = argparse.ArgumentParser(
        description="Enhanced Union type usage validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool detects complex Union types that should be replaced with proper models:

• Unions with 3+ types that could be models
• Repeated union patterns across files
• Mixed primitive/complex type unions
• Overly broad unions that should use 'Any' or specific models

Examples of problematic patterns:
• Union[str, int, bool, float] → Value Object model
• Union[str, int, dict] → Discriminated union model
• Union[dict, list, str] → Specific data structure model
        """,
    )
    parser.add_argument(
        "--max-unions", type=int, default=100, help="Maximum allowed Union types"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation mode"
    )
    parser.add_argument(
        "--show-patterns", action="store_true", help="Show repeated pattern analysis"
    )
    parser.add_argument(
        "--suggest-models", action="store_true", help="Generate model suggestions"
    )
    parser.add_argument(
        "--export-report", type=str, help="Export detailed report to file"
    )
    parser.add_argument(
        "--min-complexity",
        type=int,
        default=3,
        help="Minimum union complexity to flag (default: 3)",
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    python_files = list(base_path.rglob("*.py"))

    # Filter out archived files and __pycache__
    python_files = [
        f
        for f in python_files
        if "/archived/" not in str(f)
        and "archived" not in f.parts
        and "__pycache__" not in str(f)
    ]

    if not python_files:
        print("✅ Union validation: No Python files to validate")
        return 0

    total_unions = 0
    total_issues = []
    all_patterns = []

    # Process all files
    for py_file in python_files:
        union_count, issues, patterns = validate_python_file(py_file)
        total_unions += union_count
        all_patterns.extend(patterns)

        if issues:
            total_issues.extend([f"{py_file}: {issue}" for issue in issues])

    # Analyze repeated patterns
    if args.show_patterns or args.strict:
        repeated_issues = analyze_repeated_patterns(all_patterns)
        total_issues.extend(repeated_issues)

    # Generate model suggestions
    suggestions = []
    if args.suggest_models:
        complex_patterns = [
            p for p in all_patterns if p.type_count >= args.min_complexity
        ]
        suggestions = generate_model_suggestions(complex_patterns)
        if suggestions:
            print("\n💡 Model suggestions:")
            for suggestion in suggestions:
                print(f"   {suggestion}")

    # Export detailed report if requested
    if args.export_report:
        export_detailed_report(
            args.export_report,
            total_unions,
            total_issues,
            all_patterns,
            suggestions,
            args.min_complexity,
            python_files,
        )
        print(f"\n📄 Detailed report exported to: {args.export_report}")

    # Report results
    if total_issues:
        print(f"❌ Union validation issues found:")
        for issue in total_issues:
            print(f"   {issue}")

    # Strict mode additional checks
    if args.strict:
        complex_unions = [
            p for p in all_patterns if p.type_count >= args.min_complexity
        ]
        if complex_unions:
            print(
                f"\n⚠️  Strict mode: Found {len(complex_unions)} unions with {args.min_complexity}+ types"
            )
            for pattern in complex_unions[:5]:  # Show first 5
                print(
                    f"   {pattern.file_path}:{pattern.line} - {pattern.get_signature()}"
                )
            if len(complex_unions) > 5:
                print(f"   ... and {len(complex_unions) - 5} more")

    if total_unions > args.max_unions:
        print(f"❌ Union count exceeded: {total_unions} > {args.max_unions}")
        return 1

    if total_issues:
        return 1

    print(
        f"✅ Union validation: {total_unions} unions in {len(python_files)} files "
        f"(limit: {args.max_unions})"
    )

    # Summary statistics
    if all_patterns:
        complex_count = len(
            [p for p in all_patterns if p.type_count >= args.min_complexity]
        )
        if complex_count > 0:
            print(
                f"   📊 {complex_count} complex unions ({args.min_complexity}+ types) found"
            )

    return 0


def export_detailed_report(
    file_path: str,
    total_unions: int,
    total_issues: List[str],
    all_patterns: List[UnionPattern],
    suggestions: List[str],
    min_complexity: int,
    python_files: List[Path],
) -> None:
    """Export a detailed report to a file."""
    import json
    from datetime import datetime

    report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_files_scanned": len(python_files),
            "total_unions_found": total_unions,
            "min_complexity_threshold": min_complexity,
            "total_issues": len(total_issues),
        },
        "summary": {
            "complex_unions": len(
                [p for p in all_patterns if p.type_count >= min_complexity]
            ),
            "primitive_heavy": len(
                [
                    p
                    for p in all_patterns
                    if len([t for t in p.types if t in {"str", "int", "bool", "float"}])
                    >= 3
                ]
            ),
            "repeated_patterns": len(
                set(
                    tuple(sorted(p.types))
                    for p in all_patterns
                    if all_patterns.count(p) >= 2
                )
            ),
        },
        "issues": total_issues,
        "patterns": [
            {
                "signature": p.get_signature(),
                "types": p.types,
                "type_count": p.type_count,
                "file": p.file_path,
                "line": p.line,
            }
            for p in all_patterns
        ],
        "suggestions": suggestions,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        if file_path.endswith(".json"):
            json.dump(report, f, indent=2)
        else:
            # Generate markdown report
            f.write("# Union Type Validation Report\n\n")
            f.write(f"Generated: {report['metadata']['generated_at']}\n\n")
            f.write("## Summary\n\n")
            f.write(
                f"- **Files Scanned**: {report['metadata']['total_files_scanned']}\n"
            )
            f.write(f"- **Total Unions**: {report['metadata']['total_unions_found']}\n")
            f.write(f"- **Complex Unions**: {report['summary']['complex_unions']}\n")
            f.write(f"- **Issues Found**: {report['metadata']['total_issues']}\n\n")

            if total_issues:
                f.write("## Issues\n\n")
                for issue in total_issues:
                    f.write(f"- {issue}\n")
                f.write("\n")

            if suggestions:
                f.write("## Model Suggestions\n\n")
                for suggestion in suggestions:
                    f.write(f"### {suggestion.split(':')[0]}\n\n")
                    f.write(f"```python\n{suggestion}\n```\n\n")

            f.write("## All Union Patterns\n\n")
            for pattern in sorted(
                all_patterns, key=lambda p: p.type_count, reverse=True
            ):
                f.write(
                    f"- `{pattern.get_signature()}` at {pattern.file_path}:{pattern.line}\n"
                )


if __name__ == "__main__":
    sys.exit(main())
