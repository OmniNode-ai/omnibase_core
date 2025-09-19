#!/usr/bin/env python3
"""
Circular dependency checker for ONEX architecture.

Prevents circular imports between core and nodes domains.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DependencyAnalyzer:
    """Analyzes Python files for import dependencies."""

    def __init__(self, src_path: Path):
        self.src_path = src_path
        self.dependencies: Dict[str, Set[str]] = {}
        self.files_analyzed: Set[str] = set()

    def analyze_file(self, file_path: Path) -> Set[str]:
        """Analyze a Python file for its imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)

            return imports

        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            return set()

    def build_dependency_graph(self) -> None:
        """Build the complete dependency graph."""
        # Find all Python files
        for py_file in self.src_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            relative_path = str(py_file.relative_to(self.src_path))
            module_name = relative_path.replace("/", ".").replace(".py", "")

            imports = self.analyze_file(py_file)
            # Filter to only omnibase_core imports
            filtered_imports = {
                imp for imp in imports
                if imp.startswith("omnibase_core")
            }

            self.dependencies[module_name] = filtered_imports
            self.files_analyzed.add(relative_path)

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            # Get dependencies for this node
            deps = self.dependencies.get(node, set())
            for dep in deps:
                # Convert import to module name
                dep_module = dep.replace("omnibase_core.", "")
                if dep_module in self.dependencies:
                    if dfs(dep_module, path + [node]):
                        # Continue to find all cycles
                        pass

            rec_stack.remove(node)
            return False

        # Check each module
        for module in self.dependencies:
            if module not in visited:
                dfs(module, [])

        return cycles

    def check_domain_violations(self) -> List[Tuple[str, str, str]]:
        """Check for domain boundary violations."""
        violations = []

        for module, imports in self.dependencies.items():
            # Determine module domain
            if "models/core/" in module:
                module_domain = "core"
            elif "models/nodes/" in module:
                module_domain = "nodes"
            else:
                continue  # Skip non-model modules

            for imp in imports:
                # Check if import violates domain boundaries
                if imp.startswith("omnibase_core.models."):
                    import_parts = imp.split(".")
                    if len(import_parts) >= 4:
                        import_domain = import_parts[2]  # models.{domain}

                        # Rule: core should never import from nodes
                        if module_domain == "core" and import_domain == "nodes":
                            violations.append((module, imp, "CRITICAL: Core importing from Nodes"))

        return violations


def main():
    """Main entry point for dependency checking."""
    if len(sys.argv) > 1:
        src_path = Path(sys.argv[1])
    else:
        # Default to current directory structure
        src_path = Path("src/omnibase_core")

    if not src_path.exists():
        print(f"Error: Source path {src_path} does not exist")
        sys.exit(1)

    print(f"🔍 Analyzing dependencies in {src_path}")

    analyzer = DependencyAnalyzer(src_path)
    analyzer.build_dependency_graph()

    print(f"📊 Analyzed {len(analyzer.files_analyzed)} Python files")

    # Check for circular dependencies
    cycles = analyzer.find_circular_dependencies()
    if cycles:
        print(f"\n❌ CIRCULAR DEPENDENCIES FOUND ({len(cycles)}):")
        for i, cycle in enumerate(cycles, 1):
            print(f"  {i}. {' → '.join(cycle)}")
        sys.exit(1)
    else:
        print("\n✅ No circular dependencies found")

    # Check for domain violations
    violations = analyzer.check_domain_violations()
    if violations:
        print(f"\n❌ DOMAIN BOUNDARY VIOLATIONS FOUND ({len(violations)}):")
        for module, import_name, violation_type in violations:
            print(f"  {violation_type}")
            print(f"    Module: {module}")
            print(f"    Import: {import_name}")
        sys.exit(1)
    else:
        print("✅ No domain boundary violations found")

    # Summary
    core_models = len([m for m in analyzer.dependencies if "models/core/" in m])
    nodes_models = len([m for m in analyzer.dependencies if "models/nodes/" in m])

    print(f"\n📈 DEPENDENCY SUMMARY:")
    print(f"  Core models: {core_models}")
    print(f"  Nodes models: {nodes_models}")
    print(f"  Total dependencies tracked: {sum(len(deps) for deps in analyzer.dependencies.values())}")

    print("\n🎉 All dependency checks passed!")


if __name__ == "__main__":
    main()