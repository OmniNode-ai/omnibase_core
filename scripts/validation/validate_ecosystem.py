#!/usr/bin/env python3
"""
ONEX Ecosystem Validation
Cross-repository validation for the entire omni* ecosystem.

This script validates consistency and compliance across all omni* repositories
in a parent directory.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from validate_onex_standards import OnexStandardsValidator


class OnexEcosystemValidator:
    """Validates the entire ONEX ecosystem of repositories."""

    def __init__(self, ecosystem_path: str = ".."):
        self.ecosystem_path = Path(ecosystem_path)
        self.repositories = self._discover_repositories()
        self.results = {}

    def _discover_repositories(self) -> List[Path]:
        """Discover all omni* repositories in the ecosystem path."""
        repositories = []

        for path in self.ecosystem_path.iterdir():
            if (
                path.is_dir()
                and path.name.startswith("omni")
                and not path.name.startswith(".")
            ):
                # Check if it's a git repository
                if (path / ".git").exists() or (path / "pyproject.toml").exists():
                    repositories.append(path)

        repositories.sort(key=lambda p: p.name)
        return repositories

    def validate_ecosystem(self) -> Dict[str, Any]:
        """Validate all repositories in the ecosystem."""
        print(f"🌐 Validating ONEX Ecosystem ({len(self.repositories)} repositories)")
        print(f"   Ecosystem path: {self.ecosystem_path.absolute()}")
        print(f"   Repositories: {', '.join(r.name for r in self.repositories)}")

        ecosystem_results = {}
        ecosystem_violations = []
        ecosystem_warnings = []

        # Validate each repository
        for repo_path in self.repositories:
            print(f"\n🔍 Validating {repo_path.name}...")

            validator = OnexStandardsValidator(str(repo_path))
            repo_result = validator.validate_all()

            ecosystem_results[repo_path.name] = repo_result

            if not repo_result["success"]:
                ecosystem_violations.extend(
                    [f"{repo_path.name}: {v}" for v in repo_result["violations"]]
                )

            if repo_result["warnings"]:
                ecosystem_warnings.extend(
                    [f"{repo_path.name}: {w}" for w in repo_result["warnings"]]
                )

        # Cross-repository validation
        cross_repo_results = self._validate_cross_repository()
        ecosystem_results["cross_repository"] = cross_repo_results

        if not cross_repo_results["success"]:
            ecosystem_violations.extend(cross_repo_results["violations"])

        # Summary
        failed_repos = [
            name
            for name, result in ecosystem_results.items()
            if name != "cross_repository" and not result["success"]
        ]

        print(f"\n{'='*60}")
        if failed_repos or not cross_repo_results["success"]:
            print(f"❌ ONEX Ecosystem Validation FAILED")
            if failed_repos:
                print(f"   Failed repositories: {', '.join(failed_repos)}")
            if not cross_repo_results["success"]:
                print(f"   Cross-repository issues found")
        else:
            print(f"✅ ONEX Ecosystem Validation PASSED")
            print(f"   All {len(self.repositories)} repositories compliant")

        if ecosystem_violations:
            print(f"\n🚨 Ecosystem Violations ({len(ecosystem_violations)}):")
            for violation in ecosystem_violations[:20]:  # Limit output
                print(f"   • {violation}")
            if len(ecosystem_violations) > 20:
                print(f"   ... and {len(ecosystem_violations) - 20} more violations")

        if ecosystem_warnings:
            print(f"\n⚠️  Ecosystem Warnings ({len(ecosystem_warnings)}):")
            for warning in ecosystem_warnings[:10]:  # Limit output
                print(f"   • {warning}")
            if len(ecosystem_warnings) > 10:
                print(f"   ... and {len(ecosystem_warnings) - 10} more warnings")

        return {
            "success": len(failed_repos) == 0 and cross_repo_results["success"],
            "repositories": ecosystem_results,
            "violations": ecosystem_violations,
            "warnings": ecosystem_warnings,
            "summary": {
                "total_repositories": len(self.repositories),
                "passed_repositories": len(self.repositories) - len(failed_repos),
                "failed_repositories": len(failed_repos),
                "cross_repository_success": cross_repo_results["success"],
            },
        }

    def _validate_cross_repository(self) -> Dict[str, Any]:
        """Validate consistency across repositories."""
        violations = []

        # Check Python version consistency
        python_versions = self._check_python_versions()
        if len(python_versions) > 1:
            violations.append(f"Inconsistent Python versions: {python_versions}")

        # Check dependency version consistency for shared packages
        dep_inconsistencies = self._check_dependency_consistency()
        violations.extend(dep_inconsistencies)

        # Check pre-commit hook consistency
        precommit_inconsistencies = self._check_precommit_consistency()
        violations.extend(precommit_inconsistencies)

        # Check naming pattern consistency
        naming_inconsistencies = self._check_naming_consistency()
        violations.extend(naming_inconsistencies)

        return {
            "success": len(violations) == 0,
            "violations": violations,
            "checks": {
                "python_versions": python_versions,
                "dependency_consistency": dep_inconsistencies,
                "precommit_consistency": precommit_inconsistencies,
                "naming_consistency": naming_inconsistencies,
            },
        }

    def _check_python_versions(self) -> Dict[str, str]:
        """Check Python version consistency across repositories."""
        python_versions = {}

        for repo_path in self.repositories:
            pyproject_path = repo_path / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    import tomli

                    with open(pyproject_path, "rb") as f:
                        data = tomli.load(f)

                    python_version = (
                        data.get("tool", {})
                        .get("poetry", {})
                        .get("dependencies", {})
                        .get("python")
                    )

                    if python_version:
                        python_versions[repo_path.name] = python_version
                except Exception:
                    # If tomli not available or parsing fails, skip
                    pass

        return python_versions

    def _check_dependency_consistency(self) -> List[str]:
        """Check for inconsistent dependency versions across repositories."""
        violations = []

        # Common dependencies to check
        common_deps = ["pydantic", "fastapi", "pytest", "black", "isort", "mypy"]
        dep_versions = {dep: {} for dep in common_deps}

        for repo_path in self.repositories:
            pyproject_path = repo_path / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    import tomli

                    with open(pyproject_path, "rb") as f:
                        data = tomli.load(f)

                    dependencies = (
                        data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                    )

                    dev_dependencies = (
                        data.get("tool", {})
                        .get("poetry", {})
                        .get("group", {})
                        .get("dev", {})
                        .get("dependencies", {})
                    )

                    all_deps = {**dependencies, **dev_dependencies}

                    for dep in common_deps:
                        if dep in all_deps:
                            version = all_deps[dep]
                            if version not in dep_versions[dep]:
                                dep_versions[dep][version] = []
                            dep_versions[dep][version].append(repo_path.name)

                except Exception:
                    pass

        # Find inconsistencies
        for dep, versions in dep_versions.items():
            if len(versions) > 1:
                version_info = ", ".join(
                    [f"{v} ({', '.join(repos)})" for v, repos in versions.items()]
                )
                violations.append(f"Inconsistent {dep} versions: {version_info}")

        return violations

    def _check_precommit_consistency(self) -> List[str]:
        """Check for pre-commit hook consistency."""
        violations = []

        precommit_configs = {}
        for repo_path in self.repositories:
            precommit_path = repo_path / ".pre-commit-config.yaml"
            if precommit_path.exists():
                try:
                    with open(precommit_path) as f:
                        content = f.read()
                        # Simple text search for hook validation - no YAML parsing needed

                    # Simple check for hook IDs in content
                    hook_ids = set()
                    if "validate-repository-structure" in content:
                        hook_ids.add("validate-repository-structure")
                    if "validate-naming-conventions" in content:
                        hook_ids.add("validate-naming-conventions")

                    precommit_configs[repo_path.name] = hook_ids
                except Exception:
                    pass

        # Check for missing ONEX standard hooks
        required_hooks = {
            "validate-repository-structure",
            "validate-naming-conventions",
            "validate-string-versions",
            "black",
            "isort",
        }

        for repo_name, hooks in precommit_configs.items():
            missing_hooks = required_hooks - hooks
            if missing_hooks:
                violations.append(
                    f"{repo_name} missing required hooks: {', '.join(missing_hooks)}"
                )

        return violations

    def _check_naming_consistency(self) -> List[str]:
        """Check for naming pattern consistency."""
        violations = []

        # Check repository naming patterns
        valid_prefixes = ["omnibase", "omniagent", "omnimcp", "omnidocs"]

        for repo_path in self.repositories:
            repo_name = repo_path.name
            if not any(repo_name.startswith(prefix) for prefix in valid_prefixes):
                violations.append(
                    f"Repository {repo_name} doesn't follow omni* naming convention"
                )

        return violations

    def generate_report(self, output_path: str = "ecosystem_report.json"):
        """Generate a detailed ecosystem validation report."""
        if not self.results:
            self.results = self.validate_ecosystem()

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"📄 Detailed report saved to: {output_path}")


def main():
    """CLI interface for ecosystem validation."""
    parser = argparse.ArgumentParser(description="Validate ONEX ecosystem")
    parser.add_argument(
        "path", nargs="?", default="..", help="Path containing omni* repositories"
    )
    parser.add_argument("--report", help="Generate JSON report file")
    parser.add_argument(
        "--repositories", nargs="*", help="Specific repositories to validate"
    )

    args = parser.parse_args()

    validator = OnexEcosystemValidator(args.path)

    # Filter repositories if specified
    if args.repositories:
        validator.repositories = [
            r for r in validator.repositories if r.name in args.repositories
        ]

    # Run validation
    result = validator.validate_ecosystem()

    # Generate report if requested
    if args.report:
        validator.results = result
        validator.generate_report(args.report)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
