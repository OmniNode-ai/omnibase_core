# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.813577'
# description: Stamped by ToolPython
# entrypoint: python://template_type
# hash: 98974d07ed33338caa5298e9dd587e12dc4b11b907a4e905aa45abeff5b20588
# last_modified_at: '2025-05-29T14:13:58.578412+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: template_type.py
# namespace: python://omnibase.enums.template_type
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 0546e615-0213-4b0a-8cac-b67d73a7c281
# version: 1.0.0
# === /OmniNode:Metadata ===


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTemplateType(StrValueHelper, str, Enum):
    """
    Canonical template types for metadata stamping and registry.
    """

    MINIMAL = "minimal"
    EXTENDED = "extended"
    YAML = "yaml"
    MARKDOWN = "markdown"
