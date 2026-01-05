"""
CLI Operations Models

Models for command-line interface operations, execution, and results.

Deprecated Aliases (OMN-1071)
=============================
This module provides deprecated aliases for classes renamed in v0.4.0.
The following aliases will be removed in a future version:

- ``ModelCliResultFormatter`` -> use ``UtilCliResultFormatter`` from
  ``omnibase_core.utils.util_cli_result_formatter``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names.
"""

from typing import Any

from omnibase_core.types import (
    TypedDictCliInputDict,
    TypedDictDebugInfoData,
    TypedDictPerformanceMetricData,
    TypedDictTraceInfoData,
)

from .model_cli_action import ModelCliAction
from .model_cli_advanced_params import ModelCliAdvancedParams
from .model_cli_command_option import ModelCliCommandOption
from .model_cli_debug_info import ModelCliDebugInfo
from .model_cli_execution import ModelCliExecution
from .model_cli_execution_context import ModelCliExecutionContext
from .model_cli_execution_input_data import ModelCliExecutionInputData
from .model_cli_execution_result import ModelCliExecutionResult
from .model_cli_execution_summary import ModelCliExecutionSummary
from .model_cli_node_execution_input import ModelCliNodeExecutionInput
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result import ModelCliResult
from .model_diff_entry import ModelDiffEntry
from .model_diff_result import ModelDiffResult
from .model_output_format_options import ModelOutputFormatOptions

__all__ = [
    "ModelCliAction",
    "ModelCliAdvancedParams",
    "ModelCliCommandOption",
    "ModelCliDebugInfo",
    "ModelCliExecution",
    "ModelCliExecutionContext",
    "ModelCliExecutionInputData",
    "ModelCliExecutionResult",
    "ModelCliExecutionSummary",
    "ModelCliNodeExecutionInput",
    "ModelCliOutputData",
    "ModelCliResult",
    "ModelDiffEntry",
    "ModelDiffResult",
    "ModelOutputFormatOptions",
    "TypedDictCliInputDict",
    "TypedDictDebugInfoData",
    "TypedDictPerformanceMetricData",
    "TypedDictTraceInfoData",
    # DEPRECATED: Use UtilCliResultFormatter from omnibase_core.utils instead
    "ModelCliResultFormatter",
]


# =============================================================================
# Deprecated aliases: Lazy-load with warnings per OMN-1071 renaming.
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy loading for deprecated aliases per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelCliResultFormatter -> UtilCliResultFormatter
    """
    import warnings

    if name == "ModelCliResultFormatter":
        warnings.warn(
            "'ModelCliResultFormatter' is deprecated, use 'UtilCliResultFormatter' "
            "from 'omnibase_core.utils.util_cli_result_formatter' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        from omnibase_core.utils.util_cli_result_formatter import UtilCliResultFormatter

        return UtilCliResultFormatter

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
