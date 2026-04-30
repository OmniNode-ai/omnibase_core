# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import math

import pytest

from omnibase_core.analysis.co_change_matrix import compute_lift, compute_npmi
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


def test_npmi_perfect_correlation() -> None:
    # both files always co-occur: p_ab == p_a == p_b
    npmi = compute_npmi(p_a=0.5, p_b=0.5, p_ab=0.5)
    assert math.isclose(npmi, 1.0, abs_tol=1e-9)


def test_npmi_independence() -> None:
    # independent: p_ab = p_a * p_b
    npmi = compute_npmi(p_a=0.5, p_b=0.5, p_ab=0.25)
    assert math.isclose(npmi, 0.0, abs_tol=1e-9)


def test_npmi_clamped() -> None:
    result = compute_npmi(p_a=0.5, p_b=0.5, p_ab=0.0001)
    assert -1.0 <= result <= 1.0


def test_npmi_zero_p_ab_returns_minus_one() -> None:
    assert compute_npmi(p_a=0.5, p_b=0.5, p_ab=0.0) == -1.0


def test_npmi_p_ab_one_returns_one() -> None:
    assert compute_npmi(p_a=1.0, p_b=1.0, p_ab=1.0) == 1.0


def test_npmi_out_of_range_raises() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        compute_npmi(p_a=0.5, p_b=0.5, p_ab=-0.1)
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


def test_npmi_p_ab_exceeds_min_pa_pb_raises() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        compute_npmi(p_a=0.3, p_b=0.4, p_ab=0.35)
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


def test_lift_above_one_when_correlated() -> None:
    assert compute_lift(p_a=0.5, p_b=0.5, p_ab=0.5) > 1.0


def test_lift_one_when_independent() -> None:
    result = compute_lift(p_a=0.5, p_b=0.5, p_ab=0.25)
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_lift_zero_when_p_a_is_zero() -> None:
    assert compute_lift(p_a=0.0, p_b=0.5, p_ab=0.0) == 0.0


def test_lift_zero_when_p_b_is_zero() -> None:
    assert compute_lift(p_a=0.5, p_b=0.0, p_ab=0.0) == 0.0


def test_lift_out_of_range_raises() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        compute_lift(p_a=1.5, p_b=0.5, p_ab=0.5)
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


def test_lift_p_ab_exceeds_min_pa_pb_raises() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        compute_lift(p_a=0.3, p_b=0.4, p_ab=0.35)
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
