#!/usr/bin/env python3
"""
Analyze exception handling patterns in the codebase.

This script identifies problematic exception handling patterns:
1. Bare except: blocks without # fallback-ok comments
2. except Exception: blocks without proper logging
3. except Exception as e: blocks that don't use the exception variable
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class ExceptionPatternAnalyzer:
    """Analyze exception handling patterns in Python files."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: List[Dict[str, any]] = []

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for exception handling issues."""
        try:
            content = file_path.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Check for bare except:
                if re.search(r"^\s*except\s*:", line):
                    # Check if there's a fallback-ok comment nearby
                    context = "\n".join(lines[max(0, i - 2) : i + 2])
                    if "# fallback-ok" not in context:
                        self.issues.append(
                            {
                                "file": str(file_path.relative_to(self.root_dir)),
                                "line": i,
                                "type": "bare_except",
                                "severity": "high",
                                "line_content": line.strip(),
                            }
                        )

                # Check for except Exception: without as e
                elif re.search(r"^\s*except\s+Exception\s*:", line):
                    # Check if there's proper logging in the next few lines
                    next_lines = lines[i : i + 5]
                    has_logging = any(
                        "emit_log_event" in l or "logger." in l or "_logger." in l
                        for l in next_lines
                    )
                    has_fallback_ok = any("# fallback-ok" in l for l in next_lines)

                    if not has_logging and not has_fallback_ok:
                        self.issues.append(
                            {
                                "file": str(file_path.relative_to(self.root_dir)),
                                "line": i,
                                "type": "unlogged_exception",
                                "severity": "medium",
                                "line_content": line.strip(),
                            }
                        )

                # Check for except Exception as e: where e is not used
                elif match := re.search(
                    r"^\s*except\s+Exception\s+as\s+(\w+)\s*:", line
                ):
                    var_name = match.group(1)
                    # Check if the exception variable is used in the next few lines
                    next_lines = "\n".join(lines[i : i + 10])
                    var_used = var_name in next_lines

                    if not var_used:
                        self.issues.append(
                            {
                                "file": str(file_path.relative_to(self.root_dir)),
                                "line": i,
                                "type": "unused_exception_var",
                                "severity": "low",
                                "line_content": line.strip(),
                            }
                        )

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    def analyze_directory(self) -> None:
        """Recursively analyze all Python files in the directory."""
        src_dir = self.root_dir / "src" / "omnibase_core"
        for py_file in src_dir.rglob("*.py"):
            self.analyze_file(py_file)

    def generate_report(self) -> str:
        """Generate a report of all issues found."""
        if not self.issues:
            return "✅ No exception handling issues found!"

        # Group by severity
        high = [i for i in self.issues if i["severity"] == "high"]
        medium = [i for i in self.issues if i["severity"] == "medium"]
        low = [i for i in self.issues if i["severity"] == "low"]

        report = []
        report.append("=" * 80)
        report.append("EXCEPTION HANDLING ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Total issues: {len(self.issues)}")
        report.append(f"  High severity: {len(high)}")
        report.append(f"  Medium severity: {len(medium)}")
        report.append(f"  Low severity: {len(low)}")
        report.append("")

        if high:
            report.append("=" * 80)
            report.append("HIGH SEVERITY: Bare except: blocks")
            report.append("=" * 80)
            for issue in high:
                report.append(f"  {issue['file']}:{issue['line']}")
                report.append(f"    {issue['line_content']}")
                report.append("")

        if medium:
            report.append("=" * 80)
            report.append("MEDIUM SEVERITY: except Exception: without logging")
            report.append("=" * 80)
            for issue in medium[:20]:  # Limit to first 20
                report.append(f"  {issue['file']}:{issue['line']}")
                report.append(f"    {issue['line_content']}")
            if len(medium) > 20:
                report.append(f"  ... and {len(medium) - 20} more")
            report.append("")

        if low:
            report.append(
                f"LOW SEVERITY: {len(low)} cases of unused exception variables"
            )
            report.append("")

        return "\n".join(report)


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent.parent
    analyzer = ExceptionPatternAnalyzer(root_dir)

    print("Analyzing exception handling patterns...")
    analyzer.analyze_directory()

    print(analyzer.generate_report())

    # Exit with error code if high severity issues found
    high_severity = sum(1 for i in analyzer.issues if i["severity"] == "high")
    sys.exit(1 if high_severity > 0 else 0)


if __name__ == "__main__":
    main()
