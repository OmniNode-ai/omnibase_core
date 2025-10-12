#!/usr/bin/env python3
"""
Create a systematic plan to reach 60% coverage by targeting the biggest opportunities.
"""

import re
import subprocess
from collections import defaultdict


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
                "-q",
                "--tb=no",
            ],
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


def create_coverage_plan():
    """Create a systematic plan to reach 60% coverage."""
    coverage_data = get_coverage_data()

    if not coverage_data:
        print("No coverage data available")
        return

    # Sort by uncovered lines (biggest impact first)
    by_uncovered_lines = sorted(
        coverage_data, key=lambda x: x["uncovered_lines"], reverse=True
    )

    print("=== SYSTEMATIC COVERAGE PLAN ===")
    print(f"Current coverage: 31.34%")
    print(f"Target coverage: 60.00%")
    print(f"Gap to close: 28.66%")
    print()

    # Group files by impact potential
    high_impact = [
        item
        for item in coverage_data
        if item["uncovered_lines"] > 100 and item["coverage_percent"] < 50
    ]
    medium_impact = [
        item
        for item in coverage_data
        if 50 <= item["uncovered_lines"] <= 100 and item["coverage_percent"] < 70
    ]
    low_impact = [
        item
        for item in coverage_data
        if item["uncovered_lines"] < 50 and item["coverage_percent"] < 80
    ]

    print("=== HIGH IMPACT FILES (100+ uncovered lines, <50% coverage) ===")
    for i, item in enumerate(high_impact[:20], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    print(f"\n=== MEDIUM IMPACT FILES (50-100 uncovered lines, <70% coverage) ===")
    for i, item in enumerate(medium_impact[:30], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    print(f"\n=== LOW IMPACT FILES (<50 uncovered lines, <80% coverage) ===")
    for i, item in enumerate(low_impact[:50], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    # Calculate potential impact
    total_uncovered = sum(item["uncovered_lines"] for item in coverage_data)
    total_lines = sum(item["total_lines"] for item in coverage_data)

    print(f"\n=== COVERAGE IMPACT ANALYSIS ===")
    print(f"Total uncovered lines: {total_uncovered}")
    print(f"Total lines: {total_lines}")

    # Show files that could have biggest impact
    high_impact_files = [
        item
        for item in coverage_data
        if item["uncovered_lines"] > 50 and item["coverage_percent"] < 80
    ]
    high_impact_files.sort(key=lambda x: x["uncovered_lines"], reverse=True)

    print(f"\n=== TOP 200 FILES FOR MAXIMUM COVERAGE GAIN ===")
    for i, item in enumerate(high_impact_files[:200], 1):
        print(
            f"{i:3d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    # Create prioritized list for testing
    print(f"\n=== PRIORITIZED TESTING LIST (Top 200 files) ===")
    prioritized = sorted(
        coverage_data,
        key=lambda x: (x["uncovered_lines"], -x["coverage_percent"]),
        reverse=True,
    )

    for i, item in enumerate(prioritized[:200], 1):
        print(
            f"{i:3d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )


if __name__ == "__main__":
    create_coverage_plan()
