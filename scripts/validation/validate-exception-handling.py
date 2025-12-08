#!/usr/bin/env python3
"""
ONEX Exception Handling Validation Hook

Validates that exception handling follows ONEX standards:
1. No bare except: blocks without # fallback-ok comments
2. No except Exception: blocks without proper logging or # fallback-ok comments
3. All exceptions should be logged with context

Exit codes:
  0 - All validations passed
  1 - Validation failures found
"""

import argparse
import re
import sys
from pathlib import Path


class ExceptionHandlingValidator:
    """Validates exception handling patterns in Python files."""

    def __init__(self):
        self.errors: list[tuple[str, int, str]] = []

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate a single Python file for exception handling anti-patterns.

        Returns:
            True if valid, False if issues found
        """
        # Track starting error count to return per-file validity
        starting_error_count = len(self.errors)

        try:
            content = file_path.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Check for bare except:
                if re.search(r"^\s*except\s*:", line):
                    # Check if there's a fallback-ok comment nearby (within 2 lines)
                    context_start = max(0, i - 3)
                    context_end = min(len(lines), i + 2)
                    context = "\n".join(lines[context_start:context_end])

                    if "# fallback-ok" not in context:
                        self.errors.append(
                            (
                                str(file_path),
                                i,
                                f"Bare except: without fallback-ok comment: {line.strip()}",
                            )
                        )

                # Check for except BaseException:
                elif re.search(r"^\s*except\s+BaseException\s*:", line):
                    # BaseException should be rare and always justified
                    context_start = max(0, i - 3)
                    context_end = min(len(lines), i + 2)
                    context = "\n".join(lines[context_start:context_end])

                    if "# fallback-ok" not in context:
                        self.errors.append(
                            (
                                str(file_path),
                                i,
                                f"except BaseException: without fallback-ok comment: {line.strip()}",
                            )
                        )

                # Check for except Exception: without as e
                elif re.search(r"^\s*except\s+Exception\s*:", line):
                    # Check if there's proper logging or fallback-ok in the next few lines
                    # Convert from 1-indexed line number to 0-indexed array position
                    next_lines_start = i - 1
                    next_lines_end = min(len(lines), i + 5)
                    next_lines = lines[next_lines_start:next_lines_end]

                    has_logging = any(
                        "emit_log_event" in line
                        or "logger." in line
                        or "_logger." in line
                        or "log." in line
                        for line in next_lines
                    )
                    has_fallback_ok = any(
                        "# fallback-ok" in line for line in next_lines
                    )

                    # Flag handlers with no logging AND no control flow
                    # Control flow: return, raise, break, continue, or any function call
                    handler_content = "\n".join(next_lines)
                    has_control_flow = any(
                        keyword in handler_content
                        for keyword in ["return", "raise", "break", "continue"]
                    ) or (
                        # Check for function calls (contains parentheses with content)
                        re.search(r"\w+\s*\([^)]*\)", handler_content) is not None
                    )

                    if not has_logging and not has_fallback_ok and not has_control_flow:
                        self.errors.append(
                            (
                                str(file_path),
                                i,
                                f"except Exception: without logging or control flow: {line.strip()}",
                            )
                        )

            # Return True only if no NEW errors were added for this file
            return len(self.errors) == starting_error_count

        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
            return False

    def print_report(self) -> None:
        """Print validation report with all errors."""
        if not self.errors:
            return

        print("\n" + "=" * 80)
        print("❌ ONEX Exception Handling Validation Failed")
        print("=" * 80)
        print(f"\nFound {len(self.errors)} issue(s):\n")

        for file_path, line_num, message in self.errors:
            print(f"  {file_path}:{line_num}")
            print(f"    {message}\n")

        print("=" * 80)
        print("Fix options:")
        print("  1. Add proper logging: emit_log_event_sync(LogLevel.ERROR, ...)")
        print("  2. Use specific exception types: except (AttributeError, TypeError)")
        print("  3. Add # fallback-ok comment with justification")
        print("=" * 80)


def main() -> int:
    """Main entry point for the validation hook."""
    parser = argparse.ArgumentParser(
        description="Validate ONEX exception handling patterns"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Python files to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any issues (default: warn only)",
    )

    args = parser.parse_args()

    validator = ExceptionHandlingValidator()
    all_valid = True

    for file_path in args.files:
        path = Path(file_path)
        if path.suffix == ".py" and path.exists():
            if not validator.validate_file(path):
                all_valid = False

    if not all_valid:
        validator.print_report()
        return 1 if args.strict else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
