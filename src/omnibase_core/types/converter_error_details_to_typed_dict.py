from __future__ import annotations

"""
Convert legacy error dict[str, Any] to TypedDict.
"""


from .typed_dict_error_details import TypedDictErrorDetails
from .typed_dict_legacy_error import TypedDictLegacyError
from .util_datetime_parser import parse_datetime


def convert_error_details_to_typed_dict(
    error: TypedDictLegacyError,
) -> TypedDictErrorDetails:
    """Convert legacy error dict[str, Any] to TypedDict."""
    result = TypedDictErrorDetails(
        error_code=str(error.get("error_code", "")),
        error_message=str(error.get("error_message", "")),
        error_type=str(error.get("error_type", "")),
        timestamp=parse_datetime(error.get("timestamp")),
    )

    if "stack_trace" in error and error["stack_trace"] is not None:
        result["stack_trace"] = str(error["stack_trace"])

    if "context" in error and isinstance(error["context"], dict):
        context_dict: dict[str, str] = {
            k: str(v) for k, v in error["context"].items() if v is not None
        }
        result["context"] = context_dict

    return result
