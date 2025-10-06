#!/usr/bin/env python3
"""
Analyze Pydantic call-arg errors from mypy output.

This script parses mypy errors, categorizes them by type, and provides
detailed statistics to guide automated fixing.

Usage:
    poetry run python scripts/analyze_pydantic_errors.py
    poetry run python scripts/analyze_pydantic_errors.py --output report.json
"""

import argparse
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PydanticError:
    """Represents a single Pydantic error from mypy."""

    file_path: str
    line_number: int
    error_type: str
    model_name: str | None
    field_name: str | None
    full_message: str

    @classmethod
    def from_mypy_line(cls, line: str) -> "PydanticError | None":
        """Parse a mypy error line into a PydanticError object."""
        # Pattern: file.py:123: error: Message [call-arg]
        match = re.match(r"^([^:]+):(\d+): error: (.+) \[call-arg\]$", line.strip())
        if not match:
            return None

        file_path, line_num, message = match.groups()

        # Determine error type and extract details
        error_type = "unknown"
        model_name = None
        field_name = None

        if "Missing named argument" in message:
            error_type = "missing_argument"
            # Extract: Missing named argument "field_name" for "ModelName"
            arg_match = re.search(
                r'Missing named argument "([^"]+)" for "([^"]+)"', message
            )
            if arg_match:
                field_name = arg_match.group(1)
                model_name = arg_match.group(2)

        elif "Unexpected keyword argument" in message:
            error_type = "unexpected_argument"
            # Extract: Unexpected keyword argument "arg_name" for "method_name"
            arg_match = re.search(
                r'Unexpected keyword argument "([^"]+)" for "([^"]+)"', message
            )
            if arg_match:
                field_name = arg_match.group(1)
                model_name = arg_match.group(2)

        elif "Too many arguments" in message:
            error_type = "too_many_arguments"
            arg_match = re.search(r'for "([^"]+)"', message)
            if arg_match:
                model_name = arg_match.group(1)

        elif "Missing positional argument" in message:
            error_type = "missing_positional"
            arg_match = re.search(r'Missing positional argument "([^"]+)"', message)
            if arg_match:
                field_name = arg_match.group(1)

        return cls(
            file_path=file_path,
            line_number=int(line_num),
            error_type=error_type,
            model_name=model_name,
            field_name=field_name,
            full_message=message,
        )


class PydanticErrorAnalyzer:
    """Analyzes Pydantic call-arg errors and generates reports."""

    def __init__(self):
        self.errors: list[PydanticError] = []
        self.stats: dict[str, Any] = {}

    def run_mypy(self) -> list[str]:
        """Run mypy and capture call-arg errors."""
        print("Running mypy to collect call-arg errors...")
        result = subprocess.run(
            ["poetry", "run", "mypy", "src/omnibase_core/"],
            capture_output=True,
            text=True,
        )

        # Combine stdout and stderr, filter for call-arg errors
        output = result.stdout + result.stderr
        errors = [line for line in output.split("\n") if "[call-arg]" in line]

        print(f"Found {len(errors)} call-arg errors")
        return errors

    def parse_errors(self, error_lines: list[str]) -> None:
        """Parse mypy error lines into structured objects."""
        for line in error_lines:
            error = PydanticError.from_mypy_line(line)
            if error:
                self.errors.append(error)

    def generate_statistics(self) -> dict[str, Any]:
        """Generate comprehensive statistics about errors."""
        stats: dict[str, Any] = {
            "total_errors": len(self.errors),
            "unique_files": len(set(e.file_path for e in self.errors)),
            "by_error_type": defaultdict(int),
            "by_model": defaultdict(int),
            "by_field": defaultdict(int),
            "by_file": defaultdict(int),
            "top_models": [],
            "top_fields": [],
            "top_files": [],
        }

        # Count by category
        for error in self.errors:
            stats["by_error_type"][error.error_type] += 1

            if error.model_name:
                stats["by_model"][error.model_name] += 1

            if error.field_name:
                stats["by_field"][error.field_name] += 1

            stats["by_file"][error.file_path] += 1

        # Get top 20 for each category
        stats["top_models"] = sorted(
            stats["by_model"].items(), key=lambda x: x[1], reverse=True
        )[:20]

        stats["top_fields"] = sorted(
            stats["by_field"].items(), key=lambda x: x[1], reverse=True
        )[:20]

        stats["top_files"] = sorted(
            stats["by_file"].items(), key=lambda x: x[1], reverse=True
        )[:20]

        # Convert defaultdicts to regular dicts for JSON serialization
        stats["by_error_type"] = dict(stats["by_error_type"])
        stats["by_model"] = dict(stats["by_model"])
        stats["by_field"] = dict(stats["by_field"])
        stats["by_file"] = dict(stats["by_file"])

        self.stats = stats
        return stats

    def print_report(self) -> None:
        """Print a formatted analysis report."""
        stats = self.stats

        print("\n" + "=" * 80)
        print("PYDANTIC CALL-ARG ERROR ANALYSIS REPORT")
        print("=" * 80)

        print(f"\nTotal Errors: {stats['total_errors']}")
        print(f"Unique Files: {stats['unique_files']}")

        print("\n--- Error Types ---")
        for error_type, count in sorted(
            stats["by_error_type"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {error_type}: {count}")

        print("\n--- Top 15 Models with Most Errors ---")
        for model, count in stats["top_models"][:15]:
            print(f"  {model}: {count}")

        print("\n--- Top 15 Fields with Most Errors ---")
        for field, count in stats["top_fields"][:15]:
            print(f"  {field}: {count}")

        print("\n--- Top 10 Files with Most Errors ---")
        for file_path, count in stats["top_files"][:10]:
            file_name = Path(file_path).name
            print(f"  {file_name}: {count}")

        print("\n" + "=" * 80)

        # Recommendations
        print("\nRECOMMENDATIONS:")
        missing_arg_count = stats["by_error_type"].get("missing_argument", 0)
        unexpected_arg_count = stats["by_error_type"].get("unexpected_argument", 0)

        if missing_arg_count > 0:
            print(f"\n1. Fix {missing_arg_count} missing argument errors:")
            print("   - Use fix_pydantic_missing_fields.py to add default values")
            print("   - Or update Field() syntax to use default= parameter")

        if unexpected_arg_count > 0:
            print(f"\n2. Fix {unexpected_arg_count} unexpected argument errors:")
            print("   - Use fix_pydantic_field_names.py to update field names")
            print("   - Check for renamed or deprecated parameters")

        print("\n" + "=" * 80)

    def save_report(self, output_path: Path) -> None:
        """Save detailed report as JSON."""
        report = {
            "statistics": self.stats,
            "errors": [
                {
                    "file": e.file_path,
                    "line": e.line_number,
                    "type": e.error_type,
                    "model": e.model_name,
                    "field": e.field_name,
                    "message": e.full_message,
                }
                for e in self.errors
            ],
        }

        output_path.write_text(json.dumps(report, indent=2))
        print(f"\nDetailed report saved to: {output_path}")

    def get_fixable_files(self) -> dict[str, list[PydanticError]]:
        """Get files grouped by error type for targeted fixing."""
        fixable: dict[str, list[PydanticError]] = defaultdict(list)

        for error in self.errors:
            if error.error_type == "missing_argument":
                fixable[error.file_path].append(error)

        return dict(fixable)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Pydantic call-arg errors from mypy"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON report path (default: pydantic_errors_report.json)",
        default=Path("pydantic_errors_report.json"),
    )
    parser.add_argument(
        "--no-run-mypy",
        action="store_true",
        help="Use cached errors from /tmp/mypy_call_arg_errors.txt",
    )

    args = parser.parse_args()

    analyzer = PydanticErrorAnalyzer()

    # Get error lines
    if args.no_run_mypy:
        cache_file = Path("/tmp/mypy_call_arg_errors.txt")
        if not cache_file.exists():
            print("Error: No cached errors found. Run without --no-run-mypy first.")
            return 1
        error_lines = cache_file.read_text().strip().split("\n")
        print(f"Using cached errors from {cache_file}")
    else:
        error_lines = analyzer.run_mypy()

    # Parse and analyze
    analyzer.parse_errors(error_lines)
    analyzer.generate_statistics()

    # Generate report
    analyzer.print_report()
    analyzer.save_report(args.output)

    # Print fixable file count
    fixable = analyzer.get_fixable_files()
    print(f"\nFixable files (missing_argument): {len(fixable)}")

    return 0


if __name__ == "__main__":
    exit(main())
