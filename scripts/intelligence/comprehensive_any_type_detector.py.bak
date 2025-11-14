#!/usr/bin/env python3
"""
ONEX Type System Validation - Comprehensive Any Type Detector

Zero tolerance enforcement for Any type usage across omnibase_core.
Performs AST-based analysis to detect ALL instances of Any type usage.
"""

import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Optional


@dataclass
class AnyTypeViolation:
    """Represents a detected Any type violation."""

    file_path: str
    line_number: int
    column: int
    violation_type: str
    context: str
    code_snippet: str
    severity: str


class AnyTypeDetector(ast.NodeVisitor):
    """AST visitor to detect Any type usage patterns."""

    def __init__(self, file_path: str, source_lines: list[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: list[AnyTypeViolation] = []
        self.imports: set[str] = set()
        self.typing_imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports, especially typing module."""
        if node.module == "typing" or (node.module and "typing" in node.module):
            for alias in node.names:
                self.typing_imports.add(
                    alias.name if alias.asname is None else alias.asname
                )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Detect direct Any identifier usage."""
        if node.id == "Any":
            # Check if this is in a type annotation context
            self._record_violation(
                node,
                violation_type="Direct Any Usage",
                context=f"Identifier '{node.id}' used",
                severity="CRITICAL",
            )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect Any in generic types (list[Any], dict[str, Any], etc.)."""
        # Check if slice contains Any
        if self._contains_any(node):
            self._record_violation(
                node,
                violation_type="Generic Any Usage",
                context="Generic type containing Any",
                severity="CRITICAL",
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function signatures for Any types."""
        # Check arguments
        for arg in node.args.args:
            if arg.annotation and self._annotation_contains_any(arg.annotation):
                self._record_violation(
                    arg.annotation,
                    violation_type="Function Parameter Any",
                    context=f"Parameter '{arg.arg}' annotated with Any",
                    severity="CRITICAL",
                )

        # Check return type
        if node.returns and self._annotation_contains_any(node.returns):
            self._record_violation(
                node.returns,
                violation_type="Function Return Any",
                context=f"Function '{node.name}' returns Any",
                severity="CRITICAL",
            )

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check variable annotations for Any types."""
        if node.annotation and self._annotation_contains_any(node.annotation):
            target_name = "unknown"
            if isinstance(node.target, ast.Name):
                target_name = node.target.id

            self._record_violation(
                node.annotation,
                violation_type="Variable Annotation Any",
                context=f"Variable '{target_name}' annotated with Any",
                severity="CRITICAL",
            )
        self.generic_visit(node)

    def _contains_any(self, node: ast.AST) -> bool:
        """Check if AST node contains Any reference."""
        if isinstance(node, ast.Name) and node.id == "Any":
            return True
        elif isinstance(node, ast.Subscript):
            return self._contains_any(node.value) or self._contains_any(node.slice)
        elif (
            isinstance(node, ast.Tuple)
            or isinstance(node, ast.List)
            or hasattr(node, "elts")
        ):
            return any(self._contains_any(elt) for elt in node.elts)
        return False

    def _annotation_contains_any(self, annotation: ast.AST) -> bool:
        """Check if type annotation contains Any."""
        return self._contains_any(annotation)

    def _record_violation(
        self, node: ast.AST, violation_type: str, context: str, severity: str
    ) -> None:
        """Record a detected Any type violation."""
        line_number = getattr(node, "lineno", 0)
        column = getattr(node, "col_offset", 0)

        # Get code snippet
        code_snippet = ""
        if 1 <= line_number <= len(self.source_lines):
            code_snippet = self.source_lines[line_number - 1].strip()

        violation = AnyTypeViolation(
            file_path=self.file_path,
            line_number=line_number,
            column=column,
            violation_type=violation_type,
            context=context,
            code_snippet=code_snippet,
            severity=severity,
        )

        self.violations.append(violation)


class TypeSystemValidator:
    """Main type system validation coordinator."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.target_directories = [
            "src/omnibase_core/models/contracts",
            "src/omnibase_core/models/nodes",
            "src/omnibase_core/models/core",
            "src/omnibase_core/types",
        ]
        self.all_violations: list[AnyTypeViolation] = []
        self.files_scanned: int = 0
        self.files_with_violations: int = 0

    def scan_all_files(self) -> dict[str, list[AnyTypeViolation]]:
        """Scan all Python files in target directories for Any type violations."""
        violation_summary = {}

        for directory in self.target_directories:
            dir_path = self.base_path / directory
            if not dir_path.exists():
                print(f"⚠️  Directory not found: {dir_path}")
                continue

            print(f"🔍 Scanning: {directory}")

            for py_file in dir_path.rglob("*.py"):
                violations = self._scan_file(py_file)
                self.files_scanned += 1

                if violations:
                    self.files_with_violations += 1
                    violation_summary[str(py_file)] = violations
                    self.all_violations.extend(violations)

        return violation_summary

    def _scan_file(self, file_path: Path) -> list[AnyTypeViolation]:
        """Scan a single Python file for Any type violations."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                source_lines = content.splitlines()

            # Parse AST
            tree = ast.parse(content, filename=str(file_path))

            # Create detector and run analysis
            detector = AnyTypeDetector(str(file_path), source_lines)
            detector.visit(tree)

            return detector.violations

        except Exception as e:
            print(f"❌ Error scanning {file_path}: {e}")
            return []

    def generate_report(self) -> str:
        """Generate comprehensive violation report."""
        report_lines = []

        # Header
        report_lines.extend(
            [
                "# ONEX Type System Validation Report",
                "## Zero Tolerance Any Type Detection Results",
                "",
                "**Scan Summary**",
                f"- Files Scanned: {self.files_scanned}",
                f"- Files with Violations: {self.files_with_violations}",
                f"- Total Violations: {len(self.all_violations)}",
                f"- **Status**: {'✅ COMPLIANT' if len(self.all_violations) == 0 else '❌ VIOLATIONS DETECTED'}",
                "",
            ]
        )

        if len(self.all_violations) == 0:
            report_lines.extend(
                [
                    "## 🎉 Zero Violations Found!",
                    "",
                    "All files passed the zero-tolerance Any type validation.",
                    "ONEX strong typing standards are fully compliant.",
                    "",
                ]
            )
            return "\n".join(report_lines)

        # Group violations by severity
        critical_violations = [
            v for v in self.all_violations if v.severity == "CRITICAL"
        ]

        report_lines.extend(
            [
                "## Critical Violations (Must Fix)",
                "",
                f"Found {len(critical_violations)} critical Any type violations that must be eliminated:",
                "",
            ]
        )

        # Group by file for better organization
        violations_by_file = {}
        for violation in critical_violations:
            file_key = violation.file_path
            if file_key not in violations_by_file:
                violations_by_file[file_key] = []
            violations_by_file[file_key].append(violation)

        # Report violations by file
        for file_path, violations in sorted(violations_by_file.items()):
            relative_path = file_path.replace(str(self.base_path), "")
            report_lines.extend(
                [f"### File: {relative_path}", f"**Violations**: {len(violations)}", ""]
            )

            for violation in violations:
                report_lines.extend(
                    [
                        f"- **Line {violation.line_number}**: {violation.violation_type}",
                        f"  - Context: {violation.context}",
                        f"  - Code: `{violation.code_snippet}`",
                        "",
                    ]
                )

        # Add remediation guidance
        report_lines.extend(
            [
                "## Remediation Guidance",
                "",
                "### Any Type Replacement Strategies",
                "",
                "1. **Direct Any Usage**: Replace with specific types",
                "   ```python",
                "   # ❌ Prohibited",
                "   param: Any",
                "   ",
                "   # ✅ ONEX Compliant",
                "   param: ModelSchemaValue | str | int",
                "   ```",
                "",
                "2. **Generic Any Usage**: Use specific generic types",
                "   ```python",
                "   # ❌ Prohibited",
                "   data: dict[str, Any]",
                "   ",
                "   # ✅ ONEX Compliant",
                "   data: dict[str, ModelSchemaValue]",
                "   ```",
                "",
                "3. **Function Signatures**: Specify exact parameter and return types",
                "   ```python",
                "   # ❌ Prohibited",
                "   def process(data: Any) -> Any:",
                "   ",
                "   # ✅ ONEX Compliant",
                "   def process(data: ModelContractData) -> ModelProcessingResult:",
                "   ```",
                "",
            ]
        )

        return "\n".join(report_lines)


def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = "/Volumes/PRO-G40/Code/omnibase_core"

    print("🚀 ONEX Type System Validation - Zero Tolerance Any Type Detection")
    print(f"📁 Base Path: {base_path}")
    print("=" * 80)

    validator = TypeSystemValidator(base_path)
    violations = validator.scan_all_files()

    print("=" * 80)
    print("📊 Generating Comprehensive Report...")

    report = validator.generate_report()

    # Save report
    report_path = Path(base_path) / "TYPE_SYSTEM_VALIDATION_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📄 Report saved to: {report_path}")
    print("")

    # Print summary
    if len(validator.all_violations) == 0:
        print("✅ SUCCESS: Zero Any type violations detected!")
        print("🎯 ONEX strong typing standards are fully compliant.")
    else:
        print(
            f"❌ VIOLATIONS DETECTED: {len(validator.all_violations)} Any type violations found"
        )
        print(
            f"📁 Files affected: {validator.files_with_violations}/{validator.files_scanned}"
        )
        print("🚨 Zero tolerance policy requires ALL violations to be fixed")

    return len(validator.all_violations)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
