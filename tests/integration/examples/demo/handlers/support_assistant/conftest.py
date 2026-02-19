# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for support assistant integration tests."""

import os

import pytest


@pytest.fixture(scope="session")
def local_llm_url() -> str:
    """URL for local LLM server.

    Uses session scope since this is a constant value read from environment.
    Defaults to localhost for portability.
    """
    return os.getenv("LLM_LOCAL_URL", "http://localhost:8200")


@pytest.fixture(scope="session")
def local_model_name() -> str:
    """Model name for local LLM server.

    Uses session scope since this is a constant value.
    """
    return os.getenv("LLM_LOCAL_MODEL", "qwen2.5-14b")
