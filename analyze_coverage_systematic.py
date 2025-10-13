#!/usr/bin/env python3
"""
Systematic coverage analysis to identify the biggest opportunities for improvement.
"""

import os
import re
from collections import defaultdict
from pathlib import Path


def parse_html_coverage():
    """Parse HTML coverage files to extract coverage data."""
    htmlcov_dir = Path("htmlcov")
    if not htmlcov_dir.exists():
        print("No htmlcov directory found. Run coverage first.")
        return []

    coverage_data = []

    for html_file in htmlcov_dir.glob("*.html"):
        if html_file.name == "index.html":
            continue

        try:
            with open(html_file) as f:
                content = f.read()

            # Extract file path from the HTML
            file_match = re.search(r"<h1>([^<]+)</h1>", content)
            if not file_match:
                continue

            file_path = file_match.group(1)
            if not file_path.startswith("src/omnibase_core/"):
                continue

            # Extract coverage statistics
            stats_match = re.search(
                r'<p class="text">\s*(\d+)\s*statements\s*</p>', content
            )
            if not stats_match:
                continue

            statements = int(stats_match.group(1))

            # Count missing lines (red lines in coverage)
            missing_lines = content.count('class="c c-0"')
            covered_lines = content.count('class="c c-1"')

            # Calculate coverage percentage
            total_lines = missing_lines + covered_lines
            if total_lines > 0:
                coverage_percent = (covered_lines / total_lines) * 100
            else:
                coverage_percent = 100.0

            coverage_data.append(
                {
                    "file": file_path.replace("src/omnibase_core/", ""),
                    "statements": statements,
                    "missing_lines": missing_lines,
                    "covered_lines": covered_lines,
                    "total_lines": total_lines,
                    "coverage_percent": coverage_percent,
                    "uncovered_lines": missing_lines,
                }
            )

        except Exception as e:
            print(f"Error parsing {html_file}: {e}")
            continue

    return coverage_data


def analyze_coverage_opportunities():
    """Analyze coverage data and identify opportunities."""
    coverage_data = parse_html_coverage()

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
    current_coverage = (
        ((total_lines - total_uncovered) / total_lines) * 100 if total_lines > 0 else 0
    )

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

    print("\n=== HIGH IMPACT FILES (50+ uncovered lines, <80% coverage) ===")
    for i, item in enumerate(high_impact[:30], 1):
        print(
            f"{i:2d}. {item['file']:<60} {item['uncovered_lines']:3d} uncovered ({item['coverage_percent']:5.1f}%)"
        )

    # Create prioritized list for testing
    print("\n=== PRIORITIZED TESTING LIST (Top 200 files) ===")
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
    analyze_coverage_opportunities()
