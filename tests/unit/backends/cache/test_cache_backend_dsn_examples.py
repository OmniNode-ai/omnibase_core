# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for source examples that should not embed local DSNs."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
FLAGGED_SOURCE_MODULES = (
    "src/omnibase_core/backends/cache/__init__.py",
    "src/omnibase_core/backends/cache/backend_cache_redis.py",
    "src/omnibase_core/mixins/mixin_caching.py",
)
CONCRETE_LOCAL_REDIS_DSNS = (
    "redis://localhost:16379",
    "redis://localhost:16379/0",
)


@pytest.mark.unit
@pytest.mark.parametrize("module_path", FLAGGED_SOURCE_MODULES)
def test_flagged_cache_modules_do_not_embed_concrete_local_redis_dsn(
    module_path: str,
) -> None:
    """Cache examples should rely on caller-owned config, not local DSNs."""
    source = (REPO_ROOT / module_path).read_text(encoding="utf-8")

    for dsn in CONCRETE_LOCAL_REDIS_DSNS:
        assert dsn not in source
