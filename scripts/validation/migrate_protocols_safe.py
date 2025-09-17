#!/usr/bin/env python3
"""
Safe Protocol Migration with Deduplication

Safely migrates protocols from service repositories to omnibase_spi while:
1. Checking for existing duplicates in SPI
2. Comparing protocol signatures before migration
3. Preventing duplicate protocol creation
4. Updating import statements automatically

Usage:
    # Dry run first (recommended)
    python scripts/migration/migrate_protocols_safe.py --source-repo . --dry-run

    # Execute migration
    python scripts/migration/migrate_protocols_safe.py --source-repo . --execute

    # Migrate specific protocol
    python scripts/migration/migrate_protocols_safe.py --source-repo . --protocol ProtocolAgentLifecycle --execute
"""

import argparse
import ast
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import our duplication audit script
sys.path.append(str(Path(__file__).parent.parent / "validation"))
from audit_protocol_duplicates import (
    ProtocolInfo,
    analyze_duplicates,
    extract_protocol_signature,
    find_all_protocols,
    suggest_spi_location,
)


class SafeProtocolMigrator:
    """Safely migrates protocols with deduplication checks."""

    def __init__(self, source_repo: Path, spi_repo: Path, dry_run: bool = True):
        self.source_repo = source_repo.resolve()
        self.spi_repo = spi_repo.resolve()
        self.dry_run = dry_run
        self.migration_log = []

    def log_action(self, action: str, details: str):
        """Log migration action."""
        log_entry = f"{'[DRY RUN] ' if self.dry_run else ''}{action}: {details}"
        self.migration_log.append(log_entry)
        print(f"{'🔍' if self.dry_run else '✅'} {log_entry}")

    def find_source_protocols(self) -> List[ProtocolInfo]:
        """Find all protocols in source repository."""
        protocols = []
        src_path = self.source_repo / "src"

        if not src_path.exists():
            self.log_action("ERROR", f"Source path not found: {src_path}")
            return protocols

        for py_file in src_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "class Protocol" in content:
                    protocol_info = extract_protocol_signature(py_file)
                    if protocol_info and protocol_info.name:
                        protocols.append(protocol_info)
            except Exception as e:
                self.log_action("WARNING", f"Could not parse {py_file}: {e}")

        return protocols

    def find_spi_protocols(self) -> List[ProtocolInfo]:
        """Find all existing protocols in omnibase_spi."""
        protocols = []
        spi_src = self.spi_repo / "src" / "omnibase_spi" / "protocols"

        if not spi_src.exists():
            self.log_action("INFO", f"SPI protocols directory not found: {spi_src}")
            return protocols

        for py_file in spi_src.rglob("*.py"):
            try:
                if py_file.name != "__init__.py":
                    protocol_info = extract_protocol_signature(py_file)
                    if protocol_info and protocol_info.name:
                        protocols.append(protocol_info)
            except Exception as e:
                self.log_action("WARNING", f"Could not parse SPI file {py_file}: {e}")

        return protocols

    def check_for_duplicates(
        self, source_protocol: ProtocolInfo, spi_protocols: List[ProtocolInfo]
    ) -> Optional[ProtocolInfo]:
        """Check if protocol already exists in SPI."""

        # Check by name
        name_matches = [p for p in spi_protocols if p.name == source_protocol.name]
        if name_matches:
            existing = name_matches[0]
            if existing.signature_hash == source_protocol.signature_hash:
                return existing  # Exact duplicate
            else:
                self.log_action(
                    "CONFLICT",
                    f"Protocol {source_protocol.name} exists in SPI with different signature",
                )
                self.log_action(
                    "DETAILS",
                    f"Source: {source_protocol.signature_hash} vs SPI: {existing.signature_hash}",
                )
                return existing  # Name conflict

        # Check by signature hash (same interface, different name)
        signature_matches = [
            p
            for p in spi_protocols
            if p.signature_hash == source_protocol.signature_hash
        ]
        if signature_matches:
            existing = signature_matches[0]
            self.log_action(
                "SIMILAR",
                f"Protocol {source_protocol.name} has same signature as {existing.name} in SPI",
            )
            return existing

        return None  # No duplicate found

    def determine_spi_destination(self, protocol: ProtocolInfo) -> Path:
        """Determine appropriate SPI directory for protocol."""
        suggested_dir = suggest_spi_location(protocol)
        spi_protocols_dir = self.spi_repo / "src" / "omnibase_spi" / "protocols"
        destination_dir = spi_protocols_dir / suggested_dir

        return destination_dir

    def migrate_protocol_file(
        self, source_protocol: ProtocolInfo, destination_dir: Path
    ) -> bool:
        """Migrate protocol file to SPI."""
        source_file = Path(source_protocol.file_path)
        destination_file = destination_dir / source_file.name

        if destination_file.exists():
            self.log_action(
                "ERROR", f"Destination file already exists: {destination_file}"
            )
            return False

        try:
            if not self.dry_run:
                destination_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, destination_file)

                # Update __init__.py in destination directory
                self.update_init_file(destination_dir, source_protocol.name)

            self.log_action(
                "MIGRATE",
                f"Moved {source_protocol.name} from {source_file} to {destination_file}",
            )
            return True

        except Exception as e:
            self.log_action("ERROR", f"Failed to migrate {source_protocol.name}: {e}")
            return False

    def update_init_file(self, directory: Path, protocol_name: str):
        """Update __init__.py to export the new protocol."""
        init_file = directory / "__init__.py"

        if not init_file.exists():
            # Create new __init__.py
            content = f'"""Protocol definitions for {directory.name}."""\n\n'
            content += (
                f"from .{Path(protocol_name.lower()).stem} import {protocol_name}\n\n"
            )
            content += f"__all__ = ['{protocol_name}']\n"
        else:
            # Update existing __init__.py
            content = init_file.read_text()
            if protocol_name not in content:
                # Add import
                import_line = (
                    f"from .{Path(protocol_name.lower()).stem} import {protocol_name}\n"
                )

                if "from ." in content:
                    # Add after last import
                    lines = content.splitlines()
                    import_index = -1
                    for i, line in enumerate(lines):
                        if line.startswith("from ."):
                            import_index = i
                    if import_index >= 0:
                        lines.insert(import_index + 1, import_line.strip())
                        content = "\n".join(lines)
                else:
                    # Add at beginning
                    content = import_line + content

                # Update __all__
                if "__all__" in content:
                    # Add to existing __all__
                    content = content.replace(
                        "__all__ = [", f"__all__ = ['{protocol_name}', "
                    )
                else:
                    # Add __all__
                    content += f"\n__all__ = ['{protocol_name}']\n"

        if not self.dry_run:
            init_file.write_text(content)

    def update_source_imports(
        self, source_protocol: ProtocolInfo, destination_path: str
    ):
        """Update imports in source repository to reference SPI."""
        repo_src = self.source_repo / "src"

        # Find all Python files that might import this protocol
        for py_file in repo_src.rglob("*.py"):
            try:
                content = py_file.read_text()
                protocol_name = source_protocol.name

                # Look for imports of this protocol
                if protocol_name in content:
                    # Update relative imports to SPI imports
                    updated_content = self.replace_protocol_imports(
                        content, protocol_name, destination_path
                    )

                    if updated_content != content:
                        if not self.dry_run:
                            py_file.write_text(updated_content)
                        self.log_action(
                            "UPDATE_IMPORT", f"Updated imports in {py_file}"
                        )

            except Exception as e:
                self.log_action(
                    "WARNING", f"Could not update imports in {py_file}: {e}"
                )

    def replace_protocol_imports(
        self, content: str, protocol_name: str, spi_path: str
    ) -> str:
        """Replace protocol imports with SPI imports."""
        lines = content.splitlines()
        updated_lines = []

        for line in lines:
            # Skip lines that already import from omnibase_spi
            if "omnibase_spi" in line:
                updated_lines.append(line)
                continue

            # Replace local protocol imports
            if (
                f"import {protocol_name}" in line
                or f"from " in line
                and protocol_name in line
            ):
                # Convert to SPI import
                new_import = (
                    f"from omnibase_spi.protocols.{spi_path} import {protocol_name}"
                )
                updated_lines.append(new_import)
                self.log_action("REPLACE_IMPORT", f"'{line.strip()}' → '{new_import}'")
            else:
                updated_lines.append(line)

        return "\n".join(updated_lines)

    def remove_source_protocol(self, source_protocol: ProtocolInfo):
        """Remove protocol file from source repository."""
        source_file = Path(source_protocol.file_path)

        if not self.dry_run:
            source_file.unlink()

        self.log_action("REMOVE", f"Deleted source file: {source_file}")

    def migrate_protocols(self, specific_protocol: Optional[str] = None) -> Dict:
        """Execute complete protocol migration with safety checks."""
        results = {"migrated": [], "skipped": [], "conflicts": [], "errors": []}

        # Find protocols in source and SPI
        source_protocols = self.find_source_protocols()
        spi_protocols = self.find_spi_protocols()

        self.log_action(
            "INVENTORY",
            f"Found {len(source_protocols)} protocols in source, {len(spi_protocols)} in SPI",
        )

        if specific_protocol:
            source_protocols = [
                p for p in source_protocols if p.name == specific_protocol
            ]
            if not source_protocols:
                self.log_action(
                    "ERROR", f"Protocol {specific_protocol} not found in source"
                )
                return results

        for source_protocol in source_protocols:
            self.log_action("PROCESSING", f"Analyzing {source_protocol.name}")

            # Check for duplicates
            duplicate = self.check_for_duplicates(source_protocol, spi_protocols)

            if duplicate:
                if duplicate.signature_hash == source_protocol.signature_hash:
                    self.log_action(
                        "SKIP",
                        f"{source_protocol.name} already exists in SPI with same signature",
                    )

                    # Update imports and remove source
                    spi_path = Path(duplicate.file_path).parent.name
                    self.update_source_imports(source_protocol, spi_path)
                    self.remove_source_protocol(source_protocol)

                    results["skipped"].append(source_protocol.name)
                else:
                    self.log_action(
                        "CONFLICT",
                        f"{source_protocol.name} conflicts with existing SPI protocol",
                    )
                    results["conflicts"].append(source_protocol.name)
                continue

            # No duplicate found - safe to migrate
            destination_dir = self.determine_spi_destination(source_protocol)
            spi_path = destination_dir.name

            success = self.migrate_protocol_file(source_protocol, destination_dir)
            if success:
                self.update_source_imports(source_protocol, spi_path)
                self.remove_source_protocol(source_protocol)
                results["migrated"].append(source_protocol.name)
            else:
                results["errors"].append(source_protocol.name)

        return results

    def generate_summary_report(self, results: Dict):
        """Generate migration summary report."""
        print("\n" + "=" * 80)
        print("📋 PROTOCOL MIGRATION SUMMARY")
        print("=" * 80)

        migrated = results["migrated"]
        skipped = results["skipped"]
        conflicts = results["conflicts"]
        errors = results["errors"]

        print(f"\n✅ Successfully migrated: {len(migrated)}")
        for protocol in migrated:
            print(f"   • {protocol}")

        print(f"\n⏭️  Skipped (already in SPI): {len(skipped)}")
        for protocol in skipped:
            print(f"   • {protocol}")

        print(f"\n⚠️  Conflicts detected: {len(conflicts)}")
        for protocol in conflicts:
            print(f"   • {protocol} (manual resolution required)")

        print(f"\n❌ Errors encountered: {len(errors)}")
        for protocol in errors:
            print(f"   • {protocol}")

        # Save migration log
        if not self.dry_run:
            log_file = self.source_repo / "protocol_migration_log.txt"
            with open(log_file, "w") as f:
                f.write("\n".join(self.migration_log))
            print(f"\n💾 Migration log saved: {log_file}")

        return len(conflicts) == 0 and len(errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Safely migrate protocols to omnibase_spi"
    )
    parser.add_argument("--source-repo", default=".", help="Source repository path")
    parser.add_argument(
        "--spi-repo", default="../omnibase_spi", help="omnibase_spi repository path"
    )
    parser.add_argument("--protocol", help="Migrate specific protocol only")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Dry run (default)"
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute migration (overrides dry-run)"
    )

    args = parser.parse_args()

    # Handle dry-run vs execute
    dry_run = args.dry_run and not args.execute

    source_repo = Path(args.source_repo)
    spi_repo = Path(args.spi_repo)

    if not source_repo.exists():
        print(f"❌ Source repository not found: {source_repo}")
        sys.exit(1)

    if not spi_repo.exists():
        print(f"❌ SPI repository not found: {spi_repo}")
        sys.exit(1)

    print(f"🚀 Starting {'DRY RUN' if dry_run else 'LIVE'} protocol migration")
    print(f"   Source: {source_repo}")
    print(f"   SPI: {spi_repo}")

    migrator = SafeProtocolMigrator(source_repo, spi_repo, dry_run)
    results = migrator.migrate_protocols(args.protocol)
    success = migrator.generate_summary_report(results)

    if success:
        print(f"\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Migration completed with issues - check conflicts and errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
