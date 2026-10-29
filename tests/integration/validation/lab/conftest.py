# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lab-only collection (OMN-21529): the live-broker overlay test is collected only when the
launch names the overlay under test, so a runner with no broker never collects, and never
skips, it."""

from __future__ import annotations

from pathlib import Path

import pytest

OVERLAY_OPTION = "--validator-runtime-overlay"
BROKER_OPTION = "--validator-runtime-broker"
BROKER_ENV = "KAFKA_BOOTSTRAP_SERVERS"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(OVERLAY_OPTION, default=None, help="Overlay file of the live run")
    parser.addoption(
        BROKER_OPTION,
        default=None,
        help="Value of the broker address the overlay's ${env.KAFKA_BOOTSTRAP_SERVERS} names",
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    if collection_path.name.startswith("test_") and not config.getoption(
        OVERLAY_OPTION
    ):
        return True
    return None


@pytest.fixture
def overlay_under_test(request: pytest.FixtureRequest) -> Path:
    return Path(str(request.config.getoption(OVERLAY_OPTION))).resolve()


@pytest.fixture(autouse=True)
def broker_in_environment(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The suite's autouse isolation clears the broker variable; restore the launch's value."""
    broker = request.config.getoption(BROKER_OPTION)
    if broker:
        monkeypatch.setenv(BROKER_ENV, str(broker))
