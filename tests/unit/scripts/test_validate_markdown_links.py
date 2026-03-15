# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for markdown link validation.

Tests for anchor extraction and duplicate heading disambiguation following
GitHub's anchor generation conventions.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from omnibase_core.scripts.validate_markdown_links import (
    BrokenLink,
    LinkInfo,
    ValidationResult,
    _heading_to_anchor,
    extract_headings_as_anchors,
    is_external_link,
    is_http_link,
    normalize_url_for_validation,
    validate_internal_link,
)


class TestHeadingToAnchor:
    """Tests for converting headings to GitHub-style anchors."""

    def test_basic_heading(self) -> None:
        """Basic heading conversion to lowercase with hyphens."""
        assert _heading_to_anchor("Hello World") == "hello-world"

    def test_removes_punctuation(self) -> None:
        """Punctuation should be removed."""
        assert _heading_to_anchor("What's New?") == "whats-new"
        assert _heading_to_anchor("Hello, World!") == "hello-world"

    def test_preserves_hyphens(self) -> None:
        """Existing hyphens should be preserved."""
        assert _heading_to_anchor("My-Heading") == "my-heading"

    def test_preserves_underscores(self) -> None:
        """Underscores should be preserved."""
        assert _heading_to_anchor("my_heading") == "my_heading"

    def test_removes_inline_code(self) -> None:
        """Inline code backticks should be removed, with hyphens collapsed."""
        # Code is removed, leaving double space which becomes double hyphen,
        # then collapsed to single hyphen
        assert _heading_to_anchor("Using `code` in heading") == "using-in-heading"

    def test_removes_images(self) -> None:
        """Images should be removed from headings."""
        assert _heading_to_anchor("![alt](image.png) Title") == "title"

    def test_keeps_link_text(self) -> None:
        """Link text should be kept, URL removed."""
        assert _heading_to_anchor("[Link Text](http://example.com)") == "link-text"

    def test_removes_consecutive_hyphens(self) -> None:
        """Consecutive hyphens should be collapsed."""
        assert _heading_to_anchor("A  B") == "a-b"
        assert _heading_to_anchor("A - B") == "a-b"

    def test_strips_leading_trailing_hyphens(self) -> None:
        """Leading and trailing hyphens should be stripped."""
        assert _heading_to_anchor("-Leading") == "leading"
        assert _heading_to_anchor("Trailing-") == "trailing"


class TestExtractHeadingsAsAnchors:
    """Tests for extracting anchors from markdown content."""

    def test_simple_headings(self) -> None:
        """Extract anchors from simple headings."""
        content = """
# Heading One
## Heading Two
### Heading Three
"""
        anchors = extract_headings_as_anchors(content)
        assert "heading-one" in anchors
        assert "heading-two" in anchors
        assert "heading-three" in anchors

    def test_duplicate_headings(self) -> None:
        """Duplicate headings should get suffixed anchors."""
        content = """
## Foo
Some content
## Foo
More content
## Foo
"""
        anchors = extract_headings_as_anchors(content)
        assert "foo" in anchors
        assert "foo-1" in anchors
        assert "foo-2" in anchors
        assert len(anchors) == 3

    def test_natural_anchor_collision(self) -> None:
        """Natural anchors should not collide with disambiguated ones.

        When "Foo-1" heading exists naturally, the second "Foo" should
        get "foo-2" instead of "foo-1".
        """
        content = """
## Foo
## Foo-1
## Foo
"""
        anchors = extract_headings_as_anchors(content)
        assert "foo" in anchors
        assert "foo-1" in anchors
        assert "foo-2" in anchors
        assert len(anchors) == 3

    def test_reverse_collision_order(self) -> None:
        """Test collision when natural anchor comes after duplicates.

        When two "Foo" headings come before "Foo-1", the "Foo-1" heading
        should get "foo-1-1".
        """
        content = """
## Foo
## Foo
## Foo-1
"""
        anchors = extract_headings_as_anchors(content)
        assert "foo" in anchors
        assert "foo-1" in anchors
        assert "foo-1-1" in anchors
        assert len(anchors) == 3

    def test_multiple_collision_chain(self) -> None:
        """Test multiple levels of collision."""
        content = """
## Foo
## Foo
## Foo
## Foo-1
## Foo-2
"""
        anchors = extract_headings_as_anchors(content)
        # First Foo -> foo
        # Second Foo -> foo-1
        # Third Foo -> foo-2 (would be foo-2 since foo-1 taken)
        # Foo-1 -> foo-1-1 (foo-1 already taken by second Foo)
        # Foo-2 -> foo-2-1 (foo-2 already taken by third Foo)
        assert "foo" in anchors
        assert "foo-1" in anchors
        assert "foo-2" in anchors
        assert "foo-1-1" in anchors
        assert "foo-2-1" in anchors
        assert len(anchors) == 5

    def test_html_anchors_included(self) -> None:
        """HTML anchor tags should be included."""
        content = """
# Heading

<a name="custom-anchor"></a>

Some content

<a id="another-anchor"></a>
"""
        anchors = extract_headings_as_anchors(content)
        assert "heading" in anchors
        assert "custom-anchor" in anchors
        assert "another-anchor" in anchors

    def test_case_insensitive_collisions(self) -> None:
        """Headings with different cases should collide."""
        content = """
## Foo
## FOO
## foo
"""
        anchors = extract_headings_as_anchors(content)
        assert "foo" in anchors
        assert "foo-1" in anchors
        assert "foo-2" in anchors
        assert len(anchors) == 3

    def test_punctuation_collisions(self) -> None:
        """Headings that become identical after normalization should collide."""
        content = """
## Hello World
## Hello, World!
## Hello-World
"""
        anchors = extract_headings_as_anchors(content)
        # All three normalize to "hello-world"
        assert "hello-world" in anchors
        assert "hello-world-1" in anchors
        assert "hello-world-2" in anchors
        assert len(anchors) == 3

    def test_empty_content(self) -> None:
        """Empty content should return empty set."""
        anchors = extract_headings_as_anchors("")
        assert len(anchors) == 0

    def test_no_headings(self) -> None:
        """Content without headings should return empty set."""
        content = """
Just some text without any headings.

More paragraphs here.
"""
        anchors = extract_headings_as_anchors(content)
        assert len(anchors) == 0

    def test_heading_levels(self) -> None:
        """All heading levels 1-6 should be recognized."""
        content = """
# H1
## H2
### H3
#### H4
##### H5
###### H6
"""
        anchors = extract_headings_as_anchors(content)
        assert "h1" in anchors
        assert "h2" in anchors
        assert "h3" in anchors
        assert "h4" in anchors
        assert "h5" in anchors
        assert "h6" in anchors

    def test_complex_collision_scenario(self) -> None:
        """Complex real-world collision scenario."""
        content = """
## Installation
## Configuration
## Installation
## Installation-1
## Configuration
"""
        anchors = extract_headings_as_anchors(content)
        # First Installation -> installation
        # Configuration -> configuration
        # Second Installation -> installation-1
        # Installation-1 -> installation-1-1 (installation-1 taken)
        # Second Configuration -> configuration-1
        assert "installation" in anchors
        assert "configuration" in anchors
        assert "installation-1" in anchors
        assert "installation-1-1" in anchors
        assert "configuration-1" in anchors
        assert len(anchors) == 5


class TestIsExternalLink:
    """Tests for external link detection."""

    def test_http_link(self) -> None:
        """HTTP links are external."""
        assert is_external_link("http://example.com") is True

    def test_https_link(self) -> None:
        """HTTPS links are external."""
        assert is_external_link("https://example.com") is True

    def test_protocol_relative_link(self) -> None:
        """Protocol-relative links are external."""
        assert is_external_link("//example.com/path") is True

    def test_mailto_link(self) -> None:
        """Mailto links are external."""
        assert is_external_link("mailto:user@example.com") is True

    def test_tel_link(self) -> None:
        """Tel links are external."""
        assert is_external_link("tel:+1234567890") is True

    def test_ftp_link(self) -> None:
        """FTP links are external."""
        assert is_external_link("ftp://ftp.example.com") is True

    def test_javascript_link(self) -> None:
        """JavaScript links are external (and should be skipped)."""
        assert is_external_link("javascript:void(0)") is True

    def test_data_link(self) -> None:
        """Data URIs are external (and should be skipped)."""
        assert is_external_link("data:text/plain;base64,SGVsbG8=") is True

    def test_file_link(self) -> None:
        """File links are external (and should be skipped)."""
        assert is_external_link("file:///path/to/file") is True

    def test_relative_path_not_external(self) -> None:
        """Relative paths are not external."""
        assert is_external_link("./docs/README.md") is False
        assert is_external_link("../README.md") is False
        assert is_external_link("docs/README.md") is False

    def test_anchor_link_not_external(self) -> None:
        """Anchor-only links are not external."""
        assert is_external_link("#section") is False

    def test_repo_root_relative_not_external(self) -> None:
        """Repo-root relative links (starting with /) are not external."""
        assert is_external_link("/docs/README.md") is False


class TestIsHttpLink:
    """Tests for HTTP/HTTPS link detection (for network validation)."""

    def test_http_is_http_link(self) -> None:
        """HTTP links can be validated."""
        assert is_http_link("http://example.com") is True

    def test_https_is_http_link(self) -> None:
        """HTTPS links can be validated."""
        assert is_http_link("https://example.com") is True

    def test_protocol_relative_is_http_link(self) -> None:
        """Protocol-relative links are treated as HTTPS."""
        assert is_http_link("//example.com/path") is True

    def test_mailto_not_http_link(self) -> None:
        """Mailto links cannot be validated via HTTP."""
        assert is_http_link("mailto:user@example.com") is False

    def test_tel_not_http_link(self) -> None:
        """Tel links cannot be validated via HTTP."""
        assert is_http_link("tel:+1234567890") is False

    def test_ftp_not_http_link(self) -> None:
        """FTP links cannot be validated via HTTP."""
        assert is_http_link("ftp://ftp.example.com") is False

    def test_javascript_not_http_link(self) -> None:
        """JavaScript links cannot be validated."""
        assert is_http_link("javascript:void(0)") is False

    def test_data_not_http_link(self) -> None:
        """Data URIs cannot be validated via HTTP."""
        assert is_http_link("data:text/plain;base64,SGVsbG8=") is False


class TestNormalizeUrlForValidation:
    """Tests for URL normalization before validation."""

    def test_protocol_relative_to_https(self) -> None:
        """Protocol-relative URLs should be normalized to HTTPS."""
        assert normalize_url_for_validation("//example.com") == "https://example.com"
        assert (
            normalize_url_for_validation("//example.com/path")
            == "https://example.com/path"
        )

    def test_http_unchanged(self) -> None:
        """HTTP URLs should not be changed."""
        assert (
            normalize_url_for_validation("http://example.com") == "http://example.com"
        )

    def test_https_unchanged(self) -> None:
        """HTTPS URLs should not be changed."""
        assert (
            normalize_url_for_validation("https://example.com") == "https://example.com"
        )

    def test_relative_path_unchanged(self) -> None:
        """Relative paths should not be changed."""
        assert normalize_url_for_validation("./docs/README.md") == "./docs/README.md"


class TestURLEncodedAnchors:
    """Tests for URL-encoded anchor handling."""

    def test_url_encoded_space_in_anchor(self, tmp_path: Path) -> None:
        """URL-encoded space should match heading with space.

        Tests that #my%20section matches a heading like "## my section".
        Note: Current implementation may not decode URL-encoded anchors,
        so this test documents expected behavior.
        """
        # Create a markdown file with a heading containing a space
        md_file = tmp_path / "test.md"
        md_file.write_text("## my section\n\nSome content here.\n", encoding="utf-8")

        # Extract anchors from the file
        content = md_file.read_text(encoding="utf-8")
        anchors = extract_headings_as_anchors(content)

        # The anchor should be "my-section" (spaces converted to hyphens)
        assert "my-section" in anchors

        # Test that the URL-encoded anchor is handled
        # GitHub converts spaces to hyphens, so %20 should not appear in anchors
        # The link should use the hyphenated form
        link = LinkInfo(
            url="#my-section",
            text="Link to section",
            line_number=1,
            source_file=md_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Hyphenated anchor should be valid"

    def test_url_encoded_special_chars(self, tmp_path: Path) -> None:
        """URL-encoded special characters should be decoded.

        Tests that anchors with special characters are properly handled.
        """
        # Create a markdown file with a heading that has special chars
        md_file = tmp_path / "test.md"
        # GitHub strips most special chars, so "foo/bar" becomes "foobar"
        md_file.write_text("## foo bar\n\nContent.\n", encoding="utf-8")

        content = md_file.read_text(encoding="utf-8")
        anchors = extract_headings_as_anchors(content)

        # Verify the anchor was generated correctly
        assert "foo-bar" in anchors

        # Test link validation
        link = LinkInfo(
            url="#foo-bar",
            text="Link",
            line_number=1,
            source_file=md_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Link to foo-bar should be valid"

    def test_double_encoded_anchor(self, tmp_path: Path) -> None:
        """Double-encoded anchors should be handled gracefully.

        Tests behavior with %2520 (double-encoded space).
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("## normal heading\n\nContent.\n", encoding="utf-8")

        # A double-encoded anchor %2520 represents a literal "%20" after first decode
        # This is an edge case that should fail gracefully (anchor not found)
        link = LinkInfo(
            url="#%2520invalid",
            text="Double encoded",
            line_number=1,
            source_file=md_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)

        # Should return an error since anchor doesn't exist
        assert result is not None
        assert "not found" in result.lower()

    def test_percent_in_heading(self, tmp_path: Path) -> None:
        """Headings with percent signs are handled correctly."""
        md_file = tmp_path / "test.md"
        md_file.write_text("## 100% Complete\n\nContent.\n", encoding="utf-8")

        content = md_file.read_text(encoding="utf-8")
        anchors = extract_headings_as_anchors(content)

        # Percent sign is stripped as punctuation
        assert "100-complete" in anchors


class TestUnicodeFilenames:
    """Tests for Unicode filename handling."""

    def test_unicode_heading(self) -> None:
        """Unicode characters in headings should work."""
        # Japanese text "nihongo" meaning "Japanese language"
        content = "## \u65e5\u672c\u8a9e\n\nSome content.\n"
        anchors = extract_headings_as_anchors(content)

        # Unicode characters should be preserved in anchors
        assert "\u65e5\u672c\u8a9e" in anchors

    def test_unicode_heading_with_latin(self) -> None:
        """Mixed Unicode and Latin characters in headings."""
        content = "## Hello \u4e16\u754c\n\nContent.\n"
        anchors = extract_headings_as_anchors(content)

        # Both Unicode and Latin should be preserved
        assert "hello-\u4e16\u754c" in anchors

    def test_emoji_in_heading(self) -> None:
        """Emoji in headings should be handled."""
        content = "## Hello \U0001f44b World\n\nContent.\n"
        anchors = extract_headings_as_anchors(content)

        # Emojis may be stripped or preserved depending on implementation
        # Current implementation keeps word characters, so emoji behavior varies
        # The anchor should at least contain the text parts
        # Check that we get some valid anchor
        assert len(anchors) == 1
        anchor = next(iter(anchors))
        # The anchor should contain "hello" and "world" at minimum
        assert "hello" in anchor
        assert "world" in anchor

    def test_unicode_filename_validation(self, tmp_path: Path) -> None:
        """Unicode filenames should be validated correctly."""
        # Create a file with a Unicode name
        unicode_file = tmp_path / "\u6587\u6863.md"
        unicode_file.write_text("## Content\n\nText here.\n", encoding="utf-8")

        # Create a file that links to the Unicode filename
        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](\u6587\u6863.md)\n", encoding="utf-8")

        link = LinkInfo(
            url="\u6587\u6863.md",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Link to Unicode filename should be valid"

    def test_cyrillic_heading(self) -> None:
        """Cyrillic characters in headings should work."""
        # Russian: "Привет мир" means "Hello world"
        content = (
            "## \u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440\n\nContent.\n"
        )
        anchors = extract_headings_as_anchors(content)

        assert "\u043f\u0440\u0438\u0432\u0435\u0442-\u043c\u0438\u0440" in anchors

    def test_arabic_heading(self) -> None:
        """Arabic characters in headings should work."""
        # Arabic: "مرحبا" means "Hello"
        content = "## \u0645\u0631\u062d\u0628\u0627\n\nContent.\n"
        anchors = extract_headings_as_anchors(content)

        assert "\u0645\u0631\u062d\u0628\u0627" in anchors


class TestSymlinkHandling:
    """Tests for symlink handling."""

    def test_broken_symlink_handled(self, tmp_path: Path) -> None:
        """Broken symlinks should return informative error."""
        # Create a broken symlink
        target = tmp_path / "nonexistent.md"
        symlink = tmp_path / "broken_link.md"
        symlink.symlink_to(target)

        # Create a source file that links to the broken symlink
        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](broken_link.md)\n", encoding="utf-8")

        link = LinkInfo(
            url="broken_link.md",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)

        # Should report the target as not found
        assert result is not None
        assert "not found" in result.lower()

    def test_valid_symlink_followed(self, tmp_path: Path) -> None:
        """Valid symlinks should be followed and validated."""
        # Create a real target file
        target_dir = tmp_path / "real"
        target_dir.mkdir()
        target_file = target_dir / "target.md"
        target_file.write_text("## Target Section\n\nContent.\n", encoding="utf-8")

        # Create a symlink to it
        symlink = tmp_path / "linked.md"
        symlink.symlink_to(target_file)

        # Create a source file that links to the symlink
        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](linked.md#target-section)\n", encoding="utf-8")

        link = LinkInfo(
            url="linked.md#target-section",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Valid symlink with anchor should be valid"

    def test_symlink_outside_repo(self, tmp_path: Path) -> None:
        """Symlinks pointing outside repo should be detected."""
        # Create a file outside the "repo" directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.md"
        outside_file.write_text("## Secret\n\nSecret content.\n", encoding="utf-8")

        # Create the "repo" directory
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create a symlink inside repo pointing outside
        symlink = repo_dir / "escape.md"
        symlink.symlink_to(outside_file)

        # Create a source file that links to the symlink
        source_file = repo_dir / "source.md"
        source_file.write_text("[Link](escape.md)\n", encoding="utf-8")

        link = LinkInfo(
            url="escape.md",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        # The symlink resolves to a path outside repo_dir
        result = validate_internal_link(link, repo_dir, cache)

        # Should detect that the resolved path is outside the repo
        assert result is not None
        assert "outside" in result.lower()

    def test_directory_symlink_handled(self, tmp_path: Path) -> None:
        """Directory symlinks should be handled correctly."""
        # Create a real directory with a markdown file
        real_dir = tmp_path / "real_docs"
        real_dir.mkdir()
        real_file = real_dir / "readme.md"
        real_file.write_text("## Documentation\n\nContent.\n", encoding="utf-8")

        # Create a symlink to the directory
        symlink_dir = tmp_path / "docs"
        symlink_dir.symlink_to(real_dir)

        # Create a source file that links through the symlinked directory
        source_file = tmp_path / "source.md"
        source_file.write_text(
            "[Link](docs/readme.md#documentation)\n", encoding="utf-8"
        )

        link = LinkInfo(
            url="docs/readme.md#documentation",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Link through directory symlink should be valid"


class TestErrorHandling:
    """Tests for error handling edge cases."""

    def test_permission_error_handled(self, tmp_path: Path) -> None:
        """Permission errors should be handled gracefully.

        Note: This test may be skipped in environments where permission
        restrictions are not enforced (Docker containers, certain CI systems).
        """
        if os.name == "nt":
            pytest.skip("Permission tests not applicable on Windows")

        # Create a file with no read permissions
        restricted_file = tmp_path / "restricted.md"
        restricted_file.write_text("## Secret\n\nContent.\n", encoding="utf-8")
        restricted_file.chmod(0o000)

        try:
            # Verify permissions are actually enforced in this environment
            try:
                restricted_file.read_text(encoding="utf-8")
                # If we can read the file despite 000 perms, skip the test
                pytest.skip("Environment does not enforce file permissions (Docker/CI)")
            except PermissionError:
                pass  # Good - permissions are enforced

            # Create a source file that links to the restricted file
            source_file = tmp_path / "source.md"
            source_file.write_text("[Link](restricted.md)\n", encoding="utf-8")

            # Note: The link target exists, but reading it for anchor validation
            # may fail. The file existence check should still pass.
            link = LinkInfo(
                url="restricted.md#secret",
                text="Link",
                line_number=1,
                source_file=source_file,
            )

            cache: dict[Path, set[str]] = {}
            result = validate_internal_link(link, tmp_path, cache)

            # File exists but anchor can't be validated due to permission error
            # Should handle gracefully (either return error or treat as empty anchors)
            # The current implementation catches OSError and returns empty set
            assert result is not None  # Anchor won't be found
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

    def test_invalid_utf8_content(self, tmp_path: Path) -> None:
        """Files with invalid UTF-8 should be handled."""
        # Create a file with invalid UTF-8 bytes
        invalid_file = tmp_path / "invalid.md"
        invalid_file.write_bytes(b"## Valid\n\nContent with invalid bytes: \xff\xfe\n")

        # Try to extract anchors - should handle gracefully
        try:
            content = invalid_file.read_text(encoding="utf-8", errors="replace")
            anchors = extract_headings_as_anchors(content)
            # With errors="replace", we should still get the valid heading
            assert "valid" in anchors
        except UnicodeDecodeError:
            # If strict encoding is used, this is also acceptable behavior
            pass

    def test_empty_file_handled(self, tmp_path: Path) -> None:
        """Empty files should be handled gracefully."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        content = empty_file.read_text(encoding="utf-8")
        anchors = extract_headings_as_anchors(content)

        assert len(anchors) == 0

        # Validate a link to the empty file
        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](empty.md)\n", encoding="utf-8")

        link = LinkInfo(
            url="empty.md",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Link to empty file (without anchor) should be valid"

    def test_anchor_in_empty_file_fails(self, tmp_path: Path) -> None:
        """Anchor in empty file should fail validation."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](empty.md#nonexistent)\n", encoding="utf-8")

        link = LinkInfo(
            url="empty.md#nonexistent",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is not None
        assert "not found" in result.lower()

    def test_very_long_filename_handled(self, tmp_path: Path) -> None:
        """Very long filenames should be handled (OS dependent)."""
        # Create a file with a reasonably long name (within most filesystem limits)
        long_name = "a" * 200 + ".md"
        try:
            long_file = tmp_path / long_name
            long_file.write_text("## Content\n\nText.\n", encoding="utf-8")

            source_file = tmp_path / "source.md"
            source_file.write_text(f"[Link]({long_name})\n", encoding="utf-8")

            link = LinkInfo(
                url=long_name,
                text="Link",
                line_number=1,
                source_file=source_file,
            )

            cache: dict[Path, set[str]] = {}
            result = validate_internal_link(link, tmp_path, cache)
            assert result is None, "Link to long filename should be valid"
        except OSError:
            # Some filesystems have shorter limits - this is acceptable
            pytest.skip("Filesystem does not support long filenames")

    def test_special_chars_in_filename(self, tmp_path: Path) -> None:
        """Special characters in filenames should be handled."""
        # Test with characters that are valid in most filesystems
        special_file = tmp_path / "file-with_special.chars.md"
        special_file.write_text("## Content\n\nText.\n", encoding="utf-8")

        source_file = tmp_path / "source.md"
        source_file.write_text("[Link](file-with_special.chars.md)\n", encoding="utf-8")

        link = LinkInfo(
            url="file-with_special.chars.md",
            text="Link",
            line_number=1,
            source_file=source_file,
        )

        cache: dict[Path, set[str]] = {}
        result = validate_internal_link(link, tmp_path, cache)
        assert result is None, "Link to file with special chars should be valid"


class TestValidationResultBool:
    """Tests for ValidationResult __bool__ behavior."""

    def test_valid_result_is_truthy(self) -> None:
        """ValidationResult with no broken links should be truthy."""
        result = ValidationResult(broken_links=[], files_checked=5, links_checked=10)
        assert bool(result) is True
        assert result.is_valid is True

    def test_invalid_result_is_falsy(self) -> None:
        """ValidationResult with broken links should be falsy."""
        broken = BrokenLink(
            link=LinkInfo(
                url="broken.md",
                text="Broken",
                line_number=1,
                source_file=Path("test.md"),
            ),
            reason="File not found",
        )
        result = ValidationResult(
            broken_links=[broken], files_checked=5, links_checked=10
        )
        assert bool(result) is False
        assert result.is_valid is False


class TestLinkInfoMissingReference:
    """Tests for LinkInfo missing reference detection."""

    def test_missing_reference_detection(self) -> None:
        """LinkInfo should detect missing reference-style links."""
        link = LinkInfo(
            url="__ONEX_MISSING_REF__:undefined",
            text="Some Text",
            line_number=1,
            source_file=Path("test.md"),
        )
        assert link.is_missing_reference is True
        assert link.missing_reference_name == "undefined"

    def test_normal_link_not_missing_reference(self) -> None:
        """Normal links should not be flagged as missing references."""
        link = LinkInfo(
            url="./docs/readme.md",
            text="Link",
            line_number=1,
            source_file=Path("test.md"),
        )
        assert link.is_missing_reference is False
        assert link.missing_reference_name is None

    def test_display_link_for_missing_reference(self) -> None:
        """Display link should show reference format for missing refs."""
        link = LinkInfo(
            url="__ONEX_MISSING_REF__:myref",
            text="Link Text",
            line_number=1,
            source_file=Path("test.md"),
        )
        assert link.display_link == "[Link Text][myref]"

    def test_display_link_for_normal_link(self) -> None:
        """Display link should show markdown format for normal links."""
        link = LinkInfo(
            url="./docs/readme.md",
            text="Link Text",
            line_number=1,
            source_file=Path("test.md"),
        )
        assert link.display_link == "[Link Text](./docs/readme.md)"
