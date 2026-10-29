# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Console caller of the source-file gather node for private vocabularies (OMN-21494).

The console script ``resolve-private-vocabulary`` hands its arguments to the
composition root and prints the resolved path, or one refusal line. The process
environment and the clock are captured once, here, at the process boundary, and
travel on the request.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    build_container,
    capture_environment,
    resolve_private_vocabulary,
)

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Print the resolved path, or one refusal line on stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Contract vocabulary name.")
    parser.add_argument("--path", type=Path, help="Explicit vocabulary path.")
    args = parser.parse_args(argv)
    try:
        container = build_container()
        resolution = resolve_private_vocabulary(
            container,
            args.name,
            environment=capture_environment(container),
            now=datetime.now(UTC),
            explicit_path=args.path,
        )
    except ModelOnexError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return 1
    if resolution.found:
        sys.stdout.write(f"{resolution.path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
