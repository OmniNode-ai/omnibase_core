# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Oracle-equivalent salted windows, overlap collapse and per-line waiver."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePath
from typing import Final

from omnibase_core.models.nodes.exposed_identifiers_check.model_exposed_identifier_entry import (
    ModelExposedIdentifierEntry,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.denylist_failure import (
    DenylistError,
)

VALIDATOR_ID: Final[str] = "arch-exposed-identifiers"

# Same ticket+reason discipline as the five leaked-literals classes.
ANNOTATION_RE = re.compile(
    r"#\s*onex-allow-exposed-identifier\s+OMN-[0-9]+\s+reason=\"[^\"]+\""
)

# Identifier tokens. Lowercased input, so no A-Z class is needed.
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.\-]*")

# Directories and suffixes that are never source-of-truth for a committed literal.
EXCLUDED_DIR_PARTS = frozenset(
    {
        ".git",
        "dist",
        "build",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "htmlcov",
        ".tox",
        "site-packages",
    }
)
EXCLUDED_SUFFIXES = (
    ".lock",
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".whl",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".mp4",
    ".mov",
)

# A token longer than this is a blob (minified bundle, base64 payload), not an
# identifier a human typed. Windowing it is quadratic and finds nothing real.
MAX_TOKEN_LEN = 512

MAX_BYTES = 8 * 1024 * 1024


class Denylist:
    """Length-indexed digest lookup. Holds no plaintext, by construction."""

    def __init__(self, doc: object) -> None:
        if not isinstance(doc, dict):
            raise DenylistError("denylist must be a JSON object")
        salt = doc.get("salt")
        if not isinstance(salt, str) or not salt:
            raise DenylistError("denylist has no 'salt'")
        entries = doc.get("entries")
        if not isinstance(entries, list) or not entries:
            raise DenylistError("denylist has no 'entries'")

        self.salt = salt
        # Pre-absorb the salt once; every window hash then clones this state
        # instead of re-hashing the salt bytes. The window scan is the hot loop.
        self._salted = hashlib.sha256(salt.encode("utf-8"))
        self.entries: list[ModelExposedIdentifierEntry] = []
        self.by_len: dict[int, dict[str, ModelExposedIdentifierEntry]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise DenylistError("denylist entry must be a JSON object")
            for field in ("id", "kind", "length", "sha256", "ticket"):
                if field not in entry:
                    raise DenylistError(
                        f"denylist entry missing '{field}': {entry.get('id', '?')}"
                    )
            length = entry["length"]
            if not isinstance(length, int) or length < 4:
                raise DenylistError(
                    f"entry {entry['id']}: 'length' must be an int >= 4"
                )
            digest = entry["sha256"]
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise DenylistError(
                    f"entry {entry['id']}: 'sha256' must be 64 lowercase hex chars"
                )
            # A plaintext field would defeat the whole design; refuse to load one.
            for forbidden in ("value", "literal", "plaintext"):
                if forbidden in entry:
                    raise DenylistError(
                        f"entry {entry['id']}: '{forbidden}' is forbidden -- this denylist "
                        f"ships in public repos and must never carry plaintext"
                    )
            parsed = ModelExposedIdentifierEntry(
                label=str(entry["id"]),
                kind=str(entry["kind"]),
                length=length,
                sha256=digest,
                ticket=str(entry["ticket"]),
            )
            self.entries.append(parsed)
            self.by_len.setdefault(length, {})[digest] = parsed

        self.lengths = sorted(self.by_len)
        self.min_len = self.lengths[0]

    @classmethod
    def from_json(cls, source: str) -> Denylist:
        """Validate the caller's inline JSON; this matcher performs no reads."""
        try:
            document: object = json.loads(source)
        except json.JSONDecodeError as exc:
            raise DenylistError(f"denylist is not valid JSON: {exc}") from exc
        return cls(document)

    def digest(self, value: str) -> str:
        hasher = self._salted.copy()
        hasher.update(value.encode("utf-8"))
        return hasher.hexdigest()

    def scan_line(
        self, line: str
    ) -> list[tuple[int, int, ModelExposedIdentifierEntry]]:
        """Return (col, length, entry) for each hit, longest-match-wins on overlap."""
        low = line.lower()
        raw: list[tuple[int, int, ModelExposedIdentifierEntry]] = []
        for tok in TOKEN_RE.finditer(low):
            text = tok.group(0)
            span = len(text)
            if span < self.min_len or span > MAX_TOKEN_LEN:
                continue
            base = tok.start()
            for length in self.lengths:
                if span < length:
                    break  # lengths ascend; every later one is longer still
                bucket = self.by_len[length]
                for offset in range(span - length + 1):
                    entry = bucket.get(self.digest(text[offset : offset + length]))
                    if entry is not None:
                        raw.append((base + offset, length, entry))
        if len(raw) < 2:
            return raw
        # Collapse overlaps: a full UUID also matches its own prefix entry.
        raw.sort(key=lambda hit: (hit[0], -hit[1]))
        kept: list[tuple[int, int, ModelExposedIdentifierEntry]] = []
        covered_to = -1
        for col, length, entry in raw:
            if col < covered_to:
                continue
            kept.append((col, length, entry))
            covered_to = col + length
        return kept


def is_scannable_source(path: str, source: str) -> bool:
    """Apply the oracle's pure path exclusions and first-8192-byte binary check."""
    label = PurePath(path)
    return (
        not EXCLUDED_DIR_PARTS.intersection(label.parts)
        and not label.name.lower().endswith(EXCLUDED_SUFFIXES)
        and b"\0" not in source.encode("utf-8", errors="surrogateescape")[:8192]
    )
