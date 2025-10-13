#!/usr/bin/env python3
"""
Script to analyze coverage data and create a sorted list of files by coverage percentage.
"""

import re
import subprocess
import sys


def get_coverage_data():
    """Get coverage data from pytest."""
    try:
        result = subprocess.run(
            [
                "poetry",
                "run",
                "pytest",
                "--cov=src",
                "--cov-report=term-missing",
                "--tb=no",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd="/Volumes/PRO-G40/Code/omnibase_core",
        )

        # Coverage often returns non-zero exit code but still provides data
        # Let's check if we got any coverage data in stdout

        lines = result.stdout.split("\n")
        coverage_data = []

        print(f"Got {len(lines)} lines of output")
        print(f"First few lines: {lines[:5]}")
        print(f"Last few lines: {lines[-5:]}")

        for line in lines:
            # Match lines that contain coverage percentages
            if re.match(r"^src/.*\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\.\d+%", line):
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        file_path = parts[0]
                        total_lines = int(parts[1])
                        missing_lines = int(parts[2])
                        excluded_lines = int(parts[3])
                        partial_lines = int(parts[4])
                        coverage_pct = float(parts[5].rstrip("%"))

                        coverage_data.append(
                            {
                                "file": file_path,
                                "total_lines": total_lines,
                                "missing_lines": missing_lines,
                                "excluded_lines": excluded_lines,
                                "partial_lines": partial_lines,
                                "coverage_pct": coverage_pct,
                            }
                        )
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing line: {line} - {e}")
                        continue

        return coverage_data

    except Exception as e:
        print(f"Error getting coverage data: {e}")
        return []


def main():
    """Main function to analyze and display coverage data."""
    print("Getting coverage data...")
    coverage_data = get_coverage_data()

    if not coverage_data:
        print("No coverage data found.")
        return

    # Sort by coverage percentage (ascending - lowest coverage first)
    sorted_data = sorted(coverage_data, key=lambda x: x["coverage_pct"])

    # Create the analysis file
    with open("coverage_analysis.txt", "w") as f:
        f.write(
            "COVERAGE ANALYSIS - Files sorted by coverage percentage (lowest to highest)\n"
        )
        f.write("=" * 80 + "\n\n")

        # Write files with 0% coverage first
        zero_coverage = [item for item in sorted_data if item["coverage_pct"] == 0.0]
        if zero_coverage:
            f.write("FILES WITH 0% COVERAGE:\n")
            f.write("-" * 40 + "\n")
            for item in zero_coverage:
                f.write(
                    f"{item['file']:<60} {item['coverage_pct']:>6.1f}% ({item['total_lines']} lines)\n"
                )
            f.write(f"\nTotal files with 0% coverage: {len(zero_coverage)}\n\n")

        # Write files with 1-20% coverage
        low_coverage = [item for item in sorted_data if 0 < item["coverage_pct"] <= 20]
        if low_coverage:
            f.write("FILES WITH 1-20% COVERAGE:\n")
            f.write("-" * 40 + "\n")
            for item in low_coverage:
                f.write(
                    f"{item['file']:<60} {item['coverage_pct']:>6.1f}% ({item['total_lines']} lines)\n"
                )
            f.write(f"\nTotal files with 1-20% coverage: {len(low_coverage)}\n\n")

        # Write files with 21-40% coverage
        medium_low_coverage = [
            item for item in sorted_data if 20 < item["coverage_pct"] <= 40
        ]
        if medium_low_coverage:
            f.write("FILES WITH 21-40% COVERAGE:\n")
            f.write("-" * 40 + "\n")
            for item in medium_low_coverage:
                f.write(
                    f"{item['file']:<60} {item['coverage_pct']:>6.1f}% ({item['total_lines']} lines)\n"
                )
            f.write(
                f"\nTotal files with 21-40% coverage: {len(medium_low_coverage)}\n\n"
            )

        # Write files with 41-60% coverage
        medium_coverage = [
            item for item in sorted_data if 40 < item["coverage_pct"] <= 60
        ]
        if medium_coverage:
            f.write("FILES WITH 41-60% COVERAGE:\n")
            f.write("-" * 40 + "\n")
            for item in medium_coverage:
                f.write(
                    f"{item['file']:<60} {item['coverage_pct']:>6.1f}% ({item['total_lines']} lines)\n"
                )
            f.write(f"\nTotal files with 41-60% coverage: {len(medium_coverage)}\n\n")

        # Write all files sorted by coverage
        f.write("ALL FILES SORTED BY COVERAGE (lowest to highest):\n")
        f.write("-" * 80 + "\n")
        for item in sorted_data:
            f.write(
                f"{item['file']:<60} {item['coverage_pct']:>6.1f}% ({item['total_lines']} lines)\n"
            )

        # Summary statistics
        f.write(f"\nSUMMARY:\n")
        f.write(f"Total files analyzed: {len(sorted_data)}\n")
        f.write(f"Files with 0% coverage: {len(zero_coverage)}\n")
        f.write(f"Files with 1-20% coverage: {len(low_coverage)}\n")
        f.write(f"Files with 21-40% coverage: {len(medium_low_coverage)}\n")
        f.write(f"Files with 41-60% coverage: {len(medium_coverage)}\n")

        # Calculate potential coverage gain
        total_missing_lines = sum(item["missing_lines"] for item in sorted_data)
        total_lines = sum(item["total_lines"] for item in sorted_data)
        current_coverage = (
            ((total_lines - total_missing_lines) / total_lines) * 100
            if total_lines > 0
            else 0
        )

        f.write(f"\nCOVERAGE ANALYSIS:\n")
        f.write(f"Current coverage: {current_coverage:.2f}%\n")
        f.write(f"Total missing lines: {total_missing_lines}\n")
        f.write(f"Total lines: {total_lines}\n")

        # Top opportunities for coverage improvement
        f.write(f"\nTOP 20 OPPORTUNITIES FOR COVERAGE IMPROVEMENT:\n")
        f.write("-" * 60 + "\n")
        for i, item in enumerate(sorted_data[:20]):
            f.write(
                f"{i+1:2d}. {item['file']:<50} {item['coverage_pct']:>6.1f}% ({item['missing_lines']} missing lines)\n"
            )

    print(f"Coverage analysis saved to coverage_analysis.txt")
    print(f"Total files analyzed: {len(sorted_data)}")
    print(f"Files with 0% coverage: {len(zero_coverage)}")
    print(f"Files with 1-20% coverage: {len(low_coverage)}")
    print(f"Files with 21-40% coverage: {len(medium_low_coverage)}")
    print(f"Files with 41-60% coverage: {len(medium_coverage)}")


if __name__ == "__main__":
    main()
