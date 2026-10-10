# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure fingerprint computation — no I/O, no logging (compute node policy).

Ticket: OMN-3556
"""

from __future__ import annotations

import hashlib
import json
import re

_FRAME_RE = re.compile(r'File "([^"]+)", line \d+, in (\w+)')
_MEMORY_RE = re.compile(r"0x[0-9a-fA-F]+")


def _extract_frames(traceback: str) -> list[str]:
    """Extract file:function frames from a Python traceback.

    Uses last 2 path components (not just basename) to avoid collisions
    between same-named files in different packages (e.g. pkg_a/foo.py vs
    pkg_b/foo.py would collide if we used basename only).

    Line numbers are stripped — same error at a different line is the same frame.
    Memory addresses are stripped before frame extraction.
    Frame order is preserved (encodes call stack identity).
    """
    clean = _MEMORY_RE.sub("0xADDR", traceback)
    frames = []
    for match in _FRAME_RE.finditer(clean):
        path, func = match.group(1), match.group(2)
        # Use last 2 path components to avoid basename collisions in monorepos
        parts = path.replace("\\", "/").split("/")
        short_path = "/".join(parts[-2:]).strip('"')
        frames.append(f"{short_path}:{func}")
    return frames


def compute_error_fingerprint(
    failure_output: str,
    failing_tests: list[str],
) -> str:
    """Compute a stable fingerprint for a CI failure.

    Fingerprint is SHA-256 of:
        - extracted frames in stack order (not sorted — order is identity)
        - failing test names sorted (order-independent)

    Returns hex digest string.
    """
    frames = _extract_frames(failure_output)
    sorted_tests = sorted(failing_tests)
    payload = json.dumps({"frames": frames, "tests": sorted_tests}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
    "_extract_frames",
    "compute_error_fingerprint",
]
