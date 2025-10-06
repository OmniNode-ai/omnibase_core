#!/usr/bin/env python3
"""Analyze MyPy errors and categorize them for systematic fixing."""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_mypy():
    """Run mypy and capture output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd="/Volumes/PRO-G40/Code/omnibase_core",
    )
    return result.stdout + result.stderr


def parse_errors(output):
    """Parse mypy output into structured error data."""
    errors = []
    lines = output.split("\n")

    for line in lines:
        if ": error:" in line:
            # Parse: file:line: error: message  [error-code]
            match = re.match(r"^(.+?):(\d+): error: (.+?)  \[(.+?)\]", line)
            if match:
                file_path, line_num, message, error_code = match.groups()
                errors.append(
                    {
                        "file": file_path,
                        "line": int(line_num),
                        "message": message,
                        "error_code": error_code,
                    }
                )

    return errors


def categorize_errors(errors):
    """Categorize errors by type."""
    by_code = defaultdict(list)
    by_file = defaultdict(list)
    name_defined_names = defaultdict(int)

    for error in errors:
        by_code[error["error_code"]].append(error)
        by_file[error["file"]].append(error)

        # Track undefined names
        if error["error_code"] == "name-defined":
            match = re.search(r'Name "(.+?)" is not defined', error["message"])
            if match:
                name_defined_names[match.group(1)] += 1

    return by_code, by_file, name_defined_names


def print_analysis(by_code, by_file, name_defined_names):
    """Print error analysis."""
    print("=" * 80)
    print("MYPY ERROR ANALYSIS")
    print("=" * 80)
    print()

    # Total count
    total_errors = sum(len(errs) for errs in by_code.values())
    print(f"Total Errors: {total_errors}")
    print(f"Files with Errors: {len(by_file)}")
    print()

    # Top error codes
    print("TOP ERROR CODES:")
    print("-" * 80)
    sorted_codes = sorted(by_code.items(), key=lambda x: len(x[1]), reverse=True)
    for code, errs in sorted_codes[:15]:
        print(f"  {code:25s} {len(errs):5d} errors")
    print()

    # Most common undefined names
    if name_defined_names:
        print("MOST COMMON UNDEFINED NAMES (name-defined errors):")
        print("-" * 80)
        sorted_names = sorted(
            name_defined_names.items(), key=lambda x: x[1], reverse=True
        )
        for name, count in sorted_names[:20]:
            print(f"  {name:40s} {count:4d} occurrences")
        print()

    # Files with most errors
    print("FILES WITH MOST ERRORS:")
    print("-" * 80)
    sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
    for file_path, errs in sorted_files[:20]:
        print(f"  {len(errs):4d} errors: {file_path}")
    print()


def main():
    """Main analysis function."""
    print("Running mypy...")
    output = run_mypy()

    print("Parsing errors...")
    errors = parse_errors(output)

    print(f"Found {len(errors)} errors")
    print()

    print("Categorizing...")
    by_code, by_file, name_defined_names = categorize_errors(errors)

    print_analysis(by_code, by_file, name_defined_names)


if __name__ == "__main__":
    main()
