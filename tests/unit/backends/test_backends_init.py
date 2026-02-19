# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Basic sanity test for backends package."""

import pytest


@pytest.mark.unit
class TestBackendsPackage:
    """Test backends package structure."""

    @pytest.mark.timeout(60)
    def test_backends_submodules_exist(self) -> None:
        """Verify backends submodules are importable."""
        from tests.unit.backends import cache, metrics

        assert cache is not None
        assert metrics is not None
