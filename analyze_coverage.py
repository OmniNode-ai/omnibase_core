#!/usr/bin/env python3
"""
Script to analyze coverage and identify the biggest opportunities for improvement.
"""

import re
import subprocess
from collections import defaultdict


def get_coverage_data():
    """Get coverage data from pytest."""
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "--cov=src", "--cov-report=term-missing", "-q"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(f"Coverage command failed with return code {result.returncode}")
            return []

        lines = result.stdout.split("\n")
        coverage_data = []

        for line in lines:
            # Match coverage lines like: src/omnibase_core/models/...    123   45   67   8  45.67%
            match = re.match(
                r"^src/omnibase_core/(.+)\.py\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%",
                line,
            )
            if match:
                file_path = match.group(1)
                total_lines = int(match.group(2))
                missing_lines = int(match.group(3))
                excluded_lines = int(match.group(4))
                partial_lines = int(match.group(5))
                coverage_percent = float(match.group(6))

                coverage_data.append(
                    {
                        "file": file_path,
                        "total_lines": total_lines,
                        "missing_lines": missing_lines,
                        "excluded_lines": excluded_lines,
                        "partial_lines": partial_lines,
                        "coverage_percent": coverage_percent,
                        "uncovered_lines": missing_lines + partial_lines,
                    }
                )

        return coverage_data

    except subprocess.TimeoutExpired:
        print("Coverage command timed out")
        return []
    except Exception as e:
        print(f"Error running coverage: {e}")
        return []


def analyze_coverage_opportunities():
    """Analyze coverage data and identify opportunities."""
    coverage_data = get_coverage_data()

    if not coverage_data:
        print("No coverage data available")
        return

    # Sort by different criteria
    by_uncovered_lines = sorted(
        coverage_data, key=lambda x: x["uncovered_lines"], reverse=True
    )
    by_coverage_percent = sorted(coverage_data, key=lambda x: x["coverage_percent"])
    by_total_lines = sorted(coverage_data, key=lambda x: x["total_lines"], reverse=True)

    print("=== TOP 50 FILES BY UNCOVERED LINES ===")
    for i, item in enumerate(by_uncovered_lines[:50], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    print("\n=== TOP 50 FILES BY LOWEST COVERAGE % ===")
    for i, item in enumerate(by_coverage_percent[:50], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['coverage_percent']:5.1f}% ({item['uncovered_lines']:3d} uncovered)"
        )

    print("\n=== TOP 50 LARGEST FILES ===")
    for i, item in enumerate(by_total_lines[:50], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['total_lines']:3d} lines ({item['coverage_percent']:5.1f}%)"
        )

    # Calculate potential impact
    print("\n=== COVERAGE IMPACT ANALYSIS ===")
    total_uncovered = sum(item["uncovered_lines"] for item in coverage_data)
    total_lines = sum(item["total_lines"] for item in coverage_data)
    current_coverage = ((total_lines - total_uncovered) / total_lines) * 100

    print(f"Current coverage: {current_coverage:.2f}%")
    print(f"Total uncovered lines: {total_uncovered}")
    print(f"Total lines: {total_lines}")

    # Show files that could have biggest impact
    high_impact = [
        item
        for item in coverage_data
        if item["uncovered_lines"] > 50 and item["coverage_percent"] < 80
    ]
    high_impact.sort(key=lambda x: x["uncovered_lines"], reverse=True)

    print(f"\n=== HIGH IMPACT FILES (50+ uncovered lines, <80% coverage) ===")
    for i, item in enumerate(high_impact[:30], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )


if __name__ == "__main__":
    analyze_coverage_opportunities()
