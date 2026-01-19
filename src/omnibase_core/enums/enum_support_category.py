"""Support ticket category classification."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSupportCategory(StrValueHelper, str, Enum):
    """Support ticket category for routing and classification.

    Categories are hierarchical with a primary domain (billing, account, technical)
    and a secondary type within that domain.
    """

    BILLING_REFUND = "billing_refund"
    BILLING_PAYMENT = "billing_payment"
    ACCOUNT_ACCESS = "account_access"
    ACCOUNT_PROFILE = "account_profile"
    TECHNICAL_BUG = "technical_bug"
    TECHNICAL_HOWTO = "technical_howto"


__all__ = ["EnumSupportCategory"]
