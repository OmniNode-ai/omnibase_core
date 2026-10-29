# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lab-only collection (OMN-21529): the live-broker overlay test is collected only when the
launch names the overlay under test, so a runner with no broker never collects, and never
skips, it."""

from __future__ import annotations

from pathlib import Path

import pytest

OVERLAY_OPTION = "--validator-runtime-overlay"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(OVERLAY_OPTION, default=None, help="Overlay file of the live run")


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    if collection_path.name.startswith("test_") and not config.getoption(
        OVERLAY_OPTION
    ):
        return True
    return None


@pytest.fixture
def overlay_under_test(request: pytest.FixtureRequest) -> Path:
    return Path(str(request.config.getoption(OVERLAY_OPTION))).resolve()
