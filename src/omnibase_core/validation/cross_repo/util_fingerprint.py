# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fingerprint utility for cross-repo validation.

Generates deterministic fingerprints for validation violations
to enable stable baseline tracking and suppression.

Fingerprint formula: hash(rule_id, file_path, import_path)[:16]

Related ticket: OMN-1774
"""

from __future__ import annotations

import hashlib


def generate_fingerprint(
    rule_id: str,  # string-id-ok: canonical rule registry key, not a database UUID
    file_path: str,
    symbol: str,
) -> str:
    """Generate a stable fingerprint for a validation violation.

    The fingerprint is a 16-character hex string derived from SHA-256
    of the concatenated inputs. This provides:
    - Determinism: Same inputs always produce same output
    - Uniqueness: Different inputs produce different outputs
    - Stability: Fingerprints survive code reformatting

    Args:
        rule_id: The canonical rule identifier (e.g., "repo_boundaries").
        file_path: Path to the file, relative to repo root.
        symbol: The imported module path that triggered the violation.

    Returns:
        A 16-character lowercase hex string.

    Example:
        >>> generate_fingerprint("repo_boundaries", "src/app/handler.py", "infra.services")
        'a1b2c3d4e5f67890'  # Example output
    """
    # Normalize inputs to ensure consistent fingerprints
    normalized_rule = rule_id.strip()
    normalized_path = file_path.strip()
    normalized_symbol = symbol.strip()

    # Concatenate with delimiters to prevent ambiguity
    # Using null byte as delimiter since it cannot appear in any of the inputs
    content = f"{normalized_rule}\x00{normalized_path}\x00{normalized_symbol}"

    # Generate SHA-256 hash
    hash_bytes = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Return first 16 hex characters (64 bits of entropy)
    return hash_bytes[:16]
