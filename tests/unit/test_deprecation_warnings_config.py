"""
Test suite for pytest deprecation warning configuration (OMN-199).

This module serves as a canary test to verify that pytest is properly configured
to display DeprecationWarning and PendingDeprecationWarning during test runs.
If the pytest filterwarnings configuration is broken or removed, these tests
will fail, alerting developers to the issue.

Configuration Location:
    pyproject.toml -> [tool.pytest.ini_options] -> filterwarnings

Related Issue: OMN-199 - Configure pytest deprecation warning capture
"""

from __future__ import annotations

import warnings

import pytest


@pytest.mark.unit
class TestDeprecationWarningsConfig:
    """Tests verifying pytest deprecation warning configuration works correctly."""

    def test_deprecation_warnings_are_displayed(self) -> None:
        """Verify pytest displays DeprecationWarning (OMN-199).

        This test serves as a canary to detect if the pytest filterwarnings
        configuration for DeprecationWarning is broken or removed.
        """
        with pytest.warns(DeprecationWarning, match="test deprecation warning"):
            warnings.warn("test deprecation warning", DeprecationWarning, stacklevel=1)

    def test_pending_deprecation_warnings_are_displayed(self) -> None:
        """Verify pytest displays PendingDeprecationWarning (OMN-199).

        This test serves as a canary to detect if the pytest filterwarnings
        configuration for PendingDeprecationWarning is broken or removed.
        """
        with pytest.warns(PendingDeprecationWarning, match="test pending deprecation"):
            warnings.warn(
                "test pending deprecation", PendingDeprecationWarning, stacklevel=1
            )

    def test_deprecation_warning_category_is_correct(self) -> None:
        """Verify DeprecationWarning is captured with correct category.

        Tests that warnings are captured as DeprecationWarning, not converted
        to another warning type by the filter configuration.
        """
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            warnings.warn("category test warning", DeprecationWarning, stacklevel=1)

            assert len(captured) == 1
            assert issubclass(captured[0].category, DeprecationWarning)
            assert "category test warning" in str(captured[0].message)

    def test_pending_deprecation_warning_category_is_correct(self) -> None:
        """Verify PendingDeprecationWarning is captured with correct category.

        Tests that warnings are captured as PendingDeprecationWarning, not
        converted to another warning type by the filter configuration.
        """
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            warnings.warn(
                "pending category test warning", PendingDeprecationWarning, stacklevel=1
            )

            assert len(captured) == 1
            assert issubclass(captured[0].category, PendingDeprecationWarning)
            assert "pending category test warning" in str(captured[0].message)

    def test_multiple_deprecation_warnings_are_captured(self) -> None:
        """Verify multiple deprecation warnings can be captured in sequence.

        Ensures the configuration doesn't suppress repeated warnings, which
        is important for identifying multiple deprecation issues.
        """
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            warnings.warn("first deprecation", DeprecationWarning, stacklevel=1)
            warnings.warn("second deprecation", DeprecationWarning, stacklevel=1)
            warnings.warn("third deprecation", DeprecationWarning, stacklevel=1)

            assert len(captured) == 3
            assert all(issubclass(w.category, DeprecationWarning) for w in captured)

    def test_deprecation_warning_includes_stacklevel(self) -> None:
        """Verify deprecation warnings preserve stacklevel information.

        Tests that the warning configuration preserves the ability to track
        the source location of deprecation warnings, which is critical for
        identifying and fixing deprecated code usage.
        """

        def deprecated_function() -> None:
            """Simulate a deprecated function."""
            warnings.warn(
                "deprecated_function is deprecated, use new_function instead",
                DeprecationWarning,
                stacklevel=2,
            )

        with pytest.warns(DeprecationWarning, match="deprecated_function"):
            deprecated_function()
