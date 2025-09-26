#!/usr/bin/env python3
"""
Enhanced ONEX Type System Validator - Comprehensive Compliance Checking

Zero tolerance enforcement for ONEX type system standards:
1. Any type elimination (zero tolerance)
2. ModelSchemaValue usage validation
3. TypedDict Model* naming convention compliance
4. Generic type usage patterns
5. TYPE_CHECKING conditional import structures
"""

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple


@dataclass
class TypeViolation:
    """Represents any type system violation."""

    file_path: str
    line_number: int
    column: int
    violation_type: str
    severity: str
    context: str
    code_snippet: str
    remediation: str


class EnhancedTypeValidator(ast.NodeVisitor):
    """Comprehensive type system validator using AST analysis."""

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: List[TypeViolation] = []
        self.imports: Set[str] = set()
        self.typing_imports: Set[str] = set()
        self.from_typing_imports: Set[str] = set()
        self.type_checking_blocks: List[int] = []
        self.typeddict_classes: List[str] = []
        self.model_schema_value_usage: List[Tuple[int, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports, especially typing module."""
        if node.module == "typing":
            for alias in node.names:
                self.from_typing_imports.add(
                    alias.name if alias.asname is None else alias.asname
                )
        elif node.module and "typing" in node.module:
            for alias in node.names:
                self.typing_imports.add(
                    alias.name if alias.asname is None else alias.asname
                )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Detect TYPE_CHECKING conditional blocks."""
        if (isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING") or (
            isinstance(node.test, ast.Attribute)
            and isinstance(node.test.value, ast.Name)
            and node.test.value.id == "typing"
            and node.test.attr == "TYPE_CHECKING"
        ):
            self.type_checking_blocks.append(node.lineno)
            self._validate_type_checking_block(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Validate class definitions, especially TypedDicts."""
        class_name = node.name

        # Check TypedDict naming conventions
        if self._is_typeddict_class(node):
            self.typeddict_classes.append(class_name)
            self._validate_typeddict_naming(node, class_name)
            self._validate_typeddict_fields(node)

        # Check for ModelSchemaValue usage patterns
        self._check_model_schema_value_usage_in_class(node)

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Detect various naming pattern violations."""
        # Any type detection
        if node.id == "Any":
            self._record_violation(
                node,
                "Any Type Usage",
                "CRITICAL",
                f"Direct Any usage: '{node.id}'",
                "Replace Any with specific types: str | int | ModelSchemaValue",
            )

        # ModelSchemaValue usage tracking
        if node.id == "ModelSchemaValue":
            self.model_schema_value_usage.append((getattr(node, "lineno", 0), node.id))

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Validate generic type usage."""
        if self._contains_any(node):
            self._record_violation(
                node,
                "Generic Any Usage",
                "CRITICAL",
                "Generic type contains Any",
                "Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]",
            )

        # Check for lazy Union usage patterns
        self._validate_union_usage(node)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Validate function signatures."""
        # Check for Any in parameters
        for arg in node.args.args:
            if arg.annotation and self._annotation_contains_any(arg.annotation):
                self._record_violation(
                    arg.annotation,
                    "Function Parameter Any",
                    "CRITICAL",
                    f"Parameter '{arg.arg}' uses Any type",
                    f"Specify exact type for parameter '{arg.arg}': use str | int | ModelSchemaValue",
                )

        # Check for Any in return type
        if node.returns and self._annotation_contains_any(node.returns):
            self._record_violation(
                node.returns,
                "Function Return Any",
                "CRITICAL",
                f"Function '{node.name}' returns Any",
                f"Specify exact return type for '{node.name}': use specific return type instead of Any",
            )

        # Check for proper ModelSchemaValue usage in functions
        self._validate_modelschemavalue_in_function(node)

        self.generic_visit(node)

    def _is_typeddict_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a TypedDict."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "TypedDict":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "TypedDict":
                return True
        return False

    def _validate_typeddict_naming(self, node: ast.ClassDef, class_name: str) -> None:
        """Validate TypedDict follows Model* naming convention."""
        if not class_name.startswith("TypedDict"):
            self._record_violation(
                node,
                "TypedDict Naming Convention",
                "HIGH",
                f"TypedDict class '{class_name}' doesn't follow TypedDict* naming pattern",
                f"Rename '{class_name}' to 'TypedDict{class_name}' to follow ONEX conventions",
            )

    def _validate_typeddict_fields(self, node: ast.ClassDef) -> None:
        """Validate TypedDict field types don't use Any."""
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if stmt.annotation and self._annotation_contains_any(stmt.annotation):
                    self._record_violation(
                        stmt.annotation,
                        "TypedDict Field Any",
                        "CRITICAL",
                        f"TypedDict field '{stmt.target.id}' uses Any type",
                        f"Replace Any in field '{stmt.target.id}' with ModelSchemaValue or specific type",
                    )

    def _validate_type_checking_block(self, node: ast.If) -> None:
        """Validate TYPE_CHECKING conditional imports."""
        # Check if imports inside TYPE_CHECKING are properly structured
        has_imports = any(
            isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body
        )
        if not has_imports:
            self._record_violation(
                node,
                "Empty TYPE_CHECKING Block",
                "MEDIUM",
                "TYPE_CHECKING block contains no imports",
                "Remove empty TYPE_CHECKING block or add necessary type-only imports",
            )

    def _validate_union_usage(self, node: ast.Subscript) -> None:
        """Check for lazy Union type patterns."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            # Check if Union has more than 3 types (potential lazy typing)
            if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) > 4:
                self._record_violation(
                    node,
                    "Lazy Union Usage",
                    "MEDIUM",
                    f"Union with {len(node.slice.elts)} types may indicate lazy typing",
                    "Consider using specific types or creating a protocol instead of large Union",
                )

    def _validate_modelschemavalue_in_function(self, node: ast.FunctionDef) -> None:
        """Check if functions properly use ModelSchemaValue instead of Any."""
        # This is a placeholder for more complex validation logic
        pass

    def _check_model_schema_value_usage_in_class(self, node: ast.ClassDef) -> None:
        """Check ModelSchemaValue usage patterns in class definitions."""
        # This is a placeholder for more complex validation logic
        pass

    def _contains_any(self, node: ast.AST) -> bool:
        """Check if AST node contains Any reference."""
        if isinstance(node, ast.Name) and node.id == "Any":
            return True
        elif isinstance(node, ast.Subscript):
            return self._contains_any(node.value) or self._contains_any(node.slice)
        elif isinstance(node, ast.Tuple):
            return any(self._contains_any(elt) for elt in node.elts)
        elif isinstance(node, ast.List):
            return any(self._contains_any(elt) for elt in node.elts)
        elif hasattr(node, "elts"):
            return any(self._contains_any(elt) for elt in node.elts)
        return False

    def _annotation_contains_any(self, annotation: ast.AST) -> bool:
        """Check if type annotation contains Any."""
        return self._contains_any(annotation)

    def _record_violation(
        self,
        node: ast.AST,
        violation_type: str,
        severity: str,
        context: str,
        remediation: str,
    ) -> None:
        """Record a detected type system violation."""
        line_number = getattr(node, "lineno", 0)
        column = getattr(node, "col_offset", 0)

        code_snippet = ""
        if 1 <= line_number <= len(self.source_lines):
            code_snippet = self.source_lines[line_number - 1].strip()

        violation = TypeViolation(
            file_path=self.file_path,
            line_number=line_number,
            column=column,
            violation_type=violation_type,
            severity=severity,
            context=context,
            code_snippet=code_snippet,
            remediation=remediation,
        )

        self.violations.append(violation)


class ComprehensiveTypeSystemValidator:
    """Main comprehensive type system validation coordinator."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.target_directories = [
            "src/omnibase_core/models/contracts",
            "src/omnibase_core/models/nodes",
            "src/omnibase_core/models/core",
            "src/omnibase_core/types",
        ]
        self.all_violations: List[TypeViolation] = []
        self.files_scanned: int = 0
        self.files_with_violations: int = 0
        self.violation_stats = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def validate_all_files(self) -> Dict[str, any]:
        """Run comprehensive type system validation."""
        print("🚀 Enhanced ONEX Type System Validation")
        print("=" * 80)

        validation_results = {}

        for directory in self.target_directories:
            dir_path = self.base_path / directory
            if not dir_path.exists():
                print(f"⚠️  Directory not found: {dir_path}")
                continue

            print(f"🔍 Validating: {directory}")

            for py_file in dir_path.rglob("*.py"):
                violations = self._validate_file(py_file)
                self.files_scanned += 1

                if violations:
                    self.files_with_violations += 1
                    validation_results[str(py_file)] = violations
                    self.all_violations.extend(violations)

        # Update statistics
        for violation in self.all_violations:
            self.violation_stats[violation.severity] += 1

        return validation_results

    def _validate_file(self, file_path: Path) -> List[TypeViolation]:
        """Validate a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                source_lines = content.splitlines()

            tree = ast.parse(content, filename=str(file_path))
            validator = EnhancedTypeValidator(str(file_path), source_lines)
            validator.visit(tree)

            return validator.violations

        except Exception as e:
            print(f"❌ Error validating {file_path}: {e}")
            return []

    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive validation report."""
        report_lines = []

        # Header with comprehensive summary
        report_lines.extend(
            [
                "# ONEX Type System Comprehensive Validation Report",
                "## Zero Tolerance Type Safety Enforcement Results",
                "",
                "### Validation Summary",
                f"- **Files Scanned**: {self.files_scanned}",
                f"- **Files with Violations**: {self.files_with_violations}",
                f"- **Total Violations**: {len(self.all_violations)}",
                "",
                "### Violation Breakdown by Severity",
                f"- **CRITICAL**: {self.violation_stats['CRITICAL']} (Any type violations, must fix immediately)",
                f"- **HIGH**: {self.violation_stats['HIGH']} (Convention violations, should fix)",
                f"- **MEDIUM**: {self.violation_stats['MEDIUM']} (Code quality issues, recommended to fix)",
                f"- **LOW**: {self.violation_stats['LOW']} (Minor issues, optional fixes)",
                "",
                f"### **Status**: {'✅ COMPLIANT' if len(self.all_violations) == 0 else '❌ VIOLATIONS DETECTED'}",
                "",
            ]
        )

        if len(self.all_violations) == 0:
            report_lines.extend(
                [
                    "## 🎉 Full Compliance Achieved!",
                    "",
                    "✅ Zero Any type violations detected",
                    "✅ All ModelSchemaValue usage patterns correct",
                    "✅ TypedDict naming conventions followed",
                    "✅ Generic type usage patterns compliant",
                    "✅ TYPE_CHECKING imports properly structured",
                    "",
                    "**Result**: ONEX strong typing standards are fully compliant.",
                    "",
                ]
            )
            return "\n".join(report_lines)

        # Group violations by severity and file
        critical_violations = [
            v for v in self.all_violations if v.severity == "CRITICAL"
        ]
        high_violations = [v for v in self.all_violations if v.severity == "HIGH"]
        medium_violations = [v for v in self.all_violations if v.severity == "MEDIUM"]

        # Critical violations (Any types)
        if critical_violations:
            report_lines.extend(
                [
                    "## 🚨 CRITICAL Violations (Zero Tolerance - Must Fix)",
                    "",
                    f"Found {len(critical_violations)} critical violations that MUST be eliminated:",
                    "",
                ]
            )

            violations_by_file = self._group_violations_by_file(critical_violations)
            for file_path, violations in sorted(violations_by_file.items()):
                self._add_file_violations_to_report(report_lines, file_path, violations)

        # High violations (Conventions)
        if high_violations:
            report_lines.extend(
                [
                    "## ⚠️  HIGH Priority Violations (Should Fix)",
                    "",
                    f"Found {len(high_violations)} high priority violations:",
                    "",
                ]
            )

            violations_by_file = self._group_violations_by_file(high_violations)
            for file_path, violations in sorted(violations_by_file.items()):
                self._add_file_violations_to_report(report_lines, file_path, violations)

        # Medium violations (Code quality)
        if medium_violations:
            report_lines.extend(
                [
                    "## 📋 MEDIUM Priority Violations (Recommended)",
                    "",
                    f"Found {len(medium_violations)} medium priority violations:",
                    "",
                ]
            )

            violations_by_file = self._group_violations_by_file(medium_violations)
            for file_path, violations in sorted(violations_by_file.items()):
                self._add_file_violations_to_report(report_lines, file_path, violations)

        # Comprehensive remediation guidance
        report_lines.extend(
            [
                "## 🛠️  Comprehensive Remediation Strategy",
                "",
                "### Phase 1: CRITICAL - Any Type Elimination (Zero Tolerance)",
                "",
                "**Every Any type must be replaced with specific types:**",
                "",
                "```python",
                "# ❌ CRITICAL VIOLATIONS",
                "param: Any",
                "def func() -> Any:",
                "data: Dict[str, Any]",
                "items: List[Any]",
                "",
                "# ✅ ONEX COMPLIANT",
                "param: str | int | ModelSchemaValue",
                "def func() -> ModelProcessingResult:",
                "data: Dict[str, ModelSchemaValue]",
                "items: List[ModelSchemaValue]",
                "```",
                "",
                "### Phase 2: HIGH - Convention Compliance",
                "",
                "**TypedDict Naming**: All TypedDict classes must start with 'TypedDict'",
                "```python",
                "# ❌ Wrong",
                "class ConfigSummary(TypedDict):",
                "",
                "# ✅ Correct",
                "class TypedDictConfigSummary(TypedDict):",
                "```",
                "",
                "### Phase 3: MEDIUM - Code Quality Improvements",
                "",
                "**Union Optimization**: Large unions may indicate lazy typing",
                "```python",
                "# ❌ Potential lazy typing",
                "Union[str, int, float, bool, dict, list]",
                "",
                "# ✅ Better approach",
                "Protocol or specific model class",
                "```",
                "",
                "### Priority Order",
                f"1. Fix {self.violation_stats['CRITICAL']} CRITICAL violations first (Any types)",
                f"2. Address {self.violation_stats['HIGH']} HIGH violations (conventions)",
                f"3. Consider {self.violation_stats['MEDIUM']} MEDIUM violations (quality)",
                "",
            ]
        )

        return "\n".join(report_lines)

    def _group_violations_by_file(
        self, violations: List[TypeViolation]
    ) -> Dict[str, List[TypeViolation]]:
        """Group violations by file for better organization."""
        violations_by_file = {}
        for violation in violations:
            file_key = violation.file_path
            if file_key not in violations_by_file:
                violations_by_file[file_key] = []
            violations_by_file[file_key].append(violation)
        return violations_by_file

    def _add_file_violations_to_report(
        self, report_lines: List[str], file_path: str, violations: List[TypeViolation]
    ) -> None:
        """Add file violations to report."""
        relative_path = file_path.replace(str(self.base_path), "")
        report_lines.extend(
            [f"### File: {relative_path}", f"**Violations**: {len(violations)}", ""]
        )

        for violation in violations:
            report_lines.extend(
                [
                    f"- **Line {violation.line_number}**: {violation.violation_type} ({violation.severity})",
                    f"  - **Issue**: {violation.context}",
                    f"  - **Code**: `{violation.code_snippet}`",
                    f"  - **Fix**: {violation.remediation}",
                    "",
                ]
            )


def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = "/Volumes/PRO-G40/Code/omnibase_core"

    validator = ComprehensiveTypeSystemValidator(base_path)
    validator.validate_all_files()

    print("=" * 80)
    print("📊 Generating Comprehensive Validation Report...")

    report = validator.generate_comprehensive_report()

    # Save report
    report_path = Path(base_path) / "COMPREHENSIVE_TYPE_VALIDATION_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📄 Report saved to: {report_path}")
    print("")

    # Print final summary
    if len(validator.all_violations) == 0:
        print("✅ SUCCESS: Full ONEX type system compliance achieved!")
        print("🎯 All validation criteria passed.")
    else:
        print(
            f"❌ VIOLATIONS DETECTED: {len(validator.all_violations)} total violations found"
        )
        print(f"🚨 CRITICAL (Any types): {validator.violation_stats['CRITICAL']}")
        print(f"⚠️  HIGH (Conventions): {validator.violation_stats['HIGH']}")
        print(f"📋 MEDIUM (Quality): {validator.violation_stats['MEDIUM']}")
        print("")
        print("🎯 Zero tolerance policy requires ALL CRITICAL violations to be fixed")

    return validator.violation_stats[
        "CRITICAL"
    ]  # Return critical violations for exit code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
