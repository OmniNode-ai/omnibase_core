#!/usr/bin/env python3
"""Migration script for omni* ecosystem standardization."""

import shutil
import os
import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
import argparse

class RepositoryMigrator:
    """Migrates repository to standard omni* ecosystem structure."""

    def __init__(self, repo_path: Path, repo_name: str, dry_run: bool = False):
        self.repo_path = repo_path
        self.repo_name = repo_name
        self.dry_run = dry_run
        self.migration_log: List[str] = []
        self.errors: List[str] = []

    def migrate_repository(self):
        """Execute complete repository migration."""
        print(f"🚀 Starting migration for {self.repo_name}")

        if self.dry_run:
            print("   🔍 DRY RUN MODE - No changes will be made")

        try:
            self._create_standard_structure()
            self._migrate_scattered_models()
            self._migrate_enums()
            self._consolidate_protocols()
            self._create_onex_node_structure()
            self._generate_migration_report()

            if not self.errors:
                print(f"✅ Migration completed successfully for {self.repo_name}")
                return True
            else:
                print(f"⚠️  Migration completed with {len(self.errors)} warnings for {self.repo_name}")
                return False

        except Exception as e:
            self.errors.append(f"Critical error during migration: {str(e)}")
            print(f"❌ Migration failed for {self.repo_name}: {str(e)}")
            return False

    def _create_standard_structure(self):
        """Create standard directory structure."""
        standard_dirs = [
            f"src/{self.repo_name}/models",
            f"src/{self.repo_name}/enums",
            f"src/{self.repo_name}/nodes/effect",
            f"src/{self.repo_name}/nodes/compute",
            f"src/{self.repo_name}/nodes/reducer",
            f"src/{self.repo_name}/nodes/orchestrator",
            f"src/{self.repo_name}/services",
            f"src/{self.repo_name}/core",
            f"src/{self.repo_name}/mixins",
            f"src/{self.repo_name}/utils",
            f"src/{self.repo_name}/exceptions",
            f"src/{self.repo_name}/cli",
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "tools/validation",
            "tools/migration",
            "tools/quality",
            "docs",
        ]

        for dir_path in standard_dirs:
            full_path = self.repo_path / dir_path

            if not self.dry_run:
                full_path.mkdir(parents=True, exist_ok=True)

                # Create __init__.py files
                init_file = full_path / "__init__.py"
                if not init_file.exists():
                    init_file.write_text(f'"""Auto-generated __init__.py during migration."""\n')

            self.migration_log.append(f"Created directory: {dir_path}")

    def _migrate_scattered_models(self):
        """Consolidate all scattered model files."""
        print("   📂 Migrating scattered model files...")

        # Find all potential model files
        model_patterns = [
            "**/model_*.py",
            "**/models.py",
            "**/model.py",
            "**/*model*.py"
        ]

        model_files = set()
        for pattern in model_patterns:
            model_files.update(self.repo_path.rglob(pattern))

        # Filter out files in target directory and test files
        models_dir = self.repo_path / f"src/{self.repo_name}/models"
        filtered_files = []

        for model_file in model_files:
            # Skip if already in target directory
            if models_dir.exists() and models_dir in model_file.parents:
                continue

            # Skip test files
            if "test" in str(model_file).lower():
                continue

            # Skip __pycache__ and similar
            if "__pycache__" in str(model_file):
                continue

            # Check if file actually contains model classes
            if self._contains_model_classes(model_file):
                filtered_files.append(model_file)

        print(f"   📊 Found {len(filtered_files)} model files to migrate")

        for model_file in filtered_files:
            domain = self._extract_domain(model_file)
            domain_dir = models_dir / domain

            if not self.dry_run:
                domain_dir.mkdir(parents=True, exist_ok=True)

                # Create domain __init__.py
                domain_init = domain_dir / "__init__.py"
                if not domain_init.exists():
                    domain_init.write_text(f'"""Models for {domain} domain."""\n')

            # Determine target filename
            target_filename = self._standardize_model_filename(model_file)
            target_file = domain_dir / target_filename

            if not self.dry_run:
                try:
                    shutil.copy2(model_file, target_file)
                    self.migration_log.append(f"Migrated model: {model_file.relative_to(self.repo_path)} -> {target_file.relative_to(self.repo_path)}")
                except Exception as e:
                    self.errors.append(f"Failed to migrate {model_file}: {str(e)}")
            else:
                self.migration_log.append(f"[DRY RUN] Would migrate: {model_file.relative_to(self.repo_path)} -> {target_file.relative_to(self.repo_path)}")

    def _contains_model_classes(self, file_path: Path) -> bool:
        """Check if file contains classes that look like models."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    # Look for model-like patterns
                    if (class_name.startswith("Model") or
                        "BaseModel" in [base.id for base in node.bases if hasattr(base, 'id')] or
                        "model" in class_name.lower() or
                        any("pydantic" in str(decorator) for decorator in node.decorator_list)):
                        return True

        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            pass

        return False

    def _extract_domain(self, file_path: Path) -> str:
        """Extract domain from file path for organization."""
        path_parts = [part.lower() for part in file_path.parts]

        # Domain indicators in order of preference
        domain_indicators = [
            "auth", "authentication", "user", "workflow", "data", "config",
            "core", "event", "api", "service", "node", "protocol", "tool",
            "agent", "cli", "exception", "mixin", "util"
        ]

        # Check path parts for domain indicators
        for indicator in domain_indicators:
            for part in path_parts:
                if indicator in part:
                    return indicator

        # Check file content for domain hints
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()

            for indicator in domain_indicators:
                if indicator in content:
                    return indicator

        except:
            pass

        # Default domain
        return "common"

    def _standardize_model_filename(self, file_path: Path) -> str:
        """Generate standardized filename for model file."""
        original_name = file_path.name

        # If already follows convention, keep it
        if original_name.startswith("model_") and original_name.endswith(".py"):
            return original_name

        # Generate new name based on file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            model_classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Model"):
                    model_classes.append(node.name)

            if model_classes:
                # Use first model class name to generate filename
                class_name = model_classes[0]
                # Convert ModelUserAuth -> model_user_auth.py
                snake_name = self._camel_to_snake(class_name[5:])  # Remove "Model" prefix
                return f"model_{snake_name}.py"

        except:
            pass

        # Fallback: convert filename
        base_name = file_path.stem
        if base_name == "models" or base_name == "model":
            return "model_common.py"
        else:
            snake_name = self._camel_to_snake(base_name)
            return f"model_{snake_name}.py"

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        # Handle specific patterns
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()

    def _migrate_enums(self):
        """Consolidate all enum files."""
        print("   📊 Migrating enum files...")

        enum_files = []
        for pattern in ["**/enum_*.py", "**/*enum*.py"]:
            enum_files.extend(self.repo_path.rglob(pattern))

        enums_dir = self.repo_path / f"src/{self.repo_name}/enums"
        filtered_files = []

        for enum_file in enum_files:
            # Skip if already in target directory
            if enums_dir.exists() and enums_dir in enum_file.parents:
                continue

            # Skip test files
            if "test" in str(enum_file).lower():
                continue

            if self._contains_enum_classes(enum_file):
                filtered_files.append(enum_file)

        print(f"   📊 Found {len(filtered_files)} enum files to migrate")

        for enum_file in filtered_files:
            target_filename = self._standardize_enum_filename(enum_file)
            target_file = enums_dir / target_filename

            if not self.dry_run:
                try:
                    shutil.copy2(enum_file, target_file)
                    self.migration_log.append(f"Migrated enum: {enum_file.relative_to(self.repo_path)} -> {target_file.relative_to(self.repo_path)}")
                except Exception as e:
                    self.errors.append(f"Failed to migrate {enum_file}: {str(e)}")
            else:
                self.migration_log.append(f"[DRY RUN] Would migrate enum: {enum_file.relative_to(self.repo_path)} -> {target_file.relative_to(self.repo_path)}")

    def _contains_enum_classes(self, file_path: Path) -> bool:
        """Check if file contains enum classes."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class inherits from Enum or has Enum in name
                    bases = [base.id for base in node.bases if hasattr(base, 'id')]
                    if ("Enum" in bases or node.name.startswith("Enum") or
                        "enum" in node.name.lower()):
                        return True

        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            pass

        return False

    def _standardize_enum_filename(self, file_path: Path) -> str:
        """Generate standardized filename for enum file."""
        original_name = file_path.name

        if original_name.startswith("enum_") and original_name.endswith(".py"):
            return original_name

        # Generate based on content or filename
        base_name = file_path.stem
        snake_name = self._camel_to_snake(base_name)
        return f"enum_{snake_name}.py"

    def _consolidate_protocols(self):
        """Handle protocol migration/consolidation."""
        if self.repo_name == "omnibase_spi":
            print("   📋 SPI repository - protocols stay here")
            return

        print("   📋 Checking protocol files for migration to omnibase_spi...")

        protocol_files = list(self.repo_path.rglob("protocol_*.py"))

        if not protocol_files:
            print("   ✅ No protocol files found")
            return

        print(f"   📊 Found {len(protocol_files)} protocol files")

        if len(protocol_files) > 3:
            print(f"   ⚠️  {len(protocol_files)} protocol files exceed limit of 3 for non-SPI repositories")

            # List all protocol files that need migration
            self.migration_log.append(f"MANUAL MIGRATION NEEDED: {len(protocol_files)} protocol files should be moved to omnibase_spi:")
            for protocol_file in protocol_files:
                self.migration_log.append(f"  - {protocol_file.relative_to(self.repo_path)}")

            self.errors.append(f"Protocol migration required: {len(protocol_files)} files need manual migration to omnibase_spi")
        else:
            print(f"   ✅ Protocol count ({len(protocol_files)}) within acceptable limit of 3")

    def _create_onex_node_structure(self):
        """Create ONEX four-node architecture structure."""
        print("   🏗️  Creating ONEX four-node structure...")

        node_types = ["effect", "compute", "reducer", "orchestrator"]

        for node_type in node_types:
            node_dir = self.repo_path / f"src/{self.repo_name}/nodes/{node_type}"

            if not self.dry_run:
                node_dir.mkdir(parents=True, exist_ok=True)

                # Create node-specific __init__.py with template
                init_file = node_dir / "__init__.py"
                if not init_file.exists():
                    init_content = f'''"""
ONEX {node_type.upper()} Node implementations.

{self._get_node_description(node_type)}
"""
'''
                    init_file.write_text(init_content)

                # Create example node file if none exists
                example_files = list(node_dir.glob("*.py"))
                if len(example_files) <= 1:  # Only __init__.py exists
                    example_file = node_dir / f"node_{node_type}_example.py"
                    if not example_file.exists():
                        example_content = self._generate_node_template(node_type)
                        example_file.write_text(example_content)

            self.migration_log.append(f"Created ONEX {node_type} node structure")

    def _get_node_description(self, node_type: str) -> str:
        """Get description for node type."""
        descriptions = {
            "effect": "Data persistence and external system interactions.",
            "compute": "Business logic computations and data transformations.",
            "reducer": "Data aggregation and stream processing.",
            "orchestrator": "Workflow coordination and system orchestration."
        }
        return descriptions.get(node_type, "ONEX node implementation.")

    def _generate_node_template(self, node_type: str) -> str:
        """Generate template code for node type."""
        class_name = f"Node{node_type.capitalize()}Example"

        return f'''"""
Example {node_type.upper()} node implementation.

This is a template/example - replace with actual implementation.
"""

from typing import Any, Dict
from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.core.model_onex_container import ModelOnexContainer


class {class_name}(NodeReducerService):
    """
    Example {node_type.upper()} node following ONEX four-node architecture.

    {self._get_node_description(node_type)}
    """

    def __init__(self, container: ModelOnexContainer):
        super().__init__(container)
        # Initialize node-specific components

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data according to {node_type.upper()} node responsibilities.

        Args:
            input_data: Input data for processing

        Returns:
            Processed data
        """
        # TODO: Implement actual {node_type} logic
        return {{"processed": True, "node_type": "{node_type}"}}
'''

    def _generate_migration_report(self):
        """Generate migration completion report."""
        report_path = self.repo_path / "MIGRATION_REPORT.md"

        content = f"# Migration Report: {self.repo_name}\n\n"
        content += f"**Migration Date**: {datetime.now().isoformat()}\n"
        content += f"**Mode**: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}\n"
        content += f"**Status**: {'⚠️ WARNINGS' if self.errors else '✅ SUCCESS'}\n\n"

        if self.errors:
            content += "## ⚠️ Errors and Warnings\n\n"
            for error in self.errors:
                content += f"- {error}\n"
            content += "\n"

        content += "## 📋 Actions Taken\n\n"
        for log_entry in self.migration_log:
            content += f"- {log_entry}\n"

        content += "\n## 🔄 Next Steps\n\n"
        content += "1. **Verify imports**: Run validation scripts to check all imports work\n"
        content += "2. **Run validation**: Execute `python tools/validation/validate_structure.py . {}`\n".format(self.repo_name)
        content += "3. **Update documentation**: Update any references to old file locations\n"
        content += "4. **Run tests**: Execute test suite to ensure everything works\n"
        content += "5. **Clean up**: Remove old files after confirming migration success\n"

        if any("MANUAL MIGRATION NEEDED" in log for log in self.migration_log):
            content += "6. **Manual protocol migration**: Move protocol files to omnibase_spi\n"

        if not self.dry_run:
            report_path.write_text(content)

        print(f"\n📊 Migration Report:")
        print(f"   - Actions taken: {len(self.migration_log)}")
        print(f"   - Errors/Warnings: {len(self.errors)}")
        if not self.dry_run:
            print(f"   - Report saved: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Migrate repository to omni* ecosystem standards")
    parser.add_argument("repo_path", help="Path to repository root")
    parser.add_argument("repo_name", help="Repository name (e.g., omnibase_core)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)

    print(f"🚀 Omni* Ecosystem Repository Migration")
    print(f"Repository: {args.repo_name}")
    print(f"Path: {repo_path}")

    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)\n")
    else:
        print("Mode: LIVE MIGRATION\n")

    migrator = RepositoryMigrator(repo_path, args.repo_name, args.dry_run)
    success = migrator.migrate_repository()

    if success:
        print(f"\n✅ Migration completed successfully!")
        print(f"📋 Run validation: python tools/validation/validate_structure.py . {args.repo_name}")
        sys.exit(0)
    else:
        print(f"\n⚠️  Migration completed with warnings - review MIGRATION_REPORT.md")
        sys.exit(0)  # Don't fail for warnings

if __name__ == "__main__":
    main()