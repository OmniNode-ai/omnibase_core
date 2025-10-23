#!/usr/bin/env python3
"""
Enhanced Union type usage validation for omni* repositories.
Validates that Union types are used properly according to ONEX standards.
Uses AST-based legitimacy validation instead of arbitrary counting.
Ensures unions follow proper typing patterns for strong type safety.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class UnionLegitimacyValidator:
    """Validates the legitimacy of union patterns based on ONEX standards."""

    def __init__(self):
        # Legitimate union patterns
        self.legitimate_patterns = {
            "optional": self._is_optional_pattern,
            "result_monadic": self._is_result_pattern,
            "discriminated": self._is_discriminated_union,
            "model_schema_value": self._is_model_schema_value_pattern,
            "error_handling": self._is_error_handling_pattern,
            "type_narrowing": self._is_type_narrowing_pattern,
            "type_alias_definition": self._is_type_alias_definition,
        }

        # Invalid/lazy patterns to flag
        self.lazy_patterns = {
            "primitive_soup": self._is_primitive_soup,
            "any_contaminated": self._is_any_contaminated,
            "overly_broad": self._is_overly_broad,
            "semantic_mismatch": self._is_semantic_mismatch,
        }

    def validate_union_legitimacy(
        self, union_pattern: UnionPattern, file_content: str | None = None
    ) -> dict[str, Any]:
        """
        Validate if a union pattern is legitimate according to ONEX standards.

        Returns:
            Dict with 'is_legitimate', 'pattern_type', 'issues', 'suggestions'
        """
        result = {
            "is_legitimate": False,
            "pattern_type": None,
            "issues": [],
            "suggestions": [],
            "confidence": 0.0,
        }

        # Check for legitimate patterns first
        for pattern_name, checker in self.legitimate_patterns.items():
            if checker(union_pattern, file_content):
                result["is_legitimate"] = True
                result["pattern_type"] = pattern_name
                result["confidence"] = (
                    0.9
                    if pattern_name in ["optional", "result_monadic", "discriminated"]
                    else 0.7
                )
                return result

        # Check for lazy/invalid patterns
        for pattern_name, checker in self.lazy_patterns.items():
            if checker(union_pattern, file_content):
                result["pattern_type"] = pattern_name
                result["issues"].append(f"Invalid union pattern: {pattern_name}")
                result["suggestions"].extend(
                    self._get_suggestions_for_pattern(pattern_name, union_pattern)
                )
                result["confidence"] = 0.8
                return result

        # If no specific pattern detected, evaluate based on semantics
        result.update(self._evaluate_semantic_legitimacy(union_pattern))
        return result

    def _is_optional_pattern(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a legitimate Optional[T] pattern (T | None)."""
        return len(pattern.types) == 2 and "None" in pattern.types

    def _is_result_pattern(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a Result[T, E] monadic error handling pattern."""
        # Look for Result[T, E] patterns or Result-like discriminated unions
        types = pattern.types

        # Direct Result type usage
        if any("Result[" in t for t in types):
            return True

        # Look for success/error discriminated union pattern
        has_success_variant = any(
            "success" in t.lower() or "ok" in t.lower() for t in types
        )
        has_error_variant = any(
            "error" in t.lower() or "err" in t.lower() for t in types
        )

        return has_success_variant and has_error_variant and len(types) == 2

    def _is_discriminated_union(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a properly discriminated union with Literal discriminators."""
        # Look for Literal types in the union
        has_literal = any("Literal[" in t for t in pattern.types)

        # Check for discriminator-like patterns
        has_type_field = any("type" in t.lower() and '"' in t for t in pattern.types)
        has_kind_field = any("kind" in t.lower() and '"' in t for t in pattern.types)

        # Check for Field(discriminator=) pattern in file content (modern Pydantic approach)
        has_field_discriminator = False
        if file_content:
            # Look for Field(discriminator="field_name") pattern near the union
            import re

            # Pattern to match Field(..., discriminator="...") with flexible parameter order
            # Matches: Field(discriminator="...") or Field(..., discriminator="...") or Field(..., discriminator='...')
            discriminator_pattern = (
                r'Field\s*\([^)]*discriminator\s*=\s*["\'][^"\']+["\']'
            )
            has_field_discriminator = bool(
                re.search(discriminator_pattern, file_content)
            )

        # Must have discriminator indicators and reasonable type count
        return (
            has_literal or has_type_field or has_kind_field or has_field_discriminator
        ) and len(pattern.types) <= 5

    def _is_model_schema_value_pattern(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this uses proper ModelSchemaValue patterns instead of Any."""
        # Look for ModelSchemaValue or strongly typed schema patterns
        has_model_schema = any("ModelSchemaValue" in t for t in pattern.types)
        has_schema_pattern = any("Schema" in t and "Value" in t for t in pattern.types)

        # Avoid Any contamination
        has_any = "Any" in pattern.types

        return (has_model_schema or has_schema_pattern) and not has_any

    def _is_error_handling_pattern(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a legitimate error handling pattern."""
        types = pattern.types

        # Exception handling patterns
        has_exception = any("Exception" in t or "Error" in t for t in types)
        has_success_type = any(t not in ["Exception", "Error", "None"] for t in types)

        return has_exception and has_success_type and len(types) <= 3

    def _is_type_narrowing_pattern(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a legitimate type narrowing pattern."""
        types = pattern.types

        # Type narrowing with related types (e.g., str | Path, int | float)
        if len(types) == 2:
            type_pairs = [
                {"str", "Path"},
                {"int", "float"},
                {"bytes", "str"},
                {"list", "tuple"},
                {"dict", "Mapping"},
            ]

            types_set = set(types)
            return any(types_set == pair for pair in type_pairs)

        return False

    def _is_type_alias_definition(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """
        Check if this is a legitimate type alias definition.

        Type alias definitions in model_onex_common_types.py are canonical
        type definitions that define the ONEX type system. They should be
        exempt from primitive_soup detection because they:
        1. Are in the canonical type definition file
        2. Use recursive forward references (list["TypeAlias"])
        3. Are documented replacements for Any types
        4. Define the type system itself
        """
        # Check if this is in the canonical type definition file
        is_canonical_file = "model_onex_common_types.py" in pattern.file_path

        # Check if this union uses recursive forward references
        # Look for patterns like list["TypeName"] or dict[str, "TypeName"]
        has_recursive_reference = any('"' in str(t) for t in pattern.types)

        # If in canonical file or has recursive references, it's a type alias definition
        if is_canonical_file:
            return True

        # If it has recursive forward references, it's likely a type alias
        if has_recursive_reference:
            return True

        return False

    def _is_primitive_soup(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this is a lazy 'primitive soup' union."""
        primitive_types = {"str", "int", "bool", "float", "bytes"}
        types_set = set(pattern.types)

        # 3+ primitives is usually lazy typing
        primitive_count = len(types_set & primitive_types)
        return primitive_count >= 3 and len(pattern.types) >= 3

    def _is_any_contaminated(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this union contains Any types (anti-pattern)."""
        return "Any" in pattern.types or any("Any" in t for t in pattern.types)

    def _is_overly_broad(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if this union is overly broad without semantic meaning."""
        # 5+ different types usually indicates lack of proper modeling
        if len(pattern.types) >= 5:
            return True

        # Mixed primitive and complex types without clear semantics
        primitive_types = {"str", "int", "bool", "float", "bytes"}
        complex_types = {"dict", "list", "tuple", "set"}

        has_primitives = any(t in primitive_types for t in pattern.types)
        has_complex = any(t in complex_types for t in pattern.types)

        return has_primitives and has_complex and len(pattern.types) >= 4

    def _is_semantic_mismatch(
        self, pattern: UnionPattern, file_content: str | None = None
    ) -> bool:
        """Check if union types have semantic mismatch."""
        # Common anti-patterns
        problematic_combinations = [
            {
                "str",
                "bool",
                "dict",
            },  # String, boolean, and dictionary have no semantic relationship
            {
                "int",
                "list",
                "bool",
            },  # Number, list, and boolean are semantically unrelated
            {"float", "dict", "str", "bool"},  # Too many unrelated types
        ]

        types_set = set(pattern.types)
        return any(combo.issubset(types_set) for combo in problematic_combinations)

    def _evaluate_semantic_legitimacy(self, pattern: UnionPattern) -> dict[str, Any]:
        """Evaluate legitimacy based on semantic coherence when no specific pattern matches."""
        # Default to legitimate for small, coherent unions
        if len(pattern.types) <= 2:
            return {
                "is_legitimate": True,
                "pattern_type": "simple_union",
                "confidence": 0.6,
                "issues": [],
                "suggestions": [],
            }

        # For larger unions, be more conservative
        return {
            "is_legitimate": False,
            "pattern_type": "unclassified_complex",
            "confidence": 0.7,
            "issues": ["Complex union pattern needs review"],
            "suggestions": ["Consider using discriminated union or proper model"],
        }

    def _get_suggestions_for_pattern(
        self, pattern_type: str, pattern: UnionPattern
    ) -> list[str]:
        """Get specific suggestions for improving invalid patterns."""
        suggestions = {
            "primitive_soup": [
                "Replace with specific type (str, int, etc.) if only one type is actually needed",
                'Use TypeVar for generic functions: T = TypeVar("T", str, int, float)',
                "Create discriminated union with Literal discriminator",
                "Consider using ModelSchemaValue with proper type field",
            ],
            "any_contaminated": [
                "Replace Any with specific types",
                "Use ModelSchemaValue instead of Any for schema values",
                "Consider using TypeVar with proper bounds",
            ],
            "overly_broad": [
                "Split into multiple functions with specific types",
                "Create discriminated union with proper discriminator field",
                "Use Protocol or TypeVar for generic behavior",
            ],
            "semantic_mismatch": [
                "Group semantically related types",
                "Create separate functions for different type families",
                "Use discriminated union with clear type categories",
            ],
        }

        return suggestions.get(
            pattern_type, ["Consider using more specific typing patterns"]
        )


class UnionPattern:
    """Represents a Union pattern for analysis."""

    def __init__(self, types: list[str], line: int, file_path: str):
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
    """Enhanced checker for Union type usage patterns with legitimacy validation."""

    def __init__(self, file_path: str, file_content: str | None = None):
        self.union_count = 0
        self.legitimate_union_count = 0
        self.invalid_union_count = 0
        self.issues = []
        self.file_path = file_path
        self.file_content = file_content
        self.union_patterns: list[UnionPattern] = []
        self.legitimacy_validator = UnionLegitimacyValidator()

        # Track patterns by legitimacy
        self.legitimate_patterns: list[UnionPattern] = []
        self.invalid_patterns: list[UnionPattern] = []
        self.validation_results: dict[str, Any] = {}

        # Statistics
        self.pattern_statistics = {
            "optional": 0,
            "result_monadic": 0,
            "discriminated": 0,
            "model_schema_value": 0,
            "error_handling": 0,
            "type_narrowing": 0,
            "type_alias_definition": 0,
            "primitive_soup": 0,
            "any_contaminated": 0,
            "overly_broad": 0,
            "semantic_mismatch": 0,
            "simple_union": 0,
            "unclassified_complex": 0,
        }

    def _extract_type_name(self, node: ast.AST) -> str:
        """Extract type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            # Preserve string constants as quoted names for forward references
            # This allows has_recursive_reference check to detect patterns like list["JsonSerializable"]
            if isinstance(node.value, str):
                return f'"{node.value}"'
            return type(node.value).__name__
        elif isinstance(node, ast.Subscript):
            # Handle list[str], dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                base_type = node.value.id

                # Check if subscript contains forward-reference strings
                # This allows detection of recursive patterns like list["MyType"]
                forward_ref = self._extract_forward_ref_from_subscript(node.slice)
                if forward_ref:
                    # Include forward reference in type name for recursive detection
                    return f'{base_type}["{forward_ref}"]'

                return base_type
        elif isinstance(node, ast.Attribute):
            # Handle module.Type patterns
            return f"{self._extract_type_name(node.value)}.{node.attr}"
        return "Unknown"

    def _extract_forward_ref_from_subscript(self, slice_node: ast.AST) -> str | None:
        """Extract forward-reference string from subscript slice."""
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            # Direct forward reference: list["MyType"]
            return slice_node.value
        elif isinstance(slice_node, ast.Tuple):
            # Multiple subscripts: dict[str, "MyType"]
            for elt in slice_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    return elt.value
        elif isinstance(slice_node, ast.Subscript):
            # Nested subscripts: list[list["MyType"]]
            return self._extract_forward_ref_from_subscript(slice_node.slice)
        return None

    def _has_suppression_comment(self, line_number: int) -> bool:
        """Check if the union has a suppression comment above it."""
        if not self.file_content:
            return False

        lines = self.file_content.split("\n")
        if line_number <= 0 or line_number > len(lines):
            return False

        # AST line numbers are 1-based, convert to 0-based index
        # Check the lines before the union (up to 5 lines before)
        for offset in range(1, min(6, line_number + 1)):
            check_line_idx = line_number - offset - 1  # Convert to 0-based index
            if check_line_idx >= 0 and check_line_idx < len(lines):
                line = lines[check_line_idx].strip()
                # Check for suppression comment formats
                if "# union-ok:" in line or "# ONEX_VALIDATION_IGNORE:" in line:
                    return True
                # Stop searching if we hit a non-comment line
                if line and not line.startswith("#"):
                    break

        return False

    def _analyze_union_pattern(self, union_pattern: UnionPattern) -> None:
        """Analyze a union pattern using legitimacy validation."""
        # Check for suppression comment first
        if self._has_suppression_comment(union_pattern.line):
            # Skip validation for suppressed unions
            self.legitimate_patterns.append(union_pattern)
            self.legitimate_union_count += 1
            return

        # Validate legitimacy using the new validator
        validation_result = self.legitimacy_validator.validate_union_legitimacy(
            union_pattern, self.file_content
        )

        # Store validation result
        pattern_key = f"{union_pattern.file_path}:{union_pattern.line}"
        self.validation_results[pattern_key] = validation_result

        # Update statistics
        pattern_type = validation_result["pattern_type"]
        if pattern_type and pattern_type in self.pattern_statistics:
            self.pattern_statistics[pattern_type] += 1

        # Categorize the pattern
        if validation_result["is_legitimate"]:
            self.legitimate_patterns.append(union_pattern)
            self.legitimate_union_count += 1
        else:
            self.invalid_patterns.append(union_pattern)
            self.invalid_union_count += 1

            # Add issues from validation
            for issue in validation_result["issues"]:
                self.issues.append(
                    f"Line {union_pattern.line}: {issue} - {union_pattern.get_signature()}"
                )

            # Add suggestions as issues for now (can be separated later)
            for suggestion in validation_result["suggestions"]:
                self.issues.append(
                    f"Line {union_pattern.line}: Suggestion - {suggestion}"
                )

        # Check for duplicate types (still relevant)
        if len(set(union_pattern.types)) != len(union_pattern.types):
            unique_types = list(set(union_pattern.types))
            self.issues.append(
                f"Line {union_pattern.line}: Union contains duplicate types "
                f"{union_pattern.get_signature()} → Union[{', '.join(sorted(unique_types))}]"
            )

        # Modern syntax conversion for old Union[T, None] patterns
        if validation_result["pattern_type"] == "optional" and "Union[" in str(
            union_pattern.types
        ):
            non_none_type = next(t for t in union_pattern.types if t != "None")
            # Only suggest conversion if this was written in old Union[] syntax
            # This is a style suggestion, not a legitimacy issue
            # We'll handle this in a separate style checker if needed

    def visit_Subscript(self, node):
        """Visit subscript nodes (e.g., Union[str, int])."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            self._process_union_types(node, node.slice, node.lineno)
        self.generic_visit(node)

    def visit_BinOp(self, node):
        """Visit binary operation nodes (e.g., str | int | float)."""
        if isinstance(node.op, ast.BitOr):
            # Skip bitwise operations and set operations - only process type unions
            if self._is_likely_type_union(node):
                # Modern union syntax: str | int | float
                union_types = self._extract_union_from_binop(node)
                if len(union_types) >= 2:  # Only process if we have multiple types
                    self.union_count += 1

                    # Create union pattern for analysis
                    union_pattern = UnionPattern(
                        union_types, node.lineno, self.file_path
                    )
                    self.union_patterns.append(union_pattern)

                    # Analyze the pattern with legitimacy validation
                    self._analyze_union_pattern(union_pattern)
        self.generic_visit(node)

    def _is_likely_type_union(self, node: ast.BinOp) -> bool:
        """Check if a BinOp with | is likely a type union vs set/bitwise operation."""

        def has_attribute_access(n):
            """Check if node involves attribute access (like re.FLAG)."""
            if isinstance(n, ast.Attribute):
                return True
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                return has_attribute_access(n.left) or has_attribute_access(n.right)
            return False

        def has_variable_reference(n):
            """Check if node is a variable reference (like set1)."""
            if isinstance(n, ast.Name):
                # Simple heuristic: lowercase names are likely variables, not types
                return n.id.islower() and n.id not in {
                    "str",
                    "int",
                    "float",
                    "bool",
                    "bytes",
                }
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                return has_variable_reference(n.left) or has_variable_reference(n.right)
            return False

        # Skip if this looks like bitwise flags (re.FLAG | re.FLAG)
        if has_attribute_access(node):
            return False

        # Skip if this looks like set operations (var1 | var2)
        if has_variable_reference(node):
            return False

        return True

    def _extract_union_from_binop(self, node: ast.BinOp) -> list[str]:
        """Extract union types from modern union syntax (A | B | C)."""
        types = []

        def collect_types(n):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                collect_types(n.left)
                collect_types(n.right)
            else:
                type_name = self._extract_type_name(n)
                if type_name not in types:  # Avoid duplicates
                    types.append(type_name)

        collect_types(node)
        return types

    def _process_union_types(self, node, slice_node, line_no):
        """Process union types from Union[...] syntax."""
        # Extract union types
        union_types = []
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                type_name = self._extract_type_name(elt)
                union_types.append(type_name)
        else:
            # Single element in Union (shouldn't happen, but handle it)
            type_name = self._extract_type_name(slice_node)
            union_types.append(type_name)

        self.union_count += 1

        # Create union pattern for analysis
        union_pattern = UnionPattern(union_types, line_no, self.file_path)
        self.union_patterns.append(union_pattern)

        # Analyze the pattern with legitimacy validation
        self._analyze_union_pattern(union_pattern)


def validate_python_file(file_path: Path) -> dict[str, Any]:
    """Validate Union usage in a Python file with legitimacy analysis."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker(str(file_path), content)
        checker.visit(tree)

        return {
            "union_count": checker.union_count,
            "legitimate_count": checker.legitimate_union_count,
            "invalid_count": checker.invalid_union_count,
            "issues": checker.issues,
            "union_patterns": checker.union_patterns,
            "legitimate_patterns": checker.legitimate_patterns,
            "invalid_patterns": checker.invalid_patterns,
            "pattern_statistics": checker.pattern_statistics,
            "validation_results": checker.validation_results,
        }

    except Exception as e:
        return {
            "union_count": 0,
            "legitimate_count": 0,
            "invalid_count": 0,
            "issues": [f"Error parsing {file_path}: {e}"],
            "union_patterns": [],
            "legitimate_patterns": [],
            "invalid_patterns": [],
            "pattern_statistics": {},
            "validation_results": {},
        }


def analyze_repeated_patterns(all_patterns: list[UnionPattern]) -> list[str]:
    """Analyze repeated union patterns across files."""
    pattern_counts = Counter()
    pattern_files = defaultdict(set)

    for pattern in all_patterns:
        # Skip simple optional patterns (T | None) - these are correct modern syntax
        is_simple_optional = pattern.type_count == 2 and "None" in pattern.types
        if is_simple_optional:
            continue

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


def generate_model_suggestions(patterns: list[UnionPattern]) -> list[str]:
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
                suggestion += "\n  • class ModelValue(BaseModel):"
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
                suggestion += "\n    - value: str | int | bool | float  # Use specific types instead of Any"

            # Configuration value pattern (common in CLI models)
            elif len(types_set) >= 5:
                suggestion += "\n  • class ModelConfigurationValue(BaseModel):"
                suggestion += "\n    - raw_value: str | int | bool | float"
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
    """Enhanced main validation function with AST-based legitimacy validation."""
    parser = argparse.ArgumentParser(
        description="Enhanced Union type usage validation with legitimacy analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool validates Union types based on legitimacy patterns rather than arbitrary counting:

LEGITIMATE PATTERNS:
• Optional[T] or T | None patterns
• Result[T, E] monadic error handling
• Discriminated unions with Literal discriminators
• ModelSchemaValue patterns for typed schemas
• Type narrowing patterns (str | Path, int | float)

INVALID PATTERNS:
• Primitive soup unions (str | int | bool | float)
• Any-contaminated unions
• Overly broad unions without semantic meaning
• Semantically mismatched type combinations

The validator focuses on type safety and semantic coherence rather than arbitrary limits.
        """,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode (fail on any invalid patterns)",
    )
    parser.add_argument(
        "--show-patterns", action="store_true", help="Show detailed pattern analysis"
    )
    parser.add_argument(
        "--show-statistics", action="store_true", help="Show pattern type statistics"
    )
    parser.add_argument(
        "--suggest-models",
        action="store_true",
        help="Generate model suggestions for invalid patterns",
    )
    parser.add_argument(
        "--export-report", type=str, help="Export detailed legitimacy report to file"
    )
    parser.add_argument(
        "--allow-invalid",
        type=int,
        default=0,
        help="Maximum allowed invalid union patterns (default: 0)",
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    if base_path.is_file() and base_path.suffix == ".py":
        python_files = [base_path]
    else:
        python_files = list(base_path.rglob("*.py"))
        # Sort files for deterministic order across different systems
        python_files.sort(key=lambda p: str(p))

    # Filter out archived files, examples, and __pycache__
    python_files = [
        f
        for f in python_files
        if "/archived/" not in str(f)
        and "archived" not in f.parts
        and "/archive/" not in str(f)
        and "archive" not in f.parts
        and "/examples/" not in str(f)
        and "examples" not in f.parts
        and "__pycache__" not in str(f)
    ]

    if not python_files:
        print("✅ Union validation: No Python files to validate")
        return 0

    # Initialize counters
    total_unions = 0
    total_legitimate = 0
    total_invalid = 0
    total_issues = []
    all_patterns = []
    all_legitimate_patterns = []
    all_invalid_patterns = []
    global_statistics = {}

    # Process all files
    for py_file in python_files:
        file_result = validate_python_file(py_file)

        total_unions += file_result["union_count"]
        total_legitimate += file_result["legitimate_count"]
        total_invalid += file_result["invalid_count"]
        all_patterns.extend(file_result["union_patterns"])
        all_legitimate_patterns.extend(file_result["legitimate_patterns"])
        all_invalid_patterns.extend(file_result["invalid_patterns"])

        # Aggregate statistics
        for pattern_type, count in file_result["pattern_statistics"].items():
            global_statistics[pattern_type] = (
                global_statistics.get(pattern_type, 0) + count
            )

        if file_result["issues"]:
            total_issues.extend(
                [f"{py_file}: {issue}" for issue in file_result["issues"]]
            )

    # Analyze repeated patterns for invalid unions only
    if args.show_patterns:
        repeated_issues = analyze_repeated_patterns(all_invalid_patterns)
        total_issues.extend(repeated_issues)

    # Show pattern statistics
    if args.show_statistics:
        print("\n📊 Union Pattern Statistics:")
        legitimate_stats = {
            k: v
            for k, v in global_statistics.items()
            if k
            in [
                "optional",
                "result_monadic",
                "discriminated",
                "model_schema_value",
                "error_handling",
                "type_narrowing",
                "type_alias_definition",
                "simple_union",
            ]
        }
        invalid_stats = {
            k: v
            for k, v in global_statistics.items()
            if k
            in [
                "primitive_soup",
                "any_contaminated",
                "overly_broad",
                "semantic_mismatch",
                "unclassified_complex",
            ]
        }

        if legitimate_stats:
            print("   ✅ Legitimate patterns:")
            for pattern_type, count in legitimate_stats.items():
                if count > 0:
                    print(f"      {pattern_type}: {count}")

        if invalid_stats:
            print("   ❌ Invalid patterns:")
            for pattern_type, count in invalid_stats.items():
                if count > 0:
                    print(f"      {pattern_type}: {count}")

    # Generate model suggestions for invalid patterns
    suggestions = []
    if args.suggest_models and all_invalid_patterns:
        suggestions = generate_model_suggestions(all_invalid_patterns)
        if suggestions:
            print("\n💡 Model suggestions for invalid patterns:")
            for suggestion in suggestions[:3]:  # Show first 3
                print(f"   {suggestion}")
            if len(suggestions) > 3:
                print(f"   ... and {len(suggestions) - 3} more suggestions")

    # Export detailed report if requested
    if args.export_report:
        export_legitimacy_report(
            args.export_report,
            total_unions,
            total_legitimate,
            total_invalid,
            total_issues,
            all_patterns,
            all_legitimate_patterns,
            all_invalid_patterns,
            global_statistics,
            suggestions,
            python_files,
        )
        print(f"\n📄 Detailed legitimacy report exported to: {args.export_report}")

    # Report validation results
    print("\n📈 Union Validation Results:")
    print(f"   Total unions found: {total_unions}")
    print(f"   Legitimate unions: {total_legitimate}")
    print(f"   Invalid unions: {total_invalid}")

    if total_issues:
        print("\n❌ Union legitimacy issues found:")
        for issue in total_issues[:10]:  # Show first 10
            print(f"   {issue}")
        if len(total_issues) > 10:
            print(f"   ... and {len(total_issues) - 10} more issues")

    # Determine validation outcome
    validation_failed = False

    # Check invalid union count against threshold
    if total_invalid > args.allow_invalid:
        print(
            f"\n❌ Too many invalid unions: {total_invalid} > {args.allow_invalid} (allowed)"
        )
        validation_failed = True

    # Strict mode: fail on any invalid patterns
    if args.strict and total_invalid > 0:
        print(f"\n❌ Strict mode: Found {total_invalid} invalid union patterns")
        if all_invalid_patterns:
            print("   Invalid patterns:")
            for pattern in all_invalid_patterns[:5]:
                print(
                    f"      {pattern.file_path}:{pattern.line} - {pattern.get_signature()}"
                )
            if len(all_invalid_patterns) > 5:
                print(f"      ... and {len(all_invalid_patterns) - 5} more")
        validation_failed = True

    if validation_failed:
        return 1

    # Success message
    legitimacy_ratio = (
        (total_legitimate / total_unions * 100) if total_unions > 0 else 100
    )
    print(f"\n✅ Union validation passed: {legitimacy_ratio:.1f}% legitimate unions")
    print(f"   📁 Scanned {len(python_files)} Python files")
    print(
        f"   🎯 Found {total_legitimate} legitimate unions, {total_invalid} invalid unions"
    )

    return 0


def export_legitimacy_report(
    file_path: str,
    total_unions: int,
    total_legitimate: int,
    total_invalid: int,
    total_issues: list[str],
    all_patterns: list[UnionPattern],
    legitimate_patterns: list[UnionPattern],
    invalid_patterns: list[UnionPattern],
    global_statistics: dict[str, int],
    suggestions: list[str],
    python_files: list[Path],
) -> None:
    """Export a detailed legitimacy-based report to a file."""
    import json
    from datetime import datetime

    report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_files_scanned": len(python_files),
            "validation_approach": "ast_based_legitimacy",
            "tool_version": "2.0_legitimacy_enhanced",
        },
        "summary": {
            "total_unions": total_unions,
            "legitimate_unions": total_legitimate,
            "invalid_unions": total_invalid,
            "legitimacy_ratio": (
                (total_legitimate / total_unions * 100) if total_unions > 0 else 100
            ),
            "total_issues": len(total_issues),
        },
        "pattern_statistics": global_statistics,
        "legitimate_patterns": [
            {
                "signature": p.get_signature(),
                "types": p.types,
                "type_count": p.type_count,
                "file": p.file_path,
                "line": p.line,
            }
            for p in legitimate_patterns
        ],
        "invalid_patterns": [
            {
                "signature": p.get_signature(),
                "types": p.types,
                "type_count": p.type_count,
                "file": p.file_path,
                "line": p.line,
            }
            for p in invalid_patterns
        ],
        "issues": total_issues,
        "suggestions": suggestions,
        "legitimacy_criteria": {
            "legitimate_types": [
                "optional: T | None patterns",
                "result_monadic: Result[T, E] error handling",
                "discriminated: Unions with Literal discriminators",
                "model_schema_value: Proper ModelSchemaValue usage",
                "error_handling: Exception handling patterns",
                "type_narrowing: Related type narrowing (str | Path)",
                "type_alias_definition: Type alias definitions with recursive forward references",
                "simple_union: Small coherent unions",
            ],
            "invalid_types": [
                "primitive_soup: 3+ primitive types without semantic meaning",
                "any_contaminated: Unions containing Any types",
                "overly_broad: 5+ types or mixed primitive/complex without semantics",
                "semantic_mismatch: Unrelated type combinations",
                "unclassified_complex: Complex patterns needing review",
            ],
        },
    }

    with open(file_path, "w", encoding="utf-8") as f:
        if file_path.endswith(".json"):
            json.dump(report, f, indent=2)
        else:
            # Generate markdown report
            f.write("# Union Type Legitimacy Validation Report\n\n")
            f.write(f"Generated: {report['metadata']['generated_at']}\n")
            f.write("Validation Approach: AST-based Legitimacy Analysis\n\n")

            f.write("## Executive Summary\n\n")
            f.write(
                f"- **Files Scanned**: {report['metadata']['total_files_scanned']}\n"
            )
            f.write(f"- **Total Unions**: {report['summary']['total_unions']}\n")
            f.write(
                f"- **Legitimate Unions**: {report['summary']['legitimate_unions']}\n"
            )
            f.write(f"- **Invalid Unions**: {report['summary']['invalid_unions']}\n")
            f.write(
                f"- **Legitimacy Ratio**: {report['summary']['legitimacy_ratio']:.1f}%\n"
            )
            f.write(f"- **Issues Found**: {report['summary']['total_issues']}\n\n")

            if global_statistics:
                f.write("## Pattern Statistics\n\n")
                legitimate_stats = {
                    k: v
                    for k, v in global_statistics.items()
                    if k
                    in [
                        "optional",
                        "result_monadic",
                        "discriminated",
                        "model_schema_value",
                        "error_handling",
                        "type_narrowing",
                        "type_alias_definition",
                        "simple_union",
                    ]
                    and v > 0
                }
                invalid_stats = {
                    k: v
                    for k, v in global_statistics.items()
                    if k
                    in [
                        "primitive_soup",
                        "any_contaminated",
                        "overly_broad",
                        "semantic_mismatch",
                        "unclassified_complex",
                    ]
                    and v > 0
                }

                if legitimate_stats:
                    f.write("### ✅ Legitimate Patterns\n\n")
                    for pattern_type, count in legitimate_stats.items():
                        f.write(f"- **{pattern_type}**: {count}\n")
                    f.write("\n")

                if invalid_stats:
                    f.write("### ❌ Invalid Patterns\n\n")
                    for pattern_type, count in invalid_stats.items():
                        f.write(f"- **{pattern_type}**: {count}\n")
                    f.write("\n")

            if total_issues:
                f.write("## Issues Found\n\n")
                for issue in total_issues:
                    f.write(f"- {issue}\n")
                f.write("\n")

            if suggestions:
                f.write("## Model Suggestions\n\n")
                for suggestion in suggestions:
                    f.write("### Suggestion\n\n")
                    f.write(f"```\n{suggestion}\n```\n\n")

            f.write("## Legitimacy Criteria\n\n")
            f.write("### ✅ Legitimate Pattern Types\n\n")
            for criteria in report["legitimacy_criteria"]["legitimate_types"]:
                f.write(f"- {criteria}\n")

            f.write("\n### ❌ Invalid Pattern Types\n\n")
            for criteria in report["legitimacy_criteria"]["invalid_types"]:
                f.write(f"- {criteria}\n")


def export_detailed_report(
    file_path: str,
    total_unions: int,
    total_issues: list[str],
    all_patterns: list[UnionPattern],
    suggestions: list[str],
    min_complexity: int,
    python_files: list[Path],
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
                {
                    tuple(sorted(p.types))
                    for p in all_patterns
                    if all_patterns.count(p) >= 2
                }
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
