#!/usr/bin/env python3
"""
Phase 3 HIGH Risk Model Analysis Script

Identifies models with 50+ imports and complex factory methods for Phase 3 remediation.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def count_imports_in_file(file_path: Path) -> int:
    """Count total imports in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        import_count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                import_count += len(node.names)
            elif isinstance(node, ast.ImportFrom):
                import_count += len(node.names) if node.names else 1

        return import_count
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return 0


def has_factory_methods(file_path: Path) -> List[str]:
    """Check for factory methods in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        factory_methods = []

        # Find @classmethod factory patterns
        classmethod_pattern = (
            r"@classmethod\s+def\s+(from_\w+|create_\w+|parse_\w+|load_\w+)\s*\("
        )
        matches = re.finditer(classmethod_pattern, content, re.MULTILINE)
        for match in matches:
            factory_methods.append(match.group(1))

        # Find standalone factory function patterns
        function_pattern = (
            r"def\s+(from_\w+|create_\w+|parse_\w+|load_\w+)\s*\([^)]*\)\s*->"
        )
        matches = re.finditer(function_pattern, content, re.MULTILINE)
        for match in matches:
            factory_methods.append(match.group(1))

        return factory_methods
    except Exception as e:
        print(f"Error checking factory methods in {file_path}: {e}")
        return []


def analyze_system_dependencies(file_path: Path) -> Dict[str, int]:
    """Analyze dependencies on critical system components."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        critical_imports = {
            "infrastructure": 0,
            "core_services": 0,
            "event_system": 0,
            "container": 0,
            "protocols": 0,
            "node_system": 0,
        }

        # Pattern matching for critical system components
        patterns = {
            "infrastructure": r"from omnibase_core\.core\.infrastructure|import.*infrastructure",
            "core_services": r"from omnibase_core\.services|import.*services",
            "event_system": r"from omnibase_core\.events|import.*events",
            "container": r"from omnibase_core\.core\.model_onex_container|import.*container",
            "protocols": r"from omnibase_core\.protocol|import.*protocol",
            "node_system": r"from omnibase_core\.nodes|import.*nodes",
        }

        for category, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            critical_imports[category] = len(matches)

        return critical_imports
    except Exception as e:
        print(f"Error analyzing dependencies in {file_path}: {e}")
        return {}


def calculate_risk_score(
    import_count: int, factory_methods: List[str], critical_deps: Dict[str, int]
) -> Tuple[int, str]:
    """Calculate risk score for a model file."""
    score = 0
    risk_factors = []

    # Import complexity (50+ imports = HIGH risk baseline)
    if import_count >= 50:
        score += 50
        risk_factors.append(f"HIGH imports ({import_count})")
    elif import_count >= 25:
        score += 25
        risk_factors.append(f"MEDIUM imports ({import_count})")

    # Factory method complexity
    if factory_methods:
        factory_score = len(factory_methods) * 10
        score += factory_score
        risk_factors.append(f"Factory methods: {', '.join(factory_methods)}")

    # Critical system dependencies
    critical_score = sum(critical_deps.values()) * 5
    if critical_score > 0:
        score += critical_score
        risk_factors.append(f"Critical deps: {critical_deps}")

    # Risk level classification
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 25:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level, risk_factors


def scan_models_directory(base_path: Path) -> Dict[str, Dict]:
    """Scan models directory for risk analysis."""
    results = {}

    models_path = base_path / "src" / "omnibase_core" / "models"

    for root, dirs, files in os.walk(models_path):
        for file in files:
            if file.startswith("model_") and file.endswith(".py"):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(base_path)

                # Analyze file
                import_count = count_imports_in_file(file_path)
                factory_methods = has_factory_methods(file_path)
                critical_deps = analyze_system_dependencies(file_path)

                score, level, risk_factors = calculate_risk_score(
                    import_count, factory_methods, critical_deps
                )

                results[str(relative_path)] = {
                    "import_count": import_count,
                    "factory_methods": factory_methods,
                    "critical_deps": critical_deps,
                    "risk_score": score,
                    "risk_level": level,
                    "risk_factors": risk_factors,
                }

    return results


def generate_phase3_analysis():
    """Generate Phase 3 HIGH risk model analysis."""
    base_path = Path(".")

    print("🔍 Phase 3: HIGH Risk Model Analysis")
    print("=" * 50)

    results = scan_models_directory(base_path)

    # Filter for HIGH and CRITICAL risk models
    high_risk_models = {
        path: data
        for path, data in results.items()
        if data["risk_level"] in ["HIGH", "CRITICAL"]
    }

    print(f"\n📊 Analysis Results:")
    print(f"Total models scanned: {len(results)}")
    print(f"HIGH/CRITICAL risk models: {len(high_risk_models)}")

    # Sort by risk score (highest first)
    sorted_models = sorted(
        high_risk_models.items(), key=lambda x: x[1]["risk_score"], reverse=True
    )

    print(f"\n🚨 HIGH/CRITICAL Risk Models for Phase 3:")
    print("-" * 60)

    for i, (path, data) in enumerate(sorted_models, 1):
        print(f"\n{i}. {path}")
        print(f"   Risk Level: {data['risk_level']} (Score: {data['risk_score']})")
        print(f"   Imports: {data['import_count']}")
        print(f"   Factory Methods: {data['factory_methods']}")
        print(f"   Critical Dependencies: {data['critical_deps']}")
        print(f"   Risk Factors: {'; '.join(data['risk_factors'])}")

    # Generate prioritization matrix
    print(f"\n📋 Phase 3 Prioritization Matrix:")
    print("-" * 40)

    critical_models = [p for p, d in sorted_models if d["risk_level"] == "CRITICAL"]
    high_models = [p for p, d in sorted_models if d["risk_level"] == "HIGH"]

    print(f"CRITICAL Priority (Score 75+): {len(critical_models)} models")
    for path in critical_models[:5]:  # Top 5 critical
        print(f"  • {path}")

    print(f"\nHIGH Priority (Score 50-74): {len(high_models)} models")
    for path in high_models[:5]:  # Top 5 high
        print(f"  • {path}")

    return sorted_models


if __name__ == "__main__":
    high_risk_models = generate_phase3_analysis()
