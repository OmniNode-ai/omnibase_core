#!/usr/bin/env python3
"""
Import analysis and optimization tool for omnibase_core.

This script analyzes import patterns to identify optimization opportunities:
1. Circular imports
2. Unused imports
3. Heavy imports that could be lazy-loaded
4. Import organization improvements
"""

import ast
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImportAnalyzer(ast.NodeVisitor):
    """AST-based import analyzer."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports: List[Dict] = []
        self.import_usage: Dict[str, List[int]] = defaultdict(
            list
        )  # name -> line numbers
        self.function_imports: Dict[str, List[Dict]] = defaultdict(
            list
        )  # function -> imports

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(
                {
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "function": None,
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.imports.append(
                {
                    "type": "from_import",
                    "module": node.module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "function": None,
                }
            )

    def visit_Name(self, node: ast.Name):
        # Track where imported names are used
        self.import_usage[node.id].append(node.lineno)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for imports inside functions (lazy loading opportunity)
        for child in ast.walk(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        self.function_imports[node.name].append(
                            {
                                "type": "import",
                                "module": alias.name,
                                "line": child.lineno,
                            }
                        )
                elif isinstance(child, ast.ImportFrom):
                    for alias in child.names:
                        self.function_imports[node.name].append(
                            {
                                "type": "from_import",
                                "module": child.module,
                                "name": alias.name,
                                "line": child.lineno,
                            }
                        )

        self.generic_visit(node)


class ImportOptimizer:
    """Analyze and optimize imports across the codebase."""

    def __init__(self, src_path: Path):
        self.src_path = src_path
        self.files_analyzed: Dict[str, ImportAnalyzer] = {}
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.circular_imports: List[List[str]] = []
        self.optimization_suggestions: List[Dict] = []

    def analyze_file(self, file_path: Path) -> ImportAnalyzer:
        """Analyze imports in a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, str(file_path))
            analyzer = ImportAnalyzer(str(file_path))
            analyzer.visit(tree)
            return analyzer

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Failed to analyze {file_path}: {e}")
            return ImportAnalyzer(str(file_path))

    def analyze_all_files(self):
        """Analyze all Python files in the project."""
        print("🔍 Analyzing import patterns...")

        python_files = list(self.src_path.rglob("*.py"))
        print(f"📁 Found {len(python_files)} Python files")

        for file_path in python_files:
            rel_path = str(file_path.relative_to(self.src_path))
            self.files_analyzed[rel_path] = self.analyze_file(file_path)

        print(f"✅ Analyzed {len(self.files_analyzed)} files")

    def build_import_graph(self):
        """Build import dependency graph."""
        print("🔗 Building import dependency graph...")

        for file_path, analyzer in self.files_analyzed.items():
            module_name = file_path.replace("/", ".").replace(".py", "")

            for imp in analyzer.imports:
                if imp["type"] == "from_import" and imp["module"]:
                    if imp["module"].startswith("omnibase_core"):
                        self.import_graph[module_name].add(imp["module"])
                elif imp["type"] == "import":
                    if imp["module"].startswith("omnibase_core"):
                        self.import_graph[module_name].add(imp["module"])

    def find_circular_imports(self):
        """Detect circular import patterns."""
        print("🔄 Detecting circular imports...")

        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.import_graph.get(node, []):
                dfs(neighbor, path + [neighbor])

            rec_stack.remove(node)

        for module in self.import_graph:
            if module not in visited:
                dfs(module, [module])

        self.circular_imports = cycles
        if cycles:
            print(f"⚠️  Found {len(cycles)} circular import patterns")
        else:
            print("✅ No circular imports detected")

    def analyze_heavy_imports(self):
        """Identify potentially heavy imports that could be lazy-loaded."""
        print("🔍 Analyzing heavy imports...")

        # Common heavy imports that might benefit from lazy loading
        heavy_imports = {
            "pydantic": "Heavy validation library",
            "requests": "HTTP library with dependencies",
            "numpy": "Scientific computing library",
            "pandas": "Data analysis library",
            "matplotlib": "Plotting library",
            "scipy": "Scientific library",
            "PIL": "Image processing library",
            "cv2": "Computer vision library",
        }

        lazy_loading_opportunities = []

        for file_path, analyzer in self.files_analyzed.items():
            top_level_heavy = []
            function_heavy = []

            for imp in analyzer.imports:
                module = imp.get("module", "") or ""
                for heavy_module, description in heavy_imports.items():
                    if heavy_module in module:
                        if imp["function"] is None:
                            top_level_heavy.append((imp, description))
                        else:
                            function_heavy.append((imp, description))

            if top_level_heavy and function_heavy:
                lazy_loading_opportunities.append(
                    {
                        "file": file_path,
                        "top_level": top_level_heavy,
                        "function_level": function_heavy,
                    }
                )

        if lazy_loading_opportunities:
            self.optimization_suggestions.extend(
                [
                    {
                        "type": "lazy_loading",
                        "file": opp["file"],
                        "description": f"Consider lazy loading heavy imports in {opp['file']}",
                        "impact": "Reduce import time",
                    }
                    for opp in lazy_loading_opportunities
                ]
            )

    def analyze_unused_imports(self):
        """Identify potentially unused imports."""
        print("🗑️  Analyzing unused imports...")

        unused_count = 0

        for file_path, analyzer in self.files_analyzed.items():
            for imp in analyzer.imports:
                import_name = (
                    imp.get("alias")
                    or imp.get("name")
                    or imp.get("module", "").split(".")[-1]
                )

                if import_name not in analyzer.import_usage:
                    self.optimization_suggestions.append(
                        {
                            "type": "unused_import",
                            "file": file_path,
                            "line": imp["line"],
                            "import": import_name,
                            "description": f"Potentially unused import: {import_name}",
                            "impact": "Reduce import overhead",
                        }
                    )
                    unused_count += 1

        print(f"📊 Found {unused_count} potentially unused imports")

    def analyze_import_organization(self):
        """Analyze import organization and suggest improvements."""
        print("📚 Analyzing import organization...")

        for file_path, analyzer in self.files_analyzed.items():
            # Group imports by type
            stdlib_imports = []
            third_party_imports = []
            local_imports = []

            for imp in analyzer.imports:
                module = imp.get("module", "") or ""
                if module.startswith("omnibase_core"):
                    local_imports.append(imp)
                elif any(
                    stdlib in module
                    for stdlib in [
                        "datetime",
                        "pathlib",
                        "typing",
                        "functools",
                        "collections",
                        "itertools",
                        "os",
                        "sys",
                    ]
                ):
                    stdlib_imports.append(imp)
                else:
                    third_party_imports.append(imp)

            # Check if imports are properly organized (stdlib -> third-party -> local)
            all_imports = analyzer.imports
            if len(all_imports) > 5:  # Only check files with significant imports
                # Simple heuristic: if local imports appear before third-party imports
                local_lines = [imp["line"] for imp in local_imports]
                third_party_lines = [imp["line"] for imp in third_party_imports]

                if (
                    local_lines
                    and third_party_lines
                    and min(local_lines) < max(third_party_lines)
                ):
                    self.optimization_suggestions.append(
                        {
                            "type": "import_organization",
                            "file": file_path,
                            "description": f"Import organization could be improved in {file_path}",
                            "impact": "Better code organization",
                        }
                    )

    def run_analysis(self):
        """Run complete import analysis."""
        print("🚀 Starting Import Analysis")
        print("=" * 50)

        self.analyze_all_files()
        self.build_import_graph()
        self.find_circular_imports()
        self.analyze_heavy_imports()
        self.analyze_unused_imports()
        self.analyze_import_organization()

    def print_results(self):
        """Print analysis results."""
        print("\n📊 Import Analysis Results:")
        print("=" * 50)

        print(f"Files analyzed: {len(self.files_analyzed)}")
        print(f"Circular imports: {len(self.circular_imports)}")
        print(f"Optimization suggestions: {len(self.optimization_suggestions)}")

        if self.circular_imports:
            print("\n🔄 Circular Import Patterns:")
            for i, cycle in enumerate(self.circular_imports[:5]):  # Show first 5
                print(f"  {i+1}. {' -> '.join(cycle)}")

        # Group suggestions by type
        suggestions_by_type = defaultdict(list)
        for suggestion in self.optimization_suggestions:
            suggestions_by_type[suggestion["type"]].append(suggestion)

        for suggestion_type, suggestions in suggestions_by_type.items():
            print(
                f"\n📋 {suggestion_type.replace('_', ' ').title()} ({len(suggestions)} items):"
            )
            for suggestion in suggestions[:3]:  # Show first 3 of each type
                print(f"  - {suggestion['description']}")

    def generate_optimization_recommendations(self):
        """Generate specific optimization recommendations."""
        print("\n🎯 Import Optimization Recommendations:")
        print("=" * 50)

        recommendations = []

        # 1. Circular imports (highest priority)
        if self.circular_imports:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": f"{len(self.circular_imports)} circular import patterns detected",
                    "solution": "Refactor circular dependencies using dependency injection or restructuring",
                    "impact": "Prevent import errors and improve modularity",
                }
            )

        # 2. Heavy imports
        heavy_import_count = len(
            [s for s in self.optimization_suggestions if s["type"] == "lazy_loading"]
        )
        if heavy_import_count > 0:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "issue": f"{heavy_import_count} heavy imports could be lazy-loaded",
                    "solution": "Move heavy imports inside functions where they are used",
                    "impact": "Reduce startup time and memory usage",
                }
            )

        # 3. Unused imports
        unused_count = len(
            [s for s in self.optimization_suggestions if s["type"] == "unused_import"]
        )
        if unused_count > 5:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "issue": f"{unused_count} potentially unused imports",
                    "solution": "Remove unused imports and add import linting to CI/CD",
                    "impact": "Reduce import overhead and improve code cleanliness",
                }
            )

        # 4. Import organization
        org_issues = len(
            [
                s
                for s in self.optimization_suggestions
                if s["type"] == "import_organization"
            ]
        )
        if org_issues > 0:
            recommendations.append(
                {
                    "priority": "LOW",
                    "issue": f"{org_issues} files with suboptimal import organization",
                    "solution": "Use tools like isort to automatically organize imports",
                    "impact": "Improve code readability and maintainability",
                }
            )

        if not recommendations:
            print("✅ No major import optimization issues detected!")
        else:
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. [{rec['priority']}] {rec['issue']}")
                print(f"   Solution: {rec['solution']}")
                print(f"   Impact: {rec['impact']}")

        return recommendations


def main():
    """Main entry point for import analysis."""
    src_path = Path(__file__).parent.parent.parent / "src"

    if not src_path.exists():
        print(f"❌ Source path does not exist: {src_path}")
        return

    optimizer = ImportOptimizer(src_path)

    start_time = time.perf_counter()
    optimizer.run_analysis()
    end_time = time.perf_counter()

    optimizer.print_results()
    recommendations = optimizer.generate_optimization_recommendations()

    print(f"\n⏱️  Analysis completed in {end_time - start_time:.2f} seconds")

    return recommendations


if __name__ == "__main__":
    main()
