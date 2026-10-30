# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Collect GitHub lineage probes only when explicitly opted in, like validator lab tests."""

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--dev-tag-lineage-live",
        action="store_true",
        help="Run the GitHub dev-tag lineage probes",
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    if collection_path.name.startswith("test_") and not config.getoption(
        "--dev-tag-lineage-live"
    ):
        return True
    return None
