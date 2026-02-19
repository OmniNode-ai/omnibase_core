# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for error_taxonomy rule.

Related ticket: OMN-1775
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleErrorTaxonomyConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_error_taxonomy import (
    RuleErrorTaxonomy,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


class TestRuleErrorTaxonomy:
    """Tests for RuleErrorTaxonomy."""

    @pytest.fixture
    def config(self) -> ModelRuleErrorTaxonomyConfig:
        """Create a test configuration."""
        return ModelRuleErrorTaxonomyConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            canonical_error_modules=["omnibase_core.errors"],
            forbidden_error_modules=["omnibase_core.services"],
            base_error_class="ModelOnexError",
            require_error_code=True,
            warn_bare_raise=True,
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary source directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_wild_exception_in_forbidden_module(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that exceptions in forbidden modules are detected."""
        # Create a services directory (forbidden)
        services_dir = tmp_src_dir / "omnibase_core" / "services"
        services_dir.mkdir(parents=True)

        py_file = services_dir / "service_bad.py"
        py_file.write_text(
            '''
class ServiceError(Exception):
    """An error defined in the wrong place."""
    pass
'''
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        wild_issues = [i for i in issues if i.code == "ERROR_TAXONOMY_WILD_EXCEPTION"]
        assert len(wild_issues) == 1
        assert "ServiceError" in wild_issues[0].message
        assert wild_issues[0].severity == EnumSeverity.ERROR

    def test_detects_exception_outside_canonical_modules(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that exceptions outside canonical modules get a warning."""
        # Create a random module (not canonical, not forbidden)
        random_dir = tmp_src_dir / "omnibase_core" / "utils"
        random_dir.mkdir(parents=True)

        py_file = random_dir / "util_helpers.py"
        py_file.write_text(
            '''
class HelperError(Exception):
    """An error defined outside canonical modules."""
    pass
'''
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should be a warning, not an error
        wild_issues = [i for i in issues if i.code == "ERROR_TAXONOMY_WILD_EXCEPTION"]
        assert len(wild_issues) == 1
        assert wild_issues[0].severity == EnumSeverity.WARNING

    def test_passes_exception_in_canonical_module(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that exceptions in canonical modules pass."""
        # Create the errors directory (canonical)
        errors_dir = tmp_src_dir / "omnibase_core" / "errors"
        errors_dir.mkdir(parents=True)

        py_file = errors_dir / "error_custom.py"
        py_file.write_text(
            '''
from omnibase_core.models.errors import ModelOnexError

class CustomError(ModelOnexError):
    """A properly placed error."""
    pass
'''
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should have no wild exception issues
        wild_issues = [i for i in issues if i.code == "ERROR_TAXONOMY_WILD_EXCEPTION"]
        assert len(wild_issues) == 0

    def test_detects_bad_inheritance(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that exceptions not inheriting from base class are detected."""
        errors_dir = tmp_src_dir / "omnibase_core" / "errors"
        errors_dir.mkdir(parents=True)

        py_file = errors_dir / "error_bad_inheritance.py"
        py_file.write_text(
            '''
class BadInheritanceError(Exception):
    """Inherits from Exception instead of ModelOnexError."""
    pass
'''
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        inheritance_issues = [
            i for i in issues if i.code == "ERROR_TAXONOMY_BAD_INHERITANCE"
        ]
        assert len(inheritance_issues) == 1
        assert "ModelOnexError" in inheritance_issues[0].message

    def test_detects_missing_error_code(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that ModelOnexError raises without error_code are detected."""
        py_file = tmp_src_dir / "missing_code.py"
        py_file.write_text(
            """
from omnibase_core.models.errors import ModelOnexError

def bad_function():
    raise ModelOnexError(message="Missing error code")
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        missing_code_issues = [
            i for i in issues if i.code == "ERROR_TAXONOMY_MISSING_CODE"
        ]
        assert len(missing_code_issues) == 1
        assert "error_code" in missing_code_issues[0].message

    def test_passes_raise_with_error_code(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that raises with error_code pass."""
        py_file = tmp_src_dir / "good_raise.py"
        py_file.write_text(
            """
from omnibase_core.models.errors import ModelOnexError
from omnibase_core.enums import EnumCoreErrorCode

def good_function():
    raise ModelOnexError(
        message="Has error code",
        error_code=EnumCoreErrorCode.VALIDATION_FAILED,
    )
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        missing_code_issues = [
            i for i in issues if i.code == "ERROR_TAXONOMY_MISSING_CODE"
        ]
        assert len(missing_code_issues) == 0

    def test_detects_bare_raise(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that bare raise statements are detected."""
        py_file = tmp_src_dir / "bare_raise.py"
        py_file.write_text(
            """
def risky_function():
    try:
        do_something()
    except ValueError:
        raise  # Bare raise without context
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        bare_raise_issues = [i for i in issues if i.code == "ERROR_TAXONOMY_BARE_RAISE"]
        assert len(bare_raise_issues) == 1
        assert bare_raise_issues[0].severity == EnumSeverity.WARNING

    def test_skips_bare_raise_when_disabled(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that bare raise warnings can be disabled."""
        config = ModelRuleErrorTaxonomyConfig(
            enabled=True,
            warn_bare_raise=False,
        )

        py_file = tmp_src_dir / "bare_raise.py"
        py_file.write_text(
            """
def risky_function():
    try:
        do_something()
    except ValueError:
        raise
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        bare_raise_issues = [i for i in issues if i.code == "ERROR_TAXONOMY_BARE_RAISE"]
        assert len(bare_raise_issues) == 0

    def test_skips_when_disabled(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that rule is skipped when disabled."""
        config = ModelRuleErrorTaxonomyConfig(enabled=False)

        py_file = tmp_src_dir / "bad_code.py"
        py_file.write_text(
            """
class WildError(Exception):
    pass

raise ModelOnexError(message="no code")
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_handles_syntax_errors(
        self,
        config: ModelRuleErrorTaxonomyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that files with syntax errors are skipped gracefully."""
        py_file = tmp_src_dir / "syntax_error.py"
        py_file.write_text(
            """
class BrokenError(Exception
    # Missing closing paren
"""
        )

        rule = RuleErrorTaxonomy(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        # Should not raise, should return empty
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0
