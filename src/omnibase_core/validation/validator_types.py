from __future__ import annotations

"""
Type validation tools for ONEX compliance.

This module provides validation functions for proper type usage:
- Union type validation
- String typing anti-pattern detection
- Pydantic pattern validation
- Generic type validation
"""

import argparse
import ast
import sys
from pathlib import Path

from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern

from .union_usage_checker import UnionUsageChecker
from .validation_utils import ModelValidationResult


def validate_union_usage_file(
    file_path: Path,
) -> tuple[int, list[str], list[ModelUnionPattern]]:
    """Validate Union usage in a Python file.

    Returns a tuple of (union_count, issues, patterns).
    Errors are returned as issues in the list, not raised.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker(str(file_path))
        checker.visit(tree)

        return checker.union_count, checker.issues, checker.union_patterns

    except FileNotFoundError as e:
        # Return file not found error as an issue
        return 0, [f"Error: File not found: {e}"], []
    except SyntaxError as e:
        # Return syntax error as an issue
        return 0, [f"Error parsing {file_path}: {e}"], []
    except (
        Exception
    ) as e:  # fallback-ok: Validation errors are returned as issues, not raised
        # Return other errors as issues
        return 0, [f"Failed to validate union usage in {file_path}: {e}"], []


def validate_union_usage_directory(
    directory: Path, max_unions: int = 100, strict: bool = False
) -> ModelValidationResult[None]:
    """Validate Union usage in a directory."""
    python_files = []
    for py_file in directory.rglob("*.py"):
        # Filter out archived files, examples, and __pycache__
        if any(
            part in str(py_file)
            for part in [
                "/archived/",
                "archived",
                "/archive/",
                "archive",
                "/examples/",
                "examples",
                "__pycache__",
            ]
        ):
            continue
        python_files.append(py_file)

    if not python_files:
        return ModelValidationResult(
            is_valid=True,
            errors=[],
            metadata=ModelValidationMetadata(
                files_processed=0,
            ),
        )

    total_unions = 0
    total_issues = []
    all_patterns = []

    # Process all files
    for py_file in python_files:
        union_count, issues, patterns = validate_union_usage_file(py_file)
        total_unions += union_count
        all_patterns.extend(patterns)

        if issues:
            total_issues.extend([f"{py_file}: {issue}" for issue in issues])

    is_valid = (total_unions <= max_unions) and (not total_issues or not strict)

    return ModelValidationResult(
        is_valid=is_valid,
        errors=total_issues,
        metadata=ModelValidationMetadata(
            validation_type="union_usage",
            files_processed=len(python_files),
            violations_found=len(total_issues),
            total_unions=total_unions,
            max_unions=max_unions,
            complex_patterns=len([p for p in all_patterns if p.type_count >= 3]),
            strict_mode=strict,
        ),
    )


def validate_union_usage_cli() -> int:
    """CLI interface for union usage validation."""
    parser = argparse.ArgumentParser(
        description="Enhanced Union type usage validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool detects complex Union types that should be replaced with proper models:

• Unions with 3+ types that could be models
• Repeated union patterns across files
• Mixed primitive/complex type unions
• Overly broad unions that should use specific types, generics, or strongly-typed models

Examples of problematic patterns:
• Union[str, int, bool, float] → Use specific type (str), generic TypeVar, or domain-specific model
• Union[str, int, dict[str, Any]] → Use specific type or generic TypeVar
• Union[dict[str, Any], list[Any], str] → Use specific collection type or generic
        """,
    )
    parser.add_argument(
        "--max-unions", type=int, default=100, help="Maximum allowed Union types"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation mode"
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    if base_path.is_file() and base_path.suffix == ".py":
        # Single file validation
        union_count, issues, _ = validate_union_usage_file(base_path)

        if issues:
            print(f"❌ Union validation issues found in {base_path}:")
            for issue in issues:
                print(f"   {issue}")
            return 1

        print(
            f"✅ Union validation: {union_count} unions in {base_path} (limit: {args.max_unions})"
        )
        return 0
    # Directory validation
    result = validate_union_usage_directory(base_path, args.max_unions, args.strict)

    if result.errors:
        print("❌ Union validation issues found:")
        for error in result.errors:
            print(f"   {error}")

    total_unions = (
        result.metadata.total_unions
        if result.metadata and result.metadata.total_unions is not None
        else 0
    )
    if total_unions > args.max_unions:
        print(f"❌ Union count exceeded: {total_unions} > {args.max_unions}")
        return 1

    if result.errors:
        return 1

    total_unions_final = (
        result.metadata.total_unions
        if result.metadata and result.metadata.total_unions is not None
        else 0
    )
    files_processed = (
        result.metadata.files_processed
        if result.metadata and result.metadata.files_processed is not None
        else 0
    )
    print(
        f"✅ Union validation: {total_unions_final} unions in {files_processed} files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(validate_union_usage_cli())
