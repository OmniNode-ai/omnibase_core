#!/usr/bin/env python3
"""
Protocol Duplication Audit - Cross-Repository Analysis

Scans all omni* repositories and omnibase_spi to identify:
1. Duplicate protocol definitions (same interface, different repos)
2. Similar protocols that should be merged
3. Protocol naming conflicts
4. Missing protocols that should exist in SPI

Usage:
    python scripts/validation/audit_protocol_duplicates.py --repos-root ../
    python scripts/validation/audit_protocol_duplicates.py --check-repo omniagent
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProtocolInfo:
    """Information about a discovered protocol."""

    name: str
    file_path: str
    repository: str
    methods: list[str]
    signature_hash: str
    line_count: int
    imports: list[str]


class ProtocolSignatureExtractor(ast.NodeVisitor):
    """Extracts protocol signature for comparison."""

    def __init__(self):
        self.methods = []
        self.imports = []
        self.class_name = ""

    def visit_ClassDef(self, node):
        """Extract class definition."""
        if "Protocol" in node.name and node.name[0].isupper():
            self.class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Extract method signature
                    args = [arg.arg for arg in item.args.args if arg.arg != "self"]
                    returns = ast.unparse(item.returns) if item.returns else "None"
                    signature = f"{item.name}({', '.join(args)}) -> {returns}"
                    self.methods.append(signature)
                elif isinstance(item, ast.Expr) and isinstance(
                    item.value, ast.Constant
                ):
                    # Skip docstrings and ellipsis
                    continue
        self.generic_visit(node)

    def visit_Import(self, node):
        """Extract imports."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        """Extract from imports."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")


def extract_protocol_signature(file_path: Path) -> ProtocolInfo:
    """Extract protocol signature from Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        extractor = ProtocolSignatureExtractor()
        extractor.visit(tree)

        # Create signature hash from methods
        methods_str = "|".join(sorted(extractor.methods))
        signature_hash = hashlib.md5(methods_str.encode()).hexdigest()[:12]

        return ProtocolInfo(
            name=extractor.class_name,
            file_path=str(file_path),
            repository=file_path.parts[-4] if len(file_path.parts) >= 4 else "unknown",
            methods=extractor.methods,
            signature_hash=signature_hash,
            line_count=len(content.splitlines()),
            imports=extractor.imports,
        )

    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}")
        return None


def find_all_protocols(repos_root: Path) -> list[ProtocolInfo]:
    """Find all protocols across all repositories."""
    protocols = []

    # Look for omni* repositories
    for repo_path in repos_root.iterdir():
        if not repo_path.is_dir():
            continue

        repo_name = repo_path.name
        if not (repo_name.startswith("omni") or repo_name == "omnibase_spi"):
            continue

        print(f"🔍 Scanning {repo_name}...")

        # Find Python files that might contain protocols
        src_path = repo_path / "src"
        if not src_path.exists():
            continue

        for py_file in src_path.rglob("*.py"):
            # Only check files that are likely to contain protocols
            if (
                "protocol" in py_file.name.lower()
                or py_file.name.startswith("protocol_")
                or ("Protocol" in py_file.read_text(errors="ignore")[:1000])
            ):  # Check only first 1000 chars
                protocol_info = extract_protocol_signature(py_file)
                if (
                    protocol_info and protocol_info.name and protocol_info.methods
                ):  # Only count protocols with methods
                    protocols.append(protocol_info)

    return protocols


def analyze_duplicates(protocols: list[ProtocolInfo]) -> dict[str, list[ProtocolInfo]]:
    """Group protocols by similarity for duplicate analysis."""

    # Group by exact signature hash
    by_signature = defaultdict(list)
    for protocol in protocols:
        by_signature[protocol.signature_hash].append(protocol)

    # Group by name similarity
    by_name = defaultdict(list)
    for protocol in protocols:
        by_name[protocol.name].append(protocol)

    return {
        "exact_duplicates": {k: v for k, v in by_signature.items() if len(v) > 1},
        "name_conflicts": {k: v for k, v in by_name.items() if len(v) > 1},
    }


def print_duplication_report(duplicates: dict, protocols: list[ProtocolInfo]):
    """Print comprehensive duplication analysis report."""

    print("\n" + "=" * 80)
    print("🔍 PROTOCOL DUPLICATION ANALYSIS REPORT")
    print("=" * 80)

    total_protocols = len(protocols)
    spi_protocols = len([p for p in protocols if "omnibase_spi" in p.repository])
    service_protocols = total_protocols - spi_protocols

    print("\n📊 PROTOCOL INVENTORY:")
    print(f"   Total protocols found: {total_protocols}")
    print(f"   In omnibase_spi: {spi_protocols}")
    print(f"   In service repos: {service_protocols}")

    # Exact duplicates (same interface)
    exact_dupes = duplicates["exact_duplicates"]
    if exact_dupes:
        print(f"\n🚨 EXACT DUPLICATES FOUND: {len(exact_dupes)} groups")
        print("   These protocols have identical interfaces and should be merged:")

        for signature_hash, duplicate_protocols in exact_dupes.items():
            print(f"\n   📋 Signature Hash: {signature_hash}")
            for protocol in duplicate_protocols:
                spi_marker = (
                    "✅ [IN SPI]"
                    if "omnibase_spi" in protocol.repository
                    else "❌ [SERVICE]"
                )
                print(f"      {spi_marker} {protocol.name}")
                print(f"         Repository: {protocol.repository}")
                print(f"         File: {protocol.file_path}")
                print(f"         Methods: {len(protocol.methods)}")

            # Recommend action
            spi_versions = [
                p for p in duplicate_protocols if "omnibase_spi" in p.repository
            ]
            if spi_versions:
                print(
                    "      💡 RECOMMENDATION: Keep SPI version, remove from service repos"
                )
            else:
                print(
                    "      💡 RECOMMENDATION: Move to omnibase_spi, remove duplicates"
                )

    # Name conflicts (same name, different interface)
    name_conflicts = duplicates["name_conflicts"]
    if name_conflicts:
        print(f"\n⚠️  NAME CONFLICTS FOUND: {len(name_conflicts)} conflicts")
        print("   These protocols share names but have different interfaces:")

        for name, conflicting_protocols in name_conflicts.items():
            if len(conflicting_protocols) > 1:
                print(f"\n   📋 Protocol Name: {name}")
                for protocol in conflicting_protocols:
                    print(f"      Repository: {protocol.repository}")
                    print(f"      Signature: {protocol.signature_hash}")
                    print(
                        f"      Methods: {protocol.methods[:3]}{'...' if len(protocol.methods) > 3 else ''}"
                    )
                print("      💡 RECOMMENDATION: Rename or merge these protocols")

    # Migration opportunities
    service_only_protocols = [
        p for p in protocols if "omnibase_spi" not in p.repository
    ]
    if service_only_protocols:
        print(f"\n🎯 MIGRATION OPPORTUNITIES: {len(service_only_protocols)} protocols")
        print("   These protocols exist only in service repos and should move to SPI:")

        by_repo = defaultdict(list)
        for protocol in service_only_protocols:
            by_repo[protocol.repository].append(protocol)

        for repo, repo_protocols in by_repo.items():
            print(f"\n   📦 {repo} ({len(repo_protocols)} protocols):")
            for protocol in repo_protocols:
                print(f"      • {protocol.name}")
                print(
                    f"        Methods: {len(protocol.methods)}, Lines: {protocol.line_count}"
                )
                print(
                    f"        Suggested SPI location: protocols/{suggest_spi_location(protocol)}/"
                )

    if not exact_dupes and not name_conflicts:
        print("\n✅ NO DUPLICATES FOUND!")
        print("   All protocols have unique names and signatures.")
        if service_protocols > 0:
            print(
                f"   However, {service_protocols} protocols should still migrate to SPI for architectural purity."
            )


def suggest_spi_location(protocol: ProtocolInfo) -> str:
    """Suggest appropriate SPI directory for a protocol."""
    name_lower = protocol.name.lower()

    if any(word in name_lower for word in ["agent", "lifecycle", "coordinator"]):
        return "agent"
    elif any(word in name_lower for word in ["workflow", "task", "execution"]):
        return "workflow"
    elif any(word in name_lower for word in ["file", "reader", "writer", "storage"]):
        return "file_handling"
    elif any(word in name_lower for word in ["event", "bus", "message", "pub"]):
        return "core"
    elif any(word in name_lower for word in ["monitor", "metric", "observ", "trace"]):
        return "monitoring"
    elif any(word in name_lower for word in ["service", "client", "integration"]):
        return "integration"
    elif any(
        word in name_lower for word in ["reducer", "orchestrator", "compute", "effect"]
    ):
        return "core"
    else:
        return "core"  # Default to core


def generate_migration_plan(protocols: list[ProtocolInfo], duplicates: dict) -> dict:
    """Generate actionable migration plan."""
    plan = {"remove_duplicates": [], "migrate_to_spi": [], "resolve_conflicts": []}

    # Handle exact duplicates
    for signature_hash, duplicate_protocols in duplicates["exact_duplicates"].items():
        spi_versions = [
            p for p in duplicate_protocols if "omnibase_spi" in p.repository
        ]
        service_versions = [
            p for p in duplicate_protocols if "omnibase_spi" not in p.repository
        ]

        if spi_versions and service_versions:
            # Remove service versions, keep SPI
            for service_protocol in service_versions:
                plan["remove_duplicates"].append(
                    {
                        "action": "delete",
                        "protocol": service_protocol.name,
                        "file": service_protocol.file_path,
                        "reason": f"Duplicate of SPI version: {spi_versions[0].file_path}",
                    }
                )
        elif len(service_versions) > 1:
            # Multiple service versions, migrate one to SPI, remove others
            primary = service_versions[0]
            plan["migrate_to_spi"].append(
                {
                    "action": "migrate",
                    "protocol": primary.name,
                    "from": primary.file_path,
                    "to": f"omnibase_spi/protocols/{suggest_spi_location(primary)}/",
                    "reason": "Primary version for SPI",
                }
            )

            for duplicate in service_versions[1:]:
                plan["remove_duplicates"].append(
                    {
                        "action": "delete",
                        "protocol": duplicate.name,
                        "file": duplicate.file_path,
                        "reason": f"Duplicate of {primary.file_path}",
                    }
                )

    # Handle name conflicts
    for name, conflicting_protocols in duplicates["name_conflicts"].items():
        if len(conflicting_protocols) > 1:
            plan["resolve_conflicts"].append(
                {
                    "action": "rename_or_merge",
                    "protocols": [p.file_path for p in conflicting_protocols],
                    "reason": f"Name conflict for {name}",
                }
            )

    return plan


def main():
    parser = argparse.ArgumentParser(
        description="Audit protocol duplicates across omni* repositories"
    )
    parser.add_argument(
        "--repos-root", default="../", help="Root directory containing repositories"
    )
    parser.add_argument("--check-repo", help="Check specific repository only")
    parser.add_argument(
        "--generate-plan", action="store_true", help="Generate migration plan JSON"
    )

    args = parser.parse_args()

    repos_root = Path(args.repos_root).resolve()

    if not repos_root.exists():
        print(f"❌ Repository root not found: {repos_root}")
        sys.exit(1)

    print(f"🔍 Scanning repositories in: {repos_root}")

    protocols = find_all_protocols(repos_root)

    if not protocols:
        print("❌ No protocols found in any repository")
        sys.exit(0)

    duplicates = analyze_duplicates(protocols)
    print_duplication_report(duplicates, protocols)

    if args.generate_plan:
        plan = generate_migration_plan(protocols, duplicates)
        import json

        with open("protocol_migration_plan.json", "w") as f:
            json.dump(plan, f, indent=2, default=str)
        print("\n💾 Migration plan saved to: protocol_migration_plan.json")

    # Exit codes for CI
    exact_dupes = len(duplicates["exact_duplicates"])
    name_conflicts = len(duplicates["name_conflicts"])

    if exact_dupes > 0 or name_conflicts > 0:
        print(
            f"\n🚨 VALIDATION FAILED: {exact_dupes} duplicates, {name_conflicts} conflicts"
        )
        sys.exit(1)
    else:
        print("\n✅ VALIDATION PASSED: No duplicates detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
