#!/usr/bin/env python3
"""
Fix Pydantic missing field errors using AST-based code transformation.

This script:
1. Parses Python files using AST
2. Identifies Pydantic model instantiations with missing optional fields
3. Adds missing fields with appropriate default values
4. Preserves code formatting and comments where possible

Usage:
    # Dry run (preview changes)
    poetry run python scripts/fix_pydantic_missing_fields.py --dry-run

    # Fix specific file
    poetry run python scripts/fix_pydantic_missing_fields.py --file src/path/to/file.py

    # Fix all files
    poetry run python scripts/fix_pydantic_missing_fields.py --all

    # Fix with backup
    poetry run python scripts/fix_pydantic_missing_fields.py --all --backup
"""

import argparse
import ast
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FieldInfo:
    """Information about a Pydantic model field."""

    name: str
    type_annotation: str
    has_default: bool
    default_value: Any = None
    is_optional: bool = False


@dataclass
class ModelInfo:
    """Information about a Pydantic model."""

    name: str
    file_path: Path
    fields: dict[str, FieldInfo] = field(default_factory=dict)


@dataclass
class FixResult:
    """Result of a fix operation."""

    file_path: str
    line_number: int
    model_name: str
    fields_added: list[str]
    original_code: str
    fixed_code: str
    success: bool
    error_message: str | None = None


class PydanticModelAnalyzer:
    """Analyzes Pydantic models to extract field information."""

    def __init__(self):
        self.models: dict[str, ModelInfo] = {}

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a file to extract Pydantic model definitions."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Pydantic model (inherits from BaseModel)
                    if self._is_pydantic_model(node):
                        model_info = self._extract_model_info(node, file_path)
                        self.models[model_info.name] = model_info

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    def _is_pydantic_model(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is a Pydantic model."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                return True
        return False

    def _extract_model_info(
        self, class_node: ast.ClassDef, file_path: Path
    ) -> ModelInfo:
        """Extract field information from a Pydantic model."""
        model = ModelInfo(name=class_node.name, file_path=file_path)

        for node in class_node.body:
            if isinstance(node, ast.AnnAssign):
                field_info = self._extract_field_info(node)
                if field_info:
                    model.fields[field_info.name] = field_info

        return model

    def _extract_field_info(self, ann_assign: ast.AnnAssign) -> FieldInfo | None:
        """Extract field information from an annotated assignment."""
        if not isinstance(ann_assign.target, ast.Name):
            return None

        field_name = ann_assign.target.id
        type_annotation = ast.unparse(ann_assign.annotation)

        # Check if field has default value
        has_default = ann_assign.value is not None
        default_value = None

        # Determine if optional (has None in union or has default)
        is_optional = (
            "None" in type_annotation
            or ("|" in type_annotation and "None" in type_annotation)
            or "Optional" in type_annotation
        )

        if has_default:
            # Try to extract default value
            if isinstance(ann_assign.value, ast.Call):
                # Field(...) or Field(default=...)
                for keyword in ann_assign.value.keywords:
                    if keyword.arg == "default" or keyword.arg is None:
                        default_value = ast.unparse(keyword.value)
                        break
                else:
                    # Check positional args (old syntax)
                    if ann_assign.value.args:
                        default_value = ast.unparse(ann_assign.value.args[0])
            else:
                default_value = ast.unparse(ann_assign.value)

        return FieldInfo(
            name=field_name,
            type_annotation=type_annotation,
            has_default=has_default,
            default_value=default_value,
            is_optional=is_optional,
        )


class PydanticFieldFixer:
    """Fixes Pydantic model instantiation errors."""

    def __init__(self, analyzer: PydanticModelAnalyzer, dry_run: bool = False):
        self.analyzer = analyzer
        self.dry_run = dry_run
        self.fixes: list[FixResult] = []

    def get_default_value_for_field(self, field_info: FieldInfo) -> str:
        """Generate appropriate default value for a field."""
        # If field already has a default, use it
        if field_info.default_value:
            if field_info.default_value == "None":
                return "None"
            if field_info.default_value.startswith("Field("):
                # Extract default from Field()
                match = re.search(r"default=([^,)]+)", field_info.default_value)
                if match:
                    return match.group(1)
                return "None"  # Field() without explicit default
            return field_info.default_value

        # Generate appropriate default based on type
        type_str = field_info.type_annotation.lower()

        if field_info.is_optional or "none" in type_str:
            return "None"

        # Try to infer from type
        if "str" in type_str:
            return '""'
        elif "int" in type_str:
            return "0"
        elif "float" in type_str:
            return "0.0"
        elif "bool" in type_str:
            return "False"
        elif "list" in type_str:
            return "[]"
        elif "dict" in type_str:
            return "{}"
        else:
            return "None"  # Conservative default

    def fix_file(
        self, file_path: Path, errors: list[dict[str, Any]]
    ) -> list[FixResult]:
        """Fix Pydantic errors in a single file."""
        results = []

        if not errors:
            return results

        try:
            content = file_path.read_text()
            lines = content.split("\n")

            # Group errors by line number
            errors_by_line: dict[int, list[dict[str, Any]]] = {}
            for error in errors:
                line_num = error["line"] - 1  # Convert to 0-indexed
                if line_num not in errors_by_line:
                    errors_by_line[line_num] = []
                errors_by_line[line_num].append(error)

            # Process each line with errors
            modifications = []
            for line_num, line_errors in sorted(errors_by_line.items()):
                result = self._fix_line(
                    lines[line_num], line_errors, file_path, line_num + 1
                )
                if result:
                    modifications.append((line_num, result))
                    results.append(result)

            # Apply modifications (in reverse order to preserve line numbers)
            if modifications and not self.dry_run:
                for line_num, result in reversed(modifications):
                    if result.success:
                        lines[line_num] = result.fixed_code

                # Write back to file
                new_content = "\n".join(lines)
                file_path.write_text(new_content)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return results

    def _fix_line(
        self,
        line: str,
        errors: list[dict[str, Any]],
        file_path: Path,
        line_number: int,
    ) -> FixResult | None:
        """Fix a single line with missing field errors."""
        # Get model name from first error
        if not errors:
            return None

        model_name = errors[0].get("model")
        if not model_name or model_name not in self.analyzer.models:
            return FixResult(
                file_path=str(file_path),
                line_number=line_number,
                model_name=model_name or "unknown",
                fields_added=[],
                original_code=line,
                fixed_code=line,
                success=False,
                error_message=f"Model {model_name} not found in analyzer",
            )

        model_info = self.analyzer.models[model_name]

        # Extract missing fields
        missing_fields = [e["field"] for e in errors if e.get("field")]

        # Parse the line to find the constructor call
        try:
            # Find the constructor call pattern: ModelName(...)
            pattern = rf"\b{model_name}\s*\("
            match = re.search(pattern, line)
            if not match:
                return None

            # Extract current arguments
            start_pos = match.end()
            # Find matching closing paren (simple approach)
            paren_count = 1
            end_pos = start_pos
            while end_pos < len(line) and paren_count > 0:
                if line[end_pos] == "(":
                    paren_count += 1
                elif line[end_pos] == ")":
                    paren_count -= 1
                end_pos += 1

            current_args = line[start_pos : end_pos - 1]

            # Build new arguments
            new_args_parts = []
            if current_args.strip():
                new_args_parts.append(current_args.rstrip(",").rstrip())

            # Add missing fields with defaults
            for field_name in missing_fields:
                if field_name in model_info.fields:
                    field_info = model_info.fields[field_name]
                    default_value = self.get_default_value_for_field(field_info)
                    new_args_parts.append(f"{field_name}={default_value}")

            new_args = ", ".join(new_args_parts)

            # Reconstruct the line
            fixed_line = line[: match.end()] + new_args + line[end_pos - 1 :]

            return FixResult(
                file_path=str(file_path),
                line_number=line_number,
                model_name=model_name,
                fields_added=missing_fields,
                original_code=line,
                fixed_code=fixed_line,
                success=True,
            )

        except Exception as e:
            return FixResult(
                file_path=str(file_path),
                line_number=line_number,
                model_name=model_name,
                fields_added=[],
                original_code=line,
                fixed_code=line,
                success=False,
                error_message=str(e),
            )


def load_error_report(report_path: Path) -> dict[str, Any]:
    """Load error report from JSON."""
    return json.loads(report_path.read_text())


def group_errors_by_file(
    errors: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group errors by file path."""
    by_file: dict[str, list[dict[str, Any]]] = {}
    for error in errors:
        file_path = error["file"]
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(error)
    return by_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fix Pydantic missing field errors")
    parser.add_argument(
        "--file",
        type=Path,
        help="Fix a specific file",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fix all files with errors",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backups before modifying files",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("pydantic_errors_report.json"),
        help="Error report JSON file (default: pydantic_errors_report.json)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.all:
        parser.error("Must specify either --file or --all")

    if not args.report.exists():
        print(f"Error report not found: {args.report}")
        print("Run analyze_pydantic_errors.py first to generate the report")
        return 1

    # Load error report
    print(f"Loading error report from {args.report}...")
    report = load_error_report(args.report)
    all_errors = report["errors"]

    # Filter for missing_argument errors only
    fixable_errors = [e for e in all_errors if e["type"] == "missing_argument"]
    print(f"Found {len(fixable_errors)} fixable errors (missing_argument)")

    # Group by file
    errors_by_file = group_errors_by_file(fixable_errors)

    # Filter files if specific file requested
    if args.file:
        target_file = str(args.file)
        if target_file not in errors_by_file:
            print(f"No errors found for {target_file}")
            return 0
        errors_by_file = {target_file: errors_by_file[target_file]}

    print(f"Processing {len(errors_by_file)} files...")

    # Analyze all model files first
    print("Analyzing Pydantic models...")
    analyzer = PydanticModelAnalyzer()

    # Analyze all Python files in src/omnibase_core/models
    model_files = Path("src/omnibase_core/models").rglob("*.py")
    for model_file in model_files:
        analyzer.analyze_file(model_file)

    print(f"Found {len(analyzer.models)} Pydantic models")

    # Create fixer
    fixer = PydanticFieldFixer(analyzer, dry_run=args.dry_run)

    # Process files
    all_results = []
    for file_path, errors in errors_by_file.items():
        file_path_obj = Path(file_path)

        # Create backup if requested
        if args.backup and not args.dry_run:
            backup_path = file_path_obj.with_suffix(file_path_obj.suffix + ".bak")
            shutil.copy2(file_path_obj, backup_path)
            print(f"Created backup: {backup_path}")

        # Fix the file
        results = fixer.fix_file(file_path_obj, errors)
        all_results.extend(results)

        # Print results
        for result in results:
            if result.success:
                print(f"\n✓ Fixed {result.file_path}:{result.line_number}")
                print(f"  Model: {result.model_name}")
                print(f"  Added fields: {', '.join(result.fields_added)}")
                if args.dry_run:
                    print(f"  Before: {result.original_code.strip()}")
                    print(f"  After:  {result.fixed_code.strip()}")
            else:
                print(f"\n✗ Failed {result.file_path}:{result.line_number}")
                print(f"  Error: {result.error_message}")

    # Summary
    print("\n" + "=" * 80)
    successful = sum(1 for r in all_results if r.success)
    failed = sum(1 for r in all_results if not r.success)

    print("SUMMARY:")
    print(f"  Total fixes attempted: {len(all_results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if args.dry_run:
        print("\n  DRY RUN - No files were modified")
    else:
        print("\n  Files have been updated")

    print("=" * 80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
