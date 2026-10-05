# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Core markdown extraction and anchor generation, without I/O."""

import re
from collections.abc import Iterator

from omnibase_core.models.nodes.markdown_links_check.model_markdown_link import (
    ModelMarkdownLink,
)

MARKDOWN_LINK_PATTERN = re.compile(
    r'\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)'
)

# Regex to match reference-style links: [text][ref] with [ref]: url
MARKDOWN_REF_LINK_PATTERN = re.compile(r"\[(?P<text>[^\]]+)\]\[(?P<ref>[^\]]*)\]")
MARKDOWN_REF_DEFINITION_PATTERN = re.compile(
    r"^\[(?P<ref>[^\]]+)\]:\s*(?P<url>\S+)", re.MULTILINE
)

# Regex to match HTML anchor tags for heading extraction
HTML_ANCHOR_PATTERN = re.compile(r'<a\s+(?:name|id)=["\']([^"\']+)["\']', re.IGNORECASE)


MISSING_REF_SENTINEL = "__ONEX_MISSING_REF__"


def _remove_code_blocks(content: str) -> str:
    """Remove fenced code blocks from content to avoid false positives.

    Replaces fenced code blocks (``` ... ```) with empty lines to preserve
    line number alignment while excluding code from link extraction.
    """
    result_lines = []
    in_code_block = False
    code_fence_pattern = re.compile(r"^\s*```")

    for line in content.split("\n"):
        if code_fence_pattern.match(line):
            in_code_block = not in_code_block
            result_lines.append("")  # Preserve line count
        elif in_code_block:
            result_lines.append("")  # Preserve line count
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def _remove_inline_code(line: str) -> str:
    """Remove inline code spans from a line to avoid false positives.

    Inline code (backticks) can contain patterns that look like reference-style
    links, e.g., `dict["key"]["value"]` would match as [key][value].
    """
    return re.sub(r"`[^`]+`", "", line)


def extract_links_from_markdown(
    content: str, source_file: str
) -> Iterator[ModelMarkdownLink]:
    """Extract all links from markdown content."""
    # Build reference definitions map (before removing code blocks)
    ref_definitions: dict[str, str] = {}
    for match in MARKDOWN_REF_DEFINITION_PATTERN.finditer(content):
        ref_definitions[match.group("ref").lower()] = match.group("url")

    # Remove fenced code blocks to avoid false positives
    content_without_code = _remove_code_blocks(content)
    lines = content_without_code.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Remove inline code to avoid matching dict["key"]["value"] as links
        line_without_inline_code = _remove_inline_code(line)

        # Extract inline links [text](url)
        for match in MARKDOWN_LINK_PATTERN.finditer(line_without_inline_code):
            yield ModelMarkdownLink(
                url=match.group("url"),
                text=match.group("text"),
                line_number=line_num,
                source_file=source_file,
            )

        # Extract reference-style links [text][ref]
        for match in MARKDOWN_REF_LINK_PATTERN.finditer(line_without_inline_code):
            ref = match.group("ref") or match.group("text")
            url = ref_definitions.get(ref.lower())
            if url:
                yield ModelMarkdownLink(
                    url=url,
                    text=match.group("text"),
                    line_number=line_num,
                    source_file=source_file,
                )
            else:
                # Yield sentinel for undefined reference - will be caught during validation
                yield ModelMarkdownLink(
                    url=f"{MISSING_REF_SENTINEL}:{ref}",
                    text=match.group("text"),
                    line_number=line_num,
                    source_file=source_file,
                )


def extract_headings_as_anchors(content: str) -> set[str]:
    """Extract all heading anchors from markdown content.

    GitHub-style anchor generation:
    - Lowercase
    - Replace spaces with hyphens
    - Remove punctuation except hyphens
    - Handle duplicates with -1, -2 suffix for disambiguation

    Disambiguation handles collision between:
    - Duplicate headings (e.g., two "## Foo" headings)
    - Natural anchors that match disambiguated forms (e.g., "## Foo-1" colliding
      with second "## Foo" which would normally become foo-1)

    Examples:
        ["Foo", "Foo"] -> {"foo", "foo-1"}
        ["Foo", "Foo-1", "Foo"] -> {"foo", "foo-1", "foo-2"}
    """
    anchors: set[str] = set()
    anchor_counts: dict[str, int] = {}

    # Match ATX headings: # Heading, ## Heading, etc.
    heading_pattern = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
    for match in heading_pattern.finditer(content):
        heading_text = match.group(1).strip()
        base_anchor = _heading_to_anchor(heading_text)

        # Handle duplicate headings with -1, -2 suffixes (GitHub style)
        # Check against full anchors set to handle collisions with natural anchors
        if base_anchor in anchors:
            # Need to disambiguate - find first available suffix
            count = anchor_counts.get(base_anchor, 0)
            suffix = count + 1
            unique_anchor = f"{base_anchor}-{suffix}"
            # Keep incrementing until we find an anchor not already used
            # This handles cases like "Foo", "Foo-1", "Foo" where the second
            # "Foo" can't use "foo-1" because it's already taken by "Foo-1"
            while unique_anchor in anchors:
                suffix += 1
                unique_anchor = f"{base_anchor}-{suffix}"
            anchor_counts[base_anchor] = suffix
        else:
            unique_anchor = base_anchor
            anchor_counts[base_anchor] = 0

        anchors.add(unique_anchor)

    # Match HTML anchors: <a name="anchor"> or <a id="anchor">
    for match in HTML_ANCHOR_PATTERN.finditer(content):
        anchors.add(match.group(1))

    return anchors


def _heading_to_anchor(heading: str) -> str:
    """Convert a heading to its GitHub-style anchor."""
    # Strip backtick delimiters but keep code text (GitHub-compatible)
    anchor = heading.replace("`", "")
    # Remove images
    anchor = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", anchor)
    # Remove links but keep text
    anchor = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", anchor)
    # Lowercase
    anchor = anchor.lower()
    # Replace spaces with hyphens
    anchor = anchor.replace(" ", "-")
    # Remove punctuation except hyphens and underscores (GitHub-compatible)
    anchor = re.sub(r"[^\w\-]", "", anchor)
    # Strip leading/trailing hyphens
    anchor = anchor.strip("-")
    return anchor


def is_external_link(url: str) -> bool:
    """Check if a URL is an external link.

    Recognizes:
    - HTTP/HTTPS links (http://, https://)
    - Protocol-relative URLs (//)
    - Non-HTTP schemes (mailto:, tel:, ftp:, javascript:, data:, file:)
    """
    return url.startswith(
        (
            "http://",
            "https://",
            "//",
            "mailto:",
            "tel:",
            "ftp://",
            "javascript:",
            "data:",
            "file://",
        )
    )


def is_http_link(url: str) -> bool:
    """Check if a URL is an HTTP/HTTPS link (can be validated via network).

    Returns True for:
    - http:// and https:// links
    - Protocol-relative URLs (//) which are treated as https://

    Returns False for:
    - mailto:, tel:, javascript:, ftp:, data:, file:, etc.
    - Internal/relative links
    """
    return url.startswith(("http://", "https://", "//"))


def normalize_url_for_validation(url: str) -> str:
    """Normalize a URL for external validation.

    - Protocol-relative URLs (//example.com) are normalized to https://example.com
    - Other URLs are returned unchanged
    """
    if url.startswith("//"):
        return "https:" + url
    return url
