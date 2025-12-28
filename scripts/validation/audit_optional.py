#!/usr/bin/env python3
"""Optional type usage auditor for omni* ecosystem."""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OptionalViolation:
    file_path: str
    line_number: int
    variable_name: str
    context: str
    justification_needed: bool
    description: str
    severity: str = "warning"


class OptionalUsageAuditor:
    """Audits Optional type usage for business justification."""

    # Patterns that usually shouldn't be Optional
    SUSPICIOUS_PATTERNS: list[str] = [
        r".*_id.*: .*Optional",  # IDs are usually required
        r".*id.*: .*Optional",  # IDs are usually required
        r".*status.*: .*Optional",  # Status is usually known
        r".*result.*: .*Optional",  # Results are usually available
        r".*response.*: .*Optional",  # Responses are usually present
        r".*value.*: .*Optional",  # Values are usually required
        r".*name.*: .*Optional",  # Names are usually required
        r".*type.*: .*Optional",  # Types are usually known
    ]

    # Patterns where Optional is typically justified
    JUSTIFIED_PATTERNS: list[str] = [
        r".*_date.*: .*Optional",  # Dates can be null (not yet occurred)
        r".*_time.*: .*Optional",  # Times can be null
        r".*email.*: .*Optional",  # Email might be optional
        r".*phone.*: .*Optional",  # Phone might be optional
        r".*external.*: .*Optional",  # External data might be missing
        r".*cache.*: .*Optional",  # Cache values might be missing
        r".*optional.*: .*Optional",  # Obviously optional
        r".*nullable.*: .*Optional",  # Obviously nullable
        r".*default.*: .*Optional",  # Default values can be optional
        r".*config.*: .*Optional",  # Config can have defaults
        r".*setting.*: .*Optional",  # Settings can have defaults
        r".*metadata.*: .*Optional",  # Metadata might be missing
        r".*description.*: .*Optional",  # Descriptions are often optional
        r".*comment.*: .*Optional",  # Comments are often optional
        r".*note.*: .*Optional",  # Notes are often optional
        r".*approval.*: .*Optional",  # Approval dates/info can be null
        r".*completion.*: .*Optional",  # Completion dates can be null
        r".*last_.*: .*Optional",  # Last action times can be null
        r".*previous.*: .*Optional",  # Previous values can be null
    ]

    # Justification keywords that indicate business reasoning
    JUSTIFICATION_KEYWORDS: list[str] = [
        "optional",
        "nullable",
        "might be",
        "may be",
        "user input",
        "external",
        "api",
        "third party",
        "not required",
        "can be null",
        "default",
        "config",
        "setting",
        "pending",
        "future",
        "calculated",
        "derived",
        "temporary",
        "cache",
        "optimization",
    ]

    def __init__(self, base_path: Path, files: list[Path] | None = None):
        """Initialize auditor.

        Args:
            base_path: Base path for computing relative file paths in reports.
            files: Optional list of specific files to audit. If None, will scan
                base_path recursively when audit_optional_usage() is called.
        """
        self.base_path = base_path
        self.files = files
        self.violations: list[OptionalViolation] = []

    def audit_optional_usage(self) -> bool:
        """Audit all Optional type usage."""
        if self.files is not None:
            # Audit specific files provided
            files_to_check = self.files
        else:
            # Scan directory recursively (original behavior)
            files_to_check = list(self.base_path.rglob("*.py"))

        for py_file in files_to_check:
            # Skip test files, __pycache__, and archived directories
            if (
                "test" in str(py_file).lower()
                or "__pycache__" in str(py_file)
                or "/archived/" in str(py_file)
            ):
                continue

            self._audit_file(py_file)

        return len([v for v in self.violations if v.justification_needed]) == 0

    def _audit_file(self, file_path: Path) -> None:
        """Audit Optional usage in a specific file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.AnnAssign):
                    self._check_annotation(file_path, node, lines)
                elif isinstance(node, ast.FunctionDef):
                    self._check_function_annotations(file_path, node, lines)
                elif isinstance(node, ast.ClassDef):
                    # Check class attributes
                    for class_node in ast.walk(node):
                        if isinstance(class_node, ast.AnnAssign):
                            self._check_annotation(file_path, class_node, lines)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    def _check_annotation(
        self, file_path: Path, node: ast.AnnAssign, lines: list[str]
    ) -> None:
        """Check type annotations for Optional usage."""
        if hasattr(node, "annotation"):
            annotation_str = ast.unparse(node.annotation)
            if "Optional" in annotation_str or (
                "|" in annotation_str and "None" in annotation_str
            ):
                var_name = (
                    ast.unparse(node.target) if hasattr(node, "target") else "unknown"
                )
                self._evaluate_optional_usage(
                    file_path, node.lineno, var_name, annotation_str, lines
                )

    def _check_function_annotations(
        self, file_path: Path, node: ast.FunctionDef, lines: list[str]
    ) -> None:
        """Check function parameter and return type annotations for Optional usage."""
        # Check return type
        if hasattr(node, "returns") and node.returns:
            return_annotation = ast.unparse(node.returns)
            if "Optional" in return_annotation or (
                "|" in return_annotation and "None" in return_annotation
            ):
                self._evaluate_optional_usage(
                    file_path,
                    node.lineno,
                    f"{node.name}() return",
                    return_annotation,
                    lines,
                )

        # Check parameters
        for arg in node.args.args:
            if hasattr(arg, "annotation") and arg.annotation:
                param_annotation = ast.unparse(arg.annotation)
                if "Optional" in param_annotation or (
                    "|" in param_annotation and "None" in param_annotation
                ):
                    self._evaluate_optional_usage(
                        file_path, node.lineno, arg.arg, param_annotation, lines
                    )

    def _evaluate_optional_usage(
        self,
        file_path: Path,
        line_num: int,
        var_name: str,
        annotation: str,
        lines: list[str],
    ) -> None:
        """Evaluate whether Optional usage is justified."""
        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

        # Get surrounding context (3 lines before and after)
        context_start = max(0, line_num - 4)
        context_end = min(len(lines), line_num + 3)
        context_lines = lines[context_start:context_end]
        context = "\n".join(context_lines)

        # Check if it's justified by pattern
        full_annotation = f"{var_name}: {annotation}"
        is_pattern_justified = any(
            re.match(pattern, full_annotation, re.IGNORECASE)
            for pattern in self.JUSTIFIED_PATTERNS
        )

        # Check if it's suspicious by pattern
        is_suspicious = any(
            re.match(pattern, full_annotation, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        )

        # Look for comment justification in current line or surrounding lines
        has_comment_justification = self._has_comment_justification(context.lower())

        # Look for Field description with justification
        has_field_justification = self._has_field_justification(line_content)

        needs_justification = (
            is_suspicious
            and not is_pattern_justified
            and not has_comment_justification
            and not has_field_justification
        )

        # Get relative path for display, fallback to absolute if not under base_path
        try:
            display_path = str(file_path.relative_to(self.base_path))
        except ValueError:
            # File is not under base_path, use path relative to cwd or absolute
            try:
                display_path = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                display_path = str(file_path)

        if needs_justification:
            self.violations.append(
                OptionalViolation(
                    file_path=display_path,
                    line_number=line_num,
                    variable_name=var_name,
                    context=line_content.strip(),
                    justification_needed=True,
                    description=f"Suspicious Optional usage for '{var_name}' needs business justification",
                    severity="error",
                )
            )
        elif "Optional" in annotation or ("|" in annotation and "None" in annotation):
            # Track all Optional usage for reporting
            justification_reason = (
                "pattern justified"
                if is_pattern_justified
                else (
                    "has justification"
                    if has_comment_justification
                    else "acceptable usage"
                )
            )

            self.violations.append(
                OptionalViolation(
                    file_path=display_path,
                    line_number=line_num,
                    variable_name=var_name,
                    context=line_content.strip(),
                    justification_needed=False,
                    description=f"Optional usage ({justification_reason})",
                    severity="info",
                )
            )

    def _has_comment_justification(self, context: str) -> bool:
        """Check if context contains justification keywords."""
        return any(keyword in context for keyword in self.JUSTIFICATION_KEYWORDS)

    def _has_field_justification(self, line_content: str) -> bool:
        """Check if line has Pydantic Field with description explaining Optional."""
        if "Field(" in line_content and "description=" in line_content:
            # Extract description
            desc_match = re.search(r'description=["\'](.*?)["\']', line_content)
            if desc_match:
                description = desc_match.group(1).lower()
                return any(
                    keyword in description for keyword in self.JUSTIFICATION_KEYWORDS
                )
        return False

    def generate_report(self) -> str:
        """Generate Optional usage audit report."""
        needs_justification = [v for v in self.violations if v.justification_needed]
        justified_usage = [v for v in self.violations if not v.justification_needed]

        report = "📊 Optional Type Usage Audit Report\n"
        report += "=" * 40 + "\n\n"

        report += f"Total Optional usage found: {len(self.violations)}\n"
        report += f"Needs business justification: {len(needs_justification)}\n"
        report += f"Justified/Acceptable: {len(justified_usage)}\n\n"

        if needs_justification:
            report += "🔴 REQUIRES BUSINESS JUSTIFICATION:\n"
            report += "=" * 38 + "\n"
            for violation in needs_justification:
                report += (
                    f"🔴 {violation.variable_name} (Line {violation.line_number})\n"
                )
                report += f"   File: {violation.file_path}\n"
                report += f"   Context: {violation.context}\n"
                report += "   Action: Add comment explaining why Optional is needed\n"
                report += (
                    "   Example: # Optional: User might not provide this value\n\n"
                )

        # Show summary of justified usage by category
        if justified_usage:
            report += "✅ JUSTIFIED OPTIONAL USAGE SUMMARY:\n"
            report += "=" * 37 + "\n"

            # Categorize justified usage
            pattern_justified = [
                v for v in justified_usage if "pattern justified" in v.description
            ]
            comment_justified = [
                v for v in justified_usage if "has justification" in v.description
            ]
            acceptable = [
                v for v in justified_usage if "acceptable usage" in v.description
            ]

            report += f"• Pattern justified (dates, external data, etc.): {len(pattern_justified)}\n"
            report += (
                f"• Comment justified (has explanation): {len(comment_justified)}\n"
            )
            report += f"• Generally acceptable: {len(acceptable)}\n\n"

            # Show a few examples of justified usage
            if pattern_justified:
                report += "Examples of pattern-justified Optional usage:\n"
                for violation in pattern_justified[:3]:
                    report += (
                        f"  ✅ {violation.variable_name} in {violation.file_path}\n"
                    )
                if len(pattern_justified) > 3:
                    report += f"  ... and {len(pattern_justified) - 3} more\n"
                report += "\n"

        # Add improvement suggestions
        report += "💡 IMPROVEMENT SUGGESTIONS:\n"
        report += "=" * 28 + "\n"
        report += "1. Add comments explaining business rationale for Optional fields\n"
        report += (
            "2. Use Pydantic Field descriptions to document why values can be None\n"
        )
        report += "3. Consider if Optional is truly needed or if a default value would be better\n"
        report += "4. For API responses, document which fields might be null from external systems\n\n"

        # Add acceptable patterns reference
        report += "📚 COMMONLY JUSTIFIED OPTIONAL PATTERNS:\n"
        report += "=" * 41 + "\n"
        report += (
            "✅ Timestamps that haven't occurred yet (completion_date, approval_date)\n"
        )
        report += "✅ User-provided optional information (email, phone, description)\n"
        report += "✅ External API data that might be missing\n"
        report += "✅ Configuration values with system defaults\n"
        report += "✅ Cache values that might be expired/missing\n"
        report += "✅ Derived/calculated values not yet computed\n\n"

        report += "❌ USUALLY SHOULD NOT BE OPTIONAL:\n"
        report += "=" * 33 + "\n"
        report += "❌ Primary keys and foreign key IDs\n"
        report += "❌ Status fields (status should always be known)\n"
        report += "❌ Processing results (result should always exist)\n"
        report += "❌ Entity names and core identifiers\n"
        report += "❌ Internal processing values\n"

        return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Optional type usage in omni* ecosystem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validation/audit_optional.py .                    # Audit entire repo
    python scripts/validation/audit_optional.py src/omnibase_core    # Audit specific directory
    python scripts/validation/audit_optional.py file1.py file2.py   # Audit specific files (pre-commit)
        """,
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to validate. If a directory is provided, "
        "it will be scanned recursively for .py files.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Collect files to check and determine base path
    files_to_check: list[Path] = []
    directory_mode = False
    base_path: Path | None = None

    for path_str in args.paths:
        p = Path(path_str).resolve()
        if not p.exists():
            print(f"Warning: Path does not exist, skipping: {p}")
            continue

        if p.is_file():
            if p.suffix == ".py":
                files_to_check.append(p)
            else:
                print(f"Warning: Skipping non-Python file: {p}")
        elif p.is_dir():
            # If a directory is provided, use it as base_path and scan recursively
            base_path = p
            directory_mode = True
            files_to_check = []  # Clear any files, directory takes precedence
            break  # Directory mode takes precedence
        else:
            print(f"Warning: Skipping unknown path type: {p}")

    # Handle case where no valid paths were found
    if not directory_mode and not files_to_check:
        print("Error: No valid Python files or directories provided")
        sys.exit(1)

    # For file mode, compute common base path from all files
    if not directory_mode and files_to_check:
        # Find common parent directory for all files
        all_parents = [f.parent for f in files_to_check]
        if all_parents:
            # Use the common prefix of all parent paths
            base_path = Path(os.path.commonpath(all_parents))
        else:
            base_path = Path.cwd()

    # Determine if we're in file mode or directory mode
    if directory_mode:
        # Directory mode: scan recursively (original behavior)
        auditor = OptionalUsageAuditor(base_path, files=None)  # type: ignore[arg-type]
    else:
        # File mode: audit specific files
        auditor = OptionalUsageAuditor(base_path, files=files_to_check)  # type: ignore[arg-type]

    is_valid = auditor.audit_optional_usage()

    print(auditor.generate_report())

    if is_valid:
        print("\n[OK] SUCCESS: All Optional usage is justified!")
        sys.exit(0)
    else:
        errors = len([v for v in auditor.violations if v.justification_needed])
        print(f"\n[WARNING] {errors} Optional usages need business justification!")
        sys.exit(0)  # Don't fail the build for this, just warn


if __name__ == "__main__":
    main()
