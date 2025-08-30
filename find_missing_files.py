#!/usr/bin/env python3
"""
Missing Files Discovery Script

Systematically identifies missing files preventing omnibase-core imports
by comparing with omnibase_3 and analyzing import failures.
"""

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MissingFile:
    """Represents a missing file needed for imports."""

    import_path: str
    file_path: str
    referenced_by: list[str]
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    exists_in_omnibase3: bool


class MissingFileFinder:
    """Finds missing files by analyzing import failures."""

    def __init__(self):
        self.omnibase_core_root = Path("/Volumes/PRO-G40/Code/omnibase-core")
        self.omnibase3_root = Path("/Volumes/PRO-G40/Code/omnibase_3")
        self.missing_files: dict[str, MissingFile] = {}

    def find_import_failures(self) -> list[str]:
        """Test imports and capture failure messages."""
        print("🔍 Testing core module imports...")

        test_script = """
import sys
sys.path.insert(0, "/Volumes/PRO-G40/Code/omnibase-core/src")

failed_imports = []

# Test basic core imports
try:
    import omnibase_core.core.onex_container
    print("✅ ONEXContainer imports")
except Exception as e:
    failed_imports.append(f"omnibase.core.onex_container: {e}")

try:
    from omnibase_core.core import ONEXContainer
    print("✅ Core init imports")
except Exception as e:
    failed_imports.append(f"omnibase.core.__init__: {e}")

try:
    import omnibase_core.core.node_compute
    print("✅ NodeCompute imports")
except Exception as e:
    failed_imports.append(f"omnibase.core.node_compute: {e}")

for failure in failed_imports:
    print(f"❌ {failure}")
"""

        result = subprocess.run(
            ["python", "-c", test_script],
            capture_output=True,
            text=True,
            cwd=self.omnibase_core_root,
            check=False,
        )

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        # Extract missing module names from error messages
        failures = []
        for line in result.stderr.split("\n"):
            if "ModuleNotFoundError" in line or "ImportError" in line:
                failures.append(line.strip())

        return failures

    def find_file_in_omnibase3(self, module_name: str) -> Path | None:
        """Find if a module exists in omnibase_3."""
        # Convert module name to file path
        module_parts = module_name.replace("omnibase.", "").split(".")

        # Try different possible locations
        possible_paths = [
            self.omnibase3_root
            / "src"
            / "omnibase"
            / "/".join(module_parts[:-1])
            / f"{module_parts[-1]}.py",
            self.omnibase3_root
            / "src"
            / "omnibase"
            / "/".join(module_parts)
            / "__init__.py",
            self.omnibase3_root / "src" / "omnibase" / "/".join(module_parts) + ".py",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def analyze_imports_in_file(self, file_path: Path) -> list[str]:
        """Extract import statements from a Python file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return imports
        except Exception as e:
            print(f"⚠️  Failed to parse {file_path}: {e}")
            return []

    def scan_missing_dependencies(self) -> None:
        """Scan for missing files by analyzing imports."""
        print("🔍 Scanning for missing dependencies...")

        # Get all Python files in omnibase-core
        python_files = list(self.omnibase_core_root.glob("src/**/*.py"))

        for py_file in python_files:
            imports = self.analyze_imports_in_file(py_file)

            for import_name in imports:
                if not import_name.startswith("omnibase"):
                    continue

                # Check if this import would fail
                try:
                    # Test if we can resolve this import path in omnibase-core
                    import_parts = import_name.replace("omnibase.", "").split(".")
                    expected_path = (
                        self.omnibase_core_root
                        / "src"
                        / "omnibase"
                        / "/".join(import_parts[:-1])
                        / f"{import_parts[-1]}.py"
                    )

                    if not expected_path.exists():
                        # Check if it exists as a package
                        expected_package = (
                            self.omnibase_core_root
                            / "src"
                            / "omnibase"
                            / "/".join(import_parts)
                            / "__init__.py"
                        )

                        if not expected_package.exists():
                            # This is a missing file!
                            omnibase3_path = self.find_file_in_omnibase3(import_name)

                            if import_name not in self.missing_files:
                                self.missing_files[import_name] = MissingFile(
                                    import_path=import_name,
                                    file_path=str(expected_path),
                                    referenced_by=[],
                                    priority=self.calculate_priority(import_name),
                                    exists_in_omnibase3=omnibase3_path is not None,
                                )

                            self.missing_files[import_name].referenced_by.append(
                                str(py_file),
                            )

                except Exception:
                    pass  # Skip resolution errors

    def calculate_priority(self, import_name: str) -> int:
        """Calculate priority based on import name."""
        critical_keywords = [
            "model_semver",
            "model_contract",
            "subcontract",
            "core_errors",
            "onex_error",
        ]
        important_keywords = ["protocol_", "model_", "enum_"]

        for keyword in critical_keywords:
            if keyword in import_name:
                return 1  # Critical

        for keyword in important_keywords:
            if keyword in import_name:
                return 2  # Important

        return 3  # Nice-to-have

    def generate_report(self) -> None:
        """Generate missing files report."""
        print("\n" + "=" * 80)
        print("🎯 MISSING FILES DISCOVERY REPORT")
        print("=" * 80)

        if not self.missing_files:
            print("✅ No missing files detected!")
            return

        # Sort by priority
        by_priority = {1: [], 2: [], 3: []}
        for missing_file in self.missing_files.values():
            by_priority[missing_file.priority].append(missing_file)

        priority_names = {1: "🚨 CRITICAL", 2: "⚠️  IMPORTANT", 3: "💡 NICE-TO-HAVE"}

        for priority in [1, 2, 3]:
            if by_priority[priority]:
                print(
                    f"\n{priority_names[priority]} ({len(by_priority[priority])} files):",
                )
                print("-" * 50)

                for missing_file in sorted(
                    by_priority[priority],
                    key=lambda x: x.import_path,
                ):
                    print(f"📁 {missing_file.import_path}")
                    print(f"   Path: {missing_file.file_path}")
                    print(
                        f"   In omnibase_3: {'✅' if missing_file.exists_in_omnibase3 else '❌'}",
                    )
                    print(f"   Referenced by: {len(missing_file.referenced_by)} files")
                    if len(missing_file.referenced_by) <= 3:
                        for ref in missing_file.referenced_by:
                            print(f"     - {Path(ref).name}")
                    else:
                        for ref in missing_file.referenced_by[:2]:
                            print(f"     - {Path(ref).name}")
                        print(
                            f"     ... and {len(missing_file.referenced_by) - 2} more",
                        )
                    print()

        # Summary statistics
        total_missing = len(self.missing_files)
        in_omnibase3 = sum(
            1 for f in self.missing_files.values() if f.exists_in_omnibase3
        )
        critical = len(by_priority[1])

        print("=" * 80)
        print("📊 SUMMARY STATISTICS")
        print("-" * 30)
        print(f"Total missing files: {total_missing}")
        print(f"Available in omnibase_3: {in_omnibase3}")
        print(f"Critical files: {critical}")
        print(
            (
                f"Success rate potential: {(in_omnibase3/total_missing)*100:.1f}%"
                if total_missing > 0
                else "100%"
            ),
        )

    def run_discovery(self) -> None:
        """Run complete discovery process."""
        print("🚀 Starting Missing Files Discovery...")
        print(f"📂 omnibase-core: {self.omnibase_core_root}")
        print(f"📂 omnibase_3: {self.omnibase3_root}")
        print()

        # Test actual import failures
        failures = self.find_import_failures()
        print(f"\n📋 Found {len(failures)} direct import failures")

        # Scan for missing dependencies
        self.scan_missing_dependencies()

        # Generate report
        self.generate_report()


if __name__ == "__main__":
    finder = MissingFileFinder()
    finder.run_discovery()
