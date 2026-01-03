# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for invariant evaluation service tests.

Provides reusable fixtures for:
- ServiceInvariantEvaluator instances (default and with allow-list)
- Common invariant configurations for testing
"""

import pytest

from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.fixture
def evaluator() -> ServiceInvariantEvaluator:
    """Provide a default ServiceInvariantEvaluator instance.

    Returns:
        ServiceInvariantEvaluator with no import restrictions (trusted code model).
    """
    return ServiceInvariantEvaluator()


@pytest.fixture
def evaluator_with_allowlist() -> ServiceInvariantEvaluator:
    """Provide a ServiceInvariantEvaluator with import path restrictions.

    Returns:
        ServiceInvariantEvaluator that only allows imports from
        tests.unit.services.invariant.custom_validators module.
    """
    return ServiceInvariantEvaluator(
        allowed_import_paths=["tests.unit.services.invariant.custom_validators"]
    )
