"""
Type aliases for Universal Conversation Memory System.

IMPORTANT: The ugly Dict-based type aliases have been REPLACED with proper
Pydantic models following ONEX architectural standards. This module now
contains only the remaining legacy aliases for CLI configuration.

## New ONEX-Compliant Models (USE THESE INSTEAD):
- ModelSessionData - Replaces SessionDataType
- ModelSessionExport - Replaces SessionExportType
- ModelSessionStats - Replaces SessionMetadataType
- ModelConversationFilter - Replaces ConversationFilterType
- ModelStatistics - Replaces StatisticsType

## Migration Path:
All new code should use the proper Pydantic models above. These provide:
- Runtime validation and type safety
- Better IDE support and auto-completion
- Clean, maintainable architecture following ONEX standards
- Proper error handling and validation

## Imports:
```python
from omnibase_core.model.memory.model_session_data import ModelSessionData
from omnibase_core.model.memory.model_session_export import ModelSessionExport
from omnibase_core.model.memory.model_session_stats import ModelSessionStats
from omnibase_core.model.memory.model_conversation_filter import ModelConversationFilter
from omnibase_core.model.memory.model_statistics import ModelStatistics
```
"""

from omnibase_core.core.common_types import ModelScalarValue

# Type aliases for CLI configuration
CliConfigType = dict[str, str | int | bool]
"""CLI configuration structure for user preferences and settings.

Supports:
- String values: api_url, api_key, export_format
- Integer values: default_limit, connection_timeout
- Boolean values: auto_session, rich_output, verbose_logging

Example:
    config: CliConfigType = {
        "api_url": "http://localhost:8089/api/v1",
        "default_limit": 10,
        "rich_output": True
    }
"""

ExportFormatType = ModelScalarValue
"""Flexible value type for export format configuration.

Allows various data types in export configurations to support
different export formats and their specific requirements.

Used in CLI configuration functions for flexible parameter handling
where export settings may need different data types based on format.

Example:
    export_config: Dict[str, ExportFormatType] = {
        "format": "json",           # str
        "include_metadata": True,   # bool
        "max_results": 1000,        # int
        "similarity_threshold": 0.7 # float
    }
"""
