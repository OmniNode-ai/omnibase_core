# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Port the seven remaining old markdown-validator test classes to the node.

Old LinkInfo inputs become markdown links, result validity becomes PASS/FAIL,
and heading assertions inspect the runtime's gathered anchor inventory.
"""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_markdown_links_check_compute.handler import (
    NodeMarkdownLinksCheckCompute,
)
from omnibase_core.nodes.node_markdown_links_check_compute.runtime_markdown_links_check import (
    build_request,
    main,
)

pytestmark = pytest.mark.unit


def _write(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _run(
    root: Path,
    capsys: pytest.CaptureFixture[str],
    exit_code: int,
    source_file: Path | None = None,
) -> tuple[ModelMarkdownLinksCheckInput, ModelValidationReport, str]:
    root = root.resolve()
    paths = [source_file] if source_file else []
    request, errors = build_request(
        root, paths, root / ".markdown-link-check.json", None
    )
    assert errors == []
    report = NodeMarkdownLinksCheckCompute().handle(request)
    report_path = root / "report.json"
    args = ["--root", str(root), "--verbose", "--report-json", str(report_path)]
    if source_file:
        args.insert(0, str(source_file))
    assert main(args) == exit_code
    saved = ModelValidationReport.model_validate_json(report_path.read_text())
    assert saved.findings == report.findings
    assert saved.overall_status == report.overall_status
    assert report.overall_status == ("PASS" if exit_code == 0 else "FAIL")
    output = capsys.readouterr()
    assert output.err == ""
    if exit_code == 0:
        assert report.findings == ()
        assert "Markdown Links: PASS" in output.out
    else:
        assert report.findings
        assert "MARKDOWN LINK VALIDATION FAILED" in output.out
    return request, report, output.out


def _anchors(request: ModelMarkdownLinksCheckInput, path: Path) -> set[str]:
    return set(
        next(entry.anchors for entry in request.inventory if entry.path == str(path))
    )


def _assert_broken(
    report: ModelValidationReport,
    source_file: Path,
    url: str,
    message: str,
    display: str,
    rule: str = "internal-link",
) -> None:
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == f"{source_file}:1"
    assert finding.rule_id == rule
    assert finding.message == message
    assert finding.evidence == {"target": url, "display_link": display}


class TestURLEncodedAnchors:
    def test_url_encoded_space_in_anchor(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        md_file = _write(tmp_path, "test.md", "## my section\n\nSome content here.\n")
        # Materialize the old separate LinkInfo on line one of the same file.
        md_file.write_text(
            "[Link to section](#my-section)\n" + md_file.read_text(), encoding="utf-8"
        )
        request, _, _ = _run(tmp_path, capsys, 0, md_file)
        assert "my-section" in _anchors(request, md_file)

    def test_url_encoded_special_chars(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        md_file = _write(tmp_path, "test.md", "## foo bar\n\nContent.\n")
        md_file.write_text("[Link](#foo-bar)\n" + md_file.read_text(), encoding="utf-8")
        request, _, _ = _run(tmp_path, capsys, 0, md_file)
        assert "foo-bar" in _anchors(request, md_file)

    def test_double_encoded_anchor(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        md_file = _write(tmp_path, "test.md", "## normal heading\n\nContent.\n")
        md_file.write_text(
            "[Double encoded](#%2520invalid)\n" + md_file.read_text(), encoding="utf-8"
        )
        _, report, output = _run(tmp_path, capsys, 1, md_file)
        _assert_broken(
            report,
            md_file,
            "#%2520invalid",
            "Anchor '%20invalid' not found in file",
            "[Double encoded](#%2520invalid)",
        )
        assert "not found" in report.findings[0].message.lower()
        assert "Link: [Double encoded](#%2520invalid)" in output

    def test_percent_in_heading(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        md_file = _write(tmp_path, "test.md", "## 100% Complete\n\nContent.\n")
        source = _write(tmp_path, "source.md", "[Link](test.md#100-complete)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "100-complete" in _anchors(request, md_file)


class TestUnicodeFilenames:
    def test_unicode_heading(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "test.md", "## 日本語\n\nSome content.\n")
        source = _write(tmp_path, "source.md", "[Link](test.md#日本語)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "日本語" in _anchors(request, target)

    def test_unicode_heading_with_latin(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "test.md", "## Hello 世界\n\nContent.\n")
        source = _write(tmp_path, "source.md", "[Link](test.md#hello-世界)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "hello-世界" in _anchors(request, target)

    def test_emoji_in_heading(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "test.md", "## Hello 👋 World\n\nContent.\n")
        request, errors = build_request(
            tmp_path, [target], tmp_path / ".markdown-link-check.json", None
        )
        assert errors == []
        anchors = _anchors(request, target)
        assert len(anchors) == 1
        anchor = next(iter(anchors))
        assert "hello" in anchor
        assert "world" in anchor
        source = _write(tmp_path, "source.md", f"[Link](test.md#{anchor})\n")
        _run(tmp_path, capsys, 0, source)

    def test_unicode_filename_validation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "文档.md", "## Content\n\nText here.\n")
        source = _write(tmp_path, "source.md", "[Link](文档.md)\n")
        _run(tmp_path, capsys, 0, source)

    def test_cyrillic_heading(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "test.md", "## Привет мир\n\nContent.\n")
        source = _write(tmp_path, "source.md", "[Link](test.md#привет-мир)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "привет-мир" in _anchors(request, target)

    def test_arabic_heading(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "test.md", "## مرحبا\n\nContent.\n")
        source = _write(tmp_path, "source.md", "[Link](test.md#مرحبا)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "مرحبا" in _anchors(request, target)


class TestSymlinkHandling:
    def test_broken_symlink_handled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "broken_link.md").symlink_to(tmp_path / "nonexistent.md")
        source = _write(tmp_path, "source.md", "[Link](broken_link.md)\n")
        _, report, _ = _run(tmp_path, capsys, 1, source)
        _assert_broken(
            report,
            source,
            "broken_link.md",
            "Target file not found: broken_link.md",
            "[Link](broken_link.md)",
        )
        assert "not found" in report.findings[0].message.lower()

    def test_valid_symlink_followed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "real/target.md", "## Target Section\n\nContent.\n")
        (tmp_path / "linked.md").symlink_to(target)
        source = _write(tmp_path, "source.md", "[Link](linked.md#target-section)\n")
        _run(tmp_path, capsys, 0, source)

    def test_symlink_outside_repo(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        outside = _write(
            tmp_path, "outside/secret.md", "## Secret\n\nSecret content.\n"
        )
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "escape.md").symlink_to(outside)
        source = _write(repo, "source.md", "[Link](escape.md)\n")
        _, report, _ = _run(repo, capsys, 1, source)
        _assert_broken(
            report,
            source,
            "escape.md",
            f"Link points outside repository: {outside.resolve()}",
            "[Link](escape.md)",
        )
        assert "outside" in report.findings[0].message.lower()

    def test_directory_symlink_handled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "real_docs/readme.md", "## Documentation\n\nContent.\n")
        (tmp_path / "docs").symlink_to(tmp_path / "real_docs", target_is_directory=True)
        source = _write(tmp_path, "source.md", "[Link](docs/readme.md#documentation)\n")
        _run(tmp_path, capsys, 0, source)


class TestErrorHandling:
    def test_permission_error_handled(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        restricted = _write(tmp_path, "restricted.md", "## Secret\n\nContent.\n")
        restricted.chmod(0o000)
        try:
            try:
                restricted.read_text(encoding="utf-8")
            except PermissionError:
                pass
            else:
                # Exercise the same permission failure even under a privileged runner.
                original_read = Path.read_text

                def unreadable(path: Path, *args: object, **kwargs: object) -> str:
                    if path.resolve() == restricted.resolve():
                        raise PermissionError(str(path))
                    return original_read(path, encoding="utf-8", errors="replace")

                monkeypatch.setattr(Path, "read_text", unreadable)
            # The old LinkInfo used this anchor although its disk source omitted it.
            source = _write(tmp_path, "source.md", "[Link](restricted.md#secret)\n")
            _, report, _ = _run(tmp_path, capsys, 1, source)
            _assert_broken(
                report,
                source,
                "restricted.md#secret",
                "Anchor 'secret' not found in restricted.md",
                "[Link](restricted.md#secret)",
            )
        finally:
            restricted.chmod(0o644)

    def test_invalid_utf8_content(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = tmp_path / "invalid.md"
        target.write_bytes(b"## Valid\n\nContent with invalid bytes: \xff\xfe\n")
        source = _write(tmp_path, "source.md", "[Link](invalid.md#valid)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert "valid" in _anchors(request, target)

    def test_empty_file_handled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = _write(tmp_path, "empty.md", "")
        source = _write(tmp_path, "source.md", "[Link](empty.md)\n")
        request, _, _ = _run(tmp_path, capsys, 0, source)
        assert len(_anchors(request, target)) == 0

    def test_anchor_in_empty_file_fails(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "empty.md", "")
        source = _write(tmp_path, "source.md", "[Link](empty.md#nonexistent)\n")
        _, report, _ = _run(tmp_path, capsys, 1, source)
        _assert_broken(
            report,
            source,
            "empty.md#nonexistent",
            "Anchor 'nonexistent' not found in empty.md",
            "[Link](empty.md#nonexistent)",
        )
        assert "not found" in report.findings[0].message.lower()

    def test_very_long_filename_handled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        long_name = "a" * 200 + ".md"
        _write(tmp_path, long_name, "## Content\n\nText.\n")
        source = _write(tmp_path, "source.md", f"[Link]({long_name})\n")
        _run(tmp_path, capsys, 0, source)

    def test_special_chars_in_filename(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "file-with_special.chars.md", "## Content\n\nText.\n")
        source = _write(tmp_path, "source.md", "[Link](file-with_special.chars.md)\n")
        _run(tmp_path, capsys, 0, source)


class TestValidationResultBool:
    def test_valid_result_is_truthy(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Preserve the old counters through five files with ten valid links.
        for index in range(5):
            _write(
                tmp_path,
                f"doc{index}.md",
                "[One](#content) [Two](#content)\n## Content\n",
            )
        _, report, output = _run(tmp_path, capsys, 0)
        assert report.overall_status == "PASS"
        assert "5 files, 10 links checked, 0 skipped" in output

    def test_invalid_result_is_falsy(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(
            tmp_path, "test.md", "[Broken](broken.md) [Valid](#content)\n## Content\n"
        )
        for index in range(4):
            _write(
                tmp_path,
                f"doc{index}.md",
                "[One](#content) [Two](#content)\n## Content\n",
            )
        _, report, output = _run(tmp_path, capsys, 1)
        _assert_broken(
            report,
            tmp_path / "test.md",
            "broken.md",
            "Target file not found: broken.md",
            "[Broken](broken.md)",
        )
        assert "5 files, 10 links checked, 1 broken, 0 skipped" in output


class TestLinkInfoMissingReference:
    def test_missing_reference_detection(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = _write(tmp_path, "test.md", "[Some Text][undefined]\n")
        _, report, _ = _run(tmp_path, capsys, 1, source)
        _assert_broken(
            report,
            source,
            "__ONEX_MISSING_REF__:undefined",
            "Reference-style link [undefined] has no definition",
            "[Some Text][undefined]",
            "missing-reference",
        )

    def test_normal_link_not_missing_reference(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "docs/readme.md", "# Documentation\n")
        source = _write(tmp_path, "test.md", "[Link](./docs/readme.md)\n")
        _, report, output = _run(tmp_path, capsys, 0, source)
        assert report.findings == ()
        assert "  OK: [Link](./docs/readme.md)" in output
        assert "has no definition" not in output

    def test_display_link_for_missing_reference(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = _write(tmp_path, "test.md", "[Link Text][myref]\n")
        _, report, output = _run(tmp_path, capsys, 1, source)
        _assert_broken(
            report,
            source,
            "__ONEX_MISSING_REF__:myref",
            "Reference-style link [myref] has no definition",
            "[Link Text][myref]",
            "missing-reference",
        )
        assert "    Link: [Link Text][myref]" in output

    def test_display_link_for_normal_link(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _write(tmp_path, "docs/readme.md", "# Documentation\n")
        source = _write(tmp_path, "test.md", "[Link Text](./docs/readme.md)\n")
        _, _, output = _run(tmp_path, capsys, 0, source)
        assert "  OK: [Link Text](./docs/readme.md)" in output


class TestMarkdownLinkConfigExclusions:
    def test_omni_worktrees_excluded(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        broken = _write(
            tmp_path,
            "omni_worktrees/OMN-1234/somerepo/.venv/lib/README.md",
            "[broken](./nonexistent.md)\n",
        )
        real_doc = _write(tmp_path, "docs/README.md", "# Real doc\n\nContent.\n")
        _write(
            tmp_path,
            ".markdown-link-check.json",
            json.dumps(
                {
                    "excludeFiles": ["omni_worktrees/**", ".venv/**"],
                }
            ),
        )
        request, _, output = _run(tmp_path, capsys, 0)
        found = {Path(file.path) for file in request.files}
        assert real_doc in found
        assert broken not in found
        assert "1 files, 0 links checked" in output

    def test_plugins_venv_excluded(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        broken = _write(
            tmp_path,
            "plugins/onex/lib/.venv/lib/python3.13/Privacy.md",
            "[broken](../README.md)\n[also broken](./C_API.md)\n",
        )
        real_doc = _write(tmp_path, "README.md", "# Repo root\n\nContent.\n")
        _write(
            tmp_path,
            ".markdown-link-check.json",
            json.dumps(
                {
                    "excludeFiles": ["plugins/**/.venv/**", ".venv/**"],
                }
            ),
        )
        request, _, output = _run(tmp_path, capsys, 0)
        found = {Path(file.path) for file in request.files}
        assert real_doc in found
        assert broken not in found
        assert "1 files, 0 links checked" in output

    def test_normal_docs_not_excluded(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        normal_docs = [
            _write(tmp_path, name, "# Doc\n\nContent.\n")
            for name in ["README.md", "docs/INDEX.md", "docs/architecture/OVERVIEW.md"]
        ]
        _write(
            tmp_path,
            ".markdown-link-check.json",
            json.dumps(
                {
                    "excludeFiles": [
                        "omni_worktrees/**",
                        ".venv/**",
                        "plugins/**/.venv/**",
                        "plugins/**/lib/.venv/**",
                    ],
                }
            ),
        )
        request, _, output = _run(tmp_path, capsys, 0)
        found = {Path(file.path) for file in request.files}
        for doc in normal_docs:
            assert doc in found, f"{doc.name} must not be excluded by worktree patterns"
        assert "3 files, 0 links checked" in output
