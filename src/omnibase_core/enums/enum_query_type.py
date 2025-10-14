"""
Query type enumeration for LLM routing and model selection.

Defines the types of queries for intelligent model routing and
specialized processing in conversational RAG systems.
"""

from enum import Enum


class EnumQueryType(str, Enum):
    """
    Query type enumeration for LLM model selection and routing.

    Used to determine the most appropriate model for specific query types
    in conversational RAG and document processing systems.
    """

    # General query types
    EXPLANATION = "explanation"
    GENERAL = "general"
    CONVERSATION = "conversation"
    DOCUMENTATION = "documentation"

    # Technical query types
    CODE = "code"
    TECHNICAL = "technical"
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"

    # Analysis query types
    ANALYSIS = "analysis"
    COMPARISON = "comparison"
    EVALUATION = "evaluation"

    # Search and retrieval types
    SEARCH = "search"
    LOOKUP = "lookup"
    REFERENCE = "reference"

    # Creative and planning types
    CREATIVE = "creative"
    PLANNING = "planning"
    BRAINSTORMING = "brainstorming"
