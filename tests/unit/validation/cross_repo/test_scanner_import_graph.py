"""Tests for import graph scanner.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
    ModelImportInfo,
    ScannerImportGraph,
)

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


class TestModelImportInfo:
    """Tests for ModelImportInfo model."""

    def test_full_import_path_simple_import(self) -> None:
        """Test full_import_path for simple import."""
        info = ModelImportInfo(
            module="os.path",
            line_number=1,
            is_from_import=False,
        )

        assert info.full_import_path == "os.path"

    def test_full_import_path_from_import(self) -> None:
        """Test full_import_path for from-style import."""
        info = ModelImportInfo(
            module="os.path",
            name="join",
            line_number=1,
            is_from_import=True,
        )

        assert info.full_import_path == "os.path.join"

    def test_immutable(self) -> None:
        """Test that ModelImportInfo is immutable."""
        info = ModelImportInfo(
            module="os",
            line_number=1,
            is_from_import=False,
        )

        with pytest.raises(Exception):  # ValidationError in Pydantic v2
            info.module = "sys"  # type: ignore[misc]


class TestModelFileImports:
    """Tests for ModelFileImports model."""

    def test_with_imports(self) -> None:
        """Test creating FileImports with imports."""
        imports = ModelFileImports(
            file_path=Path("/test/file.py"),
            imports=(
                ModelImportInfo(module="os", line_number=1, is_from_import=False),
            ),
        )

        assert imports.file_path == Path("/test/file.py")
        assert len(imports.imports) == 1
        assert imports.parse_error is None

    def test_with_parse_error(self) -> None:
        """Test creating FileImports with parse error."""
        imports = ModelFileImports(
            file_path=Path("/test/bad.py"),
            parse_error="Syntax error at line 5",
        )

        assert imports.parse_error is not None
        assert len(imports.imports) == 0


class TestScannerImportGraph:
    """Tests for ScannerImportGraph."""

    @pytest.fixture
    def scanner(self) -> ScannerImportGraph:
        """Create a scanner instance."""
        return ScannerImportGraph()

    def test_scan_simple_import(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning a file with simple imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent(
                """
            import os
            import sys
            from pathlib import Path
        """
            ).strip()
        )

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 3

        # Check import os
        os_import = next(i for i in result.imports if i.module == "os")
        assert os_import.is_from_import is False

        # Check from pathlib import Path
        path_import = next(i for i in result.imports if i.module == "pathlib")
        assert path_import.is_from_import is True
        assert path_import.name == "Path"

    def test_scan_from_import(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning from-style imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent(
                """
            from os.path import join, exists
            from typing import TYPE_CHECKING
        """
            ).strip()
        )

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 3

        # Check full import path property
        join_import = next(i for i in result.imports if i.name == "join")
        assert join_import.full_import_path == "os.path.join"

    def test_scan_syntax_error(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test handling of syntax errors."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def broken(")

        result = scanner.scan_file(test_file)

        assert result.parse_error is not None
        assert "Syntax error" in result.parse_error

    def test_scan_aliased_import(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning aliased imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import numpy as np")

        result = scanner.scan_file(test_file)

        assert len(result.imports) == 1
        assert result.imports[0].module == "numpy"
        assert result.imports[0].alias == "np"

    def test_scan_multiple_files(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning multiple files."""
        file1 = tmp_path / "a.py"
        file1.write_text("import os")

        file2 = tmp_path / "b.py"
        file2.write_text("import sys")

        results = scanner.scan_files([file1, file2])

        assert len(results) == 2
        assert file1 in results
        assert file2 in results

    def test_scan_relative_import(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning relative imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent(
                """
            from . import helper
            from .. import parent
            from .utils import util_func
        """
            ).strip()
        )

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 3

        # Relative imports should have empty or partial module
        helper_import = next(i for i in result.imports if i.name == "helper")
        assert helper_import.module == ""

    def test_scan_multiline_import(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning multiline imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent(
                """
            from typing import (
                Any,
                Dict,
                List,
            )
        """
            ).strip()
        )

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 3

    def test_scan_empty_file(self, scanner: ScannerImportGraph, tmp_path: Path) -> None:
        """Test scanning an empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 0

    def test_scan_file_not_found(self, scanner: ScannerImportGraph) -> None:
        """Test handling of file not found."""
        result = scanner.scan_file(Path("/nonexistent/file.py"))

        assert result.parse_error is not None
        assert "Could not read" in result.parse_error

    def test_get_all_imports(self, scanner: ScannerImportGraph, tmp_path: Path) -> None:
        """Test flattening all imports."""
        file1 = tmp_path / "a.py"
        file1.write_text("import os\nimport sys")

        file2 = tmp_path / "b.py"
        file2.write_text("import json")

        file_imports = scanner.scan_files([file1, file2])
        all_imports = scanner.get_all_imports(file_imports)

        assert len(all_imports) == 3
        # Check that tuples contain (path, import_info)
        paths = [p for p, _ in all_imports]
        assert file1 in paths
        assert file2 in paths

    def test_get_all_imports_skips_parse_errors(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test that get_all_imports skips files with parse errors."""
        good_file = tmp_path / "good.py"
        good_file.write_text("import os")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(")

        file_imports = scanner.scan_files([good_file, bad_file])
        all_imports = scanner.get_all_imports(file_imports)

        # Only the good file's imports should be included
        assert len(all_imports) == 1
        assert all_imports[0][0] == good_file

    def test_scan_with_comments_and_docstrings(
        self, scanner: ScannerImportGraph, tmp_path: Path
    ) -> None:
        """Test scanning files with comments and docstrings."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            dedent(
                '''
            """Module docstring."""
            # This is a comment
            import os  # inline comment

            # Another comment
            from pathlib import Path
        '''
            ).strip()
        )

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 2

    def test_scan_real_fixture_file(self, scanner: ScannerImportGraph) -> None:
        """Test scanning a real fixture file."""
        bad_handler = FIXTURES_DIR / "fake_app" / "src" / "fake_app" / "bad_handler.py"

        if not bad_handler.exists():
            pytest.skip("Fixture file not found")

        result = scanner.scan_file(bad_handler)

        assert result.parse_error is None
        # Should find the forbidden import
        modules = [i.full_import_path for i in result.imports]
        assert any("fake_infra.services" in m for m in modules)

    def test_import_star(self, scanner: ScannerImportGraph, tmp_path: Path) -> None:
        """Test scanning wildcard imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text("from os.path import *")

        result = scanner.scan_file(test_file)

        assert result.parse_error is None
        assert len(result.imports) == 1
        assert result.imports[0].name == "*"
        assert result.imports[0].is_from_import is True
