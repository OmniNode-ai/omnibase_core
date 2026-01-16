"""Enumeration for invariant report status."""

from enum import Enum

from omnibase_core.utils.util_str_enum_base import StrValueHelper


class EnumInvariantReportStatus(StrValueHelper, str, Enum):
    """Overall status of an invariant evaluation report."""

    PASSED = "passed"  # All invariants passed
    FAILED = "failed"  # Completed, has violations
    PARTIAL = "partial"  # Some checks skipped or errored
    ERROR = "error"  # Evaluation itself failed to run


__all__ = ["EnumInvariantReportStatus"]
