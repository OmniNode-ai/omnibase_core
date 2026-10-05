# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the markdown-link matcher helpers.

Ported unchanged from ``tests/unit/scripts/test_validate_markdown_links.py`` (the
tests of ``omnibase_core.scripts.validate_markdown_links`` that exercise the pure
helpers), now run against the same helpers in
``node_markdown_links_check_compute.matcher_markdown_links`` (OMN-20565).
"""

from __future__ import annotations

import pytest

from omnibase_core.nodes.node_markdown_links_check_compute.matcher_markdown_links import (
    _heading_to_anchor,
    extract_headings_as_anchors,
    is_external_link,
    is_http_link,
    normalize_url_for_validation,
)

pytestmark = pytest.mark.unit


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
        """Inline code backticks should be stripped but code text kept (GitHub-compatible)."""
        # GitHub keeps text inside backticks, just removes backtick delimiters
        assert _heading_to_anchor("Using `code` in heading") == "using-code-in-heading"

    def test_removes_images(self) -> None:
        """Images should be removed from headings."""
        assert _heading_to_anchor("![alt](image.png) Title") == "title"

    def test_keeps_link_text(self) -> None:
        """Link text should be kept, URL removed."""
        assert _heading_to_anchor("[Link Text](http://example.com)") == "link-text"

    def test_preserves_consecutive_hyphens(self) -> None:
        """Consecutive hyphens should be preserved (GitHub-compatible)."""
        assert _heading_to_anchor("A  B") == "a--b"
        assert _heading_to_anchor("A - B") == "a---b"

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
