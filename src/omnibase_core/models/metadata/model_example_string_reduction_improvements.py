"""
String Field Reduction Improvements Demonstration.

This file demonstrates the improvements made to reduce excessive string fields
in metadata models while maintaining functionality and improving consistency.
"""

from __future__ import annotations

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.models.metadata.model_function_node_data import ModelFunctionNodeData
from omnibase_core.models.metadata.model_metadata_node_info import ModelMetadataNodeInfo
from omnibase_core.models.metadata.model_node_info_summary import ModelNodeInfoSummary
from omnibase_core.models.metadata.model_structured_description import (
    ModelStructuredDescription,
)
from omnibase_core.models.metadata.model_structured_display_name import (
    ModelStructuredDisplayName,
)
from omnibase_core.models.metadata.model_structured_tags import ModelStructuredTags


def demonstrate_string_field_improvements() -> None:
    """
    Demonstrate the improvements made to reduce string field reliance.

    BEFORE: Models had excessive unstructured string fields
    AFTER: Models use structured types with validation and consistency
    """

    print("=== STRING FIELD REDUCTION IMPROVEMENTS ===\n")

    # 1. Demonstrate Structured Display Names
    print("1. STRUCTURED DISPLAY NAMES")
    print("BEFORE: node_display_name: str | None")
    print("AFTER:  display_name: ModelStructuredDisplayName")

    structured_name = ModelStructuredDisplayName.for_function_node(
        "user_auth",
        category=EnumStandardCategory.AUTHENTICATION,
    )
    print(f"   Generated name: {structured_name.display_name}")
    print(f"   Human readable: {structured_name.human_readable_name}")
    print(f"   Category qualified: {structured_name.category_qualified_name}")
    print()

    # 2. Demonstrate Structured Descriptions
    print("2. STRUCTURED DESCRIPTIONS")
    print("BEFORE: description: str")
    print("AFTER:  description: ModelStructuredDescription")

    structured_desc = ModelStructuredDescription.for_function_node(
        "user_auth",
        functionality="Authenticates users with JWT tokens and RBAC",
        category=EnumStandardCategory.AUTHENTICATION,
    )
    print(f"   Purpose: {structured_desc.purpose}")
    print(f"   Full description: {structured_desc.full_description}")
    print(f"   Use cases: {', '.join(structured_desc.use_cases)}")
    print()

    # 3. Demonstrate Structured Tags
    print("3. STRUCTURED TAGS")
    print("BEFORE: tags: list[str]")
    print("AFTER:  tags: ModelStructuredTags")

    structured_tags = ModelStructuredTags.for_function_node(
        function_category=EnumStandardCategory.AUTHENTICATION,
        complexity=EnumStandardTag.MODERATE,
        custom_tags=["jwt", "rbac"],
    )
    print(f"   Standard tags: {[tag.value for tag in structured_tags.standard_tags]}")
    print(f"   Primary category: {structured_tags.primary_category}")
    print(f"   Custom tags: {structured_tags.custom_tags}")
    print(f"   All tags: {structured_tags.all_tags}")
    print()

    # 4. Demonstrate Model Improvements
    print("4. MODEL IMPROVEMENTS")

    # Function Node Data
    print("ModelFunctionNodeData:")
    function_node = ModelFunctionNodeData.create_function_node(
        name="user_authentication",
        description_purpose="Secure user authentication with multiple providers",
        function_category=EnumStandardCategory.AUTHENTICATION,
        complexity=EnumStandardTag.MODERATE,
        custom_tags=["oauth", "jwt", "security"],
    )
    print(f"   Display name: {function_node.display_name.display_name}")
    print(f"   Description: {function_node.description.summary_description}")
    print(f"   Tags: {function_node.tags.all_tags}")
    print()

    # Metadata Node Info
    print("ModelMetadataNodeInfo:")
    node_info = ModelMetadataNodeInfo.create_function_info(
        name="api_endpoint_auth",
        description="API endpoint authentication and authorization",
    )
    print(f"   Display name: {node_info.display_name.display_name}")
    print(f"   Description: {node_info.description.summary_description}")
    print(f"   Tags: {node_info.tags.all_tags}")
    print(
        f"   Categories: {[cat for cat in [node_info.tags.primary_category] + node_info.tags.secondary_categories if cat is not None]}",
    )
    print()

    # Node Info Summary
    print("ModelNodeInfoSummary:")
    summary = ModelNodeInfoSummary.create_minimal_node(
        node_name="auth_summary",
        node_type=EnumNodeType.FUNCTION,
    )
    # Set additional properties
    summary.core.description = "Authentication system summary"
    summary.categorization.tags = ["production", "monitored"]
    print(f"   Display name: {summary.node_display_name}")
    print(f"   Description: {summary.description}")
    print(f"   Tags: {summary.tags}")
    print(f"   Categories: {summary.categories}")
    print()


def demonstrate_benefits() -> None:
    """Demonstrate the benefits of the structured approach."""

    print("=== BENEFITS OF STRUCTURED TYPES ===\n")

    print("1. CONSISTENCY")
    print("   - Standardized naming patterns across all models")
    print("   - Consistent tag categorization with EnumStandardTag")
    print("   - Uniform description templates\n")

    print("2. VALIDATION")
    print("   - Structured naming prevents invalid characters")
    print("   - Tag validation ensures proper classification")
    print("   - Description templates ensure completeness\n")

    print("3. MAINTAINABILITY")
    print("   - Central enum management for tags and categories")
    print("   - Clean property access patterns")
    print("   - Easy updates to naming conventions\n")

    print("4. DISCOVERABILITY")
    print("   - Categorical organization of tags and names")
    print("   - Human-readable alternatives for display")
    print("   - Structured search and filtering capabilities\n")

    print("5. REDUCED STRING FIELD RELIANCE")
    print("   - ModelFunctionNodeData: 3 string fields → 0 direct string fields")
    print("   - ModelMetadataNodeInfo: 4 string fields → 0 direct string fields")
    print("   - ModelNodeInfoSummary: 4 string fields → 0 direct string fields")
    print("   - Direct access to structured data types\n")


if __name__ == "__main__":
    demonstrate_string_field_improvements()
    print("\n" + "=" * 50 + "\n")
    demonstrate_benefits()
