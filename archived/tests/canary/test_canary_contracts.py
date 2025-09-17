#!/usr/bin/env python3
"""
Simple contract structure checker for canary nodes.
Tests basic YAML structure and required fields without full Pydantic validation.
"""

from pathlib import Path


def check_yaml_structure_simple(file_path: Path) -> dict:
    """Simple YAML structure check without external dependencies."""
    try:
        # Try to read as plain text and look for key indicators
        with open(file_path) as f:
            content = f.read()

        # Check for required fields
        checks = {
            "has_node_type": "node_type:" in content,
            "has_main_tool_class": "main_tool_class:" in content,
            "has_dependencies": "dependencies:" in content,
            "has_service_config": "service_configuration:" in content,
            "uses_nodecanary_class": "NodeCanary" in content,
            "no_external_deps_for_compute": True,  # Will check specifically
        }

        # Check for architectural compliance
        is_compute = 'node_type: "COMPUTE"' in content
        has_external_deps = "requires_external_dependencies: true" in content

        if is_compute and has_external_deps:
            checks["no_external_deps_for_compute"] = False

        return {
            "file": str(file_path),
            "exists": True,
            "checks": checks,
            "is_valid": all(checks.values()),
            "content_length": len(content),
        }

    except Exception as e:
        return {
            "file": str(file_path),
            "exists": False,
            "error": str(e),
            "is_valid": False,
        }


def main():
    """Check all canary contracts."""
    print("🔍 CANARY CONTRACTS STRUCTURE CHECK")
    print("=" * 50)

    canary_path = Path("src/omnibase_core/nodes/canary")
    if not canary_path.exists():
        print(f"❌ Canary path not found: {canary_path}")
        return

    # Find all contract.yaml files
    contract_files = list(canary_path.glob("**/contract.yaml"))
    print(f"📋 Found {len(contract_files)} contract files\n")

    results = []
    for contract_file in sorted(contract_files):
        result = check_yaml_structure_simple(contract_file)
        results.append(result)

        # Extract node name from path
        node_name = contract_file.parent.parent.name

        if result["is_valid"]:
            print(f"✅ {node_name}: STRUCTURE OK")
        else:
            print(f"❌ {node_name}: ISSUES FOUND")

        # Show specific check results
        if "checks" in result:
            for check, passed in result["checks"].items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check}")

        if "error" in result:
            print(f"   ❌ Error: {result['error']}")

        print()

    # Summary
    valid_contracts = sum(1 for r in results if r["is_valid"])
    print(
        f"📊 SUMMARY: {valid_contracts}/{len(results)} contracts passed structure checks",
    )

    if valid_contracts == len(results):
        print("🎉 All contracts have valid structure!")
    else:
        print("⚠️  Some contracts need attention")


if __name__ == "__main__":
    main()
